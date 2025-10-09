"""
Task 13: Localization Support for BabyShield API
Provides multi-language support with fallback to en-US
"""

from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/i18n", tags=["Localization"])


# ========================= MODELS =========================


class LocalizedString(BaseModel):
    """A string with translations"""

    key: str
    value: str
    locale: str


class LocalizedContent(BaseModel):
    """Content with all translations"""

    key: str
    translations: Dict[str, str]


class SupportedLocale(BaseModel):
    """Supported locale information"""

    code: str
    name: str
    native_name: str
    direction: str = Field("ltr", description="Text direction: ltr or rtl")
    date_format: str
    time_format: str
    currency: str
    decimal_separator: str
    thousands_separator: str


# ========================= LOCALIZATION DATA =========================

# Supported locales
SUPPORTED_LOCALES = {
    "en-US": SupportedLocale(
        code="en-US",
        name="English (United States)",
        native_name="English",
        direction="ltr",
        date_format="MM/DD/YYYY",
        time_format="12h",
        currency="USD",
        decimal_separator=".",
        thousands_separator=",",
    ),
    "es-ES": SupportedLocale(
        code="es-ES",
        name="Spanish (Spain)",
        native_name="Español",
        direction="ltr",
        date_format="DD/MM/YYYY",
        time_format="24h",
        currency="EUR",
        decimal_separator=",",
        thousands_separator=".",
    ),
    "es-MX": SupportedLocale(
        code="es-MX",
        name="Spanish (Mexico)",
        native_name="Español (México)",
        direction="ltr",
        date_format="DD/MM/YYYY",
        time_format="12h",
        currency="MXN",
        decimal_separator=".",
        thousands_separator=",",
    ),
}

