"""Issue 93 — varredura global refeita: beiral no volume e tabela gerada."""
import numpy as np
import pandas as pd
import pytest

from mlc_projeto import main as pipeline
from mlc_projeto.predim import varredura_global as V


def test_volume_inclui_o_balanco_do_beiral():
    a = pipeline.GEO_PARAMS["a_bal"]
    assert a > 0
    com = V.volume_mlc_m3(10.0, 1.0, 0.32)
    sem = V.volume_mlc_m3(10.0, 1.0, 0.32, n_balancos=0)
    h_p = 1.0 - a * np.tan(np.radians(10.0))
    assert com - sem == pytest.approx(18 * 0.32 * a * (1.0 + h_p) / 2, rel=1e-3)


def test_grade_da_tese():
    pts = V.GRADE_PADRAO.pontos()
    assert len(pts) == 21 * 17 * 9
    assert (10.0, 1.0, 0.32) in pts


def test_fronteira_escolhe_menor_volume_por_margem():
    base = dict(status="APROVADO", eta_contraventamento_vertical=0.8,
                eta_pilar_contraventado=0.5)
    df = pd.DataFrame([
        dict(base, alpha_deg=8.0, h0=0.6, b=0.24, volume_mlc_m3=110, eta_cisalhamento=0.95),
        dict(base, alpha_deg=9.0, h0=0.8, b=0.28, volume_mlc_m3=150, eta_cisalhamento=0.55),
        dict(base, alpha_deg=10.0, h0=1.0, b=0.32, volume_mlc_m3=226, eta_cisalhamento=0.40),
        dict(base, alpha_deg=6.0, h0=0.4, b=0.20, volume_mlc_m3=90, eta_cisalhamento=0.5,
             status="REPROVADO"),
    ])
    f = {r["margem"]: r for r in V.fronteira(df)}
    assert f[1.0]["volume_mlc_m3"] == 110
    assert f[0.6]["volume_mlc_m3"] == 150
    assert f[0.4]["volume_mlc_m3"] == 226
    assert f[None]["alpha_deg"] == 10.0                  # adotada


def test_reprova_reconhece_numpy_bool(monkeypatch):
    """`ok` como numpy.bool_ era omitido da lista de causas (`is False`)."""
    falso = np.float64(1.05) <= 1.0                     # numpy.bool_(False)
    assert falso is not False
    res = {"meta": {"status": "REPROVADO", "eta_max": 1.05, "n_verif": 3},
           "a": {"eta": 1.05, "ok": falso},
           "b": {"eta": 0.50, "ok": np.float64(0.5) <= 1.0},
           "c": {"eta": 0.10, "ok": None},
           "d": {"eta": 1.20, "ok": False}}
    monkeypatch.setattr(pipeline, "_main_impl", lambda **k: res)
    r = V.rodar_ponto(10.0, 1.0, 0.32)
    assert r["reprova"] == "a;d"
