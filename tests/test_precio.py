"""Pruebas del cálculo de precio, de la referencia del Estado y del gráfico (paso 5)."""

import pandas as pd
import pytest

from backend.grafico_precio import grafico_precio
from backend.precio import (MIN_ORDENES, con_igv, piso_unitario, precio_con_margen, precio_sugerido,
                            referencia_estado, repartir_flete, semaforo)
from backend.precios import buscar_precios, cargar_precios_estado, terminos_por_defecto


def test_piso_margen_e_igv():
    piso = piso_unitario(costo=10.0, flete_item=100.0, cantidad=50)  # 10 + 2 de flete por unidad
    assert piso == pytest.approx(12.0)
    assert precio_con_margen(piso, 0.25) == pytest.approx(15.0)
    assert con_igv(100.0, True) == pytest.approx(118.0)
    assert con_igv(100.0, False) == pytest.approx(100.0)


def test_flete_se_reparte_en_proporcion_al_valor():
    assert repartir_flete(100.0, [300.0, 100.0]) == pytest.approx([75.0, 25.0])
    assert repartir_flete(90.0, [0.0, 0.0, 0.0]) == pytest.approx([30.0, 30.0, 30.0])


def test_referencia_minimo_mediana_maximo_y_debil():
    ref = referencia_estado([10, 12, 14, 20, 30])
    assert (ref.n_ordenes, ref.minimo, ref.mediana, ref.maximo) == (5, 10, 14, 30)
    assert not ref.debil
    assert referencia_estado([10] * (MIN_ORDENES - 1)).debil
    assert referencia_estado([]) is None


def test_precio_sugerido():
    ref = referencia_estado([10, 12, 14, 20, 30])  # mediana 14
    assert precio_sugerido(propio=18, piso=11, referencia=ref) == 14  # baja a la mediana
    assert precio_sugerido(propio=13, piso=11, referencia=ref) == 13  # ya es menor que la mediana
    assert precio_sugerido(propio=18, piso=16, referencia=ref) == 16  # nunca bajo el piso
    assert precio_sugerido(propio=18, piso=11, referencia=None) == 18  # sin referencia: tu precio
    assert precio_sugerido(propio=18, piso=11, referencia=referencia_estado([10, 12])) == 18  # débil


@pytest.mark.parametrize("precio, color", [(9, "rojo"), (14, "verde"), (25, "amarillo"), (31, "rojo")])
def test_semaforo(precio, color):
    ref = referencia_estado([10, 12, 14, 20, 30])
    assert semaforo(precio, piso=9.5, referencia=ref).color == color


def test_semaforo_sin_referencia_y_con_referencia_debil():
    assert semaforo(15, 10, None).color == "gris"
    luz = semaforo(11, 10, referencia_estado([12, 13]))
    assert luz.color == "verde" and "Referencia débil" in luz.mensaje


# ---------------------------------------------------------------- precios del Estado

def precios_de_prueba():
    return pd.DataFrame({
        "fecha": ["2026-06-01", "2026-07-15", "2026-08-03"],
        "entidad": ["Entidad A", "Entidad B", "Entidad C"],
        "descripcion": ["PAPEL BOND A4 75 g/m² x 500 hojas", "Papel Bond A4 80 g", "Archivador de palanca oficio"],
        "unidad": ["Paquete", "Paquete", "Unidad"],
        "cantidad": [100, 50, 20],
        "precio_unitario": [17.5, 19.0, 7.2],
        "orden": ["OC-1", "OC-2", "OC-3"],
        "fuente": ["https://catalogos.perucompras.gob.pe/ConsultaOrdenesPub"] * 3,
        "fecha_consulta": ["2026-11-09"] * 3,
    })


def test_busqueda_sin_tildes_ni_mayusculas():
    df = precios_de_prueba()
    assert list(buscar_precios(df, "papel bond A4")["orden"]) == ["OC-1", "OC-2"]
    assert list(buscar_precios(df, "archivador")["orden"]) == ["OC-3"]
    assert buscar_precios(df, "tóner").empty
    assert buscar_precios(df, "").empty


def test_terminos_por_defecto():
    assert terminos_por_defecto("Papel bond A4") == "papel bond a4"
    assert terminos_por_defecto("Archivador de palanca lomo ancho tamaño oficio") == "archivador palanca lomo"


def test_sin_archivo_de_precios_devuelve_tabla_vacia(tmp_path):
    assert cargar_precios_estado(tmp_path / "no_existe.csv").empty


def test_grafico_rotula_minimo_mediana_maximo_y_numero_de_ordenes():
    ordenes = precios_de_prueba().iloc[:2]
    ref = referencia_estado(ordenes["precio_unitario"])
    figura = grafico_precio(ordenes, ref, tu_precio=18.0)
    textos = " ".join(a.text for a in figura.layout.annotations)
    assert "Mín. S/ 17.50" in textos and "Máx. S/ 19.00" in textos and "Mediana S/ 18.25" in textos
    assert "2 órdenes" in figura.layout.title.text and "referencia débil" in figura.layout.title.text