# Translations dictionary
TRANSLATIONS = {
    # App UI
    "app.name": {"en-US": "BabyShield", "es-ES": "BabyShield", "es-MX": "BabyShield"},
    "app.tagline": {
        "en-US": "Scan or search recalled products. Instant safety info for families.",
        "es-ES": "Escanea o busca productos retirados. Información de seguridad instantánea para familias.",
        "es-MX": "Escanea o busca productos retirados. Información de seguridad instantánea para familias.",
    },
    # Navigation
    "nav.home": {"en-US": "Home", "es-ES": "Inicio", "es-MX": "Inicio"},
    "nav.scan": {"en-US": "Scan", "es-ES": "Escanear", "es-MX": "Escanear"},
    "nav.search": {"en-US": "Search", "es-ES": "Buscar", "es-MX": "Buscar"},
    "nav.alerts": {"en-US": "Alerts", "es-ES": "Alertas", "es-MX": "Alertas"},
    "nav.settings": {"en-US": "Settings", "es-ES": "Configuración", "es-MX": "Configuración"},
    # Barcode Scanner
    "scanner.permission.title": {
        "en-US": "Enable Camera for Barcode Scanning",
        "es-ES": "Habilitar Cámara para Escanear Códigos",
        "es-MX": "Habilitar Cámara para Escanear Códigos",
    },
    "scanner.permission.message": {
        "en-US": "BabyShield needs camera access to scan product barcodes and check for safety recalls. No photos are stored.",
        "es-ES": "BabyShield necesita acceso a la cámara para escanear códigos de barras y verificar retiros de seguridad. No se almacenan fotos.",
        "es-MX": "BabyShield necesita acceso a la cámara para escanear códigos de barras y verificar retiros de seguridad. No se almacenan fotos.",
    },
    "scanner.instruction": {
        "en-US": "Point camera at product barcode",
        "es-ES": "Apunta la cámara al código de barras",
        "es-MX": "Apunta la cámara al código de barras",
    },
    "scanner.scanning": {
        "en-US": "Scanning...",
        "es-ES": "Escaneando...",
        "es-MX": "Escaneando...",
    },
    # Search
    "search.placeholder": {
        "en-US": "Search for products or brands",
        "es-ES": "Buscar productos o marcas",
        "es-MX": "Buscar productos o marcas",
    },
    "search.button": {"en-US": "Search", "es-ES": "Buscar", "es-MX": "Buscar"},
    "search.no_results": {
        "en-US": "No results found",
        "es-ES": "No se encontraron resultados",
        "es-MX": "No se encontraron resultados",
    },
    "search.loading": {"en-US": "Loading...", "es-ES": "Cargando...", "es-MX": "Cargando..."},
    # Recall Status Messages
    "recall.found": {
        "en-US": "⚠️ Recall Found!",
        "es-ES": "⚠️ ¡Retiro Encontrado!",
        "es-MX": "⚠️ ¡Retiro Encontrado!",
    },
    "recall.not_found": {
        "en-US": "✅ No recalls found",
        "es-ES": "✅ No se encontraron retiros",
        "es-MX": "✅ No se encontraron retiros",
    },
    "recall.similar_found": {
        "en-US": "No direct match—showing similar recalls",
        "es-ES": "Sin coincidencia directa—mostrando retiros similares",
        "es-MX": "Sin coincidencia directa—mostrando retiros similares",
    },
    "recall.safe_product": {
        "en-US": "This product appears to be safe",
        "es-ES": "Este producto parece ser seguro",
        "es-MX": "Este producto parece ser seguro",
    },
    # Recall Details
    "recall.product_name": {
        "en-US": "Product Name",
        "es-ES": "Nombre del Producto",
        "es-MX": "Nombre del Producto",
    },
    "recall.brand": {"en-US": "Brand", "es-ES": "Marca", "es-MX": "Marca"},
    "recall.hazard": {"en-US": "Hazard", "es-ES": "Peligro", "es-MX": "Peligro"},
    "recall.remedy": {"en-US": "Remedy", "es-ES": "Solución", "es-MX": "Solución"},
    "recall.date": {
        "en-US": "Recall Date",
        "es-ES": "Fecha del Retiro",
        "es-MX": "Fecha del Retiro",
    },
    # Actions
    "action.view_details": {
        "en-US": "View Details",
        "es-ES": "Ver Detalles",
        "es-MX": "Ver Detalles",
    },
    "action.scan_another": {
        "en-US": "Scan Another",
        "es-ES": "Escanear Otro",
        "es-MX": "Escanear Otro",
    },
    "action.share": {"en-US": "Share", "es-ES": "Compartir", "es-MX": "Compartir"},
    "action.save": {"en-US": "Save", "es-ES": "Guardar", "es-MX": "Guardar"},
    "action.cancel": {"en-US": "Cancel", "es-ES": "Cancelar", "es-MX": "Cancelar"},
    "action.ok": {"en-US": "OK", "es-ES": "OK", "es-MX": "OK"},
    "action.retry": {"en-US": "Retry", "es-ES": "Reintentar", "es-MX": "Reintentar"},
    # Settings
    "settings.language": {"en-US": "Language", "es-ES": "Idioma", "es-MX": "Idioma"},
    "settings.notifications": {
        "en-US": "Notifications",
        "es-ES": "Notificaciones",
        "es-MX": "Notificaciones",
    },
    "settings.privacy": {"en-US": "Privacy", "es-ES": "Privacidad", "es-MX": "Privacidad"},
    "settings.about": {"en-US": "About", "es-ES": "Acerca de", "es-MX": "Acerca de"},
    "settings.help": {"en-US": "Help", "es-ES": "Ayuda", "es-MX": "Ayuda"},
    # Accessibility Labels
    "a11y.scan_button": {
        "en-US": "Scan barcode button",
        "es-ES": "Botón escanear código de barras",
        "es-MX": "Botón escanear código de barras",
    },
    "a11y.search_button": {
        "en-US": "Search button",
        "es-ES": "Botón de búsqueda",
        "es-MX": "Botón de búsqueda",
    },
    "a11y.back_button": {"en-US": "Go back", "es-ES": "Volver atrás", "es-MX": "Volver atrás"},
    "a11y.close_button": {"en-US": "Close", "es-ES": "Cerrar", "es-MX": "Cerrar"},
    "a11y.menu_button": {"en-US": "Open menu", "es-ES": "Abrir menú", "es-MX": "Abrir menú"},
    # Error Messages
    "error.network": {
        "en-US": "Network error. Please check your connection.",
        "es-ES": "Error de red. Por favor verifica tu conexión.",
        "es-MX": "Error de red. Por favor verifica tu conexión.",
    },
    "error.generic": {
        "en-US": "Something went wrong. Please try again.",
        "es-ES": "Algo salió mal. Por favor intenta de nuevo.",
        "es-MX": "Algo salió mal. Por favor intenta de nuevo.",
    },
    "error.camera_permission": {
        "en-US": "Camera permission required",
        "es-ES": "Se requiere permiso de cámara",
        "es-MX": "Se requiere permiso de cámara",
    },
    "error.invalid_barcode": {
        "en-US": "Invalid barcode. Please try again.",
        "es-ES": "Código de barras inválido. Por favor intenta de nuevo.",
        "es-MX": "Código de barras inválido. Por favor intenta de nuevo.",
    },
}


# ========================= HELPER FUNCTIONS =========================


def parse_accept_language(accept_language: str) -> List[str]:
    """
    Parse Accept-Language header and return ordered list of locales
    Example: "en-US,en;q=0.9,es;q=0.8" -> ["en-US", "en", "es"]
    """
    if not accept_language:
        return ["en-US"]

    locales = []
    parts = accept_language.split(",")

    for part in parts:
        locale = part.split(";")[0].strip()
        locales.append(locale)

    # Add fallback
    if "en-US" not in locales:
        locales.append("en-US")

    return locales


def get_best_locale(requested_locales: List[str]) -> str:
    """
    Find the best matching locale from requested list
    """
    for locale in requested_locales:
        # Exact match
        if locale in SUPPORTED_LOCALES:
            return locale

        # Try language-only match (es -> es-ES)
        lang = locale.split("-")[0]
        for supported in SUPPORTED_LOCALES:
            if supported.startswith(lang):
                return supported

    # Default to en-US
    return "en-US"


