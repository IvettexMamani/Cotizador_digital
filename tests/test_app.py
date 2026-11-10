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

    # 0: datos generales, 1: ítems, 2 y 3: una tabla de requisitos por ítem
    papel, archivador = app.dataframe[2].value, app.dataframe[3].value
    assert len(papel) + len(archivador) == 9
    assert "Ítem" not in papel.columns  # cada tabla ya es de un solo ítem
    assert "Gramaje: mínimo 75 g/m2." in papel["Fuente (cita del documento)"].tolist()
    assert "material" in archivador["Atributo"].tolist()
    assert any("Modo demo" in aviso.value for aviso in app.warning)


def test_cruce_recomienda_productos_y_marca_el_dato_sin_fuente(app):
    procesar_ejemplo(app)

    # dataframes: 0-3 extracción; 4-5 ranking y matriz del ítem 1; 6-7 los del ítem 2
    assert app.dataframe[4].value["SKU"].iloc[0] == "EJ-PAP-075"
    assert app.selectbox[1].value.startswith("EJ-PAP-075")
    assert app.selectbox[2].value.startswith("EJ-ARC-080")

    matriz_archivador = app.dataframe[7].value
    material = matriz_archivador[matriz_archivador["Requisito"] == "material"].iloc[0]
    assert "revisar" in material["Estado"]
    assert material["Fuente del dato"] == "— sin fuente —"


def test_pdf_bloqueado_hasta_ingresar_precio_y_confirmar(app):
    procesar_ejemplo(app)
    assert any("Ingresa tu margen" in i.value for i in app.info)
    assert any("El PDF todavía no se puede generar" in e.value for e in app.error)

    app.number_input(key="margen").set_value(20.0).run()
    app.number_input(key="flete").set_value(50.0).run()
    app.checkbox(key="responsable").check().run()
    bloqueo = next(e.value for e in app.error if "El PDF todavía no se puede generar" in e.value)
    assert "material" in bloqueo  # el dato en rojo sigue sin confirmar

    app.checkbox(key="confirmo_2_EJ-ARC-080_material").check().run()
    assert not app.exception
    assert not any("El PDF todavía no se puede generar" in e.value for e in app.error)
    assert any("Todo revisado" in s.value for s in app.success)


@pytest.mark.lento
def test_bien_fuera_del_catalogo_con_la_foto_de_ejemplo(app):
    procesar_ejemplo(app)
    app.checkbox(key="foto_ejemplo_2").check().run(timeout=240)  # OCR real de la etiqueta
    assert not app.exception

    verificacion = next(d.value for d in app.dataframe if "Leído en la foto" in d.value.columns)
    estados = dict(zip(verificacion["Requisito"], verificacion["Estado"]))
    assert "cumple" in estados["ancho de lomo"] and "revisar" in estados["material"]

    # Sin costo ni stock todavía no se puede ofrecer
    assert any("Ingresa tu costo y tu stock" in i.value for i in app.info)
    assert not any(o.startswith("FOTO-2") for o in app.selectbox(key="producto_item_2").options)

    app.number_input(key="foto_costo_2").set_value(4.0).run()
    app.number_input(key="foto_stock_2").set_value(300.0).run()
    assert any(o.startswith("FOTO-2") for o in app.selectbox(key="producto_item_2").options)


def avance(app) -> list[str]:
    return [m.value for m in app.sidebar.markdown if m.value[:1] in "✅👉⚪"]


def test_la_barra_lateral_muestra_el_avance_real(app):
    # Al abrir: la solicitud de ejemplo ya está elegida y lo que sigue es leerla
    assert avance(app)[0].startswith("✅") and avance(app)[1].startswith("👉")
    assert all(paso.startswith("⚪") for paso in avance(app)[2:])

    procesar_ejemplo(app)  # lee, extrae y recomienda productos
    assert [p[0] for p in avance(app)] == ["✅", "✅", "✅", "✅", "👉", "⚪"]

    app.number_input(key="margen").set_value(20.0).run()
    app.number_input(key="flete").set_value(50.0).run()
    assert [p[0] for p in avance(app)] == ["✅", "✅", "✅", "✅", "✅", "👉"]

    app.checkbox(key="responsable").check().run()
    app.checkbox(key="confirmo_2_EJ-ARC-080_material").check().run()
    assert [p[0] for p in avance(app)] == ["✅"] * 6
