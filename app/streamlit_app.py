"""Cotizador Digital: aplicación Streamlit (punto de entrada).

Bloque 2: pasos 1 a 3 del flujo (subir, leer y extraer requisitos).

Ejecutar desde la raíz del repo:
    streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

import truststore

truststore.inject_into_ssl()  # certificados del sistema (un antivirus puede interceptar HTTPS)

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # para importar ai/ y backend/ desde app/

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(RAIZ / ".env")  # antes de importar el extractor: define la clave y el modelo

from ai.extractor import MODELO, ErrorExtraccion, extraer_requisitos, hay_clave, huella  # noqa: E402
from backend.lectura import EXTENSIONES_ADMITIDAS, leer_documento  # noqa: E402

DIAGRAMA = RAIZ / "docs" / "flujo_demo.png"
CARPETA_SOLICITUDES = RAIZ / "data" / "solicitudes"

ONE_LINER = (
    "Preparamos cotizaciones listas para firmar para mypes proveedoras del "
    "Estado peruano, mediante IA que lee la solicitud de cotización y la cruza "
    "con su catálogo de productos."
)

# (nombre del paso, ¿ya funciona?)
PASOS = [
    ("Subir solicitud", True),
    ("Leer documento", True),
    ("Extraer requisitos", True),
    ("Cruce con catálogo", False),
    ("Fijar precio", False),
    ("Confirmar y PDF", False),
]

SIMBOLOS = {">=": "≥", "<=": "≤", "=": "=", ">": ">", "<": "<", "incluye": "incluye"}
METODOS = {"pdfplumber": "Texto digital (pdfplumber)", "ocr": "OCR (PaddleOCR)",
           "mixto": "Mixto (pdfplumber + OCR)"}


# ---------------------------------------------------------------- funciones con caché

@st.cache_data(show_spinner=False)
def leer(nombre: str, contenido: bytes):
    return leer_documento(nombre, contenido)


@st.cache_data(show_spinner=False)
def extraer(texto: str, contenido: bytes, nombre: str):
    # En caché: si se vuelve a procesar el mismo documento no se paga otra llamada al LLM.
    return extraer_requisitos(texto, contenido, nombre)


def formato_cantidad(valor: float) -> str:
    return f"{valor:,.0f}" if float(valor).is_integer() else f"{valor:,.2f}"


def ejemplos_disponibles() -> list[Path]:
    return sorted(p for p in CARPETA_SOLICITUDES.iterdir() if p.suffix.lower() in EXTENSIONES_ADMITIDAS)


# ---------------------------------------------------------------- encabezado y barra lateral

st.set_page_config(page_title="Cotizador Digital", page_icon="📄", layout="wide")

with st.sidebar:
    st.header("Cotizador Digital")
    if hay_clave():
        st.success(f"🤖 IA activa · modelo `{MODELO}`")
    else:
        st.warning("🧪 **Modo demo sin clave.** Se usan resultados precalculados de las solicitudes de ejemplo.")
    st.markdown("**Flujo**")
    for numero, (nombre, listo) in enumerate(PASOS, start=1):
        st.markdown(f"{'✅' if listo else '🕓'} {numero}. {nombre}")
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
    ejemplos = ejemplos_disponibles()
    if ejemplos:
        elegido = st.selectbox("Solicitud de ejemplo", ejemplos, format_func=lambda p: p.name)
        nombre, contenido = elegido.name, elegido.read_bytes()
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
    filas = [
        {
            "Ítem": item.numero,
            "Atributo": req.atributo,
            "Exigencia": f"{SIMBOLOS[req.operador]} {req.valor}" + (f" {req.unidad}" if req.unidad else ""),
            "Fuente (cita del documento)": req.texto_fuente,
            "Pág.": req.pagina,
        }
        for item in solicitud.items
        for req in item.requisitos
    ]
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True, width="stretch")
    else:
        st.info("El documento no trae especificaciones técnicas por ítem.")

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

    st.info("🕓 Próximo paso (Bloque 3): cruzar estos requisitos con tu catálogo de productos.")

st.divider()
st.caption(
    "La herramienta nunca firma ni envía nada: la cotización la revisa, firma y "
    "presenta el proveedor. Proyecto final, Diplomatura en Ciencia de Datos (Q-Lab PUCP)."
)
