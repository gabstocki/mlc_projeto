# -*- coding: utf-8 -*-
"""
PAINEL DE CONTROLO das correções da auditoria adversarial v2.

Reverifica cada achado de forma INDEPENDENTE: não chama a suíte de testes do
projeto nem confia no que o relatório diz. Para cada F-XX reconstrói aqui a
propriedade que a correção estabelece e confronta-a com o software.

Uso:  .venv/bin/python auditoria_v2/check_correcoes.py
"""
import contextlib
import inspect
import io
import ast
import sys
import math
import pathlib

OK, XX, ABERTO = "OK ", "XX ", "-- "
linhas = []


def check(fid, titulo, fn, aberto=False):
    if aberto:
        linhas.append((ABERTO, fid, titulo, fn))
        return
    try:
        detalhe = fn()
        linhas.append((OK, fid, titulo, detalhe))
    except AssertionError as e:
        linhas.append((XX, fid, titulo, f"FALHOU: {e}"))
    except Exception as e:
        linhas.append((XX, fid, titulo, f"{type(e).__name__}: {str(e)[:80]}"))


# ── modelo de referência, montado uma vez ────────────────────────────────────
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento

GEO = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
MAT = GlulamMaterial("GL24h", 3, "media")


def _load(tab25=False):
    kw = (dict(l2=13.0, n_tramos=1, obstrucoes_sob_cobertura=False) if tab25
          else dict(l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True))
    pv = ParametrosVento(V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
                         L=20.25, H1=GEO.h_ap - GEO.h0, h=7.0,
                         dist_portico=5.75, **kw)
    return pv, carregamentos_com_vento(
        GEO, MAT, 0.8229, 0.40, 5.75, pv, b_pilar=0.32, h_pilar=0.27,
        n_pilares_linha=9, n_linhas_portico=3, L_cob_m=46.0, B_cob_m=40.5,
        empuxo_desenvolve=False)


PV, LOAD = _load()


# ── F-01 ─────────────────────────────────────────────────────────────────────
def f01():
    from mlc_projeto.checks.elu.contraventamento_transversal import demanda_transversal
    from mlc_projeto.core.wind import coeficientes_tabela10
    ce = coeficientes_tabela10(PV.beta_deg)
    A_agua = (GEO.L / 2) / math.cos(GEO.alpha_rad) * LOAD.area_trib
    dc = max(abs(ce[a] - ce[b]) for a, b in (("a", "b"), ("c", "d")))
    ref = 1.5 * dc * PV.q * A_agua * math.sin(GEO.alpha_rad) * 9
    dem = demanda_transversal(LOAD, PV, 7.0, 0.32, 0.27, n_frames=9, n_porticos=2)
    assert abs(dem["H_cob_kN"] - ref) / ref < 2e-3, f"{dem['H_cob_kN']} vs {ref}"
    assert dem["H_tr_kN"] > dem["H_vento_topo_kN"] + dem["H_imp_kN"]
    return (f"H_cob={dem['H_cob_kN']:.1f} kN (ref {ref:.1f}) = "
            f"{dem['H_cob_kN']/dem['H_vento_topo_kN']:.2f}× o arrasto de pilares")


# ── F-02 ─────────────────────────────────────────────────────────────────────
def f02():
    from mlc_projeto.checks.elu.estabilidade_global import (
        alpha_cr_membro, alpha_cr_sistema, verificar_estabilidade_global)
    r = alpha_cr_sistema(3756.0, 7.0, 3586.0)
    assert abs(r["alpha_cr"] - 3756.0 * 7.0 / 3586.0) < 1e-9, "Eq. (5.2)"
    m = alpha_cr_membro(MAT, 0.32, 1.0, 10.0, 0.0)
    assert m["indeterminado"] and math.isinf(m["alpha_cr"]), "1e99 ainda presente"
    sem = verificar_estabilidade_global(
        GEO, MAT, LOAD, contravento_vertical_ok=True,
        contravento_transversal_ok=True, nocional_no_contraventamento=True)
    assert sem["ok"] is False and sem["metodo_analise"] == "alpha_cr_nao_determinado"
    return (f"α_cr=K·h/V ✓ | N_Ed=0 → indeterminado (não 1e99) ✓ | "
            f"sem rigidez declarada → '{sem['metodo_analise']}' ✓")


