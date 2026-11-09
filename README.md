# Cotizador Digital

> Preparamos cotizaciones listas para firmar para mypes proveedoras del Estado peruano, mediante IA que lee la solicitud de cotización y la cruza con su catálogo de productos.

**Estado:** en construcción. Funcionan los pasos 1 a 3 (subir, leer y extraer requisitos). Este README se completa en el Bloque 5.

## Regla de oro

Ningún dato técnico entra a la cotización sin una fuente. Lo que no está verificado se marca en rojo y el PDF no se genera hasta que el proveedor lo revise y confirme. **La herramienta nunca firma ni envía nada.**

## Flujo de la demo (solo bienes)

![Flujo de la demo](docs/flujo_demo.png)

1. **Subir la solicitud de cotización:** PDF digital, PDF escaneado o foto.
2. **Leerla:** pdfplumber para texto; PaddleOCR para escaneados e imágenes.
3. **Extraer requisitos** con un LLM de salida estructurada, validados con Pydantic.
4. **Cruzar con el catálogo** del proveedor: cumple / revisar / no cumple, con la fuente de cada dato.
5. **Fijar precio:** costo + margen + flete, comparado con lo que pagó el Estado (datos abiertos).
6. **Confirmar y generar el PDF**, listo para imprimir y firmar.

## Cómo correrlo en local

Requiere Python 3.11.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # opcional: agrega tu ANTHROPIC_API_KEY; sin clave corre en modo demo
streamlit run app/streamlit_app.py
```

**Modo demo sin clave:** si no hay `ANTHROPIC_API_KEY` o la API falla, la app usa los resultados guardados en `data/precalculado/` para las solicitudes de ejemplo y lo avisa en pantalla. Así la demo no depende de internet. Para guardar el resultado de una solicitud nueva (requiere clave):

```bash
python -m ai.precalcular data/solicitudes/mi_solicitud.pdf
```

**Pruebas:** `pytest` (todas) o `pytest -m "not lento"` (sin las de OCR).

## Estructura

```
app/        aplicación Streamlit
backend/    lectura, cruce, precios, PDF
ai/         prompts, esquemas Pydantic, extractor LLM, OCR
data/       muestras chicas, sin datos personales
docs/       diagrama, capturas, research/ y agente.md
notebooks/  exploración de precios
tests/      pruebas del cruce y del cálculo de precio
```

## Qué sigue (fuera de la demo)

- Buscador de oportunidades
- Alertas por WhatsApp
- Lectura de correo
- Verificación de RUC y RNP
- Cotizaciones de servicios

## Licencia

[MIT](LICENSE)
