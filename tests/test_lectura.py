"""Pruebas de la lectura de solicitudes (paso 2)."""

from pathlib import Path

import pytest

from backend.lectura import leer_documento

SOLICITUDES = Path(__file__).resolve().parent.parent / "data" / "solicitudes"


def _leer(nombre: str):
    return leer_documento(nombre, (SOLICITUDES / nombre).read_bytes())


def test_pdf_digital_se_lee_con_pdfplumber_sin_ocr():
    lectura = _leer("ejemplo_sintetico.pdf")

    assert lectura.metodo == "pdfplumber"
    assert lectura.paginas_ocr == []
    assert "=== Página 1 ===" in lectura.texto
    assert "Gramaje: mínimo 75 g/m2." in lectura.texto


def test_formato_no_admitido_da_error_claro():
    with pytest.raises(ValueError, match="Formato no admitido"):
        leer_documento("solicitud.docx", b"contenido")


@pytest.mark.lento
@pytest.mark.parametrize("nombre", ["ejemplo_sintetico_escaneado.pdf", "ejemplo_sintetico_foto.png"])
def test_escaneados_y_fotos_pasan_por_ocr(nombre):
    lectura = _leer(nombre)

    assert lectura.metodo == "ocr"
    assert lectura.confianza_ocr > 0.9
    # Datos clave que el OCR debe leer bien
    for fragmento in ("Gramaje: mínimo 75 g/m2", "Ancho de lomo: mínimo 8 cm", "001-2026-UL/MDE"):
        assert fragmento in lectura.texto
