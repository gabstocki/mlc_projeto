"""Ancoragem do canto — chumbadores moldados com cabeça e cortante do CV.

Dois problemas tratados aqui:

  A) O CORTANTE DOS PAINÉIS não chegava à verificação da ancoragem.
     `verificar_succao_uplift` tomava o cortante na base como |H_suc| — apenas o
     empuxo do arco, NULO no modelo adotado (Opção B). Os ~236 kN que os painéis
     de contraventamento entregam à MESMA base, na mesma combinação de vento,
     ficavam de fora. E não há atrito a compensar: no caso governante a base
     está tracionada, sem compressão sob a chapa.

  B) O `F_CHU_KN = 80 kN` era um valor ARBITRADO. Com chumbadores moldados com
     cabeça, o lado do aço é verificável por EN 1993-1-8 a partir da bitola e
     da classe; o lado do concreto exige EN 1992-4, que o projeto ainda não tem
     em cópia controlada — e por isso permanece NOT VALIDATED.
"""

from __future__ import annotations

import pytest

from mlc_projeto.connections.ancoragem import (
    CAMPOS_CONCRETO_OBRIGATORIOS,
    area_resistente,
    resistencia_aco_barra,
    verificar_grupo_ancoragem,
)


# Geometria adotada no projeto: c = 1,5·h_ef, que é o ponto em que a borda
# deixa de truncar o cone. Com c/s menores o cone REPROVA — ver
# test_cone_governa_e_e_sensivel_a_borda_e_espacamento.
DADOS_COMPLETOS = {
    "h_ef_mm": 400.0, "A_cabeca_mm2": 2375.0, "c_borda_mm": 600.0,
    "s_grupo_mm": 400.0, "classe_concreto": "C25/30",
    "concreto_fissurado": True,
    "verificacao_en1992_4": "CEN/TS 1992-4-2:2009 §6.2.4/6.2.5/6.3.4/6.4",
}


# ── Lado do aço ──────────────────────────────────────────────────────────────

def test_resistencia_do_aco_com_gamma_Ms_por_efeito():
    """EN 1992-4:2018 Tab. 4.1 — γ_Ms difere entre tração e corte."""
    r = resistencia_aco_barra(24, "8.8")
    A_s, f_ub = area_resistente(24), 800.0
    assert r["gamma_Ms_tracao"] == pytest.approx(1.5, rel=1e-6)   # 1,2·800/640
    assert r["gamma_Ms_corte"] == pytest.approx(1.25, rel=1e-6)   # ≥1,25
    assert r["N_Rd_kN"] == pytest.approx(0.9 * f_ub * A_s / 1.5 / 1e3, rel=1e-3)
    assert r["V_Rd_kN"] == pytest.approx(0.6 * f_ub * A_s / 1.25 / 1e3, rel=1e-3)


def test_gamma_Ms_corte_penaliza_classe_10_9():
    """f_yk/f_uk > 0,8 na 10.9 ⇒ γ_Ms,corte = 1,5, não 1,25."""
    from mlc_projeto.connections.ancoragem import gamma_Ms_corte
    assert gamma_Ms_corte("8.8") == pytest.approx(1.25, rel=1e-6)
    assert gamma_Ms_corte("10.9") == pytest.approx(1.5, rel=1e-6)


def test_classe_e_diametro_invalidos_sao_rejeitados():
    with pytest.raises(ValueError, match="classe"):
        resistencia_aco_barra(24, "12.9")
    with pytest.raises(ValueError, match="áreas resistentes"):
        area_resistente(23)


def test_resistencia_cresce_com_bitola_e_classe():
    assert (resistencia_aco_barra(30, "8.8")["N_Rd_kN"]
            > resistencia_aco_barra(24, "8.8")["N_Rd_kN"])
    assert (resistencia_aco_barra(24, "10.9")["N_Rd_kN"]
            > resistencia_aco_barra(24, "8.8")["N_Rd_kN"])


# ── Chaveta: desacopla o cortante ────────────────────────────────────────────

def test_chaveta_retira_o_cortante_dos_chumbadores():
    sem = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=False)
    com = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=True)
    assert sem["eta_V"] > 0.0
    assert com["eta_V"] == 0.0
    assert com["eta_interacao"] < sem["eta_interacao"]
    assert com["V_nos_chumbadores_kN"] == 0.0


def test_interacao_tracao_cortante_e_aplicada():
    """EN 1993-1-8 §3.4: F_v/F_v,Rd + F_t/(1,4·F_t,Rd) ≤ 1,0."""
    r = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=False)
    esperado = r["eta_V"] + r["N_Ed_kN"] / (1.4 * r["N_Rd_grupo_kN"])
    assert r["eta_interacao"] == pytest.approx(esperado, rel=1e-3)
    assert r["eta_aco"] >= r["eta_N"]


# ── O aço passar NÃO aprova a ancoragem ──────────────────────────────────────

def test_aco_ok_nao_aprova_sem_o_lado_do_concreto():
    r = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=True)
    assert r["ok_aco"] is True
    assert r["en_1992_4_verificado"] is False
    assert r["status_concreto"] == "NOT VALIDATED"
    assert r["ok"] is False, "aço aprovado não pode aprovar a ancoragem"
    assert len(r["modos_en_1992_4_pendentes"]) == 7


def test_com_dados_completos_do_concreto_o_contrato_fecha():
    r = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=True,
                                  dados_concreto=DADOS_COMPLETOS)
    assert r["en_1992_4_verificado"] is True
    assert r["ok"] is True


