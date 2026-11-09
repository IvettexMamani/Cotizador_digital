"""Gráfico de la tarjeta de precio (plotly).

Una sola fila horizontal: cada punto es una orden de compra del Estado (precio
unitario), la línea gris va del mínimo al máximo, una marca señala la mediana
y el rombo naranja es tu precio. Mínimo, mediana, máximo y número de órdenes
van rotulados directamente en el gráfico.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from backend.precio import ReferenciaEstado

# Paleta de referencia (skill dataviz): posición 1 (azul) para las órdenes y
# posición 2 (naranja) para tu precio. Además cambia la forma (círculo / rombo).
AZUL = "#2a78d6"
NARANJA = "#eb6834"
GRIS = "#8a8984"


def grafico_precio(ordenes: pd.DataFrame, referencia: ReferenciaEstado, tu_precio: float) -> go.Figure:
    """ordenes: columnas precio_unitario, fecha, entidad, cantidad (precios en la misma base que tu_precio)."""
    figura = go.Figure()

    # Rango mínimo-máximo
    figura.add_trace(go.Scatter(
        x=[referencia.minimo, referencia.maximo], y=[0, 0], mode="lines",
        line=dict(color=GRIS, width=2), hoverinfo="skip", showlegend=False,
    ))
    # Una marca por orden de compra
    figura.add_trace(go.Scatter(
        x=ordenes["precio_unitario"], y=[0] * len(ordenes), mode="markers",
        name="Órdenes de compra del Estado",
        marker=dict(color=AZUL, size=10, opacity=0.8, line=dict(color="white", width=2)),
        customdata=ordenes[["fecha", "entidad", "cantidad"]].astype(str).values,
        hovertemplate="S/ %{x:,.2f} por unidad<br>%{customdata[0]} · %{customdata[1]}"
                      "<br>Cantidad: %{customdata[2]}<extra></extra>",
    ))
    # Mediana
    figura.add_trace(go.Scatter(
        x=[referencia.mediana], y=[0], mode="markers", showlegend=False,
        marker=dict(symbol="line-ns", size=26, line=dict(color=GRIS, width=3)),
        hovertemplate="Mediana: S/ %{x:,.2f}<extra></extra>",
    ))
    # Tu precio
    figura.add_trace(go.Scatter(
        x=[tu_precio], y=[0], mode="markers", name="Tu precio",
        marker=dict(symbol="diamond", color=NARANJA, size=16, line=dict(color="white", width=2)),
        hovertemplate="Tu precio: S/ %{x:,.2f}<extra></extra>",
    ))

    rotulos = [
        (referencia.minimo, f"Mín. S/ {referencia.minimo:,.2f}", "bottom"),
        (referencia.mediana, f"Mediana S/ {referencia.mediana:,.2f}", "top"),
        (referencia.maximo, f"Máx. S/ {referencia.maximo:,.2f}", "bottom"),
    ]
    for x, texto, lado in rotulos:
        figura.add_annotation(x=x, y=0, text=texto, showarrow=False, yshift=22 if lado == "top" else -22,
                              font=dict(size=12))
    figura.add_annotation(x=tu_precio, y=0, text=f"<b>Tu precio S/ {tu_precio:,.2f}</b>", showarrow=False,
                          yshift=40, font=dict(size=12))

    debil = " · referencia débil" if referencia.debil else ""
    figura.update_layout(
        title=dict(text=f"Precio unitario pagado por el Estado · {referencia.n_ordenes} órdenes{debil}",
                   font=dict(size=14)),
        height=240, margin=dict(l=10, r=10, t=60, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
        yaxis=dict(visible=False, range=[-1, 1.3]),
        xaxis=dict(title="Soles por unidad", showgrid=True, gridwidth=1, zeroline=False),
        hovermode="closest",
    )
    return figura
