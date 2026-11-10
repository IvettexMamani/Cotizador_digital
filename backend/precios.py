"""Precios que pagó el Estado por bienes similares (datos abiertos).

Fuente: órdenes de compra de Catálogos Electrónicos de Perú Compras
(https://catalogos.perucompras.gob.pe/ConsultaOrdenesPub). La exportación de
datos abiertos trae solo el total de cada orden; el precio por producto sale
del PDF de la orden. Se arma así:
    1. backend/descargar_ordenes.py baja una muestra pequeña de PDF a data/cache/.
    2. backend/ordenes_pdf.py los lee (OCR) y escribe data/precios_estado.csv.

El archivo limpio tiene solo los campos útiles, sin datos personales, con la
URL de origen y la fecha de consulta. precio_unitario está siempre con IGV.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from backend.cruce import normalizar

RAIZ = Path(__file__).resolve().parent.parent
PRECIOS_ESTADO = RAIZ / "data" / "precios_estado.csv"

COLUMNAS = ["fecha", "entidad", "descripcion", "unidad", "cantidad", "precio_unitario",
            "orden", "fuente", "fecha_consulta"]

# Palabras que no ayudan a buscar productos similares
PALABRAS_VACIAS = {"de", "del", "la", "el", "los", "las", "y", "o", "para", "con", "sin", "en",
                   "por", "a", "tamano", "tipo", "unidad", "x"}


def cargar_precios_estado(ruta: Path = PRECIOS_ESTADO) -> pd.DataFrame:
    """Devuelve los precios limpios, o una tabla vacía si todavía no hay datos."""
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS)
    df = pd.read_csv(ruta, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce")
    df["precio_unitario"] = pd.to_numeric(df["precio_unitario"], errors="coerce")
    return df.dropna(subset=["precio_unitario"])


def terminos_por_defecto(descripcion: str, maximo: int = 3) -> str:
    """Primeras palabras útiles de la descripción del ítem: 'Papel bond A4' -> 'papel bond a4'."""
    palabras = [p for p in re.findall(r"[a-z0-9]+", normalizar(descripcion)) if p not in PALABRAS_VACIAS]
    return " ".join(palabras[:maximo])


def buscar_precios(df: pd.DataFrame, terminos: str) -> pd.DataFrame:
    """Órdenes cuya descripción contiene todas las palabras buscadas (sin tildes ni mayúsculas)."""
    palabras = [p for p in re.findall(r"[a-z0-9]+", normalizar(terminos)) if p not in PALABRAS_VACIAS]
    if df.empty or not palabras:
        return df.iloc[0:0]
    descripciones = df["descripcion"].map(normalizar)
    mascara = pd.Series(True, index=df.index)
    for palabra in palabras:
        mascara &= descripciones.str.contains(rf"\b{re.escape(palabra)}", regex=True)
    return df[mascara]
