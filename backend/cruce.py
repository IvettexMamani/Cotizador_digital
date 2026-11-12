"""Paso 4 del flujo: cruzar los requisitos de la solicitud con el catálogo.

Para cada ítem se buscan los productos de la misma categoría y, por cada
requisito técnico, se decide:

- "cumple":    el dato del producto satisface lo exigido y tiene fuente.
- "revisar":   no se puede afirmar que cumple (falta el dato, falta la fuente,
               unidades distintas, coincidencia parcial...). Se muestra en rojo.
- "no cumple": el dato del producto contradice lo exigido.

Regla de oro: un dato sin fuente nunca queda como "cumple".

Los productos se ordenan por estado (cumple > revisar > no cumple), luego por
disponibilidad (stock suficiente primero) y luego por menor costo, que para un
mismo precio de venta significa mayor margen.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

from ai.esquemas import Item, RequisitoTecnico, SolicitudCotizacion

CUMPLE, REVISAR, NO_CUMPLE = "cumple", "revisar", "no cumple"
ORDEN_ESTADO = {CUMPLE: 0, REVISAR: 1, NO_CUMPLE: 2}
SIMBOLOS = {">=": "≥", "<=": "≤", "=": "=", ">": ">", "<": "<", "incluye": "incluye"}

# Conversiones simples: unidad -> (magnitud, factor a la unidad base)
CONVERSIONES = {
    "mm": ("longitud", 0.1), "cm": ("longitud", 1.0), "m": ("longitud", 100.0),
    "g": ("masa", 1.0), "kg": ("masa", 1000.0),
    "ml": ("volumen", 1.0), "l": ("volumen", 1000.0),
}
SIMILITUD_MINIMA = 0.8  # para asociar nombres de atributo parecidos

# El gramaje del papel es masa por área (g/m2), pero en los TDR y en los empaques se abrevia
# «papel bond 80 g» o «80 gr». Solo en el atributo gramaje esas unidades se leen como g/m2.
UNIDADES_GRAMAJE = {"g", "gr", "grs", "gramos", "g/m2", "gr/m2", "grs/m2", "gsm"}


# ---------------------------------------------------------------- normalización

def normalizar(texto: str | None) -> str:
    """Minúsculas, sin tildes, sin espacios repetidos ni puntuación al final."""
    if not texto:
        return ""
    sin_tildes = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip(" .,;:")


def normalizar_unidad(unidad: str | None) -> str:
    return normalizar((unidad or "").replace("²", "2").replace("³", "3")).replace(" ", "")


def separar_numero(texto: str | None) -> tuple[float | None, str]:
    """'75' -> (75.0, ''); '8 cm' -> (8.0, 'cm'); 'A4' -> (None, '')."""
    coincidencia = re.fullmatch(r"\s*(-?\d+(?:[.,]\d+)?)\s*([^\d\s].*)?", str(texto or ""))
    if not coincidencia:
        return None, ""
    return float(coincidencia.group(1).replace(",", ".")), (coincidencia.group(2) or "").strip()


def convertir(valor: float, desde: str, hacia: str) -> float | None:
    desde, hacia = normalizar_unidad(desde), normalizar_unidad(hacia)
    if desde == hacia:
        return valor
    if desde in CONVERSIONES and hacia in CONVERSIONES:
        (magnitud_a, factor_a), (magnitud_b, factor_b) = CONVERSIONES[desde], CONVERSIONES[hacia]
        if magnitud_a == magnitud_b:
            return valor * factor_a / factor_b
    return None


def texto_valor(valor: str, unidad: str | None) -> str:
    return f"{valor} {unidad}".strip() if unidad else str(valor)


# ---------------------------------------------------------------- resultados

@dataclass
class ResultadoRequisito:
    atributo: str
    exigido: str
    ofrecido: str | None
    fuente: str | None
    estado: str
    motivo: str
    texto_solicitud: str  # cita de la solicitud de donde sale el requisito


@dataclass
class EvaluacionProducto:
    sku: str
    producto: str
    marca_modelo: str
    unidad_venta: str
    costo_unitario: float
    stock: float
    stock_suficiente: bool
    es_ejemplo: bool
    resultados: list[ResultadoRequisito] = field(default_factory=list)

    def contar(self, estado: str) -> int:
        return sum(r.estado == estado for r in self.resultados)

    @property
    def estado(self) -> str:
        if not self.resultados:
            return REVISAR  # sin requisitos, no hay nada que garantice que es el producto pedido
        return max((r.estado for r in self.resultados), key=ORDEN_ESTADO.get)


@dataclass
class ResultadoItem:
    item: Item
    evaluaciones: list[EvaluacionProducto]  # ya ordenadas

    @property
    def aptas(self) -> list[EvaluacionProducto]:
        return [e for e in self.evaluaciones if e.estado != NO_CUMPLE]

    @property
    def recomendado(self) -> EvaluacionProducto | None:
        return self.aptas[0] if self.aptas else None


# ---------------------------------------------------------------- comparación

def _comparar_numeros(operador: str, ofrecido: float, exigido: float) -> bool:
    tolerancia = 1e-9
    return {
        "=": abs(ofrecido - exigido) <= tolerancia,
        ">=": ofrecido >= exigido - tolerancia,
        "<=": ofrecido <= exigido + tolerancia,
        ">": ofrecido > exigido + tolerancia,
        "<": ofrecido < exigido - tolerancia,
    }[operador]


def comparar(requisito: RequisitoTecnico, valor: str, unidad: str | None) -> tuple[str, str]:
    """Compara un requisito con el dato del producto. Devuelve (estado, motivo)."""
    exigido = texto_valor(f"{SIMBOLOS[requisito.operador]} {requisito.valor}", requisito.unidad)
    ofrecido = texto_valor(valor, unidad)

    if requisito.operador == "incluye":
        dato = normalizar(valor)
        if dato in {"no", "no incluye", "sin"}:
            return NO_CUMPLE, "El producto no lo incluye."
        if dato in {"si", "incluye", "incluido"} or normalizar(requisito.valor) in dato:
            return CUMPLE, "El producto lo incluye."
        return REVISAR, f"Verificar si el producto incluye «{requisito.valor}»."

    numero_exigido, unidad_en_exigido = separar_numero(requisito.valor)
    numero_ofrecido, unidad_en_ofrecido = separar_numero(valor)
    if numero_exigido is not None and numero_ofrecido is not None:
        unidad_exigida = requisito.unidad or unidad_en_exigido
        unidad_ofrecida = unidad or unidad_en_ofrecido
        equivalencia = ""
        if ("gramaje" in normalizar(requisito.atributo)
                and normalizar_unidad(unidad_exigida) in UNIDADES_GRAMAJE
                and normalizar_unidad(unidad_ofrecida) in UNIDADES_GRAMAJE
                and normalizar_unidad(unidad_exigida) != normalizar_unidad(unidad_ofrecida)):
            abreviada = unidad_exigida if normalizar_unidad(unidad_exigida) != "g/m2" else unidad_ofrecida
            equivalencia = f" (en el gramaje del papel, «{abreviada}» equivale a g/m2)"
            unidad_exigida = unidad_ofrecida = "g/m2"
        convertido = convertir(numero_ofrecido, unidad_ofrecida, unidad_exigida)
        if convertido is None:
            return REVISAR, f"Unidades distintas ({unidad_ofrecida or 'sin unidad'} y {unidad_exigida or 'sin unidad'}): verificar."
        nota = equivalencia
        if normalizar_unidad(unidad_ofrecida) != normalizar_unidad(unidad_exigida):
            nota = f" ({ofrecido} = {convertido:g} {unidad_exigida})"
        if _comparar_numeros(requisito.operador, convertido, numero_exigido):
            return CUMPLE, f"Cumple{nota}."
        return NO_CUMPLE, f"Ofrece {ofrecido}{nota}; se exige {exigido}."

    if requisito.operador != "=":
        return REVISAR, "No se pudo comparar como número: verificar."

    a, b = normalizar(requisito.valor), normalizar(valor)
    if a == b:
        return CUMPLE, "Coincide."
    if a and b and (a in b or b in a):
        return REVISAR, "Coincidencia parcial: verificar."
    return NO_CUMPLE, f"Ofrece «{valor}»; se exige «{requisito.valor}»."


def _buscar_atributo(nombre: str, atributos: dict[str, pd.Series]) -> tuple[pd.Series | None, bool]:
    """Busca el atributo por nombre exacto (normalizado) o, si no, por similitud."""
    clave = normalizar(nombre)
    if clave in atributos:
        return atributos[clave], True
    parecidos = difflib.get_close_matches(clave, list(atributos), n=1, cutoff=SIMILITUD_MINIMA)
    if parecidos:
        return atributos[parecidos[0]], False
    return None, False


def evaluar_producto(item: Item, filas: pd.DataFrame) -> EvaluacionProducto:
    primera = filas.iloc[0]
    atributos = {normalizar(f["atributo"]): f for _, f in filas.iterrows()}
    evaluacion = EvaluacionProducto(
        sku=primera["sku"], producto=primera["producto"], marca_modelo=primera["marca_modelo"],
        unidad_venta=primera["unidad_venta"], costo_unitario=float(primera["costo_unitario_soles"]),
        stock=float(primera["stock"]), stock_suficiente=float(primera["stock"]) >= item.cantidad,
        es_ejemplo=normalizar(primera["es_ejemplo"]) in {"si", "s", "true", "1"},
    )

    for requisito in item.requisitos:
        exigido = texto_valor(f"{SIMBOLOS[requisito.operador]} {requisito.valor}", requisito.unidad)
        fila, exacto = _buscar_atributo(requisito.atributo, atributos)
        if fila is None:
            evaluacion.resultados.append(ResultadoRequisito(
                requisito.atributo, exigido, None, None, REVISAR,
                "El catálogo no tiene este dato del producto.", requisito.texto_fuente))
            continue

        estado, motivo = comparar(requisito, fila["valor"], fila["unidad"])
        fuente = fila["fuente"] or None
        if estado == CUMPLE and not exacto:
            estado, motivo = REVISAR, f"Se asoció «{requisito.atributo}» con «{fila['atributo']}»: verificar."
        if estado == CUMPLE and fuente is None:
            estado, motivo = REVISAR, "Dato sin fuente: agrega la ficha técnica que lo respalde."
        evaluacion.resultados.append(ResultadoRequisito(
            requisito.atributo, exigido, texto_valor(fila["valor"], fila["unidad"]), fuente,
            estado, motivo, requisito.texto_fuente))
    return evaluacion


def _palabras(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalizar(texto))


def es_de_la_categoria(descripcion: str, categoria: str) -> bool:
    """Todas las palabras de la categoría aparecen en la descripción del ítem.

    Admite plurales simples: 'archivador' coincide con 'archivadores'.
    """
    palabras_item = _palabras(descripcion)
    return bool(categoria.strip()) and all(
        any(p == c or (len(c) >= 4 and (p.startswith(c) or c.startswith(p)) and len(p) >= 4)
            for p in palabras_item)
        for c in _palabras(categoria)
    )


def cruzar(solicitud: SolicitudCotizacion, catalogo: pd.DataFrame) -> list[ResultadoItem]:
    resultados = []
    for item in solicitud.items:
        evaluaciones = [
            evaluar_producto(item, filas)
            for _, filas in catalogo.groupby("sku", sort=False)
            if es_de_la_categoria(item.descripcion, filas.iloc[0]["categoria"])
        ]
        evaluaciones.sort(key=lambda e: (ORDEN_ESTADO[e.estado], not e.stock_suficiente, e.costo_unitario))
        resultados.append(ResultadoItem(item=item, evaluaciones=evaluaciones))
    return resultados
