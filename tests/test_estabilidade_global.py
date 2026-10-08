"""Testes — estabilidade global (P-Δ, nocionais, α_cr)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.estabilidade_global import (
    forca_nocional,
    alpha_cr_membro,
    amplificacao_segunda_ordem,
    verificar_estabilidade_global,
)


def test_forca_nocional_phi():
    r = forca_nocional(V_Ed_kN=400.0, h_m=7.0, m_colunas=2)
    assert 0.002 < r["phi"] < 0.01
    assert r["H_imp_kN"] == pytest.approx(r["phi"] * 400.0, rel=1e-3)
    assert r["H_imp_kN"] < 5.0  # << H típico do pórtico


def test_alpha_cr_arco_meia_agua():
    """Modo de arco L_ef=L/2: α_cr de sistema > α_cr de barra L_ef=L."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    barra = alpha_cr_membro(mat, b=0.30, h=1.00, L_ef_m=20.25, N_Ed_kN=1600.0)
    arco = alpha_cr_membro(mat, b=0.30, h=1.00, L_ef_m=10.125, N_Ed_kN=1600.0)
    assert arco["alpha_cr"] > barra["alpha_cr"]
    assert arco["alpha_cr"] > 10.0


def test_k_II_proximo_de_um():
    assert amplificacao_segunda_ordem(100.0) == pytest.approx(1.0101, rel=1e-3)
    assert amplificacao_segunda_ordem(10.0) == pytest.approx(1.1111, rel=1e-3)


def _load_R2():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.30)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,   # cobertura real: 2 tramos + veículos sob a cobertura (Onda 2)
    )
    load = carregamentos_com_vento(
        geo, mat, 1.5, 0.25, 5.75, pv,
        b_pilar=0.22, h_pilar=0.26,
    )
    return geo, mat, load


def test_estabilidade_sem_contravento_e_mecanismo():
    """
    Issue 14: pórtico biarticulado SEM contraventamento vertical informado é
    um mecanismo sway (α_cr,sway → 0) — NÃO pode ser classificado non-sway.
    """
    geo, mat, load = _load_R2()
    res = verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
    )
    assert res["sistema_non_sway"] is False
    assert res["ok"] is False
    assert res["metodo_analise"] == "instavel_lateralmente"
    assert res["alpha_cr_sway"] == 0.0
    # F-02: o α_cr de ARCO continua a existir, mas como INFORMATIVO — deixou de
    # ser o critério de dispensa de 2.ª ordem (`alpha_cr` é agora o de sistema).
    assert res["alpha_cr_arco"] >= 10.0


def test_estabilidade_so_uma_direcao_ainda_mecanismo():
    """
    Non-sway exige AMBAS as direções. Só a longitudinal verificada (transversal
    ausente) ainda é mecanismo.
    """
    geo, mat, load = _load_R2()
    res = verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
        contravento_vertical_ok=True,   # só longitudinal
    )
    assert res["non_sway_long"] is True
    assert res["non_sway_transv"] is False
    assert res["sistema_non_sway"] is False
    assert res["ok"] is False
    assert res["metodo_analise"] == "instavel_lateralmente"


