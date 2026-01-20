# main.py - Código completo con soporte de visitas
import pandas as pd
from datetime import datetime, timedelta
import json
import time

from config import CONFIG, wcapi

# ============================================
# CONFIGURACIÓN
# ============================================

# ============================================
# FUNCIONES DE EXTRACCIÓN
# ============================================
def extraer_productos():
    """Obtiene todos los productos con sus datos relevantes + visitas"""
    productos = []
    page = 1
    max_reintentos = CONFIG["max_reintentos"]
    
    while True:
        reintentos = 0
        while reintentos < max_reintentos:
            try:
                print(f"📄 Extrayendo página {page}...", end=" ")
                response = wcapi.get(
                    "products",
                    params={"per_page": CONFIG["per_page"], "page": page},
                )
                
                if response.status_code != 200:
                    print(f"❌ Error: {response.status_code}")
                    return pd.DataFrame(productos)
                
                # Limpiar warnings de PHP
                text = response.text
                json_start = text.find('[')
                if json_start == -1:
                    print(f"❌ No JSON")
                    return pd.DataFrame(productos)
                
                clean_json = text[json_start:]
                data = json.loads(clean_json)
                
                if not isinstance(data, list):
                    print(f"❌ Respuesta inesperada")
                    return pd.DataFrame(productos)
                
                if not data:
                    print("✅ Fin de productos")
                    break
                    
                for producto in data:
                    # Buscar visitas en meta_data (Post Views Counter)
                    visitas = 0
                    for meta in producto.get('meta_data', []):
                        # Post Views Counter guarda con esta clave
                        if meta['key'] in CONFIG["visitas_meta_keys"]:
                            try:
                                visitas = int(meta['value'])
                                break
                            except:
                                pass
                    
                    productos.append({
                        'id': producto['id'],
                        'nombre': producto['name'],
                        'sku': producto['sku'],
                        'precio_actual': producto['regular_price'],
                        'precio_oferta': producto['sale_price'],
                        'stock': producto['stock_quantity'],
                        'categorias': [cat['name'] for cat in producto['categories']],
                        'fecha_creacion': producto['date_created'],
                        'visitas': visitas
                    })
                
                print(f"✅ {len(data)} productos")
                page += 1
                time.sleep(CONFIG["sleep_between_pages"])
                break
                
            except Exception as e:
                reintentos += 1
                print(f"⚠️ Intento {reintentos}/{max_reintentos} falló: {str(e)[:50]}...")
                if reintentos < max_reintentos:
                    print(f"   Esperando {CONFIG['retry_sleep_seconds']} segundos...")
                    time.sleep(CONFIG["retry_sleep_seconds"])
                else:
                    print(f"❌ Error en página {page}")
                    return pd.DataFrame(productos)
        
        if not data:
            break
    
    print(f"\n📦 Total productos extraídos: {len(productos)}")
    return pd.DataFrame(productos)

def extraer_ventas(dias=None):
    """Obtiene órdenes de los últimos X días - TODOS los estados que representan ventas"""
    if dias is None:
        dias = CONFIG["ventas_dias"]
    fecha_desde = (datetime.now() - timedelta(days=dias)).isoformat()
    
    # Estados que representan ventas reales
    estados_validos = CONFIG["estados_validos"]
    
    ventas = []
    
    for estado in estados_validos:
        print(f"\n📊 Extrayendo órdenes con estado: {estado}")
        page = 1
        max_reintentos = CONFIG["max_reintentos"]
        
        while True:
            reintentos = 0
            while reintentos < max_reintentos:
                try:
                    print(f"   Página {page}...", end=" ")
                    response = wcapi.get("orders", params={
                        "per_page": CONFIG["per_page"],
                        "page": page,
                        "after": fecha_desde,
                        "status": estado
                    })
                    
                    if response.status_code != 200:
                        print(f"❌ Error: {response.status_code}")
                        break
                    
                    # Limpiar warnings de PHP
                    text = response.text
                    json_start = text.find('[')
                    if json_start == -1:
                        print(f"❌ No JSON")
                        break
                    
                    clean_json = text[json_start:]
                    data = json.loads(clean_json)
                    
                    if not isinstance(data, list) or not data:
                        print("✅ Fin")
                        break
                        
                    for orden in data:
                        for item in orden['line_items']:
                            ventas.append({
                                'producto_id': item['product_id'],
                                'nombre': item['name'],
                                'cantidad': item['quantity'],
                                'precio_venta': float(item['price']),
                                'total': float(item['total']),
                                'fecha': orden['date_created'],
                                'orden_id': orden['id'],
                                'estado': orden['status']
                            })
                    
                    print(f"✅ {len(data)} órdenes")
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
    
    print(f"\n🛒 Total ventas extraídas: {len(ventas)}")
    return pd.DataFrame(ventas)

