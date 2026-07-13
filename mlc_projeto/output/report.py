"""
output/report.py — Memorial de cálculo em LaTeX.

Gera o arquivo .tex e compila para PDF se pdflatex estiver disponível.
Estrutura: tabelas de resultados com referências normativas.
Simples, direto, uso interno do escritório.
"""

from __future__ import annotations

import subprocess
import os
from pathlib import Path
from datetime import date

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


# ── Gerador LaTeX ─────────────────────────────────────────────────────────────

def _br(x: float, nd: int = 2) -> str:
    """Formato decimal brasileiro para LaTeX (vírgula)."""
    return f"{float(x):.{nd}f}".replace(".", "{,}")


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
    r_cum  = resultados.get("cumeeira",    {})
    r_fl   = resultados.get("flambagem",   {})
    r_fx   = resultados.get("flexao",      {})
    r_ci   = resultados.get("cisalhamento",{})
    r_ap   = resultados.get("apoio",       {})
    r_fc   = resultados.get("flexo_comp",  {})
    r_pc   = resultados.get("pilar_central", {})
    r_els  = resultados.get("ELS",         {})
    r_L1   = resultados.get("L1",          {})
    r_L2   = resultados.get("L2",          {})
    r_L3   = resultados.get("L3",          {})
    r_L1c  = resultados.get("L1c",         {})
    r_L2c  = resultados.get("L2c",         {})
    r_L3c  = resultados.get("L3c",         {})
    r_fL1  = resultados.get("fadiga_L1",   {})
    r_fL2  = resultados.get("fadiga_L2",   {})
    r_fL1c = resultados.get("fadiga_L1c",  {})
    r_cv   = resultados.get("contraventamento", {})
    r_ter  = resultados.get("terca", {})
    meta   = resultados.get("meta", {})

    # Extrair sub-dicts de flexo_comp
    r_viga  = r_fc.get("viga",  {}) if r_fc else {}
    r_pilar = r_fc.get("pilar", {}) if r_fc else {}
    r_ter_biela = r_cv.get("terca", {}) if r_cv else {}

    k_def = float(resultados.get("k_def", mat.k_def))
    s_m   = float(meta.get("s", r_fl.get("l_1_m", 2.53)))
    l_1_ef = float(r_cv.get("l_1_efetivo_m", r_fl.get("l_1_m", s_m)) or s_m)
    l_ap  = float(meta.get("l_ap", r_ap.get("l_ap_m", 0.90)))
    f_c   = (geo.h_ap - geo.h0) / 2.0
    cob_ok = bool(r_cv.get("cobertura_ok", r_cv.get("ok", False)))
    cob_txt = "válida" if cob_ok else "NÃO válida"

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
            f"\\textcolor{{{cor}}}{{{float(eta):.4f}}} & "
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

    tex = r"""\documentclass[a4paper,11pt]{article}

% ── Pacotes ──────────────────────────────────────────────────
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[brazil]{babel}
\usepackage[left=2.5cm,right=2.5cm,top=2.5cm,bottom=2.5cm]{geometry}
\usepackage{booktabs}
\usepackage{array}
\usepackage{xcolor}
\usepackage{helvet}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage{multirow}
\usepackage{amsmath}
\usepackage{amssymb}

\renewcommand{\familydefault}{\sfdefault}

% Cores
\definecolor{etaok}{RGB}{0,128,0}
\definecolor{etaerr}{RGB}{200,0,0}
\definecolor{cabec}{RGB}{40,40,40}
\definecolor{cinza}{RGB}{245,245,245}

% Cabeçalho e rodapé
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\fancyhead[L]{\small\textbf{STOCKI Engenharia Estrutural}}
\fancyhead[R]{\small Memorial de Cálculo -- Galpão MLC}
\fancyfoot[C]{\small Página \thepage\ de \pageref{LastPage}}
\fancyfoot[R]{\small """ + hoje + r"""}

\setlength{\parindent}{0pt}
\setlength{\parskip}{4pt}

% ── Início do documento ───────────────────────────────────────
\begin{document}

% Capa / Cabeçalho
\begin{center}
  {\Large\textbf{MEMORIAL DE CÁLCULO}} \\[6pt]
  {\large Estrutura em Madeira Lamelada Colada (MLC)} \\[4pt]
  {\normalsize Galpão para Estacionamento Coberto} \\[12pt]
  \begin{tabular}{ll}
    \textbf{Responsável Técnico:} & Gabriel Stocki \\
    \textbf{CREA:}                & PR 195315/D \\
    \textbf{Empresa:}             & STOCKI Engenharia Estrutural \\
    \textbf{Data:}                & """ + hoje + r""" \\
  \end{tabular}
\end{center}

\vspace{6pt}
\hrule
\vspace{10pt}

% ── 1. Normas de Referência ───────────────────────────────────
\section*{1. Normas de Referência}

\begin{tabular}{ll}
  EN 1995-1-1:2004 & Eurocode 5 -- Estruturas de madeira \\
  EN 1990:2002     & Eurocode -- Bases de projeto \\
  EN 14080:2013    & Madeira lamelada colada -- Requisitos \\
  EN 14592:2008    & Fixadores de aço para estruturas de madeira \\
  EN 1993-1-8:2005 & Eurocode 3 -- Ligações \\
  ABNT NBR 6123:1988 & Forças devidas ao vento em edificações \\
\end{tabular}

% ── 2. Dados Gerais ───────────────────────────────────────────
\section*{2. Dados Gerais do Projeto}

\begin{tabular}{lll}
  \toprule
  \textbf{Item} & \textbf{Valor} & \textbf{Observação} \\
  \midrule
  Uso & Estacionamento coberto & Galpão aberto nas laterais \\
  Localização & Londrina -- PR & -- \\
  Vão total & 40{,}50~m & 2 pórticos $\times$ 20{,}25~m \\
  Comprimento & 46{,}00~m & -- \\
  Pé-direito & 7{,}00~m & -- \\
  Espaçamento entre pórticos & 5{,}75~m & Vão das terças \\
  Sistema estrutural & Viga biarticulada MLC & 1$\times$ hiperestática \\
  \bottomrule
\end{tabular}

% ── 3. Material ───────────────────────────────────────────────
\section*{3. Material -- """ + mat.classe + r""" (EN 14080)}

\begin{tabular}{llll}
  \toprule
  \textbf{Propriedade} & \textbf{Valor} & \textbf{Propriedade} & \textbf{Valor} \\
  \midrule
  $f_{m,k}$    & """ + _br(mat.f_m_k/1e6, 1) + r"""~MPa  & $E_{0,mean}$ & """ + _br(mat.E0_mean/1e6, 0) + r"""~MPa \\
  $f_{t,90,k}$ & """ + _br(mat.f_t90_k/1e6, 2) + r"""~MPa  & $E_{0,05}$   & """ + _br(mat.E0_05/1e6, 0) + r"""~MPa  \\
  $f_{c,0,k}$  & """ + _br(mat.f_c0_k/1e6, 1) + r"""~MPa  & $G_{mean}$   & """ + _br(mat.G_mean/1e6, 0) + r"""~MPa    \\
  $f_{c,90,k}$ & """ + _br(mat.f_c90_k/1e6, 2) + r"""~MPa  & $\rho_k$     & """ + _br(mat.rho_k, 0) + r"""~kg/m³  \\
  $f_{v,k}$    & """ + _br(mat.f_v_k/1e6, 2) + r"""~MPa  & $\gamma_M$   & 1{,}25     \\
  \multicolumn{2}{l}{Classe de serviço: """ + f"{mat.classe_servico}" + r""" (EC5 \S2.3.1.3)} &
  \multicolumn{2}{l}{$k_{def} = """ + _br(k_def, 2) + r"""$ \quad (EC5 Tab.~3.2)} \\
  \bottomrule
\end{tabular}

\vspace{4pt}
\textit{CS""" + f"{mat.classe_servico}" + r""": estrutura aberta nas laterais / exposição a intempérie.}

\vspace{4pt}
\begin{tabular}{lll}
  \toprule
  \textbf{Duração} & $k_{mod}$ (CS""" + f"{mat.classe_servico}" + r""") & \textbf{Combinação} \\
  \midrule
  Curta       & """ + _br(GlulamMaterial(mat.classe, mat.classe_servico, 'curta').k_mod, 2) + r""" & ELU com vento dominante \\
  Longa       & """ + _br(GlulamMaterial(mat.classe, mat.classe_servico, 'longa').k_mod, 2) + r""" & ELS / acções de longa duração \\
  Permanente  & """ + _br(GlulamMaterial(mat.classe, mat.classe_servico, 'permanente').k_mod, 2) + r""" & Comb. quase-permanente (fluência) \\
  \bottomrule
\end{tabular}

% ── 4. Ações e Combinações ────────────────────────────────────
\section*{4. Ações e Combinações}

\textbf{Cargas características (pórtico intermédio):}

\begin{tabular}{llll}
  \toprule
  \textbf{Ação} & \textbf{Valor por área} & \textbf{Valor linear} & \textbf{Norma} \\
  \midrule
  Permanente $g_k$ & """ + _br(g_area, 2) + r"""~kN/m² & """ + _br(g_k, 3) + r"""~kN/m & Estimativa \\
  Sobrecarga $q_k$ & """ + _br(q_area, 2) + r"""~kN/m² & """ + _br(q_k, 3) + r"""~kN/m & EN 1991-1-1 \\
  \multicolumn{3}{l}{Área tributária $= L_t = """ + _br(area_trib, 2) + r"""$~m (pórtico intermédio)} & Geometria \\
  \bottomrule
\end{tabular}

\vspace{6pt}
\textbf{Vento -- NBR 6123 (cobertura isolada 2 águas):}

\begin{tabular}{lll}
  \toprule
  \textbf{Parâmetro} & \textbf{Valor} & \textbf{Ref.} \\
  \midrule
  $V_0$ (Londrina/PR) & 45{,}0~m/s & Fig.~1 \\
  $S_1$ & 1{,}0 & \S5.2 \\
  $S_2$ (Cat.~IV, Cl.~B) & 0{,}83 & Tab.~3 \\
  $S_3$ & 1{,}0 & \S5.5 \\
  $H_1 = h_{ap}-h_0$ & """ + _br(geo.h_ap - geo.h0, 3) + r"""~m & Geometria """ + cand + r""" \\
  $\tan\beta = H_1/(L/2)$ & """ + _br((geo.h_ap-geo.h0)/(geo.L/2), 4) + r""" & \\
  \bottomrule
\end{tabular}

\vspace{6pt}
\textbf{Combinações de ações -- EN 1990 (valores do pipeline):}

\begin{tabular}{p{3.2cm}p{7.5cm}r}
  \toprule
  \textbf{Combinação} & \textbf{Descrição} & \textbf{$q_{tot}$ (kN/m)} \\
  \midrule
""" + comb_lines + r"""  \bottomrule
\end{tabular}

% ── 5. Sistema Estrutural ─────────────────────────────────────
\section*{5. Sistema Estrutural -- Viga Biarticulada (MLC monolítica)}

\begin{itemize}
  \item Peça única de duplo-bisel: extradorso em duas águas, intradorso reto.
  \item \textbf{Sem rótula na cumeeira} (continuidade física da MLC).
  \item Rótulas apenas nos apoios (bases).
  \item Grau de hiperestaticidade: 1 -- empuxo $H$ por \textbf{compatibilidade}
        (Castigliano / força unitária no eixo centroidal $y_c$).
  \item Integração em projecção horizontal $\mathrm{d}x$ (autorizada no projecto).
  \item $M$ na cumeeira em geral $\neq 0$ $\Rightarrow$ EC5 \S6.4.3 activo.
  \item Classe de serviço """ + f"{mat.classe_servico}" + r""": galpão aberto nas laterais.
  \item \textbf{Contraventamento horizontal} (cruzes de St.~André + terças-biela):
        garante a função estrutural da cobertura e valida $l_1=s$ no LTB
        (EC5~\S9.2.5) -- ver \S9.
\end{itemize}

\textbf{Análise (combinação governante """ + gov_nome.replace("_", r"\_") + r"""):}

\[
  R_v = \frac{qL}{2} = """ + _br(Rv_gov, 2) + r"""~\text{kN}
\]
\[
  H = \frac{\int M_0 y_c / I \,\mathrm{d}x}{\int y_c^2 / I \,\mathrm{d}x}
    = """ + _br(H_gov, 2) + r"""~\text{kN}
  \qquad
  f_c = \frac{h_{ap}-h_0}{2} = """ + _br(f_c, 3) + r"""~\text{m}
\]
\[
  M(x) = M_0(x) - H\, y_c(x),\quad
  M_{max} = """ + _br(Mmax_gov, 2) + r"""~\text{kN·m}
  \ (x = """ + _br(xM_gov, 3) + r"""~\text{m})
\]
\[
  M_{cumeeira} = """ + _br(Mcum_gov, 2) + r"""~\text{kN·m},\quad
  N_{apoio} = """ + _br(N_gov, 2) + r"""~\text{kN}
\]

% ── 6. Geometria da Viga (candidata de projecto) ──────────────
\section*{6. Geometria da Viga -- Candidata """ + cand + r"""}

\begin{tabular}{lll}
  \toprule
  \textbf{Parâmetro} & \textbf{Valor} & \textbf{Observação} \\
  \midrule
  Vão $L$ & """ + _br(geo.L, 2) + r"""~m & Por pórtico \\
  Altura no apoio $h_0$ & """ + _br(geo.h0, 2) + r"""~m & """ + cand + r""" \\
  Inclinação $\alpha$ & """ + _br(geo.alpha_deg, 1) + r"""° & Extradorso \\
  Largura $b$ & """ + _br(geo.b, 2) + r"""~m & \\
  Altura na cumeeira $h_{ap}$ & """ + _br(geo.h_ap, 3) + r"""~m & \\
  Flecha do eixo $f_c$ & """ + _br(f_c, 3) + r"""~m & $(h_{ap}-h_0)/2$ \\
  Espaçamento terças $s$ & """ + _br(s_m, 2) + r"""~m & Geometria de cobertura \\
  $l_1$ efectivo (LTB) & """ + _br(l_1_ef, 2) + r"""~m & """ + (
    "Cobertura OK $\\Rightarrow l_1=s$" if cob_ok
    else "Cobertura falha $\\Rightarrow l_1=\\ell$ (penalizado)"
) + r""" \\
  $l_{ef}$ flambagem & """ + _br(0.9 * l_1_ef, 3) + r"""~m & EC5 Tab.~6.1 ($0{,}9\,l_1$) \\
  Placa de apoio $l_{ap}$ & """ + _br(l_ap, 2) + r"""~m & \\
  \bottomrule
\end{tabular}

% ── 7. Verificações ELU ───────────────────────────────────────
\section*{7. Verificações ELU -- Viga}

\begin{tabular}{p{5.5cm}lcc}
  \toprule
  \textbf{Verificação} & \textbf{Norma} & $\boldsymbol{\eta}$ & \textbf{Status} \\
  \midrule
""" + \
    eta_row("Cumeeira ($t_{90}$, $M\\neq 0$)", "EC5 \\S6.4.3",
            _eta(r_cum), _ok(r_cum)) + \
    eta_row("Flambagem lateral",             "EC5 \\S6.3.3",
            _eta(r_fl), _ok(r_fl)) + \
    eta_row("Flexo-compressão viga",         "EC5 \\S6.3.2+\\S6.3.3",
            _eta(r_fx), _ok(r_fx)) + \
    eta_row("Cisalhamento ($b_{ef}=k_{cr}b$)", "EC5 \\S6.1.7",
            _eta(r_ci), _ok(r_ci)) + \
    eta_row("Compressão no apoio",           "EC5 \\S6.1.5+\\S6.2.2",
            _eta(r_ap), _ok(r_ap)) + \
