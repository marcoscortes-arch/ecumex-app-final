from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import pandas as pd
import os

app = FastAPI(title="Ecumex - Buscador de Ventas")

# --- RUTAS SIMPLES PARA LA NUBE ---
CARPETA_FOTOS = "fotos"
CARPETA_TEMPLATES = "templates"
RUTA_CSV = "data/productos.csv"

app.mount("/fotos", StaticFiles(directory=CARPETA_FOTOS), name="fotos")
templates = Jinja2Templates(directory=CARPETA_TEMPLATES)

df_catalogo = pd.DataFrame()

if os.path.exists(RUTA_CSV):
    df_catalogo = pd.read_csv(RUTA_CSV)
    for col in ['codigo', 'descripcion', 'marca']:
        if col in df_catalogo.columns:
            df_catalogo[col] = df_catalogo[col].astype(str).fillna('')
    
    # TRUCO EXTRA: Extraer modelos comunes
    MODELOS_COMUNES = ["HILUX", "COROLLA", "YARIS", "RANGER", "SPARK", "AVEO", "DMAX", "BT50", "TUCSON", "RIO", "PICANTO", "LOGAN"]
    df_catalogo['modelo'] = 'GENERAL'
    
    for mod in MODELOS_COMUNES:
        df_catalogo.loc[df_catalogo['descripcion'].str.upper().str.contains(mod), 'modelo'] = mod

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/filtros")
async def obtener_filtros():
    if df_catalogo.empty:
        return JSONResponse({"marcas": [], "modelos": []})
    
    marcas = sorted(df_catalogo['marca'].unique().tolist())
    modelos = sorted([m for m in df_catalogo['modelo'].unique().tolist() if m != 'GENERAL'])
    
    return JSONResponse({"marcas": marcas, "modelos": modelos})

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
        
    resultados = df_filtrado.head(100).to_dict(orient="records")

    for item in resultados:
        item['imagen_url'] = f"/fotos/{item.get('imagen', 'no-image.png')}"
        try: precio = float(item.get('precio_venta', 0))
        except: precio = 0.0
            
        item['mensaje_wa'] = (
            f"Buen día, le saludamos de Ecumex. Le comparto la oferta del repuesto:\n\n"
            f"📌 *{item.get('descripcion', '')}*\n"
            f"🔹 Código: {item.get('codigo', '')}\n"
            f"💰 Precio: ${precio:.2f}\n"
            f"🚚 Envío: $10.00 (Servientrega, paga al recibir)\n\n"
            f"Quedo atento a su confirmación."
        )
        item['precio_venta'] = precio
        
    return JSONResponse(resultados)