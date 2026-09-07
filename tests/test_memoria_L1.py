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
    """f_h,0,k = 0,082·(1−0,01·d)·ρ_k (EC5 Eq. 8.32) — valor PARALELO."""
    L1, mat = _L1(d_mm=24)
    assert L1["f_h_paralelo_MPa"] == pytest.approx(
        0.082 * (1 - 0.01 * 24) * mat.rho_k, rel=1e-3)


def test_fh_alpha_e_o_valor_usado():
    """
    F-03: o embutimento EFETIVAMENTE usado é f_h,α,k (EC5 Eq. 8.31), com o
    ângulo entre a resultante e as fibras — `f_h0k_MPa` passou a carregá-lo.
    """
    import math
    L1, mat = _L1(d_mm=24)
    k90 = 1.35 + 0.015 * 24
    a = math.radians(L1["alpha_fibras_deg"])
    f_par = 0.082 * (1 - 0.01 * 24) * mat.rho_k
    assert L1["k_90"] == pytest.approx(k90, rel=1e-6)
    assert L1["alpha_fibras_deg"] == pytest.approx(L1["theta_deg"], abs=1e-2)
    assert L1["f_h0k_MPa"] == pytest.approx(
        f_par / (k90 * math.sin(a) ** 2 + math.cos(a) ** 2), rel=1e-3)
    assert L1["f_h0k_MPa"] < L1["f_h_paralelo_MPa"]


def test_Kser_formula():
    """K_ser = ρ_m^1,5·d/23 (EC5 §7.1 Tab. 7.1)."""
    L1, mat = _L1(d_mm=24)
    assert L1["K_ser_Nmm"] == pytest.approx(mat.rho_mean ** 1.5 * 24 / 23.0, rel=1e-3)


def test_t1_desconta_a_chapa():
    """
    F-14: t₁ é a madeira de CADA LADO da chapa central — (b − t_chapa)/2, e não
    b/2. A chapa embutida tem t ≥ d (rigidez para a rótula do pino).
    """
    L1, _ = _L1(d_mm=24)
    assert L1["t1_madeira_mm"] == pytest.approx((0.32 * 1000 - 24) / 2, abs=0.1)
    assert L1["t1_madeira_mm"] < 0.32 * 1000 / 2


def test_nef_respeita_o_teto_da_norma():
    """
    EC5 Eq. (8.34): n_ef = min(n ; n^0,9·(a₁/13d)^0,25) — logo n_ef ≤ n, com
    IGUALDADE admissível (é o que sucede numa fileira de um único pino, onde não
    há grupo a reduzir). Exigir desigualdade estrita seria exigir mais do que a
    norma.
    """
    L1, _ = _L1()
    assert L1["n_ef_row"] <= L1["n_linha"] + 1e-9
    assert L1["n_ef"] <= L1["n_pinos"] + 1e-9


def test_nef_reduz_de_facto_uma_fileira_com_varios_pinos():
    """A redução de grupo existe e morde quando há fileira // fibras."""
    from mlc_projeto.connections.connections import n_ef
    L1, _ = _L1()
    a1 = L1["a1_mm"]
    assert n_ef(1, a1, 24) == pytest.approx(1.0)
    for n in (3, 5, 8):
        assert n_ef(n, a1, 24) < n
