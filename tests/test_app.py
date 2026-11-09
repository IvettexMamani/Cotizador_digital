"""Prueba de humo: la app de Streamlit abre sin errores y muestra la bienvenida."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"


def test_la_app_abre_con_la_bienvenida():
    app = AppTest.from_file(str(APP)).run()

    assert not app.exception
    assert app.title[0].value == "Cotizador Digital"
    # La regla de oro debe estar visible desde la primera pantalla
    assert "Regla de oro" in app.error[0].value
