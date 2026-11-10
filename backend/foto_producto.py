"""Paso 4 (opción): ofrecer un bien que no está en el catálogo, a partir de una
foto de su etiqueta, empaque o ficha técnica.

1. El texto de la foto se lee con OCR (backend.lectura -> PaddleOCR).
2. Para cada requisito del ítem se busca en ese texto un dato que lo respalde:
   - Primero en las líneas que nombran el atributo ("Lomo: 8 cm" para "ancho de lomo").
   - Si es un número, se busca una cifra con una unidad compatible
     (80 mm sirve para un requisito en cm).
   - Si es un texto, se busca lo exigido o se toma lo que dice después de ":".
3. Cada requisito se compara con el mismo motor del catálogo (backend.cruce).
   La fuente del dato es la línea leída en la foto.

Regla de oro: solo cuenta lo que está impreso y se pudo leer. Queda en rojo
("revisar") lo que no se lee, lo que se leyó en una línea que no nombra el
atributo y los textos que no coinciden (el OCR o la redacción pueden variar).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai.esquemas import Item, RequisitoTecnico
from backend.cruce import (CONVERSIONES, NO_CUMPLE, REVISAR, SIMBOLOS, EvaluacionProducto,
                           ResultadoRequisito, comparar, normalizar, normalizar_unidad, separar_numero,
                           texto_valor)

MIN_CARACTERES = 15  # menos texto que esto: la foto no tiene datos legibles

# Otras formas de escribir unidades que no están en las conversiones de backend.cruce
ALIAS_UNIDADES = {
    "g/m2": ["g/m2", "gr/m2", "grs/m2", "g/m 2", "gsm"],
    "hojas": ["hojas", "hoja", "hjs"],
}
PALABRAS_VACIAS = {"de", "del", "la", "el", "los", "las", "por", "para", "con", "y"}


@dataclass
class Hallazgo:
    """Lo que se leyó en la foto para un requisito."""
    valor: str
    unidad: str | None
    linea: str      # línea de la foto de donde sale (la fuente)
    nombra_atributo: bool  # la línea menciona el atributo: la asociación es segura


def _palabras_clave(atributo: str) -> list[str]:
    return [p for p in re.findall(r"[a-z0-9]+", normalizar(atributo))
            if len(p) >= 3 and p not in PALABRAS_VACIAS]


def _nombra(linea_normalizada: str, claves: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(c)}", linea_normalizada) for c in claves)


def _unidades_compatibles(unidad: str) -> list[str]:
    """La unidad exigida y las que se pueden convertir a ella, de la más larga a la más corta."""
    u = normalizar_unidad(unidad)
    if u in CONVERSIONES:
        magnitud = CONVERSIONES[u][0]
        candidatas = [x for x, (m, _) in CONVERSIONES.items() if m == magnitud]
    else:
        candidatas = ALIAS_UNIDADES.get(u, [u])
    return sorted(set(candidatas), key=len, reverse=True)


def _numero_con_unidad(linea_normalizada: str, unidad: str) -> tuple[str, str] | None:
    """'lomo ancho: 80 mm' con unidad 'cm' -> ('80', 'mm'). Los alias se devuelven como la unidad exigida."""
    unidades = _unidades_compatibles(unidad)
    patron = "|".join(re.escape(u) for u in unidades)
    m = re.search(rf"(\d+(?:[.,]\d+)?)\s*({patron})(?![a-z0-9])", linea_normalizada)
    if not m:
        return None
    encontrada = m[2]
    if normalizar_unidad(unidad) not in CONVERSIONES:  # alias: g/m 2, gr/m2... -> g/m2
        encontrada = unidad
    return m[1].replace(",", "."), encontrada


def _despues_de(linea: str, claves: list[str]) -> str:
    """Lo que dice la línea después de ':' o, si no hay, sin el nombre del atributo."""
    if ":" in linea:
        return linea.split(":", 1)[1].strip()
    texto = linea
    for c in claves:
        texto = re.sub(rf"\b{re.escape(c)}\w*", "", normalizar(texto))
    return texto.strip(" -")


def buscar(requisito: RequisitoTecnico, texto: str) -> Hallazgo | None:
    """Busca en el texto de la foto el dato que corresponde a un requisito."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    claves = _palabras_clave(requisito.atributo)
    con_nombre = [l for l in lineas if _nombra(normalizar(l), claves)]
    numero_exigido, unidad_en_valor = separar_numero(requisito.valor)
    unidad = requisito.unidad or unidad_en_valor

    if numero_exigido is not None and requisito.operador != "incluye":
        if not unidad:  # número sin unidad: solo en líneas que nombran el atributo
            for linea in con_nombre:
                m = re.search(r"\d+(?:[.,]\d+)?", _despues_de(linea, claves))
                if m:
                    return Hallazgo(m[0].replace(",", "."), None, linea, True)
            return None
        for grupo, seguro in ((con_nombre, True), (lineas, False)):
            for linea in grupo:
                encontrado = _numero_con_unidad(normalizar(linea), unidad)
                if encontrado:
                    return Hallazgo(encontrado[0], encontrado[1], linea, seguro)
        return None

    exigido = normalizar(requisito.valor)
    patron = rf"\b{re.escape(exigido)}\b"
    for linea in con_nombre:  # 1) línea que nombra el atributo
        if re.search(patron, normalizar(linea)):
            return Hallazgo(requisito.valor, None, linea, True)
    if con_nombre:
        dicho = _despues_de(con_nombre[0], claves)
        if dicho:
            return Hallazgo(dicho, None, con_nombre[0], True)
    for linea in lineas:  # 2) el valor exigido en cualquier línea
        if re.search(patron, normalizar(linea)):
            return Hallazgo(requisito.valor, None, linea, False)
    return None


