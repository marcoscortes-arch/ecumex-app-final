import fitz  # PyMuPDF
import os
import re
import pandas as pd

PDF_PATH = "catalogo.pdf"
CARPETA_FOTOS = "fotos"
CSV_PATH = "data/productos.csv"

MARCAS_MAP = {
    "TOYOTA": ["TOY", "TOYOTA"],
    "CHEVROLET": ["CHEV", "CHEVROLET"],
    "NISSAN": ["NISS", "NISSAN"],
    "HYUNDAI": ["HYUN", "HYUNDAI"],
    "KIA": ["KIA"],
    "MAZDA": ["MAZ", "MAZDA"],
    "FORD": ["FORD"],
    "VOLKSWAGEN": ["VW", "VOLKS", "VOLKSWAGEN"]
}

MODELOS_COMUNES = ["HILUX", "COROLLA", "YARIS", "RANGER", "SPARK", "AVEO", "DMAX", "BT50", "TUCSON", "RIO", "PICANTO", "LOGAN", "ELANTRA", "GETZ", "CRETA"]

def calcular_precio_venta(costo):
    if costo <= 0: return 0.0
    return round((costo * 1.15) / 0.70, 2)

def extraer_datos():
    os.makedirs("data", exist_ok=True)
    os.makedirs(CARPETA_FOTOS, exist_ok=True)
    
    doc = fitz.open(PDF_PATH)
    registros = []

    print(f"⏳ Procesando {len(doc)} páginas con precisión milimétrica...")
    
    for num_pagina, pagina in enumerate(doc):
        bloques = pagina.search_for("COD:")
        
        for bloque in bloques:
            # 1. Recortar la imagen (ajustado para que no agarre texto de otras columnas)
            rect_imagen = fitz.Rect(bloque.x0 - 190, bloque.y0 - 5, bloque.x0 - 5, bloque.y0 + 110)
            pix = pagina.get_pixmap(clip=rect_imagen, dpi=150)
            
            # 2. Extraer texto del bloque buscando el código exacto
            area_texto = fitz.Rect(bloque.x0 - 10, bloque.y0 - 5, bloque.x0 + 180, bloque.y0 + 140)
            texto_producto = pagina.get_text("text", clip=area_texto)
            
            # Si el texto no contiene el código que buscamos, lo ignoramos
            if "COD:" not in texto_producto:continue
            
            lineas = [l.strip() for l in texto_producto.split('\n') if l.strip()]
            if not lineas: continue
            
            # Extraer Código (Asegurándonos de que es el código correcto de la etiqueta negra)
            match_codigo = re.search(r'COD:\s*([A-Z0-9\-]+)', texto_producto)
            if not match_codigo: continue
            codigo = match_codigo.group(1).strip()
            
            # 4. Extraer Stock y Precio (Buscando en todo el texto del bloque)
            stock_match = re.search(r'STOCK\s+(\d+)', texto_producto)
            stock = int(stock_match.group(1)) if stock_match else 0
            
            precio_match = re.search(r'PRECIO\s+\$?([\d\.\,]+)', texto_producto)
            costo = 0.0
            if precio_match:
                costo_str = precio_match.group(1).replace(',', '')
                try: costo = float(costo_str)
                except: pass
            
            # 5. Extraer Descripción (Todo el texto entre el código y la palabra STOCK)
            desc_partes = texto_producto.split("STOCK")[0].replace(f"COD: {codigo}", "").strip()
            descripcion = " ".join(desc_partes.split())
            
            # 6. Detectar Marca y Modelo
            marca = "GENERAL"
            desc_upper = descripcion.upper()
            for m, abreviaturas in MARCAS_MAP.items():
                if any(ab in desc_upper for ab in abreviaturas):
                    marca = m
                    break
            
            modelo = "GENERAL"
            for mod in MODELOS_COMUNES:
                if mod in desc_upper:
                    modelo = mod
                    break
            
            nombre_imagen = f"{codigo}.png"
            ruta_img = os.path.join(CARPETA_FOTOS, nombre_imagen)
            
            if not os.path.exists(ruta_img):
                pix.save(ruta_img)
            
            registros.append({
                "codigo": codigo,
                "descripcion": descripcion,
                "marca": marca,
                "modelo": modelo,
                "stock": stock,
                "costo": costo,
                "precio_venta": calcular_precio_venta(costo),
                "imagen": nombre_imagen
            })

    # Guardar en CSV
    df = pd.DataFrame(registros)
    df.to_csv(CSV_PATH, index=False)
    print(f"\n✅ ¡Éxito! Se extrajeron {len(registros)} productos con sus datos exactos.")

if __name__ == "__main__":
    extraer_datos()