"""Pruebas del catálogo que sube el proveedor en la app (CSV o Excel) y de la plantilla."""

import io

import pandas as pd
import pytest

from backend.catalogo import (CATALOGO_EJEMPLO, COLUMNAS, ErrorCatalogo, leer_catalogo_subido,
                              plantilla_excel)


def test_la_plantilla_es_un_catalogo_valido_con_instrucciones():
    contenido = plantilla_excel()
    catalogo = leer_catalogo_subido("plantilla_catalogo.xlsx", contenido)
    assert list(catalogo.columns) == COLUMNAS
    assert catalogo["sku"].nunique() == 1
    assert catalogo["costo_unitario_soles"].iloc[0] == 5.2
    assert catalogo[catalogo["atributo"] == "ancho de lomo"]["valor"].iloc[0] == "8"  # no "8.0"
    hojas = pd.read_excel(io.BytesIO(contenido), sheet_name=None)
    assert set(hojas) == {"catalogo", "instrucciones"}
    assert set(hojas["instrucciones"]["columna"]) == set(COLUMNAS)


def test_csv_con_coma_igual_que_el_de_ejemplo():
    catalogo = leer_catalogo_subido("mi_catalogo.csv", CATALOGO_EJEMPLO.read_bytes())
    assert catalogo["sku"].nunique() == 5


def test_csv_de_excel_en_espanol_con_punto_y_coma_y_latin1():
    texto = CATALOGO_EJEMPLO.read_text(encoding="utf-8").replace(",", ";").replace("14.50", "14,50")
    catalogo = leer_catalogo_subido("catalogo.csv", texto.encode("latin-1"))
    assert catalogo[catalogo["sku"] == "EJ-PAP-075"]["costo_unitario_soles"].iloc[0] == 14.5
    assert "tamaño" in catalogo["atributo"].tolist()  # la ñ se lee bien


def test_encabezados_con_mayusculas_y_espacios():
    texto = CATALOGO_EJEMPLO.read_text(encoding="utf-8").splitlines()
    texto[0] = ",".join(f" {c.upper()} " for c in texto[0].split(","))
    catalogo = leer_catalogo_subido("c.csv", "\n".join(texto).encode("utf-8"))
    assert list(catalogo.columns) == COLUMNAS


@pytest.mark.parametrize("nombre, contenido, mensaje", [
    ("catalogo.pdf", b"%PDF", "Formato no admitido"),
    ("catalogo.csv", "sku,producto\nA,B\n".encode(), "faltan las columnas"),
    ("catalogo.xlsx", b"no es un excel", "No se pudo leer"),
])
def test_errores_con_mensaje_claro(nombre, contenido, mensaje):
    with pytest.raises(ErrorCatalogo, match=mensaje):
        leer_catalogo_subido(nombre, contenido)


def test_fila_sin_valor_indica_la_fila():
    lineas = CATALOGO_EJEMPLO.read_text(encoding="utf-8").splitlines()
    partes = lineas[3].split(",")
    partes[lineas[0].split(",").index("valor")] = ""  # se borra el valor del 3.er dato
    lineas[3] = ",".join(partes)
    with pytest.raises(ErrorCatalogo, match="filas 4"):  # fila 4 de Excel (la 1 es el encabezado)
        leer_catalogo_subido("c.csv", "\n".join(lineas).encode("utf-8"))
