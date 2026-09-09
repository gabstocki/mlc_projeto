"""
Resíduo do [F-06] — os módulos que ainda liam a combinação por procuração.

O F-06 foi fechado nas verificações da viga (mísula, ápice, flexão, LTB, apoio,
pilares), mas sobreviveu onde ninguém foi olhar: contraventamento, estabilidade
global, fadiga e terças continuavam a ler `combinacao_ELU_governante()` — o
seletor de max|M|, que é gravítico — ou, no caso das terças, uma combinação
escrita à mão em código.

O que estes testes fixam é a PROPRIEDADE, não o número: cada verificação tem de
maximizar a SUA medida de demanda. Um envelope correto nunca devolve menos que
qualquer combinação isolada — é o critério do EN 1990 §6.4.3.2.
"""

import pytest

from mlc_projeto.core.geometry   import GeometriaViga
from mlc_projeto.core.materials  import GlulamMaterial
from mlc_projeto.core.wind       import ParametrosVento
from mlc_projeto.core.loads      import carregamentos_com_vento


def _modelo():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32, n_pts=1001)
    mat = GlulamMaterial("GL24h", 3, "curta")
    vento = ParametrosVento(
        V0=45.0, S1=1.0, S3=1.0, categoria="IV", classe="B",
        L=geo.L, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=0.80, q_area=0.40, L_t=5.75,
        params_vento=vento, empuxo_desenvolve=False,
    )
    return geo, mat, load


# ── Contraventamento de cobertura (EC5 §9.2.5) ───────────────────────────────

def test_N_d_do_contraventamento_e_o_envelope_da_propria_medida():
    """
    `N_d = |N| + (1−k_crit)·M/h` não é monótono em |M|: `h` é a altura NA SEÇÃO
    de M_max e varia com a combinação. O envelope tem de ser feito sobre N_d.
    """
    from mlc_projeto.checks.elu.contraventamento import forca_compressao_estabilizar

    geo, _, load = _modelo()
    k_crit = 0.9
    res = forca_compressao_estabilizar(load, geo, k_crit=k_crit)

    def _N_d(c):
        h = float(geo.h(c.x_Mmax_m)) or float(geo.h_ap)
        return abs(float(c.N_viga_kN)) + (1 - k_crit) * abs(float(c.M_max_kNm)) / h

    pior = max(_N_d(c) for c in load.combinacoes_ELU_fisicas().values())
    assert res["N_d_kN"] == pytest.approx(pior, abs=1e-3)
    # e nunca é menor do que qualquer combinação isolada
    for c in load.combinacoes_ELU_fisicas().values():
        assert res["N_d_kN"] >= _N_d(c) - 1e-9


# ── Forças nocionais (EN 1993-1-1 §5.3.2) ────────────────────────────────────

@pytest.mark.parametrize("modulo, funcao", [
    ("mlc_projeto.checks.elu.contraventamento_vertical",
     "verificar_contraventamento_vertical"),
])
def test_nocional_usa_a_carga_vertical_maxima(modulo, funcao):
    """
    A nocional é φ·V_Ed,vertical: o que se maximiza é a CARGA VERTICAL. Lia-se
    da combinação de max|M|, que é uma procuração — coincide muitas vezes, mas
    coincidir não é verificar.
    """
    import importlib
    geo, mat, load = _modelo()
    mod = importlib.import_module(modulo)
    res = getattr(mod, funcao)(
        geo=geo, load=load, H_pilar_m=7.0, b_baia_long_m=5.75,
        L_comp=46.0, dist_portico=5.75, n_porticos=2,
    )
    R_v_max = max(abs(float(c.V_max_kN))
                  for c in load.combinacoes_ELU_fisicas().values())
    # A carga vertical total publicada tem de sair do R_v do ENVELOPE.
    n_frames = max(2, round(46.0 / 5.75) + 1)
    esperado = 2.0 * 2 * R_v_max * n_frames
    assert res["V_vert_total_kN"] == pytest.approx(esperado, abs=0.1)


# ── Estabilidade global: três medidas, três envelopes ────────────────────────

def test_estabilidade_separa_os_envelopes_das_tres_medidas():
    """
    `V_portal` (nocional), a RAZÃO H_imp/H_Ed e `N_viga` (α_cr) têm envelopes
    diferentes. A razão é entre grandezas da MESMA combinação — misturar
    estados seria o vício que o envelope existe para evitar.
    """
    from mlc_projeto.checks.elu.estabilidade_global import (
        verificar_estabilidade_global,
    )
    geo, mat, load = _modelo()
    res = verificar_estabilidade_global(
        geo, mat, load, H_pilar_m=7.0, b_pilar=0.22, h_pilar=0.26,
        contravento_vertical_ok=True, contravento_transversal_ok=True,
        K_lat_long_kNpm=59417.0, K_lat_transv_kNpm=8450.0,
        V_Ed_total_kN=3586.0,
    )
    combs = load.combinacoes_ELU_fisicas().values()
    # o empuxo publicado é o MÁXIMO...
    assert res["H_Ed_kN"] == pytest.approx(
        max(abs(float(c.H_kN)) for c in combs), rel=1e-6)
    # ...e o da combinação que governa a razão é outro, e menor
    assert res["H_Ed_da_razao_kN"] <= res["H_Ed_kN"] + 1e-9
    assert res["comb_H_imp_over_H"] in load.combinacoes_ELU_fisicas()


