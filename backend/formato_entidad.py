"""Paso 6 (opción): completar el formato de cotización de la entidad (PDF o foto).

En las entidades que usan el SIGA, la propia "Solicitud de cotización" es el
formato de respuesta: el proveedor llena el VALOR TOTAL de cada ítem, el TOTAL y
las condiciones de compra. Este módulo:

1. Ubica el texto del formato y su posición: con pdfplumber si el PDF es digital,
   con PaddleOCR si es escaneado o una foto.
2. Decide qué escribir y dónde (plan de llenado), solo con datos que la app ya
   verificó: precios del paso 5, marca del producto ofrecido y lo que el
   proveedor escribió en "Condiciones de tu oferta".
3. Escribe encima del PDF original (no lo reemplaza): mismo diseño de la entidad.

Regla de oro: no se inventa nada. Lo que la app no sabe queda en blanco y se
avisa; la firma nunca se llena.
"""

from __future__ import annotations

import difflib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from fpdf import FPDF
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter

from backend.cruce import normalizar
from backend.pdf import IGV, CondicionesOferta, Cotizacion, _t  # noqa: F401 (CondicionesOferta se reexporta)

DPI_OCR = 200
MIN_CARACTERES_TEXTO = 40  # menos texto que esto en una página: está escaneada
COLOR_TEXTO = (0, 51, 153)  # azul oscuro: se distingue lo que escribió la app
TAMANO_LETRA = 8.5
MARGEN = 4.0

ENCABEZADOS_TOTAL = {"valor total", "precio total", "importe total", "monto total", "total s/"}
PRIMERAS_PALABRAS = {"valor", "precio", "importe", "monto"}
ETIQUETAS_TOTAL = {"total", "total s/", "total s/.", "total general"}

# (clave, patrón sin tildes, nombre para mostrar)
CONDICIONES = [
    ("forma_pago", r"forma de pago", "Forma de pago"),
    ("garantia", r"garantia", "Garantía"),
    ("plazo_entrega", r"plazo de entrega", "Plazo de entrega"),
    ("moneda", r"tipo de moneda", "Tipo de moneda"),
    ("validez", r"validez de la (cotizacion|oferta)", "Validez de la cotización"),
    ("marca", r"marca de procedencia", "Marca de procedencia"),
    ("tipo_cambio", r"tipo de cambio", "Tipo de cambio"),
]


@dataclass
class Fragmento:
    """Texto del formato con su caja, en puntos del PDF (origen arriba a la izquierda)."""
    texto: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def alto(self) -> float:
        return self.y1 - self.y0

    @property
    def norma(self) -> str:
        return normalizar(self.texto).strip(" -:")


@dataclass
class Escritura:
    pagina: int
    x: float          # izquierda (alineación "izquierda") o centro ("centro")
    y: float          # centro vertical de la línea
    texto: str
    alineacion: str
    ancho_max: float
    campo: str
    fuente: str


@dataclass
class PlanLlenado:
    escrituras: list[Escritura] = field(default_factory=list)
    en_blanco: list[str] = field(default_factory=list)    # campos del formato que quedan vacíos
    no_ubicados: list[str] = field(default_factory=list)  # datos que no se supo dónde escribir
    avisos: list[str] = field(default_factory=list)

    @property
    def reconocido(self) -> bool:
        """Se reconoció al menos la tabla de precios."""
        return any(e.campo.startswith("Ítem") for e in self.escrituras)


# ---------------------------------------------------------------- lectura del formato

def a_pdf(nombre_archivo: str, contenido: bytes) -> bytes:
    """Una foto del formato se convierte en un PDF de una página (ancho A4)."""
    if Path(nombre_archivo).suffix.lower() == ".pdf":
        return contenido
    imagen = ImageOps.exif_transpose(Image.open(io.BytesIO(contenido))).convert("RGB")
    ancho = 595.0
    alto = ancho * imagen.height / imagen.width
    pdf = FPDF(unit="pt", format=(ancho, alto))
    pdf.add_page()
    pdf.image(imagen, x=0, y=0, w=ancho, h=alto)
    return bytes(pdf.output())