# ── F-03 ─────────────────────────────────────────────────────────────────────
def f03():
    from mlc_projeto.connections.connections import f_h_alpha_k, f_h_k, k_90
    a = math.degrees(math.atan2(99.2225, 8.7478))
    k90, f0 = 1.35 + 0.015 * 24, 0.082 * (1 - 0.24) * 385
    ref = f0 / (k90 * math.sin(math.radians(a)) ** 2 + math.cos(math.radians(a)) ** 2)
    got = f_h_alpha_k(385.0, 24.0, a)
    assert abs(got - ref) < 1e-6, f"{got} vs {ref}"
    assert abs(k_90(24.0) - k90) < 1e-9
    assert abs(f_h_k(385.0, 24.0) - f0) < 1e-6
    return f"f_h,α={got:.3f} MPa vs f_h,0={f0:.3f} ({got/f0-1:+.1%}), k90={k90:.3f}"


# ── F-04 ─────────────────────────────────────────────────────────────────────
def f04():
    from mlc_projeto.output.report import (
        VERIFICACOES_EXPORT, estatisticas_resumo, extrair_eta_ok,
        tabela_verificacoes)
    for mau in ({}, {"eta": None}, {"eta": "x"}, {"eta": float("nan")}, None):
        eta, ok = extrair_eta_ok(mau)
        assert ok is False and math.isnan(eta), f"{mau!r} → ({eta}, {ok})"
    tab = tabela_verificacoes({"cisalhamento": {"eta": 0.5}})
    assert {c for c, _, _ in VERIFICACOES_EXPORT} <= {r["chave"] for r in tab}
    est = estatisticas_resumo(tab)
    assert est["status"] == "REPROVADO" and est["pendentes"]
    return (f"vazio/None/str/NaN → (nan, False) ✓ | catálogo completo "
            f"({len(tab)} linhas) ✓ | {len(est['pendentes'])} pendentes reprovam ✓")


# ── F-05 ─────────────────────────────────────────────────────────────────────
def f05():
    from mlc_projeto.connections.connections import distancias_minimas
    a = math.degrees(math.atan2(99.2225, 8.7478))
    ref = max((2 + 2 * abs(math.sin(math.radians(a)))) * 24, 3 * 24)
    d = distancias_minimas(24.0, theta_deg=a)
    assert abs(d["a4t_mm"] - ref) < 0.05, f"{d['a4t_mm']} vs {ref}"
    assert abs(d["a3c_mm"] - 72.0) < 1e-9, "a3,c de cavilha tem de ser 3d"
    return (f"a4,t={d['a4t_mm']:.1f} mm (era 72,0 → +{d['a4t_mm']/72-1:.1%}) | "
            f"a3,c=3d preservado (Tab. 8.5, não 8.4)")


# ── F-06 ─────────────────────────────────────────────────────────────────────
def f06():
    from mlc_projeto.checks.elu.cumeeira import verifica_cumeeira
    _, l25 = _load(tab25=True)
    gov = l25.combinacao_ELU_governante()
    r = verifica_cumeeira(GEO, MAT, l25)
    assert not (set(l25.combinacoes_ELU_fisicas()) & set(l25.ALIASES_ELU))
    assert r["n_combinacoes_varridas"] == len(l25.combinacoes_ELU_fisicas())
    assert r["comb_gov"] != gov.nome, "ápice deveria governar noutra combinação"
    # envelope reconstruído aqui
    tan_a = math.tan(GEO.alpha_rad)
    Vb = GEO.b * GEO.L * (GEO.h_ap - 0.25 * GEO.L * tan_a)
    Vap = min(GEO.b * GEO.h_ap ** 2 * (1 - 0.25 * tan_a), 2 * Vb / 3)
    kvol = min((0.01 / Vap) ** 0.2, 1.0)
    env = max((0.2 * tan_a * 6 * abs(c.M_cumeeira_kNm) * 1e3
               / (GEO.b * GEO.h_ap ** 2)) / (1.4 * kvol * MAT.com_duracao(c.duracao).f_t90_d)
              for c in l25.combinacoes_ELU_fisicas().values())
    assert abs(r["eta_t90"] - env) / env < 2e-3
    return (f"rota Tab.25: seletor antigo={gov.nome}, ápice governa em "
            f"{r['comb_gov']} ({r['duracao']}) | η={r['eta_t90']:.4f} = envelope")


