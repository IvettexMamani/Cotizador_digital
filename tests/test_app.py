"""Pruebas de la app de Streamlit (sin navegador, con AppTest)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # modo demo: nunca llama a la API en las pruebas
    return AppTest.from_file(str(APP), default_timeout=60).run()


def test_la_app_abre_con_la_regla_de_oro_y_el_modo_demo(app):
    assert not app.exception
    assert app.title[0].value == "Cotizador Digital"
    assert "Regla de oro" in app.error[0].value
    assert "Modo demo sin clave" in app.sidebar.warning[0].value


def procesar_ejemplo(app):
    selector = app.selectbox[0]
    selector.select_index(selector.options.index("ejemplo_sintetico.pdf")).run()
    app.button[0].click().run()
    assert not app.exception
    return app


def test_flujo_con_la_solicitud_de_ejemplo_muestra_los_requisitos(app):
    procesar_ejemplo(app)

    requisitos = app.dataframe[2].value  # 0: datos generales, 1: ítems, 2: requisitos
    assert len(requisitos) == 9
    assert "Gramaje: mínimo 75 g/m2." in requisitos["Fuente (cita del documento)"].tolist()
    assert any("Modo demo" in aviso.value for aviso in app.warning)


def test_cruce_recomienda_productos_y_marca_el_dato_sin_fuente(app):
    procesar_ejemplo(app)

    # dataframes: 0-2 extracción; 3-4 ranking y matriz del ítem 1; 5-6 los del ítem 2
    assert app.dataframe[3].value["SKU"].iloc[0] == "EJ-PAP-075"
    assert app.selectbox[1].value == "EJ-PAP-075"
    assert app.selectbox[2].value == "EJ-ARC-080"

    matriz_archivador = app.dataframe[6].value
    material = matriz_archivador[matriz_archivador["Requisito"] == "material"].iloc[0]
    assert "revisar" in material["Estado"]
    assert material["Fuente del dato"] == "— sin fuente —"
