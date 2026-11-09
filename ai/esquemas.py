"""Esquemas Pydantic de la solicitud de cotización (paso 3 del flujo).

Este esquema se envía al LLM como formato de salida estructurada (sesión 08):
la API devuelve un JSON que cumple exactamente esta estructura y Pydantic lo
valida al recibirlo. Las descripciones de cada campo son instrucciones para
el modelo.

Regla de oro: cada requisito técnico lleva la cita textual del documento y la
página de donde sale, para que el proveedor pueda verificarlo.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Operador = Literal["=", ">=", "<=", ">", "<", "incluye"]


class RequisitoTecnico(BaseModel):
    atributo: str = Field(
        description="Característica exigida, breve y en minúsculas. Ej.: 'gramaje', 'tamaño', 'material'."
    )
    operador: Operador = Field(
        description=(
            "'>=' si el documento dice mínimo / al menos / no menor de; "
            "'<=' si dice máximo / hasta / no mayor de; "
            "'>' o '<' solo si dice 'mayor que' o 'menor que' de forma estricta; "
            "'=' para un valor exacto o una característica cualitativa (color, material, tamaño A4); "
            "'incluye' si exige que el producto tenga o traiga algo (accesorio, certificado, garantía)."
        )
    )
    valor: str = Field(
        description="Valor exigido tal como aparece en el documento, sin la unidad. Ej.: '75', 'A4', 'blanco'."
    )
    unidad: str | None = Field(
        description="Unidad de medida del valor tal como aparece (ej. 'g/m2', 'cm', 'hojas'); null si no tiene unidad."
    )
    texto_fuente: str = Field(
        description="Cita textual exacta del documento de la que sale este requisito. Copiar, no parafrasear."
    )
    pagina: int | None = Field(
        description="Número de página donde está la cita, según los marcadores '=== Página N ==='; null si no se sabe."
    )


class Item(BaseModel):
    numero: int = Field(description="Número de ítem tal como figura en el documento.")
    descripcion: str = Field(description="Descripción del bien solicitado.")
    cantidad: float = Field(description="Cantidad solicitada.")
    unidad: str = Field(description="Unidad de medida de la cantidad (ej. 'Paquete', 'Unidad', 'Caja').")
    requisitos: list[RequisitoTecnico] = Field(
        description="Especificaciones técnicas de este ítem. Lista vacía si el documento no las indica."
    )


class SolicitudCotizacion(BaseModel):
    entidad: str = Field(description="Nombre de la entidad pública que solicita la cotización.")
    numero_solicitud: str | None = Field(
        description="Número o código de la solicitud de cotización; null si no aparece."
    )
    objeto: str = Field(description="Objeto de la contratación (qué se quiere adquirir), como lo dice el documento.")
    items: list[Item] = Field(description="Bienes solicitados, uno por ítem.")
    plazo_entrega: str | None = Field(description="Plazo de entrega tal como aparece; null si no aparece.")
    lugar_entrega: str | None = Field(description="Lugar de entrega tal como aparece; null si no aparece.")
    fecha_limite: str | None = Field(
        description="Fecha (y hora, si la hay) límite para presentar la cotización, tal como aparece; null si no aparece."
    )
    anexos_solicitados: list[str] = Field(
        description="Anexos y documentos que el proveedor debe presentar, uno por elemento."
    )
    dudas: list[str] = Field(
        description=(
            "Partes ambiguas, ilegibles, incompletas o contradictorias que el proveedor debe revisar "
            "antes de cotizar. Lista vacía si no hay."
        )
    )