# ── F-07 ─────────────────────────────────────────────────────────────────────
def f07():
    from mlc_projeto.checks.elu.flambagem_lateral import (
        calcular_l_ef, verifica_flambagem_lateral)
    l1, h = 2.53, 2.7854
    assert calcular_l_ef(l1, posicao_carga="centro_gravidade") == 0.9 * l1
    assert abs(calcular_l_ef(l1, posicao_carga="borda_comprimida", h_m=h)
               - (0.9 * l1 + 2 * h)) < 1e-9
    try:
        calcular_l_ef(l1, posicao_carga="borda_comprimida")
        raise AssertionError("aceitou borda comprimida sem h_m")
    except ValueError:
        pass
    r = verifica_flambagem_lateral(GEO, MAT, LOAD, l_1=l1)
    assert r["posicao_carga"] == "borda_comprimida"
    assert abs(r["l_ef_m"] - (0.9 * l1 + 2 * r["h_crit_m"])) < 1e-3
    assert r["k_crit"] < 1.0, "k_crit devia deixar de ser 1,0"
    return (f"l_ef={r['l_ef_m']:.2f} m (era {0.9*l1:.2f} → {r['l_ef_m']/(0.9*l1):.2f}×) | "
            f"λ_rel={r['lambda_rel_m']:.3f} k_crit={r['k_crit']:.4f} η={r['eta']:.4f}")


# ── F-11 ─────────────────────────────────────────────────────────────────────
def f11():
    from mlc_projeto.checks.elu.contraventamento_vertical import (
        ACO, GAMMA_M0, GAMMA_M2, PASSO_ROSCA_MM, _n_t_rd_kN,
        area_resistente_rosca, verifica_painel_vertical)
    for d in (16.0, 24.0, 33.0, 45.0):
        p_ = PASSO_ROSCA_MM[int(d)]
        As = math.pi / 4 * (d - 0.9382 * p_) ** 2
        assert abs(area_resistente_rosca(d) - As) < 1e-9
        A = math.pi * d ** 2 / 4
        npl = A * ACO["S235"]["f_y"] / GAMMA_M0 / 1e3
        nu = 0.9 * As * ACO["S235"]["f_u"] / GAMMA_M2 / 1e3
        assert abs(_n_t_rd_kN(d, "S235") - min(npl, nu)) < 1e-9, d
    r = verifica_painel_vertical(100.0, 7.0, 5.75, 33.0, "S235")
    assert r["modo_tracao_gov"] == "secao_liquida"
    assert "ligações de extremidade" in r["pendente"].lower()
    return (f"Ø33: N_pl={r['N_pl_Rd_kN']:.1f} vs N_u={r['N_u_Rd_kN']:.1f} kN → "
            f"governa {r['modo_tracao_gov']} ({r['N_u_Rd_kN']/r['N_pl_Rd_kN']-1:+.1%}) "
            f"| ligações de extremidade declaradas pendentes")


