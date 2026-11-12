"""Pruebas de la revisión como evaluador (con la solicitud de EJEMPLO SINTÉTICO)."""

import json
from datetime import date
from pathlib import Path

from ai.esquemas import RequisitoTecnico, SolicitudCotizacion
from backend.catalogo import cargar_catalogo
from backend.cruce import cruzar
from backend.pdf import CondicionesOferta, Cotizacion, DatosProveedor, LineaCotizacion
from backend.precio import Semaforo
from backend.revision import ATENCION, OK, PROBLEMA, leer_fecha, leer_plazo, revisar, ruc_valido

RAIZ = Path(__file__).resolve().parent.parent
ANTES_DEL_LIMITE = date(2026, 11, 11)  # la solicitud de ejemplo vence el 16 de noviembre de 2026


def solicitud() -> SolicitudCotizacion:
    datos = json.loads((RAIZ / "data" / "precalculado" / "ejemplo_sintetico.json").read_text(encoding="utf-8"))
    return SolicitudCotizacion.model_validate(datos["solicitud"])


def cotizacion(sol=None, condiciones=None, proveedor=None, cotizar_todo=True) -> Cotizacion:
    sol = sol or solicitud()
    resultados = cruzar(sol, cargar_catalogo(RAIZ / "data" / "catalogo_ejemplo.csv"))
    lineas = [LineaCotizacion(r.item, r.recomendado if cotizar_todo or r.item.numero == 1 else None, 10.0)
              for r in resultados]
    return Cotizacion(sol, lineas, proveedor or DatosProveedor(), True, set(), True,
                      condiciones=condiciones or CondicionesOferta())


def por_tema(observaciones) -> dict:
    return {o.tema: o for o in observaciones}


def test_leer_fecha_en_los_formatos_habituales():
    assert leer_fecha("16 de noviembre de 2026, hasta las 16:00 horas") == date(2026, 11, 16)
    assert leer_fecha("3 de setiembre del 2026") == date(2026, 9, 3)
    assert leer_fecha("05/12/2026 a las 12:00") == date(2026, 12, 5)
    assert leer_fecha("31 de febrero de 2026") is None
    assert leer_fecha("a más tardar el lunes") is None


def test_leer_plazo():
    assert leer_plazo("10 días calendario, contados desde el día siguiente") == (10, "calendario")
    assert leer_plazo("diez (10) días hábiles") == (10, "hábiles")
    assert leer_plazo("15 dias") == (15, None)
    assert leer_plazo("inmediato") is None


def test_ruc_con_digito_verificador():
    assert ruc_valido("20131312955")  # RUC público de la SUNAT
    assert not ruc_valido("20131312956")  # mismo número con otro dígito verificador
    assert not ruc_valido("2013131295")  # 10 dígitos
    assert not ruc_valido("30131312955")  # no empieza con 1 o 2


def test_fecha_limite_vigente_o_vencida():
    assert por_tema(revisar(cotizacion(), hoy=ANTES_DEL_LIMITE))["Fecha límite"].estado == OK
    vencida = por_tema(revisar(cotizacion(), hoy=date(2026, 11, 17)))["Fecha límite"]
    assert vencida.estado == PROBLEMA and "16/11/2026" in vencida.mensaje


def test_documentos_que_faltan():
    faltan = por_tema(revisar(cotizacion(), adjuntos=set(), hoy=ANTES_DEL_LIMITE))["Documentos"]
    assert faltan.estado == PROBLEMA and "Te faltan 5 de 5" in faltan.mensaje
    assert ".;" not in faltan.mensaje and ".." not in faltan.mensaje
    completos = por_tema(revisar(cotizacion(), adjuntos={0, 1, 2, 3, 4}, hoy=ANTES_DEL_LIMITE))["Documentos"]
    assert completos.estado == OK


def test_plazo_de_entrega_contra_los_terminos_de_referencia():
    def plazo(ofrecido):
        return por_tema(revisar(cotizacion(condiciones=CondicionesOferta(plazo_entrega=ofrecido)),
                                hoy=ANTES_DEL_LIMITE))["Plazo de entrega"]
    assert plazo("").estado == ATENCION  # la entidad pide 10 días calendario
    assert plazo("8 días calendario").estado == OK
    assert plazo("15 días calendario").estado == PROBLEMA
    assert plazo("10 días hábiles").estado == ATENCION  # otra unidad: no se compara


def test_dato_confirmado_sin_ficha_tecnica():
    temas = por_tema(revisar(cotizacion(), hoy=ANTES_DEL_LIMITE))
    assert temas["Ítem 1 · respaldo técnico"].estado == OK
    archivador = temas["Ítem 2 · respaldo técnico"]
    assert archivador.estado == ATENCION and "material" in archivador.mensaje


def test_garantia_exigida_en_los_terminos_de_referencia():
    sol = solicitud()
    sol.items[0].requisitos.append(RequisitoTecnico(
        atributo="garantía", operador="incluye", valor="12 meses", unidad=None,
        texto_fuente="Garantía mínima de 12 meses.", pagina=1))
    sin_garantia = por_tema(revisar(cotizacion(sol), hoy=ANTES_DEL_LIMITE))
    assert sin_garantia["Garantía"].estado == ATENCION
    assert "garantía" not in sin_garantia["Condiciones de compra"].mensaje  # no se repite
    con_garantia = revisar(cotizacion(sol, CondicionesOferta(garantia="12 meses")), hoy=ANTES_DEL_LIMITE)
    assert por_tema(con_garantia)["Garantía"].estado == OK


def test_item_sin_cotizar_precio_y_datos_de_la_empresa():
    semaforos = {1: Semaforo("rojo", "Más caro que el máximo pagado por el Estado.")}
    temas = por_tema(revisar(cotizacion(cotizar_todo=False), semaforos=semaforos, hoy=ANTES_DEL_LIMITE))
    assert temas["Ítem 2"].estado == ATENCION  # no se cotiza
    assert temas["Ítem 1 · precio"].estado == PROBLEMA
    assert temas["Datos de tu empresa"].estado == ATENCION  # sin razón social ni RUC

    mal_ruc = DatosProveedor(razon_social="EMPRESA DE EJEMPLO", ruc="20131312956")
    assert por_tema(revisar(cotizacion(proveedor=mal_ruc), hoy=ANTES_DEL_LIMITE))["Datos de tu empresa"].estado \
        == PROBLEMA


def test_ordena_de_lo_mas_grave_a_lo_menos_grave():
    estados = [o.estado for o in revisar(cotizacion(), hoy=date(2026, 12, 1))]
    assert estados == sorted(estados, key=[PROBLEMA, ATENCION, OK].index)
    assert estados[0] == PROBLEMA
