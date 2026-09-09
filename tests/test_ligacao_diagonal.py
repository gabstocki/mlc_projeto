"""
Achado A3 — ligações de EXTREMIDADE das diagonais de contraventamento.

A barra estava verificada desde o [F-11]; o pino, o olhal e a solda que a
seguram não existiam. Estes testes fixam as resistências contra as fórmulas da
EN 1993-1-8 (valores calculados à mão) e a decisão de projeto que importa: a
ligação é dimensionada pela CAPACIDADE da barra, para que a plastificação
fique no tirante e não no pino.
"""

import math

import pytest

from mlc_projeto.connections import ligacao_diagonal as LD


# ── Resistências elementares (EN 1993-1-8 Tab. 3.10, §4.5.3.3) ───────────────

def test_corte_do_pino_contra_a_formula():
    """F_v,Rd = 0,6·A·f_up/γ_M2, por plano de corte."""
    A = math.pi * 36.0 ** 2 / 4.0
    esperado = 0.6 * A * 510.0 / 1.25 / 1e3          # S355 f_u = 510
    assert LD.resistencia_corte_pino(36, "S355") == pytest.approx(esperado)


def test_esmagamento_contra_a_formula():
    """F_b,Rd = 1,5·t·d·f_y/γ_M0."""
    esperado = 1.5 * 20.0 * 36.0 * 235.0 / 1.00 / 1e3
    assert LD.resistencia_esmagamento(20, 36, "S235") == pytest.approx(esperado)


def test_flexao_do_pino_contra_a_formula():
    """M_Rd = 1,5·W_el·f_yp/γ_M0, com W_el = π·d³/32."""
    W_el = math.pi * 36.0 ** 3 / 32.0
    esperado = 1.5 * W_el * 355.0 / 1.00 / 1e6
    assert LD.momento_resistente_pino(36, "S355") == pytest.approx(esperado)


def test_momento_atuante_usa_o_braco_da_figura_3_11():
    """M_Ed = F/8 · (b + 4c + 2a) — chapa interior b, abas a, folgas c."""
    F, b, a, c = 200.0, 20.0, 12.0, 2.0
    esperado = F * (b + 4 * c + 2 * a) / 8.0 / 1e3
    assert LD.momento_atuante_pino(F, b, a, c) == pytest.approx(esperado)


def test_solda_de_angulo_metodo_simplificado():
    """f_vw,d = (f_u/√3)/(β_w·γ_M2); β_w = 0,80 em S235 (Tab. 4.1)."""
    f_vw_d = (360.0 / math.sqrt(3.0)) / (0.80 * 1.25)
    esperado = f_vw_d * 5.0 * 120.0 * 2 / 1e3
    assert LD.resistencia_solda_angulo(5, 120, 2, "S235") == pytest.approx(esperado)


def test_solda_recusa_aco_sem_beta_w_tabelado():
    with pytest.raises(ValueError, match="β_w"):
        LD.resistencia_solda_angulo(5, 120, 2, "S460")


def test_geometria_do_olhal_contra_a_tabela_3_9():
    """a ≥ F·γ_M0/(2·t·f_y) + 2d_0/3 ; c ≥ (mesmo termo) + d_0/3."""
    F, t, d_0 = 211.7, 20.0, 37.0
    termo = F * 1e3 / (2.0 * t * 235.0)
    g = LD.geometria_olhal_requerida(F, t, d_0, "S235")
    assert g["a_req_mm"] == pytest.approx(termo + 2 * d_0 / 3)
    assert g["c_req_mm"] == pytest.approx(termo + d_0 / 3)
    assert g["a_req_mm"] > g["c_req_mm"]      # a direção da força pede mais


# ── Verificação de um detalhe dado ───────────────────────────────────────────

def test_verificacao_reporta_todos_os_modos_e_o_governante():
    r = LD.verificar_ligacao_diagonal(
        N_Ed_kN=166.9, d_pino_mm=36, t_eye_mm=20, t_fork_mm=12,
        a_borda_mm=55, c_borda_mm=40, a_solda_mm=5, l_solda_mm=120,
    )
    assert set(r["etas"]) == {
        "corte_pino", "esmagamento_olhal", "esmagamento_manilha",
        "flexao_pino", "interacao_M_V", "geometria_a", "geometria_c", "solda",
    }
    assert r["eta"] == max(r["etas"].values())
    assert r["modo_gov"] in r["etas"]
    assert r["ok"] is True


def test_detalhe_subdimensionado_reprova():
    """Chapa fina de mais: a geometria da Tab. 3.9 deixa de ser satisfeita."""
    r = LD.verificar_ligacao_diagonal(
        N_Ed_kN=300.0, d_pino_mm=20, t_eye_mm=8, t_fork_mm=8,
        a_borda_mm=30, c_borda_mm=25, a_solda_mm=4, l_solda_mm=80,
    )
    assert r["eta"] > 1.0
    assert r["ok"] is False