r"""  \bottomrule
\end{tabular}

\vspace{4pt}
\textbf{Detalhes -- Flexo-compressão viga (EC5~\S6.3.2 Eq.~6.23):}

\[
  \left(\frac{\sigma_{c,0,d}}{k_c \cdot f_{c,0,d}}\right)^2
  + \frac{\sigma_{m,d}}{f_{m,d}} \leq 1{,}0
\]

\begin{tabular}{lllll}
  \toprule
  $M_d$ (kN·m) & $N_d$ (kN) & $\sigma_{c,0,d}$ (MPa) & $\sigma_{m,d}$ (MPa) & $k_c$ \\
  \midrule
""" + \
    f"  {r_viga.get('M_max_kNm',0):.2f} & " + \
    f"{r_viga.get('N_d_kN',0):.2f} & " + \
    f"{r_viga.get('sigma_c_MPa',0):.4f} & " + \
    f"{r_viga.get('sigma_m_MPa',0):.4f} & " + \
    f"{r_viga.get('k_c_y',0):.4f} \\\\\n" + \
r"""  \bottomrule
\end{tabular}

% ── 8. Verificações ELU -- Pilares ────────────────────────────
\section*{8. Verificações ELU -- Pilares}

Compressão simples EC5~\S6.3.2; $l_{ef}=1{,}0\cdot H$ (rótulas nas extremidades).

\begin{tabular}{llllllc}
  \toprule
  \textbf{Pilar} & Secção (m) & $N_d$ (kN) & $\lambda$ & $\lambda_{rel}$ & $k_c$ & $\eta$ \\
  \midrule
  Lateral & """ + \
    f"{r_pilar.get('b_m', 0.22):.2f}$\\times${r_pilar.get('h_m', 0.26):.2f} & " + \
    f"{r_pilar.get('N_d_kN', 0):.2f} & " + \
    f"{r_pilar.get('lambda', 0):.1f} & " + \
    f"{r_pilar.get('lambda_rel', 0):.4f} & " + \
    f"{r_pilar.get('k_c', 0):.4f} & " + \
    f"\\textcolor{{{'etaok' if _ok(r_pilar) else 'etaerr'}}}{{{_eta(r_pilar):.4f}}} \\\\\n" + \