def test_estabilidade_com_contravento_dispensa_2a_ordem():
    """
    Com contraventamento vertical E transversal verificados (non-sway nas duas
    direções), e demais critérios atendidos, dispensa-se a 2.ª ordem global.
    """
    geo, mat, load = _load_R2()
    res = verificar_estabilidade_global(
        geo, mat, load,
        H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
        contravento_vertical_ok=True,
        contravento_transversal_ok=True,
        # F-02: α_cr de SISTEMA (EN 1993-1-1 Eq. 5.2) — rigidez real das cruzes
        K_lat_long_kNpm=59417.0,
        K_lat_transv_kNpm=8450.0,
        V_Ed_total_kN=3586.0,
    )
    assert res["ok"] is True
    assert res["metodo_analise"] == "1a_ordem"
    assert res["sistema_non_sway"] is True
    assert res["non_sway_long"] is True
    assert res["non_sway_transv"] is True
    assert res["alpha_cr_sway"] > 1e5        # estabilidade provida pelos contraventos
    assert res["alpha_cr"] >= 10.0           # α_cr de SISTEMA (direção crítica)
    assert res["direcao_critica"] == "transversal"
    assert res["alpha_cr_arco"] >= 10.0      # modo arco (informativo)
    # Resíduo do [F-06]: a razão H_imp/H_Ed passou a ser avaliada COMBINAÇÃO A
    # COMBINAÇÃO (cada uma um estado coerente) e retém-se a máxima, em vez de
    # ser lida da combinação de max|M|. Sobe de ~0,0086 para ~0,0122 — continua
    # muito abaixo do limiar de dispensa de 0,10, que é o critério normativo.
    assert res["H_imp_over_H"] < 0.10        # limiar de dispensa (AUD-008)
    assert res["H_imp_over_H"] > 0.01        # e é o envelope, não a de max|M|
    assert res["w_over_f"] < 0.05
    assert res["H_imp_kN"] < 5.0
    # Onda 2: sem o caso de pressão descendente da Tab.25, a combinação que
    # maximiza a reação vertical passa a ser gravítica e H cai (~374 kN).
    assert res["H_Ed_kN"] > 300.0
    # E o empuxo da combinação que governa a RAZÃO é outro — muito menor. São
    # perguntas diferentes e o resultado publica as duas.
    assert res["H_Ed_da_razao_kN"] < res["H_Ed_kN"]
    assert res["comb_H_imp_over_H"]
    # barra pode ter α_cr < 10 — informativo, coberto por k_c
    assert "k_c" in res["nota_alpha_cr_barra"]


def test_estabilidade_contravento_reprovado():
    """Contraventamento transversal não conforme → mecanismo sway (ok False)."""
    geo, mat, load = _load_R2()
    res = verificar_estabilidade_global(
        geo, mat, load,
        H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
        contravento_vertical_ok=True,
        contravento_transversal_ok=False,
    )
    assert res["sistema_non_sway"] is False
    assert res["non_sway_transv"] is False
    assert res["ok"] is False
    assert res["metodo_analise"] == "instavel_lateralmente"


# ── Issue 46 — imperfeições pela EN 1995-1-1 §5.4.4 ───────────────────────────

def test_inclinacao_inicial_ec5_eq_5_1():
    """φ = 0,005 para h ≤ 5 m; φ = 0,005·√(5/h) para h > 5 m."""
    from mlc_projeto.checks.elu.estabilidade_global import inclinacao_inicial_ec5
    import math
    assert inclinacao_inicial_ec5(3.0) == pytest.approx(0.005)
    assert inclinacao_inicial_ec5(5.0) == pytest.approx(0.005)
    assert inclinacao_inicial_ec5(7.0) == pytest.approx(0.005 * math.sqrt(5 / 7))
    assert inclinacao_inicial_ec5(7.0) == pytest.approx(0.00423, abs=1e-5)


def test_curvatura_inicial_ec5_eq_5_2():
    from mlc_projeto.checks.elu.estabilidade_global import curvatura_inicial_ec5
    assert curvatura_inicial_ec5(7.0) == pytest.approx(0.0175)


def test_forca_nocional_usa_ec5_sem_reducao_por_colunas():
    """O EC5 não reduz φ pelo número de colunas (ao contrário do α_m da
    EN 1993-1-1 §5.3.2, que fica só como comparação)."""
    r2 = forca_nocional(V_Ed_kN=1000.0, h_m=7.0, m_colunas=2)
    r9 = forca_nocional(V_Ed_kN=1000.0, h_m=7.0, m_colunas=9)
    assert r2["phi"] == r9["phi"] == pytest.approx(0.004226, abs=1e-6)
    assert "5.4.4" in r2["norma"]
    assert r2["phi"] > r2["phi_en1993_comparacao"]


def test_contraventamento_vertical_usa_a_mesma_fonte():
    from mlc_projeto.checks.elu.contraventamento_vertical import (
        forca_nocional as fn_cv,
    )
    assert fn_cv(1000.0, 7.0, 9)["H_imp_kN"] == pytest.approx(
        forca_nocional(1000.0, 7.0, 9)["H_imp_kN"])
