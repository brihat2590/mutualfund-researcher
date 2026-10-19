from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import logging

from app.dhan_client import DhanClient
from app.rolling_calc import RollingCalculator
from app.rating_engine import RatingEngine
from app.cache_db import CacheDB
from app.models import FundResearchItem, CategorySummaryKPI, ResearchResponse

logger = logging.getLogger(__name__)

class MutualFundResearcher:
    def __init__(self, cache_db: Optional[CacheDB] = None, dhan_client: Optional[DhanClient] = None):
        self.cache = cache_db or CacheDB()
        self.client = dhan_client or DhanClient()

    def research_category(self, subcategory_name: str, force_refresh: bool = False) -> ResearchResponse:
        """
        Executes full research for a mutual fund category:
        1. Checks cache if not force_refresh
        2. Searches Dhan API for category schemes
        3. Filters schemes with inception age >= 9 years
        4. Fetches NAV data & calculates 5-year rolling returns
        5. Computes multi-factor rating out of 10
        6. Caches results in SQLite and returns sorted list
        """
        subcategory_name = subcategory_name.strip()
        if not force_refresh:
            cached_data = self.cache.get_subcategory_cache(subcategory_name)
            if cached_data:
                summary_dict, funds = cached_data
                summary = CategorySummaryKPI(
                    total_funds_searched=summary_dict.get("total_funds_searched", len(funds)),
                    qualifying_funds_9y=len(funds),
                    category_avg_rolling_mean=summary_dict.get("category_avg_rolling_mean", 0.0),
                    category_avg_ter=summary_dict.get("category_avg_ter", 0.0),
                    category_avg_aum=summary_dict.get("category_avg_aum", 0.0),
                    category_top_rated_fund=summary_dict.get("category_top_rated_fund", ""),
                    category_top_rating=summary_dict.get("category_top_rating", 0.0),
                    is_cached=True,
                    last_updated=summary_dict.get("last_updated", datetime.now().strftime("%Y-%m-%d %H:%M"))
                )
                return ResearchResponse(
                    subcategory=subcategory_name,
                    summary=summary,
                    funds=funds
                )

        # Fresh Fetch & Calculation
        all_schemes = self.client.search_funds_by_subcategory(subcategory_name)
        now = datetime.now()
        nine_years_days = 9.0 * 365.25

        qualifying_raw_funds = []
        for s in all_schemes:
            inc_str = s.get("dmfm_inception_date")
            if inc_str:
                try:
                    inc_date = datetime.strptime(inc_str.split()[0], "%Y-%m-%d")
                    age_years = (now - inc_date).days / 365.25
                    if age_years >= 9.0:
                        qualifying_raw_funds.append((s, inc_date, age_years))
                except Exception as e:
                    pass

        def process_fund(fund_tuple) -> Optional[FundResearchItem]:
            s, inc_date, age_years = fund_tuple
            scode = str(s.get("dmfm_cmots_scheme_code") or "").strip()
            if not scode:
                return None

            # Historical chart fetch (10 years back to ensure full 5-year rolling coverage)
            start_date = (now - timedelta(days=int(10.5 * 365.25))).strftime("%Y-%m-%d")
            chart_res = self.client.fetch_nav_chart(scode, start_date=start_date)
            dates = chart_res.get("dates", [])
            navs = chart_res.get("navs", [])

            rolling_stats = RollingCalculator.calculate_5y_rolling_returns(dates, navs)
            if not rolling_stats:
                return None

            # Parse metadata
            fund_name = s.get("dmfm_scheme_name") or "Unknown Fund"
            amc_name = s.get("dmfm_amc_name") or ""
            aum = float(s.get("dmfm_scheme_aum") or 0.0)
            
            # Expense ratio: check multiple fields provided by Dhan
            raw_ter = s.get("dmfm_expense_ratio") or s.get("dmfm_ter") or 0.0
            try:
                expense_ratio = float(raw_ter)
            except:
                expense_ratio = 1.0

            # Minimum SIP amount
            raw_sip = s.get("dmfm_sip_min_amt_m") or s.get("dmfm_min_sip_invest_amt") or 500.0
            try:
                min_sip_amount = float(raw_sip)
            except:
                min_sip_amount = 500.0

            benchmark = s.get("dmfm_benchmark") or "N/A"
            fund_manager = s.get("dmfm_fund_manager") or "N/A"
            risk_level = s.get("dmfm_risk_value") or "High"
            exit_load = s.get("dmfm_exit_load") or "N/A"
            latest_nav = float(s.get("dmfm_latest_nav_value") or 0.0)
            latest_nav_date = s.get("dmfm_latest_nav_date") or ""

            # Precalculated returns from Dhan API
            def parse_float(key):
                val = s.get(key)
                if val is not None:
                    try:
                        return float(val)
                    except:
                        return None
                return None

            pre_1m = parse_float("dmfm_scheme_1_month_return")
            pre_3m = parse_float("dmfm_scheme_3_month_return")
            pre_6m = parse_float("dmfm_scheme_6_month_return")
            pre_1y = parse_float("dmfm_scheme_1_year_return")
            pre_3y = parse_float("dmfm_scheme_3_year_return")
            pre_5y = parse_float("dmfm_scheme_5_year_return")
            pre_3y_abs = parse_float("dmfm_3_year_absolute_return")
            pre_5y_abs = parse_float("dmfm_5_year_absolute_return")

            # Rating calculation
            rating_breakdown = RatingEngine.calculate_rating(
                rolling=rolling_stats,
                expense_ratio=expense_ratio,
                aum=aum,
                precalculated_5y=pre_5y or rolling_stats.mean
            )

            return FundResearchItem(
                scode=scode,
                fund_name=fund_name,
                amc_name=amc_name,
                subcategory_name=subcategory_name,
                inception_date=inc_date.strftime("%Y-%m-%d"),
                age_years=round(age_years, 1),
                aum=round(aum, 2),
                expense_ratio=round(expense_ratio, 2),
                min_sip_amount=round(min_sip_amount, 2),
                benchmark=benchmark,
                fund_manager=fund_manager,
                risk_level=risk_level,
                exit_load=exit_load,
                latest_nav=latest_nav,
                latest_nav_date=latest_nav_date,
                precalculated_1m=pre_1m,
                precalculated_3m=pre_3m,
                precalculated_6m=pre_6m,
                precalculated_1y=pre_1y,
                precalculated_3y=pre_3y,
                precalculated_5y=pre_5y,
                precalculated_3y_abs=pre_3y_abs,
                precalculated_5y_abs=pre_5y_abs,
                rolling_stats=rolling_stats,
                rating=rating_breakdown.total_rating,
                rating_breakdown=rating_breakdown
            )

        processed_funds: List[FundResearchItem] = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            results = executor.map(process_fund, qualifying_raw_funds)
            for res in results:
                if res:
                    processed_funds.append(res)

        # Sort by rating descending (secondary by rolling mean)
        processed_funds.sort(key=lambda x: (x.rating, x.rolling_stats.mean), reverse=True)

        # Calculate category summary KPIs
        if processed_funds:
            avg_roll = round(sum(f.rolling_stats.mean for f in processed_funds) / len(processed_funds), 2)
            avg_ter = round(sum(f.expense_ratio for f in processed_funds) / len(processed_funds), 2)
            avg_aum = round(sum(f.aum for f in processed_funds) / len(processed_funds), 2)
            top_fund = processed_funds[0].fund_name
            top_rating = processed_funds[0].rating
        else:
            avg_roll = 0.0
            avg_ter = 0.0
            avg_aum = 0.0
            top_fund = "None"
            top_rating = 0.0

        summary_dict = {
            "total_funds_searched": len(all_schemes),
            "qualifying_funds_9y": len(processed_funds),
            "category_avg_rolling_mean": avg_roll,
            "category_avg_ter": avg_ter,
            "category_avg_aum": avg_aum,
            "category_top_rated_fund": top_fund,
            "category_top_rating": top_rating,
            "is_cached": False,
            "last_updated": now.strftime("%Y-%m-%d %H:%M")
        }

        # Cache to SQLite
        self.cache.save_subcategory_cache(subcategory_name, summary_dict, processed_funds)

        summary = CategorySummaryKPI(**summary_dict)
        return ResearchResponse(
            subcategory=subcategory_name,
            summary=summary,
            funds=processed_funds
        )
