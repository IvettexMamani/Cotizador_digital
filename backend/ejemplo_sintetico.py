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

import io
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


FOTO_PRODUCTO = CARPETA.parent / "fotos_productos" / "ejemplo_etiqueta_archivador.png"

# Etiqueta ficticia de un archivador que no está en el catálogo. A propósito NO
# dice el material: así la demo muestra que lo que no se lee queda en rojo.
ETIQUETA = [
    ("B", 9, "EJEMPLO SINTÉTICO - ETIQUETA FICTICIA"),
    ("B", 14, "ARCHIVADOR DE PALANCA"),
    ("", 11, "Marca: MARCA EJEMPLO   Modelo: EJ-200"),
    ("", 11, "Tamaño: oficio"),
    ("", 11, "Lomo ancho: 80 mm"),
    ("", 11, "Mecanismo: palanca metálica con anillos"),
    ("", 11, "Contenido: 1 unidad"),
]


def generar_foto_producto(destino: Path = FOTO_PRODUCTO) -> Path:
    """Etiqueta de producto como imagen, ligeramente girada, como una foto con el celular."""
    pdf = FPDF(unit="mm", format=(110, 72))
    pdf.set_creation_date(FECHA_FIJA)
    pdf.set_margins(8, 8, 8)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.rect(4, 4, 102, 64)
    for estilo, tamano, texto in ETIQUETA:
        pdf.set_font("Helvetica", estilo, tamano)
        pdf.cell(0, tamano * 0.55, texto, new_x="LMARGIN", new_y="NEXT")
    temporal = destino.with_suffix(".pdf")
    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(temporal))
    with pdfplumber.open(temporal) as documento:
        imagen = documento.pages[0].to_image(resolution=200).original.convert("L")
    temporal.unlink()
    imagen.rotate(1.5, expand=True, fillcolor=205).save(destino)  # fondo gris: la mesa
    return destino


# ---------------------------------------------------------------- solicitud con formato del SIGA

SIGA_ESCANEADO = CARPETA.parent / "formatos" / "ejemplo_siga_escaneado.pdf"

# Diseño inspirado en la "Solicitud de cotización" que imprime el SIGA del MEF: el proveedor
# responde en el mismo documento (VALOR TOTAL por ítem, TOTAL y condiciones de compra).
# Entidad, proveedor, RUC y códigos son ficticios.
SIGA_ITEMS = [
    ("200", "PAQUETE", "111100000001", "PAPEL BOND A4", ESPECIFICACIONES["Ítem 1 - Papel bond A4"]),
    ("150", "UNIDAD", "111100000002", "ARCHIVADOR DE PALANCA LOMO ANCHO TAMAÑO OFICIO",
     ESPECIFICACIONES["Ítem 2 - Archivador de palanca"]),
]
SIGA_CONDICIONES = [
    "- Forma de Pago:", "- Garantía:", "- La Cotización debe incluir el I.G.V.",
    "- Plazo de Entrega en N° Días/ Ejecución del Servicio :", "- Tipo de Moneda :",
    "- Validez de la cotización :", "- Indicar Marca de Procedencia", "- Tipo de Cambio :",
]
COLUMNAS_SIGA = [("CANTIDAD", 18), ("UNIDAD\nMEDIDA", 22), ("ITEM", 26), ("DESCRIPCION", 96), ("VALOR\nTOTAL", 24)]


def _texto(pdf: FPDF, x: float, y: float, texto: str, tamano: float = 8, estilo: str = "") -> None:
    pdf.set_font("Helvetica", estilo, tamano)
    pdf.set_xy(x, y)
    pdf.cell(0, tamano * 0.45, texto)


