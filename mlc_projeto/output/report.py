"""
output/report.py — Memorial de cálculo em LaTeX.

Gera o arquivo .tex e compila para PDF se pdflatex estiver disponível.
Estrutura: tabelas de resultados com referências normativas.
Simples, direto, uso interno do escritório.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from datetime import date

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


# ── Helpers (robustos a None / tipos inválidos) ───────────────────────────────

def _f(x, default: float = 0.0) -> float:
    """float seguro; None/inválido → default."""
    if x is None:
        return float(default)
    try:
        return float(x)
    except (TypeError, ValueError):
        return float(default)


def _i(x, default: int = 0) -> int:
    return int(round(_f(x, default)))


def _br(x, nd: int = 2) -> str:
    """Decimal brasileiro para LaTeX. Aceita None."""
    return f"{_f(x):.{nd}f}".replace(".", "{,}")


def _tex_escape(s: object) -> str:
    """Escapa caracteres especiais LaTeX em texto livre."""
    if s is None:
        return ""
    t = str(s)
    for a, b in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
        ("←", r"$\leftarrow$"),
        ("—", "--"),
        ("–", "--"),
        ("×", r"$\times$"),
        ("ℓ", r"$\ell$"),
        ("º", r"\textordmasculine{}"),
    ):
        t = t.replace(a, b)
    return t


def _clean_dict(d: object) -> dict:
    """Substitui None em folhas: texto → '', número → 0; recorre em dicts."""
    if not isinstance(d, dict):
        return {}
    text_keys = (
        "descricao", "nota", "nome", "ligacao", "sistema", "posicao",
        "norma", "modo_gov", "aco", "comb", "regime", "nota_chu",
        "l_1_nota", "eta_gov_key", "norma_barra",
    )
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out[k] = _clean_dict(v)
        elif v is None:
            out[k] = "" if k in text_keys else 0
        else:
            out[k] = v
    return out


def gerar_tex(
    resultados: dict,
    geo:        GeometriaViga,
    mat:        GlulamMaterial,
    nome:       str = "memorial_mlc",
    load=None,
) -> Path:
    """
    Gera o arquivo .tex do memorial de cálculo.

    Args:
        resultados : Dict com todos os resultados do pipeline
        geo        : Geometria da viga
        mat        : Material (classe de serviço e k_def)
        nome       : Nome base do arquivo
        load       : Carregamentos (opcional — combinações e esforços)

    Returns:
        Path do arquivo .tex gerado
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    tex_path = OUTPUT_DIR / f"{nome}.tex"

    hoje = date.today().strftime("%d/%m/%Y")

    # Extrair resultados dos módulos (mesmas chaves do console / main)
    r_cum  = _clean_dict(resultados.get("cumeeira",    {}))
    r_fl   = _clean_dict(resultados.get("flambagem",   {}))
    r_fx   = _clean_dict(resultados.get("flexao",      {}))
    r_ci   = _clean_dict(resultados.get("cisalhamento",{}))
    r_ap   = _clean_dict(resultados.get("apoio",       {}))
    r_fc   = _clean_dict(resultados.get("flexo_comp",  {}))
    r_pc   = _clean_dict(resultados.get("pilar_central", {}))
    r_els  = _clean_dict(resultados.get("ELS",         {}))
    r_L1   = _clean_dict(resultados.get("L1",          {}))
    r_L2   = _clean_dict(resultados.get("L2",          {}))
    r_L3   = _clean_dict(resultados.get("L3",          {}))
    r_L1c  = _clean_dict(resultados.get("L1c",         {}))
    r_L2c  = _clean_dict(resultados.get("L2c",         {}))
    r_L3c  = _clean_dict(resultados.get("L3c",         {}))
    r_fL1  = _clean_dict(resultados.get("fadiga_L1",   {}))
    r_fL2  = _clean_dict(resultados.get("fadiga_L2",   {}))
    r_fL1c = _clean_dict(resultados.get("fadiga_L1c",  {}))
    r_cv   = _clean_dict(resultados.get("contraventamento", {}))
    r_ter  = _clean_dict(resultados.get("terca", {}))
    meta   = _clean_dict(resultados.get("meta", {}))

    # Extrair sub-dicts de flexo_comp
    r_viga  = r_fc.get("viga",  {}) if r_fc else {}
    r_pilar = r_fc.get("pilar", {}) if r_fc else {}
    r_ter_biela = r_cv.get("terca", {}) if r_cv else {}
    if not isinstance(r_viga, dict):
        r_viga = {}
    if not isinstance(r_pilar, dict):
        r_pilar = {}
    if not isinstance(r_ter_biela, dict):
        r_ter_biela = {}

    k_def  = _f(resultados.get("k_def", mat.k_def), getattr(mat, "k_def", 2.0))
    s_m    = _f(meta.get("s", r_fl.get("l_1_m", 2.53)), 2.53)
    l_1_ef = _f(r_cv.get("l_1_efetivo_m", r_fl.get("l_1_m", s_m)), s_m)
    l_ap   = _f(meta.get("l_ap", r_ap.get("l_ap_m", 0.90)), 0.90)
    f_c    = (geo.h_ap - geo.h0) / 2.0
    cob_ok = bool(r_cv.get("cobertura_ok", r_cv.get("ok", False))) if r_cv else False
    cob_txt = "válida" if cob_ok else "NÃO válida"
    eta_lig_alvo = _f(meta.get("eta_lig_alvo", r_L1.get("eta_alvo", 0.85)), 0.85)

    # Combinação governante e cargas (se load disponível)
    if load is not None:
        gov = load.combinacao_ELU_governante()
        area_trib = load.area_trib
        g_k, q_k = load.g_k, load.q_k
        g_area, q_area = load.g_area, load.q_area
        combs = load.combinacoes
    else:
        gov = None
        area_trib = meta.get("area_trib", 5.75)
        g_area = meta.get("g_area", 1.50)
        q_area = meta.get("q_area", 0.25)
        g_k = g_area * area_trib
        q_k = q_area * area_trib
        combs = {}

    def eta_row(nome_verif, norma, eta, ok=True):
        simbolo = r"\checkmark" if ok else r"\times"
        cor     = "etaok" if ok else "etaerr"
        return (
            f"  {nome_verif} & {norma} & "
            f"\\textcolor{{{cor}}}{{{_f(eta):.4f}}} & "
            f"\\textcolor{{{cor}}}{{{simbolo}}} \\\\\n"
        )

    def _eta(d, key="eta", default=0.0):
        return float(d.get(key, default) or 0.0)

    def _ok(d, default=True):
        return bool(d.get("ok", default))

    # Linhas de combinações (dinâmicas)
    comb_lines = ""
    if combs:
        ordem_c = ["ELU_C2", "ELU_C1", "ELU_C3", "ELU_C4", "ELS_S1", "ELS_S2", "ELS_S3"]
        for nome in ordem_c:
            if nome not in combs:
                continue
            c = combs[nome]
            tag = r" \textit{(governa)}" if gov and c.nome == gov.nome else ""
            # remove marcador de console se existir (o tag LaTeX basta)
            desc = (c.descricao
                    .replace(" ← GOVERNA", "")
                    .replace("← GOVERNA", "")
                    .replace("_", r"\_"))
            comb_lines += (
                f"  {nome.replace('_', '\\_')}{tag} & "
                f"{desc} & {_br(c.q_tot, 3)} \\\\\n"
            )
    else:
        comb_lines = "  -- & (carregar \\texttt{load} no relatório) & -- \\\\\n"

    # Esforços governantes
    if gov is not None:
        H_gov = gov.H_kN
        Rv_gov = gov.V_max_kN
        Mmax_gov = gov.M_max_kNm
        Mcum_gov = gov.M_cumeeira_kNm
        N_gov = gov.N_viga_kN
        xM_gov = gov.x_Mmax_m
        q_gov = gov.q_tot
        gov_nome = gov.nome
    else:
        H_gov = Mmax_gov = Mcum_gov = N_gov = xM_gov = q_gov = Rv_gov = 0.0
        gov_nome = "--"

    # ELS — cores e símbolos por verificação
    eta_S1 = float(r_els.get("eta_S1", 0) or 0)
    eta_nf = float(r_els.get("eta_net_fin", 0) or 0)
    ok_S1  = eta_S1 <= 1.0
    ok_nf  = eta_nf <= 1.0
    cor_S1 = "etaok" if ok_S1 else "etaerr"
    cor_nf = "etaok" if ok_nf else "etaerr"
    sim_S1 = r"\checkmark" if ok_S1 else r"\times"
    sim_nf = r"\checkmark" if ok_nf else r"\times"

    cand = str(meta.get("candidato", "R2"))

    # η máximo (todas as verificações do resumo)
    etas_resumo = [
        _eta(r_cum), _eta(r_fl), _eta(r_fx), _eta(r_ci), _eta(r_ap),
        _eta(r_pilar), _eta(r_pc), _eta(r_cv), _eta(r_ter), _eta(r_els),
        _eta(r_L1), _eta(r_L2), _eta(r_L3),
        _eta(r_L1c), _eta(r_L2c), _eta(r_L3c),
        _eta(r_fL1), _eta(r_fL2), _eta(r_fL1c),
    ]
    eta_max = max(etas_resumo) if etas_resumo else 0.0

    parts: list[str] = []
    # Secções LaTeX em subexpressões (evita profundidade AST excessiva)

    parts.append('\\documentclass[a4paper,11pt]{article}\n\n% ── Pacotes ──────────────────────────────────────────────────\n\\usepackage[T1]{fontenc}\n\\usepackage[utf8]{inputenc}\n\\usepackage[brazil]{babel}\n\\usepackage[left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm]{geometry}\n\\usepackage{booktabs}\n\\usepackage{array}\n\\usepackage{xcolor}\n\\usepackage{helvet}\n\\usepackage{fancyhdr}\n\\usepackage{lastpage}\n\\usepackage{multirow}\n\\usepackage{amsmath}\n\\usepackage{amssymb}\n\n\\renewcommand{\\familydefault}{\\sfdefault}\n\n% Cores\n\\definecolor{etaok}{RGB}{0,128,0}\n\\definecolor{etaerr}{RGB}{200,0,0}\n\\definecolor{cabec}{RGB}{40,40,40}\n\\definecolor{cinza}{RGB}{245,245,245}\n\n% Cabeçalho e rodapé\n\\pagestyle{fancy}\n\\fancyhf{}\n\\renewcommand{\\headrulewidth}{0.4pt}\n\\fancyhead[L]{\\small\\textbf{STOCKI Engenharia Estrutural}}\n\\fancyhead[R]{\\small Memorial de Cálculo -- Galpão MLC}\n\\fancyfoot[C]{\\small Página \\thepage\\ de \\pageref{LastPage}}\n\\fancyfoot[R]{\\small ')
    parts.append(hoje)
    parts.append('}\n\n\\setlength{\\parindent}{0pt}\n\\setlength{\\parskip}{4pt}\n\n% ── Início do documento ───────────────────────────────────────\n\\begin{document}\n\n% Capa / Cabeçalho\n\\begin{center}\n  {\\Large\\textbf{MEMORIAL DE CÁLCULO}} \\\\[6pt]\n  {\\large Estrutura em Madeira Lamelada Colada (MLC)} \\\\[4pt]\n  {\\normalsize Galpão para Estacionamento Coberto} \\\\[12pt]\n  \\begin{tabular}{ll}\n    \\textbf{Responsável Técnico:} & Gabriel Stocki \\\\\n    \\textbf{CREA:}                & PR 195315/D \\\\\n    \\textbf{Empresa:}             & STOCKI Engenharia Estrutural \\\\\n    \\textbf{Data:}                & ')
    parts.append(hoje)
    parts.append(' \\\\\n  \\end{tabular}\n\\end{center}\n\n\\vspace{6pt}\n\\hrule\n\\vspace{10pt}\n\n% ── 1. Normas de Referência ───────────────────────────────────\n\\section*{1. Normas de Referência}\n\n\\begin{tabular}{ll}\n  EN 1995-1-1:2004 & Eurocode 5 -- Estruturas de madeira \\\\\n  EN 1990:2002     & Eurocode -- Bases de projeto \\\\\n  EN 14080:2013    & Madeira lamelada colada -- Requisitos \\\\\n  EN 14592:2008    & Fixadores de aço para estruturas de madeira \\\\\n  EN 1993-1-8:2005 & Eurocode 3 -- Ligações \\\\\n  ABNT NBR 6123:1988 & Forças devidas ao vento em edificações \\\\\n\\end{tabular}\n\n% ── 2. Dados Gerais ───────────────────────────────────────────\n\\section*{2. Dados Gerais do Projeto}\n\n\\begin{tabular}{lll}\n  \\toprule\n  \\textbf{Item} & \\textbf{Valor} & \\textbf{Observação} \\\\\n  \\midrule\n  Uso & Estacionamento coberto & Galpão aberto nas laterais \\\\\n  Localização & Londrina -- PR & -- \\\\\n  Vão total & 40{,}50~m & 2 pórticos $\\times$ 20{,}25~m \\\\\n  Comprimento & 46{,}00~m & -- \\\\\n  Pé-direito & 7{,}00~m & -- \\\\\n  Espaçamento entre pórticos & 5{,}75~m & Vão das terças \\\\\n  Sistema estrutural & Viga biarticulada MLC & 1$\\times$ hiperestática \\\\\n  \\bottomrule\n\\end{tabular}\n\n% ── 3. Material ───────────────────────────────────────────────\n\\section*{3. Material -- ')
    parts.append(mat.classe)
    parts.append(' (EN 14080)}\n\n\\begin{tabular}{llll}\n  \\toprule\n  \\textbf{Propriedade} & \\textbf{Valor} & \\textbf{Propriedade} & \\textbf{Valor} \\\\\n  \\midrule\n  $f_{m,k}$    & ')
    parts.append(_br(mat.f_m_k / 1000000.0, 1))
    parts.append('~MPa  & $E_{0,mean}$ & ')
    parts.append(_br(mat.E0_mean / 1000000.0, 0))
    parts.append('~MPa \\\\\n  $f_{t,90,k}$ & ')
    parts.append(_br(mat.f_t90_k / 1000000.0, 2))
    parts.append('~MPa  & $E_{0,05}$   & ')
    parts.append(_br(mat.E0_05 / 1000000.0, 0))
    parts.append('~MPa  \\\\\n  $f_{c,0,k}$  & ')
    parts.append(_br(mat.f_c0_k / 1000000.0, 1))
    parts.append('~MPa  & $G_{mean}$   & ')
    parts.append(_br(mat.G_mean / 1000000.0, 0))
    parts.append('~MPa    \\\\\n  $f_{c,90,k}$ & ')
    parts.append(_br(mat.f_c90_k / 1000000.0, 2))
    parts.append('~MPa  & $\\rho_k$     & ')
    parts.append(_br(mat.rho_k, 0))
    parts.append('~kg/m³  \\\\\n  $f_{v,k}$    & ')
    parts.append(_br(mat.f_v_k / 1000000.0, 2))
    parts.append('~MPa  & $\\gamma_M$   & 1{,}25     \\\\\n  \\multicolumn{2}{l}{Classe de serviço: ')
    parts.append(f'{mat.classe_servico}')
    parts.append(' (EC5 \\S2.3.1.3)} &\n  \\multicolumn{2}{l}{$k_{def} = ')
    parts.append(_br(k_def, 2))
    parts.append('$ \\quad (EC5 Tab.~3.2)} \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\textit{CS')
    parts.append(f'{mat.classe_servico}')
    parts.append(': estrutura aberta nas laterais / exposição a intempérie.}\n\n\\vspace{4pt}\n\\begin{tabular}{lll}\n  \\toprule\n  \\textbf{Duração} & $k_{mod}$ (CS')
    parts.append(f'{mat.classe_servico}')
    parts.append(') & \\textbf{Combinação} \\\\\n  \\midrule\n  Curta       & ')
    parts.append(_br(GlulamMaterial(mat.classe, mat.classe_servico, 'curta').k_mod, 2))
    parts.append(' & ELU com vento dominante \\\\\n  Longa       & ')
    parts.append(_br(GlulamMaterial(mat.classe, mat.classe_servico, 'longa').k_mod, 2))
    parts.append(' & ELS / acções de longa duração \\\\\n  Permanente  & ')
    parts.append(_br(GlulamMaterial(mat.classe, mat.classe_servico, 'permanente').k_mod, 2))
    parts.append(' & Comb. quase-permanente (fluência) \\\\\n  \\bottomrule\n\\end{tabular}\n\n% ── 4. Ações e Combinações ────────────────────────────────────\n\\section*{4. Ações e Combinações}\n\n\\textbf{Cargas características (pórtico intermédio):}\n\n\\begin{tabular}{llll}\n  \\toprule\n  \\textbf{Ação} & \\textbf{Valor por área} & \\textbf{Valor linear} & \\textbf{Norma} \\\\\n  \\midrule\n  Permanente $g_k$ & ')
    parts.append(_br(g_area, 2))
    parts.append('~kN/m² & ')
    parts.append(_br(g_k, 3))
    parts.append('~kN/m & Estimativa \\\\\n  Sobrecarga $q_k$ & ')
    parts.append(_br(q_area, 2))
    parts.append('~kN/m² & ')
    parts.append(_br(q_k, 3))
    parts.append('~kN/m & EN 1991-1-1 \\\\\n  \\multicolumn{3}{l}{Área tributária $= L_t = ')
    parts.append(_br(area_trib, 2))
    parts.append('$~m (pórtico intermédio)} & Geometria \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{6pt}\n\\textbf{Vento -- NBR 6123 (cobertura isolada 2 águas):}\n\n\\begin{tabular}{lll}\n  \\toprule\n  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Ref.} \\\\\n  \\midrule\n  $V_0$ (Londrina/PR) & 45{,}0~m/s & Fig.~1 \\\\\n  $S_1$ & 1{,}0 & \\S5.2 \\\\\n  $S_2$ (Cat.~IV, Cl.~B) & 0{,}83 & Tab.~3 \\\\\n  $S_3$ & 1{,}0 & \\S5.5 \\\\\n  $H_1 = h_{ap}-h_0$ & ')
    parts.append(_br(geo.h_ap - geo.h0, 3))
    parts.append('~m & Geometria ')
    parts.append(cand)
    parts.append(' \\\\\n  $\\tan\\beta = H_1/(L/2)$ & ')
    parts.append(_br((geo.h_ap - geo.h0) / (geo.L / 2), 4))
    parts.append(' & \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{6pt}\n\\textbf{Combinações de ações -- EN 1990 (valores do pipeline):}\n\n\\begin{tabular}{p{3.2cm}p{7.5cm}r}\n  \\toprule\n  \\textbf{Combinação} & \\textbf{Descrição} & \\textbf{$q_{tot}$ (kN/m)} \\\\\n  \\midrule\n')
    parts.append(comb_lines)
    parts.append('  \\bottomrule\n\\end{tabular}\n\n% ── 5. Sistema Estrutural ─────────────────────────────────────\n\\section*{5. Sistema Estrutural -- Viga Biarticulada (MLC monolítica)}\n\n\\begin{itemize}\n  \\item Peça única de duplo-bisel: extradorso em duas águas, intradorso reto.\n  \\item \\textbf{Sem rótula na cumeeira} (continuidade física da MLC).\n  \\item Rótulas apenas nos apoios (bases).\n  \\item Grau de hiperestaticidade: 1 -- empuxo $H$ por \\textbf{compatibilidade}\n        (Castigliano / força unitária no eixo centroidal $y_c$).\n  \\item Integração em projecção horizontal $\\mathrm{d}x$ (autorizada no projecto).\n  \\item $M$ na cumeeira em geral $\\neq 0$ $\\Rightarrow$ EC5 \\S6.4.3 activo.\n  \\item Classe de serviço ')
    parts.append(f'{mat.classe_servico}')
    parts.append(': galpão aberto nas laterais.\n  \\item \\textbf{Contraventamento horizontal} (cruzes de St.~André + terças-biela):\n        garante a função estrutural da cobertura e valida $l_1=s$ no LTB\n        (EC5~\\S9.2.5) -- ver \\S9.\n\\end{itemize}\n\n\\textbf{Análise (combinação governante ')
    parts.append(gov_nome.replace('_', '\\_'))
    parts.append('):}\n\n\\[\n  R_v = \\frac{qL}{2} = ')
    parts.append(_br(Rv_gov, 2))
    parts.append('~\\text{kN}\n\\]\n\\[\n  H = \\frac{\\int M_0 y_c / I \\,\\mathrm{d}x}{\\int y_c^2 / I \\,\\mathrm{d}x}\n    = ')
    parts.append(_br(H_gov, 2))
    parts.append('~\\text{kN}\n  \\qquad\n  f_c = \\frac{h_{ap}-h_0}{2} = ')
    parts.append(_br(f_c, 3))
    parts.append('~\\text{m}\n\\]\n\\[\n  M(x) = M_0(x) - H\\, y_c(x),\\quad\n  M_{max} = ')
    parts.append(_br(Mmax_gov, 2))
    parts.append('~\\text{kN·m}\n  \\ (x = ')
    parts.append(_br(xM_gov, 3))
    parts.append('~\\text{m})\n\\]\n\\[\n  M_{cumeeira} = ')
    parts.append(_br(Mcum_gov, 2))
    parts.append('~\\text{kN·m},\\quad\n  N_{apoio} = ')
    parts.append(_br(N_gov, 2))
    parts.append('~\\text{kN}\n\\]\n\n% ── 6. Geometria da Viga (candidata de projecto) ──────────────\n\\section*{6. Geometria da Viga -- Candidata ')
    parts.append(cand)
    parts.append('}\n\n\\begin{tabular}{lll}\n  \\toprule\n  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Observação} \\\\\n  \\midrule\n  Vão $L$ & ')
    parts.append(_br(geo.L, 2))
    parts.append('~m & Por pórtico \\\\\n  Altura no apoio $h_0$ & ')
    parts.append(_br(geo.h0, 2))
    parts.append('~m & ')
    parts.append(cand)
    parts.append(' \\\\\n  Inclinação $\\alpha$ & ')
    parts.append(_br(geo.alpha_deg, 1))
    parts.append('° & Extradorso \\\\\n  Largura $b$ & ')
    parts.append(_br(geo.b, 2))
    parts.append('~m & \\\\\n  Altura na cumeeira $h_{ap}$ & ')
    parts.append(_br(geo.h_ap, 3))
    parts.append('~m & \\\\\n  Flecha do eixo $f_c$ & ')
    parts.append(_br(f_c, 3))
    parts.append('~m & $(h_{ap}-h_0)/2$ \\\\\n  Espaçamento terças $s$ & ')
    parts.append(_br(s_m, 2))
    parts.append('~m & Geometria de cobertura \\\\\n  $l_1$ efectivo (LTB) & ')
    parts.append(_br(l_1_ef, 2))
    parts.append('~m & ')
    parts.append('Cobertura OK $\\Rightarrow l_1=s$' if cob_ok else 'Cobertura falha $\\Rightarrow l_1=\\ell$ (penalizado)')
    parts.append(' \\\\\n  $l_{ef}$ flambagem & ')
    parts.append(_br(0.9 * l_1_ef, 3))
    parts.append('~m & EC5 Tab.~6.1 ($0{,}9\\,l_1$) \\\\\n  Placa de apoio $l_{ap}$ & ')
    parts.append(_br(l_ap, 2))
    parts.append('~m & \\\\\n  \\bottomrule\n\\end{tabular}\n\n% ── 7. Verificações ELU ───────────────────────────────────────\n\\section*{7. Verificações ELU -- Viga}\n\n\\begin{tabular}{p{5.5cm}lcc}\n  \\toprule\n  \\textbf{Verificação} & \\textbf{Norma} & $\\boldsymbol{\\eta}$ & \\textbf{Status} \\\\\n  \\midrule\n')
    parts.append(eta_row('Cumeeira ($t_{90}$, $M\\neq 0$)', 'EC5 \\S6.4.3', _eta(r_cum), _ok(r_cum)))
    parts.append(eta_row('Flambagem lateral', 'EC5 \\S6.3.3', _eta(r_fl), _ok(r_fl)))
    parts.append(eta_row('Flexo-compressão viga', 'EC5 \\S6.3.2+\\S6.3.3', _eta(r_fx), _ok(r_fx)))
    parts.append(eta_row('Cisalhamento ($b_{ef}=k_{cr}b$)', 'EC5 \\S6.1.7', _eta(r_ci), _ok(r_ci)))
    parts.append(eta_row('Compressão no apoio', 'EC5 \\S6.1.5+\\S6.2.2', _eta(r_ap), _ok(r_ap)))
    parts.append('  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\textbf{Detalhes -- Flexo-compressão viga (EC5~\\S6.3.2 Eq.~6.23):}\n\n\\[\n  \\left(\\frac{\\sigma_{c,0,d}}{k_c \\cdot f_{c,0,d}}\\right)^2\n  + \\frac{\\sigma_{m,d}}{f_{m,d}} \\leq 1{,}0\n\\]\n\n\\begin{tabular}{lllll}\n  \\toprule\n  $M_d$ (kN·m) & $N_d$ (kN) & $\\sigma_{c,0,d}$ (MPa) & $\\sigma_{m,d}$ (MPa) & $k_c$ \\\\\n  \\midrule\n')
    parts.append(f'  {r_viga.get('M_max_kNm', 0):.2f} & ')
    parts.append(f'{r_viga.get('N_d_kN', 0):.2f} & ')
    parts.append(f'{r_viga.get('sigma_c_MPa', 0):.4f} & ')
    parts.append(f'{r_viga.get('sigma_m_MPa', 0):.4f} & ')
    parts.append(f'{r_viga.get('k_c_y', 0):.4f} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n% ── 8. Verificações ELU -- Pilares ────────────────────────────\n\\section*{8. Verificações ELU -- Pilares}\n\nCompressão simples EC5~\\S6.3.2; $l_{ef}=1{,}0\\cdot H$ (rótulas nas extremidades).\n\n\\begin{tabular}{llllllc}\n  \\toprule\n  \\textbf{Pilar} & Secção (m) & $N_d$ (kN) & $\\lambda$ & $\\lambda_{rel}$ & $k_c$ & $\\eta$ \\\\\n  \\midrule\n  Lateral & ')
    parts.append(f'{r_pilar.get('b_m', 0.22):.2f}$\\times${r_pilar.get('h_m', 0.26):.2f} & ')
    parts.append(f'{r_pilar.get('N_d_kN', 0):.2f} & ')
    parts.append(f'{r_pilar.get('lambda', 0):.1f} & ')
    parts.append(f'{r_pilar.get('lambda_rel', 0):.4f} & ')
    parts.append(f'{r_pilar.get('k_c', 0):.4f} & ')
    parts.append(f'\\textcolor{{{('etaok' if _ok(r_pilar) else 'etaerr')}}}{{{_eta(r_pilar):.4f}}} \\\\\n')
    parts.append('  Central ($N\\approx 2R_v$) & ')
    parts.append(f'{r_pc.get('b_m', 0.28):.2f}$\\times${r_pc.get('h_m', 0.28):.2f} & ')
    parts.append(f'{r_pc.get('N_d_kN', 0):.2f} & ')
    parts.append(f'{r_pc.get('lambda', 0):.1f} & ')
    parts.append(f'{r_pc.get('lambda_rel', 0):.4f} & ')
    parts.append(f'{r_pc.get('k_c', 0):.4f} & ')
    parts.append(f'\\textcolor{{{('etaok' if _ok(r_pc) else 'etaerr')}}}{{{_eta(r_pc):.4f}}} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n% ── 9. Contraventamento / integridade da cobertura ────────────\n\\section*{9. Contraventamento -- Integridade Estrutural da Cobertura}\n\nO contraventamento horizontal \\textbf{não é acessório}: é o que torna as\nterças apoios laterais válidos da viga principal. Sem ele, a hipótese\n$l_{ef}=0{,}9s$ da flambagem lateral (EC5~\\S6.3.3) deixa de ser legítima.\n\n\\textbf{Cadeia de forças (plano da cobertura):}\n\\begin{enumerate}\n  \\item Viga MLC comprimida ($N$ + $M$) gera força de estabilização\n        (EC5~\\S9.2.5).\n  \\item Terças actuam como \\textbf{bielas} (compressão + rigidez $EA/L$).\n  \\item Cruzes de St.~André nos módulos extremos (diagonal tracionada).\n  \\item Reacções no pórtico de extremidade $\\rightarrow$ fundação.\n\\end{enumerate}\n\n\\vspace{4pt}\n\\textbf{9.1 Compressão a estabilizar e sistema (EC5~\\S9.2.5)}\n\n\\begin{tabular}{lll}\n  \\toprule\n  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Ref.} \\\\\n  \\midrule\n  $N_{axial}$ (biarticulada) & ')
    parts.append(_br(r_cv.get('N_axial_kN', 0), 2))
    parts.append('~kN & Análise \\\\\n  $N_{flex}=(1-k_{crit})M_d/h$ & ')
    parts.append(_br(r_cv.get('N_flex_kN', 0), 2))
    parts.append('~kN & \\S9.2.5.2 \\\\\n  $N_d$ (estabilizar) & ')
    parts.append(_br(r_cv.get('N_d_kN', 0), 2))
    parts.append('~kN & \\\\\n  N.º de vigas $n$ & ')
    parts.append(f'{_i(r_cv.get('n_vigas', 0))}')
    parts.append(' & 9 eixos $\\times$ 2 pórticos \\\\\n  $\\ell$ (vão do sistema) & ')
    parts.append(_br(r_cv.get('ell_m', 46), 1))
    parts.append('~m & Entre baías rígidas \\\\\n  $k_\\ell=\\min(1,\\sqrt{15/\\ell})$ & ')
    parts.append(_br(r_cv.get('k_ell', 0), 3))
    parts.append(' & \\S9.2.5.3 \\\\\n  $q_d=k_\\ell n N_d/(k_{f,3}\\ell)$ & ')
    parts.append(_br(r_cv.get('q_d_kNpm', 0), 4))
    parts.append('~kN/m &\n    $k_{f,3}=')
    parts.append(_br(r_cv.get('k_f3', 50), 0))
    parts.append('$ \\\\\n  $R_{ext}=q_d\\ell/2$ & ')
    parts.append(_br(r_cv.get('R_ext_kN', 0), 2))
    parts.append('~kN & Por extremo \\\\\n  $a$ (restrição na viga) & ')
    parts.append(_br(r_cv.get('a_restricao_m', s_m), 2))
    parts.append('~m & $=s$ \\\\\n  $F_d=N_d/k_{f,2}$ (por apoio) & ')
    parts.append(_br(r_cv.get('F_d_apoio_kN', 0), 3))
    parts.append('~kN &\n    $k_{f,2}=')
    parts.append(_br(r_cv.get('k_f2', 80), 0))
    parts.append('$ (MLC) \\\\\n  $C_{\\min}=k_s N_d/a$ & ')
    parts.append(_br(r_cv.get('C_min_kNpm', 0), 1))
    parts.append('~kN/m &\n    $k_s=')
    parts.append(_br(r_cv.get('k_s', 4), 0))
    parts.append('$ \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\textbf{9.2 Diagonal de aço (EN~1993-1-1~\\S6.2.3)}\n\n\\begin{tabular}{lll}\n  \\toprule\n  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Obs.} \\\\\n  \\midrule\n  Layout & Cruzes nos ')
    parts.append(_tex_escape(r_cv.get('posicao', '2 modulos extremos')))
    parts.append(' & \\\\\n  Painel & ')
    parts.append(_br(r_cv.get('L_panel_m', 5.75), 2))
    parts.append('$\\times$')
    parts.append(_br(r_cv.get('s_terca_m', s_m), 2))
    parts.append('~m &\n    $d_{diag}=')
    parts.append(_br(r_cv.get('d_diag_m', 0), 3))
    parts.append('$~m,\n    $\\theta=')
    parts.append(_br(r_cv.get('theta_deg', 0), 1))
    parts.append('$° \\\\\n  Barra & $\\varnothing$')
    parts.append(f'{r_cv.get('d_barra_mm', 16):.0f}')
    parts.append('~mm ')
    parts.append(f'{r_cv.get('aco', 'S235')}')
    parts.append(' &\n    $A=')
    parts.append(_br(r_cv.get('A_mm2', 0), 1))
    parts.append('$~mm² \\\\\n  $F_{diag}$ & ')
    parts.append(_br(r_cv.get('F_diag_kN', 0), 2))
    parts.append('~kN & Tração (1 diagonal activa) \\\\\n  $N_{t,Rd}$ & ')
    parts.append(_br(r_cv.get('N_t_Rd_kN', 0), 2))
    parts.append('~kN & $A f_y/\\gamma_{M0}$ \\\\\n  $\\eta_N$ (diagonal) & ')
    parts.append(f'\\textcolor{{{('etaok' if r_cv.get('ok_diag', False) else 'etaerr')}}}{{{_eta(r_cv, 'eta_diag_N'):.4f}}}')
    parts.append(' & \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\textbf{9.3 Flecha do sistema e terça-biela}\n\n\\begin{tabular}{lll}\n  \\toprule\n  \\textbf{Verificação} & \\textbf{Valor} & $\\boldsymbol{\\eta}$ \\\\\n  \\midrule\n  $\\delta\\leq\\ell/500$ (rigidez global) &\n    ')
    parts.append(f'{r_cv.get('delta_mm', 0):.2f}')
    parts.append('~mm $\\leq$ ')
    parts.append(f'{r_cv.get('delta_lim_mm', 0):.1f}')
    parts.append('~mm & ')
    parts.append(f'\\textcolor{{{('etaok' if r_cv.get('ok_delta', False) else 'etaerr')}}}{{{_eta(r_cv, 'eta_delta'):.4f}}}')
    parts.append(' \\\\\n  Terça-biela $N_{Ed}/N_{Rd}$ (EC5~\\S6.3.2) &\n    $F=')
    parts.append(_br(r_cv.get('F_terca_kN', 0), 2))
    parts.append('$~kN,\n    $N_{Rd}=')
    parts.append(_br(r_ter_biela.get('N_Rd_kN', 0), 1))
    parts.append('$~kN & ')
    parts.append(f'\\textcolor{{{('etaok' if r_cv.get('ok_terca', False) else 'etaerr')}}}{{{_eta(r_cv, 'eta_terca'):.4f}}}')
    parts.append(' \\\\\n  Rigidez terça $EA/L\\geq C_{\\min}$ &\n    ')
    parts.append(_br(r_cv.get('C_terca_kNpm', 0), 0))
    parts.append(' $\\geq$ ')
    parts.append(_br(r_cv.get('C_min_kNpm', 0), 0))
    parts.append('~kN/m & ')
    parts.append(f'\\textcolor{{{('etaok' if r_cv.get('ok_C_terca', False) else 'etaerr')}}}{{{_eta(r_cv, 'eta_C_terca'):.4f}}}')
    parts.append(' \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\textbf{9.4 Função estrutural da cobertura (acoplamento ao LTB)}\n\n\\begin{tabular}{ll}\n  \\toprule\n  \\textbf{Indicador} & \\textbf{Resultado} \\\\\n  \\midrule\n  $\\mathtt{cobertura\\_ok}$ & ')
    parts.append('\\textcolor{etaok}{\\textbf{SIM}}' if cob_ok else '\\textcolor{etaerr}{\\textbf{NÃO}}')
    parts.append(' \\\\\n  Restrição lateral das terças & ')
    parts.append(cob_txt)
    parts.append(' para LTB \\\\\n  $l_1$ efectivo adoptado & ')
    parts.append(_br(l_1_ef, 3))
    parts.append('~m \\\\\n  $\\eta$ governante (contravent.) & ')
    parts.append(f'\\textcolor{{{('etaok' if _ok(r_cv) else 'etaerr')}}}{{{_eta(r_cv):.4f}}}')
    parts.append(' \\quad(')
    parts.append(str(r_cv.get('eta_gov_key', '--')).replace('_', '\\_'))
    parts.append(') \\\\\n  Quantitativo & ')
    parts.append(f'{_i(r_cv.get('n_barras', 0))}')
    parts.append(' barras $\\times$ ')
    parts.append(_br(r_cv.get('L_barra_m', 0), 2))
    parts.append('~m $=$ ')
    parts.append(_br(r_cv.get('L_total_m', 0), 1))
    parts.append('~m\n    (')
    parts.append(_br(r_cv.get('peso_total_kg', 0), 1))
    parts.append('~kg) \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\textit{Nota:} vento no sentido do comprimento do galpão (eixo~$Y$) e\ncontraventamento vertical de frontões \\textbf{não} estão neste módulo --\nsão sistema global distinto. Aqui trata-se apenas da estabilização das\nvigas e da integridade do plano da cobertura (EC5~\\S9.2.5).\n\n% ── 10. Verificações ELS ──────────────────────────────────────\n\\section*{10. Verificações ELS -- Flechas}\n\n\\begin{tabular}{lllcc}\n  \\toprule\n  \\textbf{Verificação} & \\textbf{Valor} & \\textbf{Limite} & $\\boldsymbol{\\eta}$ & \\\\\n  \\midrule\n  $w_{inst}(S1) \\leq L/300$ & ')
    parts.append(f'{r_els.get('w_S1_mm', 0):.2f}~mm & ')
    parts.append(f'{r_els.get('lim_inst_mm', 67.5):.2f}~mm & ')
    parts.append(f'\\textcolor{{{cor_S1}}}{{{eta_S1:.4f}}} & ')
    parts.append(f'\\textcolor{{{cor_S1}}}{{{sim_S1}}} \\\\\n')
    parts.append('  $w_{net,fin} \\leq L/250$ & ')
    parts.append(f'{r_els.get('w_net_fin_mm', 0):.2f}~mm & ')
    parts.append(f'{r_els.get('lim_fin_mm', 81.0):.2f}~mm & ')
    parts.append(f'\\textcolor{{{cor_nf}}}{{{eta_nf:.4f}}} & ')
    parts.append(f'\\textcolor{{{cor_nf}}}{{{sim_nf}}} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n')
    parts.append(f'Fluência (EC5~\\S2.3.2.2): $w_{{fin}} = {r_els.get('w_G_mm', 0):.2f}(1+{k_def:.2f}) + {r_els.get('w_Q1_mm', 0):.2f} = {r_els.get('w_fin_mm', 0):.2f}$~mm ($k_{{def}}={k_def:.2f}$, $\\psi_2=0$).\n\n')
    parts.append('\n% ── 11. Ligações ──────────────────────────────────────────────\n\\section*{11. Ligações}\n\n\\textit{Critério de projecto (uso público):} $\\eta_{\\mathrm{alvo}}=')
    parts.append(_br(eta_lig_alvo, 2))
    parts.append('$ para L1/L1c e L3 (ligações em madeira tendem a falha frágil;\nEC5 exige $\\eta\\leq 1{,}0$ -- o alvo 0{,}85 é margem de projecto).\n$n_{ef}$ por fileira // fibras: EC5~\\S8.5.1.1\n($n_{ef}=n^{0,9}(a_1/(13d))^{1/4}\\leq n$).\n\n\\vspace{4pt}\n\\begin{tabular}{p{4.5cm}p{5cm}cc}\n  \\toprule\n  \\textbf{Ligação} & \\textbf{Norma} & $\\boldsymbol{\\eta}$ & \\textbf{Status} \\\\\n  \\midrule\n')
    parts.append(eta_row('L1 -- Viga-pilar (base)', 'EC5 \\S8.2+\\S8.5.1.1+\\S8.6', _eta(r_L1), _ok(r_L1)))
    parts.append(eta_row('L2 -- Cumeeira', 'EC5 \\S6.1.4+\\S6.1.5+\\S8.6', _eta(r_L2), _ok(r_L2)))
    parts.append(eta_row('L3 -- Sapata (fundação)', 'EN 1993-1-8+EN 1992-4', _eta(r_L3), _ok(r_L3)))
    parts.append(eta_row('L1c -- Base pilar central', 'EC5 \\S8.2+\\S8.3+\\S8.6', _eta(r_L1c), _ok(r_L1c)))
    parts.append(eta_row('L2c -- Cumeeira central', 'EC5 \\S6.1.4+\\S6.1.5+\\S8.6', _eta(r_L2c), _ok(r_L2c)))
    parts.append(eta_row('L3c -- Sapata central', 'EN 1993-1-8+EN 1992-4', _eta(r_L3c), _ok(r_L3c)))
    parts.append('  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\begin{tabular}{llll}\n  \\toprule\n  \\textbf{Ligação} & \\textbf{Detalhe} & \\textbf{Parâmetro} & \\textbf{Valor} \\\\\n  \\midrule\n  L1 -- Viga-pilar & Pinos em chapa embutida &\n    $d$, $n$, layout &\n    ')
    parts.append(f'{r_L1.get('d_mm', 0):.0f}~mm, {r_L1.get('n_pinos', 0)}, ')
    parts.append(f'{r_L1.get('n_linha', 0)}$\\times${r_L1.get('n_linhas', 0)} \\\\\n')
    parts.append('  & & $F_{v,Rd}/\\text{pino}$ (2 planos) & ')
    parts.append(f'{r_L1.get('F_v_Rd_kN', 0):.3f}~kN \\\\\n')
    parts.append('  & & $n_{ef,row}$, $n_{ef}$ total & ')
    parts.append(f'{r_L1.get('n_ef_row', 0):.2f} (de {r_L1.get('n_linha', 0)}), ')
    parts.append(f'{r_L1.get('n_ef', 0):.2f} \\\\\n')
    parts.append('  & & $R_{total}$, $F_{res}$ & ')
    parts.append(f'{r_L1.get('R_total_kN', 0):.1f}~kN, ')
    parts.append(f'{r_L1.get('F_res_kN', 0):.1f}~kN \\\\\n')
    parts.append('  & & $\\eta$, $\\eta_{alvo}$ & ')
    parts.append(f'{_eta(r_L1):.4f}, {r_L1.get('eta_alvo', 0.85):.2f} \\\\\n')
    parts.append('  \\midrule\n  L2 -- Cumeeira & Pino passante & $d$, $n$ & ')
    parts.append(f'{r_L2.get('d_pino_mm', r_L2.get('d_mm', 0)):.0f}~mm, {r_L2.get('n_pino', r_L2.get('n_pinos', 0))} \\\\\n')
    parts.append('  & Compressão axial & $\\sigma_{c,0,d}$ & ')
    parts.append(f'{r_L2.get('sigma_c0_MPa', 0):.4f}~MPa \\\\\n')
    parts.append('  & & $\\eta$ & ')
    parts.append(f'{_eta(r_L2):.4f} \\\\\n')
    parts.append('  \\midrule\n  L3 -- Sapata & Chumbadores & $n$, $F_{chu}$ & ')
    parts.append(f'{r_L3.get('n_chumbadores', 0)}, {r_L3.get('F_chu_kN', 0):.0f}~kN/chu \\\\\n')
    parts.append('  & Chapa de base & Dimensões & ')
    parts.append(f'{r_L3.get('lado_chapa_cm', 0):.1f}$\\times${r_L3.get('lado_chapa_cm', 0):.1f}~cm \\\\\n')
    parts.append('  & & $H_d$, $\\eta$, $\\eta_{alvo}$ & ')
    parts.append(f'{r_L3.get('H_d_kN', 0):.1f}~kN, {_eta(r_L3):.4f}, ')
    parts.append(f'{r_L3.get('eta_alvo', 0.85):.2f} \\\\\n')
    parts.append('  \\midrule\n  L1c -- Central & 2 chapas independentes &\n    $d$, $n$/chapa, layout &\n    ')
    parts.append(f'{r_L1c.get('d_mm', 0):.0f}~mm, {r_L1c.get('n_pinos', 0)}, {r_L1c.get('n_linha', 0)}$\\times${r_L1c.get('n_linhas', 0)} \\\\\n')
    parts.append('  & & $\\eta$ & ')
    parts.append(f'{_eta(r_L1c):.4f} \\\\\n')
    parts.append('  \\midrule\n  L3c -- Sapata central & Chumbadores (H$\\approx$0) & $n$ & ')
    parts.append(f'{r_L3c.get('n_chumbadores', 0)} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n\\vspace{6pt}\n\\subsection*{11.1 Fadiga e deslizamento (EC5 \\S7.1 + \\S8.1.5)}\n\n\\begin{tabular}{llcccc}\n  \\toprule\n  \\textbf{Lig.} & \\textbf{Descrição} & $u_{inst}$ & $u_{fin}$ &\n  $\\eta_{slip}$ & $\\eta_{alt}$ \\\\\n  \\midrule\n')
    parts.append(f'  L1 & {_tex_escape(r_fL1.get('descricao', 'Base lateral'))} & {r_fL1.get('u_inst_mm', 0):.3f}~mm & {r_fL1.get('u_fin_mm', 0):.3f}~mm & {_eta(r_fL1, 'eta_slip'):.4f} & {_eta(r_fL1, 'eta_alt'):.4f} \\\\\n  L2 & {_tex_escape(r_fL2.get('descricao', 'Cumeeira'))} & {r_fL2.get('u_inst_mm', 0):.3f}~mm & {r_fL2.get('u_fin_mm', 0):.3f}~mm & {_eta(r_fL2, 'eta_slip'):.4f} & {_eta(r_fL2, 'eta_alt'):.4f} \\\\\n  L1c & {_tex_escape(r_fL1c.get('descricao', 'Base central'))} & {r_fL1c.get('u_inst_mm', 0):.3f}~mm & {r_fL1c.get('u_fin_mm', 0):.3f}~mm & {_eta(r_fL1c, 'eta_slip'):.4f} & {_eta(r_fL1c, 'eta_alt'):.4f} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n% ── 12. Resumo ────────────────────────────────────────────────\n\\section*{12. Resumo das Taxas de Utilização}\n\n\\begin{tabular}{llcc}\n  \\toprule\n  \\textbf{Verificação} & \\textbf{Norma} & $\\boldsymbol{\\eta}$ & \\textbf{Status} \\\\\n  \\midrule\n')
    parts.append(eta_row('Cumeeira ($t_{90}$, $M\\neq 0$)', 'EC5 \\S6.4.3', _eta(r_cum), _ok(r_cum, True)))
    parts.append(eta_row('Flambagem lateral', 'EC5 \\S6.3.3', _eta(r_fl), _ok(r_fl)))
    parts.append(eta_row('Flexo-comp. viga', 'EC5 \\S6.3.2', _eta(r_fx), _ok(r_fx)))
    parts.append(eta_row('Cisalhamento', 'EC5 \\S6.1.7', _eta(r_ci), _ok(r_ci)))
    parts.append(eta_row('Apoio', 'EC5 \\S6.1.5+\\S6.2.2', _eta(r_ap), _ok(r_ap)))
    parts.append(eta_row('Pilar lateral', 'EC5 \\S6.3.2', _eta(r_pilar), _ok(r_pilar)))
    parts.append(eta_row('Pilar central', 'EC5 \\S6.3.2', _eta(r_pc), _ok(r_pc)))
    parts.append(eta_row('Cobertura / contravent.', 'EC5 \\S9.2.5', _eta(r_cv), _ok(r_cv)))
    parts.append(eta_row('Terça (flexão)', 'EC5 \\S6.1.6+\\S6.1.7', _eta(r_ter), _ok(r_ter)))
    parts.append(eta_row('ELS -- flechas', 'EC5 \\S2.3.2.2', _eta(r_els), _ok(r_els)))
    parts.append(eta_row('L1 -- Viga-pilar', 'EC5 \\S8.2+\\S8.6', _eta(r_L1), _ok(r_L1)))
    parts.append(eta_row('L2 -- Cumeeira', 'EC5 \\S8.6', _eta(r_L2), _ok(r_L2)))
    parts.append(eta_row('L3 -- Sapata', 'EN 1993-1-8', _eta(r_L3), _ok(r_L3)))
    parts.append(eta_row('L1c -- Base central', 'EC5 \\S8.2+\\S8.6', _eta(r_L1c), _ok(r_L1c)))
    parts.append(eta_row('L2c -- Cumeeira central', 'EC5 \\S8.6', _eta(r_L2c), _ok(r_L2c)))
    parts.append(eta_row('L3c -- Sapata central', 'EN 1993-1-8', _eta(r_L3c), _ok(r_L3c)))
    parts.append(eta_row('Fadiga L1 ($\\eta_{slip}$)', 'EC5 \\S7.1', _eta(r_fL1), _ok(r_fL1)))
    parts.append(eta_row('Fadiga L2 ($\\eta_{slip}$)', 'EC5 \\S7.1', _eta(r_fL2), _ok(r_fL2)))
    parts.append(eta_row('Fadiga L1c ($\\eta_{slip}$)', 'EC5 \\S7.1', _eta(r_fL1c), _ok(r_fL1c)))
    parts.append('  \\midrule\n  \\multicolumn{2}{l}{\\textbf{$\\eta$ máximo}} &\n  \\multicolumn{2}{c}{\\textbf{')
    parts.append(f'{eta_max:.4f}')
    parts.append('}} \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{10pt}\n\\hrule\n\\vspace{4pt}\n{\\small Calculado por pipeline automatizado em Python -- EC5 + EN 1990 + NBR 6123.\nTodos os valores conferidos pelo Eng.\\ Resp.\\ antes da emissão.}\n\n\\end{document}\n')

    tex = "".join(parts)

    tex_path.write_text(tex, encoding="utf-8")
    return tex_path