# ── Fadiga/deslizamento: a resultante, não o momento ─────────────────────────

def test_fadiga_maximiza_a_resultante_na_base():
    """√(N²+V²) não é maximizado pela combinação de maior |M|."""
    from mlc_projeto.connections.connections import dimensionar_ligacoes
    from mlc_projeto.connections.fadiga_ligacoes import verificar_fadiga_deslizamento

    geo, mat, load = _modelo()
    res_lig = dimensionar_ligacoes(mat, load, geo, d_base_mm=24,
                                   com_tirante=False, eta_alvo=0.75)
    res = verificar_fadiga_deslizamento(mat=mat, load=load, geo=geo,
                                        res_lig=res_lig)
    pior = max((c.N_viga_kN ** 2 + c.V_viga_kN ** 2) ** 0.5
               for c in load.combinacoes_ELU_fisicas().values())
    assert res["L1"]["F_ELU_kN"] == pytest.approx(pior, abs=1e-3)


# ── Terças: combinações declaradas, não escritas à mão ───────────────────────

def test_terca_faz_envelope_com_os_psi_declarados():
    """
    A terça escrevia `1,35G + 1,5W + 1,05Q`. O termo 1,05Q é 1,5·ψ0,Q·Q com
    ψ0,Q = 0,70 — de outra categoria de uso. Em categoria H, ψ0,Q = 0 e Q não
    é concomitante com o vento; era o único sítio do projeto a contradizê-lo.
    """
    from mlc_projeto.checks.elu.tercas import verifica_terca
    from mlc_projeto.core.normativo import NDP_SOURCE

    mat = GlulamMaterial("GL24h", 3, "curta")
    r = verifica_terca(
        mat=mat, L_t=5.75, s=2.53, b=0.20, h=0.58, alpha_deg=10.0,
        g_k_m2=0.389, q_k_m2=0.40, w_kNm2=0.7158,
    )
    assert r["psi_0_Q"] == float(NDP_SOURCE["psi_0_Q"].valor) == 0.0
    assert r["psi_0_W"] == float(NDP_SOURCE["psi_0_W"].valor)
    # duas combinações, cada uma com a sua duração; governa a de maior η
    assert len(r["etas_por_combinacao"]) == 2
    assert r["comb_gov"] in r["etas_por_combinacao"]
    assert r["etas_por_combinacao"][r["comb_gov"]] == max(
        r["etas_por_combinacao"].values())
    assert r["duracao_gov"] in ("curta", "media")
    assert r["k_mod_gov"] == GlulamMaterial(
        "GL24h", 3, r["duracao_gov"]).k_mod


def test_terca_nao_publica_mais_a_combinacao_inexistente():
    """`ELU_C2` é um ALIAS, não uma fórmula: não pode ser publicado como uma."""
    from mlc_projeto.checks.elu.tercas import (
        verifica_terca, verifica_terca_flexocompressao,
    )
    mat = GlulamMaterial("GL24h", 3, "curta")
    kw = dict(L_t=5.75, s=2.53, b=0.20, h=0.58, alpha_deg=10.0,
              g_k_m2=0.389, q_k_m2=0.40, w_kNm2=0.7158)
    r = verifica_terca(mat=mat, **kw)
    rc = verifica_terca_flexocompressao(mat=mat, N_c_kN=47.36, **kw)
    for rotulo in (r["comb_gov"], rc["comb"]):
        assert "ELU_C2" not in rotulo
        assert "1,05Q" not in rotulo


def test_nenhum_modulo_de_producao_le_o_seletor_por_procuracao():
    """
    Guarda de regressão. `combinacao_ELU_governante()` continua a existir (é o
    alias legado do relatório), mas nenhum módulo de VERIFICAÇÃO o pode usar
    para escolher a combinação de cálculo — é um seletor de max|M|, não um
    envelope. As ocorrências que sobram estão em blocos `__main__` de
    demonstração, que não fazem parte do pipeline.
    """
    import ast
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parent.parent / "mlc_projeto"
    infratores = []
    for py in sorted(raiz.rglob("*.py")):
        rel = py.relative_to(raiz).as_posix()
        if not (rel.startswith("checks/") or rel.startswith("connections/")):
            # core/loads.py DEFINE o seletor; main.py e output/report.py usam-no
            # para IDENTIFICAR a governante no cabeçalho do memorial (rótulo),
            # não para escolher a combinação de nenhum cálculo.
            continue
        arvore = ast.parse(py.read_text(encoding="utf-8"))
        # Os blocos `if __name__ == "__main__":` são demonstrações e não fazem
        # parte do pipeline — retiram-se antes de procurar.
        arvore.body = [
            n for n in arvore.body
            if not (isinstance(n, ast.If) and "__name__" in ast.dump(n.test))
        ]
        # Procura-se a CHAMADA, não o texto: um docstring que explique porque o
        # seletor deixou de ser usado não pode reprovar o próprio módulo.
        chamadas = [
            n for n in ast.walk(arvore)
            if isinstance(n, ast.Attribute)
            and n.attr == "combinacao_ELU_governante"
        ]
        if chamadas:
            infratores.append(rel)

    assert infratores == [], (
        f"verificações que ainda usam o seletor por procuração: {infratores}")