r"""  Central ($N\approx 2R_v$) & """ + \
    f"{r_pc.get('b_m', 0.28):.2f}$\\times${r_pc.get('h_m', 0.28):.2f} & " + \
    f"{r_pc.get('N_d_kN', 0):.2f} & " + \
    f"{r_pc.get('lambda', 0):.1f} & " + \
    f"{r_pc.get('lambda_rel', 0):.4f} & " + \
    f"{r_pc.get('k_c', 0):.4f} & " + \
    f"\\textcolor{{{'etaok' if _ok(r_pc) else 'etaerr'}}}{{{_eta(r_pc):.4f}}} \\\\\n" + \
r"""  \bottomrule
\end{tabular}

% ── 9. Contraventamento / integridade da cobertura ────────────
\section*{9. Contraventamento -- Integridade Estrutural da Cobertura}

O contraventamento horizontal \textbf{não é acessório}: é o que torna as
terças apoios laterais válidos da viga principal. Sem ele, a hipótese
$l_{ef}=0{,}9s$ da flambagem lateral (EC5~\S6.3.3) deixa de ser legítima.

\textbf{Cadeia de forças (plano da cobertura):}
\begin{enumerate}
  \item Viga MLC comprimida ($N$ + $M$) gera força de estabilização
        (EC5~\S9.2.5).
  \item Terças actuam como \textbf{bielas} (compressão + rigidez $EA/L$).
  \item Cruzes de St.~André nos módulos extremos (diagonal tracionada).
  \item Reacções no pórtico de extremidade $\rightarrow$ fundação.
\end{enumerate}

\vspace{4pt}
\textbf{9.1 Compressão a estabilizar e sistema (EC5~\S9.2.5)}

\begin{tabular}{lll}
  \toprule
  \textbf{Parâmetro} & \textbf{Valor} & \textbf{Ref.} \\
  \midrule
  $N_{axial}$ (biarticulada) & """ + _br(r_cv.get("N_axial_kN", 0), 2) + r"""~kN & Análise \\
  $N_{flex}=(1-k_{crit})M_d/h$ & """ + _br(r_cv.get("N_flex_kN", 0), 2) + r"""~kN & \S9.2.5.2 \\
  $N_d$ (estabilizar) & """ + _br(r_cv.get("N_d_kN", 0), 2) + r"""~kN & \\
  N.º de vigas $n$ & """ + f"{int(r_cv.get('n_vigas', 0))}" + r""" & 9 eixos $\times$ 2 pórticos \\
  $\ell$ (vão do sistema) & """ + _br(r_cv.get("ell_m", 46), 1) + r"""~m & Entre baías rígidas \\
  $k_\ell=\min(1,\sqrt{15/\ell})$ & """ + _br(r_cv.get("k_ell", 0), 3) + r""" & \S9.2.5.3 \\
  $q_d=k_\ell n N_d/(k_{f,3}\ell)$ & """ + _br(r_cv.get("q_d_kNpm", 0), 4) + r"""~kN/m &
    $k_{f,3}=""" + _br(r_cv.get("k_f3", 50), 0) + r"""$ \\
  $R_{ext}=q_d\ell/2$ & """ + _br(r_cv.get("R_ext_kN", 0), 2) + r"""~kN & Por extremo \\
  $a$ (restrição na viga) & """ + _br(r_cv.get("a_restricao_m", s_m), 2) + r"""~m & $=s$ \\
  $F_d=N_d/k_{f,2}$ (por apoio) & """ + _br(r_cv.get("F_d_apoio_kN", 0), 3) + r"""~kN &
    $k_{f,2}=""" + _br(r_cv.get("k_f2", 80), 0) + r"""$ (MLC) \\
  $C_{\min}=k_s N_d/a$ & """ + _br(r_cv.get("C_min_kNpm", 0), 1) + r"""~kN/m &
    $k_s=""" + _br(r_cv.get("k_s", 4), 0) + r"""$ \\
  \bottomrule
\end{tabular}

\vspace{4pt}
\textbf{9.2 Diagonal de aço (EN~1993-1-1~\S6.2.3)}

\begin{tabular}{lll}
  \toprule
  \textbf{Parâmetro} & \textbf{Valor} & \textbf{Obs.} \\
  \midrule
  Layout & Cruzes nos """ + \
    str(r_cv.get("posicao", "2 modulos extremos")).replace("ℓ", r"$\ell$") + r""" & \\
  Painel & """ + _br(r_cv.get("L_panel_m", 5.75), 2) + r"""$\times$""" + \
    _br(r_cv.get("s_terca_m", s_m), 2) + r"""~m &
    $d_{diag}=""" + _br(r_cv.get("d_diag_m", 0), 3) + r"""$~m,
    $\theta=""" + _br(r_cv.get("theta_deg", 0), 1) + r"""$° \\
  Barra & $\varnothing$""" + f"{r_cv.get('d_barra_mm', 16):.0f}" + r"""~mm """ + \
    f"{r_cv.get('aco', 'S235')}" + r""" &
    $A=""" + _br(r_cv.get("A_mm2", 0), 1) + r"""$~mm² \\
  $F_{diag}$ & """ + _br(r_cv.get("F_diag_kN", 0), 2) + r"""~kN & Tração (1 diagonal activa) \\
  $N_{t,Rd}$ & """ + _br(r_cv.get("N_t_Rd_kN", 0), 2) + r"""~kN & $A f_y/\gamma_{M0}$ \\
  $\eta_N$ (diagonal) & """ + \
    f"\\textcolor{{{'etaok' if r_cv.get('ok_diag', False) else 'etaerr'}}}{{{_eta(r_cv, 'eta_diag_N'):.4f}}}" + \