def generar_siga_digital() -> bytes:
    """La solicitud SIGA de ejemplo como PDF digital (se usa para generar la versión escaneada)."""
    pdf = FPDF(format="A4")
    pdf.set_creation_date(FECHA_FIJA)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    for i, linea in enumerate(("Sistema Integrado de Gestión Administrativa", "Módulo de Logística", "Versión 26.01.02")):
        _texto(pdf, 12, 10 + i * 4, linea, 7.5, "B")
    for i, linea in enumerate(("Fecha  :  06/11/2026", "Hora    :  09:00", "Página : 1 de 1")):
        _texto(pdf, 160, 10 + i * 4.5, linea, 8.5, "B")

    pdf.set_fill_color(255, 230, 230)
    pdf.set_text_color(160, 0, 0)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_xy(12, 24)
    pdf.cell(186, 5, "EJEMPLO SINTÉTICO - Documento ficticio inspirado en el formato del SIGA. "
             "Entidad y proveedor ficticios.", border=1, fill=True, align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(12, 31)
    pdf.cell(186, 6, "SOLICITUD DE COTIZACIÓN N°  000123", align="C")
    _texto(pdf, 12, 40, "UNIDAD EJECUTORA   :  001   MUNICIPALIDAD DISTRITAL DE EJEMPLO (ENTIDAD FICTICIA)", 7.5, "B")
    _texto(pdf, 12, 44.5, "NRO. IDENTIFICACIÓN :  000000", 7.5, "B")

    pdf.rect(12, 50, 186, 30)
    proveedor = [
        ("Señores", "EMPRESA DE EJEMPLO S.A.C. (PROVEEDOR FICTICIO)"),
        ("Dirección", "AV. LOS EJEMPLOS 456 - TACNA"),
        ("Teléfono", "000000000"),
        ("Email", ""),
        ("Concepto", "ADQUISICIÓN DE ÚTILES DE OFICINA PARA LA SUBGERENCIA DE ADMINISTRACIÓN"),
    ]
    for i, (etiqueta, valor) in enumerate(proveedor):
        _texto(pdf, 15, 52 + i * 5.5, etiqueta, 7.5, "B")
        _texto(pdf, 35, 52 + i * 5.5, f":   {valor}", 7.5)
    _texto(pdf, 150, 52, "R.U.C.   :   00000000000", 7.5, "B")
    _texto(pdf, 100, 68.5, "Fecha   :   06/11/2026", 7.5)
    _texto(pdf, 160, 68.5, "Moneda  :  S/.", 7.5, "B")

    # Tabla: encabezado, cuerpo alto con líneas verticales y casilla TOTAL
    x, arriba, alto_encabezado, abajo = 12, 84, 9, 196
    pdf.rect(x, arriba, 186, abajo - arriba)
    pdf.line(x, arriba + alto_encabezado, x + 186, arriba + alto_encabezado)
    pdf.set_font("Helvetica", "B", 8)
    borde = x
    for titulo, ancho in COLUMNAS_SIGA:
        pdf.set_xy(borde, arriba + 1)
        pdf.multi_cell(ancho, 3.5, titulo, align="C")
        borde += ancho
        if borde < x + 186:
            pdf.line(borde, arriba, borde, abajo)
    fila = arriba + alto_encabezado + 2
    for cantidad, unidad, codigo, descripcion, especificaciones in SIGA_ITEMS:
        _texto(pdf, x + 2, fila, cantidad, 8)
        _texto(pdf, x + 19, fila, unidad, 8)
        _texto(pdf, x + 41, fila, codigo, 8)
        _texto(pdf, x + 67, fila, descripcion, 8, "B")
        for j, especificacion in enumerate(especificaciones, start=1):
            _texto(pdf, x + 69, fila + j * 4, especificacion, 7.5)
        fila += (len(especificaciones) + 2) * 4
    pdf.rect(150, abajo, 24, 6)
    pdf.rect(174, abajo, 24, 6)
    _texto(pdf, 156, abajo + 1.5, "TOTAL", 8, "B")

    _texto(pdf, 14, 206, "Las cotizaciones a valores referenciales deben estar dirigidas a "
           "MUNICIPALIDAD DISTRITAL DE EJEMPLO (ENTIDAD FICTICIA)", 7)
    _texto(pdf, 14, 214, "Condiciones de Compra", 7.5, "B")
    for i, condicion in enumerate(SIGA_CONDICIONES):
        _texto(pdf, 14, 218 + i * 4, condicion, 7.5, "B")
    _texto(pdf, 14, 218 + len(SIGA_CONDICIONES) * 4, "Atentamente;", 7.5)
    _texto(pdf, 120, 218, "Requerimientos Técnicos:", 7)
    _texto(pdf, 120, 222, "Ver la descripción de cada ítem.", 7)
    return bytes(pdf.output())


def generar_siga_escaneado(destino: Path = SIGA_ESCANEADO) -> Path:
    """Versión escaneada (solo imagen), como llegan las solicitudes reales."""
    with pdfplumber.open(io.BytesIO(generar_siga_digital())) as documento:
        imagen = documento.pages[0].to_image(resolution=150).original.convert("L")
    pdf = FPDF(format="A4")
    pdf.set_creation_date(FECHA_FIJA)
    pdf.add_page()
    pdf.image(imagen, x=0, y=0, w=pdf.w, h=pdf.h)
    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(destino))
    return destino


if __name__ == "__main__":
    for ruta in (generar_pdf_digital(), generar_foto(), generar_pdf_escaneado(), generar_foto_producto(),
                 generar_siga_escaneado()):
        print("Generado:", ruta.relative_to(CARPETA.parent.parent))
