from conftest import implemented

from dp_activity.visualization.chart_factory import ChartFactory


class FakeFigure:
    def savefig(self, path, **kwargs):
        path.write_text("figure", encoding="utf-8")


def test_save_creates_the_requested_chart_file(tmp_path) -> None:
    path = tmp_path / "figures" / "monthly.png"

    saved = implemented(ChartFactory().save, FakeFigure(), path)

    assert saved == path
    assert path.read_text(encoding="utf-8") == "figure"

