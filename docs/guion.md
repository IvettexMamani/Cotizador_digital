# Guion: video de respaldo y pitch de 3 minutos

En español se hablan unas 130 a 150 palabras por minuto. Los tiempos de abajo están calculados con ese ritmo.
Lo que va entre corchetes **[así]** lo completas tú con datos de tus conversaciones. No lo inventes: si no tienes el dato, quita la frase.

---

## A. Video de respaldo (60 a 90 segundos)

**Para qué:** si en la presentación falla internet o la app, pones este video. Es una grabación de pantalla de la app con tu voz encima.

**Cómo grabarlo:**

- En Windows, la Herramienta Recortes graba la pantalla (botón de video).
- Usa la app publicada, o la local con `iniciar.bat`. En el paso 1 elige los términos de referencia de ejemplo `ejemplo_sintetico_foto.png`, que muestran el OCR.
- Antes de grabar, haz el recorrido completo una vez, incluida la solicitud SIGA del paso 6: así el modelo de OCR ya está cargado y la segunda vez va rápido.

| Tiempo | En pantalla | Lo que dices |
|---|---|---|
| 0:00 – 0:10 | Portada de la app, con la regla de oro visible | "Este es el Cotizador Digital: prepara cotizaciones listas para firmar para mypes que le venden al Estado." |
| 0:10 – 0:25 | Paso 1: eliges `ejemplo_sintetico_foto.png` y presionas *Leer y extraer requisitos* | "Subo los términos de referencia que mandó la entidad. Pueden venir en PDF o en foto: si es imagen, la leo con OCR." |
| 0:25 – 0:40 | Paso 3: la tabla de requisitos de cada ítem | "La IA extrae los ítems y cada requisito técnico, con la cita exacta del documento y la página de donde sale." |
| 0:40 – 0:55 | Paso 4: matriz del archivador, con la fila en rojo | "Los cruzo con mi catálogo. En verde lo que cumple con su fuente; en rojo lo que no puedo respaldar con una ficha técnica. Por un detalle así se pierde una orden." |
| 0:55 – 1:10 | Paso 5: margen, flete y la tarjeta de precio con el gráfico | "Pongo mi margen y el flete. La app me sugiere un precio y lo compara con lo que pagó el Estado en órdenes reales." |
| 1:10 – 1:30 | Paso 6: escribes el plazo de entrega, confirmas el dato en rojo, marcas *Revisé y me hago responsable*, marcas *Usar la solicitud SIGA de ejemplo* y descargas | "Escribo mis condiciones, confirmo lo que está en rojo y me hago responsable. Recién ahí sale la cotización, escrita sobre la solicitud del SIGA que mandó la entidad. La herramienta nunca firma ni envía: eso lo hago yo." |

---

## B. Pitch oficial (3 minutos)

### Problema (0:00 – 0:30) · unas 75 palabras

> "Soy Ivette Mamani, contadora y administradora de contratos en el sector público, en Tacna. Las entidades piden cotizaciones a pequeñas empresas, que responden a mano. Conversé con dos proveedores: llenar una cotización les toma hasta media hora; lo difícil es ganar. A una ferretería le pidieron un perno de una medida que no existe: ofreció la más cercana y perdió la orden. Y una imprenta vio bajar el precio de una agenda de 8 a 6 soles en cuatro años."

*Fuente: [`docs/research/`](research/), conversación 1 (minuto 07:11) y conversación 2 (minuto 22:38).*

### Demo (0:30 – 2:30) · en vivo, unas 250 palabras

Usa la app publicada. Si falla, pon el video de respaldo (parte A).

1. **(0:30)** "Les muestro el flujo completo con unos términos de referencia de ejemplo." → En el paso 1 eliges `ejemplo_sintetico_foto.png` y presionas *Leer y extraer requisitos*.
2. **(0:45)** "Es una foto, así que la leo con OCR. Ahora la IA extrae la entidad, los ítems y cada requisito, y para cada uno guarda la cita exacta del documento." → Muestras las tablas del paso 3.
3. **(1:05)** "Cruzo cada requisito con mi catálogo. Para el papel, el producto de 75 gramos cumple todo y cada dato tiene su ficha técnica. Para el archivador, el material no tiene fuente: queda en rojo. Por un detalle así, la ferretería que entrevisté perdió una orden." → Muestras la matriz del ítem 2.
4. **(1:35)** "Pongo mi margen y mi flete. La app calcula el precio, lo compara con lo que pagó el Estado en órdenes reales de Perú Compras y me da un semáforo." → Paso 5.
5. **(1:55)** "Escribo las condiciones de mi oferta. Y esta es la regla de oro: la cotización no se genera hasta que reviso lo que está en rojo y marco *Revisé y me hago responsable*." → En el paso 6 escribes el plazo de entrega, confirmas el dato en rojo y marcas la casilla.
6. **(2:15)** "Si la entidad me mandó su solicitud del SIGA, la agrego y la app la completa encima del original: el valor de cada ítem, el total y mis condiciones. Lista para firmar." → Marcas *Usar la solicitud SIGA de ejemplo*, presionas *Descargar cotización (solicitud SIGA completada)* y abres el PDF.

### Negocio (2:30 – 3:00) · unas 70 palabras

> "El modelo es por suscripción. El primer proveedor prueba gratis con 3 cotizaciones; luego el plan Básico cuesta 79 soles al mes y el Pro, 179. [Lo que incluye cada plan.] El costo de IA por cotización es de [costo medido con `python -m ai.costos`], y el OCR y los datos de precios no cuestan nada. [Frase de un entrevistado sobre cuánto pagaría.] Cotizador Digital: cada requisito verificado y el precio comparado con lo que pagó el Estado, sin perder el control."

---

## Lista de chequeo para el día de la presentación

- [ ] Abrir **https://cotizadordigital.streamlit.app** **10 minutos antes**: la app gratuita se duerme si nadie la usa y tarda en despertar.
- [ ] Hacer el recorrido completo una vez con `ejemplo_sintetico_foto.png` y la solicitud SIGA de ejemplo, para que el OCR ya esté cargado.
- [ ] Tener el **video de respaldo** abierto en otra pestaña.
- [ ] Tener un **PDF ya descargado** por si todo falla.
- [ ] Si la clave de API no está o se acaba el crédito, la app pasa sola a modo demo y lo avisa: decirlo con naturalidad ("estoy en modo demo, con un resultado ya calculado").
- [ ] Ensayar con cronómetro al menos 3 veces. Si te pasas, recorta la demo: sáltate el texto leído del paso 2.
