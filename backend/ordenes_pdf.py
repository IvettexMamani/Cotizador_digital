"""Lee las órdenes de compra (PDF) bajadas con backend.descargar_ordenes y arma
data/precios_estado.csv: el precio unitario que pagó el Estado por cada producto.

Cómo funciona:
1. Texto de cada PDF con backend.lectura (pdfplumber u OCR si está escaneado).
   El texto se guarda en caché (data/cache/ordenes/<orden>.txt).
2. Cada línea de producto tiene: código, cantidad, unidad, descripción, precio
   unitario y total. Ejemplo (formato SIGA del MEF):
   "717200050224  100.  EMP X 500  PAPEL BOND ...  13.452000  1,345.20"
3. Una línea solo se acepta si cantidad × precio unitario = total. Así se
   descartan las líneas que el OCR leyó mal.
4. IGV: si la suma de las líneas es el total con IGV de la orden (aparecen en el
   documento el valor de venta = suma / 1,18 y el IGV), el precio incluye IGV.
   Si la suma es el valor de venta, se le agrega el 18 %. Si no se puede
   comprobar (por ejemplo, orden exonerada), la orden se descarta.

Solo se guardan: fecha, entidad (pública), descripción, unidad, cantidad,
precio unitario con IGV, orden, URL de origen y fecha de consulta. Ni
proveedores ni nombres de funcionarios.

Uso:
    python -m backend.ordenes_pdf
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.precios import COLUMNAS, PRECIOS_ESTADO

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "cache" / "ordenes"
INDICE = CARPETA / "indice.csv"

IGV = 0.18
_NUMERO = r"\d{1,3}(?:,\d{3})+(?:\.\d*)?|\d+(?:\.\d*)?"  # 1,582. / 1,345.20 / 13.452000
LINEA_ITEM = re.compile(
    rf"^(?P<codigo>\d{{8,14}})\s+(?P<cantidad>{_NUMERO})\s+(?P<resto>.+?)"
    rf"\s+(?P<unitario>{_NUMERO})\s+(?P<total>{_NUMERO})\s*$"
)
# Unidades de medida del catálogo SIGA, por si el OCR las pega a la descripción
UNIDAD_AL_INICIO = re.compile(
    r"^(?P<unidad>(?:UNIDAD|CIENTO|MILLAR|DOCENA|CAJA|PAQUETE|EMP|JUEGO|ROLLO|BOLSA|BLISTER|PAR|"
    r"RESMA|KIT|FRASCO|GALON|LITRO|SOBRE|PLIEGO)(?:\s+X\s+\d+)?)\s+(?P<descripcion>.+)$"
)


@dataclass
class LineaOrden:
    descripcion: str
    unidad: str
    cantidad: float
    precio_unitario: float
    total: float


def a_numero(texto: str) -> float:
    """'1,345.20' -> 1345.2 ; '100.' -> 100.0 (coma de miles, punto decimal)."""
    return float(texto.replace(",", ""))


def _cuadra(a: float, b: float) -> bool:
    return abs(a - b) <= max(0.05, 0.001 * abs(b))


def extraer_lineas(texto: str) -> list[LineaOrden]:
    """Líneas de producto cuyo cantidad × precio unitario coincide con el total."""
    lineas = []
    for renglon in texto.splitlines():
        m = LINEA_ITEM.match(renglon.strip())
        if not m:
            continue
        cantidad, unitario, total = (a_numero(m[k]) for k in ("cantidad", "unitario", "total"))
        if cantidad <= 0 or not _cuadra(cantidad * unitario, total):
            continue
        lineas.append(LineaOrden(*_separar_unidad(m["resto"]), cantidad, unitario, total))
    return lineas


def _separar_unidad(resto: str) -> tuple[str, str]:
    """'EMP X 500  PAPEL BOND ...' -> ('PAPEL BOND ...', 'EMP X 500')."""
    partes = re.split(r"\s{2,}", resto.strip())
    if len(partes) > 1:
        unidad, descripcion = partes[0], " ".join(partes[1:])
    else:
        m = UNIDAD_AL_INICIO.match(partes[0])
        unidad, descripcion = (m["unidad"], m["descripcion"]) if m else ("", partes[0])
    return descripcion.strip(" -"), unidad.strip()


def estado_igv(texto: str, suma_lineas: float) -> str:
    """'incluido', 'no incluido' o 'sin verificar', según los montos de la orden."""
    numeros = [a_numero(n) for n in re.findall(_NUMERO, texto) if "." in n]
    def aparece(valor: float) -> bool:
        return any(_cuadra(n, valor) for n in numeros)

    venta = suma_lineas / (1 + IGV)
    if aparece(venta) and aparece(suma_lineas - venta):
        return "incluido"
    if aparece(suma_lineas * (1 + IGV)) and aparece(suma_lineas * IGV):
        return "no incluido"
    return "sin verificar"


def leer_texto(pdf: Path) -> str:
    """Texto del PDF, con caché en un .txt al lado (el OCR tarda unos segundos por página)."""
    cache = pdf.with_suffix(".txt")
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    from backend.lectura import leer_pdf

    texto = leer_pdf(pdf.read_bytes()).texto
    cache.write_text(texto, encoding="utf-8")
    return texto


def _fecha_iso(fecha: str) -> str:
    try:
        return datetime.strptime(fecha.split()[0], "%d/%m/%Y").date().isoformat()
    except (ValueError, IndexError):
        return ""


def construir_precios(indice: pd.DataFrame, carpeta: Path = CARPETA) -> tuple[pd.DataFrame, list[str]]:
    """Recorre las órdenes del índice y devuelve la tabla limpia y un informe."""
    filas, informe = [], []
    for orden in indice[indice["archivo"] != ""].itertuples(index=False):
        texto = leer_texto(carpeta / orden.archivo)
        lineas = extraer_lineas(texto)
        if not lineas:
            informe.append(f"{orden.orden}: sin líneas legibles (formato distinto o el OCR no cuadró)")
            continue
        igv = estado_igv(texto, sum(l.total for l in lineas))
        if igv == "sin verificar":
            informe.append(f"{orden.orden}: {len(lineas)} líneas, pero no se pudo comprobar el IGV; se descarta")
            continue
        factor = 1 + IGV if igv == "no incluido" else 1.0
        for linea in lineas:
            filas.append({
                "fecha": _fecha_iso(orden.fecha_publicacion),
                "entidad": orden.entidad,
                "descripcion": linea.descripcion,
                "unidad": linea.unidad,
                "cantidad": linea.cantidad,
                "precio_unitario": round(linea.precio_unitario * factor, 4),
                "orden": orden.orden,
                "fuente": orden.fuente,
                "fecha_consulta": orden.fecha_consulta,
            })
        informe.append(f"{orden.orden}: {len(lineas)} líneas (IGV {igv})")
    return pd.DataFrame(filas, columns=COLUMNAS), informe


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    indice = pd.read_csv(INDICE, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    precios, informe = construir_precios(indice)
    print("\n".join(informe))
    precios.to_csv(PRECIOS_ESTADO, index=False, encoding="utf-8-sig")
    print(f"\n{len(precios)} precios de {precios['orden'].nunique()} órdenes -> "
          f"{PRECIOS_ESTADO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