def agrupar_palabras(palabras: list[dict]) -> list[Fragmento]:
    """Junta las palabras de pdfplumber en frases, como hace el OCR (separa por espacios grandes)."""
    lineas: list[list[dict]] = []
    for palabra in sorted(palabras, key=lambda p: (round(p["top"]), p["x0"])):
        if lineas and abs(lineas[-1][0]["top"] - palabra["top"]) < 3:
            lineas[-1].append(palabra)
        else:
            lineas.append([palabra])
    fragmentos = []
    for linea in lineas:
        actual = None
        for p in sorted(linea, key=lambda p: p["x0"]):
            alto = p["bottom"] - p["top"]
            if actual and p["x0"] - actual.x1 < max(3.0, 0.6 * alto):
                actual.texto += " " + p["text"]
                actual.x1, actual.y0, actual.y1 = p["x1"], min(actual.y0, p["top"]), max(actual.y1, p["bottom"])
            else:
                actual = Fragmento(p["text"], p["x0"], p["top"], p["x1"], p["bottom"])
                fragmentos.append(actual)
    return fragmentos


def leer_formato(nombre_archivo: str, contenido: bytes) -> tuple[bytes, list[list[Fragmento]]]:
    """Devuelve el PDF del formato y, por página, sus fragmentos de texto con posición."""
    pdf_bytes = a_pdf(nombre_archivo, contenido)
    paginas = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as documento:
        for pagina in documento.pages:
            if len((pagina.extract_text() or "").strip()) >= MIN_CARACTERES_TEXTO:
                paginas.append(agrupar_palabras(pagina.extract_words()))
                continue
            from ai.ocr import fragmentos_imagen  # import diferido: solo carga PaddleOCR si hace falta

            imagen = pagina.to_image(resolution=DPI_OCR).original
            escala = pagina.width / imagen.width
            paginas.append([Fragmento(f.texto, f.x0 * escala, f.y0 * escala, f.x1 * escala, f.y1 * escala)
                            for f in fragmentos_imagen(imagen)])
    return pdf_bytes, paginas


# ---------------------------------------------------------------- dónde va cada dato

def buscar_columna_total(fragmentos: list[Fragmento]) -> Fragmento | None:
    """Encabezado de la columna donde el proveedor escribe el total de cada ítem."""
    candidatos = []
    for f in fragmentos:
        if f.norma in ENCABEZADOS_TOTAL:
            candidatos.append(f)
        elif f.norma in PRIMERAS_PALABRAS:  # "VALOR" y debajo "TOTAL"
            for g in fragmentos:
                if g.norma == "total" and abs(g.cx - f.cx) < max(f.x1 - f.x0, 10) \
                        and 0 <= g.y0 - f.y1 < 1.5 * f.alto:
                    candidatos.append(Fragmento(f"{f.texto} {g.texto}", min(f.x0, g.x0), f.y0,
                                                max(f.x1, g.x1), g.y1))
    return min(candidatos, key=lambda c: c.y0) if candidatos else None


def coincide(descripcion: str, texto: str) -> bool:
    a, b = normalizar(descripcion), normalizar(texto)
    if not a or not b:
        return False
    if a == b or (min(len(a), len(b)) >= 6 and (a in b or b in a)):
        return True
    palabras_a, palabras_b = set(re.findall(r"[a-z0-9]+", a)), set(re.findall(r"[a-z0-9]+", b))
    if len(palabras_b) >= 2 and palabras_b <= palabras_a:  # la fila abrevia la descripción
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.85


