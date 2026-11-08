from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
import pandas as pd
import os

app = FastAPI(title="Ecumex - Buscador de Ventas")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARPETA_FOTOS = os.path.join(BASE_DIR, "fotos")
CARPETA_TEMPLATES = os.path.join(BASE_DIR, "templates")
RUTA_CSV = os.path.join(BASE_DIR, "data", "productos.csv")

app.mount("/fotos", StaticFiles(directory=CARPETA_FOTOS), name="fotos")
templates = Jinja2Templates(directory=CARPETA_TEMPLATES)

df_catalogo = pd.DataFrame()
if os.path.exists(RUTA_CSV):
    df_catalogo = pd.read_csv(RUTA_CSV)
    for col in ['codigo', 'descripcion', 'marca', 'modelo']:
        if col in df_catalogo.columns:
            df_catalogo[col] = df_catalogo[col].astype(str).fillna('')

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# NUEVA RUTA: Envía marcas y sus modelos agrupados
@app.get("/api/indice")
async def obtener_indice():
    if df_catalogo.empty:
        return JSONResponse({})
    
    indice = {}
    # Obtenemos todas las marcas únicas
    marcas = sorted(df_catalogo['marca'].unique().tolist())
    
    for m in marcas:
        if m == 'GENERAL': continue
        # Para cada marca, buscamos sus modelos únicos (ignorando GENERAL)
        modelos_marca = df_catalogo[df_catalogo['marca'] == m]['modelo'].unique().tolist()
        modelos_marca = sorted([mod for mod in modelos_marca if mod != 'GENERAL'])
        
        # Si la marca no tiene modelos específicos, ponemos uno genérico
        if not modelos_marca:
            modelos_marca = ["TODOS LOS MODELOS"]
            
        indice[m] = modelos_marca
        
    return JSONResponse(indice)

@app.get("/api/buscar")
async def buscar(q: str = "", marca: str = "", modelo: str = ""):
    if df_catalogo.empty:
        return JSONResponse([])
        
    df_filtrado = df_catalogo.copy()
    
    if marca and marca != "TODAS":
        df_filtrado = df_filtrado[df_filtrado['marca'] == marca]
        
    if modelo and modelo != "TODOS" and modelo != "TODOS LOS MODELOS":
        df_filtrado = df_filtrado[df_filtrado['modelo'] == modelo]
        
    if q:
        mask = (
            df_filtrado['codigo'].str.contains(q, case=False, na=False) |
            df_filtrado['descripcion'].str.contains(q, case=False, na=False)
        )
        df_filtrado = df_filtrado[mask]
        
    # Ordenamos alfabéticamente por defecto
    df_filtrado = df_filtrado.sort_values(by='descripcion')
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