from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RollingReturnPoint(BaseModel):
    date: str
    hist_date: str
    cagr: float

class RollingStats(BaseModel):
    mean: float = Field(..., description="Average 5-year rolling return CAGR (%)")
    median: float = Field(..., description="Median 5-year rolling return CAGR (%)")
    min_return: float = Field(..., description="Worst 5-year rolling return period CAGR (%)")
    max_return: float = Field(..., description="Best 5-year rolling return period CAGR (%)")
    std_dev: float = Field(..., description="Standard deviation / volatility of rolling returns (%)")
    prob_above_10: float = Field(..., description="Percentage of rolling periods with CAGR > 10%")
    prob_above_12: float = Field(..., description="Percentage of rolling periods with CAGR > 12%")
    prob_above_15: float = Field(..., description="Percentage of rolling periods with CAGR > 15%")
    prob_negative: float = Field(..., description="Percentage of rolling periods with negative CAGR (%)")
    observation_count: int = Field(..., description="Total number of 5Y rolling return windows")
    rolling_series: Optional[List[RollingReturnPoint]] = None

class RatingBreakdown(BaseModel):
    rolling_return_score: float = Field(..., description="Score from 5Y rolling mean CAGR (out of 3.5)")
    expense_ratio_score: float = Field(..., description="Score from expense ratio / TER (out of 2.0)")
    consistency_score: float = Field(..., description="Score from consistency and std dev (out of 1.5)")
    aum_score: float = Field(..., description="Score from fund size and scale stability (out of 1.0)")
    historical_return_score: float = Field(..., description="Score from precalculated 5Y trailing return (out of 2.0)")
    total_rating: float = Field(..., description="Final overall composite rating out of 10")
    rating_label: str = Field(..., description="E.g. Exceptional, Excellent, Good, Average, Weak")

class FundResearchItem(BaseModel):
    scode: str
    fund_name: str
    amc_name: str
    subcategory_name: str
    inception_date: str
    age_years: float
    aum: float
    expense_ratio: float
    min_sip_amount: float
    benchmark: Optional[str] = "N/A"
    fund_manager: Optional[str] = "N/A"
    risk_level: Optional[str] = "N/A"
    exit_load: Optional[str] = "N/A"
    latest_nav: Optional[float] = None
    latest_nav_date: Optional[str] = None
    
    # Precalculated returns from Dhan API
    precalculated_1m: Optional[float] = None
    precalculated_3m: Optional[float] = None
    precalculated_6m: Optional[float] = None
    precalculated_1y: Optional[float] = None
    precalculated_3y: Optional[float] = None
    precalculated_5y: Optional[float] = None
    precalculated_3y_abs: Optional[float] = None
    precalculated_5y_abs: Optional[float] = None
    
    # Computed 5-year rolling returns stats
    rolling_stats: RollingStats
    
    # Rating & Breakdown
    rating: float
    rating_breakdown: RatingBreakdown

class CategorySummaryKPI(BaseModel):
    total_funds_searched: int
    qualifying_funds_9y: int
    category_avg_rolling_mean: float
    category_avg_ter: float
    category_avg_aum: float
    category_top_rated_fund: str
    category_top_rating: float
    is_cached: bool
    last_updated: str

class ResearchResponse(BaseModel):
    subcategory: str
    summary: CategorySummaryKPI
    funds: List[FundResearchItem]
