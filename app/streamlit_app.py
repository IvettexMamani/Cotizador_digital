"""Cotizador Digital: aplicación Streamlit (punto de entrada).

Los 6 pasos del flujo: subir, leer, extraer requisitos, cruce con catálogo,
precio, y confirmación con PDF.

Ejecutar desde la raíz del repo:
    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

import truststore

truststore.inject_into_ssl()  # certificados del sistema (un antivirus puede interceptar HTTPS)

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # para importar ai/ y backend/ desde app/


def _descargar_modulos_cambiados() -> None:
    """Streamlit vuelve a ejecutar este archivo cuando cambia, pero deja en memoria los módulos de
    ai/ y backend/ que ya importó. Si alguno cambió en disco (por ejemplo, cuando Streamlit Cloud
    trae una versión nueva de GitHub), se descargan todos y las importaciones de abajo leen la versión
    nueva. Así no hace falta reiniciar la app a mano después de cada actualización."""
    propios = {nombre: modulo for nombre, modulo in sys.modules.items()
               if nombre.split(".")[0] in ("ai", "backend") and getattr(modulo, "__file__", None)}
    registro = getattr(sys, "_cotizador_mtimes", None)
    if registro is None:  # primera vez en este proceso: no se sabe qué versión está cargada
        cambiados = bool(propios)
    else:  # un módulo sin registro se importó después (import diferido): se toma como actual
        cambiados = any(nombre in registro and registro[nombre] != Path(modulo.__file__).stat().st_mtime
                        for nombre, modulo in propios.items())
    if cambiados:
        for nombre in propios:
            del sys.modules[nombre]
    sys._cotizador_mtimes = {} if cambiados or registro is None else registro


def _registrar_modulos() -> None:
    registro = sys._cotizador_mtimes
    for nombre, modulo in list(sys.modules.items()):
        if nombre.split(".")[0] in ("ai", "backend") and getattr(modulo, "__file__", None):
            registro.setdefault(nombre, Path(modulo.__file__).stat().st_mtime)


_descargar_modulos_cambiados()

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")  # antes de importar el extractor: define la clave y el modelo

from ai.extractor import MODELO, ErrorExtraccion, extraer_requisitos, hay_clave, huella  # noqa: E402
from backend.catalogo import (EXTENSIONES_CATALOGO, ErrorCatalogo, cargar_catalogo,  # noqa: E402
                              leer_catalogo_subido, plantilla_excel, ruta_catalogo)
from backend.cruce import CUMPLE, NO_CUMPLE, ORDEN_ESTADO, REVISAR, cruzar  # noqa: E402
from backend.ejemplo_sintetico import FOTO_PRODUCTO as FOTO_EJEMPLO  # noqa: E402
from backend.formato_entidad import CondicionesOferta, anchos_paginas, leer_formato, llenar, planificar  # noqa: E402
from backend.foto_producto import evaluar_foto, tiene_texto  # noqa: E402
from backend.grafico_precio import grafico_precio  # noqa: E402
from backend.lectura import EXTENSIONES_ADMITIDAS, leer_documento  # noqa: E402
from backend.pdf import (Cotizacion, DatosProveedor, LineaCotizacion, generar_pdf,  # noqa: E402
                         pendientes, por_confirmar)
from backend.precio import (IGV, con_igv, piso_unitario, precio_con_margen, precio_sugerido,  # noqa: E402
                            referencia_estado, repartir_flete, semaforo)
from backend.precios import PRECIOS_ESTADO, buscar_precios, cargar_precios_estado, terminos_por_defecto  # noqa: E402

_registrar_modulos()

DIAGRAMA = RAIZ / "docs" / "flujo_demo.png"
CARPETA_SOLICITUDES = RAIZ / "data" / "solicitudes"

ONE_LINER = (
    "Preparamos cotizaciones listas para firmar para mypes proveedoras del "
    "Estado peruano, mediante IA que lee la solicitud de cotización y la cruza "
    "con su catálogo de productos."
)

PASOS = ["Elegir solicitud", "Leer documento", "Extraer requisitos", "Cruce con catálogo",
         "Fijar precio", "Confirmar y PDF"]
SEMAFORO = {"verde": (st.success, "🟢 Verde"), "amarillo": (st.warning, "🟡 Amarillo"),
            "rojo": (st.error, "🔴 Rojo"), "gris": (st.info, "⚪ Sin referencia")}

SIMBOLOS = {">=": "≥", "<=": "≤", "=": "=", ">": ">", "<": "<", "incluye": "incluye"}
METODOS = {"pdfplumber": "pdfplumber", "ocr": "OCR · PaddleOCR", "mixto": "pdfplumber + OCR"}
ESTADO_ICONO = {CUMPLE: "✅ cumple", REVISAR: "⚠️ revisar", NO_CUMPLE: "❌ no cumple"}
# Verde = cumple; rojo = revisar o no cumple (regla de oro). Texto oscuro para que se lea en tema claro y oscuro.
COLORES = {CUMPLE: "background-color: #e6f4ea; color: #14532d",
           REVISAR: "background-color: #fde8e8; color: #7f1d1d",
           NO_CUMPLE: "background-color: #fde8e8; color: #7f1d1d"}


# ---------------------------------------------------------------- funciones con caché

@st.cache_data(show_spinner=False)
def leer(nombre: str, contenido: bytes):
    return leer_documento(nombre, contenido)


@st.cache_data(show_spinner=False)
def extraer(texto: str, contenido: bytes, nombre: str):
    # En caché: si se vuelve a procesar el mismo documento no se paga otra llamada al LLM.
    return extraer_requisitos(texto, contenido, nombre)


@st.cache_data(show_spinner=False)
def leer_catalogo(ruta: str, modificado: float):
    # "modificado" es parte de la clave de la caché: si el CSV cambia, se vuelve a leer.
    return cargar_catalogo(Path(ruta))


@st.cache_data(show_spinner=False)
def leer_precios_estado(modificado: float):
    return cargar_precios_estado()


@st.cache_data(show_spinner=False)
def leer_formato_entidad(nombre: str, contenido: bytes):
    # En caché: si el formato es escaneado, el OCR se hace una sola vez.
    return leer_formato(nombre, contenido)


def formato_cantidad(valor: float) -> str:
    return f"{valor:,.0f}" if float(valor).is_integer() else f"{valor:,.2f}"


def mostrar_foto_producto(item):
    """Paso 4 (opción): un bien que no está en el catálogo, a partir de la foto de su etiqueta.

    Devuelve su evaluación cuando el proveedor ya indicó costo y stock; si no, None.
    """
    # Si ya hay una foto en uso, la sección queda abierta (si no, se cerraría en cada recarga)
    en_uso = (st.session_state.get(f"foto_{item.numero}") is not None
              or bool(st.session_state.get(f"foto_ejemplo_{item.numero}")))
    with st.expander("📷 ¿Ofreces un bien que no está en tu catálogo? Sube la foto de su etiqueta",
                     expanded=en_uso):
        st.caption("Se lee con OCR lo que está **impreso** en la etiqueta, el empaque o la ficha técnica, y se "
                   "compara con los requisitos del ítem. Solo cuenta lo que se puede leer: lo demás queda en "
                   "rojo (regla de oro).")
        archivo = st.file_uploader("Foto (PNG o JPG)", type=["png", "jpg", "jpeg"], key=f"foto_{item.numero}")
        usar_ejemplo = FOTO_EJEMPLO.exists() and archivo is None and st.checkbox(
            "Usar la foto de ejemplo (etiqueta ficticia de un archivador)", key=f"foto_ejemplo_{item.numero}")
        if archivo is not None:
            nombre, contenido = archivo.name, archivo.getvalue()
        elif usar_ejemplo:
            nombre, contenido = FOTO_EJEMPLO.name, FOTO_EJEMPLO.read_bytes()
        else:
            return None

        with st.spinner("Leyendo la foto (la primera vez el OCR carga el modelo y tarda más)..."):
            lectura = leer(nombre, contenido)
        texto = lectura.texto.replace("=== Página 1 ===", "").strip()
        if not tiene_texto(texto):
            st.error("No se lee texto en la foto. Una foto del producto sin texto no prueba sus "
                     "especificaciones: sube la foto de la etiqueta, del empaque o de la ficha técnica.")
            return None
        st.text_area("Texto leído en la foto", texto, height=140, disabled=True, key=f"texto_foto_{item.numero}")

        c1, c2 = st.columns(2)
        producto = c1.text_input("Nombre del producto", placeholder="Ej.: Archivador de palanca lomo ancho",
                                 key=f"foto_producto_{item.numero}")
        marca = c2.text_input("Marca y modelo (como figura en la etiqueta)", key=f"foto_marca_{item.numero}")
        costo = c1.number_input("Tu costo unitario (S/)", min_value=0.0, value=None, step=0.10, format="%.2f",
                                key=f"foto_costo_{item.numero}")
        stock = c2.number_input("Stock disponible", min_value=0.0, value=None, step=1.0, format="%.0f",
                                key=f"foto_stock_{item.numero}")

        marca = marca.strip() or ("etiqueta de EJEMPLO, producto ficticio" if usar_ejemplo else "")
        evaluacion = evaluar_foto(item, texto, nombre, producto.strip(), marca,
                                  costo or 0.0, stock or 0.0, es_ejemplo=usar_ejemplo)
        estados = [r.estado for r in evaluacion.resultados]
        st.markdown(f"**Verificación con lo leído en la foto:** {ESTADO_ICONO[evaluacion.estado]}")
        st.dataframe(pd.DataFrame([
            {"Requisito": r.atributo, "Exigido": r.exigido, "Leído en la foto": r.ofrecido or "— no se lee —",
             "Estado": ESTADO_ICONO[r.estado], "Fuente del dato": r.fuente or "— sin fuente —",
             "Observación": r.motivo}
            for r in evaluacion.resultados
        ]).style.apply(lambda fila: [COLORES[estados[fila.name]]] * len(fila), axis=1),
            hide_index=True, width="stretch")

        if evaluacion.estado == NO_CUMPLE:
            st.error("Según lo leído en la foto, este bien **no cumple** algún requisito: no se puede ofrecer.")
            return None
        if costo is None or stock is None:
            st.info("Ingresa tu costo y tu stock para poder ofrecer este bien en la cotización.")
            return None
        st.success("Listo: puedes elegirlo abajo, en «Producto a ofrecer».")
        return evaluacion


def elegir_catalogo():
    """Paso 4: el catálogo del proyecto (de ejemplo o data/catalogo.csv) o el que sube el proveedor.

    El catálogo subido se usa solo en esta sesión: no se guarda en el servidor ni en GitHub.
    """
    ruta = ruta_catalogo()
    propio = f"Catálogo del proyecto (data/{ruta.name})" if ruta.name == "catalogo.csv" else "Catálogo de ejemplo"
    origen = st.radio("¿Con qué catálogo cruzo los requisitos?", [propio, "Subir mi catálogo"],
                      horizontal=True, key="origen_catalogo")

    if origen == "Subir mi catálogo":
        c1, c2 = st.columns([3, 1])
        c1.caption("CSV o Excel con **una fila por cada dato técnico** del producto, cada una con su fuente. "
                   "Se usa solo en esta sesión: no se guarda en el servidor ni en GitHub.")
        c2.download_button("⬇️ Descargar plantilla", data=plantilla_excel(), file_name="plantilla_catalogo.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        archivo = st.file_uploader("Tu catálogo (CSV o Excel)", type=[e.lstrip(".") for e in EXTENSIONES_CATALOGO],
                                   key="catalogo_subido")
        if archivo is None:
            st.info("Sube tu catálogo para cruzarlo con los requisitos. Si no tienes uno, descarga la plantilla, "
                    "o usa el catálogo de ejemplo.")
            return None
        try:
            catalogo = leer_catalogo_subido(archivo.name, archivo.getvalue())
        except ErrorCatalogo as error:
            st.error(f"No se pudo usar tu catálogo: {error}")
            return None
        nombre = archivo.name
    else:
        try:
            catalogo = leer_catalogo(str(ruta), ruta.stat().st_mtime)
        except (ErrorCatalogo, OSError) as error:
            st.error(f"No se pudo leer el catálogo `data/{ruta.name}`: {error}")
            return None
        nombre = f"data/{ruta.name}"

    ejemplo = catalogo["es_ejemplo"].str.lower().isin(["si", "sí"]).any()
    st.caption(f"Catálogo: `{nombre}` · {catalogo['sku'].nunique()} productos"
               + (" · ⚠️ incluye productos de EJEMPLO (ficticios)" if ejemplo else ""))
    return catalogo


def mostrar_cruce(solicitud) -> list:
    """Paso 4: ranking de productos y matriz de cumplimiento por ítem.

    Devuelve una lista de (resultado del ítem, producto elegido o None).
    """
    st.header("4. Cruce con tu catálogo")
    catalogo = elegir_catalogo()
    if catalogo is None:
        return []

    seleccion = []
    for resultado in cruzar(solicitud, catalogo):
        item = resultado.item
        st.subheader(f"Ítem {item.numero}: {item.descripcion}")
        st.caption(f"Cantidad solicitada: {formato_cantidad(item.cantidad)} {item.unidad}")
        if resultado.evaluaciones:
            st.dataframe(pd.DataFrame([
                {"Producto": e.producto, "SKU": e.sku, "Estado": ESTADO_ICONO[e.estado],
                 "✅": e.contar(CUMPLE), "⚠️": e.contar(REVISAR), "❌": e.contar(NO_CUMPLE),
                 "Stock": f"{e.stock:,.0f} " + ("✓" if e.stock_suficiente else "✗ insuficiente"),
                 "Costo unit. (S/)": f"{e.costo_unitario:,.2f}"}
                for e in resultado.evaluaciones
            ]), hide_index=True, width="stretch")
            if not resultado.aptas:
                st.error("Ningún producto de tu catálogo cumple los requisitos de este ítem.")
        else:
            st.error("No hay productos de esta categoría en tu catálogo.")

        de_la_foto = mostrar_foto_producto(item)
        aptas = resultado.aptas + ([de_la_foto] if de_la_foto and de_la_foto.estado != NO_CUMPLE else [])
        aptas.sort(key=lambda e: (ORDEN_ESTADO[e.estado], not e.stock_suficiente, e.costo_unitario))
        if not aptas:
            seleccion.append((resultado, None))
            continue

        por_etiqueta = {f"{e.sku} · {e.producto} ({e.estado})": e for e in aptas}
        etiqueta = st.selectbox("Producto a ofrecer (el primero es el recomendado)", list(por_etiqueta),
                                key=f"producto_item_{item.numero}")
        elegido = por_etiqueta[etiqueta]
        if elegido.estado == CUMPLE:
            st.success(f"**{elegido.producto}** cumple todos los requisitos y cada dato tiene fuente.")
        else:
            st.warning(f"**{elegido.producto}** tiene {elegido.contar(REVISAR)} dato(s) por revisar (en rojo). "
                       "No entrarán a la cotización hasta que los confirmes.")
        if not elegido.stock_suficiente:
            st.warning(f"Stock insuficiente: tienes {elegido.stock:,.0f} y se piden {formato_cantidad(item.cantidad)}.")

        estados = [r.estado for r in elegido.resultados]
        matriz = pd.DataFrame([
            {"Requisito": r.atributo, "Exigido": r.exigido, "Ofrecido": r.ofrecido or "— sin dato —",
             "Estado": ESTADO_ICONO[r.estado], "Fuente del dato": r.fuente or "— sin fuente —",
             "Observación": r.motivo}
            for r in elegido.resultados
        ])
        st.markdown("**Matriz de cumplimiento**")
        st.dataframe(matriz.style.apply(lambda fila: [COLORES[estados[fila.name]]] * len(fila), axis=1),
                     hide_index=True, width="stretch")
        seleccion.append((resultado, elegido))

    return seleccion


def mostrar_precio(seleccion) -> tuple[dict[int, float], bool]:
    """Paso 5: tarjeta de precio por ítem. Devuelve (precio unitario sin IGV por ítem, ¿agregar IGV?)."""
    st.header("5. Precio")
    st.caption("El margen y el flete son datos de tu negocio: los defines tú. "
               "Los precios del Estado se comparan con tu precio final, el que pagaría la entidad.")
    c1, c2, c3 = st.columns(3)
    margen = c1.number_input("Margen (%)", min_value=0.0, max_value=500.0, value=None, step=1.0,
                             placeholder="Tu margen habitual", key="margen")
    flete = c2.number_input("Flete total de la entrega (S/)", min_value=0.0, value=None, step=10.0,
                            placeholder="0 si no hay flete", key="flete",
                            help="Se reparte entre los ítems en proporción a su valor (costo × cantidad).")
    aplicar_igv = c3.checkbox(f"Agregar IGV ({IGV:.0%})", value=True, key="igv",
                              help="Desmárcalo si tu empresa no está afecta al IGV.")

    precios_df = leer_precios_estado(PRECIOS_ESTADO.stat().st_mtime if PRECIOS_ESTADO.exists() else 0.0)
    if precios_df.empty:
        st.info("Todavía no hay precios del Estado cargados (`data/precios_estado.csv`). "
                "La tarjeta funciona igual, pero sin referencia.")

    cotizables = [(r, e) for r, e in seleccion if e is not None]
    if not cotizables:
        st.warning("No hay ítems con un producto apto para cotizar.")
        return {}, aplicar_igv
    if margen is None or flete is None:
        st.info("Ingresa tu margen y el flete para calcular los precios.")
        return {}, aplicar_igv

    precios = {}
    fletes = repartir_flete(flete, [e.costo_unitario * r.item.cantidad for r, e in cotizables])
    for (resultado, elegido), flete_item in zip(cotizables, fletes):
        item = resultado.item
        st.subheader(f"Ítem {item.numero}: {item.descripcion}")
        # Todo en la base del precio final (con IGV si corresponde), igual que los precios del Estado
        piso = con_igv(piso_unitario(elegido.costo_unitario, flete_item, item.cantidad), aplicar_igv)
        propio = con_igv(precio_con_margen(piso_unitario(elegido.costo_unitario, flete_item, item.cantidad),
                                           margen / 100), aplicar_igv)

        terminos = st.text_input("Buscar bienes similares en los precios del Estado",
                                 value=terminos_por_defecto(item.descripcion), key=f"terminos_{item.numero}")
        ordenes = buscar_precios(precios_df, terminos)
        referencia = referencia_estado(ordenes["precio_unitario"].tolist())
        sugerido = precio_sugerido(propio, piso, referencia)

        base = " (con IGV)" if aplicar_igv else ""
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"Costo + flete{base}", f"S/ {piso:,.2f}")
        m2.metric(f"Con tu margen{base}", f"S/ {propio:,.2f}")
        m3.metric("Mediana del Estado", f"S/ {referencia.mediana:,.2f}" if referencia else "—")
        m4.metric("Precio sugerido", f"S/ {sugerido:,.2f}")

        # La clave cambia con los parámetros: si cambian, el precio vuelve al sugerido
        final = st.number_input(f"Precio unitario final{base} (S/)", min_value=0.0, value=round(sugerido, 2),
                                step=0.10, format="%.2f",
                                key=f"precio_{item.numero}_{elegido.sku}_{margen}_{flete}_{aplicar_igv}_{terminos}")
        luz = semaforo(final, piso, referencia)
        mostrar, etiqueta = SEMAFORO[luz.color]
        mostrar(f"**{etiqueta}.** {luz.mensaje}")

        if referencia is None:
            st.caption(f"Sin órdenes del Estado que coincidan con «{terminos}».")
        else:
            if referencia.debil:
                st.warning(f"Referencia débil: solo {referencia.n_ordenes} órdenes. Úsala con cautela.")
            st.plotly_chart(grafico_precio(ordenes, referencia, final), key=f"grafico_{item.numero}")
            with st.expander(f"Ver las {referencia.n_ordenes} órdenes de compra"):
                st.caption("Precios unitarios con IGV. Revisa que la unidad sea la misma que cotizas "
                           "(por ejemplo, resma de 500 hojas y no millar).")
                st.dataframe(ordenes[["fecha", "entidad", "descripcion", "unidad", "cantidad", "precio_unitario",
                                      "fuente"]],
                             hide_index=True, width="stretch")
        precios[item.numero] = final / (1 + IGV) if aplicar_igv else final
    return precios, aplicar_igv


def mostrar_confirmacion(solicitud, seleccion, precios, aplicar_igv, extraccion, documento) -> bool:
    """Paso 6: resumen, confirmación de lo que está en rojo y PDF. Devuelve True si el PDF está listo."""
    st.header("6. Confirmación y PDF")
    with st.expander("Datos de tu empresa para el PDF (opcional: no se guardan)"):
        c1, c2 = st.columns(2)
        proveedor = DatosProveedor(
            razon_social=c1.text_input("Razón social", key="razon_social"),
            ruc=c2.text_input("RUC", key="ruc"),
            direccion=c1.text_input("Dirección", key="direccion"),
            telefono=c2.text_input("Teléfono", key="telefono"),
            correo=c1.text_input("Correo", key="correo"),
            representante=c2.text_input("Representante legal", key="representante"),
        )

    lineas = [LineaCotizacion(r.item, e, precios.get(r.item.numero)) for r, e in seleccion]
    confirmados = set()
    for linea in lineas:
        item = linea.item
        st.markdown(f"**Ítem {item.numero}: {item.descripcion}**")
        if linea.evaluacion is None:
            st.error("No se cotiza: no hay un producto apto en tu catálogo.")
            continue
        e = linea.evaluacion
        estados = [r.estado for r in e.resultados]
        resumen = pd.DataFrame([
            {"Requisito": r.atributo, "Dato ofrecido": r.ofrecido or "— sin dato —",
             "Fuente": r.fuente or "— sin fuente —", "Estado": ESTADO_ICONO[r.estado]}
            for r in e.resultados
        ])
        st.dataframe(resumen.style.apply(lambda fila: [COLORES[estados[fila.name]]] * len(fila), axis=1),
                     hide_index=True, width="stretch")
        for clave, descripcion in por_confirmar(linea):
            if st.checkbox(f"🔴 Confirmo bajo mi responsabilidad: {descripcion}",
                           key=f"confirmo_{item.numero}_{e.sku}_{clave}"):
                confirmados.add((item.numero, clave))

    responsable = st.checkbox("**Revisé y me hago responsable** de la información de esta cotización.",
                              key="responsable")
    cotizacion = Cotizacion(solicitud, lineas, proveedor, aplicar_igv, confirmados, responsable)

    if extraccion.modo == "ia" and extraccion.uso and extraccion.uso.costo_usd is not None:
        st.caption(f"Costo de IA de esta cotización: US$ {extraccion.uso.costo_usd:.4f} "
                   f"({extraccion.uso.tokens_entrada + extraccion.uso.tokens_salida:,} tokens).")
    else:
        st.caption("Modo demo: esta cotización no tuvo costo de IA (resultado precalculado).")

    faltan = pendientes(cotizacion)
    if faltan:
        st.error("**El PDF todavía no se puede generar.** Falta:\n" + "\n".join(f"- {f}" for f in faltan))
        st.button("📄 Descargar cotización (PDF)", disabled=True, key="pdf_bloqueado")
        return False

    total = cotizacion.subtotal + cotizacion.igv
    st.success(f"Todo revisado. Total de la cotización: **S/ {total:,.2f}**"
               + (f" (incluye IGV de S/ {cotizacion.igv:,.2f})" if aplicar_igv else " (sin IGV)") + ".")
    nombre_pdf = "cotizacion_" + "".join(c if c.isalnum() else "_" for c in (solicitud.numero_solicitud or "solicitud"))
    st.download_button("📄 Descargar cotización (PDF)", data=generar_pdf(cotizacion),
                       file_name=f"{nombre_pdf}.pdf", mime="application/pdf", type="primary", key="pdf")
    st.caption("Revisa el PDF, fírmalo y preséntalo tú. La herramienta no firma ni envía nada.")
    mostrar_formato_entidad(cotizacion, documento)
    return True


def mostrar_formato_entidad(cotizacion, documento) -> None:
    """Paso 6 (opción): completar el formato de la entidad, escribiendo encima del PDF original."""
    st.subheader("Formato de la entidad (opcional)")
    st.caption("Si la entidad pide responder en su propio formato (por ejemplo, la solicitud de cotización del "
               "SIGA, que se llena en el mismo documento), la app escribe encima del PDF original los datos ya "
               "verificados. Lo que no sabe queda en blanco y la firma nunca se llena.")
    nombre_doc, contenido_doc = documento
    opciones = (["Completar la solicitud del paso 1"] if contenido_doc is not None else []) +         ["Subir el formato de la entidad"]
    origen = st.radio("¿Qué formato completo?", opciones, horizontal=True, key="origen_formato")
    if origen == "Subir el formato de la entidad":
        archivo = st.file_uploader("Formato de la entidad (PDF o foto)", type=["pdf", "png", "jpg", "jpeg"],
                                   key="formato_subido")
        if archivo is None:
            return
        nombre, contenido = archivo.name, archivo.getvalue()
    else:
        nombre, contenido = nombre_doc, contenido_doc

    with st.expander("Condiciones de tu oferta (las que pida el formato)", expanded=True):
        st.caption("Escribe solo lo que ofreces. Lo que dejes vacío queda en blanco en el formato.")
        c1, c2 = st.columns(2)
        condiciones = CondicionesOferta(
            forma_pago=c1.text_input("Forma de pago", key="cond_pago", placeholder="Ej.: a la conformidad"),
            garantia=c2.text_input("Garantía", key="cond_garantia"),
            plazo_entrega=c1.text_input("Plazo de entrega", key="cond_plazo", placeholder="Ej.: 10 días calendario"),
            validez=c2.text_input("Validez de la cotización", key="cond_validez", placeholder="Ej.: 30 días"),
        )
    with st.spinner("Leyendo el formato (si es escaneado, con OCR)..."):
        pdf_formato, paginas = leer_formato_entidad(nombre, contenido)
    plan = planificar(paginas, anchos_paginas(pdf_formato), cotizacion, condiciones)
    if not plan.reconocido:
        st.warning("No reconocí la tabla de precios de este formato (busco una columna «VALOR TOTAL», «PRECIO "
                   "TOTAL» o «IMPORTE TOTAL» y la descripción de cada ítem). Presenta el PDF de la cotización.")
        return
    for aviso in plan.avisos:
        st.warning(aviso)
    filas = [{"Campo del formato": e.campo, "Se escribe": e.texto, "De dónde sale": e.fuente}
             for e in plan.escrituras]
    filas += [{"Campo del formato": c, "Se escribe": "— queda en blanco —", "De dónde sale": "La app no tiene ese dato"}
              for c in plan.en_blanco]
    tabla = pd.DataFrame(filas)
    en_blanco = tabla["Se escribe"] == "— queda en blanco —"
    st.dataframe(tabla.style.apply(lambda fila: [COLORES[REVISAR] if en_blanco[fila.name] else ""] * len(fila),
                                   axis=1), hide_index=True, width="stretch")
    for falta in plan.no_ubicados:
        st.info(falta)
    st.download_button("📝 Descargar el formato completado (PDF)", data=llenar(pdf_formato, plan),
                       file_name=f"{Path(nombre).stem}_completado.pdf", mime="application/pdf", key="formato_pdf")
    st.caption("Lo que escribió la app está en azul. Revísalo, fírmalo y preséntalo tú.")


def mostrar_avance(contenedor, hechos: list[bool]) -> None:
    """Barra lateral: ✅ pasos hechos, 👉 el que sigue, ⚪ los pendientes."""
    siguiente = next((i for i, hecho in enumerate(hechos) if not hecho), None)
    with contenedor:
        for i, (nombre, hecho) in enumerate(zip(PASOS, hechos)):
            if hecho:
                st.markdown(f"✅ {i + 1}. {nombre}")
            elif i == siguiente:
                st.markdown(f"👉 **{i + 1}. {nombre}**")
            else:
                st.markdown(f"⚪ {i + 1}. {nombre}")
        if siguiente is None:
            st.caption("Cotización lista para descargar.")


def ejemplos_disponibles() -> list[Path]:
    # El PDF digital va primero: es el más rápido para empezar la demo
    return sorted((p for p in CARPETA_SOLICITUDES.iterdir() if p.suffix.lower() in EXTENSIONES_ADMITIDAS),
                  key=lambda p: (p.name != "ejemplo_sintetico.pdf", p.name))


# ---------------------------------------------------------------- encabezado y barra lateral

st.set_page_config(page_title="Cotizador Digital", page_icon="📄", layout="wide")

with st.sidebar:
    st.header("Cotizador Digital")
    if hay_clave():
        st.success(f"🤖 IA activa · modelo `{MODELO}`")
    else:
        st.warning("🧪 **Modo demo sin clave.** Se usan resultados precalculados de las solicitudes de ejemplo.")
    st.markdown("**Tu avance**")
    avance = st.container()  # se llena al final, cuando ya se sabe qué pasos están hechos
    if DIAGRAMA.exists():
        with st.expander("Ver diagrama del flujo"):
            st.image(str(DIAGRAMA), width="stretch")

st.title("Cotizador Digital")
st.caption(ONE_LINER)
st.error(
    "**Regla de oro:** ningún dato técnico entra a la cotización sin una fuente. "
    "Lo que no está verificado se marca en rojo y el PDF no se genera hasta que "
    "el proveedor lo revise y confirme."
)

# ---------------------------------------------------------------- 1. subir solicitud

st.header("1. Solicitud de cotización")
origen = st.radio("¿Qué solicitud quieres cotizar?", ["Usar una de ejemplo", "Subir mi archivo"],
                  horizontal=True)

nombre, contenido = None, None
if origen == "Usar una de ejemplo":
    ejemplos = {p.name: p for p in ejemplos_disponibles()}
    if ejemplos:
        nombre = st.selectbox("Solicitud de ejemplo", list(ejemplos))
        contenido = ejemplos[nombre].read_bytes()
    else:
        st.info("No hay solicitudes en data/solicitudes/.")
else:
    archivo = st.file_uploader("PDF digital, PDF escaneado o foto",
                               type=[e.lstrip(".") for e in sorted(EXTENSIONES_ADMITIDAS)])
    if archivo is not None:
        nombre, contenido = archivo.name, archivo.getvalue()

# Si cambia el documento, se borran los resultados del anterior.
if contenido is not None and st.session_state.get("huella") != huella(contenido):
    for clave in ("huella", "lectura", "extraccion", "error"):
        st.session_state.pop(clave, None)

if contenido is not None and st.button("Leer y extraer requisitos", type="primary"):
    st.session_state["huella"] = huella(contenido)
    with st.status("Procesando la solicitud...", expanded=True) as estado:
        try:
            st.write("Leyendo el documento (la primera lectura con OCR carga el modelo y tarda más)...")
            lectura = leer(nombre, contenido)
            st.session_state["lectura"] = lectura
            st.write("Extrayendo los requisitos...")
            st.session_state["extraccion"] = extraer(lectura.texto, contenido, nombre)
            estado.update(label="Solicitud procesada", state="complete", expanded=False)
        except (ErrorExtraccion, ValueError) as error:
            st.session_state["error"] = str(error)
            estado.update(label="No se pudo procesar la solicitud", state="error")

if "error" in st.session_state:
    st.error(st.session_state["error"])

# ---------------------------------------------------------------- 2. lectura

lectura = st.session_state.get("lectura")
if lectura is not None:
    st.header("2. Lectura del documento")
    c1, c2, c3 = st.columns(3)
    c1.metric("Método", METODOS[lectura.metodo])
    c2.metric("Páginas", lectura.n_paginas)
    c3.metric("Confianza del OCR",
              f"{lectura.confianza_ocr:.0%}" if lectura.confianza_ocr is not None else "No aplica")
    for aviso in lectura.avisos:
        st.warning(aviso)
    with st.expander("Ver el texto leído"):
        st.text(lectura.texto)

# ---------------------------------------------------------------- 3. requisitos

resultado = st.session_state.get("extraccion")
seleccion, precios, pdf_listo = [], {}, False
if resultado is not None:
    solicitud = resultado.solicitud
    st.header("3. Requisitos extraídos")

    if resultado.modo == "demo":
        st.warning(f"🧪 {resultado.aviso}")
    elif resultado.uso is not None:
        uso = resultado.uso
        costo = f" · US$ {uso.costo_usd:.4f}" if uso.costo_usd is not None else ""
        st.success(f"🤖 Extraído con `{uso.modelo}` · {uso.tokens_entrada:,} tokens de entrada, "
                   f"{uso.tokens_salida:,} de salida{costo}")

    datos_generales = pd.DataFrame(
        [
            ("Entidad", solicitud.entidad),
            ("N° de solicitud", solicitud.numero_solicitud),
            ("Objeto", solicitud.objeto),
            ("Plazo de entrega", solicitud.plazo_entrega),
            ("Lugar de entrega", solicitud.lugar_entrega),
            ("Fecha límite", solicitud.fecha_limite),
        ],
        columns=["Dato", "Valor"],
    ).fillna("— no indicado —")
    st.dataframe(datos_generales, hide_index=True, width="stretch")

    st.subheader("Ítems")
    st.dataframe(
        pd.DataFrame(
            [{"Ítem": i.numero, "Descripción": i.descripcion, "Cantidad": formato_cantidad(i.cantidad),
              "Unidad": i.unidad, "N° de requisitos": len(i.requisitos)} for i in solicitud.items]
        ),
        hide_index=True, width="stretch",
    )

    st.subheader("Requisitos técnicos")
    if not any(item.requisitos for item in solicitud.items):
        st.info("El documento no trae especificaciones técnicas por ítem.")
    for item in solicitud.items:  # una tabla por ítem
        st.markdown(f"**Ítem {item.numero}: {item.descripcion}** · "
                    f"{formato_cantidad(item.cantidad)} {item.unidad}")
        if not item.requisitos:
            st.caption("Este ítem no trae especificaciones técnicas.")
            continue
        st.dataframe(
            pd.DataFrame([
                {
                    "Atributo": req.atributo,
                    "Exigencia": f"{SIMBOLOS[req.operador]} {req.valor}" + (f" {req.unidad}" if req.unidad else ""),
                    "Fuente (cita del documento)": req.texto_fuente,
                    "Pág.": req.pagina,
                }
                for req in item.requisitos
            ]),
            hide_index=True, width="stretch",
        )

    col_anexos, col_dudas = st.columns(2)
    with col_anexos:
        st.subheader("Anexos solicitados")
        if solicitud.anexos_solicitados:
            st.markdown("\n".join(f"- {anexo}" for anexo in solicitud.anexos_solicitados))
        else:
            st.caption("No se identificaron anexos.")
    with col_dudas:
        st.subheader("Para revisar")
        if solicitud.dudas:
            for duda in solicitud.dudas:
                st.warning(duda)
        else:
            st.caption("El extractor no marcó partes dudosas.")

    seleccion = mostrar_cruce(solicitud)
    if seleccion:
        precios, aplicar_igv = mostrar_precio(seleccion)
        pdf_listo = mostrar_confirmacion(solicitud, seleccion, precios, aplicar_igv, resultado, (nombre, contenido))

mostrar_avance(avance, [
    contenido is not None,
    lectura is not None,
    resultado is not None,
    any(elegido is not None for _, elegido in seleccion),
    bool(precios),
    pdf_listo,
])

st.divider()
st.caption(
    "La herramienta nunca firma ni envía nada: la cotización la revisa, firma y "
    "presenta el proveedor. Proyecto final, Diplomatura en Ciencia de Datos (Q-Lab PUCP)."
)
