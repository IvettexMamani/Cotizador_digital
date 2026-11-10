# Guion: video de respaldo y pitch de 3 minutos

En español se hablan unas 130 a 150 palabras por minuto. Los tiempos de abajo están calculados con ese ritmo.
Lo que va entre corchetes **[así]** lo completas tú con datos de tus conversaciones. No lo inventes: si no tienes el dato, quita la frase.

---

## A. Video de respaldo (60 a 90 segundos)

**Para qué:** si en la presentación falla internet o la app, pones este video. Es una grabación de pantalla de la app con tu voz encima.

**Cómo grabarlo:**

- En Windows, la Herramienta Recortes graba la pantalla (botón de video).
- Usa la app publicada, o la local con `iniciar.bat`, y la solicitud `ejemplo_sintetico_foto.png`, que muestra el OCR.
- Antes de grabar, procésala una vez: así el modelo de OCR ya está cargado y la segunda vez va rápido.

| Tiempo | En pantalla | Lo que dices |
|---|---|---|
| 0:00 – 0:10 | Portada de la app, con la regla de oro visible | "Este es el Cotizador Digital: prepara cotizaciones listas para firmar para mypes que le venden al Estado." |
| 0:10 – 0:25 | Eliges la foto de la solicitud y presionas *Leer y extraer requisitos* | "Subo la solicitud de cotización que mandó la entidad. Puede ser un PDF o una foto: si es imagen, la leo con OCR." |
| 0:25 – 0:40 | Paso 3: la tabla de requisitos | "La IA extrae los ítems y cada requisito técnico, con la cita exacta del documento y la página de donde sale." |
| 0:40 – 0:55 | Paso 4: matriz del archivador, con la fila en rojo | "Los cruzo con mi catálogo. En verde lo que cumple con su fuente; en rojo lo que no puedo respaldar con una ficha técnica." |
| 0:55 – 1:10 | Paso 5: margen y flete, precio sugerido | "Pongo mi margen y el flete. La app me sugiere un precio y lo compara con lo que pagó el Estado." |
| 1:10 – 1:25 | Paso 6: confirmas el dato en rojo, marcas la casilla, descargas el PDF | "El PDF solo se genera cuando reviso lo que está en rojo y me hago responsable. La herramienta nunca firma ni envía: eso lo hago yo." |

---

## B. Pitch oficial (3 minutos)

### Problema (0:00 – 0:30) · unas 70 palabras

> "Soy Ivette Mamani, contadora y administradora de contratos en el sector público, en Tacna. Cada día, las entidades piden cotizaciones a pequeños proveedores para sus compras menores. Para responder una, la mype tiene que leer las especificaciones, ver si su producto cumple, buscar la ficha técnica, calcular el precio y llenar anexos. Todo a mano. [Dato de tus conversaciones: por ejemplo, cuántas solicitudes quedan sin responder.] Y cada solicitud sin responder es una venta perdida."

### Demo (0:30 – 2:30) · en vivo, unas 250 palabras

Usa la app publicada. Si falla, pon el video de respaldo (parte A).

1. **(0:30)** "Les muestro el flujo completo con una solicitud de ejemplo." → Eliges `ejemplo_sintetico_foto.png` y presionas *Leer y extraer requisitos*.
2. **(0:45)** "Es una foto, así que la leo con OCR. Ahora la IA extrae la entidad, los ítems y cada requisito, y para cada uno guarda la cita exacta del documento." → Muestras la tabla del paso 3.
3. **(1:10)** "Cruzo cada requisito con mi catálogo. Para el papel, el producto de 75 gramos cumple todo y cada dato tiene su ficha técnica. Para el archivador, el material no tiene fuente: queda en rojo." → Muestras la matriz del ítem 2.
4. **(1:40)** "Pongo mi margen y mi flete. La app calcula el precio, lo compara con lo que pagó el Estado y me da un semáforo." → Paso 5.
5. **(2:05)** "Esta es la regla de oro: el PDF no se genera hasta que reviso lo que está en rojo y marco *Revisé y me hago responsable*." → Confirmas, marcas la casilla y descargas el PDF.
6. **(2:20)** "Y aquí está la cotización: carta, precios y matriz de cumplimiento, lista para firmar." → Abres el PDF.

### Negocio (2:30 – 3:00) · unas 70 palabras

> "El modelo es por suscripción. El primer proveedor prueba gratis con 3 cotizaciones; luego el plan Básico cuesta 79 soles al mes y el Pro, 179. [Lo que incluye cada plan.] El costo de IA por cotización es de [costo medido con `python -m ai.costos`], y el OCR y los datos de precios no cuestan nada. [Frase de un entrevistado sobre cuánto pagaría.] Cotizador Digital: más cotizaciones respondidas, sin perder el control."

---

## Lista de chequeo para el día de la presentación

- [ ] Abrir la URL publicada **10 minutos antes**: la app gratuita se duerme si nadie la usa y tarda en despertar.
- [ ] Procesar una vez la solicitud de ejemplo, para que el OCR ya esté cargado.
- [ ] Tener el **video de respaldo** abierto en otra pestaña.
- [ ] Tener un **PDF ya descargado** por si todo falla.
- [ ] Si la clave de API no está o se acaba el crédito, la app pasa sola a modo demo y lo avisa: decirlo con naturalidad ("estoy en modo demo, con un resultado ya calculado").
- [ ] Ensayar con cronómetro al menos 3 veces. Si te pasas, recorta la demo: sáltate el texto leído del paso 2.
