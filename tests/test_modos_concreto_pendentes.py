"""
Achado A4 — os três modos da EN 1992-4 que estavam «declarados como pendentes».

`modos_ainda_pendentes` listava fendilhamento (§7.2.1.7), blow-out (§7.2.1.9) e
rotura de borda sob corte (§7.2.2.5), com a nota de que deviam ser confirmados
como não governantes. Declarar é melhor que esquecer — mas com a ancoragem a
η = 0,53 um modo por verificar é uma incógnita no elo mais frágil.

Cada um passa a ter uma de três saídas, e nunca silêncio:
  · resistência calculada;
  · dispensa, com a cláusula citada;
  · não-verificável, com o dado em falta escrito — e sem `ok`.
"""

import math

import pytest

from mlc_projeto.connections import ancoragem as A


DADOS = dict(
    h_ef_mm=400.0, A_cabeca_mm2=2375.0, c_borda_mm=600.0, s_grupo_mm=400.0,
    classe_concreto="C25/30", concreto_fissurado=True,
    verificacao_en1992_4="EN 1992-4:2018",
)


# ── Blow-out lateral (§7.2.1.9) ─────────────────────────────────────────────

def test_blowout_dispensado_quando_a_borda_e_folgada():
    """§7.2.1.9(1): c1 > 0,5·h_ef dispensa. Com a citação, não por afirmação."""
    r = A.resistencia_blowout(c1_mm=600.0, A_h_mm2=2375.0, h_ef_mm=400.0,
                              classe_concreto="C25/30")
    assert r["aplicavel"] is False
    assert math.isinf(r["N_Rk_cb_kN"])
    assert "7.2.1.9(1)" in r["criterio_dispensa"]


def test_blowout_calculado_quando_a_borda_e_curta():
    """c1 = 150 < 0,5·h_ef = 200 ⇒ verifica-se pela Eq. (7.24)."""
    r = A.resistencia_blowout(c1_mm=150.0, A_h_mm2=2375.0, h_ef_mm=400.0,
                              classe_concreto="C25/30")
    assert r["aplicavel"] is True
    # N⁰ = k5·c1·√A_h·√f_ck, k5 = 8,0 (fissurado)
    N0 = 8.0 * 150.0 * math.sqrt(2375.0) * math.sqrt(25.0) / 1e3
    assert r["N0_Rk_cb_kN"] == pytest.approx(N0, abs=5e-3)
    assert r["N_Rk_cb_kN"] > 0


def test_blowout_no_canto_e_menor_que_na_borda_unica():
    kw = dict(c1_mm=150.0, A_h_mm2=2375.0, h_ef_mm=400.0,
              classe_concreto="C25/30")
    borda = A.resistencia_blowout(**kw, n_bordas=1)
    canto = A.resistencia_blowout(**kw, n_bordas=2)
    assert canto["N_Rk_cb_kN"] < borda["N_Rk_cb_kN"]


def test_blowout_nao_fissurado_e_maior():
    kw = dict(c1_mm=150.0, A_h_mm2=2375.0, h_ef_mm=400.0,
              classe_concreto="C25/30")
    assert (A.resistencia_blowout(**kw, fissurado=False)["N_Rk_cb_kN"]
            > A.resistencia_blowout(**kw, fissurado=True)["N_Rk_cb_kN"])


# ── Fendilhamento (§7.2.1.7) ────────────────────────────────────────────────

def test_fendilhamento_dispensado_por_borda_e_espessura():
    r = A.resistencia_fendilhamento(
        c_min_mm=1500.0, h_bloco_mm=900.0, h_ef_mm=400.0, N_Rk_c_kN=791.0)
    assert r["aplicavel"] is False
    assert "7.2.1.7(2)(a)" in r["criterio_dispensa"]


def test_fendilhamento_dispensado_por_armadura():
    r = A.resistencia_fendilhamento(
        c_min_mm=300.0, h_bloco_mm=500.0, h_ef_mm=400.0, N_Rk_c_kN=791.0,
        armadura_controla_fissuras=True)
    assert r["aplicavel"] is False
    assert "7.2.1.7(2)(b)" in r["criterio_dispensa"]


def test_fendilhamento_reduz_o_cone_em_bloco_fino():
    """ψ_h,sp = (h/(2h_ef))^(2/3) < 1 quando h < 2·h_ef."""
    r = A.resistencia_fendilhamento(
        c_min_mm=600.0, h_bloco_mm=500.0, h_ef_mm=400.0, N_Rk_c_kN=791.0)
    assert r["aplicavel"] is True
    assert r["psi_h_sp"] == pytest.approx((500.0 / 800.0) ** (2 / 3), abs=5e-5)
    assert r["N_Rk_sp_kN"] < 791.0


def test_fendilhamento_com_h_igual_2hef_nao_reduz():
    r = A.resistencia_fendilhamento(
        c_min_mm=600.0, h_bloco_mm=800.0, h_ef_mm=400.0, N_Rk_c_kN=791.0)
    assert r["psi_h_sp"] == pytest.approx(1.0)
    assert r["N_Rk_sp_kN"] == pytest.approx(791.0)


# ── Rotura de borda sob corte (§7.2.2.5) ────────────────────────────────────

def test_borda_nao_aplicavel_com_chaveta_e_zero_nos_chumbadores():
    """
    «Não aplicável» tem de ser DEMONSTRADO: exige-se a declaração da chaveta E
    que a força nas barras seja de facto nula.
    """
    r = A.resistencia_borda_corte(
        chaveta_cisalhamento=True, V_nos_chumbadores_kN=0.0)
    assert r["aplicavel"] is False
    assert "CHAVETA" in r["criterio_dispensa"]
    assert "6.7" in r["criterio_dispensa"]     # aponta o que passa a exigir


