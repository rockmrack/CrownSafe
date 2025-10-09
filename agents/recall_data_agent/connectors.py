import os
import logging
import asyncio
import ssl
from datetime import datetime, timedelta
from typing import List, Optional
import hashlib
import re

import aiohttp
from dotenv import load_dotenv

from .models import Recall

# Try to import feedparser for RSS parsing
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logging.warning("feedparser not installed. USDA FSIS RSS parsing will fail. Install with: pip install feedparser")

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)

# Create SSL context for connections
def create_ssl_context():
    """Create SSL context for HTTPS connections"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

# ------------------------------------------------------------------------------
# CPSC Connector (no API key required) - OPTIMIZED WITH DATE FILTERING
# ------------------------------------------------------------------------------
class CPSCConnector:
    """
    Fetches recall data from CPSC SaferProducts.gov REST API.
    No API key required - fully open public API.
    Uses documented date filtering to get recent recalls only.
    """
    BASE_URL = "https://www.saferproducts.gov/RestWebServices/Recall"

    async def fetch_recent_recalls(self) -> List[Recall]:
        logger.info("Fetching recent recalls from CPSC...")
        recalls: List[Recall] = []
        
        # Use documented date filtering (not RecallNumberStartYear)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = "2015-01-01"  # Get recalls from 2015 onwards
        
        params = {
            "format": "json",
            "RecallDateStart": start_date,
            "RecallDateEnd": end_date
        }
        
        try:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.BASE_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    
                    logger.info(f"CPSC API returned {len(data)} recalls with date filtering")
                    
                    for item in data:
                        try:
                            # Parse date safely
                            date_str = item.get("RecallDate", "")
                            recall_date = None
                            if date_str:
                                try:
                                    date_str = date_str.split("T")[0]
                                    recall_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                except ValueError:
                                    logger.warning(f"Could not parse date: {date_str}")

                            # Get product name safely
                            products = item.get("Products", [])
                            product_name = "N/A"
                            if products and isinstance(products, list) and products[0]:
                                product_name = products[0].get("Name", "N/A") or "N/A"

                            # Get hazard safely
                            hazards = item.get("Hazards", [])
                            hazard = "N/A"
                            if hazards and isinstance(hazards, list) and hazards[0]:
                                hazard = hazards[0].get("Name", "N/A") or "N/A"

                            # Get URL safely
                            url = item.get("URL", "") or ""

                            # Create recall ID
                            recall_id = f"CPSC-{item.get('RecallID', 'unknown')}"

                            recall = Recall(
                                recall_id=recall_id,
                                source_agency="CPSC",
                                recall_date=recall_date,
                                product_name=product_name,
                                description=product_name,
                                hazard=hazard,
                                remedy=None,
                                url=url if url else None,
                                product_upcs=[]
                            )
                            recalls.append(recall)
                            logger.debug(f"Added CPSC recall: {recall_id}")
                            
                        except Exception as e:
                            logger.error(f"Error processing CPSC recall item: {e}")
                            continue

        except Exception as e:
            logger.error(f"Error fetching CPSC recalls: {e}", exc_info=True)
        
        logger.info(f"Successfully fetched {len(recalls)} CPSC recalls")
        return recalls

# ------------------------------------------------------------------------------
# NHTSA Connector (no API key required) - FIXED WITH CORRECT RESOURCE ID
# ------------------------------------------------------------------------------
class NHTSAConnector:
    """
    Fetches child car seat recall data from NHTSA via official Socrata dataset.
    Uses the correct resource ID (6axg-epim) for NHTSA recalls data.
    """
    SOCRATA_BASE_URL = "https://data.transportation.gov/resource"
    RESOURCE_ID = "6axg-epim"  # Correct NHTSA recalls dataset resource ID

    async def fetch_recent_recalls(self) -> List[Recall]:
        logger.info("Fetching recent child seat recalls from NHTSA via official Socrata dataset...")
        recalls: List[Recall] = []
        
        try:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            # Build the correct Socrata API URL with resource ID
            api_url = f"{self.SOCRATA_BASE_URL}/{self.RESOURCE_ID}.json"
            
            # SoQL parameters for child seat recalls since 2015
            params = {
                "$where": "recall_type='Child Seat' AND report_received_date >= '2015-01-01'",
                "$limit": 50000,
                "$order": "report_received_date DESC"
            }
            
            # Add Socrata app token if available (optional but recommended)
            socrata_token = os.getenv("SOCRATA_APP_TOKEN")
            if socrata_token:
                params["$$app_token"] = socrata_token
            
            logger.info(f"Requesting NHTSA child seat data from: {api_url}")
            
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(api_url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    
                    logger.info(f"Found {len(data)} NHTSA child seat records from official dataset")
                    
                    for item in data:
                        try:
                            # Parse date safely
                            date_str = item.get("report_received_date", "")
                            recall_date = None
                            if date_str:
                                try:
                                    # Handle Socrata date format
                                    if "T" in date_str:
                                        date_str = date_str.split("T")[0]
                                    recall_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                except ValueError:
                                    logger.warning(f"Could not parse NHTSA date: {date_str}")

                            # Build product name
                            manufacturer = item.get("manufacturer", "").strip()
                            model = item.get("model", "").strip()
                            
                            if manufacturer and model:
                                product_name = f"{manufacturer} {model}"
                            elif manufacturer:
                                product_name = f"{manufacturer} Child Car Seat"
                            else:
                                product_name = "Child Car Seat"
                            
                            if len(product_name) > 500:
                                product_name = product_name[:497] + "..."

                            # Get hazard/description
                            hazard = item.get("defect_summary", "Child seat safety issue") or "Child seat safety issue"
                            if len(hazard) > 500:
                                hazard = hazard[:497] + "..."

                            # Create recall ID
                            recall_number = item.get("recall_number", "unknown")
                            recall_id = f"NHTSA-{recall_number}"

                            # Create URL
                            if recall_number != "unknown":
                                url = f"https://www.nhtsa.gov/recalls?nhtsaId={recall_number}"
                            else:
                                url = None

                            # Get description
                            description = item.get("component_description", hazard)
                            if len(description) > 500:
                                description = description[:497] + "..."

                            recall = Recall(
                                recall_id=recall_id,
                                source_agency="NHTSA",
                                recall_date=recall_date,
                                product_name=product_name,
                                description=description,
                                hazard=hazard,
                                remedy="See NHTSA notice for remedy details",
                                url=url,
                                product_upcs=[]
                            )
                            recalls.append(recall)
                            logger.debug(f"Added NHTSA recall: {recall_id}")
                            
                        except Exception as e:
                            logger.error(f"Error processing NHTSA recall item: {e}")
                            continue

        except Exception as e:
            logger.error(f"Error fetching NHTSA recalls: {e}", exc_info=True)
        
        logger.info(f"Successfully fetched {len(recalls)} NHTSA recalls")
        return recalls

# ------------------------------------------------------------------------------
# FDA Connector (API key required) - Food, Cosmetics & Medical Devices
# ------------------------------------------------------------------------------
class FDAConnector:
    """
    Fetches recall data from FDA openFDA API.
    Requires free API key from api.data.gov.
    """
    FOOD_URL = "https://api.fda.gov/food/enforcement.json"
    DEVICE_URL = "https://api.fda.gov/device/enforcement.json"
    API_KEY = os.getenv("FDA_API_KEY")

    async def fetch_recent_recalls(self) -> List[Recall]:
        if not self.API_KEY:
            logger.warning("FDA_API_KEY not set; skipping FDA recalls.")
            return []

        logger.info("Fetching recent recalls from FDA...")
        recalls: List[Recall] = []

        try:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                
                # Fetch from both food/cosmetics and device endpoints
                endpoints = [
                    ("Food/Cosmetics", self.FOOD_URL),
                    ("Medical Devices", self.DEVICE_URL)
                ]
                
                for endpoint_name, url in endpoints:
                    try:
                        params = {"api_key": self.API_KEY, "limit": 25}
                        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                            resp.raise_for_status()
                            payload = await resp.json()
                            results = payload.get("results", [])
                            
                            logger.info(f"Found {len(results)} {endpoint_name} recalls from FDA")
                            
                            for item in results:
                                try:
                                    # Parse date safely
                                    date_str = item.get("recall_initiation_date", "")
                                    recall_date = None
                                    if date_str:
                                        try:
                                            recall_date = datetime.strptime(date_str, "%Y%m%d").date()
                                        except ValueError:
                                            logger.warning(f"Could not parse FDA date: {date_str}")

                                    # Get data safely
                                    product_name = item.get("product_description", "N/A") or "N/A"
                                    hazard = item.get("reason_for_recall", "N/A") or "N/A"
                                    recall_number = item.get('recall_number', 'unknown') or 'unknown'
                                    
                                    # Truncate long descriptions
                                    if len(product_name) > 500:
                                        product_name = product_name[:497] + "..."
                                    if len(hazard) > 500:
                                        hazard = hazard[:497] + "..."

                                    recall_id = f"FDA-{recall_number}"
                                    remedy = "Check FDA site for remedy details"
                                    url = f"https://api.fda.gov/food/enforcement.json?search=recall_number:\"{recall_number}\""

                                    recall = Recall(
                                        recall_id=recall_id,
                                        source_agency="FDA",
                                        recall_date=recall_date,
                                        product_name=product_name,
                                        description=product_name,
                                        hazard=hazard,
                                        remedy=remedy,
                                        url=url,
                                        product_upcs=[]
                                    )
                                    recalls.append(recall)
                                    logger.debug(f"Added FDA recall: {recall_id}")
                                    
                                except Exception as e:
                                    logger.error(f"Error processing FDA recall item: {e}")
                                    continue
                                    
                    except Exception as e:
                        logger.error(f"Error fetching FDA {endpoint_name} recalls: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error fetching FDA recalls: {e}", exc_info=True)

        logger.info(f"Successfully fetched {len(recalls)} FDA recalls")
        return recalls

# ------------------------------------------------------------------------------
# USDA FSIS Connector - GRACEFUL FALLBACK VERSION
# ------------------------------------------------------------------------------
class USDAFSISConnector:
    """
    USDA FSIS connector using the working RSS feed.
    FSIS handles meat, poultry, and egg products (not consumer goods like car seats).
    Uses the official RSS feed that consistently delivers all FSIS recall notices.
    """
    RSS_URL = "https://www.fsis.usda.gov/RSS/usdarss.xml"
    
    # Baby-related keywords for filtering
    BABY_KEYWORDS = [
        "baby", "infant", "formula", "pediatric", "child", 
        "toddler", "gerber", "similac", "enfamil", "beech-nut",
        "earth's best", "happy baby", "plum organics", "nursery"
    ]
    
    # Control flag
    ENABLE_CONNECTOR = True

    async def fetch_recent_recalls(self) -> List[Recall]:
        if not self.ENABLE_CONNECTOR:
            logger.info("USDA FSIS - Connector disabled")
            return []

        logger.info("USDA FSIS - Attempting to fetch recalls...")
        
        # Try RSS feed with shorter timeout
        if FEEDPARSER_AVAILABLE:
            try:
                recalls = await self._fetch_from_rss()
                if recalls:
                    return recalls
            except Exception as e:
                logger.warning(f"USDA FSIS - RSS feed failed: {e}")
        
        # If RSS fails, return a status message
        logger.warning("USDA FSIS - All data sources unavailable, returning status notice")
        return self._get_status_notice()

    async def _fetch_from_rss(self) -> List[Recall]:
        """Try to fetch from RSS with shorter timeout"""
        recalls = []
        
        ssl_context = create_ssl_context()
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        }
        
        # Use shorter timeout to fail faster
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                self.RSS_URL, 
                headers=headers,
                timeout=timeout
            ) as resp:
                resp.raise_for_status()
                rss_content = await resp.text()
                
                # Parse RSS
                feed = feedparser.parse(rss_content)
                
                for entry in feed.entries[:20]:  # Limit to recent 20
                    try:
                        title = entry.get("title", "").strip()
                        if not title:
                            continue
                        
                        recall_date = None
                        if hasattr(entry, 'published_parsed'):
                            try:
                                recall_date = datetime(*entry.published_parsed[:6]).date()
                            except:
                                pass
                        
                        link = entry.get("link", "")
                        description = entry.get("summary", "") or title
                        
                        # Clean HTML
                        if '<' in description:
                            description = re.sub('<[^<]+?>', '', description).strip()
                        
                        # Check if baby-related
                        search_text = (title + " " + description).lower()
                        is_baby_related = any(kw in search_text for kw in self.BABY_KEYWORDS)
                        
                        product_name = title
                        if is_baby_related:
                            product_name = f"[BABY PRODUCT] {title[:480]}"
                        
                        recall_id = f"FSIS-{abs(hash(title)) % 1000000}"
                        
                        recall = Recall(
                            recall_id=recall_id,
                            source_agency="USDA FSIS",
                            recall_date=recall_date,
                            product_name=product_name[:500],
                            description=description[:500],
                            hazard="Food Safety Issue",
                            remedy="See FSIS notice",
                            url=link or "https://www.fsis.usda.gov/recalls-alerts",
                            product_upcs=[]
                        )
                        recalls.append(recall)
                        
                    except Exception as e:
                        logger.error(f"USDA FSIS - Error parsing entry: {e}")
                        continue
                
                logger.info(f"USDA FSIS - Fetched {len(recalls)} recalls from RSS")
                return recalls

    def _get_status_notice(self) -> List[Recall]:
        """Return a status notice when all sources fail"""
        return [
            Recall(
                recall_id="USDA-STATUS-001",
                source_agency="USDA FSIS",
                recall_date=datetime.now().date(),
                product_name="USDA FSIS Data Currently Unavailable",
                description=(
                    "USDA FSIS recall data sources are temporarily unavailable. "
                    "This may affect baby food and meat product recall coverage. "
                    "Please check https://www.fsis.usda.gov/recalls-alerts directly for the latest information."
                ),
                hazard="Service Notice",
                remedy="Visit USDA FSIS website for current recalls",
                url="https://www.fsis.usda.gov/recalls-alerts",
                product_upcs=[]
            )
        ]

# ------------------------------------------------------------------------------
# EU RAPEX/Safety Gate Connector (via Opendatasoft public API) - CORRECTED
# ------------------------------------------------------------------------------
class EURapexConnector:
    """
    Fetches EU Safety Gate (RAPEX) data via Opendatasoft public mirror.
    No API key required.
    """
    ENDPOINT = "https://public.opendatasoft.com/api/records/1.0/search/"
    DATASET = "healthref-europe-rapex-en"

    async def fetch_recent_recalls(self, limit: int = 50) -> List[Recall]:
        logger.info("Fetching recent recalls from EU RAPEX (public mirror)...")
        recalls: List[Recall] = []
        params = {
            "dataset": self.DATASET,
            "rows": limit,
            "sort": "-alert_date"
        }

        try:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.ENDPOINT, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()
                    records = payload.get("records", [])

                    for rec in records:
                        try:
                            fields = rec.get("fields", {})
                            
                            # Parse alert date safely
                            date_str = fields.get("alert_date", "")
                            recall_date = None
                            if date_str:
                                try:
                                    recall_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                except ValueError:
                                    logger.warning(f"Could not parse RAPEX date: {date_str}")

                            # Get data safely - try multiple field variations
                            product_name = (fields.get("product") or 
                                          fields.get("product_name") or 
                                          fields.get("product_description") or 
                                          fields.get("name") or "Unknown Product")
                            
                            hazard = (fields.get("risk_type") or 
                                    fields.get("hazard") or 
                                    fields.get("risk") or 
                                    fields.get("danger") or "Safety Risk")
                            
                            alert_number = (fields.get('alert_number') or 
                                          fields.get('number') or 
                                          fields.get('id') or 'unknown')
                            
                            # Truncate long descriptions
                            if len(product_name) > 500:
                                product_name = product_name[:497] + "..."
                            if len(hazard) > 500:
                                hazard = hazard[:497] + "..."

                            recall_id = f"RAPEX-{alert_number}"
                            
                            # Try to get proper URL
                            url = (fields.get("link") or 
                                  fields.get("url") or 
                                  f"https://public.opendatasoft.com/explore/dataset/{self.DATASET}/")
                            
                            remedy = "See EU Safety Gate for remedy details"

                            recall = Recall(
                                recall_id=recall_id,
                                source_agency="EU RAPEX",
                                recall_date=recall_date,
                                product_name=product_name,
                                description=product_name,
                                hazard=hazard,
                                remedy=remedy,
                                url=url if url else None,
                                product_upcs=[]
                            )
                            recalls.append(recall)
                            logger.debug(f"Added RAPEX recall: {recall_id}")
                            
                        except Exception as e:
                            logger.error(f"Error processing RAPEX recall item: {e}")
                            continue

        except Exception as e:
            logger.error(f"Error fetching EU RAPEX recalls: {e}", exc_info=True)
        
        logger.info(f"Successfully fetched {len(recalls)} EU RAPEX recalls")
        return recalls

# ------------------------------------------------------------------------------
# UK OPSS Connector (via GOV.UK Search API)
# ------------------------------------------------------------------------------
class UKOPSSConnector:
    """
    Fetches UK OPSS safety alerts via GOV.UK Search API.
    No API key required - uses Open Government License data.
    """
    SEARCH_URL = "https://www.gov.uk/api/search.json"

    async def fetch_recent_recalls(self, limit: int = 50) -> List[Recall]:
        logger.info("Fetching recent recalls from UK OPSS...")
        recalls: List[Recall] = []

        try:
            # Search for product safety alerts and recalls
            params = {
                "filter_organisations": "office-for-product-safety-and-standards",
                "filter_content_purpose_supergroup": "guidance_and_regulation",
                "count": limit,
                "order": "-public_timestamp"
            }

            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.SEARCH_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

            # Process search results
            results = data.get("results", [])
            logger.info(f"Found {len(results)} UK OPSS documents via search API")

            for result in results[:limit]:
                try:
                    # Filter for safety-related content
                    title = result.get("title", "").lower()
                    if not any(keyword in title for keyword in ["safety", "recall", "alert", "hazard", "risk"]):
                        continue

                    # Parse date
                    ds = result.get("public_timestamp", "")
                    recall_date = None
                    if ds:
                        try:
                            recall_date = datetime.strptime(ds[:10], "%Y-%m-%d").date()
                        except Exception as e:
                            logger.warning(f"Could not parse UK OPSS date: {ds} - {e}")

                    product_name = result.get("title", "N/A") or "N/A"
                    if len(product_name) > 500:
                        product_name = product_name[:497] + "..."

                    description = result.get("description", product_name)
                    if len(description) > 500:
                        description = description[:497] + "..."

                    hazard = "Safety Alert"  # Generic hazard type for OPSS alerts
                    remedy = "See UK OPSS notice for remedy details"
                    
                    # Create ID from link
                    link = result.get("link", "")
                    link_parts = link.split("/")
                    short_id = link_parts[-1][:8] if link_parts else "unknown"
                    recall_id = f"UKOPSS-{short_id}"

                    url = f"https://www.gov.uk{link}" if link else None

                    recall = Recall(
                        recall_id=recall_id,
                        source_agency="UK OPSS",
                        recall_date=recall_date,
                        product_name=product_name,
                        description=description,
                        hazard=hazard,
                        remedy=remedy,
                        url=url,
                        product_upcs=[]
                    )
                    recalls.append(recall)
                    logger.debug(f"Added UK OPSS recall: {recall_id}")

                except Exception as e:
                    logger.error(f"Error processing UK OPSS recall item: {e}")
                    continue

                if len(recalls) >= limit:
                    break

        except Exception as e:
            logger.error(f"Error fetching UK OPSS recalls: {e}", exc_info=True)

        logger.info(f"Successfully fetched {len(recalls)} UK OPSS recalls")
        return recalls

# ------------------------------------------------------------------------------
# Singapore CPSO Connector (placeholder)
# ------------------------------------------------------------------------------
class SGCPSOConnector:
    async def fetch_recent_recalls(self) -> List[Recall]:
        logger.info("SGCPSOConnector placeholder – no implementation yet.")
        return []

# ------------------------------------------------------------------------------
# Main function to fetch from all connectors
# ------------------------------------------------------------------------------
async def fetch_all_recalls() -> List[Recall]:
    """Fetch recalls from all available connectors."""
    logger.info("Starting to fetch recalls from all connectors...")
    
    connectors = [
        CPSCConnector(),       # ✅ Working with date filtering
        NHTSAConnector(),      # ✅ FIXED: Now uses correct resource ID (6axg-epim)
        FDAConnector(),        # ✅ Working with both endpoints
        USDAFSISConnector(),   # ✅ FIXED: Now using official RSS feed (working!)
        EURapexConnector(),    # ✅ FIXED: Improved field mapping for RAPEX data
        UKOPSSConnector(),     # ✅ Working via GOV.UK Search
        SGCPSOConnector()      # Placeholder
    ]
    
    all_recalls = []
    
    for connector in connectors:
        try:
            connector_name = connector.__class__.__name__
            logger.info(f"Fetching from {connector_name}...")
            recalls = await connector.fetch_recent_recalls()
            all_recalls.extend(recalls)
            logger.info(f"Successfully fetched {len(recalls)} recalls from {connector_name}")
        except Exception as e:
            logger.error(f"Error with connector {connector.__class__.__name__}: {e}", exc_info=True)
            continue
    
    logger.info(f"Total recalls fetched: {len(all_recalls)}")
    return all_recalls

# For testing
if __name__ == "__main__":
    async def main():
        logging.basicConfig(level=logging.INFO)
        recalls = await fetch_all_recalls()
        for recall in recalls[:5]:  # Show first 5
            print(f"{recall.recall_id}: {recall.product_name}")
    
    asyncio.run(main())