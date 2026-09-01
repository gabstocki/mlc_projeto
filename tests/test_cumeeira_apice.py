"""Issue 10 — parâmetros da zona do ápice (EC5 §6.4.3, Eq. 6.41–6.56)."""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.cumeeira import (
    verifica_cumeeira,
    calcular_k_p,
    calcular_k_l,
    calcular_volumes_apice,
    calcular_k_vol,
    K_DIS,
    K_R,
    V0_KVOL,
)


def _load():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo, mat, 1.5, 0.40, 5.75, pv)
    return geo, mat, load


def test_constantes_duplo_bisel():
    """Duplo-bisel: k_dis=1,4 (Eq. 6.52); k_r=1,0 (§6.4.3(5)); V0=0,01 m³."""
    assert K_DIS == 1.4
    assert K_R == 1.0
    assert V0_KVOL == 0.01


def test_k_p_e_k_l_formulas():
    """k_p=0,2·tanα (Eq. 6.56/6.57) e k_l=1+1,4tanα+5,4tan²α (Eq. 6.44, r→∞)."""
    a = 10.0
    tan_a = math.tan(math.radians(a))
    assert calcular_k_p(a) == pytest.approx(0.2 * tan_a)
    assert calcular_k_l(a) == pytest.approx(1 + 1.4 * tan_a + 5.4 * tan_a ** 2)
    # sem bisel: k_l → 1, k_p → 0
    assert calcular_k_l(0.0) == pytest.approx(1.0)
    assert calcular_k_p(0.0) == pytest.approx(0.0)


def test_volumes_apice_duplo_bisel():
    """V_b=b·L·[h_ap−0,25·L·tanα]; V=b·h_ap²·[1−0,25·tanα] ≤ 2Vb/3."""
    b, h_ap, L, a = 0.32, 2.785, 20.25, 10.0
    tan_a = math.tan(math.radians(a))
    v = calcular_volumes_apice(b, h_ap, L, a)
    assert v["V_b_m3"] == pytest.approx(b * L * (h_ap - 0.25 * L * tan_a))
    assert v["V_ap_bruto_m3"] == pytest.approx(b * h_ap ** 2 * (1 - 0.25 * tan_a))
    assert v["V_m3"] == pytest.approx(min(v["V_ap_bruto_m3"], 2 / 3 * v["V_b_m3"]))
    # k_vol coerente
    kv = calcular_k_vol(b, h_ap, L, a)
    assert kv == pytest.approx(min((V0_KVOL / v["V_m3"]) ** 0.2, 1.0))


def test_k_vol_correto_menor_que_aproximacao_antiga():
    """O V_ap correto (>) dá k_vol MENOR que a antiga aproximação 0,15·b·h_ap²
    (era não-conservador)."""
    b, h_ap, L, a = 0.32, 2.785, 20.25, 10.0
    V_correto = calcular_volumes_apice(b, h_ap, L, a)["V_m3"]
    V_antigo = 0.15 * b * h_ap ** 2
    assert V_correto > V_antigo
    assert calcular_k_vol(b, h_ap, L, a) < (V0_KVOL / V_antigo) ** 0.2


def test_verifica_cumeeira_expoe_todos_parametros():
    """Todos os parâmetros §6.4.3 presentes e consistentes; verificação OK."""
    geo, mat, load = _load()
    r = verifica_cumeeira(geo, mat, load)
    for k in ("k_p", "k_l", "k_r", "k_dis", "k_vol",
              "V_ap_bruto_m3", "V_b_m3", "V_m3",
              "sigma_t90d_MPa", "sigma_m_ap_MPa",
              "eta_t90", "eta_flexao_ap", "eta", "alpha_ap_deg"):
        assert k in r, f"faltou {k}"
    assert r["ok"] is True
    assert r["eta"] == pytest.approx(max(r["eta_t90"], r["eta_flexao_ap"]))
    # σ_m usa k_l; σ_t90 usa k_p; portanto σ_m/σ_t90 = k_l/k_p
    # (tolerância acomoda o arredondamento das tensões a 4 casas no dict)
    assert r["sigma_m_ap_MPa"] / r["sigma_t90d_MPa"] == pytest.approx(
        r["k_l"] / r["k_p"], rel=2e-2)