# ============================================
# FUNCIONES DE ANÁLISIS
# ============================================
def analizar_datos(df_productos, df_ventas):
    """Procesa y cruza datos - incluye volumen, facturación Y visitas"""
    
    # Ventas por producto
    if not df_ventas.empty:
        ventas_por_producto = df_ventas.groupby('producto_id').agg({
            'cantidad': 'sum',
            'total': 'sum',
            'orden_id': 'count'
        }).rename(columns={'orden_id': 'num_ordenes'})
    else:
        ventas_por_producto = pd.DataFrame(columns=['cantidad', 'total', 'num_ordenes'])
    
    # Merge con productos
    analisis = df_productos.merge(
        ventas_por_producto, 
        left_on='id', 
        right_index=True, 
        how='left'
    )
    
    # Calcular métricas básicas
    analisis['cantidad'] = analisis['cantidad'].fillna(0)
    analisis['total_vendido'] = analisis['total'].fillna(0)
    analisis['num_ordenes'] = analisis['num_ordenes'].fillna(0)
    analisis['visitas'] = analisis['visitas'].fillna(0)
    
    analisis['precio_promedio_venta'] = (
        analisis['total_vendido'] / analisis['cantidad']
    ).fillna(0)
    
    periodo_dias = CONFIG["ventas_dias"]
    analisis['rotacion_dias'] = analisis['cantidad'] / periodo_dias  # ventas por día
    analisis['facturacion_dia'] = analisis['total_vendido'] / periodo_dias  # $ por día
    analisis['visitas_dia'] = analisis['visitas'] / periodo_dias  # visitas por día
    
    # Convertir precio_actual a numérico
    analisis['precio_actual'] = pd.to_numeric(analisis['precio_actual'], errors='coerce').fillna(0)
    analisis['stock'] = pd.to_numeric(analisis['stock'], errors='coerce').fillna(0)
    
    # Métricas de conversión
    analisis['tasa_conversion'] = (
        (analisis['cantidad'] / analisis['visitas'].replace(0, 1)) * 100
    ).fillna(0)
    
    # Donde no hay visitas, poner NaN en vez de 0 para distinguir
    analisis.loc[analisis['visitas'] == 0, 'tasa_conversion'] = float('nan')
    
    # Calcular margen de beneficio
    analisis['diferencia_precio'] = analisis['precio_promedio_venta'] - analisis['precio_actual']
    analisis['margen_porcentaje'] = (
        (analisis['diferencia_precio'] / analisis['precio_actual'].replace(0, 1)) * 100
    ).fillna(0)
    
    # Clasificar por VOLUMEN
    analisis['categoria_volumen'] = pd.cut(
        analisis['cantidad'], 
        bins=[-0.1, 0, 1, 10, 50, float('inf')],
        labels=['Sin ventas', 'Muy baja', 'Venta baja', 'Venta media', 'Bestseller Volumen']
    )
    
    # Clasificar por FACTURACIÓN (corregido para evitar bins iguales)
    if analisis['total_vendido'].max() > 0:
        percentiles = analisis[analisis['total_vendido'] > 0]['total_vendido'].quantile([0.25, 0.5, 0.75]).values
        
        # Asegurar que los bins sean monotónicamente crecientes
        bins_fact = [0]
        ultima = 0
        for p in percentiles:
            if p > ultima:
                bins_fact.append(p)
                ultima = p
        bins_fact.append(float('inf'))
        
        # Crear etiquetas según cantidad de bins
        labels_fact = ['Sin ingresos', 'Facturación baja', 'Facturación media', 'Facturación alta', 'Top Facturador']
        labels_fact = labels_fact[:len(bins_fact)-1]
        
        analisis['categoria_facturacion'] = pd.cut(
            analisis['total_vendido'],
            bins=bins_fact,
            labels=labels_fact,
            duplicates='drop'
        )
    else:
        analisis['categoria_facturacion'] = 'Sin ingresos'
    
    # Clasificar por VISITAS
    if analisis['visitas'].max() > 0:
        percentiles_vis = analisis[analisis['visitas'] > 0]['visitas'].quantile([0.33, 0.66]).values
        
        bins_vis = [0]
        ultima = 0
        for p in percentiles_vis:
            if p > ultima:
                bins_vis.append(p)
                ultima = p
        bins_vis.append(float('inf'))
        
        labels_vis = ['Sin visitas', 'Pocas visitas', 'Visitas medias', 'Muchas visitas']
        labels_vis = labels_vis[:len(bins_vis)-1]
        
        analisis['categoria_visitas'] = pd.cut(
            analisis['visitas'],
            bins=bins_vis,
            labels=labels_vis,
            duplicates='drop'
        )
    else:
        analisis['categoria_visitas'] = 'Sin visitas'
    
    # Flags especiales
    analisis['sin_visitas'] = analisis['visitas'] == 0
    analisis['sin_visitas_con_stock'] = (
        (analisis['visitas'] == 0) & (analisis['stock'] > CONFIG["stock_minimo_sin_visitas"])
    )
    analisis['muchas_visitas_sin_ventas'] = (
        (analisis['visitas'] > CONFIG["visitas_muchas_sin_ventas"]) & (analisis['cantidad'] == 0)
    )
    analisis['baja_conversion'] = (
        (analisis['visitas'] > CONFIG["visitas_baja_conversion"])
        & (analisis['tasa_conversion'] < CONFIG["conversion_baja_pct"])
    )
    analisis['alta_conversion'] = (
        (analisis['visitas'] > CONFIG["visitas_alta_conversion"])
        & (analisis['tasa_conversion'] > CONFIG["conversion_alta_pct"])
    )
    
    # Valor del stock
    analisis['valor_stock'] = analisis['precio_actual'] * analisis['stock']
    
    return analisis

