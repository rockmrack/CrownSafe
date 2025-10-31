"""
Safety Data Connectors for CPSC, EU Safety Gate, and Commercial Sources
Part of the Proactive Consumer Product Safety Framework
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class SafetyDataRecord:
    """Standardized safety data record from any source"""

    source: str
    source_id: str
    product_name: str
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    upc: Optional[str] = None
    gtin: Optional[str] = None
    recall_date: Optional[datetime] = None
    hazard_type: Optional[str] = None
    hazard_description: Optional[str] = None
    remedy: Optional[str] = None
    units_affected: Optional[int] = None
    incidents: Optional[int] = None
    injuries: Optional[int] = None
    deaths: Optional[int] = None
    severity: Optional[str] = None
    url: Optional[str] = None
    raw_data: Optional[Dict] = None


class CPSCDataConnector:
    """
    Comprehensive CPSC data connector
    Integrates Recalls, NEISS, Violations, and Penalties
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://www.saferproducts.gov/RestWebServices"
        self.recall_api = "https://www.cpsc.gov/Recalls/CPSC-Recall-API"

    async def fetch_recalls(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[SafetyDataRecord]:
        """
        Fetch recall data from CPSC Recall API
        """
        logger.info("Fetching CPSC recall data...")
        records = []

        try:
            async with aiohttp.ClientSession() as session:
                # CPSC Recall API endpoint
                url = f"{self.base_url}/Recall"

                params = {"format": "json", "limit": min(limit, 100)}  # API limit

                if start_date:
                    params["RecallDateStart"] = start_date.strftime("%Y-%m-%d")
                if end_date:
                    params["RecallDateEnd"] = end_date.strftime("%Y-%m-%d")

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        for recall in data.get("Results", []):
                            # Parse units affected
                            units = None
                            if recall.get("NumberOfUnits"):
                                try:
                                    units_str = recall["NumberOfUnits"].replace(",", "")
                                    units = int(units_str.split()[0])
                                except (ValueError, TypeError, IndexError):
                                    pass  # Can't parse units

                            record = SafetyDataRecord(
                                source="CPSC_RECALL",
                                source_id=recall.get("RecallID", ""),
                                product_name=recall.get("Products", [{}])[0].get("Name", "Unknown"),
                                brand=recall.get("Manufacturers", [{}])[0].get("Name"),
                                manufacturer=recall.get("Manufacturers", [{}])[0].get("Name"),
                                model_number=recall.get("Products", [{}])[0].get("Model"),
                                recall_date=self._parse_date(recall.get("RecallDate")),
                                hazard_type=recall.get("Hazards", [{}])[0].get("HazardType"),
                                hazard_description=recall.get("Description"),
                                remedy=recall.get("Remedies", [{}])[0].get("Remedy"),
                                units_affected=units,
                                incidents=recall.get("Incidents", {}).get("Count"),
                                injuries=recall.get("Injuries", {}).get("Count"),
                                deaths=recall.get("Deaths", {}).get("Count"),
                                severity=self._determine_severity(recall),
                                url=recall.get("URL"),
                                raw_data=recall,
                            )
                            records.append(record)
                    else:
                        logger.error(f"CPSC API error: {response.status}")

        except Exception as e:
            logger.error(f"Error fetching CPSC recalls: {e}")

        logger.info(f"Fetched {len(records)} CPSC recall records")
        return records

    async def fetch_neiss_data(
        self,
        start_date: Optional[datetime] = None,
        product_codes: Optional[List[int]] = None,
    ) -> List[SafetyDataRecord]:
        """
        Fetch NEISS injury data
        Note: NEISS data requires special access and processing
        """
        logger.info("Fetching NEISS injury data...")
        records = []

        # NEISS product codes for baby products (examples) - Reserved for future queries
        _ = product_codes or [
            1543,  # Baby carriers
            1545,  # Baby gates
            1528,  # Cribs
            1537,  # High chairs
            1548,  # Playpens
            1519,  # Baby bottles
        ]

        # Note: Real NEISS data requires downloading CSV files
        # This is a placeholder for the actual implementation
        # which would involve downloading and parsing NEISS public files

        return records

    async def fetch_violations(self, company_name: Optional[str] = None, limit: int = 1000) -> List[SafetyDataRecord]:
        """
        Fetch violation data from CPSC
        """
        logger.info("Fetching CPSC violation data...")
        records = []

        try:
            async with aiohttp.ClientSession() as session:
                # CPSC violations endpoint (example)
                url = f"{self.base_url}/Violations"

                params = {"format": "json", "limit": limit}
                if company_name:
                    params["Company"] = company_name

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        for violation in data.get("Results", []):
                            record = SafetyDataRecord(
                                source="CPSC_VIOLATION",
                                source_id=violation.get("ViolationID"),
                                product_name=violation.get("Product"),
                                manufacturer=violation.get("Company"),
                                hazard_type=violation.get("ViolationType"),
                                hazard_description=violation.get("Description"),
                                severity="medium",
                                raw_data=violation,
                            )
                            records.append(record)

        except Exception as e:
            logger.error(f"Error fetching CPSC violations: {e}")

        return records

    async def fetch_safety_articles(self) -> List[Dict]:
        """
        Fetches recent safety news and educational articles from the CPSC newsroom API.
        """
        logger.info("Fetching safety articles from CPSC Newsroom API...")
        news_api_url = "https://www.cpsc.gov/content/api/news"
        articles = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    news_api_url,
                    params={"type": "blog"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data:
                            # We only want articles with a clear title and URL
                            if not item.get("title") or not item.get("url"):
                                continue

                            # Create a unique ID for our database
                            article_id = f"CPSC-NEWS-{item.get('nid', 'unknown')}"

                            # Parse publication date
                            pub_date = datetime.fromtimestamp(int(item.get("created", 0)))

                            articles.append(
                                {
                                    "article_id": article_id,
                                    "title": item["title"],
                                    "summary": item.get("description", "Read more for details."),
                                    "source_agency": "CPSC",
                                    "publication_date": pub_date.date(),
                                    "image_url": item.get("image_medium"),
                                    "article_url": f"https://www.cpsc.gov{item['url']}",
                                    "is_featured": "safe sleep" in item["title"].lower()
                                    or "anchor it" in item["title"].lower(),
                                }
                            )

                        logger.info(f"Successfully fetched {len(articles)} safety articles from CPSC.")
                    else:
                        logger.error(f"CPSC News API returned status {response.status}")

        except Exception as e:
            logger.error(f"Failed to fetch safety articles from CPSC: {e}")

        return articles

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse CPSC date format"""
        if not date_str:
            return None
        try:
            # CPSC uses various formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y"]:
                try:
                    return datetime.strptime(date_str, fmt)
                except (ValueError, TypeError):
                    continue
        except Exception:
            pass
        return None

    def _determine_severity(self, recall_data: Dict) -> str:
        """Determine severity based on CPSC data"""
        deaths = recall_data.get("Deaths", {}).get("Count", 0)
        injuries = recall_data.get("Injuries", {}).get("Count", 0)

        if deaths > 0:
            return "critical"
        elif injuries > 10:
            return "high"
        elif injuries > 0:
            return "medium"
        else:
            return "low"


class EUSafetyGateConnector:
    """
    EU Safety Gate (RAPEX) data connector
    """

    def __init__(self):
        self.base_url = "https://ec.europa.eu/safety-gate-api"
        self.atom_feed = "https://ec.europa.eu/safety/gate/consumers/feed.atom"

    async def fetch_alerts(
        self,
        start_date: Optional[datetime] = None,
        countries: Optional[List[str]] = None,
        risk_types: Optional[List[str]] = None,
        limit: int = 1000,
    ) -> List[SafetyDataRecord]:
        """
        Fetch alerts from EU Safety Gate
        """
        logger.info("Fetching EU Safety Gate alerts...")
        records = []

        try:
            import feedparser

            # Parse Atom feed
            feed = feedparser.parse(self.atom_feed)

            for entry in feed.entries[:limit]:
                # Parse entry data
                alert_data = self._parse_feed_entry(entry)

                # Apply filters
                if countries and alert_data.get("country") not in countries:
                    continue
                if risk_types and alert_data.get("risk_type") not in risk_types:
                    continue

                record = SafetyDataRecord(
                    source="EU_SAFETY_GATE",
                    source_id=alert_data.get("id"),
                    product_name=alert_data.get("product"),
                    brand=alert_data.get("brand"),
                    manufacturer=alert_data.get("manufacturer"),
                    recall_date=alert_data.get("date"),
                    hazard_type=alert_data.get("risk_type"),
                    hazard_description=alert_data.get("risk_description"),
                    remedy=alert_data.get("measures"),
                    severity=alert_data.get("severity"),
                    url=entry.link,
                    raw_data=alert_data,
                )
                records.append(record)

        except Exception as e:
            logger.error(f"Error fetching EU Safety Gate alerts: {e}")

        logger.info(f"Fetched {len(records)} EU Safety Gate records")
        return records

    def _parse_feed_entry(self, entry) -> Dict:
        """Parse Atom feed entry"""
        # Extract structured data from entry
        data = {
            "id": entry.id,
            "product": entry.title,
            "date": datetime(*entry.published_parsed[:6]) if hasattr(entry, "published_parsed") else None,
            "risk_description": entry.summary if hasattr(entry, "summary") else None,
        }

        # Parse additional fields from content (reserved for future HTML parsing)
        if hasattr(entry, "content"):
            _ = entry.content[0].value if entry.content else ""  # content
            # Extract risk type, measures, etc. from content
            # This would require parsing the HTML/XML content

        return data


class CommercialDatabaseConnector:
    """
    Connector for commercial product databases
    Integrates with UPC/EAN/GTIN lookup services
    """

    def __init__(self, api_keys: Dict[str, str] = None):
        self.api_keys = api_keys or {}

    async def lookup_product_by_barcode(self, barcode: str) -> Optional[Dict]:
        """
        Look up product information by barcode
        Tries multiple services in order of preference
        """
        # Try services in order
        services = [
            ("upcitemdb", self._lookup_upcitemdb),
            ("go_upc", self._lookup_go_upc),
            ("ean_search", self._lookup_ean_search),
        ]

        for service_name, lookup_func in services:
            try:
                result = await lookup_func(barcode)
                if result:
                    logger.info(f"Found product in {service_name}: {result.get('product_name')}")
                    return result
            except Exception as e:
                logger.warning(f"Error with {service_name}: {e}")
                continue

        return None

    async def _lookup_upcitemdb(self, barcode: str) -> Optional[Dict]:
        """Look up in UPCitemdb"""
        async with aiohttp.ClientSession() as session:
            url = "https://api.upcitemdb.com/prod/v1/lookup"
            params = {"upc": barcode}
            headers = {"user_key": self.api_keys.get("upcitemdb", "")}

            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("items"):
                        item = data["items"][0]
                        return {
                            "product_name": item.get("title"),
                            "brand": item.get("brand"),
                            "model": item.get("model"),
                            "upc": barcode,
                            "images": item.get("images", []),
                            "source": "upcitemdb",
                        }
        return None

    async def _lookup_go_upc(self, barcode: str) -> Optional[Dict]:
        """Look up in Go-UPC"""
        # Implementation for Go-UPC API
        return None

    async def _lookup_ean_search(self, barcode: str) -> Optional[Dict]:
        """Look up in EAN-Search"""
        # Implementation for EAN-Search API
        return None


class DataUnificationEngine:
    """
    Entity resolution and data unification engine
    Creates golden records from multiple data sources
    """

    def __init__(self):
        self.matching_threshold = 0.8

    def create_golden_record(self, records: List[SafetyDataRecord]) -> Dict:
        """
        Create a unified golden record from multiple sources
        """
        if not records:
            return None

        # Start with the most complete record
        golden = self._find_most_complete_record(records)

        # Merge data from other records
        for record in records:
            self._merge_record(golden, record)

        # Calculate confidence score
        golden["confidence_score"] = self._calculate_confidence(golden, records)

        # Add metadata
        golden["source_records"] = [r.source_id for r in records]
        golden["sources"] = list(set(r.source for r in records))
        golden["last_updated"] = datetime.utcnow()

        return golden

    def match_records(self, record1: SafetyDataRecord, record2: SafetyDataRecord) -> float:
        """
        Calculate match score between two records
        Returns score between 0 and 1
        """
        score = 0.0
        weights = {
            "upc": 0.3,
            "gtin": 0.3,
            "model_number": 0.2,
            "product_name": 0.1,
            "brand": 0.05,
            "manufacturer": 0.05,
        }

        # Exact matches on identifiers
        if record1.upc and record1.upc == record2.upc:
            score += weights["upc"]
        if record1.gtin and record1.gtin == record2.gtin:
            score += weights["gtin"]
        if record1.model_number and record1.model_number == record2.model_number:
            score += weights["model_number"]

        # Fuzzy matches on text fields
        if record1.product_name and record2.product_name:
            similarity = self._string_similarity(record1.product_name, record2.product_name)
            score += weights["product_name"] * similarity

        if record1.brand and record2.brand:
            similarity = self._string_similarity(record1.brand, record2.brand)
            score += weights["brand"] * similarity

        if record1.manufacturer and record2.manufacturer:
            similarity = self._string_similarity(record1.manufacturer, record2.manufacturer)
            score += weights["manufacturer"] * similarity

        return score

    def _find_most_complete_record(self, records: List[SafetyDataRecord]) -> Dict:
        """Find the record with the most non-null fields"""
        best_record = None
        best_score = 0

        for record in records:
            score = sum(1 for field, value in record.__dict__.items() if value is not None)
            if score > best_score:
                best_score = score
                best_record = record.__dict__.copy()

        return best_record

    def _merge_record(self, golden: Dict, record: SafetyDataRecord):
        """Merge data from a record into the golden record"""
        for field, value in record.__dict__.items():
            if value is not None:
                if field not in golden or golden[field] is None:
                    golden[field] = value
                elif field in ["incidents", "injuries", "deaths", "units_affected"]:
                    # Sum numeric fields
                    golden[field] = (golden.get(field, 0) or 0) + (value or 0)
                elif field == "severity":
                    # Take the highest severity
                    severity_order = ["low", "medium", "high", "critical"]
                    if severity_order.index(value) > severity_order.index(golden.get(field, "low")):
                        golden[field] = value

    def _calculate_confidence(self, golden: Dict, source_records: List[SafetyDataRecord]) -> float:
        """Calculate confidence score for the golden record"""
        # Factors that increase confidence:
        # - Multiple sources agree
        # - Presence of unique identifiers (UPC, GTIN)
        # - Completeness of data

        confidence = 0.5  # Base confidence

        # Multiple sources
        if len(set(r.source for r in source_records)) > 1:
            confidence += 0.2

        # Unique identifiers present
        if golden.get("upc") or golden.get("gtin"):
            confidence += 0.2

        # Data completeness
        completeness = sum(1 for v in golden.values() if v is not None) / len(golden)
        confidence += 0.1 * completeness

        return min(confidence, 1.0)

    def _string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate string similarity using Levenshtein distance
        Returns value between 0 and 1
        """
        if not str1 or not str2:
            return 0.0

        # Convert to lowercase and strip
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

        if s1 == s2:
            return 1.0

        # Simple character-based similarity
        # In production, use python-Levenshtein or similar
        longer = max(len(s1), len(s2))
        if longer == 0:
            return 1.0

        # Count matching characters
        matches = sum(c1 == c2 for c1, c2 in zip(s1, s2, strict=False))
        return matches / longer