def test_corte_duplo_reparte_a_forca_pelos_dois_planos():
    """η de corte = (F/2)/F_v,Rd — o pino trabalha em corte duplo."""
    F = 200.0
    r = LD.verificar_ligacao_diagonal(
        N_Ed_kN=F, d_pino_mm=36, t_eye_mm=20, t_fork_mm=12,
        a_borda_mm=60, c_borda_mm=45, a_solda_mm=5, l_solda_mm=120,
    )
    esperado = (F / 2.0) / LD.resistencia_corte_pino(36, "S355")
    assert r["etas"]["corte_pino"] == pytest.approx(esperado, abs=5e-5)


# ── Dimensionamento: o critério de capacidade ────────────────────────────────

@pytest.fixture
def diagonal_longitudinal():
    """A diagonal do painel longitudinal do projeto: ∅36 S235."""
    from mlc_projeto.checks.elu.contraventamento_vertical import (
        resistencia_tracao_diagonal,
    )
    barra = resistencia_tracao_diagonal(36, "S235")
    return dict(N_Ed_kN=166.9, N_barra_Rd_kN=barra["N_t_Rd_kN"], d_barra_mm=36)


def test_dimensiona_por_capacidade_e_declara_a_sobre_resistencia(
        diagonal_longitudinal):
    r = LD.dimensionar_ligacao_diagonal(**diagonal_longitudinal)
    assert r["criterio"] == "capacidade"
    assert r["N_dimensionamento_kN"] == pytest.approx(r["N_barra_Rd_kN"])
    assert r["sobre_resistencia"] > 1.0
    # η da linha do memorial é sob o esforço REAL (comparável às outras linhas)
    assert r["eta"] < r["eta_capacidade"]
    # e o ok exige os DOIS ≤ 1 — senão o critério de capacidade seria decorativo
    assert r["ok"] is True
    assert r["eta_capacidade"] <= 0.90


def test_o_pino_nunca_e_mais_fino_que_a_barra(diagonal_longitudinal):
    r = LD.dimensionar_ligacao_diagonal(**diagonal_longitudinal)
    assert r["d_pino_mm"] >= diagonal_longitudinal["d_barra_mm"]


def test_criterio_esforco_nunca_pede_mais_que_o_de_capacidade(
        diagonal_longitudinal):
    cap = LD.dimensionar_ligacao_diagonal(**diagonal_longitudinal)
    esf = LD.dimensionar_ligacao_diagonal(
        **diagonal_longitudinal, criterio="esforco")
    assert esf["N_dimensionamento_kN"] < cap["N_dimensionamento_kN"]
    assert esf["t_eye_mm"] <= cap["t_eye_mm"]
    assert esf["sobre_resistencia"] == pytest.approx(1.0)


def test_criterio_invalido_e_recusado(diagonal_longitudinal):
    with pytest.raises(ValueError, match="criterio"):
        LD.dimensionar_ligacao_diagonal(
            **diagonal_longitudinal, criterio="qualquer")


def test_requisito_da_manilha_e_declarado_e_nao_inventado(
        diagonal_longitudinal):
    """
    A manilha é peça de catálogo. O memorial declara a força que ela tem de
    garantir — não lhe atribui resistência.
    """
    r = LD.dimensionar_ligacao_diagonal(**diagonal_longitudinal)
    assert r["requisito_manilha_kN"] == pytest.approx(r["N_dimensionamento_kN"])
    assert "fabricante" in r["nota_manilha"]


def test_quando_nada_serve_reprova_em_vez_de_lancar():
    """
    Regra 5 das convenções do projeto: η > 1 REGISTA-SE, não se lança. Um
    detalhe inexequível tem de reprovar a linha do memorial — se levantasse,
    rebentava o pipeline e a estrutura mal dimensionada a montante nunca
    chegava a ser reprovada (foi o que aconteceu com o cenário de 2 painéis
    do F-13).
    """
    r = LD.dimensionar_ligacao_diagonal(
        N_Ed_kN=8000.0, N_barra_Rd_kN=9000.0, d_barra_mm=60)
    assert r["alvo_atingido"] is False
    assert r["ok"] is False
    assert r["eta"] > 1.0
    assert "motivo" in r


def test_pino_impossivel_e_declarado_e_reprova():
    """Barra maior que qualquer pino de catálogo: o detalhe não é exequível."""
    d_max = LD.D_PINO_COMERCIAL_MM[-1]
    r = LD.dimensionar_ligacao_diagonal(
        N_Ed_kN=667.5, N_barra_Rd_kN=693.6, d_barra_mm=d_max + 4)
    assert r["pino_menor_que_barra"] is True
    assert r["ok"] is False
    assert "pino comercial" in r["motivo"]


# ── Integração com o memorial ────────────────────────────────────────────────

def test_ligacoes_das_diagonais_entram_no_catalogo_de_exportacao():
    from mlc_projeto.output.report import VERIFICACOES_EXPORT
    chaves = {c for c, _, _ in VERIFICACOES_EXPORT}
    assert {"lig_diag_vertical", "lig_diag_transversal"} <= chaves
    for chave in ("lig_diag_vertical", "lig_diag_transversal"):
        norma = next(n for c, _, n in VERIFICACOES_EXPORT if c == chave)
        assert "1993-1-8" in norma
