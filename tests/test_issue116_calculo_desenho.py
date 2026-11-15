"""Issue 116 — cada dimensão de cálculo é a mesma da cota e da lista de peças."""

import contextlib
import io
import re

import pytest

import mlc_projeto.main as M
from mlc_projeto.checks.elu.pilar_bipartido import FOLGA_ESCORA_VIGA_MM
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.output import desenhos as D


@pytest.fixture(scope="module")
def r():
    backup = M.gerar_relatorio
    try:
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            res = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = backup
    geo = GeometriaViga(**M.GEO_PARAMS)
    arr = D.arranjo_de_resultados(res, geo, **M.arranjo_kwargs(res))
    return res, arr


def _peca(pecas, marca):
    return next(p for p in pecas if p[0] == marca)



def test_chapa_de_topo_da_L1_e_o_apoio_do_calculo(r):
    res, arr = r
    nome, a, b, t = D.chapa_topo_L1(arr)
    assert a == pytest.approx(res["apoio"]["l_apoio_m"] * 1000)          # 270 = l do contato
    assert b == pytest.approx(M.B_PILAR * 1000)                          # seção inteira
    assert t == pytest.approx(M.T_CHAPA_TOPO_MM)
    ch = _peca(D._pecas_topo(arr.det, arr, "base_L3", D.chapa_topo_L1(arr)), "CH-01")
    assert ch[1].endswith(f"{a:.0f}×{b:.0f}×{t:g}")


def test_sela_e_o_apoio_central_do_calculo(r):
    res, arr = r
    assert arr.det["l_sela_viga_mm"] == pytest.approx(res["apoio_central"]["l_apoio_m"] * 1000)


def test_chapa_embutida_pinos_e_rasgo(r):
    res, arr = r
    esq, d = res["esquadro_chapas"]["L1"], arr.det
    assert (d["L1_chapa_L_mm"], d["L1_chapa_H_mm"], d["t_chapa_L1_mm"]) == (
        esq["largura_mm"], esq["altura_mm"], esq["t_adotada_mm"])
    assert d["n_pinos_L1"] == res["L1"]["n_pinos"] and d["d_pino_L1_mm"] == res["L1"]["d_mm"]
    assert d["x_pinos_L1_mm"] == esq["x_pinos_mm"]
    assert d["y_pino_alto_mm"] == res["oblongo_L1"]["y_topo_mm"]
    assert d["fundo_rasgo_mm"] == res["oblongo_L1"]["fundo_rasgo_mm"]
    # largura do rasgo: a mesma que reduz a faixa de contato e o cisalhamento
    assert d["t_rasgo_mm"] == pytest.approx(res["apoio"]["t_rasgo_m"] * 1000)
    assert d["t_rasgo_mm"] == pytest.approx(res["cisalhamento"]["t_rasgo_m"] * 1000)
    assert d["L1_rasgo_L_mm"] == esq["largura_mm"] + 60.0              # 30 além de cada face
    assert d["L1c_rasgo_L_mm"] == res["esquadro_chapas"]["L1c"]["largura_mm"] + 30.0
    assert d["folga_oblongo_mm"] == (res["oblongo_L1"]["c_cima_mm"], res["oblongo_L1"]["c_baixo_mm"])


def test_tirante_da_lista_e_o_do_calculo(r):
    res, arr = r
    for k in ("base_L3", "base_L3c"):
        v = res["tirante_interno"]["variantes"][k]
        tr = _peca(D._pecas_topo(arr.det, arr, k, ("x", 1, 1, 1)), "TR-01")
        assert f"M{v['d_mm']}×{v['L_corte_mm']:.0f}" in tr[1]
        # o comprimento elástico do deslocamento sob sucção é o livre do tirante
        assert v["L_livre_mm"] == pytest.approx(M.H_PILAR_MAD * 1000
                                                + res[k]["pilarete"]["chapa_topo_mm"][2])
        assert v["L_livre_mm"] < v["L_corte_mm"] < M.H_PILAR_ALT * 1000


def test_folgas_e_cursos_verificados_sao_os_desenhados(r):
    res, arr = r
    ds = res["deslocamento_succao"]
    assert arr.det["bipartido"]["folga_escora_mm"] == ds["escora"]["folga_mm"] == FOLGA_ESCORA_VIGA_MM
    assert arr.det["L1f"]["curso_mm"] == ds["pf"]["curso_mm"]
    assert arr.det["junta_condutor_mm"] == ds["condutor"]["junta_deslizante_mm"]


def test_bases_desenhadas_sao_as_calculadas(r):
    res, arr = r
    for kd, kr in (("L3", "base_L3"), ("L3c", "base_L3c"), ("L3f", "base_L3f"),
                   ("L3a", "base_L3a_canto")):
        b = arr.det["bases"][kd]
        assert (b["B_mm"], b["L_mm"], b["t_mm"]) == (res[kr]["B_mm"], res[kr]["L_mm"],
                                                      res[kr]["t_adotada_mm"])
