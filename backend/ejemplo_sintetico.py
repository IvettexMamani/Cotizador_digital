"""Genera la solicitud de cotización de EJEMPLO SINTÉTICO en tres formatos.

La entidad, el número de solicitud y la dirección son ficticios. Sirve para
probar el flujo mientras llegan las solicitudes públicas reales.

Salidas en data/solicitudes/:
    ejemplo_sintetico.pdf             PDF digital (con texto seleccionable)
    ejemplo_sintetico_escaneado.pdf   PDF escaneado (solo imagen, sin texto)
    ejemplo_sintetico_foto.png        foto / imagen suelta

Ejecutar desde la raíz del repo:
    .venv\\Scripts\\python.exe -m backend.ejemplo_sintetico
"""

from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
from fpdf import FPDF

CARPETA = Path(__file__).resolve().parent.parent / "data" / "solicitudes"
PDF_DIGITAL = CARPETA / "ejemplo_sintetico.pdf"
PDF_ESCANEADO = CARPETA / "ejemplo_sintetico_escaneado.pdf"
FOTO = CARPETA / "ejemplo_sintetico_foto.png"

# Fecha fija: así el PDF sale idéntico cada vez y su huella SHA-256 no cambia
# (el modo demo reconoce los archivos de ejemplo por esa huella).
FECHA_FIJA = datetime(2026, 11, 6, 9, 0, tzinfo=timezone.utc)

AVISO = (
    "EJEMPLO SINTÉTICO - Documento ficticio creado para probar el Cotizador "
    "Digital. No corresponde a ninguna entidad real."
)

ITEMS = [
    ("1", "Papel bond A4", "Paquete", "200"),
    ("2", "Archivador de palanca lomo ancho tamaño oficio", "Unidad", "150"),
]

ESPECIFICACIONES = {
    "Ítem 1 - Papel bond A4": [
        "Tamaño: A4 (210 x 297 mm).",
        "Gramaje: mínimo 75 g/m2.",
        "Contenido: 500 hojas por paquete.",
        "Color: blanco.",
        "Presentación: paquete sellado de fábrica.",
    ],
    "Ítem 2 - Archivador de palanca": [
        "Tamaño: oficio.",
        "Ancho de lomo: mínimo 8 cm.",
        "Material: cartón prensado forrado.",
        "Mecanismo: palanca metálica con anillos.",
    ],
}

CONDICIONES = [
    "Plazo de entrega: 10 días calendario, contados desde el día siguiente de "
    "notificada la orden de compra.",
    "Lugar de entrega: Almacén Central de la entidad, Av. Los Ejemplos N° 123, Tacna.",
    "Fecha límite de presentación de cotizaciones: 16 de noviembre de 2026, "
    "hasta las 16:00 horas, en mesa de partes de la entidad.",
]

ANEXOS = [
    "Anexo N° 1: Carta de presentación de la cotización.",
    "Anexo N° 2: Declaración jurada de cumplimiento de las especificaciones técnicas.",
    "Anexo N° 3: Declaración jurada de no estar impedido para contratar con el Estado.",
    "Copia de la ficha RUC.",
    "Constancia de inscripción vigente en el RNP (capítulo de bienes).",
]


def _titulo(pdf: FPDF, texto: str) -> None:
    pdf.set_font("Helvetica", "B", 10)
    pdf.ln(2)
    pdf.cell(0, 6, texto, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)


def _vineta(pdf: FPDF, texto: str) -> None:
    pdf.multi_cell(0, 5, f"- {texto}", new_x="LMARGIN", new_y="NEXT")


def generar_pdf_digital(destino: Path = PDF_DIGITAL) -> Path:
    pdf = FPDF(format="A4")
    pdf.set_creation_date(FECHA_FIJA)
    pdf.set_margins(18, 15, 18)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Marca visible de ejemplo sintético
    pdf.set_fill_color(255, 230, 230)
    pdf.set_text_color(160, 0, 0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.multi_cell(0, 5, AVISO, border=1, fill=True, align="C",
                   new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "MUNICIPALIDAD DISTRITAL DE EJEMPLO (ENTIDAD FICTICIA)",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "Unidad de Logística", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, "SOLICITUD DE COTIZACIÓN N° 001-2026-UL/MDE",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "Tacna, 6 de noviembre de 2026", align="R",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.multi_cell(
        0, 5,
        "Señores proveedores: la Unidad de Logística invita a presentar su "
        "cotización para la ADQUISICIÓN DE ÚTILES DE OFICINA PARA LA SUBGERENCIA "
        "DE ADMINISTRACIÓN, de acuerdo con las especificaciones técnicas "
        "siguientes.",
        new_x="LMARGIN", new_y="NEXT",
    )

    _titulo(pdf, "1. Requerimiento")
    with pdf.table(col_widths=(12, 100, 30, 30), text_align=("CENTER", "LEFT", "CENTER", "CENTER"),
                   line_height=6) as tabla:
        tabla.row(("Ítem", "Descripción", "Unidad", "Cantidad"))
        for fila in ITEMS:
            tabla.row(fila)

    _titulo(pdf, "2. Especificaciones técnicas")
    for item, lineas in ESPECIFICACIONES.items():
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 5, item, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for linea in lineas:
            _vineta(pdf, linea)

    _titulo(pdf, "3. Condiciones")
    for linea in CONDICIONES:
        _vineta(pdf, linea)

    _titulo(pdf, "4. Documentos que debe presentar el proveedor")
    for linea in ANEXOS:
        _vineta(pdf, linea)

    pdf.ln(10)
    pdf.cell(0, 5, "Jefe de la Unidad de Logística", align="C",
             new_x="LMARGIN", new_y="NEXT")

    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    return destino


def generar_foto(origen: Path = PDF_DIGITAL, destino: Path = FOTO) -> Path:
    """Convierte la página 1 del PDF digital en una imagen en escala de grises."""
    with pdfplumber.open(origen) as documento:
        imagen = documento.pages[0].to_image(resolution=150).original
    imagen.convert("L").save(destino)
    return destino


def generar_pdf_escaneado(foto: Path = FOTO, destino: Path = PDF_ESCANEADO) -> Path:
    """Mete la imagen en un PDF sin capa de texto, como sale de un escáner."""
    pdf = FPDF(format="A4")
    pdf.set_creation_date(FECHA_FIJA)
    pdf.add_page()
    pdf.image(str(foto), x=0, y=0, w=pdf.w, h=pdf.h)
    pdf.output(str(destino))
    return destino


if __name__ == "__main__":
    for ruta in (generar_pdf_digital(), generar_foto(), generar_pdf_escaneado()):
        print("Generado:", ruta.relative_to(CARPETA.parent.parent))
