import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DHAN_SEARCH_URL = "https://mf-openweb-search.dhan.co/SearchScript"
DHAN_CHART_URL = "https://mf-openweb-search.dhan.co/chart"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"

class DhanClient:
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.headers = {
            "user-agent": DEFAULT_USER_AGENT,
            "Content-Type": "application/json"
        }

    def search_funds_by_subcategory(self, subcategory_name: str, size: int = 1500) -> List[Dict[str, Any]]:
        """
        Fetches all mutual funds belonging to a specific subcategory (e.g. 'Flexi Cap Fund').
        Sorted by AUM descending.
        """
        payload = {
            "entity_id": "Dhanweb",
            "source": "W",
            "data": {
                "filedSearch": "",
                "search": "",
                "page": 0,
                "fieldSearchValue": "",
                "filter": {
                    "dmfm_subcategory_name": subcategory_name
                },
                "size": str(size),
                "sort": {
                    "dmfm_scheme_aum": "desc"
                },
                "tags_needed": ""
            }
        }
        try:
            response = self.session.post(DHAN_SEARCH_URL, json=payload, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            res_json = response.json()
            return res_json.get("data", []) or []
        except Exception as e:
            logger.error(f"Error fetching funds for subcategory '{subcategory_name}': {e}")
            raise

    def get_all_subcategories(self) -> List[str]:
        """
        Fetches unique subcategory names available in Dhan.
        """
        payload = {
            "entity_id": "Dhanweb",
            "source": "W",
            "data": {
                "filedSearch": "",
                "search": "",
                "page": 0,
                "fieldSearchValue": "",
                "filter": {},
                "size": "1500",
                "sort": {
                    "dmfm_scheme_aum": "desc"
                },
                "tags_needed": ""
            }
        }
        try:
            response = self.session.post(DHAN_SEARCH_URL, json=payload, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            items = response.json().get("data", []) or []
            subs = sorted(list(set(f.get("dmfm_subcategory_name") for f in items if f.get("dmfm_subcategory_name"))))
            return subs
        except Exception as e:
            logger.error(f"Error fetching subcategories: {e}")
            # Fallback list of popular categories
            return [
                "Flexi Cap Fund",
                "Large Cap Fund",
                "Mid Cap Fund",
                "Small Cap Fund",
                "Large & Mid Cap Fund",
                "Multi Cap Fund",
                "Focused Fund",
                "ELSS - Tax Saver Fund",
                "Value Fund",
                "Contra Fund",
                "Aggressive Hybrid Fund",
                "Dynamic Asset Allocation Fund or Balanced Advantage Fund"
            ]

    def fetch_nav_chart(self, scode: str, start_date: str = "2015-01-01", end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches historical daily NAV data for a scheme code (sCode).
        Returns dict with dates ('d') and NAV values ('n').
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        payload = {
            "entity_id": "Openweb",
            "source": "W",
            "data": {
                "client_id": "",
                "sCode": str(scode),
                "period": "",
                "start_date": start_date,
                "end_date": end_date
            },
            "aes_key": "",
            "ip": ""
        }
        try:
            response = self.session.post(DHAN_CHART_URL, json=payload, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            res_json = response.json()
            data_arr = res_json.get("data", [])
            if data_arr and len(data_arr) > 0:
                return {
                    "dates": data_arr[0].get("d", []),
                    "navs": data_arr[0].get("n", []),
                    "diff": data_arr[0].get("diff", []),
                    "cgpa": data_arr[0].get("cgpa", [])
                }
            return {"dates": [], "navs": []}
        except Exception as e:
            logger.warning(f"Error fetching chart for sCode {scode}: {e}")
            return {"dates": [], "navs": []}
