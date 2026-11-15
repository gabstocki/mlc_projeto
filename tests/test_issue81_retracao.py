"""Issue 81 — retração impedida pelas chapas embutidas."""

import pytest

from mlc_projeto.connections.retracao import (
    D_perp_max_mm, avaliar_retracao, n_perp_max,
)


def test_folga_do_furo_absorve_ate_133_mm_para_d20():
    # d0 − d = 2 mm; α⊥·Δu = 0,0025 × 6 → D⊥,max = 2/0,015
    assert D_perp_max_mm(20) == pytest.approx(2 / 0.015)
    assert n_perp_max(20, 60) == 3


def test_escora_larga_vira_furo_ovalizado():
    r = avaliar_retracao(rotulo="escora", n_perp=5, a2_mm=60, d_mm=20, pode_ovalizar=True)
    assert r["D_perp_mm"] == 240 and "ovalizados" in r["solucao"]
    assert r["curso_mm"] >= r["delta_mm"] + 1.0 and r["ok"]


def test_pe_nao_ovalizavel_acima_do_limite_reprova():
    r = avaliar_retracao(rotulo="pé", n_perp=4, a2_mm=60, d_mm=20, pode_ovalizar=False)
    assert not r["ok"]


def test_pe_limitado_pelo_pipeline(pipeline_res=None):
    import contextlib, io
    import mlc_projeto.main as M
    orig = M.gerar_relatorio
    M.gerar_relatorio = lambda *a, **k: {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = orig
    for k in ("base_L3", "base_L3c", "base_L3f", "base_L3a_canto", "base_L3a_central"):
        assert r[k]["pe_pilar"]["n_vert"] <= 3
    assert r["retracao_chapas"]["ok"]
