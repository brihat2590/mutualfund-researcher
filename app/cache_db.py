import sqlite3
import json
import os
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from app.models import FundResearchItem, RollingStats, RatingBreakdown, RollingReturnPoint
import logging

logger = logging.getLogger(__name__)


def _default_db_path() -> str:
    # Allow explicit override, otherwise use the writable /tmp dir on Vercel
    # (the project filesystem is read-only in serverless functions).
    override = os.environ.get("CACHE_DB_PATH")
    if override:
        return override
    if os.environ.get("VERCEL"):
        return "/tmp/mutual_fund_cache.db"
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mutual_fund_cache.db")


DB_PATH = _default_db_path()

class CacheDB:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subcategory_cache (
                    subcategory_name TEXT PRIMARY KEY,
                    updated_at TEXT,
                    fund_count INTEGER,
                    summary_json TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS funds_cache (
                    scode TEXT PRIMARY KEY,
                    subcategory_name TEXT,
                    fund_name TEXT,
                    amc_name TEXT,
                    inception_date TEXT,
                    age_years REAL,
                    aum REAL,
                    expense_ratio REAL,
                    min_sip_amount REAL,
                    benchmark TEXT,
                    fund_manager TEXT,
                    risk_level TEXT,
                    exit_load TEXT,
                    latest_nav REAL,
                    latest_nav_date TEXT,
                    precalculated_1m REAL,
                    precalculated_3m REAL,
                    precalculated_6m REAL,
                    precalculated_1y REAL,
                    precalculated_3y REAL,
                    precalculated_5y REAL,
                    precalculated_3y_abs REAL,
                    precalculated_5y_abs REAL,
                    roll_mean REAL,
                    roll_median REAL,
                    roll_min REAL,
                    roll_max REAL,
                    roll_std REAL,
                    prob_above_10 REAL,
                    prob_above_12 REAL,
                    prob_above_15 REAL,
                    prob_negative REAL,
                    observation_count INTEGER,
                    rating REAL,
                    rating_breakdown_json TEXT,
                    rolling_series_json TEXT,
                    updated_at TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_funds_subcategory ON funds_cache (subcategory_name);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_funds_rating ON funds_cache (rating DESC);
            """)
            conn.commit()

    def get_subcategory_cache(self, subcategory_name: str, max_age_hours: int = 48) -> Optional[Tuple[Dict[str, Any], List[FundResearchItem]]]:
        """
        Retrieves cached funds for subcategory if present and within max_age_hours.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT updated_at, summary_json FROM subcategory_cache WHERE subcategory_name = ?",
                    (subcategory_name,)
                )
                row = cursor.fetchone()
                if not row:
                    return None

                updated_at_str = row["updated_at"]
                updated_at = datetime.fromisoformat(updated_at_str)
                if (datetime.now() - updated_at).total_seconds() > max_age_hours * 3600:
                    return None # Cache expired

                summary_json = json.loads(row["summary_json"]) if row["summary_json"] else {}

                cursor.execute(
                    "SELECT * FROM funds_cache WHERE subcategory_name = ? ORDER BY rating DESC",
                    (subcategory_name,)
                )
                fund_rows = cursor.fetchall()
                if not fund_rows:
                    return None

                funds: List[FundResearchItem] = []
                for fr in fund_rows:
                    series = []
                    if fr["rolling_series_json"]:
                        try:
                            s_data = json.loads(fr["rolling_series_json"])
                            series = [RollingReturnPoint(**pt) for pt in s_data]
                        except:
                            series = []

                    rolling_stats = RollingStats(
                        mean=fr["roll_mean"],
                        median=fr["roll_median"],
                        min_return=fr["roll_min"],
                        max_return=fr["roll_max"],
                        std_dev=fr["roll_std"],
                        prob_above_10=fr["prob_above_10"],
                        prob_above_12=fr["prob_above_12"],
                        prob_above_15=fr["prob_above_15"],
                        prob_negative=fr["prob_negative"],
                        observation_count=fr["observation_count"],
                        rolling_series=series
                    )

                    rb = json.loads(fr["rating_breakdown_json"]) if fr["rating_breakdown_json"] else {}
                    rating_breakdown = RatingBreakdown(**rb)

                    item = FundResearchItem(
                        scode=fr["scode"],
                        fund_name=fr["fund_name"],
                        amc_name=fr["amc_name"],
                        subcategory_name=fr["subcategory_name"],
                        inception_date=fr["inception_date"],
                        age_years=fr["age_years"],
                        aum=fr["aum"],
                        expense_ratio=fr["expense_ratio"],
                        min_sip_amount=fr["min_sip_amount"],
                        benchmark=fr["benchmark"],
                        fund_manager=fr["fund_manager"],
                        risk_level=fr["risk_level"],
                        exit_load=fr["exit_load"],
                        latest_nav=fr["latest_nav"],
                        latest_nav_date=fr["latest_nav_date"],
                        precalculated_1m=fr["precalculated_1m"],
                        precalculated_3m=fr["precalculated_3m"],
                        precalculated_6m=fr["precalculated_6m"],
                        precalculated_1y=fr["precalculated_1y"],
                        precalculated_3y=fr["precalculated_3y"],
                        precalculated_5y=fr["precalculated_5y"],
                        precalculated_3y_abs=fr["precalculated_3y_abs"],
                        precalculated_5y_abs=fr["precalculated_5y_abs"],
                        rolling_stats=rolling_stats,
                        rating=fr["rating"],
                        rating_breakdown=rating_breakdown
                    )
                    funds.append(item)

                return summary_json, funds
        except Exception as e:
            logger.error(f"Error reading cache for '{subcategory_name}': {e}")
            return None

    def save_subcategory_cache(self, subcategory_name: str, summary: Dict[str, Any], funds: List[FundResearchItem]):
        """
        Saves computed research results for a subcategory into the SQLite cache.
        """
        now_str = datetime.now().isoformat()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO subcategory_cache
                    (subcategory_name, updated_at, fund_count, summary_json)
                    VALUES (?, ?, ?, ?)
                """, (subcategory_name, now_str, len(funds), json.dumps(summary)))

                for f in funds:
                    series_json = json.dumps([p.dict() for p in (f.rolling_stats.rolling_series or [])])
                    rb_json = json.dumps(f.rating_breakdown.dict())

                    cursor.execute("""
                        INSERT OR REPLACE INTO funds_cache (
                            scode, subcategory_name, fund_name, amc_name, inception_date, age_years,
                            aum, expense_ratio, min_sip_amount, benchmark, fund_manager, risk_level,
                            exit_load, latest_nav, latest_nav_date,
                            precalculated_1m, precalculated_3m, precalculated_6m, precalculated_1y,
                            precalculated_3y, precalculated_5y, precalculated_3y_abs, precalculated_5y_abs,
                            roll_mean, roll_median, roll_min, roll_max, roll_std,
                            prob_above_10, prob_above_12, prob_above_15, prob_negative,
                            observation_count, rating, rating_breakdown_json, rolling_series_json, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        f.scode, f.subcategory_name, f.fund_name, f.amc_name, f.inception_date, f.age_years,
                        f.aum, f.expense_ratio, f.min_sip_amount, f.benchmark, f.fund_manager, f.risk_level,
                        f.exit_load, f.latest_nav, f.latest_nav_date,
                        f.precalculated_1m, f.precalculated_3m, f.precalculated_6m, f.precalculated_1y,
                        f.precalculated_3y, f.precalculated_5y, f.precalculated_3y_abs, f.precalculated_5y_abs,
                        f.rolling_stats.mean, f.rolling_stats.median, f.rolling_stats.min_return, f.rolling_stats.max_return, f.rolling_stats.std_dev,
                        f.rolling_stats.prob_above_10, f.rolling_stats.prob_above_12, f.rolling_stats.prob_above_15, f.rolling_stats.prob_negative,
                        f.rolling_stats.observation_count, f.rating, rb_json, series_json, now_str
                    ))
                conn.commit()
                logger.info(f"Cached {len(funds)} funds for subcategory '{subcategory_name}'")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def get_fund_by_scode(self, scode: str) -> Optional[FundResearchItem]:
        """
        Retrieves a single fund with its full rolling series and breakdown for the modal.
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM funds_cache WHERE scode = ?", (scode,))
                fr = cursor.fetchone()
                if not fr:
                    return None

                series = []
                if fr["rolling_series_json"]:
                    try:
                        s_data = json.loads(fr["rolling_series_json"])
                        series = [RollingReturnPoint(**pt) for pt in s_data]
                    except:
                        series = []

                rolling_stats = RollingStats(
                    mean=fr["roll_mean"],
                    median=fr["roll_median"],
                    min_return=fr["roll_min"],
                    max_return=fr["roll_max"],
                    std_dev=fr["roll_std"],
                    prob_above_10=fr["prob_above_10"],
                    prob_above_12=fr["prob_above_12"],
                    prob_above_15=fr["prob_above_15"],
                    prob_negative=fr["prob_negative"],
                    observation_count=fr["observation_count"],
                    rolling_series=series
                )

                rb = json.loads(fr["rating_breakdown_json"]) if fr["rating_breakdown_json"] else {}
                rating_breakdown = RatingBreakdown(**rb)

                return FundResearchItem(
                    scode=fr["scode"],
                    fund_name=fr["fund_name"],
                    amc_name=fr["amc_name"],
                    subcategory_name=fr["subcategory_name"],
                    inception_date=fr["inception_date"],
                    age_years=fr["age_years"],
                    aum=fr["aum"],
                    expense_ratio=fr["expense_ratio"],
                    min_sip_amount=fr["min_sip_amount"],
                    benchmark=fr["benchmark"],
                    fund_manager=fr["fund_manager"],
                    risk_level=fr["risk_level"],
                    exit_load=fr["exit_load"],
                    latest_nav=fr["latest_nav"],
                    latest_nav_date=fr["latest_nav_date"],
                    precalculated_1m=fr["precalculated_1m"],
                    precalculated_3m=fr["precalculated_3m"],
                    precalculated_6m=fr["precalculated_6m"],
                    precalculated_1y=fr["precalculated_1y"],
                    precalculated_3y=fr["precalculated_3y"],
                    precalculated_5y=fr["precalculated_5y"],
                    precalculated_3y_abs=fr["precalculated_3y_abs"],
                    precalculated_5y_abs=fr["precalculated_5y_abs"],
                    rolling_stats=rolling_stats,
                    rating=fr["rating"],
                    rating_breakdown=rating_breakdown
                )
        except Exception as e:
            logger.error(f"Error fetching fund {scode}: {e}")
            return None

    def clear_cache(self, subcategory_name: Optional[str] = None):
        """
        Clears cache for a specific subcategory or all cache.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if subcategory_name:
                cursor.execute("DELETE FROM subcategory_cache WHERE subcategory_name = ?", (subcategory_name,))
                cursor.execute("DELETE FROM funds_cache WHERE subcategory_name = ?", (subcategory_name,))
            else:
                cursor.execute("DELETE FROM subcategory_cache")
                cursor.execute("DELETE FROM funds_cache")
            conn.commit()
