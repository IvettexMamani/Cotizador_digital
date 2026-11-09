# Prompt para Claude Code — Demo "Cotizador Digital"

Copia todo lo que está debajo de la línea y pégalo como primer mensaje en Claude Code, dentro de la carpeta del repositorio (recién clonado y vacío).

---

Hola. Vas a ser mi co-founder técnico. Soy Ivette Mamani Flores, contadora pública y administradora de contratos en el sector público de Tacna. Estoy construyendo, sola, una startup para el proyecto final de la Diplomatura en Ciencia de Datos (Q-Lab PUCP). Necesito una demo que funcione en vivo, de principio a fin, con datos reales, construida en un solo día de trabajo.

Te adjunto la imagen `flujo_demo.png` con el flujo de la demo: guárdala en `docs/flujo_demo.png`, úsala como referencia de lo que hay que construir y enlázala en el README.

Antes de escribir código: lee todo este mensaje, guarda el contexto esencial en un archivo `CLAUDE.md` en la raíz del repo, y muéstrame un plan corto del Bloque 1 para que lo apruebe.

## 1. La startup

**One-liner (borrador):** Preparamos cotizaciones listas para firmar para mypes proveedoras del Estado peruano, mediante IA que lee la solicitud de cotización y la cruza con su catálogo de productos.

**Problema:** las unidades de logística de entidades públicas envían solicitudes de cotización (contratos menores de hasta 8 UIT) a pequeños proveedores. Para responder cada una, el proveedor debe leer los términos de referencia, ver si su producto cumple, buscar la ficha técnica, calcular un precio competitivo y llenar los anexos. Lo hace a mano, con Word y Excel, y muchas solicitudes quedan sin responder.

**Regla de oro del producto:** ningún dato técnico entra a la cotización sin una fuente. Lo que no está verificado se marca en rojo y el PDF no se genera hasta que el proveedor lo revise y confirme. La herramienta nunca firma ni envía nada.

## 2. El único flujo que debe funcionar (solo bienes)

1. **Subir la solicitud de cotización** (PDF digital, PDF escaneado o foto), o elegir una de ejemplo.
2. **Leerla:** si el PDF tiene texto, extraerlo con pdfplumber; si es escaneado o imagen, usar **PaddleOCR** (sesión 10 del curso).
3. **Extraer los requisitos con un LLM con salida estructurada** (sesión 08): entidad, objeto, ítems, cantidad, unidad, requisitos técnicos (atributo, operador, valor, unidad), plazo y lugar de entrega, fecha límite y anexos solicitados. Validar con un esquema Pydantic.
4. **Cruzar con el catálogo** del proveedor (CSV con productos, atributos técnicos, costo, stock y URL o archivo de la ficha técnica): para cada requisito, "cumple", "revisar" o "no cumple", mostrando la fuente. Ordenar los productos que cumplen por disponibilidad y margen.
5. **Tarjeta de precio:** costo del proveedor + margen + flete, comparado con lo que pagó el Estado por bienes similares (datos abiertos de Perú Compras u OECE). Mostrar mínimo, mediana, máximo y número de órdenes en un gráfico, con un precio sugerido y un semáforo. Si hay pocos datos, decir "referencia débil".
6. **Confirmación y PDF:** pantalla de resumen con cada requisito, el dato ofrecido y su fuente; una casilla "Revisé y me hago responsable"; y recién entonces generar el PDF de la cotización (carta, matriz de cumplimiento y precio), listo para imprimir y firmar.

Todo lo demás (buscador de oportunidades, alertas, WhatsApp, lectura de correo, verificación de RUC y RNP, servicios) **queda fuera de la demo**. Va en el README como "qué sigue".

## 3. Stack y decisiones técnicas