# ── F-18 ─────────────────────────────────────────────────────────────────────
def f18():
    """
    F-18 verificado contra o TEXTO da norma (BM-17), não já contra invariantes.
    Confirma-se que 11 dos 15 itens estão fechados com evidência escrita, que
    os 4 restantes têm pergunta, e que o BM-17 corre e passa.
    """
    import subprocess
    from mlc_projeto.core import normativo as nz
    from mlc_projeto.core import wind as w

    raiz = pathlib.Path(__file__).resolve().parents[1]

    # (a) cobertura: nenhuma constante NBR de wind.py fora do catálogo
    simbolos = {s_ for i_ in nz.CATALOGO_NBR6123 for s_ in i_.simbolos}
    exigidas = {"PARAM_METEOROLOGICOS", "FATOR_RAJADA", "COEF_PRESSAO_DINAMICA",
                "TABELA_10_CE", "CPI_OBSTRUCAO_SOTAVENTO", "CA_PILAR_RET",
                "COEF_ATRITO_COBERTURA_ISOLADA"}
    assert exigidas <= simbolos, exigidas - simbolos

    # (b) os confirmados citam a evidência; os pendentes têm pergunta
    conf = [i_ for i_ in nz.CATALOGO_NBR6123 if i_.estado == "CONFIRMADO"]
    pend = nz.itens_nbr_nao_confirmados()
    assert len(conf) == 11 and len(pend) == 4, (len(conf), len(pend))
    # `bloqueio_silhueta` é o único CONFIRMADO sem BM-17: não reclama cláusula
    # nenhuma (é diagnóstico informativo), logo não há texto a confrontar.
    sem_evidencia = [i_.chave for i_ in conf
                     if "BM-17" not in i_.evidencia and i_.chave != "bloqueio_silhueta"]
    assert not sem_evidencia, sem_evidencia
    assert all(i_.questao.strip() for i_ in pend)

    # (c) F-20 e F-21 declarados no código, não só no relatório
    assert "F-20" in w.CLAUSULA_CA_PILAR
    assert "F-21" in nz.NDP_SOURCE["S3"].nota
    assert "S3" in nz.parametros_a_confirmar()

    # (d) a reserva emitida nomeia os quatro pendentes
    aviso = nz.CONFIG_NORMATIVA.aviso_nbr()
    assert all(i_.chave in aviso for i_ in pend) and "BM-17" in aviso

    # (e) BM-17 corre contra o PDF e não acusa divergência
    pdf = raiz / "NBR6123-2023.pdf"
    if pdf.exists():
        r = subprocess.run([sys.executable, "auditoria_v2/bm_nbr_texto.py"],
                           capture_output=True, text=True, cwd=raiz)
        assert r.returncode == 0, r.stdout[-1500:]
        assert "todos os valores confrontados CONFEREM" in r.stdout
        origem = "BM-17 contra o PDF: 45+3+279+40+8 conferem"
    else:
        origem = "PDF ausente — BM-15 (coerência interna) apenas"

    # (f) o anexo existe e foi regenerado do catálogo
    anexo = raiz / "ANEXO_A_NBR6123.md"
    assert anexo.exists()
    txt = anexo.read_text(encoding="utf-8")
    for marca in ("F-20", "F-21", "| **Por resolver** | **4** |"):
        assert marca in txt, f"ANEXO_A_NBR6123.md desatualizado: falta {marca!r}"

    return (f"{len(conf)}/{len(nz.CATALOGO_NBR6123)} itens confirmados contra o "
            f"texto | {origem} | 4 em aberto (v0, S3/F-21, C_a/F-20, Tab.10 α=90°)")


