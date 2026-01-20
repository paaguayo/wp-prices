# WP Prices

Script para extraer productos, ventas y métricas desde WooCommerce y generar reportes en JSON, CSV y Markdown.

## Requisitos

- Python 3.x
- Dependencias:
  - `woocommerce`
  - `pandas`
  - `urllib3`

## Configuración

Los parámetros de ejecución están centralizados en el diccionario `CONFIG` dentro de `config.py`. Puedes sobrescribir las credenciales mediante variables de entorno:

- `WC_API_URL`
- `WC_CONSUMER_KEY`
- `WC_CONSUMER_SECRET`

Además, puedes ajustar en `CONFIG`:

- Paginación y reintentos (`per_page`, `max_reintentos`, `sleep_between_pages`, `retry_sleep_seconds`).
- Rango de días para ventas (`ventas_dias`).
- Estados válidos de órdenes (`estados_validos`).
- Claves de metadatos para visitas (`visitas_meta_keys`).
- Umbrales de conversión, visitas y stock (`visitas_*`, `conversion_*`, `stock_minimo_sin_visitas`).
- Criterios de oportunidades de precio (`min_ventas_oportunidad_precio`, `umbral_diferencia_precio_pct`).

## Uso

```bash
python main.py
```

El script generará los siguientes archivos en el directorio actual:

- `reporte_precios_<timestamp>.json`
- `analisis_productos_<timestamp>.csv`
- `reporte_legible_<timestamp>.md`
