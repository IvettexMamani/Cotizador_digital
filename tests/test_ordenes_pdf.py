"""Pruebas de la lectura de órdenes de compra y de la descarga (sin red).

Los textos son inventados, con el formato de una orden SIGA leída por OCR.
"""

import pandas as pd

from backend.descargar_ordenes import elegir_muestra, leer_exportacion, url_segura
from backend.ordenes_pdf import a_numero, construir_precios, estado_igv, extraer_lineas

ORDEN_CON_IGV = """ORDEN DE COMPRA - GUÍA DE INTERNAMIENTO N°  0000001
Código  Cant.  Unid. Med.  Descripción  Unitario S/  Total S/
111100000001  50.  EMP X 500  PAPEL BOND 75 g TAMAÑO A4 - MARCA X  14.160000  708.00
PAPEL BOND DE 75 G/M2, RESMA DE 500 HOJAS
222200000002  10.  UNIDAD  ARCHIVADOR DE PALANCA LOMO ANCHO OFICIO  5.900000  59.00
V. Venta  650.00
I.G.V.  117.00
Total  :  767.00
"""


def test_a_numero_coma_de_miles_y_punto_final():
    assert a_numero("1,345.20") == 1345.2
    assert a_numero("100.") == 100.0
    assert a_numero("13.452000") == 13.452


def test_extrae_lineas_con_unidad_y_descripcion():
    lineas = extraer_lineas(ORDEN_CON_IGV)
    assert len(lineas) == 2
    papel, archivador = lineas
    assert papel.unidad == "EMP X 500"
    assert papel.descripcion == "PAPEL BOND 75 g TAMAÑO A4 - MARCA X"
    assert (papel.cantidad, papel.precio_unitario, papel.total) == (50, 14.16, 708.0)
    assert archivador.unidad == "UNIDAD"


def test_descarta_linea_que_no_cuadra():
    # El OCR leyó mal el unitario: 50 × 41,16 no da 708,00
    texto = "111100000001  50.  EMP X 500  PAPEL BOND 75 g  41.160000  708.00"
    assert extraer_lineas(texto) == []


def test_cantidad_con_miles_y_punto_final():
    texto = "333300000003  1,582.  UNIDAD  PLUMON MARCADOR COLOR ROJO -  1.168198  1,848.09"
    (linea,) = extraer_lineas(texto)
    assert linea.cantidad == 1582
    assert linea.descripcion == "PLUMON MARCADOR COLOR ROJO"


def test_separa_la_unidad_pegada_a_la_descripcion():
    texto = ("444400000004  22.  EMP X 500 PAPEL BOND 75 g TAMAÑO A4  10.844100  238.57\n"
             "555500000005  30.  CIENTO SOBRE MANILA TAMAÑO A4  9.156700  274.70")
    papel, sobre = extraer_lineas(texto)
    assert (papel.unidad, papel.descripcion) == ("EMP X 500", "PAPEL BOND 75 g TAMAÑO A4")
    assert (sobre.unidad, sobre.descripcion) == ("CIENTO", "SOBRE MANILA TAMAÑO A4")


def test_ignora_lineas_que_no_son_productos():
    texto = "0021  22.047.0104.0090.2234423.4000036  5 - 18  2.6. 2 2.2 4  1,345.20"
    assert extraer_lineas(texto) == []


def test_igv_incluido_no_incluido_y_sin_verificar():
    assert estado_igv(ORDEN_CON_IGV, 767.0) == "incluido"
    sin_igv = "V. Venta  650.00\nI.G.V.  117.00\nTotal  767.00"
    assert estado_igv(sin_igv, 650.0) == "no incluido"
    exonerada = "V. Venta  650.00\nI.G.V.  0.00\nTotal  650.00"
    assert estado_igv(exonerada, 650.0) == "sin verificar"


def test_construir_precios_sin_datos_personales(tmp_path):
    (tmp_path / "OCAM-X-1-0.txt").write_text(ORDEN_CON_IGV, encoding="utf-8")
    (tmp_path / "OCAM-X-1-0.pdf").write_bytes(b"%PDF")  # no se lee: hay caché de texto
    indice = pd.DataFrame([{
        "orden": "OCAM-X-1-0", "fecha_publicacion": "28/10/2026 17:47:19", "entidad": "ENTIDAD DE PRUEBA",
        "estado_orden": "PAGADA", "fuente": "https://ejemplo/OCAM-X-1.pdf", "fecha_consulta": "2026-11-09",
        "archivo": "OCAM-X-1-0.pdf", "resultado": "ok",
    }])
    precios, informe = construir_precios(indice, tmp_path)
    assert len(precios) == 2
    assert precios.iloc[0]["fecha"] == "2026-10-28"
    assert precios.iloc[0]["precio_unitario"] == 14.16
    assert list(precios.columns) == ["fecha", "entidad", "descripcion", "unidad", "cantidad",
                                     "precio_unitario", "orden", "fuente", "fecha_consulta"]
    assert "IGV incluido" in informe[0]


def test_orden_sin_igv_se_lleva_a_precio_con_igv(tmp_path):
    texto = ("111100000001  10.  UNIDAD  ARCHIVADOR  5.000000  50.00\n"
             "V. Venta  50.00\nI.G.V.  9.00\nTotal  59.00")
    (tmp_path / "A.txt").write_text(texto, encoding="utf-8")
    indice = pd.DataFrame([{"orden": "A", "fecha_publicacion": "01/06/2026 10:00:00", "entidad": "E",
                            "estado_orden": "PAGADA", "fuente": "u", "fecha_consulta": "2026-11-09",
                            "archivo": "A.pdf", "resultado": "ok"}])
    precios, _ = construir_precios(indice, tmp_path)
    assert precios.iloc[0]["precio_unitario"] == 5.9


def test_leer_exportacion_junta_nombres_partidos(tmp_path):
    cabecera = "|".join(f"c{i}" for i in range(26))
    fila = "|".join(["1", "AM", "20", "EMPRESA &#x0D;"]) + "\n" + "|".join(["LIMITADA"] + ["x"] * 22)
    ruta = tmp_path / "exportacion.csv"
    ruta.write_text("﻿" + cabecera + "\n" + fila + "\n", encoding="utf-8")
    df, descartadas = leer_exportacion(ruta)
    assert len(df) == 1 and descartadas == 0
    assert df.iloc[0]["c3"] == "EMPRESA  LIMITADA"


def test_muestra_fija_y_solo_ordenes_validas():
    df = pd.DataFrame({
        "Estado de la Orden Electrónica": ["PAGADA", "ACEPTADA", "RESUELTA", "PAGADA"],
        "Orden Digitalizada": ["a.pdf", "b.pdf", "c.pdf", "https://x/"],
    })
    muestra = elegir_muestra(df, 10)
    assert sorted(muestra["Orden Digitalizada"]) == ["a.pdf", "b.pdf"]
    assert elegir_muestra(df, 1).equals(elegir_muestra(df, 1))


def test_url_segura_codifica_espacios():
    url = "https://servidor/uploads/OCAM-1_28-10-26 17-47-19_FISICA.pdf"
    assert url_segura(url) == "https://servidor/uploads/OCAM-1_28-10-26%2017-47-19_FISICA.pdf"
