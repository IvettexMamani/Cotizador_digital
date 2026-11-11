---
title: Cotizador Digital
emoji: 📄
colorFrom: blue
colorTo: red
sdk: docker
app_port: 7860
pinned: true
license: mit
short_description: Cotizaciones listas para firmar para mypes proveedoras
---

# Cotizador Digital

Preparamos cotizaciones listas para firmar para mypes proveedoras del Estado peruano, mediante IA que lee los términos de referencia, verifica cada requisito contra el catálogo del proveedor, con la fuente de cada dato, y compara el precio con lo que pagó el Estado.

Proyecto final de la Diplomatura en Ciencia de Datos (Q-Lab PUCP). Código fuente: https://github.com/IvettexMamani/Cotizador_digital

- **Modo demo:** sin la clave `ANTHROPIC_API_KEY`, la app usa los resultados precalculados de la solicitud de EJEMPLO SINTÉTICO.
- **Con IA:** la clave se agrega en *Settings → Variables and secrets → New secret*. Nunca va en el código.
- **Actualizar:** este Space descarga el código desde GitHub al construirse. Después de cada cambio en GitHub: *Settings → Factory rebuild*.

La herramienta nunca firma ni envía nada: la cotización la revisa, firma y presenta el proveedor.
