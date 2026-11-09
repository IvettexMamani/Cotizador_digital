"""Guarda resultados precalculados para el modo demo (requiere clave de API).

Lee cada solicitud, la extrae con el LLM y guarda el JSON en
data/precalculado/<nombre>.json. Así la demo funciona sin internet.
Revisa a mano cada JSON generado antes de usarlo en la presentación.

Uso, desde la raíz del repo:
    .venv\\Scripts\\python.exe -m ai.precalcular data/solicitudes/mi_solicitud.pdf [otra.pdf ...]
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import truststore
from dotenv import load_dotenv

truststore.inject_into_ssl()  # certificados del sistema (ver CLAUDE.md: antivirus)
load_dotenv()

from ai.extractor import CARPETA_PRECALCULADO, MODELO, extraer_con_llm, hay_clave, huella  # noqa: E402
from backend.lectura import leer_documento  # noqa: E402


def precalcular(ruta: Path) -> Path:
    contenido = ruta.read_bytes()
    lectura = leer_documento(ruta.name, contenido)
    solicitud, uso = extraer_con_llm(lectura.texto, ruta.name)

    destino = CARPETA_PRECALCULADO / f"{ruta.stem}.json"
    datos = {
        "descripcion": f"Resultado precalculado de {ruta.name}.",
        "origen": f"Generado con {MODELO} el {date.today().isoformat()} "
                  f"(lectura: {lectura.metodo}). Revisado a mano: PENDIENTE.",
        "archivos_sha256": {ruta.name: huella(contenido)},
        "solicitud": solicitud.model_dump(),
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    costo = f"US$ {uso.costo_usd:.5f}" if uso.costo_usd is not None else "costo no calculado"
    print(f"{ruta.name}: {uso.tokens_entrada} tokens de entrada, {uso.tokens_salida} de salida "
          f"({costo}) -> {destino.relative_to(CARPETA_PRECALCULADO.parent.parent)}")
    return destino


if __name__ == "__main__":
    if not hay_clave():
        sys.exit("Falta ANTHROPIC_API_KEY en .env: este script llama al LLM.")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for argumento in sys.argv[1:]:
        precalcular(Path(argumento))
