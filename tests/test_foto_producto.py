"""Pruebas de la verificación de un bien a partir de la foto de su etiqueta.

Los textos imitan lo que devuelve el OCR de una etiqueta (inventados).
"""

from ai.esquemas import Item, RequisitoTecnico
from backend.cruce import CUMPLE, NO_CUMPLE, REVISAR
from backend.foto_producto import buscar, evaluar_foto, tiene_texto


def req(atributo, operador, valor, unidad=None):
    return RequisitoTecnico(atributo=atributo, operador=operador, valor=valor, unidad=unidad,
                            texto_fuente=f"{atributo}: {valor}", pagina=1)


ARCHIVADOR = Item(numero=2, descripcion="Archivador de palanca lomo ancho tamaño oficio", cantidad=150,
                  unidad="Unidad", requisitos=[
                      req("tamaño", "=", "oficio"),
                      req("ancho de lomo", ">=", "8", "cm"),
                      req("material", "=", "cartón prensado forrado"),
                      req("mecanismo", "=", "palanca metálica con anillos"),
                  ])

ETIQUETA = """ARCHIVADOR DE PALANCA
Marca: MARCA EJEMPLO  Modelo: EJ-200
Tamaño: oficio
Lomo ancho: 80 mm
Mecanismo: palanca metálica con anillos"""


def estados(evaluacion):
    return {r.atributo: r.estado for r in evaluacion.resultados}


def test_identifica_y_verifica_lo_impreso_en_la_etiqueta():
    e = evaluar_foto(ARCHIVADOR, ETIQUETA, "foto.png", costo_unitario=5.0, stock=200)
    assert estados(e) == {"tamaño": CUMPLE, "ancho de lomo": CUMPLE, "material": REVISAR, "mecanismo": CUMPLE}
    lomo = next(r for r in e.resultados if r.atributo == "ancho de lomo")
    assert lomo.ofrecido == "80 mm" and "80 mm = 8 cm" in lomo.motivo  # conversión de unidades
    assert lomo.fuente == "Foto (foto.png): «Lomo ancho: 80 mm»"  # la fuente es la línea leída


def test_regla_de_oro_lo_que_no_se_lee_queda_en_rojo():
    e = evaluar_foto(ARCHIVADOR, ETIQUETA, "foto.png")
    material = next(r for r in e.resultados if r.atributo == "material")
    assert material.estado == REVISAR and material.ofrecido is None and material.fuente is None
    assert e.estado == REVISAR  # el producto no queda como "cumple" mientras haya un dato sin leer


def test_numero_que_no_alcanza_no_cumple():
    texto = ETIQUETA.replace("80 mm", "6 cm")
    assert estados(evaluar_foto(ARCHIVADOR, texto, "f.png"))["ancho de lomo"] == NO_CUMPLE


def test_texto_distinto_queda_por_revisar_no_como_no_cumple():
    texto = ETIQUETA.replace("Tamaño: oficio", "Tamaño: A4")
    e = evaluar_foto(ARCHIVADOR, texto, "f.png")
    tamano = next(r for r in e.resultados if r.atributo == "tamaño")
    assert tamano.estado == REVISAR and "A4" in tamano.motivo


def test_dato_en_una_linea_que_no_nombra_el_atributo_se_revisa():
    papel = Item(numero=1, descripcion="Papel bond A4", cantidad=200, unidad="Paquete", requisitos=[
        req("gramaje", ">=", "75", "g/m2"), req("tamaño", "=", "A4")])
    e = evaluar_foto(papel, "PAPEL BOND A4\n75 g/m²\n500 hojas", "f.png")
    assert estados(e) == {"gramaje": REVISAR, "tamaño": REVISAR}
    assert buscar(papel.requisitos[0], "PAPEL BOND A4\n75 g/m²").valor == "75"
    # Con el nombre del atributo, sí cumple
    assert estados(evaluar_foto(papel, "Gramaje: 75 g/m²\nTamaño: A4", "f.png")) == {
        "gramaje": CUMPLE, "tamaño": CUMPLE}


def test_alias_de_unidades_y_coma_decimal():
    r = req("gramaje", ">=", "75", "g/m2")
    hallazgo = buscar(r, "Gramaje: 80 gr/m2")
    assert (hallazgo.valor, hallazgo.unidad) == ("80", "g/m2")
    assert buscar(req("ancho de lomo", ">=", "8", "cm"), "Lomo: 7,5 cm").valor == "7.5"


def test_datos_del_proveedor_y_stock():
    e = evaluar_foto(ARCHIVADOR, ETIQUETA, "f.png", producto="Archivador X", costo_unitario=4.5, stock=100)
    assert (e.sku, e.producto, e.costo_unitario) == ("FOTO-2", "Archivador X", 4.5)
    assert not e.stock_suficiente  # 100 < 150 pedidos


def test_foto_sin_texto():
    assert not tiene_texto("  \n ab ")
    assert tiene_texto(ETIQUETA)