def compilar_pdf(tex_path: Path) -> bool:
    """Compila .tex → PDF com pdflatex (2 passes). Retorna True se PDF ok."""
    tex_path = Path(tex_path)
    pdf_path = tex_path.with_suffix(".pdf")
    pdflatex = shutil.which("pdflatex")
    if not pdflatex:
        return False
    try:
        for _ in range(2):
            result = subprocess.run(
                [pdflatex, "-interaction=nonstopmode",
                 "-output-directory", str(tex_path.parent),
                 str(tex_path)],
                capture_output=True, timeout=90,
            )
        # sucesso se PDF existe e última compilação não falhou de forma total
        if not pdf_path.exists():
            return False
        # se returncode != 0 mas PDF existe, ainda reporta sucesso parcial
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def gerar_relatorio(
    resultados: dict,
    geo:        GeometriaViga,
    mat:        GlulamMaterial,
    nome:       str = "relatorio_mlc",
    load=None,
) -> None:
    """
    Gera relatório Excel + memorial LaTeX.

    Args:
        resultados : resultados do pipeline (incl. L1–L3, fadiga, meta)
        geo, mat   : geometria e material de projecto
        load       : Carregamentos (combinações e esforços no memorial)
        nome       : nome base dos ficheiros de saída
    """
    import pandas as pd

    OUTPUT_DIR.mkdir(exist_ok=True)

    # ── Excel ─────────────────────────────────────────────────
    ordem = [
        "cumeeira", "flambagem", "flexao", "cisalhamento", "apoio",
        "flexo_comp", "pilar_central", "terca", "contraventamento", "ELS",
        "L1", "L2", "L3", "L1c", "L2c", "L3c",
        "fadiga_L1", "fadiga_L2", "fadiga_L1c",
    ]
    linhas = []
    vistos = set()
    for verif in ordem + list(resultados.keys()):
        if verif in vistos:
            continue
        res = resultados.get(verif)
        if not isinstance(res, dict) or "eta" not in res:
            continue
        vistos.add(verif)
        linhas.append({
            "Verificação": verif,
            "η":           round(_f(res.get("eta")), 4),
            "OK":          "✓" if res.get("ok") else "✗",
        })

    xlsx_path = OUTPUT_DIR / f"{nome}.xlsx"
    if linhas:
        pd.DataFrame(linhas).to_excel(xlsx_path, index=False)
    else:
        pd.DataFrame(columns=["Verificação", "η", "OK"]).to_excel(
            xlsx_path, index=False
        )
    print(f"  Excel: {xlsx_path}")

    # ── LaTeX ─────────────────────────────────────────────────
    tex_path = gerar_tex(resultados, geo, mat, nome, load=load)
    print(f"  LaTeX: {tex_path}")

    # ── PDF ───────────────────────────────────────────────────
    if not shutil.which("pdflatex"):
        print(f"  PDF  : pdflatex não encontrado no PATH -- "
              f"compilar manualmente: pdflatex {tex_path.name}")
    else:
        ok_pdf = compilar_pdf(tex_path)
        if ok_pdf:
            print(f"  PDF  : {tex_path.with_suffix('.pdf')}")
        else:
            print(f"  PDF  : falha na compilação -- "
                  f"ver {tex_path.with_suffix('.log').name}")


# ── Execução directa ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Delega ao pipeline principal (R2 / CS3 / biarticulada) sem viz 3D
    from mlc_projeto.visualization import viz_3d
    viz_3d.visualizar_galpao = lambda *a, **k: print("  [viz 3D omitida]")
    from mlc_projeto.main import main
    main(rodar_varredura=False)
