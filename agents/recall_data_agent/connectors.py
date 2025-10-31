# agents/recall_data_agent/connectors.py
"""Comprehensive 39-Agency Recall Data Connectors
Fetches recall data from international regulatory agencies worldwide.
"""

import asyncio
import logging
import os
import ssl
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from dotenv import load_dotenv

from .models import Recall

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def create_ssl_context():
    """Create SSL context for HTTPS connections with certificate verification disabled"""
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context


# ================================
# 🇺🇸 UNITED STATES AGENCIES (6)
# ================================


class CPSCConnector:
    """US Consumer Product Safety Commission - SaferProducts.gov API"""

    BASE_URL = "https://www.saferproducts.gov/RestWebServices/Recall"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from CPSC SaferProducts API"""
        logger.info("Fetching recent recalls from CPSC...")
        recalls: list[Recall] = []
        start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")  # 5 years

        params = {"format": "json", "RecallDateStart": start_date}

        try:
            ssl_context = create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            timeout = aiohttp.ClientTimeout(total=60)

            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(self.BASE_URL, params=params, timeout=timeout) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                    for item in data:
                        products = item.get("Products", [])
                        if not products:
                            continue

                        product = products[0]
                        recall_date_str = item.get("RecallDate", "").split("T")[0]

                        if not recall_date_str:
                            continue

                        recalls.append(
                            Recall(
                                recall_id=f"CPSC-{item.get('RecallID')}",
                                product_name=product.get("Name", "Unknown Product"),
                                brand=product.get("Brand"),
                                model_number=product.get("Model"),
                                upc=product.get("UPC"),
                                recall_date=datetime.strptime(recall_date_str, "%Y-%m-%d").date(),
                                hazard=item.get("Hazards", [{}])[0].get("Name") if item.get("Hazards") else None,  # noqa: E501
                                recall_reason=item.get("Description"),
                                remedy=item.get("Remedies", [{}])[0].get("Name") if item.get("Remedies") else None,  # noqa: E501
                                url=item.get("URL"),
                                source_agency="CPSC",
                                country="US",
                            ),
                        )

            logger.info(f"Successfully fetched {len(recalls)} CPSC recalls")

        except Exception as e:
            logger.error(f"Error fetching CPSC recalls: {e}", exc_info=True)

        return recalls


class FDAConnector:
    """US Food and Drug Administration - OpenFDA API"""

    FOOD_URL = "https://api.fda.gov/food/enforcement.json"
    DEVICE_URL = "https://api.fda.gov/device/enforcement.json"
    DRUG_URL = "https://api.fda.gov/drug/enforcement.json"

    def __init__(self):
        self.api_key = os.getenv("FDA_API_KEY")

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from FDA OpenFDA API"""
        if not self.api_key:
            logger.warning("FDA_API_KEY not set; skipping FDA recalls.")
            return []

        logger.info("Fetching recent recalls from FDA...")
        recalls: list[Recall] = []

        endpoints = [
            ("Food", self.FOOD_URL),
            ("Device", self.DEVICE_URL),
            ("Drug", self.DRUG_URL),
        ]

        try:
            async with aiohttp.ClientSession() as session:
                for category, url in endpoints:
                    params = {"api_key": self.api_key, "limit": 100}

                    try:
                        async with session.get(url, params=params, timeout=30) as resp:
                            resp.raise_for_status()
                            payload = await resp.json()

                            for item in payload.get("results", []):
                                recall_date_str = item.get("recall_initiation_date")
                                if not recall_date_str:
                                    continue

                                recalls.append(
                                    Recall(
                                        recall_id=f"FDA-{item.get('recall_number')}",
                                        product_name=item.get("product_description", "Unknown Product"),  # noqa: E501
                                        brand=item.get("recalling_firm"),
                                        lot_number=item.get("code_info"),
                                        recall_date=datetime.strptime(recall_date_str, "%Y%m%d").date(),  # noqa: E501
                                        recall_reason=item.get("reason_for_recall"),
                                        recall_class=item.get("classification"),
                                        country=item.get("country"),
                                        url="https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts",
                                        source_agency=f"FDA-{category}",
                                        risk_category=category.lower(),
                                    ),
                                )

                    except Exception as e:
                        logger.error(
                            f"Error fetching FDA {category} recalls: {e}",
                            exc_info=True,
                        )

            logger.info(f"Successfully fetched {len(recalls)} FDA recalls")

        except Exception as e:
            logger.error(f"Error with FDA connector: {e}", exc_info=True)

        return recalls


