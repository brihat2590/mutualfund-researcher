import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.models import RollingStats, RollingReturnPoint
import logging

logger = logging.getLogger(__name__)

class RollingCalculator:
    @staticmethod
    def calculate_5y_rolling_returns(
        dates: List[str],
        navs: List[float],
        tolerance_days: int = 10
    ) -> Optional[RollingStats]:
        """
        Calculates 5-year rolling returns CAGR for daily NAV series.
        Finds the matching trading day ~5 years prior (t - 5 years) within tolerance.
        CAGR = (NAV_t / NAV_{t-5y}) ** (1 / actual_years) - 1.
        """
        if not dates or not navs or len(dates) < 250 * 5:
            return None

        try:
            df = pd.DataFrame({"date": pd.to_datetime(dates), "nav": navs})
            df = df.dropna().sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)
            df.set_index("date", inplace=True)
            dates_idx = df.index

            rolling_points: List[RollingReturnPoint] = []
            rolling_cagrs: List[float] = []

            for cur_date in dates_idx:
                target_5y_ago = cur_date - pd.DateOffset(years=5)
                if target_5y_ago < dates_idx[0]:
                    continue

                # Binary search for closest trading day on or before target_5y_ago
                idx = dates_idx.searchsorted(target_5y_ago, side="right") - 1
                if idx >= 0:
                    hist_date = dates_idx[idx]
                    diff_days = (target_5y_ago - hist_date).days
                    if diff_days <= tolerance_days:
                        nav_now = df.loc[cur_date, "nav"]
                        nav_then = df.loc[hist_date, "nav"]

                        if nav_then > 0 and nav_now > 0:
                            actual_years = (cur_date - hist_date).days / 365.25
                            cagr = ((nav_now / nav_then) ** (1.0 / actual_years) - 1.0) * 100.0
                            rolling_cagrs.append(cagr)
                            rolling_points.append(
                                RollingReturnPoint(
                                    date=cur_date.strftime("%Y-%m-%d"),
                                    hist_date=hist_date.strftime("%Y-%m-%d"),
                                    cagr=round(cagr, 2)
                                )
                            )

            if len(rolling_cagrs) < 20: # Require sufficient rolling observations
                return None

            arr = np.array(rolling_cagrs)
            mean_cagr = float(np.mean(arr))
            median_cagr = float(np.median(arr))
            min_cagr = float(np.min(arr))
            max_cagr = float(np.max(arr))
            std_cagr = float(np.std(arr))

            prob_10 = float(np.mean(arr > 10.0) * 100.0)
            prob_12 = float(np.mean(arr > 12.0) * 100.0)
            prob_15 = float(np.mean(arr > 15.0) * 100.0)
            prob_neg = float(np.mean(arr < 0.0) * 100.0)

            # Sample the rolling series (e.g., every 5th or 10th point for fast charting)
            # or keep weekly points (~every 5 trading days)
            step = max(1, len(rolling_points) // 300)
            sampled_series = rolling_points[::step]
            if rolling_points and (not sampled_series or sampled_series[-1].date != rolling_points[-1].date):
                sampled_series.append(rolling_points[-1])

            return RollingStats(
                mean=round(mean_cagr, 2),
                median=round(median_cagr, 2),
                min_return=round(min_cagr, 2),
                max_return=round(max_cagr, 2),
                std_dev=round(std_cagr, 2),
                prob_above_10=round(prob_10, 1),
                prob_above_12=round(prob_12, 1),
                prob_above_15=round(prob_15, 1),
                prob_negative=round(prob_neg, 1),
                observation_count=len(rolling_cagrs),
                rolling_series=sampled_series
            )
        except Exception as e:
            logger.error(f"Error computing rolling returns: {e}")
            return None
