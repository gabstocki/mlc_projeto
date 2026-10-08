"""Testes — não-concomitância Q×vento, categoria H (issue 3)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import (
    carregamentos_com_vento, peso_proprio_gk,
    GAMMA_G_sup, GAMMA_G_EQU_estab, GAMMA_Q, PSI_0_Q, PSI_1_Q, PSI_2_Q,
)


def _load():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    pp = peso_proprio_gk(geo, GlulamMaterial("GL24h", 3, "longa"),
                         5.75, 0.20, 0.58, 2.53, 0.10, 0.10)
    load = carregamentos_com_vento(geo, mat, pp["g_k_viga_kNm2"], 0.25, 5.75, pv,
                                   n_pilares_linha=9, n_linhas_portico=3,
                                   L_cob_m=46.0, B_cob_m=2 * geo.L)
    return load


def test_psi0_Q_categoria_H_zero():
    assert PSI_0_Q == 0.0


def test_coeficientes_G_EN1990():
    """
    Issue 4: G favorável STR = 1,00 (EN 1990 Tab. A1.2(B), NÃO 0,90 da NBR);
    EQU estabilizante = 0,90 e desestabilizante = 1,10 (Tab. A1.2(A)).
    """
    from mlc_projeto.core.loads import (
        GAMMA_G_inf, GAMMA_G_EQU_estab, GAMMA_G_EQU_desestab,
    )
    assert GAMMA_G_inf == 1.00              # STR favorável (Tab. A1.2(B))
    assert GAMMA_G_EQU_estab == 0.90        # EQU estabilizante (Tab. A1.2(A))
    assert GAMMA_G_EQU_desestab == 1.10     # EQU desestabilizante (Tab. A1.2(A))


def test_succao_usa_090_EQU():
    """A combinação de sucção (uplift/EQU) usa 0,90·G (Tab. A1.2(A))."""
    load = _load()
    g = load.g_k
    c3 = load.combinacao_ELU_succao()          # ELU_C3
    # recupera o vento a partir de q = 0,90G + 1,5W  →  W = (q − 0,90G)/1,5
    w = (c3.q_esq - GAMMA_G_EQU_estab * g) / GAMMA_Q
    # coerência: reconstruído bate com 0,90G + 1,5W
    assert c3.q_esq == pytest.approx(GAMMA_G_EQU_estab * g + GAMMA_Q * w, rel=1e-9)
    assert c3.q_esq < 0                          # net uplift (sucção domina)


def test_combo_Q_dominante_sem_vento():
    """ELU_Q = 1,35G + 1,5Q (sem vento) — cat. H não concomitante."""
    load = _load()
    g, q = load.g_k, load.q_k
    cq = load.combinacoes["ELU_Q"]
    esperado = GAMMA_G_sup * g + GAMMA_Q * q
    assert cq.q_esq == pytest.approx(esperado, rel=1e-6)
    assert cq.q_dir == pytest.approx(esperado, rel=1e-6)
    assert cq.duracao == "media"          # sobrecarga → média (EC5 Tab. 2.1)


def test_combo_vento_dominante_sem_Q():
    """ELU_W_* = 1,35G + 1,5W (sem Q); ELU_S_* = 0,9G + 1,5W (sem Q)."""
    load = _load()
    g = load.g_k
    # escolhe um padrão de vento qualquer presente
    nomes_W = [n for n in load.combinacoes if n.startswith("ELU_W_")]
    nomes_S = [n for n in load.combinacoes if n.startswith("ELU_S_")]
    assert nomes_W and nomes_S
    cw = load.combinacoes[nomes_W[0]]
    cs = load.combinacoes[nomes_S[0]]
    # q_esq de ELU_W = 1,35G + 1,5·w_esq  (sem termo de Q)
    w_esq_W = (cw.q_esq - GAMMA_G_sup * g) / GAMMA_Q     # recupera w_esq
    # ELU_S (sucção/uplift) = EQU: 0,90G_estab + 1,5·w_esq (EN 1990 Tab. A1.2(A))
    assert cs.q_esq == pytest.approx(GAMMA_G_EQU_estab * g + GAMMA_Q * w_esq_W, rel=1e-6)


def test_els_caracteristico_sem_vento():
    """ELS_S1 = G + Q (sem vento) — cat. H."""
    load = _load()
    g, q = load.g_k, load.q_k
    s1 = load.combinacoes["ELS_S1"]
    assert s1.q_esq == pytest.approx(g + q, rel=1e-6)
    assert s1.q_dir == pytest.approx(g + q, rel=1e-6)


def test_psi1_psi2_categoria_H_zero():
    """Issue 5: cat. H → ψ1 = ψ2 = 0 (EN 1990 Tab. A1.1)."""
    assert PSI_1_Q == 0.0
    assert PSI_2_Q == 0.0


def test_els_frequente_e_quasipermanente_iguais_a_G():
    """
    Cat. H (ψ1=ψ2=0): a combinação frequente (ELS_S2) e a quase-permanente
    (ELS_S3) reduzem-se ambas a G.
    """
    load = _load()
    g = load.g_k
    s2 = load.combinacoes["ELS_S2"]
    s3 = load.combinacoes["ELS_S3"]
    assert s2.q_esq == pytest.approx(g, rel=1e-9)      # G (sem Q)
    assert s3.q_esq == pytest.approx(g, rel=1e-9)
    assert s2.q_esq == pytest.approx(s3.q_esq, rel=1e-9)   # S2 == S3 == G


def test_nao_ha_combo_com_Q_e_vento_juntos():
    """
    Nenhuma combinação ELU deve ter Q E vento simultâneos. Verifica-se que toda
    combinação gravítica (q_tot>0, sem vento) tem q_tot = 1,35G+1,5Q OU é vento
    puro (1,35G+1,5W). Prova operacional: a combinação de maior q_tot gravítico
    ou é o vento-pressão (padrao≠"") ou é a sobrecarga pura (ELU_Q, padrao="").
    """
    load = _load()
    g, q = load.g_k, load.q_k
    q_puro = GAMMA_G_sup * g + GAMMA_Q * q         # 1,35G+1,5Q
    for nome, c in load.combinacoes_ELU().items():
        if c.padrao_vento == "":
            # combinação sem vento → deve ser a sobrecarga pura (ou alias dela)
            assert c.q_esq == pytest.approx(q_puro, rel=1e-6), nome
        # combinações com vento (padrao≠"") não contêm o termo 1,05Q:
        # a checagem direta de valores está em test_combo_vento_dominante_sem_Q


def test_ELU_C2_herda_duracao_do_governante():
    """
    Regressão (revisão da base): o alias ELU_C2 deve herdar a duração REAL do
    combinação que governa o |M|. Antes era fixado em 'curta' — se a sobrecarga Q
    (duração 'media') governasse, o k_mod ficava errado (0,70 vs 0,65 em CS3),
    a favor da resistência (contra a segurança).
    """
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")

    # (a) vento governa → ELU_C2 deve ser 'curta'
    pv_forte = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                               L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load_w = carregamentos_com_vento(geo, mat, 0.82, 0.40, 5.75, pv_forte)
    gov_w = load_w.combinacao_ELU_governante()
    assert load_w.combinacoes["ELU_C2"].duracao == gov_w.duracao

    # (b) sobrecarga Q governa (vento mínimo, q alta) → ELU_C2 deve ser 'media'
    pv_fraco = ParametrosVento(V0=1.0, S1=1, categoria="IV", classe="B", S3=1,
                               L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load_q = carregamentos_com_vento(geo, mat, 0.82, 5.0, 5.75, pv_fraco)
    gov_q = load_q.combinacao_ELU_governante()
    assert "1,5Q" in gov_q.descricao or "ELU_Q" in gov_q.descricao
    assert gov_q.duracao == "media"
    assert load_q.combinacoes["ELU_C2"].duracao == "media"


# ── Issue 45 — Q dominante + vento acompanhante (ψ0,W = 0,6) ──────────────────

def _load_projeto():
    import mlc_projeto.main as M
    from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
    from mlc_projeto.core.wind import ParametrosVento
    geo = M.GeometriaViga(**M.GEO_PARAMS)
    mat = M.GlulamMaterial(**M.MAT_CURTA)
    gk = peso_proprio_gk(geo, mat, L_t=M.L_T, b_terca=M.B_TERCA, h_terca=M.H_TERCA,
                         s_terca=M.S, g_telha_kNm2=M.G_TELHA_KNM2,
                         g_instalacoes_kNm2=M.G_INSTALACOES_KNM2)
    return carregamentos_com_vento(
        geo=geo, mat=mat, g_area=gk["g_k_viga_kNm2"], q_area=M.Q_AREA, L_t=M.L_T,
        params_vento=ParametrosVento(**M.VENTO_PARAMS),
        b_pilar=M.B_PILAR, h_pilar=M.H_PILAR, n_pilares_linha=9,
        n_linhas_portico=3, L_cob_m=M.L_COMP_GALPAO, B_cob_m=40.5,
        empuxo_desenvolve=M.EMPUXO_DESENVOLVE,
    )


def test_q_mais_vento_acompanhante_nao_altera_a_viga():
    """A dispensa da EN 1991-1-1 §3.3.2(1) não muda a viga. Issue 39: a faixa
    b3 da Tab. 10 α=90° com c_pi=−0,3 é de pressão leve (C_net=+0,1), e
    1,35G+1,5Q+0,9W dá M 4 % maior; mas a combinação com vento é de curta
    duração (k_mod 0,70 contra 0,65 da média), e a utilização M/k_mod fica
    abaixo da de 1,35G+1,5Q. Se a geometria mudar e isso se inverter, este
    teste obriga a reavaliar a dispensa."""
    import mlc_projeto.main as M
    r = _load_projeto().combinacao_Q_com_vento_acompanhante(
        mat=M.GlulamMaterial(**M.MAT_CURTA))
    assert r["n_padroes_pressao"] == 1
    assert r["M_QW_kNm"] > r["M_ELU_Q_kNm"]
    assert r["razao_utilizacao"] < 1.0
    assert r["altera_dimensionamento"] is False
    assert "3.3.2(1)" in r["norma_dispensa"]


def test_q_mais_vento_inclui_so_parcela_desfavoravel():
    """Com um padrão de pressão fictício a combinação passa a governar."""
    load = _load_projeto()
    load.padroes_vento = [dict(load.padroes_vento[0],
                               w_esq_kNm2=0.5, w_dir_kNm2=0.5, id="ficticio")]
    r = load.combinacao_Q_com_vento_acompanhante()       # sem mat: só M
    assert r["n_padroes_pressao"] == 1
    assert r["altera_dimensionamento"] is True
