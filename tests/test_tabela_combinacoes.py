"""Issue 28 — Tabela completa das combinações + Cpe dos 8 padrões (Tab.25).

Publica-se todas as combinações ELU (não só o envelope), com C_esq/C_dir de
cada padrão e as governantes marcadas.
"""

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento


def _load():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
                         # cobertura real: 2 tramos + veículos sob a cobertura (Onda 2)
                         l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True)
    return carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)


def test_29_combinacoes():
    """14 padrões × (ELU_W + ELU_S) + ELU_Q = 29: os 8 da Tab. 10 com α = 0°
    e os 6 com α = 90° (faixas b1/b2/b3 × 2 c_pi — issue 39)."""
    t = _load().tabela_combinacoes()
    assert len(t) == 29
    grupos = [r["grupo"] for r in t]
    assert grupos.count("W") == 14
    assert grupos.count("S") == 14
    assert grupos.count("Q") == 1


def test_cpe_por_padrao():
    """Cada linha de vento traz C_esq/C_dir (Cpe da meia-água); ELU_Q não."""
    t = _load().tabela_combinacoes()
    for r in t:
        if r["grupo"] in ("W", "S"):
            assert r["C_esq"] is not None and r["C_dir"] is not None
            # Onda 2: pela rota do §7.2.1 o caso é um tramo da Tabela 10,
            # não mais os carregamentos C1/C2 da Tabela 25.
            assert r["caso"].startswith(("Tab.10 tramo", "Tab.10 α=90°"))
        else:
            assert r["C_esq"] is None


def test_governantes_marcadas():
    """Há linha(s) marcada(s) como governante(s): |M| e uplift.

    Revisto na Onda 2: com o vento só em sucção, |M| e |H| passam a ser
    governados pela mesma combinação gravítica, e o marcador |H| deixa de
    aparecer isolado. O envelope continua completo — o que importa é haver
    governante de momento e de uplift identificados.
    """
    t = _load().tabela_combinacoes()
    govs = " ".join(r["governa"] for r in t)
    assert "|M|" in govs
    assert "uplift" in govs


def test_governante_M_bate_com_analise():
    """A combinação marcada |M| tem o maior |M_max| (= combinacao_ELU_governante)."""
    load = _load()
    t = load.tabela_combinacoes()
    linha_M = [r for r in t if "|M|" in r["governa"]][0]
    m_max_tab = max(abs(r["M_max_kNm"]) for r in t)
    assert abs(linha_M["M_max_kNm"]) == pytest.approx(m_max_tab, rel=1e-6)


def test_asimetrico_esq_dir_diferentes():
    """Padrões assimétricos têm C_esq ≠ C_dir; uniformes têm iguais."""
    t = _load().tabela_combinacoes()
    asim = [r for r in t if "asim" in r["padrao"]]
    unif = [r for r in t if "unif" in r["padrao"]]
    assert all(r["C_esq"] != r["C_dir"] for r in asim)
    assert all(r["C_esq"] == r["C_dir"] for r in unif)


def test_duracoes():
    """Vento → curta; ELU_Q → média."""
    t = _load().tabela_combinacoes()
    for r in t:
        if r["grupo"] in ("W", "S"):
            assert r["duracao"] == "curta"
        else:
            assert r["duracao"] == "media"