- Python 3.11, **Streamlit** para la app.
- **PaddleOCR** para documentos escaneados. Cárgalo de forma diferida y con caché, para que la app no tarde en abrir.
- **LLM con salida estructurada** mediante la API de Anthropic. Antes de programar esta parte, revisa la documentación oficial (https://docs.claude.com) para usar un modelo vigente y la forma recomendada de obtener JSON estructurado. Usa un modelo económico, porque el costo por cotización es parte del modelo de negocio.
- La clave va en `.env` localmente y en los *secrets* del servicio de despliegue. **Nunca** en el código ni en el repo.
- **Modo demo sin clave:** si no hay clave o falla la API, la app usa resultados precalculados (JSON guardado) para las solicitudes de ejemplo y lo indica en pantalla. Así la presentación no depende de internet.
- PDF final con fpdf2. Gráficos con plotly.
- Registra en cada llamada al LLM los tokens usados, para calcular el costo por cotización que va en el README.
- Despliegue: **Hugging Face Spaces** (PaddleOCR necesita memoria) o Streamlit Community Cloud si el OCR entra. Decide conmigo en el Bloque 5.

## 4. Datos: solo públicos, sintéticos o míos

- **Solicitudes de cotización:** yo descargaré manualmente 3 a 5 solicitudes públicas reales, publicadas por entidades en sus portales, y las pondré en `data/solicitudes/`. Nunca uses documentos internos de ninguna entidad. Mientras tanto, crea 1 solicitud sintética claramente marcada como "EJEMPLO SINTÉTICO" para probar el flujo.
- **Catálogo:** crea `data/catalogo_ejemplo.csv` con la estructura correcta y pocas filas marcadas como ejemplo. **No inventes especificaciones de modelos reales.** Yo completaré productos reales con datos de sus fichas oficiales, y cada fila llevará su `fuente_url`.
- **Precios del Estado:** prioriza descargas oficiales de datos abiertos (Perú Compras "Perú Observa" / buscador de órdenes de compra, y el portal de datos abiertos del OECE). Escribe un script en `backend/precios.py` que cargue y limpie esos CSV o XLSX con pandas. Si una descarga necesita hacerse a mano, dime exactamente qué filtros usar y yo la hago.
- Sin datos personales de personas reales. Si un archivo trae nombres o DNI de personas naturales, elimina esas columnas antes de guardarlo en `data/`.

## 5. Scraping responsable (sesión 03)

Si hace falta extraer información de páginas web, cumple estas reglas sin excepción:

1. **Primero busca la vía oficial:** API, datos abiertos o archivo descargable. El scraping es el último recurso.
2. **Revisa `robots.txt`** con `urllib.robotparser` antes de cada dominio. Si la ruta está prohibida, no se extrae: se usa la descarga manual.
3. **Revisa los términos de uso** del sitio y dime si prohíben la extracción automática antes de programar nada.
4. **Pausa de al menos 3 segundos** entre solicitudes al mismo dominio, sin concurrencia, con reintentos limitados y espera creciente ante errores.
5. **User-Agent identificable** con el nombre del proyecto y la URL del repo. Sin mi correo personal.
6. **Nada protegido:** no entrar a páginas con inicio de sesión, no saltar CAPTCHAs, no evadir bloqueos ni límites.
7. **Caché local** de lo descargado (`data/cache/`, ignorado por git) para no repetir solicitudes.
8. **Mínimo necesario:** guardar solo los campos útiles, con la URL de origen y la fecha de consulta.
9. **Volumen pequeño:** para la demo bastan decenas de registros, no miles.
10. Documenta en el README qué se extrajo, de dónde, cuándo y bajo qué reglas.

## 6. Estructura del repo (sección 4.1 de las bases)

```
cotizador-digital/
  README.md
  LICENSE              # MIT
  CLAUDE.md
  requirements.txt
  .env.example         # solo nombres de variables
  .gitignore           # incluye .env y data/cache/
  app/                 # streamlit_app.py
  backend/             # lectura, cruce, precios, pdf
  ai/                  # prompts, esquemas Pydantic, extractor LLM, OCR
  data/                # muestras chicas, sin datos personales
  docs/                # capturas, diagrama, research/ y agente.md
  notebooks/           # exploración de precios
  tests/               # pruebas del cruce y del cálculo de precio
```

## 7. Plan de trabajo: todo en un solo día

Vamos a construir la demo completa en una sola jornada, en 5 bloques. Al terminar cada bloque: corre las pruebas, haz un commit pequeño con mensaje claro en español, muéstrame en pocas líneas qué quedó y espera mi visto bueno antes de pasar al siguiente. Si un bloque se atrasa, recorta alcance; no te saltes la confirmación ni el PDF.

### Bloque 1 — Base del repo (1 hora)

- Estructura de carpetas, `.gitignore`, `.env.example`, LICENSE, `requirements.txt`, `CLAUDE.md` y README inicial con el one-liner.
- Guarda `docs/flujo_demo.png`.
- Plantillas en `docs/research/` para mis 3 conversaciones (fecha, perfil, preguntas, respuestas, cifras, frase textual).
- **Listo cuando:** la app de Streamlit abre en local con una pantalla de bienvenida.

### Bloque 2 — Lectura y extracción (2 a 3 horas)

- Lectura de PDF digital con pdfplumber y OCR con PaddleOCR para escaneados e imágenes.
- Esquema Pydantic y extractor con LLM de salida estructurada, con registro de tokens.
- Modo demo sin clave con JSON precalculado de la solicitud de ejemplo.
- **Listo cuando:** subo una solicitud y veo sus requisitos en una tabla.

### Bloque 3 — Cruce con catálogo (1 a 2 horas)

- Catálogo de ejemplo y motor de cruce "cumple / revisar / no cumple" con la fuente de cada dato, con pruebas en `tests/`.
- **Listo cuando:** veo la matriz de cumplimiento y el producto recomendado.

### Bloque 4 — Precio, confirmación y PDF (2 horas)

- Carga y limpieza de los datos de precios del Estado; tarjeta de precio con gráfico, precio sugerido y semáforo.
- Pantalla de confirmación con la casilla "Revisé y me hago responsable" y PDF final.
- Cálculo del costo por cotización con los tokens registrados.
- **Listo cuando:** el flujo completo corre de principio a fin y descargo el PDF.

### Bloque 5 — Despliegue, README y respaldo (2 horas)

- Despliegue en una URL pública, con la clave en *secrets* y tope de gasto en la API.
- Prueba con mis solicitudes públicas reales y mis productos reales; corregir lo que falle.
- README completo con las 9 partes de la sección 4: one-liner, founder, problema, solución e insight, why now, demo (URL, 3 capturas, diagrama de arquitectura en Mermaid, modelos y APIs con el porqué), modelo de negocio (3 planes: Primer proveedor gratis con 3 cotizaciones, Básico S/ 79, Pro S/ 179, y costo por usuario en tokens, servidor y APIs), herramientas del curso con el archivo exacto donde está cada una, y qué hizo el agente.
- Revisar que no haya secretos: `git log -p | grep -i -E "api_key|secret|token"`.
- Guion para grabar el video de respaldo de 60 a 90 segundos y ayuda para ensayar con el formato oficial: problema (0:00–0:30), demo (0:30–2:30) y negocio (2:30–3:00).
- **Listo cuando:** la URL pública funciona y el README está completo.

Opcional, solo si sobra tiempo: un script de evaluación (sesión 12) que mida qué porcentaje de requisitos se extrae bien en mis solicitudes revisadas a mano.

## 8. Cómo trabajar conmigo

- Explícame en pocas líneas qué hace cada archivo nuevo. El profesor puede pedirme que explique o cambie cualquier parte del código, y tengo que entenderlo.
- Lleva un registro en `docs/agente.md` de qué generaste tú y qué cambié yo. Eso va en la sección "Qué hizo el agente" del README.
- Prefiere lo simple que funciona sobre lo elegante. Un solo flujo, bien hecho.
- Si algo bloquea el avance (una dependencia que no instala, una fuente que no se puede usar), dímelo de inmediato y propón una alternativa.
- No inventes datos, cifras ni especificaciones. Si falta algo, pregúntame.

Empieza por el `CLAUDE.md` y el plan del Bloque 1.
