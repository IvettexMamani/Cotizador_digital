"""Paso 3 del flujo: extraer los requisitos con un LLM de salida estructurada.

- Con clave de API: llama a Claude con `messages.parse()` y el esquema Pydantic
  como formato de salida. La respuesta llega validada.
- Sin clave, o si la API falla: modo demo. Usa el resultado precalculado
  (data/precalculado/) de las solicitudes de ejemplo y lo avisa en pantalla.
- Cada llamada al LLM registra sus tokens en logs/uso_llm.jsonl para
  calcular el costo por cotización.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from ai.esquemas import SolicitudCotizacion
from ai.prompts import PLANTILLA_USUARIO, SISTEMA

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_PRECALCULADO = RAIZ / "data" / "precalculado"
REGISTRO_TOKENS = RAIZ / "logs" / "uso_llm.jsonl"

# Modelo económico: el costo por cotización es parte del modelo de negocio.
MODELO = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
ESFUERZO = "medium"  # cuánto "piensa" el modelo: low / medium / high
MAX_TOKENS = 16000

# Precio en US$ por millón de tokens (entrada, salida), según la tabla de modelos
# de la documentación de Anthropic con fecha 2026-10-06 (se vuelve a verificar en
# el Bloque 4). Haiku 5.5: tarifa para prompts de hasta 100 mil tokens; una
# solicitud de cotización usa unos pocos miles.
PRECIOS_USD_POR_MILLON = {
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


class ErrorExtraccion(Exception):
    """La extracción no se pudo completar (ni con el LLM ni en modo demo)."""


@dataclass
class UsoTokens:
    modelo: str
    tokens_entrada: int
    tokens_salida: int
    costo_usd: float | None


@dataclass
class ResultadoExtraccion:
    solicitud: SolicitudCotizacion
    modo: Literal["ia", "demo"]
    uso: UsoTokens | None = None
    aviso: str | None = None


# ---------------------------------------------------------------- utilidades

def hay_clave() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY", "").strip())


def huella(contenido: bytes) -> str:
    """SHA-256 del archivo: identifica una solicitud sin depender de su nombre."""
    return hashlib.sha256(contenido).hexdigest()


def calcular_costo(modelo: str, tokens_entrada: int, tokens_salida: int) -> float | None:
    if modelo not in PRECIOS_USD_POR_MILLON:
        return None
    precio_entrada, precio_salida = PRECIOS_USD_POR_MILLON[modelo]
    return (tokens_entrada * precio_entrada + tokens_salida * precio_salida) / 1_000_000


def registrar_uso(uso: UsoTokens, documento: str) -> None:
    REGISTRO_TOKENS.parent.mkdir(parents=True, exist_ok=True)
    fila = {"fecha": datetime.now().isoformat(timespec="seconds"), "documento": documento,
            "paso": "extraccion", **asdict(uso)}
    with REGISTRO_TOKENS.open("a", encoding="utf-8") as archivo:
        archivo.write(json.dumps(fila, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- modo IA

def extraer_con_llm(texto: str, documento: str = "") -> tuple[SolicitudCotizacion, UsoTokens]:
    import anthropic  # import diferido: el modo demo no lo necesita

    cliente = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno
    respuesta = cliente.messages.parse(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        system=SISTEMA,
        messages=[{"role": "user", "content": PLANTILLA_USUARIO.format(texto=texto)}],
        output_format=SolicitudCotizacion,
        output_config={"effort": ESFUERZO},
    )

    uso = UsoTokens(
        modelo=MODELO,
        tokens_entrada=respuesta.usage.input_tokens,
        tokens_salida=respuesta.usage.output_tokens,
        costo_usd=calcular_costo(MODELO, respuesta.usage.input_tokens, respuesta.usage.output_tokens),
    )
    registrar_uso(uso, documento)  # se registra aunque la respuesta no sirva: igual se pagó

    if respuesta.stop_reason == "refusal":
        raise ErrorExtraccion("El modelo se negó a procesar el documento.")
    if respuesta.stop_reason == "max_tokens":
        raise ErrorExtraccion("La respuesta del modelo quedó incompleta (límite de tokens).")
    if respuesta.parsed_output is None:
        raise ErrorExtraccion("El modelo no devolvió datos estructurados.")
    return respuesta.parsed_output, uso


# ---------------------------------------------------------------- modo demo

def buscar_precalculado(contenido: bytes) -> SolicitudCotizacion | None:
    """Busca en data/precalculado/ un resultado guardado para este mismo archivo."""
    codigo = huella(contenido)
    for ruta in sorted(CARPETA_PRECALCULADO.glob("*.json")):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if codigo in datos["archivos_sha256"].values():
            return SolicitudCotizacion.model_validate(datos["solicitud"])
    return None


# ---------------------------------------------------------------- punto de entrada

def extraer_requisitos(texto: str, contenido: bytes, documento: str = "") -> ResultadoExtraccion:
    """Extrae con el LLM si hay clave; si no, o si la API falla, usa el modo demo."""
    motivo_demo = "No hay clave de API configurada."

    if hay_clave():
        import anthropic

        try:
            solicitud, uso = extraer_con_llm(texto, documento)
            return ResultadoExtraccion(solicitud=solicitud, modo="ia", uso=uso)
        except (anthropic.APIError, ErrorExtraccion) as error:
            motivo_demo = f"Falló la llamada a la API ({type(error).__name__}: {error})."

    precalculado = buscar_precalculado(contenido)
    if precalculado is None:
        raise ErrorExtraccion(
            f"{motivo_demo} Además, este documento no tiene un resultado precalculado. "
            "Prueba con una de las solicitudes de ejemplo o configura la clave en .env."
        )
    return ResultadoExtraccion(
        solicitud=precalculado,
        modo="demo",
        aviso=f"Modo demo: {motivo_demo} Se muestra el resultado precalculado de esta solicitud de ejemplo.",
    )
