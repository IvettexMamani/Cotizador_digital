"""Pruebas del extractor (paso 3) que no gastan llamadas a la API."""

import json
from pathlib import Path

import pytest
from anthropic.lib._parse._transform import transform_schema

import ai.extractor as extractor
from ai.esquemas import SolicitudCotizacion

RAIZ = Path(__file__).resolve().parent.parent
SOLICITUDES = RAIZ / "data" / "solicitudes"
EJEMPLOS = ["ejemplo_sintetico.pdf", "ejemplo_sintetico_escaneado.pdf", "ejemplo_sintetico_foto.png"]


@pytest.fixture
def sin_clave(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")


def test_precalculados_validan_y_sus_huellas_coinciden_con_los_archivos():
    for ruta in extractor.CARPETA_PRECALCULADO.glob("*.json"):
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        SolicitudCotizacion.model_validate(datos["solicitud"])
        for nombre, huella in datos["archivos_sha256"].items():
            archivo = SOLICITUDES / nombre
            assert archivo.exists(), f"{ruta.name} menciona {nombre}, que no está en data/solicitudes/"
            assert extractor.huella(archivo.read_bytes()) == huella, (
                f"{nombre} cambió: vuelve a calcular su huella en {ruta.name}"
            )


@pytest.mark.parametrize("nombre", EJEMPLOS)
def test_sin_clave_usa_el_resultado_precalculado(sin_clave, nombre):
    resultado = extractor.extraer_requisitos("texto", (SOLICITUDES / nombre).read_bytes(), nombre)

    assert resultado.modo == "demo"
    assert "Modo demo" in resultado.aviso
    assert resultado.uso is None
    assert [item.numero for item in resultado.solicitud.items] == [1, 2]


def test_sin_clave_y_documento_desconocido_da_error(sin_clave):
    with pytest.raises(extractor.ErrorExtraccion, match="no tiene un resultado precalculado"):
        extractor.extraer_requisitos("texto", b"otro documento", "otro.pdf")


def test_si_falla_la_api_cae_al_modo_demo(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")

    def api_que_falla(*args, **kwargs):
        raise extractor.ErrorExtraccion("sin conexión")

    monkeypatch.setattr(extractor, "extraer_con_llm", api_que_falla)
    contenido = (SOLICITUDES / "ejemplo_sintetico.pdf").read_bytes()
    resultado = extractor.extraer_requisitos("texto", contenido, "ejemplo_sintetico.pdf")

    assert resultado.modo == "demo"
    assert "Falló la llamada a la API" in resultado.aviso


def test_costo_por_millon_de_tokens_de_haiku():
    assert extractor.calcular_costo("claude-haiku-5-5", 1_000_000, 0) == pytest.approx(0.10)
    assert extractor.calcular_costo("claude-haiku-5-5", 0, 1_000_000) == pytest.approx(0.50)
    assert extractor.calcular_costo("modelo-desconocido", 10, 10) is None


def test_el_esquema_se_puede_enviar_como_salida_estructurada():
    # Misma conversión que hace messages.parse() antes de llamar a la API.
    esquema = transform_schema(SolicitudCotizacion.model_json_schema())
    assert esquema["type"] == "object"
    assert set(esquema["required"]) == set(SolicitudCotizacion.model_fields)