def test_moldado_com_cabeca_nao_exige_eta_de_produto():
    """Cast-in headed: o concreto é coberto pelos modelos da norma, sem ETA."""
    assert "eta_produto" not in CAMPOS_CONCRETO_OBRIGATORIOS
    r = verificar_grupo_ancoragem(100.0, 0.0, 4)
    assert r["tipo_ancoragem"] == "moldado_com_cabeca"
    assert "PÓS-INSTALADO" in r["nota_eta"].upper()


# ── (A) O cortante dos painéis chega à verificação de uplift ────────────────

def test_cortante_do_contraventamento_entra_na_verificacao_de_uplift():
    """Regressão: sem a chaveta, V_brace tem de penalizar o η do canto."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from test_auditoria_regressoes import _modelo
    from mlc_projeto.checks.elu.succao_uplift import verificar_succao_uplift

    geo, mat, _, load = _modelo(empuxo=False)
    kw = dict(load=load, geo=geo, F_chu_kN=80.0, n_chu=4, b_pilar=0.32,
              h_pilar=0.27, H_pilar_m=7.0, rho_mean_kgm3=mat.rho_mean,
              com_tirante=False, N_brace_anc_kN=287.4, n_chu_canto=6)

    sem_v = verificar_succao_uplift(**kw, V_brace_kN=0.0)
    com_v = verificar_succao_uplift(**kw, V_brace_kN=236.1)
    com_chaveta = verificar_succao_uplift(**kw, V_brace_kN=236.1,
                                          chaveta_cisalhamento=True)

    assert com_v["eta"] > sem_v["eta"], "o cortante dos painéis deve penalizar"
    assert com_v["V_canto_kN"] == pytest.approx(236.1, rel=1e-6)
    # A chaveta desacopla: volta ao η só de tração.
    assert com_chaveta["eta"] == pytest.approx(sem_v["eta"], rel=1e-9)
    assert com_chaveta["V_canto_nos_chumbadores_kN"] == 0.0


# ── Lado do concreto — CEN/TS 1992-4-2:2009 ─────────────────────────────────

def test_cone_governa_sobre_o_pullout():
    """Com cabeça de área usual, o cone é o modo crítico — não o pull-out."""
    r = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=True,
                                  dados_concreto=DADOS_COMPLETOS, layout=(2, 3))
    assert r["modo_concreto_gov"] == "cone"
    assert r["N_Rd_cone_kN"] < r["N_Rd_pullout_kN"]


def test_o_aco_nao_e_o_modo_critico():
    """Em chumbador, quem governa é o concreto. η_aço sozinho engana."""
    r = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=True,
                                  dados_concreto=DADOS_COMPLETOS, layout=(2, 3))
    assert r["eta_concreto"] > r["eta_aco"]
    assert r["eta"] == pytest.approx(r["eta_concreto"], rel=1e-9)


def test_cone_e_sensivel_a_borda_e_espacamento():
    """Borda/espaçamento pequenos truncam o cone e reprovam."""
    apertado = dict(DADOS_COMPLETOS, c_borda_mm=250.0, s_grupo_mm=200.0)
    r = verificar_grupo_ancoragem(371.3, 236.1, 6, chaveta_cisalhamento=True,
                                  dados_concreto=apertado, layout=(2, 3))
    assert r["eta_concreto"] > 1.0
    assert r["ok"] is False


def test_mais_profundidade_nao_resolve_com_borda_fixa():
    """Constatação de projeto: h_ef maior PIORA se c e s não acompanharem.

    A⁰_c,N = (3·h_ef)² cresce ao quadrado enquanto A_c,N fica truncado por c e
    por s. Quem governa o cone é o TAMANHO DO BLOCO, não a profundidade.
    """
    raso = dict(DADOS_COMPLETOS, h_ef_mm=300.0, c_borda_mm=450.0, s_grupo_mm=300.0)
    fundo = dict(raso, h_ef_mm=700.0)
    eta_raso = verificar_grupo_ancoragem(371.3, 0.0, 6, chaveta_cisalhamento=True,
                                         dados_concreto=raso, layout=(2, 3))["eta_concreto"]
    eta_fundo = verificar_grupo_ancoragem(371.3, 0.0, 6, chaveta_cisalhamento=True,
                                          dados_concreto=fundo, layout=(2, 3))["eta_concreto"]
    assert eta_fundo > eta_raso


def test_declara_a_edicao_normativa_usada():
    """A edição efetivamente usada é a EN 1992-4:2018, não a TS retirada."""
    r = verificar_grupo_ancoragem(371.3, 0.0, 6, chaveta_cisalhamento=True,
                                  dados_concreto=DADOS_COMPLETOS, layout=(2, 3))
    assert r["norma_concreto"] == "BS EN 1992-4:2018"
    assert "CEN/TS" not in r["norma_concreto"], "a TS de 2009 está retirada"
    assert r["modos_ainda_pendentes"], "blow-out/fendilhamento/borda seguem pendentes"


def test_coeficientes_sao_os_da_edicao_2018():
    """k1 e k2 mudaram face à CEN/TS retirada; o cone usa f_ck CILINDRO."""
    from mlc_projeto.connections.ancoragem import (
        K_CR_HEADED, K_UCR_HEADED, K2_PULLOUT_CR, F_CK_CILINDRO,
    )
    assert (K_CR_HEADED, K_UCR_HEADED) == (8.9, 12.7)   # (7.2) NOTA, cast-in
    assert K2_PULLOUT_CR == 7.5                         # (7.11)
    assert F_CK_CILINDRO["C25/30"] == 25.0              # cilindro, não cubo
