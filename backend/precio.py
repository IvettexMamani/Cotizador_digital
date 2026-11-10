"""Paso 5 del flujo: tarjeta de precio.

Cálculos (todo por unidad de venta, en soles):

    piso              = costo + flete por unidad          (por debajo, pierdes dinero)
    precio con margen = piso × (1 + margen)
    precio final      = precio sin IGV × 1.18 si se agrega IGV

La referencia del Estado son los precios unitarios de órdenes de compra
públicas de bienes similares: mínimo, mediana, máximo y número de órdenes.
Con menos de MIN_ORDENES órdenes, la referencia es "débil".

Precio sugerido = el menor entre tu precio con margen y la mediana del Estado,
sin bajar nunca del piso. Con referencia débil o sin referencia, se sugiere tu
precio con margen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import median
from typing import Sequence

IGV = 0.18  # 16 % IGV + 2 % Impuesto de Promoción Municipal
MIN_ORDENES = 5


@dataclass
class ReferenciaEstado:
    n_ordenes: int
    minimo: float
    mediana: float
    maximo: float

    @property
    def debil(self) -> bool:
        return self.n_ordenes < MIN_ORDENES


def referencia_estado(precios: Sequence[float]) -> ReferenciaEstado | None:
    precios = [float(p) for p in precios if p is not None and p > 0]
    if not precios:
        return None
    return ReferenciaEstado(n_ordenes=len(precios), minimo=min(precios),
                            mediana=float(median(precios)), maximo=max(precios))


def repartir_flete(flete_total: float, valores: Sequence[float]) -> list[float]:
    """Reparte el flete de la entrega entre los ítems, en proporción a su valor (costo × cantidad)."""
    total = sum(valores)
    if total <= 0:
        return [flete_total / len(valores)] * len(valores) if valores else []
    return [flete_total * v / total for v in valores]


def con_igv(precio: float, aplicar: bool) -> float:
    return precio * (1 + IGV) if aplicar else precio


def piso_unitario(costo: float, flete_item: float, cantidad: float) -> float:
    return costo + (flete_item / cantidad if cantidad else 0.0)


def precio_con_margen(piso: float, margen: float) -> float:
    """margen en fracción: 0.20 = 20 %."""
    return piso * (1 + margen)


def _centimos_arriba(monto: float) -> float:
    return math.ceil(round(monto * 100, 6)) / 100


def _centimos_abajo(monto: float) -> float:
    return math.floor(round(monto * 100, 6)) / 100


def precio_sugerido(propio: float, piso: float, referencia: ReferenciaEstado | None) -> float:
    """Todos los montos en la misma base (con o sin IGV) que la referencia.

    Se devuelve en céntimos: el piso se redondea hacia arriba (para no quedar
    debajo del costo) y la mediana hacia abajo (para no quedar sobre ella).
    """
    if referencia is None or referencia.debil:
        return max(_centimos_arriba(piso), round(propio, 2))
    return max(_centimos_arriba(piso), _centimos_abajo(min(propio, referencia.mediana)))


@dataclass
class Semaforo:
    color: str  # "verde", "amarillo", "rojo" o "gris"
    mensaje: str


def semaforo(precio: float, piso: float, referencia: ReferenciaEstado | None) -> Semaforo:
    if precio < piso - 1e-9:
        return Semaforo("rojo", "Por debajo de tu costo más flete: perderías dinero.")
    if referencia is None:
        return Semaforo("gris", "Sin referencia de precios del Estado para comparar.")

    nota = f" Referencia débil: solo {referencia.n_ordenes} órdenes." if referencia.debil else ""
    if precio <= referencia.mediana + 1e-9:
        return Semaforo("verde", "Competitivo: igual o menor que la mediana pagada por el Estado." + nota)
    if precio <= referencia.maximo + 1e-9:
        return Semaforo("amarillo", "Sobre la mediana, pero dentro del rango pagado por el Estado." + nota)
    return Semaforo("rojo", "Más caro que el máximo pagado por el Estado." + nota)
