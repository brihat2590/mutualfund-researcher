import os
import logging
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from app.researcher import MutualFundResearcher
from app.cache_db import CacheDB
from app.dhan_client import DhanClient
from app.models import ResearchResponse, FundResearchItem

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mf_researcher")

app = FastAPI(
    title="Mutual Fund Research & 5-Year Rolling Return Screener",
    description="Professional mutual fund researcher analyzing funds >= 9 years old using 5-year rolling returns, TER, and AUM.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    try:
        os.makedirs(STATIC_DIR, exist_ok=True)
    except OSError:
        # Read-only filesystem (e.g. Vercel serverless); static assets are bundled.
        pass

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

researcher = MutualFundResearcher()

@app.get("/tokens.css", include_in_schema=False)
def get_design_tokens():
    return FileResponse(os.path.join(BASE_DIR, "tokens.css"), media_type="text/css")

class ResearchRequest(BaseModel):
    subcategory: str = "Flexi Cap Fund"
    force_refresh: bool = False

@app.get("/")
def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(
            index_path,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
    return {"message": "Mutual Fund Researcher API is running. index.html not yet found."}

@app.get("/api/subcategories")
def get_subcategories():
    try:
        subs = researcher.client.get_all_subcategories()
        return {"subcategories": subs}
    except Exception as e:
        logger.error(f"Error fetching subcategories: {e}")
        return {"subcategories": ["Flexi Cap Fund", "Large Cap Fund", "Mid Cap Fund", "Small Cap Fund", "ELSS - Tax Saver Fund"]}

@app.post("/api/research", response_model=ResearchResponse)
def research_funds(req: ResearchRequest):
    try:
        subcategory = req.subcategory.strip()
        if not subcategory:
            subcategory = "Flexi Cap Fund"
        res = researcher.research_category(subcategory, force_refresh=req.force_refresh)
        return res
    except Exception as e:
        logger.exception("Error processing research request")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fund/{scode}", response_model=FundResearchItem)
def get_fund_detail(scode: str):
    fund = researcher.cache.get_fund_by_scode(scode)
    if not fund:
        raise HTTPException(status_code=404, detail=f"Fund with sCode {scode} not found in cache. Please run research for its category first.")
    return fund

@app.post("/api/clear-cache")
def clear_cache(subcategory: Optional[str] = Body(None, embed=True)):
    researcher.cache.clear_cache(subcategory)
    return {"status": "success", "message": f"Cache cleared for '{subcategory}'" if subcategory else "All cache cleared"}
