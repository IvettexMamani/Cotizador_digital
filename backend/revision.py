"""Revisión como evaluador (paso 6): lo que miraría el área de logística al recibir la cotización.

En las conversaciones con proveedores, las órdenes se pierden por un detalle:
una especificación que no coincide, un documento que falta o un precio fuera
de mercado. Esta revisión lo detecta antes de enviar.

No inventa reglas: cada observación compara un dato de los términos de
referencia (fecha límite, plazo de entrega, documentos pedidos, garantía
exigida) con lo que ofrece el proveedor, o revisa la propia cotización
(condiciones en blanco, datos confirmados sin ficha técnica, precio frente a
lo que pagó el Estado, RUC). No bloquea la descarga: avisa.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from backend.cruce import CUMPLE
from backend.pdf import MESES, Cotizacion
from backend.precio import Semaforo

OK, ATENCION, PROBLEMA = "ok", "atencion", "problema"
_GRAVEDAD = {PROBLEMA: 0, ATENCION: 1, OK: 2}
_ESTADO_SEMAFORO = {"verde": OK, "amarillo": ATENCION, "rojo": PROBLEMA}
_PESOS_RUC = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


@dataclass
class Observacion:
    tema: str
    estado: str  # OK, ATENCION o PROBLEMA
    mensaje: str


def _normal(texto: str) -> str:
    """Minúsculas y sin tildes, para buscar sin importar cómo se escribió."""
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


_NUMERO_MES = {_normal(m): i for i, m in enumerate(MESES, start=1)} | {"setiembre": 9}


def leer_fecha(texto: str | None) -> date | None:
    """«16 de noviembre de 2026, hasta las 16:00 horas» o «16/11/2026» → fecha; None si no se puede leer."""
    if not texto:
        return None
    t = _normal(texto)
    try:
        if m := re.search(r"(\d{1,2})\s+de\s+([a-z]+)\s+(?:de|del)\s+(\d{4})", t):
            mes = _NUMERO_MES.get(m.group(2))
            return date(int(m.group(3)), mes, int(m.group(1))) if mes else None
        if m := re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", t):
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:  # p. ej., 31 de febrero
        return None
    return None


def leer_plazo(texto: str | None) -> tuple[int, str | None] | None:
    """«10 días calendario» o «diez (10) días hábiles» → (10, 'calendario' | 'hábiles' | None)."""
    if not texto:
        return None
    m = re.search(r"(\d+)\)?\s*dias?(?:\s+(calendarios?|habiles?))?", _normal(texto))
    if not m:
        return None
    tipo = None if m.group(2) is None else ("calendario" if m.group(2).startswith("calendario") else "hábiles")
    return int(m.group(1)), tipo


def ruc_valido(ruc: str) -> bool:
    """11 dígitos y el dígito verificador de SUNAT (módulo 11). No consulta si el RUC está activo."""
    ruc = ruc.replace(" ", "")
    if not re.fullmatch(r"[12]\d{10}", ruc):
        return False
    resto = 11 - sum(int(d) * p for d, p in zip(ruc, _PESOS_RUC)) % 11
    return int(ruc[10]) == resto % 10


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _fecha_limite(cotizacion: Cotizacion, hoy: date) -> Observacion:
    texto = cotizacion.solicitud.fecha_limite
    limite = leer_fecha(texto)
    if not texto:
        return Observacion("Fecha límite", ATENCION,
                           "Los términos de referencia no la indican: revísala en la solicitud de cotización.")
    if limite is None:
        return Observacion("Fecha límite", ATENCION, f"No pude leer la fecha («{texto}»): revísala.")
    if limite < hoy:
        return Observacion("Fecha límite", PROBLEMA,
                           f"Venció el {limite:%d/%m/%Y}: la entidad podría no recibir tu cotización.")
    if limite == hoy:
        return Observacion("Fecha límite", ATENCION, f"Vence hoy: {texto}.")
    return Observacion("Fecha límite", OK,
                       f"{texto} (quedan {_plural((limite - hoy).days, 'día', 'días')}).")


def _documentos(cotizacion: Cotizacion, adjuntos: set[int]) -> Observacion:
    anexos = cotizacion.solicitud.anexos_solicitados
    if not anexos:
        return Observacion("Documentos", ATENCION,
                           "Los términos de referencia no listan documentos: revisa si la solicitud pide anexos.")
    faltan = [a for i, a in enumerate(anexos) if i not in adjuntos]
    if not faltan:
        return Observacion("Documentos", OK, f"Marcaste los {len(anexos)} documentos que pide la entidad.")
    return Observacion("Documentos", PROBLEMA,
                       f"Te faltan {len(faltan)} de {len(anexos)}: {'; '.join(faltan)}. "
                       "Una cotización sin un documento pedido puede quedar fuera.")


def _plazo(cotizacion: Cotizacion) -> Observacion | None:
    pedido = cotizacion.solicitud.plazo_entrega
    ofrecido = cotizacion.condiciones.plazo_entrega.strip()
    if not pedido:
        return Observacion("Plazo de entrega", OK, f"Ofreces {ofrecido}.") if ofrecido else None
    if not ofrecido:
        return Observacion("Plazo de entrega", ATENCION,
                           f"La entidad pide «{pedido}» y tu oferta no indica plazo: "
                           "escríbelo en «Condiciones de tu oferta».")
    p, o = leer_plazo(pedido), leer_plazo(ofrecido)
    if p is None or o is None:
        return Observacion("Plazo de entrega", ATENCION,
                           f"Compáralos tú: la entidad pide «{pedido}» y ofreces «{ofrecido}».")
    if p[1] and o[1] and p[1] != o[1]:
        return Observacion("Plazo de entrega", ATENCION,
                           f"La entidad cuenta días {p[1]} y tú días {o[1]}: compáralos en la misma unidad.")
    if o[0] > p[0]:
        return Observacion("Plazo de entrega", PROBLEMA,
                           f"Ofreces {o[0]} días y la entidad pide {p[0]}: un plazo mayor no cumple "
                           "los términos de referencia.")
    return Observacion("Plazo de entrega", OK, f"Ofreces {ofrecido}, dentro de lo que pide la entidad ({p[0]} días).")


def _garantia_exigida(cotizacion: Cotizacion) -> Observacion | None:
    exigidas = [r for item in cotizacion.solicitud.items for r in item.requisitos
                if "garant" in _normal(r.atributo)]
    if not exigidas:
        return None
    if not cotizacion.condiciones.garantia.strip():
        return Observacion("Garantía", ATENCION,
                           f"Los términos de referencia la piden («{exigidas[0].texto_fuente}») y tu oferta no "
                           "la indica en «Condiciones de tu oferta».")
    return Observacion("Garantía", OK, f"Ofreces: {cotizacion.condiciones.garantia.strip()}.")


def _condiciones_en_blanco(cotizacion: Cotizacion, garantia_revisada: bool) -> Observacion:
    c = cotizacion.condiciones
    campos = [("forma de pago", c.forma_pago), ("validez de la oferta", c.validez)]
    if not garantia_revisada:
        campos.insert(1, ("garantía", c.garantia))
    vacias = [nombre for nombre, valor in campos if not valor.strip()]
    if vacias:
        return Observacion("Condiciones de compra", ATENCION,
                           f"Quedarán en blanco: {', '.join(vacias)}. Complétalas si la entidad las pide.")
    return Observacion("Condiciones de compra", OK, "Indicaste " + ", ".join(n for n, _ in campos) + ".")


def _respaldo_tecnico(cotizacion: Cotizacion) -> list[Observacion]:
    observaciones = []
    for linea in cotizacion.cotizadas:
        resultados = linea.evaluacion.resultados
        sin_ficha = [r.atributo for r in resultados if r.estado != CUMPLE]
        tema = f"Ítem {linea.item.numero} · respaldo técnico"
        if sin_ficha:
            observaciones.append(Observacion(
                tema, ATENCION,
                f"Confirmaste sin ficha técnica: {', '.join(sin_ficha)}. Si el evaluador pide el respaldo, "
                "no lo tendrás: consigue la ficha antes de enviar."))
        else:
            fuentes = {r.fuente for r in resultados if r.fuente}
            observaciones.append(Observacion(
                tema, OK,
                f"Cada requisito tiene su fuente ({_plural(len(fuentes), 'documento', 'documentos')}). "
                "Tenlos a mano por si la entidad los pide."))
    return observaciones


def _items_sin_cotizar(cotizacion: Cotizacion) -> list[Observacion]:
    return [Observacion(f"Ítem {l.item.numero}", ATENCION,
                        f"«{l.item.descripcion}» no se cotiza: revisa si la solicitud acepta cotizar por ítem.")
            for l in cotizacion.lineas if l.evaluacion is None]


def _precios(cotizacion: Cotizacion, semaforos: dict[int, Semaforo]) -> list[Observacion]:
    cotizados = {l.item.numero for l in cotizacion.cotizadas}
    return [Observacion(f"Ítem {numero} · precio", _ESTADO_SEMAFORO[luz.color], luz.mensaje)
            for numero, luz in sorted(semaforos.items())
            if numero in cotizados and luz.color in _ESTADO_SEMAFORO]


def _proveedor(cotizacion: Cotizacion) -> Observacion:
    p = cotizacion.proveedor
    ruc = p.ruc.replace(" ", "")
    if ruc and not ruc_valido(ruc):
        return Observacion("Datos de tu empresa", PROBLEMA,
                           f"El RUC {ruc} no es válido: revisa los 11 dígitos.")
    if not ruc or not p.razon_social.strip():
        return Observacion("Datos de tu empresa", ATENCION,
                           "La cotización saldrá sin razón social o sin RUC: complétalos en «Datos de tu empresa» "
                           "o escríbelos a mano antes de firmar.")
    return Observacion("Datos de tu empresa", OK,
                       "Razón social y RUC completos (el RUC tiene un formato válido; la app no lo consulta en SUNAT).")


def revisar(cotizacion: Cotizacion, adjuntos: set[int] | None = None,
            semaforos: dict[int, Semaforo] | None = None, hoy: date | None = None) -> list[Observacion]:
    """Observaciones del evaluador, de la más grave a la menos grave.

    adjuntos: posiciones de `anexos_solicitados` que el proveedor marcó como listos.
    semaforos: semáforo de precio de cada ítem (paso 5).
    """
    garantia = _garantia_exigida(cotizacion)
    observaciones = [
        _fecha_limite(cotizacion, hoy or date.today()),
        _documentos(cotizacion, adjuntos or set()),
        _plazo(cotizacion),
        garantia,
        _condiciones_en_blanco(cotizacion, garantia_revisada=garantia is not None),
        *_respaldo_tecnico(cotizacion),
        *_items_sin_cotizar(cotizacion),
        *_precios(cotizacion, semaforos or {}),
        _proveedor(cotizacion),
    ]
    return sorted((o for o in observaciones if o is not None), key=lambda o: _GRAVEDAD[o.estado])