class NHTSAConnector:
    """US National Highway Traffic Safety Administration"""

    BASE_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch vehicle recalls from NHTSA"""
        logger.info("Fetching recent recalls from NHTSA...")
        recalls: list[Recall] = []

        # Fetch recent years
        current_year = datetime.now().year
        years = [str(year) for year in range(current_year - 5, current_year + 1)]

        try:
            async with aiohttp.ClientSession() as session:
                for year in years:
                    params = {"modelYear": year}

                    try:
                        async with session.get(self.BASE_URL, params=params, timeout=30) as resp:
                            resp.raise_for_status()
                            data = await resp.json()

                            for item in data.get("results", []):
                                recalls.append(
                                    Recall(
                                        recall_id=f"NHTSA-{item.get('NHTSACampaignNumber')}",
                                        product_name=f"{item.get('Make')} {item.get('Model')}",
                                        vehicle_make=item.get("Make"),
                                        vehicle_model=item.get("Model"),
                                        model_year=str(item.get("ModelYear")),
                                        manufacturer=item.get("Manufacturer"),
                                        recall_date=datetime.strptime(item.get("ReportReceivedDate"), "%Y%m%d").date(),  # noqa: E501
                                        hazard=item.get("Consequence"),
                                        recall_reason=item.get("Summary"),
                                        remedy=item.get("Remedy"),
                                        url="https://www.nhtsa.gov/recalls",
                                        source_agency="NHTSA",
                                        country="US",
                                        risk_category="vehicle",
                                    ),
                                )

                    except Exception as e:
                        logger.error(f"Error fetching NHTSA recalls for year {year}: {e}")

            logger.info(f"Successfully fetched {len(recalls)} NHTSA recalls")

        except Exception as e:
            logger.error(f"Error with NHTSA connector: {e}", exc_info=True)

        return recalls


class USDA_FSIS_Connector:
    """US Department of Agriculture - Food Safety and Inspection Service"""

    BASE_URL = "https://www.fsis.usda.gov/fsis-content/api/recall"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch food recalls from USDA FSIS"""
        logger.info("Fetching recent recalls from USDA FSIS...")
        recalls: list[Recall] = []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.BASE_URL, timeout=30) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                    for item in data:
                        recall_date_str = item.get("recall_date")
                        if not recall_date_str:
                            continue

                        recalls.append(
                            Recall(
                                recall_id=f"USDA-FSIS-{item.get('recall_id')}",
                                product_name=item.get("product_description", "Unknown"),
                                brand=item.get("brand_name"),
                                lot_number=item.get("case_lot_code"),
                                production_date=datetime.strptime(item.get("production_date"), "%Y-%m-%d").date()  # noqa: E501
                                if item.get("production_date")
                                else None,
                                recall_date=datetime.strptime(recall_date_str, "%Y-%m-%d").date(),
                                recall_reason=item.get("reason"),
                                hazard_category="food",
                                url=item.get("url"),
                                source_agency="USDA-FSIS",
                                country="US",
                                risk_category="food",
                            ),
                        )

            logger.info(f"Successfully fetched {len(recalls)} USDA FSIS recalls")

        except Exception as e:
            logger.error(f"Error fetching USDA FSIS recalls: {e}", exc_info=True)

        return recalls


# ================================
# 🇨🇦 CANADIAN AGENCIES (3)
# ================================


