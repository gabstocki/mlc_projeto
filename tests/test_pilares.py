"""Testes — pilares (issue 13): N por combinação, governante e k_mod."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.pilares import verifica_pilar_governante


def _load_R2():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo, mat, 1.5, 0.25, 5.75, pv,
        n_pilares_linha=9, n_linhas_portico=3, L_cob_m=46.0, B_cob_m=2 * geo.L,
    )
    return geo, mat, load


def test_governante_e_o_maior_eta_entre_combinacoes():
    """A combinação reportada é a de maior η entre TODAS as ELU."""
    _, mat, load = _load_R2()
    res = verifica_pilar_governante(mat, load, b=0.32, h=0.27, H=7.0, fator_reacao=2.0)
    etas = [d["eta"] for d in res["combinacoes"]]
    assert res["eta"] == pytest.approx(max(etas), rel=1e-9)
    # a governante consta na lista de combinações
    assert any(d["comb"] == res["comb_gov"] for d in res["combinacoes"])


def test_N_definido_como_fator_vezes_Rv():
    """N_d = fator_reacao · R_v da combinação governante (reação vertical ELU)."""
    _, mat, load = _load_R2()
    res = verifica_pilar_governante(mat, load, b=0.32, h=0.27, H=7.0, fator_reacao=2.0)
    gov = next(d for d in res["combinacoes"] if d["comb"] == res["comb_gov"])
    assert res["N_d_kN"] == pytest.approx(2.0 * gov["R_v_kN"], abs=1e-2)
    assert res["fator_reacao"] == 2.0


def test_central_maior_que_lateral():
    """Central (fator=2) tem η maior que lateral (fator=1) na mesma seção."""
    _, mat, load = _load_R2()
    lat = verifica_pilar_governante(mat, load, b=0.32, h=0.27, H=7.0, fator_reacao=1.0)
    cen = verifica_pilar_governante(mat, load, b=0.32, h=0.27, H=7.0, fator_reacao=2.0)
    assert cen["eta"] > lat["eta"]


def test_governante_nao_e_necessariamente_o_maior_N():
    """
    Efeito do k_mod (EC5 §3.1.3): a combinação governante pode ter N menor que a
    de maior N, porque f_c,0,d depende do k_mod de cada combinação.
    Aqui a governante (Q dom., longa, k_mod menor) tem N < N da de wind dom.
    """
    _, mat, load = _load_R2()
    res = verifica_pilar_governante(mat, load, b=0.32, h=0.27, H=7.0, fator_reacao=2.0)
    N_max = max(d["N_d_kN"] for d in res["combinacoes"])
    gov = next(d for d in res["combinacoes"] if d["comb"] == res["comb_gov"])
    # a governante existe e tem o maior η, mesmo com N < N_max
    assert gov["eta"] == pytest.approx(res["eta"], rel=1e-9)
    assert gov["N_d_kN"] <= N_max + 1e-9


def test_N_pilar_nao_e_N_do_eixo_da_viga():
    """
    O N do pilar (reação vertical, ~200-420 kN) NÃO é o N do eixo da viga
    (N_max_ELU ~1,6 MN, que inclui o empuxo H).
    """
    _, mat, load = _load_R2()
    res = verifica_pilar_governante(mat, load, b=0.32, h=0.27, H=7.0, fator_reacao=2.0)
    assert res["N_d_kN"] < 0.5 * load.N_max_ELU()   # muito menor que o N da viga
    assert load.N_max_ELU() > 1000.0                # eixo da viga em ordem de MN


def test_fator_invalido():
    _, mat, load = _load_R2()
    with pytest.raises(ValueError):
        verifica_pilar_governante(mat, load, b=0.32, h=0.27, H=7.0, fator_reacao=0.0)
