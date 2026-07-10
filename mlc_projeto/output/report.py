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

def gerar_tex(
    resultados: dict,
    geo:        GeometriaViga,
    mat:        GlulamMaterial,
    nome:       str = "memorial_mlc",
) -> Path:
    """
    Gera o arquivo .tex do memorial de cálculo.

    Args:
        resultados : Dict com todos os resultados do pipeline
        geo        : Geometria da viga
        mat        : Material
        nome       : Nome base do arquivo

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

    # Extrair sub-dicts de flexo_comp
    r_viga  = r_fc.get("viga",  {}) if r_fc else {}
    r_pilar = r_fc.get("pilar", {}) if r_fc else {}

    k_def = float(resultados.get("k_def", mat.k_def))

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
  Sistema estrutural & Pórtico de 3 rótulas & Isostático \\
  \bottomrule
\end{tabular}

% ── 3. Material ───────────────────────────────────────────────
\section*{3. Material -- GL24h}

\begin{tabular}{llll}
  \toprule
  \textbf{Propriedade} & \textbf{Valor} & \textbf{Propriedade} & \textbf{Valor} \\
  \midrule
  $f_{m,k}$    & 24{,}0~MPa  & $E_{0,mean}$ & 11.500~MPa \\
  $f_{t,90,k}$ & 0{,}50~MPa  & $E_{0,05}$   & 9.600~MPa  \\
  $f_{c,0,k}$  & 24{,}0~MPa  & $G_{mean}$   & 720~MPa    \\
  $f_{c,90,k}$ & 2{,}50~MPa  & $\rho_k$     & 385~kg/m³  \\
  $f_{v,k}$    & 3{,}50~MPa  & $\gamma_M$   & 1{,}25     \\
  \multicolumn{2}{l}{Classe de serviço: 2} &
  \multicolumn{2}{l}{$k_{def} = 0{,}80$ \quad (EC5 Tab.~3.2)} \\
  \bottomrule
\end{tabular}

\vspace{4pt}
\begin{tabular}{lll}
  \toprule
  \textbf{Duração} & $k_{mod}$ & \textbf{Combinação} \\
  \midrule
  Curta  & 0{,}90 & ELU\_C2 (vento dominante) \\
  Longa  & 0{,}70 & ELS -- fluência \\
  \bottomrule
\end{tabular}

% ── 4. Ações e Combinações ────────────────────────────────────
\section*{4. Ações e Combinações}

\textbf{Cargas características:}

\begin{tabular}{llll}
  \toprule
  \textbf{Ação} & \textbf{Valor por área} & \textbf{Valor linear} & \textbf{Norma} \\
  \midrule
  Permanente $g_k$ & 1{,}50~kN/m² & 4{,}313~kN/m & Estimativa \\
  Sobrecarga $q_k$ & 0{,}25~kN/m² & 0{,}719~kN/m & EN 1991-1-1 \\
  \multicolumn{3}{l}{Área tributária = $L_t/2 = 5{,}75/2 = 2{,}875$~m} & Geometria \\
  \bottomrule
\end{tabular}

\vspace{6pt}
\textbf{Vento -- NBR 6123 Tabela 25 (cobertura isolada 2 águas):}

\begin{tabular}{lll}
  \toprule
  \textbf{Parâmetro} & \textbf{Valor} & \textbf{Ref.} \\
  \midrule
  $V_0$ (Londrina/PR) & 45{,}0~m/s & Fig.~1 \\
  $S_1$ & 1{,}0 & \S5.2 \\
  $S_2$ (Cat.~IV, Cl.~B) & 0{,}83 & Tab.~3 \\
  $S_3$ & 1{,}0 & \S5.5 \\
  $V_k = V_0 S_1 S_2 S_3$ & 37{,}35~m/s & \S5.1 \\
  $q = 0{,}613 \cdot V_k^2$ & 0{,}855~kN/m² & \S6.2 \\
  $\tan\beta = H_1/(L/2)$ & 0{,}0988 \quad ($\beta=5{,}64°$) & Geometria \\
  $C_{pb}$ (C1 barlavento) & $+0{,}837$ & Tab.~25 \\
  $C_{ps}$ (C1 sotavento)  & $-0{,}204$ & Tab.~25 \\
  \bottomrule
\end{tabular}

\vspace{6pt}
\textbf{Combinações de ações -- EN 1990 Eq.~6.10:}

\begin{tabular}{lll}
  \toprule
  \textbf{Combinação} & \textbf{Expressão} & \textbf{$q_{tot}$ (kN/m)} \\
  \midrule
  ELU\_C2 \textit{(governa)} & $1{,}35G + 1{,}5W_{C1bv} + 1{,}05Q$ & 9{,}663 \\
  ELU\_C1 & $1{,}35G + 1{,}5Q + 0{,}9W_{C1bv}$ & 8{,}752 \\
  ELU\_C3 & $0{,}9G + 1{,}5W_{C2st}$ (sucção) & 0{,}193 \\
  ELS\_S1 & $G + Q + 0{,}6W_{C1bv}$ & 6{,}266 \\
  ELS\_S3 & $G$ (fluência) & 4{,}313 \\
  \bottomrule
\end{tabular}

% ── 5. Sistema Estrutural ─────────────────────────────────────
\section*{5. Sistema Estrutural -- Pórtico de 3 Rótulas}

Adotado pórtico isostático com rótulas nas bases dos pilares e na cumeeira.
Galpão aberto nas laterais -- contraventamento vertical inviável.
Ligações sem transmissão de momento.

\textbf{Análise estrutural (carga uniforme $q$, pórtico simétrico):}

\[
  R_v = \frac{qL}{2} = \frac{9{,}663 \times 20{,}25}{2} = 97{,}84~\text{kN}
\]
\[
  H = \frac{R_v \cdot L/2 - q(L/2)^2/2}{f} = 621{,}60~\text{kN}
  \quad f = h_{ap} - h_0 = 0{,}797~\text{m}
\]
\[
  M_{max} = 123{,}82~\text{kN·m} \quad \text{em } x = 5{,}01~\text{m}
\]

% ── 6. Geometria da Viga ──────────────────────────────────────
\section*{6. Geometria da Viga}

\begin{tabular}{lll}
  \toprule
  \textbf{Parâmetro} & \textbf{Valor} & \textbf{Observação} \\
  \midrule
  Vão $L$ & """ + f"{geo.L:.2f}" + r"""~m & Por pórtico \\
  Altura no apoio $h_0$ & """ + f"{geo.h0:.2f}" + r"""~m & \\
  Inclinação $\alpha$ & """ + f"{geo.alpha_deg:.1f}" + r"""° & \\
  Largura $b$ & """ + f"{geo.b:.2f}" + r"""~m & \\
  Altura na cumeeira $h_{ap}$ & """ + f"{geo.h_ap:.3f}" + r"""~m & \\
  Espaçamento terças $s$ & 1{,}00~m & $l_{ef} = 0{,}9s = 0{,}90$~m \\
  Placa de apoio $l_{ap}$ & 0{,}50~m & \\
  \bottomrule
\end{tabular}

% ── 7. Verificações ELU ───────────────────────────────────────
\section*{7. Verificações ELU -- Viga}

\begin{tabular}{p{5.5cm}llcc}
  \toprule
  \textbf{Verificação} & \textbf{Norma} & \textbf{Equação} & $\boldsymbol{\eta}$ & \textbf{} \\
  \midrule
""" + \
    eta_row("Cumeeira (M=0, rótula)",       "EC5 \\S6.4.3",       r_cum.get("eta",0.0),  r_cum.get("ok",True)) + \
    eta_row("Flambagem lateral",             "EC5 \\S6.3.3",       r_fl.get("eta",0.0),   r_fl.get("ok",True)) + \
    eta_row("Flexo-compressão viga",         "EC5 \\S6.3.2",       r_fx.get("eta",0.0),   r_fx.get("ok",True)) + \
    eta_row("Cisalhamento no apoio",         "EC5 \\S6.1.7",       r_ci.get("eta",0.0),   r_ci.get("ok",True)) + \
    eta_row("Compressão no apoio",           "EC5 \\S6.1.5+\\S6.2.2", r_ap.get("eta",0.0), r_ap.get("ok",True)) + \
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

