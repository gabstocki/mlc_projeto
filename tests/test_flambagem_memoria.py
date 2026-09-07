"""Issue 11 — memória de cálculo da flambagem lateral (EC5 §6.3.3):
l_ef, σ_m,crit, λ_rel,m, k_crit expostos e consistentes."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.flambagem_lateral import (
    verifica_flambagem_lateral,
    calcular_l_ef,
    calcular_sigma_m_crit,
    calcular_lambda_rel_m,
    calcular_k_crit,
)


def _res(l_1=2.53):
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo, mat, 1.5, 0.40, 5.75, pv)
    return geo, mat, verifica_flambagem_lateral(geo, mat, load, l_1=l_1)


def test_memoria_expoe_todos_os_valores():
    """Todos os intermediários de reprodutibilidade presentes."""
    _, _, r = _res()
    for k in ("l_1_m", "l_ef_m", "fator_l_ef", "restricao", "tipo_carga",
              "E0_05_MPa", "sigma_m_crit_MPa", "lambda_rel_m", "k_crit",
              "regime", "sigma_md_MPa", "resist_MPa", "eta", "h_crit_m"):
        assert k in r, f"faltou {k}"


def test_l_ef_igual_09_l1_mais_2h():
    """
    l_ef = 0,9·l_1 + 2h — EC5 Tab. 6.1 (restrição contínua no topo + carga
    distribuída) MAIS a nota da tabela: as terças carregam a borda COMPRIMIDA
    (achado F-07). A razão crua só se aplica a carga no centro de gravidade.
    """
    _, _, r = _res(l_1=2.53)
    assert r["l_ef_m"] == pytest.approx(0.9 * 2.53 + 2 * r["h_crit_m"], abs=1e-3)
    assert r["posicao_carga"] == "borda_comprimida"
    assert calcular_l_ef(2.53, posicao_carga="centro_gravidade") == pytest.approx(
        0.9 * 2.53)
    assert calcular_l_ef(2.53, h_m=2.0) == pytest.approx(0.9 * 2.53 + 4.0)


def test_sigma_crit_e_lambda_consistentes():
    """σ_m,crit = 0,78·b²·E0,05/(h·l_ef) e λ_rel = √(f_m,k/σ_m,crit)."""
    geo, mat, r = _res(l_1=2.53)
    sig = calcular_sigma_m_crit(mat.E0_05, r["b_m"], r["h_crit_m"], r["l_ef_m"])
    assert r["sigma_m_crit_MPa"] == pytest.approx(sig / 1e6, rel=1e-3)
    lam = calcular_lambda_rel_m(mat.f_m_k, sig)
    assert r["lambda_rel_m"] == pytest.approx(lam, rel=1e-3)
    assert r["E0_05_MPa"] == pytest.approx(mat.E0_05 / 1e6, abs=1)


def test_k_crit_tres_regimes():
    """k_crit segue os três regimes do EC5 §6.3.3 (Eq. 6.34)."""
    assert calcular_k_crit(0.5) == pytest.approx(1.0)               # λ ≤ 0,75
    assert calcular_k_crit(1.0) == pytest.approx(1.56 - 0.75 * 1.0)  # 0,75<λ≤1,4
    assert calcular_k_crit(2.0) == pytest.approx(1.0 / 4.0)          # λ > 1,4
    # coerência com o regime reportado
    _, _, r = _res()
    if r["lambda_rel_m"] <= 0.75:
        assert r["k_crit"] == pytest.approx(1.0)
        assert "0,75" in r["regime"]