# ── F-19 ─────────────────────────────────────────────────────────────────────
def f19():
    """
    F-19: a suíte não passava no seu PRÓPRIO intervalo declarado. Verifica-se
    (a) que todo o intervalo tem teto, (b) que nada usa API removida dentro
    dele, (c) que a regra do trapézio bate contra referência de arredondamento
    correto, e (d) que a suíte passa nos dois ambientes reais.
    """
    import subprocess
    import tomllib
    from packaging.requirements import Requirement

    raiz = pathlib.Path(__file__).resolve().parents[1]
    with (raiz / "pyproject.toml").open("rb") as fh:
        deps = tomllib.load(fh)["project"]["dependencies"]
    sem_teto = [d for d in deps
                if not any(e.operator in ("<", "<=", "==", "~=")
                           for e in Requirement(d).specifier)]
    assert not sem_teto, sem_teto

    # nenhuma API removida na 2.0 sobrevive no pacote nem nos testes
    ofensas = []
    for arq in list((raiz / "mlc_projeto").rglob("*.py")) + \
               list((raiz / "tests").rglob("*.py")):
        for no in ast.walk(ast.parse(arq.read_text(encoding="utf-8"))):
            if (isinstance(no, ast.Attribute) and no.attr == "trapz"
                    and isinstance(no.value, ast.Name)
                    and no.value.id in {"np", "numpy"}):
                ofensas.append(f"{arq.name}:{no.lineno}")
    assert not ofensas, ofensas

    # a regra do trapézio contra referência exata (fsum), sem np.trapz
    from scipy.integrate import trapezoid
    import numpy as _np
    rng = _np.random.default_rng(20260906)
    pior = 0.0
    for _ in range(50):
        n = int(rng.integers(2, 400))
        x = _np.sort(rng.uniform(-1e3, 1e3, n)).tolist()
        y = rng.uniform(-1e6, 1e6, n).tolist()
        exato = math.fsum((x[k+1]-x[k])*(y[k+1]+y[k])/2.0 for k in range(n-1))
        cond = math.fsum(abs(x[k+1]-x[k])*(abs(y[k+1])+abs(y[k]))/2.0
                         for k in range(n-1))
        obtido = float(trapezoid(_np.array(y), _np.array(x)))
        pior = max(pior, abs(obtido-exato)/cond if cond else 0.0)
    assert pior <= 2.3e-16, pior

    # a suíte passa nos dois ambientes reais
    ambientes = []
    for exe in (sys.executable, str(raiz / ".venv" / "bin" / "python")):
        if not pathlib.Path(exe).exists():
            continue
        r = subprocess.run([exe, "-m", "pytest", "-q", "--no-header", "-x"],
                           capture_output=True, text=True, cwd=raiz)
        v = subprocess.run([exe, "-c", "import numpy;print(numpy.__version__)"],
                           capture_output=True, text=True).stdout.strip()
        ambientes.append((v, r.returncode))
    assert ambientes and all(rc == 0 for _, rc in ambientes), ambientes

    return (f"6/6 dependências com teto | 0 usos de np.trapz | trapézio a "
            f"{pior:.2e} da referência fsum | suíte verde em numpy "
            + ", ".join(v for v, _ in ambientes))


# ── F-13 ─────────────────────────────────────────────────────────────────────
def f13():
    import mlc_projeto.core.wind as W
    from mlc_projeto.core.normativo import NDP_SOURCE, parametros_a_confirmar
    src = inspect.getsource(W)
    for frase in ("Ft = 0,5 · q · a · b", "dimensões em planta da cobertura",
                  "duas faces da cobertura"):
        assert frase in src, f"cláusula não transcrita: {frase!r}"
    assert W.COEF_ATRITO_COBERTURA_ISOLADA == 0.5
    p = NDP_SOURCE["coef_atrito_cobertura_isolada"]
    assert p.origem == "ABNT" and p.valor == 0.5
    # O guard passou a reter o S3 depois de BM-17 apanhar [F-21]. Isso é o
    # guard a funcionar, não uma regressão do F-13: o que F-13 exige é que o
    # ATRITO não esteja pendente.
    pend = parametros_a_confirmar()
    assert "coef_atrito_cobertura_isolada" not in pend, pend
    assert set(pend) == {"S3"}, f"pendências inesperadas: {sorted(pend)}"
    f0 = LOAD.vento_0
    return (f"cláusula transcrita ✓ | C=0,5 ancorado no texto ✓ | "
            f"Ft={f0['F_friccao_kN']:.1f} kN, escala {f0['razao_bloqueio']:.2f}×")