def generar_reporte_para_claude(analisis):
    """Genera reporte estructurado - incluye volumen, facturación Y visitas"""
    
    reporte = {
        "fecha_analisis": datetime.now().isoformat(),
        "periodo_analizado": f"últimos {CONFIG['ventas_dias']} días",
        "resumen": {
            "total_productos": int(len(analisis)),
            "productos_sin_ventas": int(len(analisis[analisis['cantidad'] == 0])),
            "productos_sin_visitas": int(len(analisis[analisis['visitas'] == 0])),
            "productos_sin_visitas_con_stock": int(len(analisis[analisis['sin_visitas_con_stock'] == True])),
            "productos_bestseller_volumen": int(len(analisis[analisis['categoria_volumen'] == 'Bestseller Volumen'])),
            "productos_top_facturadores": int(len(analisis[analisis['categoria_facturacion'] == 'Top Facturador'])),
            "ingreso_total": float(analisis['total_vendido'].sum()),
            "unidades_vendidas_total": int(analisis['cantidad'].sum()),
            "visitas_totales": int(analisis['visitas'].sum()),
            "tasa_conversion_promedio": float(analisis[analisis['tasa_conversion'].notna()]['tasa_conversion'].mean()) if len(analisis[analisis['tasa_conversion'].notna()]) > 0 else 0,
            "ticket_promedio": float(analisis['total_vendido'].sum() / len(analisis[analisis['cantidad'] > 0])) if len(analisis[analisis['cantidad'] > 0]) > 0 else 0
        },
        "productos_problematicos": [],
        "productos_sin_visitas_stock_alto": [],
        "muchas_visitas_sin_ventas": [],
        "baja_conversion": [],
        "alta_conversion": [],
        "bestsellers_volumen": [],
        "top_facturadores": [],
        "oportunidades_precio": [],
        "productos_detalle": []
    }
    
    # Productos sin ventas con stock alto
    sin_ventas = analisis[
        (analisis['cantidad'] == 0) & (analisis['stock'] > 5)
    ].sort_values('valor_stock', ascending=False).head(30).to_dict('records')
    reporte['productos_problematicos'] = sin_ventas
    
    # Productos sin visitas con stock alto
    sin_visitas_stock = analisis[
        analisis['sin_visitas_con_stock'] == True
    ].sort_values('valor_stock', ascending=False).head(30).to_dict('records')
    reporte['productos_sin_visitas_stock_alto'] = sin_visitas_stock
    
    # Productos con muchas visitas pero sin ventas
    visitas_sin_ventas = analisis[
        analisis['muchas_visitas_sin_ventas'] == True
    ].sort_values('visitas', ascending=False).head(20).to_dict('records')
    reporte['muchas_visitas_sin_ventas'] = visitas_sin_ventas
    
    # Productos con baja conversión
    baja_conv = analisis[
        analisis['baja_conversion'] == True
    ].sort_values('visitas', ascending=False).head(20).to_dict('records')
    reporte['baja_conversion'] = baja_conv
    
    # Productos con alta conversión
    alta_conv = analisis[
        analisis['alta_conversion'] == True
    ].sort_values('tasa_conversion', ascending=False).head(20).to_dict('records')
    reporte['alta_conversion'] = alta_conv
    
    # Bestsellers por VOLUMEN
    bestsellers_vol = analisis[
        analisis['categoria_volumen'] == 'Bestseller Volumen'
    ].sort_values('cantidad', ascending=False).head(30).to_dict('records')
    reporte['bestsellers_volumen'] = bestsellers_vol
    
    # Top FACTURADORES
    top_fact = analisis[
        analisis['total_vendido'] > 0
    ].sort_values('total_vendido', ascending=False).head(30).to_dict('records')
    reporte['top_facturadores'] = top_fact
    
    # Oportunidades de ajuste de precio
    oportunidades = analisis[
        (analisis['cantidad'] > CONFIG["min_ventas_oportunidad_precio"]) &
        (analisis['precio_promedio_venta'] > 0) &
        (
            analisis['diferencia_precio'].abs()
            > analisis['precio_actual'] * CONFIG["umbral_diferencia_precio_pct"]
        )
    ].sort_values('cantidad', ascending=False).head(20).to_dict('records')
    reporte['oportunidades_precio'] = oportunidades
    
    # Todos los productos con métricas
    reporte['productos_detalle'] = analisis.to_dict('records')
    
    return reporte

