"""Paso 6 del flujo: PDF de la cotización, listo para imprimir y firmar.

Contenido: carta de presentación con el cuadro de precios, condiciones de la
solicitud, espacio para la firma y la matriz de cumplimiento técnico.

Regla de oro: generar_pdf() se niega a generar el documento si queda algo
pendiente: datos en rojo sin confirmar, stock sin confirmar, precios faltantes
o la casilla "Revisé y me hago responsable" sin marcar. La herramienta nunca
firma ni envía: el espacio de la firma queda en blanco.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from fpdf import FPDF

from ai.esquemas import Item, SolicitudCotizacion
from backend.cruce import CUMPLE, EvaluacionProducto
from backend.precio import IGV

STOCK = "__stock__"  # clave para confirmar el stock insuficiente de un ítem

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]

# Las fuentes estándar del PDF solo admiten caracteres latinos (latin-1)
REEMPLAZOS = {"≥": ">=", "≤": "<=", "—": "-", "–": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
              "…": "...", "•": "-", "✓": "si", "✗": "no"}


class CotizacionIncompleta(Exception):
    def __init__(self, pendientes: list[str]):
        super().__init__("; ".join(pendientes))
        self.pendientes = pendientes


@dataclass
class DatosProveedor:
    razon_social: str = ""
    ruc: str = ""
    direccion: str = ""
    telefono: str = ""
    correo: str = ""
    representante: str = ""


@dataclass
class LineaCotizacion:
    item: Item
    evaluacion: EvaluacionProducto | None  # None: el ítem no se cotiza
    precio_unitario: float | None = None  # sin IGV


@dataclass
class Cotizacion:
    solicitud: SolicitudCotizacion
    lineas: list[LineaCotizacion]
    proveedor: DatosProveedor
    aplicar_igv: bool = True
    confirmados: set[tuple[int, str]] = field(default_factory=set)  # (n.° de ítem, atributo o STOCK)
    responsable: bool = False
    fecha: date = field(default_factory=date.today)

    @property
    def cotizadas(self) -> list[LineaCotizacion]:
        return [linea for linea in self.lineas if linea.evaluacion is not None]

    @property
    def subtotal(self) -> float:
        return sum(round(l.precio_unitario or 0, 2) * l.item.cantidad for l in self.cotizadas)

    @property
    def igv(self) -> float:
        return self.subtotal * IGV if self.aplicar_igv else 0.0


def por_confirmar(linea: LineaCotizacion) -> list[tuple[str, str]]:
    """(clave, descripción) de lo que el proveedor debe confirmar en esta línea."""
    if linea.evaluacion is None:
        return []
    claves = [(r.atributo, f"{r.atributo}: {r.ofrecido or 'sin dato'} ({r.motivo})")
              for r in linea.evaluacion.resultados if r.estado != CUMPLE]
    if linea.evaluacion.stock < linea.item.cantidad:
        claves.append((STOCK, f"stock: tienes {linea.evaluacion.stock:,.0f} y se piden {linea.item.cantidad:,.0f}"))
    return claves


def pendientes(cotizacion: Cotizacion) -> list[str]:
    faltan = []
    if not cotizacion.cotizadas:
        faltan.append("No hay ítems para cotizar.")
    for linea in cotizacion.cotizadas:
        numero = linea.item.numero
        for clave, descripcion in por_confirmar(linea):
            if (numero, clave) not in cotizacion.confirmados:
                faltan.append(f"Ítem {numero}: confirma «{descripcion}».")
        if not linea.precio_unitario or linea.precio_unitario <= 0:
            faltan.append(f"Ítem {numero}: falta el precio.")
    if not cotizacion.responsable:
        faltan.append("Marca la casilla «Revisé y me hago responsable».")
    return faltan


# ---------------------------------------------------------------- PDF

def _t(texto) -> str:
    texto = "" if texto is None else str(texto)
    for original, reemplazo in REEMPLAZOS.items():
        texto = texto.replace(original, reemplazo)
    return texto.encode("latin-1", "replace").decode("latin-1")


def _soles(monto: float) -> str:
    return f"{monto:,.2f}"


def _cantidad(valor: float) -> str:
    return f"{valor:,.0f}" if float(valor).is_integer() else f"{valor:,.2f}"


class _PDF(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(110, 110, 110)
        self.cell(0, 5, _t(f"Preparado con Cotizador Digital y revisado por el proveedor. "
                           f"La herramienta no firma ni envía documentos.  Página {self.page_no()}"),
                  align="C")
        self.set_text_color(0, 0, 0)


def _campo(valor: str, ancho: int = 30) -> str:
    return valor.strip() if valor and valor.strip() else "_" * ancho


def generar_pdf(cotizacion: Cotizacion) -> bytes:
    faltan = pendientes(cotizacion)
    if faltan:
        raise CotizacionIncompleta(faltan)

    s, p = cotizacion.solicitud, cotizacion.proveedor
    pdf = _PDF(format="A4")
    pdf.set_margins(18, 15, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Encabezado del proveedor
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, _t(_campo(p.razon_social, 40)), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _t(f"RUC: {_campo(p.ruc, 11)}   ·   Dirección: {_campo(p.direccion, 30)}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _t(f"Teléfono: {_campo(p.telefono, 12)}   ·   Correo: {_campo(p.correo, 25)}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    f = cotizacion.fecha
    pdf.cell(0, 5, _t(f"{f.day} de {MESES[f.month - 1]} de {f.year}"), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, _t("COTIZACIÓN"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, _t(f"Señores: {s.entidad}"), new_x="LMARGIN", new_y="NEXT")
    if s.numero_solicitud:
        pdf.multi_cell(0, 5, _t(f"Referencia: Solicitud de cotización N° {s.numero_solicitud}"),
                       new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.multi_cell(0, 5, _t(
        f"De nuestra consideración: por medio de la presente, {_campo(p.razon_social, 30)}, "
        f"con RUC {_campo(p.ruc, 11)}, presenta su cotización para {s.objeto}, de acuerdo con las "
        "especificaciones técnicas solicitadas, según el siguiente detalle:"),
        new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # Cuadro de precios
    pdf.set_font("Helvetica", "", 8.5)
    with pdf.table(col_widths=(10, 48, 50, 18, 18, 21, 23), line_height=5,
                   text_align=("CENTER", "LEFT", "LEFT", "CENTER", "RIGHT", "RIGHT", "RIGHT")) as tabla:
        tabla.row([_t(x) for x in ("Ítem", "Descripción solicitada", "Producto ofrecido", "Unidad",
                                   "Cant.", "P. unit. (S/)", "Subtotal (S/)")])
        for linea in cotizacion.lineas:
            item = linea.item
            if linea.evaluacion is None:
                tabla.row([_t(x) for x in (str(item.numero), item.descripcion, "No se cotiza",
                                           item.unidad, _cantidad(item.cantidad), "-", "-")])
                continue
            e = linea.evaluacion
            unitario = round(linea.precio_unitario, 2)
            ofrecido = e.producto + (f" ({e.marca_modelo})" if e.marca_modelo else "")
            tabla.row([_t(x) for x in (str(item.numero), item.descripcion, ofrecido, item.unidad,
                                       _cantidad(item.cantidad), _soles(unitario),
                                       _soles(unitario * item.cantidad))])

    pdf.ln(1)
    pdf.set_font("Helvetica", "", 9.5)
    totales = [("Subtotal", cotizacion.subtotal)]
    if cotizacion.aplicar_igv:
        totales.append((f"IGV ({IGV:.0%})", cotizacion.igv))
    totales.append(("TOTAL (S/)", cotizacion.subtotal + cotizacion.igv))
    for etiqueta, monto in totales:
        pdf.set_font("Helvetica", "B" if etiqueta.startswith("TOTAL") else "", 9.5)
        pdf.cell(150, 6, _t(etiqueta), align="R")
        pdf.cell(24, 6, _soles(monto), align="R", new_x="LMARGIN", new_y="NEXT")
    if not cotizacion.aplicar_igv:
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, _t("Montos sin IGV."), align="R", new_x="LMARGIN", new_y="NEXT")

    # Condiciones
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Condiciones", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9.5)
    for etiqueta, valor in (("Plazo de entrega", s.plazo_entrega), ("Lugar de entrega", s.lugar_entrega),
                            ("Validez de la oferta", None)):
        pdf.multi_cell(0, 5, _t(f"- {etiqueta}: {valor or _campo('', 25)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5, _t("- Se adjunta la matriz de cumplimiento de las especificaciones técnicas."),
                   new_x="LMARGIN", new_y="NEXT")

    # Firma (en blanco: la herramienta nunca firma)
    pdf.ln(16)
    pdf.cell(0, 5, "_" * 40, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, _t("Firma y sello del representante legal"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, _t(_campo(p.representante, 30)), align="C", new_x="LMARGIN", new_y="NEXT")

    # Matriz de cumplimiento
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 7, _t("Matriz de cumplimiento de especificaciones técnicas"), new_x="LMARGIN", new_y="NEXT")
    hubo_confirmados = False
    for linea in cotizacion.cotizadas:
        e = linea.evaluacion
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.multi_cell(0, 5, _t(f"Ítem {linea.item.numero}: {linea.item.descripcion}  ->  {e.producto}"),
                       align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        with pdf.table(col_widths=(28, 30, 32, 52, 32), line_height=4.5, text_align="LEFT") as tabla:
            tabla.row([_t(x) for x in ("Requisito", "Exigido", "Ofrecido", "Fuente del dato", "Verificación")])
            for r in e.resultados:
                if r.estado == CUMPLE:
                    fuente, verificacion = r.fuente, "Cumple"
                else:
                    hubo_confirmados = True
                    fuente = r.fuente or "Sin fuente en el catálogo"
                    verificacion = "Confirmado por el proveedor"
                tabla.row([_t(x) for x in (r.atributo, r.exigido, r.ofrecido or "-", fuente, verificacion)])
    if hubo_confirmados:
        pdf.ln(3)
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4.5, _t(
            "Los datos marcados «Confirmado por el proveedor» no tenían una fuente verificada en el catálogo "
            "y fueron confirmados por el proveedor bajo su responsabilidad."), align="L",
            new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
