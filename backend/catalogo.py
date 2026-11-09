"""Carga y valida el catálogo de productos del proveedor (CSV).

Formato largo: una fila por cada atributo técnico de cada producto, con su
propia fuente (URL o archivo de la ficha técnica). Los datos del producto
(nombre, costo, stock...) se repiten en cada fila del mismo `sku`.

Se usa data/catalogo.csv (el catálogo real del proveedor) si existe; si no,
data/catalogo_ejemplo.csv.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO_REAL = RAIZ / "data" / "catalogo.csv"
CATALOGO_EJEMPLO = RAIZ / "data" / "catalogo_ejemplo.csv"

COLUMNAS_PRODUCTO = ["sku", "producto", "marca_modelo", "categoria", "unidad_venta",
                     "costo_unitario_soles", "stock", "es_ejemplo"]
COLUMNAS_ATRIBUTO = ["atributo", "valor", "unidad", "fuente"]
COLUMNAS = COLUMNAS_PRODUCTO + COLUMNAS_ATRIBUTO


class ErrorCatalogo(ValueError):
    """El CSV del catálogo no tiene el formato esperado."""


def ruta_catalogo() -> Path:
    return CATALOGO_REAL if CATALOGO_REAL.exists() else CATALOGO_EJEMPLO


def _a_numero(serie: pd.Series) -> pd.Series:
    # Acepta "14.50" y "14,50" (Excel en español)
    return pd.to_numeric(serie.str.strip().str.replace(",", ".", regex=False), errors="coerce")


def validar_catalogo(df: pd.DataFrame) -> pd.DataFrame:
    faltantes = [c for c in COLUMNAS if c not in df.columns]
    if faltantes:
        raise ErrorCatalogo(f"Al catálogo le faltan las columnas: {', '.join(faltantes)}.")

    df = df[COLUMNAS].copy()
    for columna in COLUMNAS:
        df[columna] = df[columna].astype(str).str.strip()

    # Fila 2 = primera fila de datos en Excel (la 1 es el encabezado)
    vacias = df[(df["sku"] == "") | (df["producto"] == "") | (df["atributo"] == "") | (df["valor"] == "")]
    if not vacias.empty:
        filas = ", ".join(str(i + 2) for i in vacias.index[:10])
        raise ErrorCatalogo(f"Hay filas sin sku, producto, atributo o valor (filas {filas}).")

    df["costo_unitario_soles"] = _a_numero(df["costo_unitario_soles"])
    df["stock"] = _a_numero(df["stock"])
    malas = df[df["costo_unitario_soles"].isna() | df["stock"].isna()]
    if not malas.empty:
        filas = ", ".join(str(i + 2) for i in malas.index[:10])
        raise ErrorCatalogo(f"Costo o stock no numérico en las filas {filas}.")

    # Los datos del producto deben ser iguales en todas sus filas
    datos = [c for c in COLUMNAS_PRODUCTO if c != "sku"]
    inconsistentes = [sku for sku, grupo in df.groupby("sku") if (grupo[datos].nunique() > 1).any()]
    if inconsistentes:
        raise ErrorCatalogo(
            "Estos productos tienen nombre, costo o stock distintos entre sus filas: "
            + ", ".join(inconsistentes[:10]) + "."
        )
    return df


def cargar_catalogo(ruta: Path | None = None) -> pd.DataFrame:
    ruta = ruta or ruta_catalogo()
    # sep=None detecta si el separador es coma o punto y coma; utf-8-sig tolera el BOM de Excel
    df = pd.read_csv(ruta, sep=None, engine="python", dtype=str, keep_default_na=False,
                     encoding="utf-8-sig")
    return validar_catalogo(df)


def resumen_productos(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por producto, con su número de atributos."""
    productos = df.groupby("sku", sort=False)[COLUMNAS_PRODUCTO[1:]].first()
    productos["n_atributos"] = df.groupby("sku", sort=False).size()
    return productos.reset_index()
