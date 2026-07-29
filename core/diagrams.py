"""Static diagrams built with Plotly shapes/annotations -- no extra
dependency beyond plotly (already required for the charts) and no system
Graphviz binary needed, unlike st.graphviz_chart.

Laid out vertically (not left-to-right) so box text stays legible when the
chart is squeezed into a narrow container -- e.g. a Streamlit page with the
sidebar open, which is the common case here.
"""
from __future__ import annotations

import math

import plotly.graph_objects as go

_BOX_STYLE = dict(
    xref="x", yref="y",
    line=dict(color="#4c4c4c", width=1.5),
)


def _box(fig: go.Figure, x0, x1, y0, y1, text: str, fill: str = "#f4f4f4", note: str | None = None) -> None:
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=fill, **_BOX_STYLE)
    fig.add_annotation(
        x=(x0 + x1) / 2, y=(y0 + y1) / 2, text=text, showarrow=False,
        font=dict(size=13), align="center",
    )
    if note:
        fig.add_annotation(
            x=x1 + 0.15, y=(y0 + y1) / 2, text=note, showarrow=False,
            font=dict(size=11, color="#b34700"), align="left", xanchor="left",
        )


def _arrow(fig: go.Figure, x: float, y0, y1) -> None:
    fig.add_annotation(
        x=x, y=y1, ax=x, ay=y0, xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=1.5, arrowcolor="#4c4c4c",
    )


def build_pipeline_diagram() -> go.Figure:
    """Dish -> exporter -> Prometheus -> CSV -> converter -> dashboard.

    Annotated at the point where the downlink/uplink unit bug was caught
    (PowerShell collector), since that's the concrete reason this diagram
    matters for a technical director: the pipeline has already produced one
    silent data error that only manual verification against upstream
    source caught.
    """
    fig = go.Figure()

    box_w, box_h, gap = 3.4, 0.7, 0.55
    x0, x1 = 0.0, box_w
    cx = box_w / 2

    steps = [
        ("Starlink Mini dish", "#f4f4f4", None),
        ("starlink_exporter<br>(gRPC poll, every 3s)", "#f4f4f4", None),
        ("Prometheus<br>(time-series DB)", "#f4f4f4", None),
        ("PowerShell collector<br>(CSV export)", "#fff3e0", "← unit bug caught here,<br>see Methodology"),
        ("samples.csv<br>(per test session)", "#f4f4f4", None),
        ("convert_real_obstruction_data.py", "#f4f4f4", None),
        ("This dashboard (app.py)", "#e8f5e9", None),
    ]

    n = len(steps)
    ys = [(n - 1 - i) * (box_h + gap) for i in range(n)]

    for (text, fill, note), y in zip(steps, ys):
        _box(fig, x0, x1, y, y + box_h, text, fill=fill, note=note)

    for i in range(n - 1):
        _arrow(fig, cx, ys[i], ys[i + 1] + box_h)

    # Probes branch in at the Prometheus step (index 2).
    prom_y = ys[2]
    probe_x0, probe_x1 = x1 + 2.6, x1 + 2.6 + box_w
    probe_cx = (probe_x0 + probe_x1) / 2
    _box(fig, probe_x0, probe_x1, prom_y, prom_y + box_h,
         "DNS / HTTP / TCP-443 /<br>small-download probes", fill="#eef4ff")
    fig.add_annotation(
        x=x1, y=prom_y + box_h / 2, ax=probe_x0, ay=prom_y + box_h / 2,
        xref="x", yref="y", axref="x", ayref="y",
        showarrow=True, arrowhead=3, arrowsize=1, arrowwidth=1.5, arrowcolor="#4c4c4c",
    )

    fig.update_xaxes(visible=False, range=[-0.3, probe_x1 + 0.3])
    fig.update_yaxes(visible=False, range=[-0.3, ys[0] + box_h + 0.3])
    fig.update_layout(
        height=620,
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white",
    )
    return fig


def build_field_of_view_diagram() -> go.Figure:
    """Illustrates why obstruction -- not signal strength or distance to a
    cell tower -- is this test program's headline metric: the dish tracks a
    moving LEO satellite across a 110-degree field of view (Starlink's own
    published spec) rather than pointing at one fixed spot, and hands off to
    the next satellite roughly every ~10 minutes as it passes overhead.
    Original illustration, not a reproduction of Starlink's product art.
    """
    fig = go.Figure()

    half_angle_deg = 55  # 110 degree field of view, centered straight up
    radius = 4.0
    angles = [90 - half_angle_deg + i for i in range(0, 2 * half_angle_deg + 1, 5)]
    arc_x = [radius * math.cos(math.radians(a)) for a in angles]
    arc_y = [radius * math.sin(math.radians(a)) for a in angles]

    # Shaded field-of-view wedge from the terminal (origin) out to the arc.
    fig.add_trace(go.Scatter(
        x=[0] + arc_x + [0], y=[0] + arc_y + [0],
        fill="toself", fillcolor="rgba(66,133,244,0.12)",
        line=dict(color="rgba(66,133,244,0.5)", width=1),
        mode="lines", hoverinfo="skip", showlegend=False,
    ))

    # Ground terminal marker.
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers+text", marker=dict(size=14, color="#4c4c4c"),
                              text=["Starlink Mini"], textposition="bottom center", showlegend=False))

    # Satellite positions along the pass (start, mid, end of the ~10-minute window).
    sat_angles = [90 - half_angle_deg + 8, 90, 90 + half_angle_deg - 8]
    sat_x = [radius * math.cos(math.radians(a)) for a in sat_angles]
    sat_y = [radius * math.sin(math.radians(a)) for a in sat_angles]
    fig.add_trace(go.Scatter(x=sat_x, y=sat_y, mode="markers+lines", marker=dict(size=10, symbol="diamond", color="#1a7f77"),
                              line=dict(color="#1a7f77", width=1, dash="dot"), showlegend=False, hoverinfo="skip"))
    fig.add_annotation(x=sat_x[1], y=sat_y[1] + 0.35, text="satellite, ~10 min visible<br>before handoff to the next one",
                        showarrow=False, font=dict(size=11, color="#1a7f77"))

    fig.add_annotation(x=arc_x[-1] * 0.55, y=arc_y[-1] * 0.55 + 0.3, text="110° field of view<br>(Starlink Mini spec)",
                        showarrow=False, font=dict(size=11, color="#4285f4"))

    # An obstruction (building) intruding into the left edge of the field of view.
    fig.add_shape(type="rect", x0=-3.3, x1=-1.7, y0=0, y1=2.6, fillcolor="#e0e0e0",
                  line=dict(color="#888", width=1))
    fig.add_annotation(x=-2.5, y=2.9, text="obstruction (building, tree, etc.)<br>blocks part of the field of view",
                        showarrow=False, font=dict(size=11, color="#8a6d00"))

    fig.update_xaxes(visible=False, range=[-4.2, 4.2], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[-0.6, 4.5])
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white")
    return fig