def _ancho_disponible(f: Fragmento, fragmentos: list[Fragmento], ancho_pagina: float) -> float:
    """Hasta el siguiente texto de la misma línea o el margen derecho."""
    a_la_derecha = [g.x0 for g in fragmentos if g.x0 > f.x1 and abs(g.cy - f.cy) < f.alto * 0.6]
    limite = min(a_la_derecha) - MARGEN if a_la_derecha else ancho_pagina - 20
    return max(limite - (f.x1 + MARGEN), 0)


def _valores_condiciones(cotizacion: Cotizacion, condiciones: CondicionesOferta) -> dict[str, tuple[str, str]]:
    """clave -> (valor, de dónde sale). Solo lo que la app sabe o escribió el proveedor."""
    propio = "Lo que escribiste en «Condiciones de tu oferta»"
    valores = {
        "forma_pago": (condiciones.forma_pago.strip(), propio),
        "garantia": (condiciones.garantia.strip(), propio),
        "plazo_entrega": (condiciones.plazo_entrega.strip(), propio),
        "validez": (condiciones.validez.strip(), propio),
        "moneda": ("Soles (S/)", "La cotización está en soles"),
        "tipo_cambio": (condiciones.tipo_cambio.strip(), propio),
    }
    marcas = [f"Ítem {l.item.numero}: {l.evaluacion.marca_modelo}" for l in cotizacion.cotizadas
              if l.evaluacion.marca_modelo.strip()]
    valores["marca"] = ("; ".join(marcas), "Catálogo: marca y modelo del producto ofrecido")
    return valores


def planificar(paginas: list[list[Fragmento]], anchos: list[float], cotizacion: Cotizacion,
               condiciones: CondicionesOferta) -> PlanLlenado:
    """Decide qué se escribe y dónde. No escribe nada todavía."""
    plan = PlanLlenado()
    texto_completo = normalizar(" ".join(f.texto for pagina in paginas for f in pagina)).replace(".", "")
    if re.search(r"inclu\w* el igv|incluye igv|inc igv", texto_completo) and not cotizacion.aplicar_igv:
        plan.avisos.append("El formato pide que la cotización incluya el IGV, pero en el paso 5 desmarcaste "
                           "el IGV: revisa los montos.")
    base = " (con IGV)" if cotizacion.aplicar_igv else " (sin IGV)"

    # 1. Tabla de precios: valor total de cada ítem y TOTAL
    pendientes = {l.item.numero: l for l in cotizacion.lineas}
    totales_escritos: list[float] = []
    ultima_tabla = None
    for n_pagina, fragmentos in enumerate(paginas):
        columna = buscar_columna_total(fragmentos)
        if columna is None:
            continue
        ultima_tabla = (n_pagina, columna, fragmentos)
        for numero, linea in list(pendientes.items()):
            fila = next((f for f in sorted(fragmentos, key=lambda f: f.y0)
                         if f.y0 > columna.y1 and f.x1 < columna.x0 and coincide(linea.item.descripcion, f.texto)),
                        None)
            if fila is None:
                continue
            del pendientes[numero]
            campo = f"Ítem {numero} · valor total"
            if linea.evaluacion is None or not linea.precio_unitario:
                plan.en_blanco.append(f"{campo} (el ítem no se cotiza)")
                continue
            total = cotizacion.valor_total(linea)
            totales_escritos.append(total)
            plan.escrituras.append(Escritura(
                n_pagina, columna.cx, fila.cy, f"{total:,.2f}", "centro", columna.x1 - columna.x0 + 30,
                campo, f"Precio final del paso 5 × {linea.item.cantidad:g}{base}"))
    for numero in pendientes:
        plan.no_ubicados.append(f"Ítem {numero}: no encontré su fila en la tabla del formato")

    if ultima_tabla and totales_escritos:
        n_pagina, columna, fragmentos = ultima_tabla
        etiqueta = next((f for f in sorted(fragmentos, key=lambda f: -f.y0)
                         if f.norma in ETIQUETAS_TOTAL and f.y0 > columna.y1 and f.x1 <= columna.x0 + 2), None)
        if etiqueta is not None:
            suma = round(sum(totales_escritos), 2)
            plan.escrituras.append(Escritura(
                n_pagina, columna.cx, etiqueta.cy, f"{suma:,.2f}", "centro",
                columna.x1 - columna.x0 + 30, "TOTAL", f"Suma de los valores totales{base}"))
            total_carta = cotizacion.total
            if len(totales_escritos) == len(cotizacion.cotizadas) and abs(suma - total_carta) >= 0.01:
                plan.avisos.append(f"Por redondeo, el TOTAL del formato (S/ {suma:,.2f}) difiere del total de "
                                   f"la carta (S/ {total_carta:,.2f}): revisa cuál presentas.")
        else:
            plan.no_ubicados.append("TOTAL: no encontré la casilla del total")

    # 2. Condiciones de compra
    valores = _valores_condiciones(cotizacion, condiciones)
    for clave, patron, nombre in CONDICIONES:
        valor, fuente = valores[clave]
        ubicado = False
        for n_pagina, fragmentos in enumerate(paginas):
            etiqueta = next((f for f in fragmentos if re.search(patron, f.norma)), None)
            if etiqueta is None:
                continue
            ubicado = True
            if valor:
                plan.escrituras.append(Escritura(
                    n_pagina, etiqueta.x1 + MARGEN, etiqueta.cy, valor, "izquierda",
                    _ancho_disponible(etiqueta, fragmentos, anchos[n_pagina]), nombre, fuente))
            else:
                plan.en_blanco.append(nombre)
            break
        if not ubicado and valor and clave not in {"moneda"}:
            plan.no_ubicados.append(f"{nombre}: el formato no tiene ese campo")
    return plan


