"""OCR con PaddleOCR (sesión 10) para PDF escaneados y fotos.

- Carga diferida: PaddleOCR se importa y se carga solo la primera vez que se
  necesita, así la app abre rápido.
- Caché: el modelo cargado queda en memoria (lru_cache) y se reutiliza.
- Modelos "mobile" (livianos) para que entre en la memoria del despliegue.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image

# Evita la verificación de conectividad de PaddleX en cada arranque (tarda varios segundos).
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

MODELO_DETECCION = "PP-OCRv5_mobile_det"
MODELO_RECONOCIMIENTO = "latin_PP-OCRv5_mobile_rec"  # alfabeto latino: tildes y ñ


@dataclass
class ResultadoOCR:
    texto: str
    confianza_promedio: float  # 0 a 1
    n_fragmentos: int


@lru_cache(maxsize=1)
def cargar_ocr():
    """Carga PaddleOCR una sola vez por proceso (la primera vez descarga los modelos)."""
    from paddleocr import PaddleOCR  # import diferido: es pesado

    return PaddleOCR(
        text_detection_model_name=MODELO_DETECCION,
        text_recognition_model_name=MODELO_RECONOCIMIENTO,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def _agrupar_en_lineas(textos, cajas) -> list[str]:
    """Ordena los fragmentos de arriba abajo y de izquierda a derecha.

    PaddleOCR devuelve un fragmento por cada bloque de texto detectado; en una
    tabla, cada celda sale por separado. Aquí se juntan los fragmentos que están
    a la misma altura para reconstruir cada línea del documento.
    """
    fragmentos = []
    for texto, (x1, y1, x2, y2) in zip(textos, cajas):
        fragmentos.append({"texto": texto, "x": x1, "y": (y1 + y2) / 2, "alto": y2 - y1})
    fragmentos.sort(key=lambda f: f["y"])

    lineas: list[list[dict]] = []
    for frag in fragmentos:
        if lineas:
            ultima = lineas[-1]
            y_linea = sum(f["y"] for f in ultima) / len(ultima)
            if abs(frag["y"] - y_linea) < frag["alto"] * 0.5:
                ultima.append(frag)
                continue
        lineas.append([frag])

    return ["  ".join(f["texto"] for f in sorted(linea, key=lambda f: f["x"])) for linea in lineas]


def leer_imagen(imagen: Image.Image) -> ResultadoOCR:
    """Aplica OCR a una imagen y devuelve el texto en orden de lectura."""
    ocr = cargar_ocr()
    arreglo = np.array(imagen.convert("RGB"))[:, :, ::-1]  # PaddleOCR espera BGR
    resultados = ocr.predict(arreglo)

    lineas: list[str] = []
    puntajes: list[float] = []
    for res in resultados:
        textos = list(res["rec_texts"])
        cajas = [tuple(map(float, caja)) for caja in res["rec_boxes"]]
        lineas.extend(_agrupar_en_lineas(textos, cajas))
        puntajes.extend(float(p) for p in res["rec_scores"])

    confianza = sum(puntajes) / len(puntajes) if puntajes else 0.0
    return ResultadoOCR(texto="\n".join(lineas), confianza_promedio=confianza, n_fragmentos=len(puntajes))
