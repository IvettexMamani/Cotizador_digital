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

1. **Subir los términos de referencia (TDR)** (PDF digital, PDF escaneado o foto) o elegir unos de ejemplo — Streamlit. En el paso 1 NO se sube la solicitud de cotización (decisión de Ivette, 2026-11-10).
2. **Leer:** texto con `pdfplumber`; escaneado/imagen con **PaddleOCR** (sesión 10). Carga diferida y con caché.
3. **Extraer requisitos** con LLM de salida estructurada (sesión 08), validado con Pydantic: entidad, objeto, ítems, cantidad, unidad, requisitos técnicos (atributo, operador, valor, unidad), plazo y lugar de entrega, fecha límite, anexos.
4. **Cruce con catálogo** (CSV): por requisito → `cumple` / `revisar` / `no cumple`, con la fuente. Ordenar productos que cumplen por disponibilidad y margen — pandas. **Opción (pedida por Ivette el 2026-11-09):** si el bien no está en el catálogo, el proveedor sube la foto de su etiqueta/empaque/ficha; `backend/foto_producto.py` lee lo impreso con OCR y lo verifica con el mismo `comparar()` del cruce.
5. **Tarjeta de precio:** costo + margen + flete vs. lo que pagó el Estado (Perú Compras / OECE). Mínimo, mediana, máximo, n° de órdenes en gráfico plotly; precio sugerido y semáforo. Pocos datos → "referencia débil".
6. **Confirmación y PDF:** resumen (requisito, dato ofrecido, fuente) + «Condiciones de tu oferta» + casilla **"Revisé y me hago responsable"** → recién ahí la cotización: PDF del proveedor con la ESTRUCTURA de la solicitud SIGA (tabla con valor total, TOTAL, condiciones de compra) + matriz de cumplimiento. Opcional en el paso 6: si el proveedor agrega la solicitud SIGA original, se entrega esa misma solicitud completada (opción B elegida por Ivette). Nunca generar una réplica del SIGA con el encabezado del sistema o datos que emite la entidad.

**Fuera de la demo** (solo en README como "qué sigue"): buscador de oportunidades, alertas por WhatsApp, lectura de correo, verificación de RUC y RNP, servicios.

## Stack y decisiones técnicas

- Python **3.11**, Streamlit, pdfplumber, PaddleOCR, Pydantic, pandas, plotly, fpdf2, API de Anthropic.
- **LLM:** antes de programarlo, revisar la documentación oficial (docs.claude.com) para elegir un modelo vigente **económico** y la forma recomendada de obtener JSON estructurado. El costo por cotización es parte del modelo de negocio.
- **Registrar tokens** (entrada/salida) en cada llamada al LLM → costo por cotización en el README.
- **Clave:** en `.env` (local) y en *secrets* del despliegue. **Nunca** en código ni en el repo. `.env.example` solo con nombres de variables.
- **Modo demo sin clave:** sin clave o si falla la API → usar JSON precalculado de las solicitudes de ejemplo y avisarlo en pantalla.
- **Despliegue (decidido con Ivette el 2026-11-08):** **Streamlit Community Cloud**, gratis, desde el repo público de GitHub. Archivo principal: `app/streamlit_app.py`; Python 3.11; las librerías de sistema van en `packages.txt` (libgl1, libglib2.0-0, libgomp1). La clave va en los *Secrets* de la app. Cada push a `main` actualiza la app.
  - Descartados: GitHub Pages (solo sitios estáticos) y Hugging Face Spaces. HF ahora exige PRO (US$ 9 al mes) para Spaces Docker o Gradio, incluso en cpu-basic: error 402 al crear el Space. El `Dockerfile` quedó en `despliegue/huggingface/` como plan B. Ivette inició sesión en el CLI `hf` (usuario IvettexMamani).

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

**Avance:** Bloque 1 ✅ · Bloque 2 ✅ (pendiente: probar el LLM con clave real) · Bloque 3 ✅ · Bloque 4 ✅ (con precios reales del Estado desde el 2026-11-09) · Bloque 5 ✅ en lo que depende del agente.

**URL pública:** https://cotizadordigital.streamlit.app (la creó Ivette; probada el 2026-11-09: PDF, foto con OCR en ~17 s, precios del Estado y descarga del PDF). Es un iframe: con playwright, buscar los elementos en `page.frames` (`/~/+/`).

**Pendientes de Ivette (marcados con ✍️ en el README):** clave de API, para medir el costo por cotización con `python -m ai.costos`; solicitudes reales en `data/solicitudes/` y catálogo real en `data/catalogo.csv`; las 3 conversaciones en `docs/research/`; historia de founder; contenido de los planes Básico y Pro. No completar nada de esto sin sus datos.

