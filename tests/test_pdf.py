"""Pruebas de la confirmación y del PDF (paso 6): la regla de oro bloquea el PDF."""

import io
import json
from pathlib import Path

import pdfplumber
import pytest

from ai.esquemas import SolicitudCotizacion
from backend.catalogo import CATALOGO_EJEMPLO, cargar_catalogo
from backend.cruce import cruzar
from backend.pdf import (STOCK, CondicionesOferta, Cotizacion, CotizacionIncompleta, DatosProveedor, LineaCotizacion,
                         generar_pdf, pendientes, por_confirmar)

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def cotizacion():
    datos = json.loads((RAIZ / "data" / "precalculado" / "ejemplo_sintetico.json").read_text(encoding="utf-8"))
    solicitud = SolicitudCotizacion.model_validate(datos["solicitud"])
    resultados = cruzar(solicitud, cargar_catalogo(CATALOGO_EJEMPLO))
    lineas = [LineaCotizacion(r.item, r.recomendado, precio) for r, precio in zip(resultados, [15.0, 6.5])]
    return Cotizacion(solicitud, lineas, DatosProveedor(razon_social="EMPRESA DE PRUEBA"))


def confirmar_todo(cot):
    cot.confirmados = {(l.item.numero, clave) for l in cot.cotizadas for clave, _ in por_confirmar(l)}
    cot.responsable = True


def test_sin_confirmar_el_pdf_queda_bloqueado(cotizacion):
    faltan = pendientes(cotizacion)
    assert any("material" in f for f in faltan)  # dato sin fuente del catálogo de ejemplo
    assert any("Revisé y me hago responsable" in f for f in faltan)
    with pytest.raises(CotizacionIncompleta):
        generar_pdf(cotizacion)


def test_solo_la_casilla_final_no_basta(cotizacion):
    cotizacion.responsable = True
    assert pendientes(cotizacion)  # sigue faltando confirmar el dato en rojo


def test_falta_de_precio_bloquea(cotizacion):
    confirmar_todo(cotizacion)
    cotizacion.lineas[0].precio_unitario = None
    assert pendientes(cotizacion) == ["Ítem 1: falta el precio."]


def test_stock_insuficiente_debe_confirmarse(cotizacion):
    cotizacion.lineas[0].item.cantidad = 10_000
    assert any(clave == STOCK for clave, _ in por_confirmar(cotizacion.lineas[0]))


def test_totales_con_y_sin_igv(cotizacion):
    # 200 × 15.00 + 150 × 6.50 = 3,975.00
    assert cotizacion.subtotal == pytest.approx(3975.0)
    assert cotizacion.igv == pytest.approx(715.5)
    cotizacion.aplicar_igv = False
    assert cotizacion.igv == 0


def test_pdf_completo(cotizacion):
    confirmar_todo(cotizacion)
    contenido = generar_pdf(cotizacion)
    assert contenido.startswith(b"%PDF")

    with pdfplumber.open(io.BytesIO(contenido)) as documento:
        texto = "\n".join(pagina.extract_text() for pagina in documento.pages)
    assert "EMPRESA DE PRUEBA" in texto
    assert "MUNICIPALIDAD DISTRITAL DE EJEMPLO" in texto
    assert "4,690.50" in texto  # total con IGV
    assert "Matriz de cumplimiento" in texto
    assert "Confirmado por el proveedor" in texto  # el dato sin fuente quedó declarado
    assert ">= 75 g/m2" in texto  # el símbolo ≥ se escribe como >= en el PDF
    assert "Firma y sello" in texto


def test_item_sin_producto_se_marca_como_no_cotizado(cotizacion):
    cotizacion.lineas[1].evaluacion = None
    confirmar_todo(cotizacion)
    with pdfplumber.open(io.BytesIO(generar_pdf(cotizacion))) as documento:
        assert "No se cotiza" in documento.pages[0].extract_text()


def test_condiciones_de_la_oferta_en_el_pdf(cotizacion):
    confirmar_todo(cotizacion)
    cotizacion.condiciones = CondicionesOferta(forma_pago="A la conformidad", tipo_cambio="No aplica")
    with pdfplumber.open(io.BytesIO(generar_pdf(cotizacion))) as documento:
        texto = documento.pages[0].extract_text()
    assert "A la conformidad" in texto and "No aplica" in texto
