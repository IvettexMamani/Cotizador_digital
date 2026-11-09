"""Costo del LLM por cotización, a partir del registro de tokens.

Cada llamada al LLM queda en logs/uso_llm.jsonl (ver ai/extractor.py). Hoy cada
cotización hace una sola llamada (la extracción de requisitos), así que el costo
por cotización es el costo promedio por llamada de extracción.

Uso, desde la raíz del repo:
    .venv\\Scripts\\python.exe -m ai.costos
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ai.extractor import REGISTRO_TOKENS


@dataclass
class ResumenUso:
    llamadas: int
    tokens_entrada_promedio: float
    tokens_salida_promedio: float
    costo_promedio_usd: float | None
    costo_total_usd: float | None
    modelos: list[str]


def resumir_uso(ruta: Path = REGISTRO_TOKENS) -> ResumenUso | None:
    if not ruta.exists():
        return None
    filas = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip()]
    filas = [f for f in filas if f.get("paso") == "extraccion"]
    if not filas:
        return None
    n = len(filas)
    costos = [f["costo_usd"] for f in filas if f.get("costo_usd") is not None]
    return ResumenUso(
        llamadas=n,
        tokens_entrada_promedio=sum(f["tokens_entrada"] for f in filas) / n,
        tokens_salida_promedio=sum(f["tokens_salida"] for f in filas) / n,
        costo_promedio_usd=sum(costos) / len(costos) if costos else None,
        costo_total_usd=sum(costos) if costos else None,
        modelos=sorted({f["modelo"] for f in filas}),
    )


if __name__ == "__main__":
    resumen = resumir_uso()
    if resumen is None:
        print("Todavía no hay llamadas registradas en logs/uso_llm.jsonl (se necesitan pruebas con clave de API).")
    else:
        print(f"Llamadas de extracción: {resumen.llamadas} ({', '.join(resumen.modelos)})")
        print(f"Tokens promedio: {resumen.tokens_entrada_promedio:,.0f} de entrada y "
              f"{resumen.tokens_salida_promedio:,.0f} de salida")
        if resumen.costo_promedio_usd is not None:
            print(f"Costo promedio por cotización: US$ {resumen.costo_promedio_usd:.5f} "
                  f"(total registrado: US$ {resumen.costo_total_usd:.4f})")
