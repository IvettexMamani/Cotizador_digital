"""Pruebas del cruce de requisitos con el catálogo (paso 4)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from ai.esquemas import Item, RequisitoTecnico, SolicitudCotizacion
from backend.catalogo import CATALOGO_EJEMPLO, COLUMNAS, cargar_catalogo, validar_catalogo
from backend.cruce import (CUMPLE, NO_CUMPLE, REVISAR, comparar, convertir, cruzar,
                           es_de_la_categoria, evaluar_producto)

RAIZ = Path(__file__).resolve().parent.parent


def req(atributo="gramaje", operador=">=", valor="75", unidad="g/m2"):
    return RequisitoTecnico(atributo=atributo, operador=operador, valor=valor, unidad=unidad,
                            texto_fuente=f"{atributo}: {valor}", pagina=1)


def catalogo(*atributos, sku="P1", categoria="papel bond", costo="10", stock="100"):
    """Catálogo mínimo: cada atributo es (nombre, valor, unidad, fuente)."""
    filas = [
        {"sku": sku, "producto": f"Producto {sku}", "marca_modelo": "x", "categoria": categoria,
         "unidad_venta": "Paquete", "costo_unitario_soles": costo, "stock": stock, "es_ejemplo": "si",
         "atributo": a, "valor": v, "unidad": u, "fuente": f}
        for a, v, u, f in atributos
    ]
    return validar_catalogo(pd.DataFrame(filas, columns=COLUMNAS))


def item(*requisitos, descripcion="Papel bond A4", cantidad=50):
    return Item(numero=1, descripcion=descripcion, cantidad=cantidad, unidad="Paquete",
                requisitos=list(requisitos))


# ---------------------------------------------------------------- comparar un requisito

@pytest.mark.parametrize("operador, ofrecido, esperado", [
    (">=", "75", CUMPLE), (">=", "80", CUMPLE), (">=", "70", NO_CUMPLE),
    ("<=", "70", CUMPLE), ("<=", "80", NO_CUMPLE),
    ("=", "75", CUMPLE), ("=", "75,0", CUMPLE), ("=", "76", NO_CUMPLE),
])
def test_comparaciones_numericas(operador, ofrecido, esperado):
    estado, _ = comparar(req(operador=operador), ofrecido, "g/m2")
    assert estado == esperado


def test_convierte_unidades_de_longitud():
    assert convertir(80, "mm", "cm") == pytest.approx(8)
    estado, motivo = comparar(req("ancho de lomo", ">=", "8", "cm"), "80", "mm")
    assert estado == CUMPLE and "80 mm = 8 cm" in motivo


def test_unidades_incompatibles_quedan_por_revisar():
    estado, _ = comparar(req("gramaje", ">=", "75", "g/m2"), "75", "kg")
    assert estado == REVISAR


def test_comparacion_de_texto_sin_tildes_ni_mayusculas():
    assert comparar(req("material", "=", "Cartón prensado", None), "carton PRENSADO", None)[0] == CUMPLE
    assert comparar(req("color", "=", "blanco", None), "blanco hueso", None)[0] == REVISAR
    assert comparar(req("color", "=", "blanco", None), "azul", None)[0] == NO_CUMPLE


def test_requisito_incluye():
    assert comparar(req("garantía", "incluye", "garantía", None), "sí", None)[0] == CUMPLE
    assert comparar(req("garantía", "incluye", "garantía", None), "no", None)[0] == NO_CUMPLE


# ---------------------------------------------------------------- regla de oro

def test_dato_sin_fuente_nunca_queda_como_cumple():
    cat = catalogo(("gramaje", "80", "g/m2", ""))
    resultado = evaluar_producto(item(req()), cat).resultados[0]
    assert resultado.estado == REVISAR
    assert "sin fuente" in resultado.motivo


def test_dato_que_falta_en_el_catalogo_queda_por_revisar():
    cat = catalogo(("color", "blanco", "", "ficha.pdf"))
    resultado = evaluar_producto(item(req("gramaje")), cat).resultados[0]
    assert resultado.estado == REVISAR and resultado.ofrecido is None


def test_atributo_asociado_por_parecido_queda_por_revisar():
    cat = catalogo(("gramajes", "80", "g/m2", "ficha.pdf"))
    resultado = evaluar_producto(item(req("gramaje")), cat).resultados[0]
    assert resultado.estado == REVISAR and "Se asoció" in resultado.motivo


# ---------------------------------------------------------------- categorías y orden

def test_categoria_admite_plurales_y_tildes():
    assert es_de_la_categoria("Archivadores de palanca", "archivador")
    assert es_de_la_categoria("PAPEL BOND A4", "papel bond")
    assert not es_de_la_categoria("Papel periódico", "papel bond")


def test_orden_estado_luego_stock_luego_costo():
    filas = pd.concat([
        catalogo(("gramaje", "80", "g/m2", "f"), sku="CARO", costo="20"),
        catalogo(("gramaje", "80", "g/m2", "f"), sku="BARATO", costo="10"),
        catalogo(("gramaje", "80", "g/m2", "f"), sku="SIN-STOCK", costo="5", stock="10"),
        catalogo(("gramaje", "80", "g/m2", ""), sku="SIN-FUENTE", costo="1"),
        catalogo(("gramaje", "60", "g/m2", "f"), sku="NO-CUMPLE", costo="1"),
    ], ignore_index=True)
    solicitud = SolicitudCotizacion(entidad="E", numero_solicitud=None, objeto="O", items=[item(req())],
                                    plazo_entrega=None, lugar_entrega=None, fecha_limite=None,
                                    anexos_solicitados=[], dudas=[])
    resultado = cruzar(solicitud, filas)[0]

    assert [e.sku for e in resultado.evaluaciones] == ["BARATO", "CARO", "SIN-STOCK", "SIN-FUENTE", "NO-CUMPLE"]
    assert resultado.recomendado.sku == "BARATO"
    assert "NO-CUMPLE" not in [e.sku for e in resultado.aptas]


# ---------------------------------------------------------------- ejemplo completo

def test_ejemplo_sintetico_con_catalogo_de_ejemplo():
    datos = json.loads((RAIZ / "data" / "precalculado" / "ejemplo_sintetico.json").read_text(encoding="utf-8"))
    solicitud = SolicitudCotizacion.model_validate(datos["solicitud"])
    papel, archivador = cruzar(solicitud, cargar_catalogo(CATALOGO_EJEMPLO))

    assert papel.recomendado.sku == "EJ-PAP-075" and papel.recomendado.estado == CUMPLE
    assert archivador.recomendado.sku == "EJ-ARC-080" and archivador.recomendado.estado == REVISAR
    material = next(r for r in archivador.recomendado.resultados if r.atributo == "material")
    assert material.estado == REVISAR  # en el catálogo de ejemplo, ese dato no tiene fuente a propósito


# ---------------------------------------------------------------- validación del catálogo

def test_papel_a3_con_catalogo_de_ejemplo():
    item = Item(numero=1, descripcion="Papel bond A3", cantidad=60, unidad="Paquete", requisitos=[
        req("tamaño", "=", "A3", None), req("gramaje", ">=", "75", "g/m2"),
        req("hojas por paquete", "=", "500", "hojas")])
    solicitud = SolicitudCotizacion(entidad="ENTIDAD FICTICIA", numero_solicitud=None, objeto="Papel A3",
                                    items=[item], plazo_entrega=None, lugar_entrega=None, fecha_limite=None,
                                    anexos_solicitados=[], dudas=[])
    (papel,) = cruzar(solicitud, cargar_catalogo(CATALOGO_EJEMPLO))
    assert papel.recomendado.sku == "EJ-PA3-075" and papel.recomendado.estado == CUMPLE
    a3_80 = next(e for e in papel.evaluaciones if e.sku == "01")  # código que puso Ivette
    assert a3_80.estado == CUMPLE and not a3_80.stock_suficiente  # 5 paquetes en stock y se piden 60
    for a4 in (e for e in papel.evaluaciones if e.sku.startswith("EJ-PAP")):
        assert a4.estado == NO_CUMPLE  # el tamaño A4 no es A3


def test_catalogo_de_ejemplo_es_valido():
    df = cargar_catalogo(CATALOGO_EJEMPLO)
    assert set(df["sku"]) == {"EJ-PAP-075", "EJ-PAP-070", "EJ-PAP-080", "EJ-PA3-075", "01",
                              "EJ-ARC-080", "EJ-ARC-050"}


def test_catalogo_con_punto_y_coma_y_coma_decimal(tmp_path):
    ruta = tmp_path / "catalogo.csv"
    ruta.write_text(";".join(COLUMNAS) + "\nP1;Papel;x;papel bond;Paquete;14,50;10;gramaje;75;g/m2;f;no\n",
                    encoding="utf-8-sig")
    df = cargar_catalogo(ruta)
    assert df["costo_unitario_soles"].iloc[0] == pytest.approx(14.5)


def test_catalogo_inconsistente_da_error_claro():
    filas = pd.concat([catalogo(("a", "1", "", "f"), costo="10"), catalogo(("b", "2", "", "f"), costo="12")])
    with pytest.raises(ValueError, match="P1"):
        validar_catalogo(filas.astype(str))
