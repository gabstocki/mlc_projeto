"""Testes — guarda de diâmetro de cavilha EC5 §8.6(2) (issue 18)."""
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.connections.connections import (
    _validar_diametro_cavilha,
    dimensionar_ligacao_base,
    D_CAVILHA_MIN_MM,
    D_CAVILHA_MAX_MM,
)


def _load():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    pp = peso_proprio_gk(geo, GlulamMaterial("GL24h", 3, "longa"),
                         5.75, 0.20, 0.58, 2.53, 0.10, 0.10)
    load = carregamentos_com_vento(
        geo, mat, pp["g_k_viga_kNm2"], 0.25, 5.75, pv,
        n_pilares_linha=9, n_linhas_portico=3, L_cob_m=46.0, B_cob_m=2 * geo.L)
    return geo, mat, load


def test_faixa_ec5_8_6():
    assert (D_CAVILHA_MIN_MM, D_CAVILHA_MAX_MM) == (6.0, 30.0)


@pytest.mark.parametrize("d", [6, 12, 16, 20, 24, 27, 30])
def test_diametros_dentro_do_escopo_aceitos(d):
    _validar_diametro_cavilha(d)   # não deve lançar


@pytest.mark.parametrize("d", [4, 5.9, 30.1, 33, 36, 40])
def test_diametros_fora_do_escopo_rejeitados(d):
    with pytest.raises(ValueError):
        _validar_diametro_cavilha(d)


def test_ligacao_base_rejeita_36mm():
    """A L1 com Ø36 (fora do escopo) é rejeitada pela guarda."""
    geo, mat, load = _load()
    with pytest.raises(ValueError):
        dimensionar_ligacao_base(mat, load, geo, d_mm=36.0)


def test_ligacao_base_24mm_ok_e_flag():
    """Ø24 mm: dimensiona, dentro do escopo, com η ≤ alvo e geometria OK."""
    geo, mat, load = _load()
    r = dimensionar_ligacao_base(mat, load, geo, d_mm=24.0, eta_alvo=0.75)
    assert r["d_norma_ok"] is True
    assert r["ok_geometria"] is True
    assert r["eta"] <= 0.75 + 1e-9
    assert r["n_pinos"] > 0