r""" & \\
  \bottomrule
\end{tabular}

\vspace{4pt}
\textbf{9.3 Flecha do sistema e terça-biela}

\begin{tabular}{lll}
  \toprule
  \textbf{Verificação} & \textbf{Valor} & $\boldsymbol{\eta}$ \\
  \midrule
  $\delta\leq\ell/500$ (rigidez global) &
    """ + f"{r_cv.get('delta_mm', 0):.2f}" + r"""~mm $\leq$ """ + \
    f"{r_cv.get('delta_lim_mm', 0):.1f}" + r"""~mm & """ + \
    f"\\textcolor{{{'etaok' if r_cv.get('ok_delta', False) else 'etaerr'}}}{{{_eta(r_cv, 'eta_delta'):.4f}}}" + \
r""" \\
  Terça-biela $N_{Ed}/N_{Rd}$ (EC5~\S6.3.2) &
    $F=""" + _br(r_cv.get("F_terca_kN", 0), 2) + r"""$~kN,
    $N_{Rd}=""" + _br(r_ter_biela.get("N_Rd_kN", 0), 1) + r"""$~kN & """ + \
    f"\\textcolor{{{'etaok' if r_cv.get('ok_terca', False) else 'etaerr'}}}{{{_eta(r_cv, 'eta_terca'):.4f}}}" + \