def generar_markdown(reporte, timestamp):
    """Genera reporte en formato Markdown para fácil lectura"""
    md = f"""# Reporte de Análisis de Precios
    
**Fecha:** {reporte['fecha_analisis']}
**Período:** {reporte['periodo_analizado']}

## 📊 Resumen Ejecutivo

- Total productos: {reporte['resumen']['total_productos']}
- Sin ventas: {reporte['resumen']['productos_sin_ventas']}
- Sin visitas: {reporte['resumen']['productos_sin_visitas']}
- Sin visitas con stock alto: {reporte['resumen']['productos_sin_visitas_con_stock']}
- Bestsellers por volumen: {reporte['resumen']['productos_bestseller_volumen']}
- Top facturadores: {reporte['resumen']['productos_top_facturadores']}
- Ingreso total: ${reporte['resumen']['ingreso_total']:,.2f}
- Unidades vendidas: {reporte['resumen']['unidades_vendidas_total']:,}
- Visitas totales: {reporte['resumen']['visitas_totales']:,}
- Tasa conversión promedio: {reporte['resumen']['tasa_conversion_promedio']:.2f}%
- Ticket promedio: ${reporte['resumen']['ticket_promedio']:,.2f}

## 🚫 Productos SIN VISITAS con Stock Alto (urgente)

"""
    for p in reporte['productos_sin_visitas_stock_alto'][:10]:
        md += f"- **{p['nombre']}** (SKU: {p['sku']})\n"
        md += f"  - Precio: ${p['precio_actual']} | Stock: {int(p['stock'])} | Valor: ${p.get('valor_stock', 0):,.0f}\n"
        md += f"  - Visitas: {int(p['visitas'])} | Ventas: {int(p['cantidad'])}\n"
    
    md += "\n## 👀 Productos con MUCHAS VISITAS pero SIN VENTAS\n\n"
    for p in reporte['muchas_visitas_sin_ventas'][:10]:
        md += f"- **{p['nombre']}** - {int(p['visitas'])} visitas, 0 ventas\n"
        md += f"  - Precio: ${p['precio_actual']} | Stock: {int(p['stock'])}\n"
    
    md += "\n## ⚠️ Productos con BAJA CONVERSIÓN (visitas pero pocas ventas)\n\n"
    for p in reporte['baja_conversion'][:10]:
        md += f"- **{p['nombre']}** - Conversión: {p['tasa_conversion']:.2f}%\n"
        md += f"  - Visitas: {int(p['visitas'])} | Ventas: {int(p['cantidad'])} | Precio: ${p['precio_actual']}\n"
    
    md += "\n## ✅ Productos con ALTA CONVERSIÓN (éxitos)\n\n"
    for p in reporte['alta_conversion'][:10]:
        md += f"- **{p['nombre']}** - Conversión: {p['tasa_conversion']:.2f}%\n"
        md += f"  - Visitas: {int(p['visitas'])} | Ventas: {int(p['cantidad'])} | Ingresos: ${p['total_vendido']:,.0f}\n"
    
    md += "\n## 💰 Top 10 Facturadores (más ingresos)\n\n"
    for i, p in enumerate(reporte['top_facturadores'][:10], 1):
        md += f"{i}. **{p['nombre']}** - ${p['total_vendido']:,.0f}\n"
        md += f"   - {int(p['cantidad'])} unidades | {int(p['visitas'])} visitas | Conv: {p['tasa_conversion']:.1f}%\n"
    
    md += "\n## 📦 Top 10 por Volumen (más unidades)\n\n"
    for i, p in enumerate(reporte['bestsellers_volumen'][:10], 1):
        md += f"{i}. **{p['nombre']}** - {int(p['cantidad'])} unidades\n"
        md += f"   - ${p['total_vendido']:,.0f} | {int(p['visitas'])} visitas | Conv: {p['tasa_conversion']:.1f}%\n"
    
    with open(f'reporte_legible_{timestamp}.md', 'w', encoding='utf-8') as f:
        f.write(md)

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================
def main():
    print("🔄 Extrayendo productos...")
    df_productos = extraer_productos()
    
    if df_productos.empty:
        print("⚠️  No se pudieron extraer productos.")
        return
    
    print(f"\n📊 Productos con visitas: {len(df_productos[df_productos['visitas'] > 0])}")
    print(f"📊 Productos sin visitas: {len(df_productos[df_productos['visitas'] == 0])}")
    
    print(f"\n📊 Extrayendo ventas ({CONFIG['ventas_dias']} días)...")
    df_ventas = extraer_ventas(dias=CONFIG["ventas_dias"])
    
    if df_ventas.empty:
        print("⚠️  No hay ventas en el período. Generando reporte solo con productos...")
        df_ventas = pd.DataFrame(columns=['producto_id', 'cantidad', 'total', 'orden_id', 'estado'])
    
    print("\n🧮 Analizando datos...")
    analisis = analizar_datos(df_productos, df_ventas)
    
    print("\n📝 Generando reporte...")
    reporte = generar_reporte_para_claude(analisis)
    
    # Guardar en diferentes formatos
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # JSON para Claude/Ollama
    with open(f'reporte_precios_{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)
    
    # CSV para Excel
    analisis.to_csv(f'analisis_productos_{timestamp}.csv', index=False)
    
    # Markdown legible
    generar_markdown(reporte, timestamp)
    
    print(f"\n✅ Reportes generados:")
    print(f"   - reporte_precios_{timestamp}.json")
    print(f"   - analisis_productos_{timestamp}.csv")
    print(f"   - reporte_legible_{timestamp}.md")

if __name__ == "__main__":
    main()