def evaluar_foto(item: Item, texto: str, nombre_archivo: str, producto: str = "", marca_modelo: str = "",
                 costo_unitario: float = 0.0, stock: float = 0.0, es_ejemplo: bool = False) -> EvaluacionProducto:
    """Evalúa los requisitos del ítem con lo leído en la foto, como si fuera un producto del catálogo."""
    evaluacion = EvaluacionProducto(
        sku=f"FOTO-{item.numero}", producto=producto or "Producto de la foto", marca_modelo=marca_modelo,
        unidad_venta=item.unidad, costo_unitario=costo_unitario, stock=stock,
        stock_suficiente=stock >= item.cantidad, es_ejemplo=es_ejemplo,
    )
    for requisito in item.requisitos:
        exigido = texto_valor(f"{SIMBOLOS[requisito.operador]} {requisito.valor}", requisito.unidad)
        hallazgo = buscar(requisito, texto)
        if hallazgo is None:
            evaluacion.resultados.append(ResultadoRequisito(
                requisito.atributo, exigido, None, None, REVISAR,
                "No se lee en la foto: confírmalo o agrega la ficha técnica.", requisito.texto_fuente))
            continue

        estado, motivo = comparar(requisito, hallazgo.valor, hallazgo.unidad)
        es_numero = separar_numero(requisito.valor)[0] is not None
        if not hallazgo.nombra_atributo and estado != REVISAR:
            estado, motivo = REVISAR, (f"Se leyó «{hallazgo.linea}», pero la línea no nombra "
                                       f"«{requisito.atributo}»: verificar.")
        elif estado == NO_CUMPLE and not es_numero:
            estado, motivo = REVISAR, f"La foto dice «{hallazgo.valor}»; se exige «{requisito.valor}»: verificar."
        evaluacion.resultados.append(ResultadoRequisito(
            requisito.atributo, exigido, texto_valor(hallazgo.valor, hallazgo.unidad),
            f"Foto ({nombre_archivo}): «{hallazgo.linea}»", estado, motivo, requisito.texto_fuente))
    return evaluacion


def tiene_texto(texto: str) -> bool:
    return len(re.sub(r"\s+", "", texto or "")) >= MIN_CARACTERES
