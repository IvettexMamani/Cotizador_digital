"""Carga y valida el catálogo de productos del proveedor (CSV).

Formato largo: una fila por cada atributo técnico de cada producto, con su
propia fuente (URL o archivo de la ficha técnica). Los datos del producto
(nombre, costo, stock...) se repiten en cada fila del mismo `sku`.

En la app, el proveedor puede subir su catálogo (CSV o Excel) a partir de la
plantilla de plantilla_excel(); se usa solo durante su sesión. Si no sube
nada, se usa data/catalogo.csv (el catálogo real del proveedor) si existe; si
no, data/catalogo_ejemplo.csv.
"""

from __future__ import annotations

import io
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


# ---------------------------------------------------------------- catálogo subido en la app

EXTENSIONES_CATALOGO = (".csv", ".xlsx")

INSTRUCCIONES = {
    "sku": "Código único del producto. Se repite en todas las filas de ese producto.",
    "producto": "Nombre del producto.",
    "marca_modelo": "Marca y modelo, como figuran en la ficha técnica.",
    "categoria": "Palabras que aparecen en la descripción del ítem que pide la entidad "
                 "(ej.: 'papel bond', 'archivador'). Así se sabe con qué ítems se compara.",
    "unidad_venta": "Unidad en que lo vendes (Paquete, Unidad, Caja...).",
    "costo_unitario_soles": "Tu costo por unidad de venta, en soles y SIN IGV (la app lo agrega).",
    "stock": "Unidades disponibles.",
    "atributo": "Un dato técnico por fila (gramaje, tamaño, color...). Mejor con el mismo nombre "
                "que usan las solicitudes.",
    "valor": "El valor del dato (75, A4, blanco...).",
    "unidad": "Unidad del valor, si tiene (g/m2, cm, hojas). Vacío si no aplica.",
    "fuente": "De dónde sale el dato: enlace o nombre de la ficha técnica. "
              "Sin fuente, el dato queda en rojo (regla de oro).",
    "es_ejemplo": "'no' para tus productos. Borra las filas de ejemplo antes de subir el archivo.",
}

# Mismo orden de columnas que data/catalogo_ejemplo.csv: datos del producto, del atributo y es_ejemplo
ORDEN_PLANTILLA = COLUMNAS_PRODUCTO[:-1] + COLUMNAS_ATRIBUTO + ["es_ejemplo"]
_PRODUCTO_PLANTILLA = {"sku": "EJ-0001", "producto": "Archivador de palanca oficio (EJEMPLO)",
                       "marca_modelo": "Marca ficticia", "categoria": "archivador", "unidad_venta": "Unidad",
                       "costo_unitario_soles": "5.20", "stock": "100", "es_ejemplo": "si",
                       "fuente": "https://ejemplo.com/ficha-archivador.pdf"}
FILAS_PLANTILLA = [
    {**_PRODUCTO_PLANTILLA, "atributo": "ancho de lomo", "valor": "8", "unidad": "cm"},
    {**_PRODUCTO_PLANTILLA, "atributo": "tamaño", "valor": "oficio", "unidad": ""},
]


def plantilla_excel() -> bytes:
    """Plantilla para el proveedor: hoja 'catalogo' (2 filas de ejemplo) y hoja 'instrucciones'."""
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as libro:
        pd.DataFrame(FILAS_PLANTILLA, columns=ORDEN_PLANTILLA).to_excel(libro, sheet_name="catalogo", index=False)
        pd.DataFrame(list(INSTRUCCIONES.items()), columns=["columna", "qué poner"]).to_excel(
            libro, sheet_name="instrucciones", index=False)
    return salida.getvalue()


def leer_catalogo_subido(nombre_archivo: str, contenido: bytes) -> pd.DataFrame:
    """Lee el catálogo que sube el proveedor (CSV con , o ; o Excel .xlsx) y lo valida."""
    extension = Path(nombre_archivo).suffix.lower()
    try:
        if extension == ".xlsx":
            df = pd.read_excel(io.BytesIO(contenido), sheet_name=0, dtype=str, keep_default_na=False)
            # Excel guarda 75 como 75.0: se devuelve a 75
            df = df.apply(lambda col: col.str.replace(r"^(-?\d+)\.0$", r"\1", regex=True))
        elif extension == ".csv":
            try:
                texto = contenido.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = contenido.decode("latin-1")  # CSV guardado por Excel en Windows
            df = pd.read_csv(io.StringIO(texto), sep=None, engine="python", dtype=str, keep_default_na=False)
        else:
            raise ErrorCatalogo(f"Formato no admitido ({extension or 'sin extensión'}): sube un CSV o un Excel (.xlsx).")
    except ErrorCatalogo:
        raise
    except Exception as error:  # archivo dañado o que no es una tabla
        raise ErrorCatalogo(f"No se pudo leer el archivo: {error}") from error
    if df.empty:
        raise ErrorCatalogo("El catálogo no tiene filas.")
    df.columns = [str(c).strip().lower() for c in df.columns]
    return validar_catalogo(df)


def resumen_productos(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por producto, con su número de atributos."""
    productos = df.groupby("sku", sort=False)[COLUMNAS_PRODUCTO[1:]].first()
    productos["n_atributos"] = df.groupby("sku", sort=False).size()
    return productos.reset_index()
