"""Issue 9 — verificação da face inclinada da mísula (EC5 §6.4.2, Eq. 6.38–6.40)."""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.misula import (
    verifica_misula,
    k_m_alpha_compressao,
    k_m_alpha_tracao,
)


def _load():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo, mat, 1.5, 0.40, 5.75, pv)
    return geo, mat, load


def test_k_m_alpha_sem_bisel_e_unitario():
    """α=0 (sem bisel) ⇒ k_m,α = 1 (Eq. 6.39/6.40 degeneram)."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    assert k_m_alpha_compressao(mat, 0.0) == pytest.approx(1.0)
    assert k_m_alpha_tracao(mat, 0.0) == pytest.approx(1.0)


def test_tracao_mais_critica_que_compressao():
    """f_t,90,d ≪ f_c,90,d ⇒ k_m,α(tração) < k_m,α(compressão) < 1."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    a = math.radians(10.0)
    k_c = k_m_alpha_compressao(mat, a)
    k_t = k_m_alpha_tracao(mat, a)
    assert k_t < k_c < 1.0


def test_k_m_alpha_valor_fechado():
    """Confere Eq. (6.40) contra cálculo manual — GL24h CS3 curta, α=10°."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    a = math.radians(10.0)
    tan_a = math.tan(a)
    fmd, fvd, fc90d = mat.f_m_d, mat.f_v_d, mat.f_c90_d
    esperado = 1.0 / math.sqrt(
        1 + (fmd / (1.5 * fvd) * tan_a) ** 2 + (fmd / fc90d * tan_a ** 2) ** 2
    )
    assert k_m_alpha_compressao(mat, a) == pytest.approx(esperado, rel=1e-12)


def test_verifica_misula_ok_e_regime():
    """Arco abatido: crown em hogging ⇒ topo tracionado governa a face inclinada."""
    geo, mat, load = _load()
    r = verifica_misula(geo, mat, load)
    assert r["ok"] is True
    assert 0.0 < r["eta"] < 1.0
    assert r["regime"] == "tracao"                    # topo em tração no ápice
    # k_m,α aplicado é o de tração e coincide com o helper
    assert r["k_m_alpha"] == pytest.approx(r["k_m_alpha_tracao"], abs=1e-4)
    # seção governante perto do ápice (crown hogging)
    assert abs(r["x_gov_m"] - geo.L / 2) < 1.5
    assert r["norma"].startswith("EC5 §6.4.2")


def test_sigma_consistente_com_M_e_h():
    """σ_m,α,d = 6|M|/(b h²) na seção governante."""
    geo, mat, load = _load()
    r = verifica_misula(geo, mat, load)
    sigma_esp = 6.0 * abs(r["M_gov_kNm"] * 1e3) / (geo.b * r["h_gov_m"] ** 2) / 1e6
    assert r["sigma_m_alpha_MPa"] == pytest.approx(sigma_esp, rel=1e-3)
