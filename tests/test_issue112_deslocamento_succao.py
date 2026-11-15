"""Issue 112 — deslocamento vertical do apoio sob sucção e compatibilidade."""

import contextlib
import io

import pytest

from mlc_projeto.checks.els.deslocamento_succao import (
    flecha_chapa_circular_mm, flecha_no_ponto, subida_grupo_mm,
)


def test_subida_do_grupo_com_engajamento_sequencial():
    # 3 pinos a 10 mm e 3 a 11 mm, K = 10 kN/mm: 30 kN fecham só a primeira fileira
    assert subida_grupo_mm(30.0, [10.0] * 3 + [11.0] * 3, 10.0) == pytest.approx(11.0, abs=1e-6)
    # 90 kN: 30 até 11 mm, mais 60 kN nos seis → +1 mm
    assert subida_grupo_mm(90.0, [10.0] * 3 + [11.0] * 3, 10.0) == pytest.approx(12.0, abs=1e-6)
    assert subida_grupo_mm(0.0, [5.0], 10.0) == 0.0


def test_flecha_da_chapa_e_da_viga():
    assert flecha_chapa_circular_mm(50.0, 70.0, 19.0) < 0.2
    assert flecha_no_ponto(10.0, 10.125, 20.25) == pytest.approx(10.0)    # meio do vão
    assert flecha_no_ponto(10.0, 0.0, 20.25) == 0.0


@pytest.fixture(scope="module")
def r():
    import mlc_projeto.main as M
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup


def test_parcelas_do_caminho_corrente(r):
    ds = r["deslocamento_succao"]
    c = ds["caminhos"]["corrente (L3)"]
    seco, umido = c[14.0], c[19.0]
    # a folga é a maior parcela na madeira seca; o tirante M20 de 6,7 m é a segunda
    assert seco["folga_mm"] == pytest.approx(11.3, abs=0.1)
    assert umido["folga_mm"] == pytest.approx(2.0, abs=0.01)
    N = ds["R_up_k_kN"]
    L = r["tirante_interno"]["variantes"]["base_L3"]["L_livre_mm"]     # issue 116: fonte única
    assert 6700 < L < 6800
    assert seco["tirante_mm"] == pytest.approx(N * 1e3 * L / (200e3 * 245), rel=1e-3)
    assert seco["total_mm"] > umido["total_mm"]
    # a frase antiga ("pequeno frente às flechas") comparava ~12 mm com 3 mm
    assert ds["subida_max_apoio_mm"] > 4 * ds["w_up_meio_mm"]


def test_compatibilidade(r):
    ds = r["deslocamento_succao"]
    assert ds["escora"]["delta_mm"] < ds["escora"]["folga_mm"]
    assert ds["pf"]["delta_mm"] < ds["pf"]["curso_mm"]
    assert ds["condutor"]["junta_deslizante_mm"] >= ds["condutor"]["subida_mm"] + 10.0
    assert ds["ok"] and ds["eta"] == pytest.approx(max(ds["escora"]["eta"], ds["pf"]["eta"]))
