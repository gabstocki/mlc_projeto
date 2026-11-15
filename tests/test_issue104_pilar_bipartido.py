"""
Issue 104 — nó de topo das baías contraventadas: pilar bipartido.

O nó da issue 66 deixava um binário H·h0 sem equilíbrio (escora sobre a viga, nó no
topo do pilar). Os 14 montantes passam a ser pilares bipartidos: duas lâminas de MLC
dos lados da viga, da base até a escora, com o nó da diagonal CV-V no topo da lâmina.
"""
import contextlib
import io
import math

import pytest

import mlc_projeto.main as M
from mlc_projeto.checks.elu.pilar_bipartido import (
    F_v_Rk_parafuso_corte_duplo, V_d_C5, geometria, verificar_pilar_bipartido,
)
from mlc_projeto.core.materials import GlulamMaterial

MAT = GlulamMaterial("GL24h", 3, "curta")


@pytest.fixture(scope="module")
def res():
    orig = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = orig


def test_geometria_e_limite_do_anexo_C():
    g = geometria(0.32, 0.16, 0.32)
    assert g["a_mm"] == pytest.approx(340.0)              # 320 + 2 × 10
    assert g["y_l_mm"] == pytest.approx(250.0)
    assert g["largura_total_mm"] == pytest.approx(660.0)
    assert g["a_max_ok"]                                    # 340 ≤ 3 × 160 (C.3.1)
    assert not geometria(0.32, 0.10, 0.32)["a_max_ok"]      # 340 > 300


def test_cortante_C5_nas_tres_faixas():
    assert V_d_C5(120.0, 20.0, 1.0) == pytest.approx(1.0)          # F/(120 k_c)
    assert V_d_C5(3600.0, 40.0, 1.0) == pytest.approx(40.0)        # F λ/(3600 k_c)
    assert V_d_C5(60.0, 80.0, 0.5) == pytest.approx(2.0)           # F/(60 k_c)


def test_parafuso_corte_duplo_modo_k_a_mao():
    """Peças grossas → governa o modo (k): 1,15·√(2·M_y·f_h·d)."""
    d, rho = 16.0, 385.0
    M_y = 0.3 * 800 * d ** 2.6
    fh = 0.082 * (1 - 0.01 * d) * rho
    assert F_v_Rk_parafuso_corte_duplo(d, 160.0, 340.0, rho, M_y) == pytest.approx(
        1.15 * math.sqrt(2 * M_y * fh * d))


def test_lamina_do_no_recebe_metade_da_gravidade_e_toda_a_componente_vertical():
    kw = dict(rotulo="t", mat=MAT, b_viga_m=0.32, L_x_m=6.7, L_y_m=7.7, R_grav_kN=200.0,
              R_up_kN=100.0, D_kN=150.0)
    r = verificar_pilar_bipartido(**kw)
    assert r["N_lamina_kN"] == pytest.approx(100.0 + 150.0)
    assert r["N_t_lamina_kN"] == pytest.approx(50.0)
    r2 = verificar_pilar_bipartido(**dict(kw, D_kN=200.0))
    assert r2["eta_comp"] > r["eta_comp"]


def test_pipeline_montantes_bipartidos(res):
    for k in ("pilar_contraventado", "pilar_lateral_montante", "pilar_central_contraventado"):
        b = res[k]
        assert b["ok"], (k, b["partes"])
        assert b["eta_comp"] <= 1.0
        for p in ("no_cavilhas", "sela_cavilhas", "espacadores"):
            assert b["partes"][p] <= 0.75 + 1e-9
    assert "no_deslizante" not in res                      # não há mais movimento relativo
    assert res["no_escora_parafusos"]["ok"]


def test_painel_com_o_no_no_nivel_da_escora(res):
    cvv = res["contraventamento_vertical"]
    g = geometria(M.GEO_PARAMS["b"])
    assert cvv["H_col_m"] == pytest.approx(M.H_PILAR_ALT + M.GEO_PARAMS["h0"] - M.DZ_NO_ESCORA_M)
    assert cvv["b_baia_m"] == pytest.approx(M.L_T - g["y_no_mm"] / 1000)
    assert res["pilar_contraventado"]["D_kN"] == pytest.approx(cvv["N_uplift_kN"], abs=0.1)


def test_bases_dos_montantes_com_dois_pilaretes(res):
    for k in ("base_L3a_canto", "base_L3a_central"):
        b = res[k]
        assert b["B_mm"] > b["L_mm"]                        # grelha girada: 3 ⊥ ao pórtico
        assert b["pilarete"]["D_mm"] <= 120.0               # cabe sob a lâmina de 160 mm
        assert b["geometria"]["folga_ok"]
        assert b["eta"] <= 1.0
    assert set(res["ligacao_topo_pilar"]["variantes"]) == {"base_L3", "base_L3c", "base_L3f"}
    from mlc_projeto.output.report import VERIFICACOES_EXPORT
    chaves = {c for c, _, _ in VERIFICACOES_EXPORT}
    assert {"pilar_lateral_montante", "no_escora_parafusos"} <= chaves
    assert "no_deslizante" not in chaves