r""" \\
  Rigidez terça $EA/L\geq C_{\min}$ &
    """ + _br(r_cv.get("C_terca_kNpm", 0), 0) + r""" $\geq$ """ + \
    _br(r_cv.get("C_min_kNpm", 0), 0) + r"""~kN/m & """ + \
    f"\\textcolor{{{'etaok' if r_cv.get('ok_C_terca', False) else 'etaerr'}}}{{{_eta(r_cv, 'eta_C_terca'):.4f}}}" + \
r""" \\
  \bottomrule
\end{tabular}

\vspace{4pt}
\textbf{9.4 Função estrutural da cobertura (acoplamento ao LTB)}

\begin{tabular}{ll}
  \toprule
  \textbf{Indicador} & \textbf{Resultado} \\
  \midrule
  $\mathtt{cobertura\_ok}$ & """ + (
    r"\textcolor{etaok}{\textbf{SIM}}" if cob_ok
    else r"\textcolor{etaerr}{\textbf{NÃO}}"
) + r""" \\
  Restrição lateral das terças & """ + cob_txt + r""" para LTB \\
  $l_1$ efectivo adoptado & """ + _br(l_1_ef, 3) + r"""~m \\
  $\eta$ governante (contravent.) & """ + \
    f"\\textcolor{{{'etaok' if _ok(r_cv) else 'etaerr'}}}{{{_eta(r_cv):.4f}}}" + \
    r""" \quad(""" + str(r_cv.get("eta_gov_key", "--")).replace("_", r"\_") + r""") \\
  Quantitativo & """ + f"{int(r_cv.get('n_barras', 0))}" + r""" barras $\times$ """ + \
    _br(r_cv.get("L_barra_m", 0), 2) + r"""~m $=$ """ + \
    _br(r_cv.get("L_total_m", 0), 1) + r"""~m
    (""" + _br(r_cv.get("peso_total_kg", 0), 1) + r"""~kg) \\
  \bottomrule
\end{tabular}

\vspace{4pt}
\textit{Nota:} vento no sentido do comprimento do galpão (eixo~$Y$) e
contraventamento vertical de frontões \textbf{não} estão neste módulo --
são sistema global distinto. Aqui trata-se apenas da estabilização das
vigas e da integridade do plano da cobertura (EC5~\S9.2.5).

% ── 10. Verificações ELS ──────────────────────────────────────
\section*{10. Verificações ELS -- Flechas}

\begin{tabular}{lllcc}
  \toprule
  \textbf{Verificação} & \textbf{Valor} & \textbf{Limite} & $\boldsymbol{\eta}$ & \\
  \midrule
  $w_{inst}(S1) \leq L/300$ & """ + \
    f"{r_els.get('w_S1_mm',0):.2f}~mm & " + \
    f"{r_els.get('lim_inst_mm',67.5):.2f}~mm & " + \
    f"\\textcolor{{{cor_S1}}}{{{eta_S1:.4f}}} & " + \
    f"\\textcolor{{{cor_S1}}}{{{sim_S1}}} \\\\\n" + \
