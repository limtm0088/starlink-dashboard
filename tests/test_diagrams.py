import plotly.graph_objects as go

from core.diagrams import build_pipeline_diagram


def test_pipeline_diagram_returns_figure_with_content():
    fig = build_pipeline_diagram()
    assert isinstance(fig, go.Figure)
    assert len(fig.layout.shapes) > 0
    assert len(fig.layout.annotations) > 0
