from woocommerce import API
import os
import urllib3

# Suprimir warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CONFIG = {
    "api_url": os.environ.get("WC_API_URL", "https://mcielectronics.cl"),  # ⚠️ CAMBIA ESTO
    "consumer_key": os.environ.get("WC_CONSUMER_KEY", "ck_0c58ea3ea68db031865637fdafa225cb250ebb0b"),  # ⚠️ CAMBIA ESTO
    "consumer_secret": os.environ.get("WC_CONSUMER_SECRET", "cs_c80f40c74567be7a19da7d157a407ab727bc557a"),  # ⚠️ CAMBIA ESTO
    "api_version": "wc/v3",
    "timeout": 30,
    "per_page": 100,
    "max_reintentos": 3,
    "sleep_between_pages": 1,
    "retry_sleep_seconds": 5,
    "ventas_dias": 90,
    "estados_validos": [
        "completed",
        "processing",
        "on-hold",
        "listo-despacho",
        "listo-retiro",
    ],
    "visitas_meta_keys": [
        "_post_views_count",
        "post_views_count",
        "_eael_post_view_count",
    ],
    "visitas_muchas_sin_ventas": 50,
    "visitas_baja_conversion": 20,
    "visitas_alta_conversion": 10,
    "conversion_baja_pct": 2,
    "conversion_alta_pct": 5,
    "stock_minimo_sin_visitas": 5,
    "min_ventas_oportunidad_precio": 10,
    "umbral_diferencia_precio_pct": 0.1,
}

wcapi = API(
    url=CONFIG["api_url"],
    consumer_key=CONFIG["consumer_key"],
    consumer_secret=CONFIG["consumer_secret"],
    version=CONFIG["api_version"],
    timeout=CONFIG["timeout"],
)
