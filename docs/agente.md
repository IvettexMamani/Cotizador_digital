# Registro del agente

Qué generó el agente (Claude Code) y qué cambió Ivette, bloque por bloque. Este registro alimenta la sección «Qué hizo el agente» del README.

El encargo original está en [`prompt_inicial.md`](prompt_inicial.md).

| Fecha | Bloque | Generó el agente | Cambió / decidió Ivette |
|---|---|---|---|
| 2026-11-08 | 0 · Inicio | `CLAUDE.md` con el contexto del proyecto y el plan del Bloque 1. | Escribió el encargo (`prompt_inicial.md`) y el diagrama `flujo_demo.png`. Aprobó el plan; pidió `git init` en la carpeta del proyecto y mover el prompt a `docs/`. |
| 2026-11-08 | 1 · Base del repo | Estructura de carpetas, `.gitignore`, `.env.example`, `requirements.txt`, README inicial, plantillas de `docs/research/`, este registro y la pantalla de bienvenida en `app/streamlit_app.py`. Cambió el titular del `LICENSE` de `IvettexMamani` a «Ivette Mamani Flores». Detectó que Avast intercepta HTTPS y lo resolvió con `truststore`. | Creó el repo en GitHub con licencia MIT. Aprobó el push. |
| 2026-11-08 | 2 · Lectura y extracción | Solicitud de EJEMPLO SINTÉTICO en 3 formatos (`backend/ejemplo_sintetico.py`); lectura con pdfplumber y OCR por página (`backend/lectura.py`, `ai/ocr.py`); esquema Pydantic con cita textual y página por requisito (`ai/esquemas.py`); prompt (`ai/prompts.py`); extractor con `claude-haiku-5-5`, registro de tokens y modo demo (`ai/extractor.py`); script `ai/precalcular.py`; resultado precalculado del ejemplo transcrito a mano; pantalla de los pasos 1 a 3; 14 pruebas. Fijó `paddlepaddle` en 3.2.2: la 3.3 falla con oneDNN y sin oneDNN el OCR es 4 veces más lento. | Aprobó iniciar el Bloque 2. |
