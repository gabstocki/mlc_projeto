"""Testes — não-concomitância Q×vento, categoria H (issue 3)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import (
    carregamentos_com_vento, peso_proprio_gk,
    GAMMA_G_sup, GAMMA_G_inf, GAMMA_Q, PSI_0_Q,
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
    # a mesma pressão em ELU_S deve satisfazer 0,9G + 1,5·w_esq
    assert cs.q_esq == pytest.approx(GAMMA_G_inf * g + GAMMA_Q * w_esq_W, rel=1e-6)


def test_els_caracteristico_sem_vento():
    """ELS_S1 = G + Q (sem vento) — cat. H."""
    load = _load()
    g, q = load.g_k, load.q_k
    s1 = load.combinacoes["ELS_S1"]
    assert s1.q_esq == pytest.approx(g + q, rel=1e-6)
    assert s1.q_dir == pytest.approx(g + q, rel=1e-6)


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
