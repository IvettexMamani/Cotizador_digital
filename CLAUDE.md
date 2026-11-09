# CLAUDE.md — Cotizador Digital

Contexto esencial para cualquier sesión de Claude Code en este repo. El encargo completo está en `docs/prompt_inicial.md`; el flujo visual, en `docs/flujo_demo.png`. Repo: https://github.com/IvettexMamani/Cotizador_digital

## Quién y para qué

- **Founder:** Ivette Mamani Flores, contadora pública y administradora de contratos en el sector público (Tacna). Trabaja sola. Claude actúa como co-founder técnico.
- **Contexto:** proyecto final de la Diplomatura en Ciencia de Datos (Q-Lab PUCP). Se necesita una **demo que funcione en vivo**, de principio a fin, con datos reales, construida en **un solo día**.
- **One-liner (borrador):** Preparamos cotizaciones listas para firmar para mypes proveedoras del Estado peruano, mediante IA que lee la solicitud de cotización y la cruza con su catálogo de productos.
- **Problema:** las áreas de logística envían solicitudes de cotización (contratos menores, hasta 8 UIT). El proveedor responde a mano (Word/Excel): leer TDR, ver si cumple, buscar ficha técnica, calcular precio, llenar anexos. Muchas quedan sin responder.

## Regla de oro (no negociable)

Ningún dato técnico entra a la cotización sin fuente. Lo no verificado se marca en **rojo** y **bloquea el PDF** hasta que el proveedor lo revise y confirme. La herramienta **nunca firma ni envía** nada.

## El único flujo de la demo (solo bienes)

1. **Subir solicitud** (PDF digital, PDF escaneado o foto) o elegir una de ejemplo — Streamlit.
2. **Leer:** texto con `pdfplumber`; escaneado/imagen con **PaddleOCR** (sesión 10). Carga diferida y con caché.
3. **Extraer requisitos** con LLM de salida estructurada (sesión 08), validado con Pydantic: entidad, objeto, ítems, cantidad, unidad, requisitos técnicos (atributo, operador, valor, unidad), plazo y lugar de entrega, fecha límite, anexos.
4. **Cruce con catálogo** (CSV): por requisito → `cumple` / `revisar` / `no cumple`, con la fuente. Ordenar productos que cumplen por disponibilidad y margen — pandas.
5. **Tarjeta de precio:** costo + margen + flete vs. lo que pagó el Estado (Perú Compras / OECE). Mínimo, mediana, máximo, n° de órdenes en gráfico plotly; precio sugerido y semáforo. Pocos datos → "referencia débil".
6. **Confirmación y PDF:** resumen (requisito, dato ofrecido, fuente) + casilla **"Revisé y me hago responsable"** → recién ahí PDF con fpdf2 (carta, matriz de cumplimiento, precio).

**Fuera de la demo** (solo en README como "qué sigue"): buscador de oportunidades, alertas por WhatsApp, lectura de correo, verificación de RUC y RNP, servicios.

## Stack y decisiones técnicas

- Python **3.11**, Streamlit, pdfplumber, PaddleOCR, Pydantic, pandas, plotly, fpdf2, API de Anthropic.
- **LLM:** antes de programarlo, revisar la documentación oficial (docs.claude.com) para elegir un modelo vigente **económico** y la forma recomendada de obtener JSON estructurado. El costo por cotización es parte del modelo de negocio.
- **Registrar tokens** (entrada/salida) en cada llamada al LLM → costo por cotización en el README.
- **Clave:** en `.env` (local) y en *secrets* del despliegue. **Nunca** en código ni en el repo. `.env.example` solo con nombres de variables.
- **Modo demo sin clave:** sin clave o si falla la API → usar JSON precalculado de las solicitudes de ejemplo y avisarlo en pantalla.
- **Despliegue:** Hugging Face Spaces (PaddleOCR necesita memoria) o Streamlit Community Cloud. Se decide con Ivette en el Bloque 5.

## Datos: solo públicos, sintéticos o de Ivette

- **Solicitudes:** Ivette descarga 3–5 solicitudes públicas reales a `data/solicitudes/`. Nunca documentos internos de una entidad. Mientras tanto: 1 solicitud sintética marcada **"EJEMPLO SINTÉTICO"**.
- **Catálogo:** `data/catalogo_ejemplo.csv` con estructura correcta y pocas filas marcadas como ejemplo. **No inventar especificaciones de modelos reales.** Ivette completa productos reales; cada fila lleva `fuente_url`.
- **Precios del Estado:** priorizar descargas oficiales de datos abiertos (Perú Compras / OECE). `backend/precios.py` carga y limpia CSV/XLSX con pandas. Si una descarga es manual, indicar a Ivette los filtros exactos.
- **Sin datos personales:** si un archivo trae nombres o DNI de personas naturales, eliminar esas columnas antes de guardarlo en `data/`.