r"""  $w_{net,fin} \leq L/250$ & """ + \
    f"{r_els.get('w_net_fin_mm',0):.2f}~mm & " + \
    f"{r_els.get('lim_fin_mm',81.0):.2f}~mm & " + \
    f"\\textcolor{{{cor_nf}}}{{{eta_nf:.4f}}} & " + \
    f"\\textcolor{{{cor_nf}}}{{{sim_nf}}} \\\\\n" + \
r"""  \bottomrule
\end{tabular}

\vspace{4pt}
""" + (
    f"Fluência (EC5~\\S2.3.2.2): "
    f"$w_{{fin}} = {r_els.get('w_G_mm', 0):.2f}"
    f"(1+{k_def:.2f}) + {r_els.get('w_Q1_mm', 0):.2f}"
    f" = {r_els.get('w_fin_mm', 0):.2f}$~mm "
    f"($k_{{def}}={k_def:.2f}$, $\\psi_2=0$).\n\n"
) + r"""
% ── 11. Ligações ──────────────────────────────────────────────
\section*{11. Ligações}

\textit{Critério de projecto (uso público):} $\eta_{\mathrm{alvo}}=""" + \
    _br(float(meta.get("eta_lig_alvo", r_L1.get("eta_alvo", 0.85))), 2) + \
r"""$ para L1/L1c e L3 (ligações em madeira tendem a falha frágil;
EC5 exige $\eta\leq 1{,}0$ -- o alvo 0{,}85 é margem de projecto).
$n_{ef}$ por fileira // fibras: EC5~\S8.5.1.1
($n_{ef}=n^{0,9}(a_1/(13d))^{1/4}\leq n$).

\vspace{4pt}
\begin{tabular}{p{4.5cm}p{5cm}cc}
  \toprule
  \textbf{Ligação} & \textbf{Norma} & $\boldsymbol{\eta}$ & \textbf{Status} \\
  \midrule
""" + \
    eta_row(
        "L1 -- Viga-pilar (base)",
        "EC5 \\S8.2+\\S8.5.1.1+\\S8.6",
        _eta(r_L1), _ok(r_L1),
    ) + \
    eta_row(
        "L2 -- Cumeeira",
        "EC5 \\S6.1.4+\\S6.1.5+\\S8.6",
        _eta(r_L2), _ok(r_L2),
    ) + \
    eta_row(
        "L3 -- Sapata (fundação)",
        "EN 1993-1-8+EN 1992-4",
        _eta(r_L3), _ok(r_L3),
    ) + \
    eta_row(
        "L1c -- Base pilar central",
        "EC5 \\S8.2+\\S8.3+\\S8.6",
        _eta(r_L1c), _ok(r_L1c),
    ) + \
    eta_row(
        "L2c -- Cumeeira central",
        "EC5 \\S6.1.4+\\S6.1.5+\\S8.6",
        _eta(r_L2c), _ok(r_L2c),
    ) + \
    eta_row(
        "L3c -- Sapata central",
        "EN 1993-1-8+EN 1992-4",
        _eta(r_L3c), _ok(r_L3c),
    ) + \
r"""  \bottomrule
\end{tabular}

\vspace{4pt}
\begin{tabular}{llll}
  \toprule
  \textbf{Ligação} & \textbf{Detalhe} & \textbf{Parâmetro} & \textbf{Valor} \\
  \midrule
  L1 -- Viga-pilar & Pinos em chapa embutida &
    $d$, $n$, layout &
    """ + \
    f"{r_L1.get('d_mm', 0):.0f}~mm, {r_L1.get('n_pinos', 0)}, " + \
    f"{r_L1.get('n_linha', 0)}$\\times${r_L1.get('n_linhas', 0)} \\\\\n" + \
r"""  & & $F_{v,Rd}/\text{pino}$ (2 planos) & """ + \
    f"{r_L1.get('F_v_Rd_kN', 0):.3f}~kN \\\\\n" + \
r"""  & & $n_{ef,row}$, $n_{ef}$ total & """ + \
    f"{r_L1.get('n_ef_row', 0):.2f} (de {r_L1.get('n_linha', 0)}), " + \
    f"{r_L1.get('n_ef', 0):.2f} \\\\\n" + \
r"""  & & $R_{total}$, $F_{res}$ & """ + \
    f"{r_L1.get('R_total_kN', 0):.1f}~kN, " + \
    f"{r_L1.get('F_res_kN', 0):.1f}~kN \\\\\n" + \
r"""  & & $\eta$, $\eta_{alvo}$ & """ + \
    f"{_eta(r_L1):.4f}, {r_L1.get('eta_alvo', 0.85):.2f} \\\\\n" + \