def test_borda_volta_a_ser_exigida_se_o_corte_passar_pelas_barras():
    r = A.resistencia_borda_corte(
        chaveta_cisalhamento=True, V_nos_chumbadores_kN=50.0)
    assert r["aplicavel"] is True
    assert r["verificavel"] is False       # faltam dados → não é ok
    assert "não verificado não é ok" in r["motivo"]


def test_borda_calculada_com_todos_os_dados():
    r = A.resistencia_borda_corte(
        chaveta_cisalhamento=False, V_nos_chumbadores_kN=50.0,
        c1_mm=600.0, h_ef_mm=400.0, d_nom_mm=24.0, l_f_mm=400.0,
        classe_concreto="C25/30")
    assert r["verificavel"] is True
    assert r["k9"] == 1.7                      # fissurado
    assert r["l_f_mm"] == pytest.approx(min(400.0, 12 * 24.0))
    assert r["V_Rk_c_kN"] > 0


# ── Esmagamento sob a chaveta (EN 1992-1-1 §6.7) ────────────────────────────

def test_esmagamento_da_chaveta_contra_a_formula():
    r = A.esmagamento_chaveta(V_Ed_kN=159.0, l_chaveta_mm=200.0,
                              h_embutida_mm=80.0, classe_concreto="C25/30")
    f_cd = 1.0 * 25.0 / 1.5
    F_Rdu = 200.0 * 80.0 * f_cd / 1e3
    assert r["F_Rdu_kN"] == pytest.approx(F_Rdu, abs=5e-3)
    assert r["eta"] == pytest.approx(159.0 / F_Rdu, abs=5e-5)
    assert r["ok"] is True


def test_confinamento_e_limitado_a_3():
    r = A.esmagamento_chaveta(V_Ed_kN=100.0, l_chaveta_mm=200.0,
                              h_embutida_mm=80.0, classe_concreto="C25/30",
                              A_c1_sobre_A_c0=100.0)
    assert r["fator_confinamento"] == pytest.approx(3.0)


def test_confinamento_menor_que_um_e_recusado():
    with pytest.raises(ValueError):
        A.esmagamento_chaveta(V_Ed_kN=100.0, l_chaveta_mm=200.0,
                              h_embutida_mm=80.0, classe_concreto="C25/30",
                              A_c1_sobre_A_c0=0.5)


# ── Integração no grupo ─────────────────────────────────────────────────────

def test_grupo_verifica_os_tres_modos_e_ja_nao_os_lista_como_pendentes():
    d = dict(DADOS, h_bloco_mm=800.0)
    r = A.verificar_grupo_ancoragem(371.3, 0.0, 6, chaveta_cisalhamento=True,
                                    dados_concreto=d, layout=(2, 3))
    assert r["modos_ainda_pendentes"] == []
    assert r["blowout"]["aplicavel"] is False       # dispensado, com citação
    assert r["fendilhamento"]["aplicavel"] is True  # h = 2·h_ef ⇒ ψ = 1
    assert r["borda_corte"]["aplicavel"] is False   # chaveta
    assert r["modos_nao_verificaveis"] == []
    assert r["ok_concreto"] is True


def test_sem_h_bloco_o_fendilhamento_fica_nao_verificavel_e_nao_aprova():
    """
    A espessura do bloco é dado da FUNDAÇÃO. Sem ela, §7.2.1.7 não se verifica
    — e um modo aplicável e não verificado não pode passar por `ok`.
    """
    r = A.verificar_grupo_ancoragem(371.3, 0.0, 6, chaveta_cisalhamento=True,
                                    dados_concreto=DADOS, layout=(2, 3))
    assert r["modos_nao_verificaveis"] == ["fendilhamento (§7.2.1.7)"]
    assert r["ok_concreto"] is False
    assert "h_bloco_mm" in r["fendilhamento"]["motivo"]


def test_bloco_fino_faz_o_fendilhamento_governar():
    d = dict(DADOS, h_bloco_mm=400.0)          # h = h_ef, metade do exigido
    r = A.verificar_grupo_ancoragem(371.3, 0.0, 6, chaveta_cisalhamento=True,
                                    dados_concreto=d, layout=(2, 3))
    assert r["modo_concreto_gov"] == "fendilhamento"
    assert r["N_Rd_fendilhamento_kN"] < r["N_Rd_cone_kN"]


# ── Requisitos publicados à fundação ────────────────────────────────────────

def test_requisitos_de_fundacao_sao_publicados_e_nao_assumidos():
    r = A.requisitos_de_fundacao_para_ancoragem(h_ef_mm=400.0, c_borda_mm=600.0)
    assert r["c1_min_dispensa_blowout_mm"] == pytest.approx(200.0)
    assert r["h_bloco_min_dispensa_fendilhamento_mm"] == pytest.approx(800.0)
    assert r["blowout_dispensado_pela_borda_declarada"] is True
    assert "Projetista de fundações" in r["destinatario"]


def test_chaveta_entra_no_catalogo_de_exportacao():
    from mlc_projeto.output.report import VERIFICACOES_EXPORT
    chaves = {c for c, _, _ in VERIFICACOES_EXPORT}
    assert "chaveta_concreto" in chaves
    norma = next(n for c, _, n in VERIFICACOES_EXPORT if c == "chaveta_concreto")
    assert "1992-1-1" in norma and "6.7" in norma