# ---------------------------------------------------------------- escribir sobre el PDF

def _ajustar(pdf: FPDF, texto: str, ancho_max: float) -> tuple[str, float]:
    """Achica la letra (hasta 6 pt) y, si no basta, recorta el texto con '...'."""
    tamano = TAMANO_LETRA
    pdf.set_font("Helvetica", "", tamano)
    while pdf.get_string_width(texto) > ancho_max and tamano > 6:
        tamano -= 0.5
        pdf.set_font("Helvetica", "", tamano)
    while pdf.get_string_width(texto) > ancho_max and len(texto) > 4:
        texto = texto[:-4] + "..."
    return texto, tamano


def llenar(pdf_bytes: bytes, plan: PlanLlenado) -> bytes:
    """Escribe el plan encima del PDF original y devuelve el PDF completado."""
    original = PdfReader(io.BytesIO(pdf_bytes))
    capa = FPDF(unit="pt")
    capa.set_auto_page_break(auto=False)
    capa.set_text_color(*COLOR_TEXTO)
    for n_pagina, pagina in enumerate(original.pages):
        capa.add_page(format=(float(pagina.mediabox.width), float(pagina.mediabox.height)))
        for e in (e for e in plan.escrituras if e.pagina == n_pagina):
            texto, tamano = _ajustar(capa, _t(e.texto), e.ancho_max)
            ancho = capa.get_string_width(texto) + 2
            x = e.x - ancho / 2 if e.alineacion == "centro" else e.x
            capa.set_xy(x, e.y - tamano * 0.6)
            capa.cell(ancho, tamano * 1.2, texto)
    encima = PdfReader(io.BytesIO(bytes(capa.output())))
    salida = PdfWriter(clone_from=io.BytesIO(pdf_bytes))  # copia del original: no se modifica el archivo subido
    for pagina, capa_pagina in zip(salida.pages, encima.pages):
        pagina.merge_page(capa_pagina)
    buffer = io.BytesIO()
    salida.write(buffer)
    return buffer.getvalue()


def anchos_paginas(pdf_bytes: bytes) -> list[float]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as documento:
        return [float(p.width) for p in documento.pages]
