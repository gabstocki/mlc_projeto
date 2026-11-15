"""
Issue 91 — desenhos faltantes: topo dos pilares (DES-11), terminais das diagonais
(DES-12), juntas das terças — emenda da corda e montante (DES-13) — e pilarete
(DES-14); soldas, aço e proteção em cada folha; bases com plano da chapa vertical,
choque e cotas de nível.

O desenho expôs três lacunas de cálculo, corrigidas aqui:
  · as terças são biapoiadas, então a corda do diafragma tem uma junta sobre
    cada viga intermediária (7 por linha), e não 3 emendas de barra comercial;
  · a chapa do montante e a da emenda ficam num rasgo superior que não pode
    descer até o cruzamento dos parafusos a 45° da junta corrente;
  · o terminal da diagonal da cobertura (CV-H) não estava dimensionado.
"""
import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.connections.terca_viga import junta_rasgo_superior, rasgo_superior
from mlc_projeto.output import desenhos as D

CORRENTE = {"a2_CG_terca_adotado_mm": 32.0, "l_ef_mm": 160.0, "passo_vertical_mm": 56.0,
            "n_por_face": 4, "d_mm": 8.0}


@pytest.fixture(scope="module")
def res():
    orig = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = orig


# ── Rasgo superior acima dos parafusos a 45° ────────────────────────────────

def test_rasgo_superior_contra_a_geometria_dos_parafusos():
    """z_sup = 32 + 160·cos45 + 3·56 − 200/2 + 8/2 = 217,1 mm (à mão)."""
    r = rasgo_superior(CORRENTE, b_terca_mm=200.0, h_terca_mm=400.0)
    assert r["z_cruzamento_sup_mm"] == pytest.approx(32 + 160 * 0.70711 + 168 - 100 + 4, abs=0.1)
    assert r["profundidade_max_mm"] == pytest.approx(400 - 217.1 - 10, abs=0.1)
    # a4,c = 60 acima, e2 = ceil(1,2·21) = 26 abaixo, 5 de fundo → D⊥ ≤ 81,9 → 2 fileiras
    assert r["D_perp_max_mm"] == pytest.approx(172.9 - 60 - 26 - 5, abs=0.1)
    assert r["n_vert_max"] == 2


def test_chapa_no_rasgo_cabe_ou_acusa():
    rg = rasgo_superior(CORRENTE, b_terca_mm=200.0, h_terca_mm=400.0)
    ok = junta_rasgo_superior(dict(n_vert=2, a2_mm=70.0, a3t_mm=140.0, n_horiz=4, a1_mm=100.0,
                                   d_mm=20.0), rg)
    assert ok["cabe"] and ok["h_chapa_mm"] == 60 + 70 + 26
    assert ok["L_chapa_mm"] == pytest.approx(2 * (140 + 300 + 40))
    nao = junta_rasgo_superior(dict(n_vert=3, a2_mm=60.0, a3t_mm=140.0, n_horiz=1, a1_mm=100.0,
                                    d_mm=20.0), rg)
    assert not nao["cabe"]


# ── Pipeline ────────────────────────────────────────────────────────────────

def test_corda_tem_uma_junta_sobre_cada_viga_intermediaria(res):
    n_eixos = round(M.L_COMP_GALPAO / M.L_T) + 1
    assert res["corda_beiral"]["n_emendas"] == n_eixos - 2 == 7


def test_emenda_e_montante_dimensionados_no_rasgo_superior(res):
    tv = res["ligacao_terca_viga"]
    em, mo, rg = tv["emenda_corda"], tv["montante"], tv["rasgo_superior"]
    assert em["F_Ed_kN"] == pytest.approx(res["contraventamento_transversal"]["N_corda_kN"], abs=0.01)
    for lig in (em, mo):
        assert lig["ok"] and lig["eta"] <= 0.75
        assert lig["n_vert"] <= rg["n_vert_max"]
        assert lig["chapa"]["profundidade_rasgo_mm"] <= rg["profundidade_max_mm"]
    assert tv["ok"]


def test_terminal_da_diagonal_da_cobertura(res):
    ld = res["lig_diag_cobertura"]
    cv = res["contraventamento"]
    assert ld["ok"] and ld["criterio"] == "capacidade"
    assert ld["N_dimensionamento_kN"] == pytest.approx(cv["N_t_Rd_kN"], abs=0.01)
    assert any("CV-H" in x["peca"] for x in res["soldas"]["itens"])
    from mlc_projeto.output.report import VERIFICACOES_EXPORT
    assert "lig_diag_cobertura" in {c for c, _, _ in VERIFICACOES_EXPORT}


# ── Desenhos ────────────────────────────────────────────────────────────────

def test_folhas_novas_registradas():
    nomes = [n for n, _ in D.FOLHAS]
    # padrão gráfico revisto: notas gerais numa folha; topo dos pilares nas DES-05/05B,
    # pilarete na DES-06; terminais e juntas renumerados
    assert {"des00_notas_gerais.pdf", "des07b_pilar_bipartido.pdf", "des09b_juntas_tercas.pdf",
            "des11_terminais.pdf"} <= set(nomes)
    assert "des11_topo_pilares.pdf" not in nomes and "des14_pilarete.pdf" not in nomes


def test_texto_da_solda_vem_do_calculo():
    d = {"soldas": [("L1: chapa embutida × chapa de topo", 4.0, 270.0, 2),
                    ("sela: enrijecedores × chapa", 4.0, None, None)]}
    assert D._solda_txt(d, "L1: chapa embutida") == "a4–270 (2 lados)"
    assert D._solda_txt(d, "sela") == "a4"
    assert D._solda_txt(d, "inexistente") is None


def test_nota_longa_demais_nao_e_cortada_em_silencio():
    f = D.Folha(60.0, 10, 0.0, 0.0, unidade="mm")
    with pytest.raises(ValueError):
        f.carimbo("DES-XX", "TESTE", "palavra " * 200)
    import matplotlib.pyplot as plt
    plt.close(f.fig)


def test_textos_das_folhas_geradas():
    import subprocess
    from pathlib import Path
    fig = Path(D.__file__).parents[2] / "tese" / "fig"
    for nome, chaves in (("des05_ligacao_L1.pdf", ("a4–270", "LISTA DE PEÇAS", "TR-01")),
                         ("des06_bases_correntes.pdf", ("piso acabado", "plano do pórtico",
                                                        "choque", "graute", "janela")),
                         ("des00_notas_gerais.pdf", ("MATERIAIS", "PROTEÇÃO", "SOLDAS",
                                                     "intumescente")),
                         ("des11_terminais.pdf", ("CV-H", "rosca recalcada", "forquilha")),
                         ("des09b_juntas_tercas.pdf", ("EMENDA DA CORDA", "MONTANTE")),
                         ("des07b_pilar_bipartido.pdf", ("contato", "CP-01"))):
        txt = subprocess.run(["pdftotext", str(fig / nome), "-"], capture_output=True,
                             text=True).stdout
        for c in chaves:
            assert c in txt, (nome, c)