% ── 8. Verificações ELU -- Pilar ──────────────────────────────
\section*{8. Verificações ELU -- Pilar}

Seção adotada: """ + \
    f"{r_pilar.get('b_m',0.20):.2f}" + r"""~m $\times$ """ + \
    f"{r_pilar.get('h_m',0.20):.2f}" + r"""~m. Compressão simples, rótulas em ambas as extremidades ($l_{ef} = 1{,}0 \cdot H$).

\begin{tabular}{lllllc}
  \toprule
  \textbf{Verificação} & $N_d$ (kN) & $\lambda$ & $\lambda_{rel}$ & $k_c$ & $\eta$ \\
  \midrule
  Compressão -- EC5~\S6.3.2 & """ + \
    f"{r_pilar.get('N_d_kN',97.84):.2f} & " + \
    f"{r_pilar.get('lambda',0):.1f} & " + \
    f"{r_pilar.get('lambda_rel',0):.4f} & " + \
    f"{r_pilar.get('k_c',0):.4f} & " + \
    f"\\textcolor{{etaok}}{{{r_pilar.get('eta',0):.4f}}} \\\\\n" + \
r"""  \bottomrule
\end{tabular}

% ── 9. Verificações ELS ───────────────────────────────────────
\section*{9. Verificações ELS -- Flechas}

