import plotly.graph_objects as go

from core.diagrams import build_field_of_view_diagram, build_pipeline_diagram


def test_pipeline_diagram_returns_figure_with_content():
    fig = build_pipeline_diagram()
    assert isinstance(fig, go.Figure)
    assert len(fig.layout.shapes) > 0
    assert len(fig.layout.annotations) > 0


def test_field_of_view_diagram_returns_figure_with_content():
    fig = build_field_of_view_diagram()
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0
    assert len(fig.layout.annotations) > 0