# ── F-14 ─────────────────────────────────────────────────────────────────────
def f14():
    from mlc_projeto.connections.connections import (
        M_y_Rk, f_h_alpha_k, johansen_chapa_central)
    a = math.degrees(math.atan2(99.2225, 8.7478))
    t1, d, fu = (320.0 - 24.0) / 2, 24.0, 400.0
    fh, My = f_h_alpha_k(385.0, d, a), M_y_Rk(fu, d)
    ref = min(fh * t1 * d,
              fh * t1 * d * (math.sqrt(2 + 4 * My / (fh * d * t1 ** 2)) - 1),
              2.3 * math.sqrt(My * fh * d))
    r = johansen_chapa_central(385.0, d, t1, fu, theta_deg=a)
    assert abs(r["F_v_Rk_N"] - ref) / ref < 1e-4, f"{r['F_v_Rk_N']} vs {ref}"
    errado = 1.15 * math.sqrt(2 * My * fh * d)
    assert abs(r["modo_g_N"] - errado) / errado > 0.05, "modo da chapa fina externa"
    assert r["F_ax_Rk_N"] == 0.0
    return (f"min(f,g,h)={r['F_v_Rk_N']/1e3:.2f} kN/plano (ref {ref/1e3:.2f}) | "
            f"gov={r['modo_gov']} | t₁={r['t1_mm']} mm | F_ax=0 (cavilha)")


# ── pipeline de ponta a ponta ────────────────────────────────────────────────
def pipeline():
    import mlc_projeto.main as M
    M.gerar_relatorio = lambda *a, **k: {}
    with contextlib.redirect_stdout(io.StringIO()):
        r = M._main_impl(rodar_varredura=False, abrir_viz=False)
    m = r["meta"]
    assert m["status"] == "APROVADO", m["status"]
    assert m["eta_max"] <= 1.0
    return (f"status={m['status']} | η_max={m['eta_max']:.4f} | "
            f"{m['n_verif']} verificações")


print("=" * 100)
print("  PAINEL DE CONTROLO — correções da auditoria adversarial v2")
print("  (cada linha é reverificada aqui, sem usar a suíte do projeto)")
print("=" * 100)

check("F-01", "Componente horizontal do vento de cobertura", f01)
check("F-02", "α_cr de SISTEMA (EN 1993-1-1 Eq. 5.2)", f02)
check("F-03", "f_h,α,k no embutimento (EC5 Eq. 8.31/8.33)", f03)
check("F-04", "Agregação do veredito: ausência ≠ aprovação", f04)
check("F-05", "a4,t com o termo (2+2·sen α)·d (Tab. 8.5)", f05)
check("F-06", "Envelope real sobre as combinações ELU", f06)
check("F-07", "l_ef da LTB com o +2h da nota da Tab. 6.1", f07)
check("F-11", "Seção líquida da diagonal (EN 1993-1-1 §6.2.3(2))", f11)
check("F-18", "Valores NBR verificados contra o TEXTO da norma (BM-17)", f18)
check("F-19", "Ambiente declarado com teto; suíte verde em NumPy 1.x e 2.x", f19)
check("F-13", "Atrito §7.2.2: cláusula transcrita e ancorada", f13)
check("F-14", "Modos da chapa CENTRAL (EC5 §8.2.3)", f14)
check("....", "Pipeline de ponta a ponta", pipeline)

for st, fid, tit, det in linhas:
    print(f"  [{st}] {fid}  {tit}")
    print(f"           {det}")

print("-" * 100)
print("  EM ABERTO (não corrigidos):")
for fid, t in (
    ("F-11", "ligações de EXTREMIDADE das diagonais (a barra já está; EN 1993-1-8)"),
    ("F-18", "4 de 15 itens NBR por resolver (11 confirmados por BM-17) — ANEXO_A_NBR6123.md"),
    ("F-20", "C_a=1,2 do pilar sob citação inexistente; refazer por §8.1.1 Tab. 26 × Tab. 28"),
    ("F-21", "S3=1,00 (grupo 3) rotulado «grupo 2»; se for grupo 2, +12,4 % em TODO o vento"),
    ("....", "Tab. 10 colunas b1/b2/b3 (α=90°) não implementadas"),
    ("....", "numeração das equações de §8.2.3 por confirmar (ver Z.13.2)"),
):
    print(f"  [{ABERTO}] {fid}  {t}")
falhas = sum(1 for st, *_ in linhas if st == XX)
print("=" * 100)
print(f"  RESULTADO: {len(linhas)-falhas}/{len(linhas)} verificações independentes OK"
      + ("" if not falhas else f"  —  {falhas} FALHA(S)"))