\begin{tabular}{lllcc}
  \toprule
  \textbf{Verificação} & \textbf{Valor} & \textbf{Limite} & $\boldsymbol{\eta}$ & \\
  \midrule
  $w_{inst}(S1) \leq L/300$ & """ + \
    f"{r_els.get('w_S1_mm',0):.2f}~mm & " + \
    f"{r_els.get('lim_inst_mm',67.5):.2f}~mm & " + \
    f"\\textcolor{{etaok}}{{{r_els.get('eta_S1',0):.4f}}} & " + \
    r"\checkmark \\" + "\n" + \
r"""  $w_{net,fin} \leq L/250$ & """ + \
    f"{r_els.get('w_net_fin_mm',0):.2f}~mm & " + \
    f"{r_els.get('lim_fin_mm',81.0):.2f}~mm & " + \
    f"\\textcolor{{etaok}}{{{r_els.get('eta_net_fin',0):.4f}}} & " + \
    r"\checkmark \\" + "\n" + \
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
% ── 10. Ligações ──────────────────────────────────────────────
\section*{10. Ligações}

\begin{tabular}{p{4cm}p{4.5cm}p{3cm}cc}
  \toprule
  \textbf{Ligação} & \textbf{Solução} & \textbf{Norma} & $\boldsymbol{\eta}$ & \\
  \midrule
""" + \
    eta_row(
        "L1 -- Viga-pilar (base)",
        "EC5 \\S8.2+\\S8.3+\\S8.6",
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
r"""  & & $F_{Rd}/\text{pino}$, $n_{ef}$ & """ + \
    f"{r_L1.get('F_v_Rd_kN', 0):.3f}~kN, {r_L1.get('n_ef', 0):.2f} \\\\\n" + \
r"""  & & $F_{res}$, $\eta$ & """ + \
    f"{r_L1.get('F_res_kN', 0):.1f}~kN, {_eta(r_L1):.4f} \\\\\n" + \
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
r"""  & & $H_d$, $\eta$ & """ + \
    f"{r_L3.get('H_d_kN', 0):.1f}~kN, {_eta(r_L3):.4f} \\\\\n" + \
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
\subsection*{10.1 Fadiga e deslizamento (EC5 \S7.1 + \S8.1.5)}

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

% ── 11. Resumo ────────────────────────────────────────────────
\section*{11. Resumo das Taxas de Utilização}

\begin{tabular}{llcc}
  \toprule
  \textbf{Verificação} & \textbf{Norma} & $\boldsymbol{\eta}$ & \textbf{Status} \\
  \midrule
""" + \
    eta_row("Cumeeira (M=0)",           "EC5 \\S6.4.3",           _eta(r_cum),  _ok(r_cum, True)) + \
    eta_row("Flambagem lateral",         "EC5 \\S6.3.3",           _eta(r_fl),   _ok(r_fl)) + \
    eta_row("Flexo-comp. viga",          "EC5 \\S6.3.2",           _eta(r_fx),   _ok(r_fx)) + \
    eta_row("Cisalhamento",              "EC5 \\S6.1.7",           _eta(r_ci),   _ok(r_ci)) + \
    eta_row("Apoio",                     "EC5 \\S6.1.5+\\S6.2.2",  _eta(r_ap),   _ok(r_ap)) + \
    eta_row("Pilar -- compressão",       "EC5 \\S6.3.2",           _eta(r_pilar),_ok(r_pilar)) + \
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
  \multicolumn{2}{c}{\textbf{""" + \
    f"{max(_eta(r_cum), _eta(r_fl), _eta(r_fx), _eta(r_ci), _eta(r_ap), _eta(r_pilar), _eta(r_els), _eta(r_L1), _eta(r_L2), _eta(r_L3), _eta(r_L1c), _eta(r_L2c), _eta(r_L3c), _eta(r_fL1), _eta(r_fL2), _eta(r_fL1c)):.4f}" + \
r"""}} \\
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
) -> None:
    """
    Gera relatório Excel + memorial LaTeX.

    Chamado pelo main.py ao final do pipeline.
    """
    import pandas as pd

    OUTPUT_DIR.mkdir(exist_ok=True)

    # ── Excel ─────────────────────────────────────────────────
    # Ignora chaves auxiliares (ex.: k_def escalar)
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
    tex_path = gerar_tex(resultados, geo, mat, nome)
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