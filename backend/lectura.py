"""Paso 2 del flujo: leer la solicitud de cotización y devolver su texto.

- PDF digital: texto con pdfplumber.
- PDF escaneado: la página no trae texto, así que se convierte en imagen y se
  le aplica OCR (PaddleOCR). La decisión se toma página por página.
- Foto (PNG/JPG): OCR directo.

Cada página se marca con "=== Página N ===" para que la extracción pueda
indicar en qué página está cada requisito (su fuente).
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from PIL import Image, ImageOps

MIN_CARACTERES_TEXTO = 40  # menos que esto en una página = página escaneada
RESOLUCION_OCR = 150  # dpi al convertir una página PDF en imagen
MAX_PAGINAS = 20  # las solicitudes de contratos menores suelen tener 1 a 5 páginas

EXTENSIONES_IMAGEN = {".png", ".jpg", ".jpeg"}
EXTENSIONES_ADMITIDAS = EXTENSIONES_IMAGEN | {".pdf"}


@dataclass
class Lectura:
    texto: str
    metodo: str  # "pdfplumber", "ocr" o "mixto"
    n_paginas: int
    paginas_ocr: list[int] = field(default_factory=list)
    confianza_ocr: float | None = None  # promedio 0-1, solo si hubo OCR
    avisos: list[str] = field(default_factory=list)


def _metodo(n_paginas: int, paginas_ocr: list[int]) -> str:
    if not paginas_ocr:
        return "pdfplumber"
    if len(paginas_ocr) == n_paginas:
        return "ocr"
    return "mixto"


def leer_pdf(contenido: bytes) -> Lectura:
    from ai.ocr import leer_imagen  # import diferido: solo carga PaddleOCR si hace falta

    partes, paginas_ocr, confianzas, avisos = [], [], [], []
    with pdfplumber.open(io.BytesIO(contenido)) as documento:
        n_paginas = len(documento.pages)
        if n_paginas > MAX_PAGINAS:
            avisos.append(
                f"El PDF tiene {n_paginas} páginas; solo se leyeron las primeras {MAX_PAGINAS}."
            )
        for numero, pagina in enumerate(documento.pages[:MAX_PAGINAS], start=1):
            texto = pagina.extract_text() or ""
            if len(texto.strip()) < MIN_CARACTERES_TEXTO:
                imagen = pagina.to_image(resolution=RESOLUCION_OCR).original
                resultado = leer_imagen(imagen)
                texto = resultado.texto
                paginas_ocr.append(numero)
                confianzas.append(resultado.confianza_promedio)
            partes.append(f"=== Página {numero} ===\n{texto.strip()}")

    return Lectura(
        texto="\n\n".join(partes),
        metodo=_metodo(min(n_paginas, MAX_PAGINAS), paginas_ocr),
        n_paginas=n_paginas,
        paginas_ocr=paginas_ocr,
        confianza_ocr=sum(confianzas) / len(confianzas) if confianzas else None,
        avisos=avisos,
    )


def leer_foto(contenido: bytes) -> Lectura:
    from ai.ocr import leer_imagen

    imagen = ImageOps.exif_transpose(Image.open(io.BytesIO(contenido)))  # corrige fotos giradas
    resultado = leer_imagen(imagen)
    return Lectura(
        texto=f"=== Página 1 ===\n{resultado.texto.strip()}",
        metodo="ocr",
        n_paginas=1,
        paginas_ocr=[1],
        confianza_ocr=resultado.confianza_promedio,
    )


def leer_documento(nombre_archivo: str, contenido: bytes) -> Lectura:
    """Punto de entrada: elige la forma de lectura según la extensión del archivo."""
    extension = Path(nombre_archivo).suffix.lower()
    if extension == ".pdf":
        lectura = leer_pdf(contenido)
    elif extension in EXTENSIONES_IMAGEN:
        lectura = leer_foto(contenido)
    else:
        raise ValueError(
            f"Formato no admitido: {extension or 'sin extensión'}. "
            f"Sube un PDF o una imagen ({', '.join(sorted(EXTENSIONES_ADMITIDAS))})."
        )

    if lectura.confianza_ocr is not None and lectura.confianza_ocr < 0.85:
        lectura.avisos.append(
            f"La confianza del OCR es baja ({lectura.confianza_ocr:.0%}). "
            "Revisa el texto leído: puede haber errores."
        )
    contenido_real = "".join(
        linea for linea in lectura.texto.splitlines() if not linea.startswith("=== Página")
    )
    if not contenido_real.strip():
        lectura.avisos.append("No se encontró texto en el documento.")
    return lectura