**Capturas del README:** `docs/capturas/0{1,2,3,4}_*.png` (la 04 es la tarjeta de precio con órdenes reales), tomadas con playwright y Edge sin ventana (`channel="msedge"`, sin descargar navegadores). playwright está en `.venv` pero no en `requirements.txt` (es solo una herramienta de desarrollo). La extensión de Chrome no conecta o no toma capturas en esta máquina.

**Precio, confirmación y PDF (Bloque 4):**
- `backend/precio.py`: piso = costo + flete por unidad; precio con margen = piso × (1 + margen); sugerido = mín(precio con margen, mediana del Estado), nunca bajo el piso, en céntimos (piso redondeado hacia arriba, mediana hacia abajo: si no, el redondeo de la casilla lo dejaba bajo el piso y en rojo). Con menos de 5 órdenes, referencia débil y se sugiere el precio con margen. Semáforo sobre el precio final: rojo si está bajo el piso o sobre el máximo; verde si está en la mediana o por debajo; amarillo entre la mediana y el máximo; gris sin referencia.
- **Margen y flete NO tienen valor por defecto:** Ivette no los ha definido y no se inventan. IGV 18 % con casilla (activada por defecto). Se compara el precio final (con IGV) con los precios del Estado. **Verificado (2026-11-09):** el precio unitario de las órdenes de Perú Compras incluye IGV (en las 18 órdenes usadas, la suma de líneas = total con IGV).
- `backend/pdf.py`: `pendientes()` bloquea el PDF si hay datos en rojo o stock sin confirmar, precios faltantes o falta "Revisé y me hago responsable". El PDF declara los datos "Confirmado por el proveedor" y deja la firma en blanco. Las fuentes estándar solo admiten latin-1: `_t()` reemplaza ≥/≤/— por >=, <=, -.
- `backend/precios.py`: carga `data/precios_estado.csv` (esquema limpio: fecha, entidad, descripcion, unidad, cantidad, precio_unitario con IGV, orden, fuente, fecha_consulta) y busca por palabras.
- **Cómo se arma `data/precios_estado.csv`:** la exportación de ConsultaOrdenesPub (Ivette la bajó a mano: `data/cache/DatosAbiertos (2).csv`, separada por `|`, 26 columnas) trae solo el total por orden; la casilla "Exportar Detallado" no agrega productos (según el diccionario de datos). El detalle está en el PDF "Orden Digitalizada" (escaneado, formato SIGA en la mayoría). `backend/descargar_ordenes.py` baja una muestra fija (semilla 2026, máx. 50, solo ACEPTADA/PAGADA) con las reglas de scraping (Ivette lo autorizó el 2026-11-09; robots.txt no existe en saeusceprod01.blob.core.windows.net ni en apps1.perucompras.gob.pe). `backend/ordenes_pdf.py` aplica OCR (texto en caché `.txt`), acepta una línea solo si cantidad × unitario = total y una orden solo si se comprueba el IGV. Resultado actual: 95 precios de 18 de 50 órdenes; papel bond A4 = 5 órdenes, archivador = 3 (referencia débil). La exportación en bruto trae datos personales (proveedores persona natural, DNI + IP del usuario): se queda en `data/cache/`.
- `ai/costos.py`: costo promedio por cotización desde `logs/uso_llm.jsonl` (`python -m ai.costos`).
- En los selectores de Streamlit, las opciones son el texto que se muestra, sin `format_func`: AppTest falla con `format_func` cuando vuelve a enviar los widgets.

**Bien fuera del catálogo con foto:** `backend/foto_producto.py` (OCR + reglas, sin LLM: funciona sin clave y no inventa). Por requisito busca primero en las líneas que nombran el atributo ("Lomo ancho: 80 mm" para "ancho de lomo"); números con unidad compatible (conversión de `backend.cruce`, alias como gr/m2 → g/m2); textos por coincidencia o lo que sigue a ":". Regla de oro: lo no leído → revisar; dato en una línea que no nombra el atributo → revisar; texto distinto → revisar (no "no cumple", el OCR/redacción varían); número que no alcanza → no cumple. La fuente es «la línea leída». En la app: un expander por ítem en el paso 4 (se mantiene abierto si hay foto en uso), costo y stock sin valor por defecto; recién con ambos el producto `FOTO-<ítem>` entra al selector. Foto de ejemplo: `data/fotos_productos/ejemplo_etiqueta_archivador.png` (`generar_foto_producto()` en `backend/ejemplo_sintetico.py`), sin material a propósito. Posible mejora con clave: modelo con visión para etiquetas sin "atributo: valor".