## Scraping responsable (sesión 03) — solo como último recurso

1. Primero API, datos abiertos o descarga oficial.
2. `robots.txt` con `urllib.robotparser` por dominio; ruta prohibida → descarga manual.
3. Revisar términos de uso y avisar a Ivette **antes** de programar.
4. ≥ 3 s entre solicitudes al mismo dominio, sin concurrencia, reintentos limitados con espera creciente.
5. User-Agent identificable con nombre del proyecto y URL del repo. **Sin correo personal.**
6. Nada protegido: sin login, sin saltar CAPTCHAs, sin evadir bloqueos.
7. Caché en `data/cache/` (ignorado por git).
8. Solo campos útiles + URL de origen + fecha de consulta.
9. Volumen pequeño (decenas de registros).
10. Documentar en el README qué, de dónde, cuándo y bajo qué reglas.

## Estructura del repo

```
README.md  LICENSE (MIT)  CLAUDE.md  requirements.txt  .env.example  .gitignore
app/        streamlit_app.py
backend/    lectura, cruce, precios, pdf
ai/         prompts, esquemas Pydantic, extractor LLM, OCR
data/       muestras chicas, sin datos personales (data/cache/ ignorado)
docs/       capturas, flujo_demo.png, diagrama, research/, agente.md
notebooks/  exploración de precios
tests/      pruebas del cruce y del cálculo de precio
```

## Plan del día (5 bloques)

| Bloque | Contenido | Listo cuando |
|---|---|---|
| 1 | Base del repo, README inicial, `docs/flujo_demo.png`, plantillas `docs/research/` | La app de Streamlit abre en local con bienvenida |
| 2 | pdfplumber + PaddleOCR, esquema Pydantic, extractor LLM con tokens, modo demo | Subo una solicitud y veo sus requisitos en tabla |
| 3 | Catálogo de ejemplo, motor de cruce con fuentes, pruebas | Veo la matriz de cumplimiento y el producto recomendado |
| 4 | Precios del Estado, tarjeta de precio, confirmación, PDF, costo por cotización | Flujo completo de principio a fin y descargo el PDF |
| 5 | Despliegue, pruebas con datos reales, README completo (9 partes), revisión de secretos, guion de video | URL pública funciona y README completo |

Opcional: script de evaluación (sesión 12) del % de requisitos bien extraídos.

**Al cerrar cada bloque:** correr pruebas → commit pequeño en español → resumen corto → **esperar visto bueno** antes del siguiente. Si hay atraso, recortar alcance, pero **nunca** la confirmación ni el PDF.

## Cómo trabajar con Ivette

- Explicar en pocas líneas qué hace cada archivo nuevo (el profesor puede pedirle que explique o cambie cualquier parte).
- Registrar en `docs/agente.md` qué generó el agente y qué cambió Ivette.
- Lo simple que funciona antes que lo elegante. Un solo flujo, bien hecho.
- Si algo bloquea (dependencia que no instala, fuente inutilizable), avisar de inmediato y proponer alternativa.
- **No inventar datos, cifras ni especificaciones.** Si falta algo, preguntar.
- Comunicación en español.

## Entorno local (verificado)

- Windows 11. `python` no está en el PATH. El proyecto usa `.venv` (Python 3.11, creado con **uv**). Correr con `.venv\Scripts\python.exe` o `.venv\Scripts\streamlit.exe`. No usar el Python 3.14 de miniconda.
- **Avast Web/Mail Shield inspecciona HTTPS** con su propio certificado raíz. Consecuencias:
  - Instalar paquetes: `uv pip install --system-certs --python .venv <paquete>`.
  - `requests`/`httpx` (SDK de Anthropic, descarga de modelos de PaddleOCR, scraping) fallan con `CERTIFICATE_VERIFY_FAILED`. Solución verificada: `import truststore; truststore.inject_into_ssl()` al inicio de todo punto de entrada que use red (app, scripts, notebooks). Es inocuo en el despliegue.
- Pruebas: `.venv\Scripts\python.exe -m pytest`.
- git con remoto `origin` = repo de GitHub, rama `main`. `gh` no instalado.
- `Cotizador_digital/` dentro de esta carpeta es un clon aparte del mismo repo; está excluido localmente en `.git/info/exclude`. No trabajar ahí.
