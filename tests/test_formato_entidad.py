"""Pruebas del llenado del formato de la entidad (solicitud SIGA de EJEMPLO SINTÉTICO)."""

import io
import json
from pathlib import Path

import pdfplumber
import pytest

from ai.esquemas import SolicitudCotizacion
from backend.catalogo import cargar_catalogo
from backend.cruce import cruzar
from backend.ejemplo_sintetico import SIGA_ESCANEADO, generar_siga_digital
from backend.formato_entidad import (CondicionesOferta, Fragmento, a_pdf, anchos_paginas, buscar_columna_total,
                                     coincide, leer_formato, llenar, planificar)
from backend.pdf import Cotizacion, DatosProveedor, LineaCotizacion

RAIZ = Path(__file__).resolve().parent.parent
PRECIOS = {1: 14.69, 2: 6.38}  # sin IGV, ilustrativos


def cotizacion(aplicar_igv=True, precios=PRECIOS) -> Cotizacion:
    datos = json.loads((RAIZ / "data" / "precalculado" / "ejemplo_sintetico.json").read_text(encoding="utf-8"))
    solicitud = SolicitudCotizacion.model_validate(datos["solicitud"])
    lineas = [LineaCotizacion(r.item, r.recomendado, precios.get(r.item.numero))
              for r in cruzar(solicitud, cargar_catalogo(RAIZ / "data" / "catalogo_ejemplo.csv"))]
    return Cotizacion(solicitud, lineas, DatosProveedor(), aplicar_igv, set(), True)


def texto_pdf(contenido: bytes) -> str:
    with pdfplumber.open(io.BytesIO(contenido)) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def test_encabezado_en_dos_lineas_valor_total():
    fragmentos = [Fragmento("VALOR", 512, 240, 542, 250), Fragmento("TOTAL", 511, 250, 542, 261),
                  Fragmento("TOTAL", 444, 560, 472, 570)]
    columna = buscar_columna_total(fragmentos)
    assert columna is not None and columna.y0 == 240 and columna.y1 == 261


def test_coincide_con_mayusculas_tildes_y_abreviaturas():
    assert coincide("PAPEL BOND A4", "PapEl Bond A4")
    assert coincide("Archivador de palanca lomo ancho tamaño oficio", "Archivador de Palanca lomo ancho tamano oficio")
    assert coincide("Papel bond tamaño A4 de 75 g", "PAPEL BOND A4")  # la fila abrevia
    assert not coincide("PAPEL BOND A4", "Tamaño: A4 (210 x 297 mm).")


def test_llena_la_solicitud_siga_digital():
    pdf_bytes, paginas = leer_formato("siga.pdf", generar_siga_digital())
    plan = planificar(paginas, anchos_paginas(pdf_bytes), cotizacion(),
                      CondicionesOferta(forma_pago="Contado, a la conformidad", plazo_entrega="10 días calendario"))
    escrito = {e.campo: e.texto for e in plan.escrituras}
    # 14.69 × 200 × 1.18 y 6.38 × 150 × 1.18
    assert escrito["Ítem 1 · valor total"] == "3,466.84"
    assert escrito["Ítem 2 · valor total"] == "1,129.26"
    assert escrito["TOTAL"] == "4,596.10"
    assert escrito["Forma de pago"] == "Contado, a la conformidad"
    assert escrito["Tipo de moneda"] == "Soles (S/)"
    # Regla de oro: lo que el proveedor no indicó queda en blanco
    assert {"Garantía", "Validez de la cotización", "Tipo de cambio"} <= set(plan.en_blanco)
    assert plan.no_ubicados == [] and plan.avisos == []

    texto = texto_pdf(llenar(pdf_bytes, plan))
    assert "3,466.84" in texto and "4,596.10" in texto and "10 días calendario" in texto
    assert "SOLICITUD DE COTIZACIÓN" in texto  # el original sigue ahí


def test_sin_igv_y_aviso_porque_el_formato_lo_pide():
    pdf_bytes, paginas = leer_formato("siga.pdf", generar_siga_digital())
    plan = planificar(paginas, anchos_paginas(pdf_bytes), cotizacion(aplicar_igv=False), CondicionesOferta())
    escrito = {e.campo: e.texto for e in plan.escrituras}
    assert escrito["Ítem 1 · valor total"] == "2,938.00"
    assert any("IGV" in aviso for aviso in plan.avisos)


def test_item_sin_precio_queda_en_blanco():
    pdf_bytes, paginas = leer_formato("siga.pdf", generar_siga_digital())
    plan = planificar(paginas, anchos_paginas(pdf_bytes), cotizacion(precios={1: 14.69}), CondicionesOferta())
    assert "Ítem 2 · valor total (el ítem no se cotiza)" in plan.en_blanco
    assert {e.campo for e in plan.escrituras} >= {"Ítem 1 · valor total", "TOTAL"}


def test_formato_que_no_tiene_tabla_de_precios():
    pdf_bytes, paginas = leer_formato("otro.pdf", (RAIZ / "data" / "solicitudes" / "ejemplo_sintetico.pdf").read_bytes())
    plan = planificar(paginas, anchos_paginas(pdf_bytes), cotizacion(), CondicionesOferta())
    assert not plan.reconocido


def test_una_foto_se_convierte_en_pdf():
    foto = (RAIZ / "data" / "fotos_productos" / "ejemplo_etiqueta_archivador.png").read_bytes()
    pdf = a_pdf("formato.png", foto)
    assert pdf.startswith(b"%PDF") and anchos_paginas(pdf) == [595.0]


@pytest.mark.lento
def test_llena_la_solicitud_siga_escaneada_con_ocr():
    pdf_bytes, paginas = leer_formato(SIGA_ESCANEADO.name, SIGA_ESCANEADO.read_bytes())
    plan = planificar(paginas, anchos_paginas(pdf_bytes), cotizacion(), CondicionesOferta(validez="30 días"))
    escrito = {e.campo: e.texto for e in plan.escrituras}
    assert escrito["TOTAL"] == "4,596.10" and escrito["Validez de la cotización"] == "30 días"
    assert "4,596.10" in texto_pdf(llenar(pdf_bytes, plan))  # la capa escrita es texto real
