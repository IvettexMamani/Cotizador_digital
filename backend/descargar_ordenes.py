"""Descarga una muestra pequeña de órdenes de compra (PDF) de Perú Compras.

Por qué: la exportación de datos abiertos del buscador de órdenes
(https://catalogos.perucompras.gob.pe/ConsultaOrdenesPub) trae solo el total
de cada orden. El precio de cada producto está en el PDF de la orden, cuyo
enlace viene en la columna "Orden Digitalizada" de esa misma exportación.

Reglas de scraping responsable (sesión 03) que cumple este script:
- Solo descarga los enlaces públicos que trae la exportación oficial; sin login
  ni CAPTCHA.
- Revisa robots.txt de cada servidor con urllib.robotparser antes de bajar nada.
- Una descarga a la vez, con al menos 3 s de pausa y pocos reintentos con
  espera creciente.
- User-Agent con el nombre del proyecto y la URL del repo, sin correos.
- Caché en data/cache/ordenes/ (ignorada por git): un PDF ya bajado no se
  vuelve a pedir.
- Volumen pequeño: 30 órdenes por defecto, 50 como máximo.
- El índice guarda solo la orden, la fecha, la entidad, el estado, la URL de
  origen y la fecha de consulta. No guarda proveedores ni usuarios.

Uso:
    python -m backend.descargar_ordenes "data/cache/DatosAbiertos (2).csv" --n 30
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "data" / "cache" / "ordenes"
INDICE = CARPETA / "indice.csv"

USER_AGENT = "CotizadorDigital/0.1 (+https://github.com/IvettexMamani/Cotizador_digital)"
PAUSA_S = 3.0
REINTENTOS = 2
MAXIMO = 50
SEMILLA = 2026
ESTADOS_VALIDOS = {"ACEPTADA", "PAGADA"}  # RESUELTA = contrato resuelto, se descarta

# Columnas de la exportación sin detalle (26). Solo se usan las de abajo.
N_COLUMNAS = 26
COL_ENTIDAD = "Razón Social Entidad"
COL_ORDEN = "Orden Electrónica"
COL_ESTADO = "Estado de la Orden Electrónica"
COL_PDF = "Orden Digitalizada"
COL_FECHA = "Fecha Publicación"


def leer_exportacion(ruta: Path) -> tuple[pd.DataFrame, int]:
    """Lee la exportación (separada por |). Algunos nombres traen un salto de
    línea dentro ("&#x0D;"), así que se juntan las líneas hasta completar la fila.
    Devuelve la tabla y cuántas filas se descartaron por no tener 26 columnas."""
    lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    cabecera = lineas[0].split("|")
    filas, descartadas, buffer = [], 0, ""
    for linea in lineas[1:]:
        buffer = f"{buffer} {linea}" if buffer else linea
        n = buffer.count("|") + 1
        if n < N_COLUMNAS:
            continue
        if n == N_COLUMNAS:
            filas.append([c.replace("&#x0D;", "").strip() for c in buffer.split("|")])
        else:
            descartadas += 1
        buffer = ""
    return pd.DataFrame(filas, columns=cabecera), descartadas


def elegir_muestra(df: pd.DataFrame, n: int, semilla: int = SEMILLA) -> pd.DataFrame:
    """Muestra fija (siempre la misma con la misma semilla) de órdenes válidas con PDF."""
    validas = df[df[COL_ESTADO].isin(ESTADOS_VALIDOS) & df[COL_PDF].str.lower().str.endswith(".pdf")]
    return validas.sample(n=min(n, len(validas)), random_state=semilla)


_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def permitido(url: str) -> bool:
    """Consulta robots.txt del servidor. Sin robots.txt (error 4xx) se permite;
    si el servidor lo prohíbe o no responde, no se descarga."""
    partes = urllib.parse.urlsplit(url)
    servidor = f"{partes.scheme}://{partes.netloc}"
    if servidor not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            pedido = urllib.request.Request(f"{servidor}/robots.txt", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(pedido, timeout=30) as r:
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                rp.disallow_all = True
            elif 400 <= e.code < 500:
                rp.allow_all = True
            else:
                rp = None
        except OSError:
            rp = None
        _robots[servidor] = rp
        time.sleep(PAUSA_S)
    rp = _robots[servidor]
    return rp is not None and rp.can_fetch(USER_AGENT, url)


def url_segura(url: str) -> str:
    """Los nombres de los PDF traen espacios: se codifican (' ' -> '%20')."""
    partes = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(partes._replace(path=urllib.parse.quote(partes.path, safe="/%")))


def descargar(url: str, destino: Path) -> str:
    """Baja un PDF con pausa y reintentos. Devuelve 'cache', 'ok' o el motivo del fallo."""
    if destino.exists() and destino.stat().st_size > 0:
        return "cache"
    url = url_segura(url)
    if not permitido(url):
        return "robots.txt no lo permite o no responde"
    pedido = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for intento in range(REINTENTOS + 1):
        time.sleep(PAUSA_S * (intento + 1))  # 3 s, luego 6 s, luego 9 s
        try:
            with urllib.request.urlopen(pedido, timeout=60) as r:
                contenido = r.read()
            if not contenido.startswith(b"%PDF"):
                return "la respuesta no es un PDF"
            destino.write_bytes(contenido)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code < 500:
                return f"HTTP {e.code}"
            motivo = f"HTTP {e.code}"
        except (OSError, ValueError) as e:
            motivo = type(e).__name__
    return motivo


def main() -> None:
    import truststore

    truststore.inject_into_ssl()  # el antivirus inspecciona HTTPS en esta máquina
    sys.stdout.reconfigure(encoding="utf-8")  # tildes en la consola de Windows

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("exportacion", type=Path, help="CSV exportado de ConsultaOrdenesPub")
    parser.add_argument("--n", type=int, default=30, help=f"órdenes a bajar (máximo {MAXIMO})")
    args = parser.parse_args()
    n = min(args.n, MAXIMO)

    df, descartadas = leer_exportacion(args.exportacion)
    print(f"Exportación: {len(df)} órdenes ({descartadas} filas descartadas por formato).")
    muestra = elegir_muestra(df, n)
    CARPETA.mkdir(parents=True, exist_ok=True)

    registros = []
    for i, fila in enumerate(muestra.itertuples(index=False), start=1):
        fila = dict(zip(muestra.columns, fila))
        orden = fila[COL_ORDEN]
        archivo = f"{orden}.pdf"
        estado = descargar(fila[COL_PDF], CARPETA / archivo)
        print(f"[{i}/{len(muestra)}] {orden}: {estado}")
        registros.append({
            "orden": orden,
            "fecha_publicacion": fila[COL_FECHA],
            "entidad": fila[COL_ENTIDAD],
            "estado_orden": fila[COL_ESTADO],
            "fuente": fila[COL_PDF],
            "fecha_consulta": date.today().isoformat(),
            "archivo": archivo if estado in ("ok", "cache") else "",
            "resultado": estado,
        })

    indice = pd.DataFrame(registros)
    if INDICE.exists():  # lo ya bajado conserva su fecha de consulta original
        previo = pd.read_csv(INDICE, dtype=str, keep_default_na=False)
        previo = previo[previo["archivo"] != ""]
        indice = pd.concat([previo, indice[~indice["orden"].isin(previo["orden"])]])
    indice.to_csv(INDICE, index=False, encoding="utf-8-sig")
    print(f"Índice: {INDICE.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
