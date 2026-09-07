"""
Testes de regressão — F-03 (auditoria adversarial v2).

Achado
------
`f_h_k` implementava a **EC5 Eq. (8.32)**, `f_h,0,k = 0,082(1−0,01d)ρ_k`, que é a
resistência ao embutimento para carga **paralela às fibras**, e
`johansen_chapa_embutida` usava-a incondicionalmente. O ângulo entre a
resultante e as fibras ERA calculado (`dimensionar_ligacao_base`, ~85° na base,
porque a resultante é dominada pelo cortante) mas servia **apenas** para as
distâncias mínimas.

Omitida: **EC5 §8.5.1.1(2), Eq. (8.31) e (8.33)**

    f_h,α,k = f_h,0,k / (k90·sen²α + cos²α)
    k90     = 1,35 + 0,015·d     (coníferas — lamelas do glulam deste projeto)

Para d = 24 mm e α ≈ 85°: k90 = 1,710 e f_h cai 41,3 % (23,99 → 14,08 MPa).
"""
import math

import pytest

from mlc_projeto.connections.connections import (
    F_U_K_PINO,
    f_h_alpha_k,
    f_h_k,
    johansen_chapa_embutida,
    k_90,
)


# ── k90 e f_h,α,k — Eq. (8.31)/(8.33) ────────────────────────────────────────

def test_k90_conifera():
    assert k_90(24.0) == pytest.approx(1.35 + 0.015 * 24.0)
    assert k_90(24.0) == pytest.approx(1.710, abs=1e-6)
    assert k_90(12.0) < k_90(30.0)          # cresce com o diâmetro


def test_k90_por_material():
    assert k_90(24.0, material="conifera") == pytest.approx(1.35 + 0.36)
    assert k_90(24.0, material="lvl") == pytest.approx(1.30 + 0.36)
    assert k_90(24.0, material="folhosa") == pytest.approx(0.90 + 0.36)
    with pytest.raises(ValueError):
        k_90(24.0, material="inexistente")


def test_f_h_alpha_reduz_com_o_angulo():
    f0 = f_h_k(385.0, 24.0)
    assert f_h_alpha_k(385.0, 24.0, 0.0) == pytest.approx(f0)
    assert f_h_alpha_k(385.0, 24.0, 90.0) == pytest.approx(f0 / k_90(24.0))
    # monotonia estrita entre 0° e 90°
    valores = [f_h_alpha_k(385.0, 24.0, a) for a in (0, 15, 30, 45, 60, 75, 90)]
    assert all(a > b for a, b in zip(valores, valores[1:]))


def test_f_h_alpha_valor_do_projeto():
    """d=24, ρ_k=385, α≈85° (resultante dominada pelo cortante na base)."""
    alpha = math.degrees(math.atan2(99.2225, 8.7478))
    f0 = f_h_k(385.0, 24.0)
    fa = f_h_alpha_k(385.0, 24.0, alpha)
    assert f0 == pytest.approx(23.993, abs=1e-3)
    assert fa == pytest.approx(14.076, abs=1e-3)
    assert fa / f0 == pytest.approx(0.587, abs=1e-3)


def test_f_h_alpha_e_simetrica_e_periodica():
    """O que conta é o ângulo com as fibras: ±α e 180°−α dão o mesmo."""
    for a in (30.0, 85.0):
        assert f_h_alpha_k(385.0, 24.0, a) == pytest.approx(
            f_h_alpha_k(385.0, 24.0, -a))
        assert f_h_alpha_k(385.0, 24.0, a) == pytest.approx(
            f_h_alpha_k(385.0, 24.0, 180.0 - a))


# ── Johansen consome o ângulo ────────────────────────────────────────────────

def test_johansen_usa_f_h_alpha():
    j0 = johansen_chapa_embutida(385.0, 24.0, 160.0, F_U_K_PINO, theta_deg=0.0)
    j85 = johansen_chapa_embutida(385.0, 24.0, 160.0, F_U_K_PINO, theta_deg=85.0)
    assert j0["f_hk_MPa"] == pytest.approx(f_h_k(385.0, 24.0), abs=1e-3)
    assert j85["f_hk_MPa"] == pytest.approx(
        f_h_alpha_k(385.0, 24.0, 85.0), abs=1e-3)
    assert j85["theta_deg"] == pytest.approx(85.0)
    assert j85["k_90"] == pytest.approx(k_90(24.0))
    # menos embutimento ⇒ menos resistência em TODOS os modos
    for modo in ("modo_I_N", "modo_IIIb_N", "modo_IV_N", "F_v_Rk_N"):
        assert j85[modo] < j0[modo], modo


def test_johansen_default_e_paralelo_as_fibras():
    """Sem ângulo declarado mantém-se o caso paralelo (Eq. 8.32)."""
    assert (johansen_chapa_embutida(385.0, 24.0, 160.0)["f_hk_MPa"]
            == pytest.approx(f_h_k(385.0, 24.0), abs=1e-3))


# ── Efeito no dimensionamento da ligação de base ─────────────────────────────

def _l1():
    from mlc_projeto.core.geometry import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento
    from mlc_projeto.connections.connections import dimensionar_ligacao_base

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "media")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,
    )
    load = carregamentos_com_vento(
        geo, mat, 0.8229, 0.40, 5.75, pv, empuxo_desenvolve=False,
    )
    return dimensionar_ligacao_base(mat=mat, load=load, geo=geo, d_mm=24)


def test_ligacao_base_usa_o_angulo_da_resultante():
    r = _l1()
    # a resultante na base é dominada pelo cortante ⇒ quase perpendicular
    assert r["theta_deg"] > 80.0
    # e o embutimento tem de refletir isso
    assert r["f_h0k_MPa"] == pytest.approx(
        f_h_alpha_k(385.0, 24.0, r["theta_deg"]), abs=1e-2)
    assert r["k_90"] == pytest.approx(k_90(24.0), abs=1e-6)


def test_ligacao_base_continua_a_cumprir_o_alvo():
    """O redimensionamento automático tem de repor a margem dos modos frágeis."""
    r = _l1()
    assert r["eta"] <= 0.75 + 1e-9
    assert r["ok"] is True