r"""  \midrule
  L2 -- Cumeeira & Pino passante & $d$, $n$ & """ + (
    f"{r_L2.get('d_pino_mm', r_L2.get('d_mm', 0)):.0f}~mm, "
    f"{r_L2.get('n_pino', r_L2.get('n_pinos', 0))} \\\\\n"
) + \
r"""  & Compressão axial & $\sigma_{c,0,d}$ & """ + \
    f"{r_L2.get('sigma_c0_MPa', 0):.4f}~MPa \\\\\n" + \
r"""  & & $\eta$ & """ + \
    f"{_eta(r_L2):.4f} \\\\\n" + \
r"""  \midrule
  L3 -- Sapata & Chumbadores & $n$, $F_{chu}$ & """ + (
    f"{r_L3.get('n_chumbadores', 0)}, "
    f"{r_L3.get('F_chu_kN', 0):.0f}~kN/chu \\\\\n"
) + \
r"""  & Chapa de base & Dimensões & """ + (
    f"{r_L3.get('lado_chapa_cm', 0):.1f}$\\times$"
    f"{r_L3.get('lado_chapa_cm', 0):.1f}~cm \\\\\n"
) + \
r"""  & & $H_d$, $\eta$, $\eta_{alvo}$ & """ + \
    f"{r_L3.get('H_d_kN', 0):.1f}~kN, {_eta(r_L3):.4f}, " + \
    f"{r_L3.get('eta_alvo', 0.85):.2f} \\\\\n" + \
r"""  \midrule
  L1c -- Central & 2 chapas independentes &
    $d$, $n$/chapa, layout &
    """ + (
    f"{r_L1c.get('d_mm', 0):.0f}~mm, {r_L1c.get('n_pinos', 0)}, "
    f"{r_L1c.get('n_linha', 0)}$\\times${r_L1c.get('n_linhas', 0)} \\\\\n"
) + \
r"""  & & $\eta$ & """ + \
    f"{_eta(r_L1c):.4f} \\\\\n" + \
r"""  \midrule
  L3c -- Sapata central & Chumbadores (H$\approx$0) & $n$ & """ + \
    f"{r_L3c.get('n_chumbadores', 0)} \\\\\n" + \
r"""  \bottomrule
\end{tabular}

\vspace{6pt}
\subsection*{11.1 Fadiga e deslizamento (EC5 \S7.1 + \S8.1.5)}

\begin{tabular}{llcccc}
  \toprule
  \textbf{Lig.} & \textbf{Descrição} & $u_{inst}$ & $u_{fin}$ &
  $\eta_{slip}$ & $\eta_{alt}$ \\
  \midrule
""" + (
    f"  L1 & {r_fL1.get('descricao', 'Base lateral')} & "
    f"{r_fL1.get('u_inst_mm', 0):.3f}~mm & "
    f"{r_fL1.get('u_fin_mm', 0):.3f}~mm & "
    f"{_eta(r_fL1, 'eta_slip'):.4f} & "
    f"{_eta(r_fL1, 'eta_alt'):.4f} \\\\\n"
    f"  L2 & {r_fL2.get('descricao', 'Cumeeira')} & "
    f"{r_fL2.get('u_inst_mm', 0):.3f}~mm & "
    f"{r_fL2.get('u_fin_mm', 0):.3f}~mm & "
    f"{_eta(r_fL2, 'eta_slip'):.4f} & "
    f"{_eta(r_fL2, 'eta_alt'):.4f} \\\\\n"
    f"  L1c & {r_fL1c.get('descricao', 'Base central')} & "
    f"{r_fL1c.get('u_inst_mm', 0):.3f}~mm & "
    f"{r_fL1c.get('u_fin_mm', 0):.3f}~mm & "
    f"{_eta(r_fL1c, 'eta_slip'):.4f} & "
    f"{_eta(r_fL1c, 'eta_alt'):.4f} \\\\\n"
) + \
r"""  \bottomrule
\end{tabular}

% ── 12. Resumo ────────────────────────────────────────────────
\section*{12. Resumo das Taxas de Utilização}

\begin{tabular}{llcc}
  \toprule
  \textbf{Verificação} & \textbf{Norma} & $\boldsymbol{\eta}$ & \textbf{Status} \\
  \midrule
""" + \
    eta_row("Cumeeira ($t_{90}$, $M\\neq 0$)", "EC5 \\S6.4.3",   _eta(r_cum),  _ok(r_cum, True)) + \
    eta_row("Flambagem lateral",         "EC5 \\S6.3.3",           _eta(r_fl),   _ok(r_fl)) + \
    eta_row("Flexo-comp. viga",          "EC5 \\S6.3.2",           _eta(r_fx),   _ok(r_fx)) + \
    eta_row("Cisalhamento",              "EC5 \\S6.1.7",           _eta(r_ci),   _ok(r_ci)) + \
    eta_row("Apoio",                     "EC5 \\S6.1.5+\\S6.2.2",  _eta(r_ap),   _ok(r_ap)) + \
    eta_row("Pilar lateral",             "EC5 \\S6.3.2",           _eta(r_pilar),_ok(r_pilar)) + \
    eta_row("Pilar central",             "EC5 \\S6.3.2",           _eta(r_pc),   _ok(r_pc)) + \
    eta_row("Cobertura / contravent.",   "EC5 \\S9.2.5",           _eta(r_cv),   _ok(r_cv)) + \
    eta_row("Terça (flexão)",            "EC5 \\S6.1.6+\\S6.1.7",  _eta(r_ter),  _ok(r_ter)) + \
    eta_row("ELS -- flechas",            "EC5 \\S2.3.2.2",         _eta(r_els),  _ok(r_els)) + \
    eta_row("L1 -- Viga-pilar",          "EC5 \\S8.2+\\S8.6",      _eta(r_L1),   _ok(r_L1)) + \
    eta_row("L2 -- Cumeeira",            "EC5 \\S8.6",             _eta(r_L2),   _ok(r_L2)) + \
    eta_row("L3 -- Sapata",              "EN 1993-1-8",            _eta(r_L3),   _ok(r_L3)) + \
    eta_row("L1c -- Base central",       "EC5 \\S8.2+\\S8.6",      _eta(r_L1c),  _ok(r_L1c)) + \
    eta_row("L2c -- Cumeeira central",   "EC5 \\S8.6",             _eta(r_L2c),  _ok(r_L2c)) + \
    eta_row("L3c -- Sapata central",     "EN 1993-1-8",            _eta(r_L3c),  _ok(r_L3c)) + \
    eta_row("Fadiga L1 ($\\eta_{slip}$)", "EC5 \\S7.1",            _eta(r_fL1),  _ok(r_fL1)) + \
    eta_row("Fadiga L2 ($\\eta_{slip}$)", "EC5 \\S7.1",            _eta(r_fL2),  _ok(r_fL2)) + \
    eta_row("Fadiga L1c ($\\eta_{slip}$)","EC5 \\S7.1",            _eta(r_fL1c), _ok(r_fL1c)) + \