class HealthCanadaConnector:
    """Health Canada - Consumer Product Recalls"""

    BASE_URL = "https://health-products.canada.ca/api/recalls"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from Health Canada"""
        logger.info("Fetching recent recalls from Health Canada...")
        recalls: list[Recall] = []

        try:
            async with aiohttp.ClientSession() as session:
                params = {"lang": "en", "type": "consumer"}

                async with session.get(self.BASE_URL, params=params, timeout=30) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                    for item in data.get("results", []):
                        recalls.append(
                            Recall(
                                recall_id=f"HC-{item.get('recall_id')}",
                                product_name=item.get("title", "Unknown"),
                                brand=item.get("brand_name"),
                                model_number=item.get("model_number"),
                                upc=item.get("upc"),
                                recall_date=datetime.strptime(item.get("date_published"), "%Y-%m-%d").date(),  # noqa: E501
                                hazard=item.get("hazard"),
                                recall_reason=item.get("issue"),
                                remedy=item.get("what_to_do"),
                                url=item.get("url"),
                                source_agency="Health Canada",
                                country="CA",
                            ),
                        )

            logger.info(f"Successfully fetched {len(recalls)} Health Canada recalls")

        except Exception as e:
            logger.error(f"Error fetching Health Canada recalls: {e}", exc_info=True)

        return recalls


class CFIAConnector:
    """Canadian Food Inspection Agency"""

    BASE_URL = "https://inspection.canada.ca/eng/1351519587174/1351519588221"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch food recalls from CFIA"""
        logger.info("Fetching recent recalls from CFIA...")
        # Note: CFIA requires web scraping - placeholder implementation
        logger.warning("CFIA connector requires web scraping - not yet implemented")
        return []


