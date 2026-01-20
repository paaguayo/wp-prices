"""Genera un reporte de pedidos y totaliza productos en un período."""
from collections import defaultdict
from datetime import datetime, timedelta
import json
import time

from main import CONFIG, wcapi


def obtener_pedidos(dias=None):
    """Obtiene pedidos en el período y sus productos."""
    if dias is None:
        dias = CONFIG["ventas_dias"]
    fecha_desde = (datetime.now() - timedelta(days=dias)).isoformat()

    pedidos = []
    estados_validos = CONFIG["estados_validos"]

    for estado in estados_validos:
        print(f"\n📦 Extrayendo pedidos con estado: {estado}")
        page = 1
        max_reintentos = CONFIG["max_reintentos"]

        while True:
            reintentos = 0
            while reintentos < max_reintentos:
                try:
                    print(f"   Página {page}...", end=" ")
                    response = wcapi.get(
                        "orders",
                        params={
                            "per_page": CONFIG["per_page"],
                            "page": page,
                            "after": fecha_desde,
                            "status": estado,
                        },
                    )

                    if response.status_code != 200:
                        print(f"❌ Error: {response.status_code}")
                        break

                    text = response.text
                    json_start = text.find("[")
                    if json_start == -1:
                        print("❌ No JSON")
                        break

                    clean_json = text[json_start:]
                    data = json.loads(clean_json)

                    if not isinstance(data, list) or not data:
                        print("✅ Fin")
                        break

                    pedidos.extend(data)
                    print(f"✅ {len(data)} pedidos")
                    page += 1
                    time.sleep(CONFIG["sleep_between_pages"])
                    break
                except Exception as e:
                    reintentos += 1
                    print(f"⚠️ Error: {str(e)[:30]}")
                    if reintentos < max_reintentos:
                        time.sleep(CONFIG["retry_sleep_seconds"])
                    else:
                        break

            if not isinstance(data, list) or not data:
                break

    return pedidos


def totalizar_productos(pedidos):
    """Suma cantidades por producto en todas las órdenes."""
    totales = defaultdict(lambda: {"nombre": "", "cantidad": 0})
    for pedido in pedidos:
        for item in pedido.get("line_items", []):
            producto_id = item.get("product_id")
            if producto_id is None:
                continue
            totales[producto_id]["nombre"] = item.get("name", "")
            totales[producto_id]["cantidad"] += int(item.get("quantity", 0))
    return totales


def generar_reporte_pedidos(pedidos, totales, timestamp):
    """Genera un reporte Markdown de pedidos y totales."""
    md = f"""# Reporte de Pedidos

**Fecha:** {datetime.now().isoformat()}
**Período:** últimos {CONFIG['ventas_dias']} días

## Pedidos

"""
    for pedido in pedidos:
        md += f"### Pedido #{pedido.get('id')} - {pedido.get('date_created')} ({pedido.get('status')})\n\n"
        for item in pedido.get("line_items", []):
            md += f"- {item.get('name')} (ID: {item.get('product_id')}) - Cantidad: {item.get('quantity')}\n"
        md += "\n"

    md += "## Totalización de productos (suma de todas las órdenes)\n\n"
    for producto_id, info in sorted(totales.items(), key=lambda x: x[1]["cantidad"], reverse=True):
        md += f"- {info['nombre']} (ID: {producto_id}) - Total: {info['cantidad']}\n"

    filename = f"reporte_pedidos_{timestamp}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(md)
    return filename


def main():
    print(f"🔄 Generando reporte de pedidos ({CONFIG['ventas_dias']} días)...")
    pedidos = obtener_pedidos()
    if not pedidos:
        print("⚠️  No se encontraron pedidos en el período.")
        return

    totales = totalizar_productos(pedidos)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = generar_reporte_pedidos(pedidos, totales, timestamp)
    print(f"\n✅ Reporte generado: {archivo}")


if __name__ == "__main__":
    main()