r"""  \midrule
  \multicolumn{2}{l}{\textbf{$\eta$ máximo}} &
  \multicolumn{2}{c}{\textbf{""" + f"{eta_max:.4f}" + r"""}} \\
  \bottomrule
\end{tabular}

\vspace{10pt}
\hrule
\vspace{4pt}
{\small Calculado por pipeline automatizado em Python -- EC5 + EN 1990 + NBR 6123.
Todos os valores conferidos pelo Eng.\ Resp.\ antes da emissão.}

\end{document}
"""

    tex_path.write_text(tex, encoding="utf-8")
    return tex_path


def compilar_pdf(tex_path: Path) -> bool:
    """Tenta compilar o .tex para PDF com pdflatex."""
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             "-output-directory", str(tex_path.parent),
             str(tex_path)],
            capture_output=True, timeout=60
        )
        # Rodar duas vezes para referências cruzadas
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             "-output-directory", str(tex_path.parent),
             str(tex_path)],
            capture_output=True, timeout=60
        )
        pdf_path = tex_path.with_suffix(".pdf")
        return pdf_path.exists()
    except (FileNotFoundError, subprocess.TimeoutExpired):
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
            "η":           round(float(res["eta"]), 4),
            "OK":          "✓" if res.get("ok") else "✗",
        })

    df = pd.DataFrame(linhas)
    xlsx_path = OUTPUT_DIR / f"{nome}.xlsx"
    df.to_excel(xlsx_path, index=False)
    print(f"  Excel: {xlsx_path}")

    # ── LaTeX ─────────────────────────────────────────────────
    tex_path = gerar_tex(resultados, geo, mat, nome, load=load)
    print(f"  LaTeX: {tex_path}")

    # ── PDF (se pdflatex disponível) ──────────────────────────
    ok_pdf = compilar_pdf(tex_path)
    if ok_pdf:
        print(f"  PDF  : {tex_path.with_suffix('.pdf')}")
    else:
        print(f"  PDF  : pdflatex não encontrado -- "
              f"compilar manualmente: pdflatex {tex_path.name}")


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
    from mlc_projeto.core.loads     import carregamentos_com_vento
    from mlc_projeto.checks.elu.cumeeira          import verifica_cumeeira
    from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral
    from mlc_projeto.checks.elu.flexao            import verifica_flexao
    from mlc_projeto.checks.elu.cisalhamento      import verifica_cisalhamento
    from mlc_projeto.checks.elu.apoio             import verifica_apoio
    from mlc_projeto.checks.elu.flexo_compressao  import verifica_flexo_compressao
    from mlc_projeto.checks.els.deflection_els    import verificar_ELS
    from mlc_projeto.connections.connections      import dimensionar_ligacoes

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial("GL24h", 2, "curta")
    mat_l = GlulamMaterial("GL24h", 2, "longa")

    params = ParametrosVento(V0=45,S1=1,categoria="IV",classe="B",
                              S3=1,L=20.25,H1=1,h=7,dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo,mat=mat,g_area=1.5,q_area=0.25,
                                    L_t=5.75,params_vento=params)

    fc  = verifica_flexo_compressao(geo,mat,load,0.20,0.20,7.0,1.0)
    lig = dimensionar_ligacoes(mat,load,geo,20,30,80)

    resultados = {
        "cumeeira":    verifica_cumeeira(geo,mat,load),
        "flambagem":   verifica_flambagem_lateral(geo,mat,load,1.0),
        "flexao":      verifica_flexao(geo,mat,load,1.0),
        "cisalhamento":verifica_cisalhamento(geo,mat,load),
        "apoio":       verifica_apoio(geo,mat,load,0.50),
        "flexo_comp":  fc,
        "ELS":         verificar_ELS(geo,mat_l,load),
        "L1":          lig["L1"],
        "L2":          lig["L2"],
        "L3":          lig["L3"],
    }

    gerar_relatorio(resultados, geo, mat, "memorial_mlc")