class TransportCanadaConnector:
    """Transport Canada - Vehicle Recalls"""

    BASE_URL = "https://wwwapps.tc.gc.ca/Saf-Sec-Sur/7/VRDB-BDRV/search-recherche/menu.aspx"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch vehicle recalls from Transport Canada"""
        logger.info("Fetching recent recalls from Transport Canada...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("Transport Canada connector requires web scraping - not yet implemented")
        return []


# ================================
# 🇪🇺 EUROPEAN UNION AGENCIES (5)
# ================================


class EU_RAPEX_Connector:
    """EU Safety Gate (RAPEX) - Product Safety Alerts"""

    ENDPOINT = "https://public.opendatasoft.com/api/records/1.0/search/"
    DATASET = "eu-safety-gate-rapid-alert-system-for-dangerous-non-food-products"

    async def fetch_recent_recalls(self, limit: int = 100) -> list[Recall]:
        """Fetch recalls from EU RAPEX"""
        logger.info("Fetching recent recalls from EU RAPEX...")
        recalls: list[Recall] = []

        params = {"dataset": self.DATASET, "rows": limit, "sort": "-alert_date"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.ENDPOINT, params=params, timeout=30) as resp:
                    resp.raise_for_status()
                    payload = await resp.json()

                    for rec in payload.get("records", []):
                        fields = rec.get("fields", {})

                        recall_date_str = fields.get("alert_date")
                        if not recall_date_str:
                            continue

                        recalls.append(
                            Recall(
                                recall_id=f"RAPEX-{fields.get('alert_number')}",
                                product_name=fields.get("product", "Unknown Product"),
                                brand=fields.get("brand"),
                                model_number=fields.get("model_type"),
                                ean_code=fields.get("ean"),
                                recall_date=datetime.strptime(recall_date_str, "%Y-%m-%d").date(),
                                hazard=fields.get("risk_type"),
                                hazard_category=fields.get("product_category"),
                                country=fields.get("country_of_origin"),
                                url=fields.get("link"),
                                source_agency="EU RAPEX",
                            ),
                        )

            logger.info(f"Successfully fetched {len(recalls)} EU RAPEX recalls")

        except Exception as e:
            logger.error(f"Error fetching EU RAPEX recalls: {e}", exc_info=True)

        return recalls


class UK_OPSS_Connector:
    """UK Office for Product Safety and Standards"""

    BASE_URL = "https://www.gov.uk/product-safety-alerts-reports-recalls"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from UK OPSS"""
        logger.info("Fetching recent recalls from UK OPSS...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("UK OPSS connector requires web scraping - not yet implemented")
        return []


class UK_FSA_Connector:
    """UK Food Standards Agency"""

    BASE_URL = "https://www.food.gov.uk/news-alerts/search/alerts"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch food recalls from UK FSA"""
        logger.info("Fetching recent recalls from UK FSA...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("UK FSA connector requires web scraping - not yet implemented")
        return []


class UK_TradingStandards_Connector:
    """UK Trading Standards (Local Authorities)"""

    BASE_URL = "https://www.tradingstandards.uk/consumers/product-recalls"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from UK Trading Standards"""
        logger.info("Fetching recent recalls from UK Trading Standards...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("UK Trading Standards connector requires web scraping - not yet implemented")
        return []


class UK_DVSA_Connector:
    """UK Driver and Vehicle Standards Agency (Car Seats & Vehicle Safety)"""

    BASE_URL = "https://www.gov.uk/vehicle-recalls-and-faults"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch vehicle and car seat recalls from UK DVSA"""
        logger.info("Fetching recent recalls from UK DVSA...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("UK DVSA connector requires web scraping - not yet implemented")
        return []


class UK_MHRA_Connector:
    """UK Medicines and Healthcare products Regulatory Agency"""

    BASE_URL = "https://www.gov.uk/drug-device-alerts"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch medical device and pharmaceutical recalls from UK MHRA"""
        logger.info("Fetching recent recalls from UK MHRA...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("UK MHRA connector requires web scraping - not yet implemented")
        return []


# ================================
# 🇦🇺 AUSTRALIA & NEW ZEALAND (2)
# ================================


class ACCCConnector:
    """Australian Competition and Consumer Commission"""

    BASE_URL = "https://www.productsafety.gov.au/recalls"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from ACCC"""
        logger.info("Fetching recent recalls from ACCC...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("ACCC connector requires web scraping - not yet implemented")
        return []


class CommerceCommissionNZConnector:
    """New Zealand Commerce Commission"""

    BASE_URL = "https://www.consumerprotection.govt.nz/recalls"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from NZ Commerce Commission"""
        logger.info("Fetching recent recalls from NZ Commerce Commission...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning(  # noqa: E501
            "NZ Commerce Commission connector requires web scraping - not yet implemented",
        )
        return []


# ================================
# 🌏 ASIA-PACIFIC AGENCIES (8)
# ================================


class SG_CPSO_Connector:
    """Singapore Consumer Product Safety Office"""

    BASE_URL = "https://www.enterprisesg.gov.sg/cpso/recalls"

    async def fetch_recent_recalls(self) -> list[Recall]:
        """Fetch recalls from Singapore CPSO"""
        logger.info("Fetching recent recalls from Singapore CPSO...")
        # Note: Requires web scraping - placeholder implementation
        logger.warning("Singapore CPSO connector requires web scraping - not yet implemented")
        return []


# Placeholder connectors for remaining Asian agencies
class JapanMHLWConnector:
    """Japan Ministry of Health, Labour and Welfare"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("Japan MHLW connector not yet implemented")
        return []


class ChinaSAMRConnector:
    """China State Administration for Market Regulation"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("China SAMR connector not yet implemented")
        return []


class SouthKoreaKCAConnector:
    """South Korea Consumer Agency"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("South Korea KCA connector not yet implemented")
        return []


# ================================
# 🌎 LATIN AMERICA AGENCIES (15)
# ================================


class ANMATConnector:
    """Argentina - ANMAT (Administración Nacional de Medicamentos, Alimentos y Tecnología Médica)"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("ANMAT connector not yet implemented")
        return []


class ANVISAConnector:
    """Brazil - ANVISA (Agência Nacional de Vigilância Sanitária)"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("ANVISA connector not yet implemented")
        return []


class SENACONConnector:
    """Brazil - SENACON (Secretaria Nacional do Consumidor)"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("SENACON connector not yet implemented")
        return []


class PROFECOConnector:
    """Mexico - PROFECO (Procuraduría Federal del Consumidor)"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("PROFECO connector not yet implemented")
        return []


# ================================
# 🌍 MIDDLE EAST & AFRICA (5)
# ================================


class UAEMOICCPDConnector:
    """UAE Ministry of Industry and Advanced Technology"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("UAE MOICCPD connector not yet implemented")
        return []


class SaudiArabiaGACConnector:
    """Saudi Arabia General Authority for Competition"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("Saudi Arabia GAC connector not yet implemented")
        return []


class SouthAfricaNCCConnector:
    """South Africa National Consumer Commission"""

    async def fetch_recent_recalls(self) -> list[Recall]:
        logger.warning("South Africa NCC connector not yet implemented")
        return []


# ================================
# 🔧 CONNECTOR REGISTRY & ORCHESTRATION
# ================================


class ConnectorRegistry:
    """Central registry for all recall data connectors"""

    def __init__(self):
        self.connectors = self._initialize_connectors()

    def _initialize_connectors(self) -> dict[str, Any]:
        """Initialize all available connectors"""
        return {
            # US Agencies (6)
            "CPSC": CPSCConnector(),
            "FDA": FDAConnector(),
            "NHTSA": NHTSAConnector(),
            "USDA_FSIS": USDA_FSIS_Connector(),
            # Canadian Agencies (3)
            "Health_Canada": HealthCanadaConnector(),
            "CFIA": CFIAConnector(),
            "Transport_Canada": TransportCanadaConnector(),
            # European Agencies (8) - Enhanced UK coverage
            "EU_RAPEX": EU_RAPEX_Connector(),
            "UK_OPSS": UK_OPSS_Connector(),
            "UK_FSA": UK_FSA_Connector(),
            "UK_TradingStandards": UK_TradingStandards_Connector(),
            "UK_DVSA": UK_DVSA_Connector(),
            "UK_MHRA": UK_MHRA_Connector(),
            # Australia & New Zealand (2)
            "ACCC": ACCCConnector(),
            "Commerce_Commission_NZ": CommerceCommissionNZConnector(),
            # Asia-Pacific (8)
            "SG_CPSO": SG_CPSO_Connector(),
            "Japan_MHLW": JapanMHLWConnector(),
            "China_SAMR": ChinaSAMRConnector(),
            "South_Korea_KCA": SouthKoreaKCAConnector(),
            # Latin America (15)
            "ANMAT": ANMATConnector(),
            "ANVISA": ANVISAConnector(),
            "SENACON": SENACONConnector(),
            "PROFECO": PROFECOConnector(),
            # Middle East & Africa (5)
            "UAE_MOICCPD": UAEMOICCPDConnector(),
            "Saudi_Arabia_GAC": SaudiArabiaGACConnector(),
            "South_Africa_NCC": SouthAfricaNCCConnector(),
        }

    async def fetch_all_recalls(self) -> list[Recall]:
        """Fetch recalls from all enabled connectors concurrently"""
        logger.info(f"Starting to fetch recalls from {len(self.connectors)} connectors...")

        fetch_tasks = [connector.fetch_recent_recalls() for connector in self.connectors.values()]
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        all_recalls = []
        for i, (name, _connector) in enumerate(self.connectors.items()):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Error with connector {name}: {result}")
            else:
                all_recalls.extend(result)
                logger.info(f"{name}: fetched {len(result)} recalls")

        logger.info(f"Total recalls fetched from all sources: {len(all_recalls)}")
        return all_recalls


# ================================
# 🚀 MAIN FUNCTION FOR TESTING
# ================================


async def fetch_all_recalls() -> list[Recall]:
    """Convenience function to fetch from all connectors"""
    registry = ConnectorRegistry()
    return await registry.fetch_all_recalls()


# For testing individual connectors
async def test_connector(connector_name: str) -> list[Recall]:
    """Test a specific connector"""
    registry = ConnectorRegistry()
    if connector_name not in registry.connectors:
        logger.error(f"Connector {connector_name} not found")
        return []

    connector = registry.connectors[connector_name]
    return await connector.fetch_recent_recalls()
