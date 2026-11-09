"""Cotizador Digital: aplicación Streamlit (punto de entrada).

Bloque 1: solo la pantalla de bienvenida. Los pasos del flujo se irán
activando en los bloques siguientes.

Ejecutar desde la raíz del repo:
    streamlit run app/streamlit_app.py
"""

from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
DIAGRAMA = RAIZ / "docs" / "flujo_demo.png"

ONE_LINER = (
    "Preparamos cotizaciones listas para firmar para mypes proveedoras del "
    "Estado peruano, mediante IA que lee la solicitud de cotización y la cruza "
    "con su catálogo de productos."
)

# (número, nombre, qué hace) — el mismo flujo de docs/flujo_demo.png
PASOS = [
    (1, "Subir solicitud", "PDF digital, PDF escaneado o foto."),
    (2, "Leer documento", "Texto con pdfplumber; escaneados con OCR."),
    (3, "Extraer requisitos", "Ítems, atributos, plazos y anexos en JSON validado."),
    (4, "Cruce con catálogo", "Cumple, revisar o no cumple, con la fuente de cada dato."),
    (5, "Fijar precio", "Costo + margen + flete vs. lo que pagó el Estado."),
    (6, "Confirmar y PDF", "Resumen + casilla «Revisé y me hago responsable»."),
]

st.set_page_config(page_title="Cotizador Digital", page_icon="📄", layout="wide")

st.title("Cotizador Digital")
st.subheader(ONE_LINER)

st.error(
    "**Regla de oro:** ningún dato técnico entra a la cotización sin una fuente. "
    "Lo que no está verificado se marca en rojo y el PDF no se genera hasta que "
    "el proveedor lo revise y confirme."
)

st.markdown("### Cómo funciona")
columnas = st.columns(len(PASOS))
for columna, (numero, nombre, detalle) in zip(columnas, PASOS):
    with columna:
        st.markdown(f"**{numero}. {nombre}**")
        st.caption(detalle)
        st.caption("🕓 Próximamente")

if DIAGRAMA.exists():
    with st.expander("Ver el diagrama completo del flujo"):
        st.image(str(DIAGRAMA), width="stretch")

st.divider()
st.caption(
    "La herramienta nunca firma ni envía nada: la cotización la revisa, firma y "
    "presenta el proveedor. Proyecto final, Diplomatura en Ciencia de Datos (Q-Lab PUCP)."
)