**Formato de la entidad (2026-11-10):** en el SIGA, la propia solicitud de cotización es el formato de respuesta (el proveedor llena VALOR TOTAL por ítem, TOTAL y condiciones de compra). `backend/formato_entidad.py`: `leer_formato()` (pdfplumber si es digital; si es escaneado/foto, `ai.ocr.fragmentos_imagen()` con cajas a 200 dpi), `planificar()` (columna «VALOR/PRECIO/IMPORTE TOTAL», incluso en dos líneas; filas por descripción del ítem; casilla TOTAL; etiquetas de condiciones) y `llenar()` (capa de texto azul con fpdf2 + `pypdf` 7: `PdfWriter(clone_from=...)` y `merge_page`). Solo datos verificados: precios del paso 5 (con IGV si está marcado), marca del catálogo, moneda soles y lo que el proveedor escribe en «Condiciones de tu oferta»; lo demás queda en blanco; nunca la firma. Se habilita solo con la cotización confirmada. **Desde el 2026-11-10 (pedido de Ivette):** la solicitud SIGA se agrega (opcional) en el paso 6, `pedir_solicitud_siga()`; si `planificar().reconocido`, la descarga principal es esa solicitud completada y el PDF propio queda como secundario. `Cotizacion.total` = suma de `valor_total()` por ítem (con IGV), así la tabla y el TOTAL cuadran; `CondicionesOferta` vive en `backend/pdf.py`. Ejemplo: `data/solicitudes/ejemplo_siga_escaneado.pdf` (+ `data/precalculado/ejemplo_siga.json`), generado por `generar_siga_escaneado()`. Ivette aportó un documento real (Gobierno Regional) solo como referencia de diseño (opción A): está en `data/cache/formatos/`, no se usa ni se sube. NO generar desde cero un formato con los datos de la entidad: se escribe sobre el original que emitió.

**Recarga de módulos en Streamlit Cloud:** Streamlit solo vuelve a ejecutar `app/streamlit_app.py`; los módulos de `ai/` y `backend/` quedaban viejos tras cada push (ImportError hasta reiniciar). `_descargar_modulos_cambiados()` al inicio de la app los descarga si cambió su fecha de modificación (verificado con AppTest).

**Catálogo subido por el proveedor (2026-11-10):** en el paso 4, radio «Catálogo de ejemplo / Subir mi catálogo» (`elegir_catalogo()` en la app). `backend/catalogo.py`: `leer_catalogo_subido()` (CSV con , o ; en utf-8 o latin-1, o .xlsx; encabezados sin importar mayúsculas; Excel 75.0 → 75) y `plantilla_excel()` (hojas catalogo + instrucciones). El catálogo subido NO se cachea con st.cache_data: se usa solo en la sesión. Sin archivo no se cruza ni se avanza al precio. No hay cuentas: se sube en cada sesión.

**Catálogo y cruce (Bloque 3):** el CSV va en formato largo (una fila por producto y atributo, cada una con su `fuente`). Columnas en `backend/catalogo.py`. Si existe `data/catalogo.csv` (el catálogo real de Ivette) se usa ese; si no, `data/catalogo_ejemplo.csv`. Se acepta `;` o `,` como separador. El cruce (`backend/cruce.py`) solo da "cumple" con dato exacto, comparación correcta **y fuente**; si falta el dato, la fuente o la unidad, o el atributo se asoció por parecido, da "revisar". Orden de los productos: estado → stock suficiente → menor costo (proxy de mayor margen). Selección del usuario en `st.session_state["seleccion_productos"]` (ítem → sku).

**Precios del Estado (fuentes descartadas):** el registro de Open Contracting (publicación 78) no sirve: cubre 2021–2023 y no trae ítems ni precios unitarios. La "Descarga Masiva" llega solo a 2023. gob.pe bloquea el acceso automático (HTTP 418): no esquivarlo, pedir descarga manual.

**Decisiones ya tomadas:** LLM `claude-haiku-5-5` (configurable con `ANTHROPIC_MODEL`), esfuerzo `medium`, `client.messages.parse(output_format=SolicitudCotizacion)`. Modo demo: busca el resultado en `data/precalculado/*.json` por la huella SHA-256 del archivo; si se regenera un ejemplo, la prueba `test_precalculados_validan...` avisa. Tokens en `logs/uso_llm.jsonl` (ignorado por git).

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
- PaddleOCR: modelos ya descargados en `~/.paddlex/official_models` (mobile det + latin rec). `paddlepaddle` fijado en 3.2.2: la 3.3.x falla con oneDNN en CPU. ~6 s por página.
- git con remoto `origin` = repo de GitHub, rama `main`. `gh` no instalado.
- `Cotizador_digital/` dentro de esta carpeta es un clon aparte del mismo repo; está excluido localmente en `.git/info/exclude`. No trabajar ahí.
