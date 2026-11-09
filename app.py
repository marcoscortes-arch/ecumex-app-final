from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
import pandas as pd
import os

app = FastAPI(title="Ecumex - Buscador de Ventas")

# Rutas relativas
CARPETA_FOTOS = "fotos"
RUTA_CSV = "data/productos.csv"

# Montar fotos (si la carpeta existe)
if os.path.exists(CARPETA_FOTOS):
    app.mount("/fotos", StaticFiles(directory=CARPETA_FOTOS), name="fotos")

df_catalogo = pd.DataFrame()

if os.path.exists(RUTA_CSV):
    try:
        df_catalogo = pd.read_csv(RUTA_CSV)
        for col in ['codigo', 'descripcion', 'marca']:
            if col in df_catalogo.columns:
                df_catalogo[col] = df_catalogo[col].astype(str).fillna('')
        
        MODELOS_COMUNES = ["HILUX", "COROLLA", "YARIS", "RANGER", "SPARK", "AVEO", "DMAX", "BT50", "TUCSON", "RIO", "PICANTO", "LOGAN"]
        df_catalogo['modelo'] = 'GENERAL'
        
        for mod in MODELOS_COMUNES:
            df_catalogo.loc[df_catalogo['descripcion'].str.upper().str.contains(mod), 'modelo'] = mod
    except Exception as e:
        print(f"Error cargando CSV: {e}")

# --- LEER EL HTML DIRECTAMENTE DEL ARCHIVO ---
@app.get("/", response_class=HTMLResponse)
async def home():
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error cargando el HTML</h1><p>Detalle: {str(e)}</p>", status_code=500)

@app.get("/api/filtros")
async def obtener_filtros():
    if df_catalogo.empty:
        return JSONResponse({"marcas": [], "modelos": [], "categorias": []})
    
    marcas = sorted(df_catalogo['marca'].unique().tolist())
    modelos = sorted([m for m in df_catalogo['modelo'].unique().tolist() if m != 'GENERAL'])
    
    # Extraer categorías comunes
    CATEGORIAS_COMUNES = ["ARNES", "BALATA", "PASTILLA", "CREMALLERA", "TERMINAL", "ROTULA", "BUJIA", "BOMBA", "SENSOR", "FILTRO", "AMORTIGUADOR", "MANGUERA", "RODAMIENTO"]
    categorias = []
    for desc in df_catalogo['descripcion'].astype(str):
        for cat in CATEGORIAS_COMUNES:
            if cat in desc.upper() and cat not in categorias:
                categorias.append(cat)
    
    return JSONResponse({"marcas": marcas, "modelos": modelos, "categorias": sorted(categorias)})

@app.get("/api/buscar")
async def buscar(q: str = "", marca: str = "", modelo: str = ""):
    if df_catalogo.empty:
        return JSONResponse([])
        
    df_filtrado = df_catalogo.copy()
    
    if marca and marca != "TODAS":
        df_filtrado = df_filtrado[df_filtrado['marca'] == marca]
    if modelo and modelo != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['modelo'] == modelo]
        
    if q:
        mask = (
            df_filtrado['codigo'].str.contains(q, case=False, na=False) |
            df_filtrado['descripcion'].str.contains(q, case=False, na=False) |
            df_filtrado['marca'].str.contains(q, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
        
    # --- ORDEN ALFABÉTICO ---
    df_filtrado = df_filtrado.sort_values(by='descripcion', ascending=True)
    resultados = df_filtrado.head(100).to_dict(orient="records")

    for item in resultados:
        item['imagen_url'] = f"/fotos/{item.get('imagen', 'no-image.png')}"
        try: precio = float(item.get('precio_venta', 0))
        except: precio = 0.0
            
        # Limpiamos la descripción para que no muestre códigos mezclados del PDF
        desc_limpia = item.get('descripcion', '')
        if item.get('codigo') in desc_limpia:
            desc_limpia = desc_limpia.replace(item.get('codigo'), '').strip()
        if '/' in desc_limpia:
            desc_limpia = desc_limpia.split('/')[0].strip()
        if not desc_limpia:
            desc_limpia = "Repuesto " + item.get('modelo', 'General')

        item['mensaje_wa'] = (
            f"Buen día, le saludamos de Ecumex. Le comparto la oferta del repuesto:\n\n"
            f"📌 *{desc_limpia}*\n"
            f"🚘 *Vehículo:* {item.get('marca', '')} {item.get('modelo', '')}\n"
            f"🔹 Código: {item.get('codigo', '')}\n"
            f"💰 Precio: ${precio:.2f}\n"
            f"🚚 Envío: $10.00 (Servientrega, paga al recibir)\n\n"
            f"Quedo atento a su confirmación."
        )
        item['precio_venta'] = precio
        
    return JSONResponse(resultados)