"""Issue 29 — Memória completa da ligação L1 exposta no resultado.

f_h,0,k, M_y,Rk, modos de Johansen (I/IIIb/IV) + governante, t₁, a₁..a₄, n_ef,
K_ser — todos devem estar no dict de dimensionar_ligacao_base (para o memorial).
"""

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.connections.connections import dimensionar_ligacao_base


def _L1(d_mm=24):
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    return dimensionar_ligacao_base(mat.com_duracao(gov.duracao), load, geo, d_mm=d_mm), mat


def test_campos_da_memoria_presentes():
    L1, _ = _L1()
    for k in ("f_h0k_MPa", "M_y_Rk_Nmm", "modo_I_kN", "modo_IIIb_kN",
              "modo_IV_kN", "F_v_Rk_plano_kN", "modo_gov", "t1_madeira_mm",
              "a1_mm", "a2_mm", "a3t_mm", "a4t_mm", "n_ef", "n_ef_row",
              "K_ser_Nmm"):
        assert k in L1, f"faltou {k}"


def test_governante_e_o_minimo_dos_modos():
    """F_v,Rk (1 plano) = min(I, IIIb, IV)."""
    L1, _ = _L1()
    modos = [L1["modo_I_kN"], L1["modo_IIIb_kN"], L1["modo_IV_kN"]]
    assert L1["F_v_Rk_plano_kN"] == pytest.approx(min(modos), rel=1e-3)


def test_My_Rk_formula():
    """M_y,Rk = 0,3·f_u,k·d^2,6 (EC5 Eq. 8.30; f_u,k=400 MPa)."""
    L1, _ = _L1(d_mm=24)
    assert L1["M_y_Rk_Nmm"] == pytest.approx(0.3 * 400.0 * 24 ** 2.6, rel=1e-3)


def test_fh0k_formula():
    """f_h,0,k = 0,082·(1−0,01·d)·ρ_k (EC5 Eq. 8.32)."""
    L1, mat = _L1(d_mm=24)
    assert L1["f_h0k_MPa"] == pytest.approx(
        0.082 * (1 - 0.01 * 24) * mat.rho_k, rel=1e-3)


def test_Kser_formula():
    """K_ser = ρ_m^1,5·d/23 (EC5 §7.1 Tab. 7.1)."""
    L1, mat = _L1(d_mm=24)
    assert L1["K_ser_Nmm"] == pytest.approx(mat.rho_mean ** 1.5 * 24 / 23.0, rel=1e-3)


def test_t1_meia_largura():
    """t₁ = b/2 (chapa embutida central)."""
    L1, _ = _L1()
    assert L1["t1_madeira_mm"] == pytest.approx(0.32 * 1000 / 2, rel=1e-6)


def test_nef_reduz_grupo():
    """n_ef < n_pinos (redução de grupo §8.5.1.1)."""
    L1, _ = _L1()
    assert L1["n_ef"] < L1["n_pinos"]
    assert L1["n_ef_row"] < L1["n_linha"]
