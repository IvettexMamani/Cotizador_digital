"""Paso 6 del flujo: PDF de la cotización, listo para imprimir y firmar.

Es un documento DEL PROVEEDOR con la misma estructura de la solicitud de
cotización del SIGA (cantidad, unidad, ítem, descripción, valor total, TOTAL y
condiciones de compra), para que el evaluador lo lea como está acostumbrado.
No lleva el encabezado del sistema ni datos que emite la entidad: si el
proveedor tiene la solicitud SIGA original, la app la completa aparte
(backend/formato_entidad.py). Al final va la matriz de cumplimiento técnico.

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
class CondicionesOferta:
    """Condiciones comerciales que escribe el proveedor (sin valores por defecto)."""
    forma_pago: str = ""
    garantia: str = ""
    plazo_entrega: str = ""
    validez: str = ""
    tipo_cambio: str = ""


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
    condiciones: CondicionesOferta = field(default_factory=CondicionesOferta)

    @property
    def cotizadas(self) -> list[LineaCotizacion]:
        return [linea for linea in self.lineas if linea.evaluacion is not None]

    def valor_total(self, linea: LineaCotizacion) -> float:
        """Valor total del ítem, con IGV si corresponde (lo que va en la columna VALOR TOTAL)."""
        factor = 1 + IGV if self.aplicar_igv else 1
        return round(round(linea.precio_unitario or 0, 2) * linea.item.cantidad * factor, 2)

    @property
    def subtotal(self) -> float:
        """Valor de venta, sin IGV."""
        return round(sum(round(l.precio_unitario or 0, 2) * l.item.cantidad for l in self.cotizadas), 2)

    @property
    def total(self) -> float:
        """Suma de los valores totales: así la tabla y el TOTAL siempre cuadran."""
        return round(sum(self.valor_total(l) for l in self.cotizadas), 2)

    @property
    def igv(self) -> float:
        return round(self.total - self.subtotal, 2) if self.aplicar_igv else 0.0


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
        self.cell(0, 5, _t(f"Cotización del proveedor, preparada con Cotizador Digital y revisada por él. "
                           f"La herramienta no firma ni envía documentos.  Página {self.page_no()}"),
                  align="C")
        self.set_text_color(0, 0, 0)


def _campo(valor: str, ancho: int = 30) -> str:
    return valor.strip() if valor and valor.strip() else "_" * ancho


def _fecha(f: date) -> str:
    return f"{f.day:02d}/{f.month:02d}/{f.year}"


def generar_pdf(cotizacion: Cotizacion) -> bytes:
    faltan = pendientes(cotizacion)
    if faltan:
        raise CotizacionIncompleta(faltan)

    s, p, c = cotizacion.solicitud, cotizacion.proveedor, cotizacion.condiciones
    pdf = _PDF(format="A4")
    pdf.set_margins(18, 15, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Encabezado: datos del proveedor (el documento es suyo) y fecha
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(120, 5.5, _t(_campo(p.razon_social, 40)))
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(0, 5.5, _t(f"Fecha : {_fecha(cotizacion.fecha)}"), align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    for linea in (f"R.U.C. : {_campo(p.ruc, 11)}", f"Dirección : {_campo(p.direccion, 30)}",
                  f"Teléfono : {_campo(p.telefono, 12)}      Email : {_campo(p.correo, 25)}"):
        pdf.cell(0, 4.5, _t(linea), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 7, _t("COTIZACIÓN"), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.cell(0, 4.5, _t(f"En respuesta a la Solicitud de Cotización N° {_campo(s.numero_solicitud or '', 10)}"),
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # Recuadro de la entidad, como en la solicitud del SIGA
    arriba = pdf.get_y()
    for etiqueta, valor in (("Señores", s.entidad), ("Concepto", s.objeto), ("Moneda", "S/. (soles)")):
        pdf.set_x(21)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(22, 5, _t(etiqueta))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.multi_cell(147, 5, _t(f":  {valor}"), new_x="LMARGIN", new_y="NEXT")
    pdf.rect(18, arriba - 1, 174, pdf.get_y() - arriba + 2)
    pdf.ln(4)

    # Tabla: CANTIDAD | UNIDAD MEDIDA | ÍTEM | DESCRIPCIÓN | VALOR TOTAL, y casilla TOTAL
    pdf.set_font("Helvetica", "", 8.5)
    with pdf.table(col_widths=(18, 22, 12, 96, 26), line_height=4.6,
                   text_align=("CENTER", "CENTER", "CENTER", "LEFT", "RIGHT")) as tabla:
        tabla.row([_t(x) for x in ("CANTIDAD", "UNIDAD MEDIDA", "ÍTEM", "DESCRIPCIÓN", "VALOR TOTAL")])
        for linea in cotizacion.lineas:
            item = linea.item
            fila = [_cantidad(item.cantidad), item.unidad.upper(), str(item.numero)]
            if linea.evaluacion is None:
                tabla.row([_t(x) for x in fila + [f"{item.descripcion}\nNo se cotiza", "-"]])
                continue
            e = linea.evaluacion
            ofrecido = e.producto + (f" - {e.marca_modelo}" if e.marca_modelo else "")
            tabla.row([_t(x) for x in fila + [f"{item.descripcion}\nOfrecemos: {ofrecido}",
                                              _soles(cotizacion.valor_total(linea))]])
        total = tabla.row()
        total.cell(_t("TOTAL"), colspan=4, align="RIGHT")
        total.cell(_soles(cotizacion.total), align="RIGHT")
    pdf.set_font("Helvetica", "I", 7.5)
    nota_igv = (f"Valor de venta S/ {_soles(cotizacion.subtotal)} + IGV ({IGV:.0%}) S/ {_soles(cotizacion.igv)}."
                if cotizacion.aplicar_igv else "Montos sin IGV.")
    pdf.cell(0, 4.5, _t(nota_igv), align="R", new_x="LMARGIN", new_y="NEXT")

    # Condiciones de compra, en el mismo orden que la solicitud del SIGA
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, _t("Condiciones de Compra"), new_x="LMARGIN", new_y="NEXT")
    marcas = "; ".join(f"Ítem {l.item.numero}: {l.evaluacion.marca_modelo}" for l in cotizacion.cotizadas
                       if l.evaluacion.marca_modelo.strip())
    condiciones = [
        ("Forma de Pago", c.forma_pago),
        ("Garantía", c.garantia),
        ("La cotización incluye el I.G.V.", "Sí" if cotizacion.aplicar_igv else "No (montos sin IGV)"),
        ("Plazo de Entrega", c.plazo_entrega),
        ("Tipo de Moneda", "Soles (S/)"),
        ("Validez de la cotización", c.validez),
        ("Marca de Procedencia", marcas),
        ("Tipo de Cambio", c.tipo_cambio),
    ]
    for etiqueta, valor in condiciones:
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.cell(55, 4.8, _t(f"- {etiqueta} :"))
        pdf.set_font("Helvetica", "", 8.5)
        pdf.multi_cell(0, 4.8, _t(valor.strip() if valor and valor.strip() else "_" * 25),
                       new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.multi_cell(0, 4.5, _t("Se adjunta la matriz de cumplimiento de las especificaciones técnicas, con la "
                              "fuente de cada dato."), new_x="LMARGIN", new_y="NEXT")

    # Firma (en blanco: la herramienta nunca firma)
    pdf.ln(14)
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
                    fuente = r.fuente or "Sin fuente verificada"
                    verificacion = "Confirmado por el proveedor"
                tabla.row([_t(x) for x in (r.atributo, r.exigido, r.ofrecido or "-", fuente, verificacion)])
    if hubo_confirmados:
        pdf.ln(3)
        pdf.set_font("Helvetica", "I", 8)
        pdf.multi_cell(0, 4.5, _t(
            "Los datos marcados «Confirmado por el proveedor» no tenían una fuente verificada (ficha técnica o etiqueta legible) "
            "y fueron confirmados por el proveedor bajo su responsabilidad."), align="L",
            new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