def translate(key: str, locale: str = "en-US") -> str:
    """
    Get translation for a key in specified locale
    """
    if key not in TRANSLATIONS:
        logger.warning(f"Translation key not found: {key}")
        return key

    translations = TRANSLATIONS[key]

    # Try exact locale
    if locale in translations:
        return translations[locale]

    # Try language-only fallback
    lang = locale.split("-")[0]
    for loc, trans in translations.items():
        if loc.startswith(lang):
            return trans

    # Fallback to en-US
    return translations.get("en-US", key)


# ========================= API ENDPOINTS =========================


@router.get("/locales", response_model=List[SupportedLocale])
async def get_supported_locales():
    """
    Get list of supported locales with their configuration
    """
    return list(SUPPORTED_LOCALES.values())


@router.get("/locale/{locale_code}")
async def get_locale_info(locale_code: str):
    """
    Get detailed information about a specific locale
    """
    if locale_code not in SUPPORTED_LOCALES:
        # Try to find a close match
        locale_code = get_best_locale([locale_code])

    return SUPPORTED_LOCALES[locale_code]


@router.get("/translations")
async def get_translations(
    locale: Optional[str] = Query("en-US", description="Locale code"),
    keys: Optional[List[str]] = Query(None, description="Specific keys to retrieve"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
):
    """
    Get translations for specified locale or from Accept-Language header

    Examples:
    - GET /api/v1/i18n/translations?locale=es-ES
    - GET /api/v1/i18n/translations (uses Accept-Language header)
    - GET /api/v1/i18n/translations?keys=app.name&keys=app.tagline
    """

    # Determine locale
    if accept_language and not locale:
        requested_locales = parse_accept_language(accept_language)
        locale = get_best_locale(requested_locales)
    elif not locale:
        locale = "en-US"

    # Build response
    if keys:
        # Return only requested keys
        result = {}
        for key in keys:
            result[key] = translate(key, locale)
    else:
        # Return all translations for locale
        result = {}
        for key in TRANSLATIONS:
            result[key] = translate(key, locale)

    return {"ok": True, "locale": locale, "translations": result}


@router.get("/translate/{key}")
async def translate_key(
    key: str,
    locale: Optional[str] = Query("en-US"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
):
    """
    Translate a single key
    """
    # Determine locale
    if accept_language and not locale:
        requested_locales = parse_accept_language(accept_language)
        locale = get_best_locale(requested_locales)

    translation = translate(key, locale)

    return {"ok": True, "key": key, "locale": locale, "value": translation}


@router.post("/translations/batch")
async def translate_batch(
    keys: List[str],
    locale: Optional[str] = Query("en-US"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
):
    """
    Translate multiple keys at once
    """
    # Determine locale
    if accept_language and not locale:
        requested_locales = parse_accept_language(accept_language)
        locale = get_best_locale(requested_locales)

    translations = {}
    for key in keys:
        translations[key] = translate(key, locale)

    return {"ok": True, "locale": locale, "translations": translations}


# ========================= ACCESSIBILITY SUPPORT =========================


@router.get("/a11y/labels")
async def get_accessibility_labels(
    locale: Optional[str] = Query("en-US"),
    accept_language: Optional[str] = Header(None, alias="Accept-Language"),
):
    """
    Get all accessibility labels for screen readers
    """
    # Determine locale
    if accept_language and not locale:
        requested_locales = parse_accept_language(accept_language)
        locale = get_best_locale(requested_locales)

    # Get all a11y labels
    a11y_labels = {}
    for key in TRANSLATIONS:
        if key.startswith("a11y."):
            a11y_labels[key] = translate(key, locale)

    return {"ok": True, "locale": locale, "labels": a11y_labels}


@router.get("/a11y/config")
async def get_accessibility_config():
    """
    Get accessibility configuration for the app
    """
    return {
        "ok": True,
        "wcag_level": "AA",
        "minimum_contrast_ratio": 4.5,
        "large_text_contrast_ratio": 3.0,
        "focus_indicator_width": 2,
        "minimum_touch_target": 44,
        "supports_dynamic_type": True,
        "supports_reduce_motion": True,
        "supports_high_contrast": True,
        "text_scaling": {"minimum": 0.85, "default": 1.0, "maximum": 2.0},
        "colors": {
            "primary": {
                "hex": "#2196F3",
                "contrast_white": 3.1,
                "contrast_black": 6.8,
                "wcag_aa_white": False,
                "wcag_aa_black": True,
            },
            "danger": {
                "hex": "#F44336",
                "contrast_white": 3.0,
                "contrast_black": 7.0,
                "wcag_aa_white": False,
                "wcag_aa_black": True,
            },
            "success": {
                "hex": "#4CAF50",
                "contrast_white": 2.5,
                "contrast_black": 8.4,
                "wcag_aa_white": False,
                "wcag_aa_black": True,
            },
        },
    }
