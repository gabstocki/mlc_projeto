"""
output/report.py — Memorial de cálculo em LaTeX (estilo institucional SIA).

Gera o arquivo .tex e compila para PDF se pdflatex estiver disponível.
Layout minimalista: Helvetica, A4, margens 2,5 cm, Booktabs, preto/branco.
"""

from __future__ import annotations

import math
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


# Catálogo único terminal / Excel / resumo LaTeX — mesma ordem e rótulos
# (chave em `resultados`, rótulo de exportação, norma)
VERIFICACOES_EXPORT: list[tuple[str, str, str]] = [
    ("cumeeira",            "Cumeeira t90",              "EC5 §6.4.3"),
    ("misula",              "Mísula face incl. σm,α",    "EC5 §6.4.2"),
    ("flambagem",           "Flambagem lateral",         "EC5 §6.3.3"),
    ("flexao",              "Flexo-comp. viga",          "EC5 §6.3.2+§6.3.3"),
    ("cisalhamento",        "Cisalhamento",              "EC5 §6.1.7"),
    ("apoio",               "Apoio",                     "EC5 §6.1.5+§6.2.2"),
    ("flexo_comp",          "Pilar lateral (N)",         "EC5 §6.3.2"),
    ("pilar_central",       "Pilar central (N)",         "EC5 §6.3.2"),
    ("pilar_vento_0",       "Pilar vento θ=0°",          "NBR 6123+EC5 §6.3.2"),
    ("pilar_vento_90",      "Pilar vento θ=90°",         "NBR 6123+EC5 §6.3.2"),
    ("pilar_contraventado", "Pilar canto (grav+brace+vento)","EC5 §6.2.3+§6.3.2"),
    ("terca",               "Terça flexão",              "EC5 §6.1.6+§6.1.7"),
    ("terca_flexocomp",     "Terça-biela flexo-comp.",   "EC5 §6.3.2 Eq.6.23/6.24"),
    ("terca_Qk_conc",       "Terça Q_k concentrado",     "EN 1991-1-1 Tab.6.10"),
    # [D1] O rótulo dizia "§6.2.5+Tab.5". O BM-17 leu a :2023: §6.2.5 é
    # *Pressões internas* e a Tab. 5 é *altura de camada limite* — nem uma nem
    # outra sustenta c_p = ±2,0 para elementos de vedação. A rota executada pelo
    # módulo é §7.2.6, e é essa que o memorial passa a citar.
    ("fixacao_telha",       "Fixação telha (sucção)",    "NBR 6123 §7.2.6"),
    ("fogo",                "Fogo (seção reduzida)",     "EN 1995-1-2 §4.2.2"),
    ("contraventamento",    "Contraventamento cobertura","EC5 §9.2.5"),
    ("contraventamento_vertical", "Contravento vertical", "EN 1993-1-1 §5.3+§6.2.3"),
    ("contraventamento_transversal", "Contravento transversal", "EN 1993-1-1 §5.3+§6.2.3"),
    ("corda_beiral",        "Corda beiral (diafragma)",  "EC5 §6.2.3+§6.3.2"),
    ("estabilidade_global", "Estabilidade global P-Δ",   "EN 1993-1-1 §5.2+§5.3"),
    ("impacto_veiculo",     "Impacto veículo (A_d)",     "EN 1991-1-7"),
    ("icamento",            "Içamento (montagem)",       "EN 1991-1-6+EC5 §6.3.3"),
    ("ancoragem_canto",     "Ancoragem canto (moldada)", "EN 1993-1-8 + EN 1992-4"),
    ("succao_uplift",       "Sucção/uplift (ancoragem)", "EN 1990+EN 1992-4"),
    ("tirante_base",        "Tirante de base",           "EN 1993-1-1 §6.2.3"),
    ("tirante_piso_robustez","Robustez tirante piso",    "EN 1991-1-7+335+1993-1-2"),
    ("ELS",                 "ELS flechas",               "EC5 §2.3.2.2+Tab.7.2"),
    ("ruptura_bloco_L1",    "Ruptura de bloco L1",       "EC5 Anexo A"),
    ("ruptura_bloco_L1c",   "Ruptura de bloco L1c",      "EC5 Anexo A"),
    ("fendilhamento_L1",    "Fendilhamento L1 (perp.)",  "EC5 §8.1.4 Eq.8.4"),
    ("fendilhamento_L1c",   "Fendilhamento L1c (perp.)", "EC5 §8.1.4 Eq.8.4"),
    ("chapa_aco_L1",        "Chapa aço L1 (furos/solda)","EN 1993-1-8+1-1"),
    ("chapa_aco_L1c",       "Chapa aço L1c (furos/solda)","EN 1993-1-8+1-1"),
    ("L1",                  "Ligação L1 base",           "EC5 §8.2+§8.5.1.1+§8.6"),
    ("L3",                  "Ligação L3 sapata",         "EN 1993-1-8+EN 1992-4"),
    ("L1c",                 "Ligação L1c base central",  "EC5 §8.2+§8.5.1.1+§8.6"),
    ("L3c",                 "Ligação L3c sapata central","EN 1993-1-8+EN 1992-4"),
    ("fadiga_L1",           "Fadiga/slip L1",            "EC5 §7.1+§8.1.5"),
    ("fadiga_L1c",          "Fadiga/slip L1c",           "EC5 §7.1+§8.1.5"),
]

# Chaves que não são verificações η (excluir do Excel automático residual)
_META_KEYS = frozenset({
    "meta", "k_def", "load", "geo", "mat",
})


#: Chaves aceites como taxa de utilização, por ordem de precedência.
_ETA_KEYS = ("eta", "eta_gov", "eta_slip")

#: Estados possíveis de uma linha do resumo.
STATUS_OK            = "OK"
STATUS_REPROVADO     = "REPROVADO"
STATUS_SEM_ETA       = "SEM η"
STATUS_NAO_EXECUTADA = "NÃO EXECUTADA"
STATUS_NAO_APLICAVEL = "NÃO APLICÁVEL"

#: Estados que impedem o carimbo APROVADO (resultado em falta, não em falha).
STATUS_PENDENTES = (STATUS_SEM_ETA, STATUS_NAO_EXECUTADA)


def eta_numerico(res: dict) -> float | None:
    """
    η estritamente numérico e finito, ou ``None`` — achado F-04.

    NUNCA devolve um valor "de segurança". ``None``, texto, ``bool``, ``NaN`` e
    ``±inf`` são AUSÊNCIA de resultado, não η = 0: converter qualquer deles em
    zero transformava uma falha de cálculo em aprovação (o mesmo mecanismo que
    ``core/validacao.py`` proíbe nos dados de entrada).
    """
    for k in _ETA_KEYS:
        if k in res:
            v = res[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return None
            v = float(v)
            return v if math.isfinite(v) else None
    return None


def extrair_eta_ok(res: dict | None) -> tuple[float, bool]:
    """
    Extrai (η, ok) de um dict de verificação.

    Devolve ``(nan, False)`` quando não há η numérico — indeterminado, nunca
    aprovado (F-04).
    """
    if not isinstance(res, dict):
        return float("nan"), False
    eta = eta_numerico(res)
    if eta is None:
        return float("nan"), False
    if "ok" in res:
        ok = bool(res["ok"])
    elif "ok_alvo" in res:
        ok = bool(res["ok_alvo"]) and eta <= 1.0 + 1e-9
    else:
        ok = eta <= 1.0 + 1e-9
    return eta, ok


def _linha_resumo(chave, rotulo, norma, eta, ok, status) -> dict:
    return {
        "chave":       chave,
        "Verificação": rotulo,
        "Norma":       norma,
        "η":           eta if math.isnan(eta) else round(eta, 4),
        "OK":          "✓" if ok else "✗",
        "ok_bool":     ok,
        "status":      status,
    }


def tabela_verificacoes(
    resultados: dict,
    nao_aplicaveis: set[str] | frozenset[str] | None = None,
) -> list[dict]:
    """
    Linhas padronizadas para terminal, Excel e memorial.

    Ordem fixa = ``VERIFICACOES_EXPORT``, **sempre por inteiro** — achado F-04.
    A versão anterior fazia ``continue`` para as chaves ausentes ou sem η, e a
    verificação desaparecia do resumo, do ``all_ok``, do ``eta_max``, do Excel e
    do memorial, sem aviso. Agora cada chave do catálogo produz sempre uma
    linha, com um ``status`` explícito:

        "OK" / "REPROVADO"    — verificação executada, com η numérico
        "SEM η"               — dicionário presente mas sem η utilizável
        "NÃO EXECUTADA"       — chave ausente de `resultados`
        "NÃO APLICÁVEL"       — exclusão DECLARADA pelo chamador

    Args:
        resultados     : dicionário de resultados do pipeline.
        nao_aplicaveis : chaves deliberadamente fora do escopo desta análise
                         (ex.: o tirante de base na Opção B). Só uma declaração
                         explícita evita a marcação como pendente — a omissão
                         nunca é aprovação.
    """
    fora = set(nao_aplicaveis or ())
    linhas: list[dict] = []
    vistos: set[str] = set()

    for chave, rotulo, norma in VERIFICACOES_EXPORT:
        vistos.add(chave)
        if chave in fora:
            linhas.append(_linha_resumo(
                chave, rotulo, norma, float("nan"), True, STATUS_NAO_APLICAVEL))
            continue
        res = resultados.get(chave)
        if not isinstance(res, dict):
            linhas.append(_linha_resumo(
                chave, rotulo, norma, float("nan"), False, STATUS_NAO_EXECUTADA))
            continue
        eta, ok = extrair_eta_ok(res)
        if math.isnan(eta):
            status = STATUS_SEM_ETA
        else:
            status = STATUS_OK if ok else STATUS_REPROVADO
        linhas.append(_linha_resumo(chave, rotulo, norma, eta, ok, status))

    # Verificações fora do catálogo — continuam a ser reportadas.
    for chave, res in resultados.items():
        if chave in vistos or chave in _META_KEYS:
            continue
        if not isinstance(res, dict):
            continue
        if not any(k in res for k in _ETA_KEYS):
            continue
        eta, ok = extrair_eta_ok(res)
        if math.isnan(eta):
            status = STATUS_SEM_ETA
        else:
            status = STATUS_OK if ok else STATUS_REPROVADO
        linhas.append(_linha_resumo(
            chave, chave, str(res.get("norma", "—"))[:40], eta, ok, status))
    return linhas


def estatisticas_resumo(linhas: list[dict]) -> dict:
    """
    Estatísticas do resumo — fonte ÚNICA do carimbo APROVADO/REPROVADO (F-04).

    Antes esta lógica estava duplicada em `main` e em `gerar_relatorio`, ambas a
    fazer `max()` sobre os η e `all()` sobre os `ok_bool` das linhas que a
    tabela tivesse produzido — sem saber quais tinham sido omitidas.

        η_max     : máximo entre os η NUMÉRICOS (um NaN seria engolido por max())
        pendentes : chaves sem resultado utilizável — bloqueiam a aprovação
        status    : APROVADO só se tudo executou, tudo passou e η_max ≤ 1
    """
    etas = [
        float(r["η"]) for r in linhas
        if isinstance(r.get("η"), (int, float)) and math.isfinite(float(r["η"]))
    ]
    eta_max = max(etas, default=0.0)
    all_ok = all(bool(r.get("ok_bool")) for r in linhas) if linhas else False
    pendentes = [
        r["chave"] for r in linhas
        if r.get("status") in STATUS_PENDENTES
    ]
    aprovado = bool(linhas) and all_ok and eta_max <= 1.0 + 1e-9 and not pendentes
    return {
        "n_linhas":      len(linhas),
        "n_executadas":  len(etas),
        "eta_max":       eta_max,
        "all_ok":        all_ok,
        "pendentes":     pendentes,
        "nao_aplicaveis": [
            r["chave"] for r in linhas if r.get("status") == STATUS_NAO_APLICAVEL
        ],
        "status":        "APROVADO" if aprovado else "REPROVADO",
    }


def _i(x, default: int = 0) -> int:
    return int(round(_f(x, default)))


def _br(x, nd: int = 2) -> str:
    """Decimal brasileiro para LaTeX. Aceita None."""
    return f"{_f(x):.{nd}f}".replace(".", "{,}")


def _tex_escape(s: object) -> str:
    """Escapa caracteres especiais LaTeX e Unicode técnico em texto livre."""
    if s is None:
        return ""
    t = str(s)
    # Ordem: barras primeiro; depois Unicode técnico → LaTeX
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
        ("→", r"$\rightarrow$"),
        ("—", "--"),
        ("–", "--"),
        ("×", r"$\times$"),
        ("ℓ", r"$\ell$"),
        ("º", r"\textordmasculine{}"),
        ("°", r"$^\circ$"),
        ("α", r"$\alpha$"),
        ("β", r"$\beta$"),
        ("γ", r"$\gamma$"),
        ("δ", r"$\delta$"),
        ("Δ", r"$\Delta$"),
        ("ε", r"$\varepsilon$"),
        ("θ", r"$\theta$"),
        ("λ", r"$\lambda$"),
        ("μ", r"$\mu$"),
        ("π", r"$\pi$"),
        ("ρ", r"$\rho$"),
        ("σ", r"$\sigma$"),
        ("φ", r"$\varphi$"),
        ("ϕ", r"$\phi$"),
        ("ψ", r"$\psi$"),
        ("ω", r"$\omega$"),
        ("η", r"$\eta$"),
        ("≥", r"$\geq$"),
        ("≤", r"$\leq$"),
        ("≠", r"$\neq$"),
        ("≈", r"$\approx$"),
        ("≪", r"$\ll$"),
        ("≫", r"$\gg$"),
        ("²", r"$^2$"),
        ("³", r"$^3$"),
        ("·", r"$\cdot$"),
        ("§", r"\S"),
        ("✓", r"\checkmark"),
        ("✗", r"$\times$"),
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


def _latex_preamble() -> str:
    """
    Preâmbulo LaTeX — especificação tipográfica institucional.

    tgheros + mathastext; A4 2,5 cm; seções não numeradas (titlesec);
    Booktabs; paginação só inferior direita; monocromático.
    """
    return r"""\documentclass[a4paper,11pt]{article}

% ── Codificação e idioma ─────────────────────────────────────
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[brazil]{babel}

% ── Página A4, margens uniformes 2,5 cm ──────────────────────
\usepackage[
  a4paper,
  margin=2.5cm
]{geometry}

% ── Matemática e tabelas (antes da tipografia sans) ──────────
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{array}
\usepackage{tabularx}
\usepackage{multirow}

% ── Tipografia sans-serif em todo o documento ────────────────
% Helvetica (TeX Gyre Heros) + matemática no mesmo corpo
\usepackage{tgheros}
\renewcommand{\familydefault}{\sfdefault}
\usepackage[italic,defaultmathsizes,symbolgreek]{mathastext}

% ── Layout tipográfico ───────────────────────────────────────
\usepackage{titlesec}
\usepackage{caption}
\usepackage{enumitem}
\usepackage{graphicx}
\usepackage{microtype}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{listings}
\usepackage{hyperref}

% ── Cores (monocromático + código) ───────────────────────────
\definecolor{codebg}{RGB}{247,247,247}
\definecolor{codeframe}{RGB}{220,220,220}
\definecolor{codenum}{RGB}{120,120,120}

% Hiperlinks pretos, sem decoração
\hypersetup{
  colorlinks=true,
  linkcolor=black,
  citecolor=black,
  urlcolor=black,
  filecolor=black,
  pdfborder={0 0 0},
  pdftitle={Memorial de Cálculo -- Galpão MLC},
  pdfauthor={STOCKI Engenharia Estrutural},
}

% ── Parágrafos e tabelas ─────────────────────────────────────
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.55em}
\setlength{\tabcolsep}{8pt}
\renewcommand{\arraystretch}{1.28}
\setlength{\aboverulesep}{0.55ex}
\setlength{\belowrulesep}{0.55ex}

% ── Hierarquia de seções (todas via \section* / \subsection*) ─
% numberless: formato das seções com estrela (sem prefixo numérico)
\titleformat{name=\section,numberless}
  {\sffamily\Large\bfseries}{}{0pt}{}
\titleformat{\section}
  {\sffamily\Large\bfseries}{}{0pt}{}
\titlespacing*{\section}{0pt}{2.4em}{1.1em}

\titleformat{name=\subsection,numberless}
  {\sffamily\large\bfseries}{}{0pt}{}
\titleformat{\subsection}
  {\sffamily\large\bfseries}{}{0pt}{}
\titlespacing*{\subsection}{0pt}{1.7em}{0.75em}

\titleformat{name=\subsubsection,numberless}
  {\sffamily\normalsize\bfseries}{}{0pt}{}
\titleformat{\subsubsection}
  {\sffamily\normalsize\bfseries}{}{0pt}{}
\titlespacing*{\subsubsection}{0pt}{1.2em}{0.55em}

% ── Listas compactas ─────────────────────────────────────────
\setlist{
  nosep,
  leftmargin=1.35em,
  itemsep=0.18em,
  topsep=0.45em,
  parsep=0pt,
  partopsep=0pt
}

% ── Figuras e legendas ───────────────────────────────────────
\captionsetup{
  font={sf,small},
  labelfont={bf},
  labelsep=period,
  justification=raggedright,
  singlelinecheck=false,
  skip=8pt,
  margin=0pt
}
\setkeys{Gin}{width=0.78\textwidth}

% ── Blocos de código (listings) ──────────────────────────────
\lstset{
  basicstyle=\ttfamily\small,
  backgroundcolor=\color{codebg},
  frame=single,
  rulecolor=\color{codeframe},
  framerule=0.3pt,
  numbers=left,
  numberstyle=\tiny\color{codenum},
  numbersep=8pt,
  breaklines=true,
  breakatwhitespace=true,
  showstringspaces=false,
  tabsize=2,
  keywordstyle=\bfseries,
  commentstyle=\itshape\color{codenum},
  stringstyle=\color{black!65},
  aboveskip=0.85em,
  belowskip=0.85em,
  xleftmargin=2.1em,
  framexleftmargin=1.6em,
  columns=fullflexible,
  keepspaces=true
}

% ── Paginação: só número inferior direito ────────────────────
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\fancyfoot[R]{\small\thepage}
\fancypagestyle{plain}{%
  \fancyhf{}%
  \renewcommand{\headrulewidth}{0pt}%
  \renewcommand{\footrulewidth}{0pt}%
  \fancyfoot[R]{\small\thepage}%
}

% ── Nota de registro (sem caixa / borda) ─────────────────────
\newcommand{\registonota}[2]{%
  \par\vspace{0.9em}%
  \noindent\textbf{#1}\par
  {\small #2}\par
  \vspace{0.5em}%
}

\begin{document}
"""


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
    r_mis  = _clean_dict(resultados.get("misula",      {}))
    r_fl   = _clean_dict(resultados.get("flambagem",   {}))
    r_fx   = _clean_dict(resultados.get("flexao",      {}))
    r_ci   = _clean_dict(resultados.get("cisalhamento",{}))
    r_ap   = _clean_dict(resultados.get("apoio",       {}))
    r_fc   = _clean_dict(resultados.get("flexo_comp",  {}))
    r_pc   = _clean_dict(resultados.get("pilar_central", {}))
    r_els  = _clean_dict(resultados.get("ELS",         {}))
    r_L1   = _clean_dict(resultados.get("L1",          {}))
    r_L3   = _clean_dict(resultados.get("L3",          {}))
    r_L1c  = _clean_dict(resultados.get("L1c",         {}))
    r_L3c  = _clean_dict(resultados.get("L3c",         {}))
    r_fL1  = _clean_dict(resultados.get("fadiga_L1",   {}))
    r_fL1c = _clean_dict(resultados.get("fadiga_L1c",  {}))
    r_cv   = _clean_dict(resultados.get("contraventamento", {}))
    r_cvv  = _clean_dict(resultados.get("contraventamento_vertical", {}))
    r_cvt  = _clean_dict(resultados.get("contraventamento_transversal", {}))
    r_cb   = _clean_dict(resultados.get("corda_beiral", {}))
    r_succ = _clean_dict(resultados.get("succao_uplift", {}))
    r_bloco = _clean_dict(resultados.get("ruptura_bloco_L1", {}))
    r_bloco_c = _clean_dict(resultados.get("ruptura_bloco_L1c", {}))
    r_ter  = _clean_dict(resultados.get("terca", {}))
    r_tfc  = _clean_dict(resultados.get("terca_flexocomp", {}))
    r_qk   = _clean_dict(resultados.get("terca_Qk_conc", {}))
    r_esq  = resultados.get("esquadro_chapas", {})    # esquadro de chapas (issue 23)
    if not isinstance(r_esq, dict):
        r_esq = {}
    r_eg   = _clean_dict(resultados.get("estabilidade_global", {}))
    r_iv   = _clean_dict(resultados.get("impacto_veiculo", {}))
    r_ic   = _clean_dict(resultados.get("icamento", {}))
    r_tir  = _clean_dict(resultados.get("tirante_base", {}))
    meta   = _clean_dict(resultados.get("meta", {}))
    com_tirante = bool(r_tir.get("ativo") or meta.get("com_tirante"))

    # Extrair sub-dicts de flexo_comp
    r_viga  = r_fc.get("viga",  {}) if r_fc else {}
    r_pilar = r_fc.get("pilar", {}) if r_fc else {}
    if not isinstance(r_viga, dict):
        r_viga = {}
    if not isinstance(r_pilar, dict):
        r_pilar = {}

    k_def  = _f(resultados.get("k_def", mat.k_def), getattr(mat, "k_def", 2.0))
    s_m    = _f(meta.get("s", r_fl.get("l_1_m", 2.53)), 2.53)
    l_1_ef = _f(r_cv.get("l_1_efetivo_m", r_fl.get("l_1_m", s_m)), s_m)
    l_ap   = _f(meta.get("l_ap", r_ap.get("l_ap_m", 0.90)), 0.90)
    f_c    = (geo.h_ap - geo.h0) / 2.0
    cob_ok = bool(r_cv.get("cobertura_ok", r_cv.get("ok", False))) if r_cv else False
    cob_txt = "válida" if cob_ok else "NÃO válida"
    eta_lig_alvo = _f(meta.get("eta_lig_alvo", r_L1.get("eta_alvo", 0.75)), 0.75)

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
        """Linha Booktabs: η e status em preto (sem cores de alerta)."""
        simbolo = r"\checkmark" if ok else r"$\times$"
        v = _f(eta, float("nan"))
        # F-04: η indeterminado imprime-se como travessão, nunca como 0,0000.
        eta_tex = "--" if math.isnan(v) else f"{v:.4f}"
        return (
            f"  {nome_verif} & {norma} & "
            f"{eta_tex} & "
            f"{simbolo} \\\\\n"
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
            desc = _tex_escape(
                c.descricao
                .replace(" ← GOVERNA", "")
                .replace("← GOVERNA", "")
            )
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

    # ELS — status em preto (sem cores)
    eta_S1 = float(r_els.get("eta_S1", 0) or 0)
    eta_nf = float(r_els.get("eta_net_fin", 0) or 0)
    ok_S1  = eta_S1 <= 1.0
    ok_nf  = eta_nf <= 1.0
    sim_S1 = r"\checkmark" if ok_S1 else r"$\times$"
    sim_nf = r"\checkmark" if ok_nf else r"$\times$"

    cand = str(meta.get("candidato", "R2"))

    # η máximo (todas as verificações do resumo)
    etas_resumo = [
        _eta(r_cum), _eta(r_fl), _eta(r_fx), _eta(r_ci), _eta(r_ap),
        _eta(r_pilar), _eta(r_pc), _eta(r_cv), _eta(r_ter), _eta(r_els),
        _eta(r_L1), _eta(r_L3),
        _eta(r_L1c), _eta(r_L3c),
        _eta(r_fL1), _eta(r_fL1c),
        _eta(r_eg), _eta(r_iv), _eta(r_ic), _eta(r_cb), _eta(r_qk),
        _eta(r_tir) if com_tirante else 0.0,
    ]
    eta_max = max(etas_resumo) if etas_resumo else 0.0

    parts: list[str] = []
    # Seções LaTeX em subexpressões (evita profundidade AST excessiva)

    # Preâmbulo + capa (tipografia institucional)
    parts.append(_latex_preamble())
    parts.append(
        '% ── Página de título (sem titlepage) ─────────────────────\n'
        '\\thispagestyle{plain}\n'
        '\\vspace*{2.0cm}\n'
        '\\begin{center}\n'
        '  {\\fontsize{22}{26}\\selectfont\\bfseries Memorial de Cálculo}\\\\[0.9em]\n'
        '  {\\large Estrutura em Madeira Lamelada Colada (MLC)}\\\\[0.5em]\n'
        '  {\\normalsize Galpão para Estacionamento Coberto}\\\\[1.8em]\n'
        '  {\\small\n'
        '  \\begin{tabular}{@{}ll@{}}\n'
        '    Responsável técnico & Gabriel Stocki \\\\\n'
        '    CREA                & PR 195315/D \\\\\n'
        '    Empresa             & STOCKI Engenharia Estrutural \\\\\n'
        f'    Data                & {hoje} \\\\\n'
        '    Documento           & Verificação estrutural -- EC5 / EN 1990 / NBR 6123 \\\\\n'
        '  \\end{tabular}}\n'
        '\\end{center}\n'
        '\\vspace{1.6cm}\n\n'
        '% ── 1. Normas de Referência ───────────────────────────────\n'
        '\\section*{1. Normas de Referência}\n\n'
        '\\begin{tabular}{@{}ll@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Norma} & \\textbf{Descrição} \\\\\n'
        '  \\midrule\n'
        '  EN 1995-1-1:2004     & Eurocode 5 -- Estruturas de madeira \\\\\n'
        '  EN 1990:2002         & Eurocode -- Bases de projeto \\\\\n'
        '  EN 14080:2013        & Madeira lamelada colada -- Requisitos \\\\\n'
        '  EN 14592:2008        & Fixadores de aço para estruturas de madeira \\\\\n'
        '  EN 1993-1-8:2005     & Eurocode 3 -- Ligações \\\\\n'
        '  EN 1991-1-7:2006     & Ações acidentais -- Impacto \\\\\n'
        '  ABNT NBR 6123:2023   & Forças devidas ao vento em edificações \\\\\n  \\multicolumn{2}{@{}l@{}}{\\footnotesize\\textit{Edição única adotada. O capítulo de vento possui achados de auditoria em aberto}} \\\\\n  \\multicolumn{2}{@{}l@{}}{\\footnotesize\\textit{(AUD-001 a AUD-005): $S_2$ sem dependência de $z$, domínio da Tab.~25 não validado e força}} \\\\\n  \\multicolumn{2}{@{}l@{}}{\\footnotesize\\textit{longitudinal de cobertura isolada sob revisão. Resultados de vento: \\textbf{NÃO VALIDADOS}.}} \\\\\n'
        '  \\bottomrule\n'
        '\\end{tabular}\n\n'
        '% ── 2. Dados Gerais ───────────────────────────────────────\n'
        '\\section*{2. Dados Gerais do Projeto}\n\n'
        '\\begin{tabular}{@{}lll@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Item} & \\textbf{Valor} & \\textbf{Observação} \\\\\n'
        '  \\midrule\n'
        '  Uso & Estacionamento coberto & Galpão aberto nas laterais \\\\\n'
        '  Localização & Londrina -- PR & -- \\\\\n'
        '  Vão total & 40{,}50~m & 2 pórticos $\\times$ 20{,}25~m \\\\\n'
        '  Comprimento & 46{,}00~m & -- \\\\\n'
        '  Pé-direito & 7{,}00~m & -- \\\\\n'
        '  Espaçamento entre pórticos & 5{,}75~m & Vão das terças \\\\\n'
        '  Sistema estrutural & Viga biarticulada MLC & 1$\\times$ hiperestática \\\\\n'
        '  \\bottomrule\n'
        '\\end{tabular}\n\n'
        '% ── 3. Material ───────────────────────────────────────────\n'
        '\\section*{3. Material -- '
    )
    parts.append(mat.classe)
    parts.append(' (EN 14080)}\n\n\\begin{tabular}{@{}llll@{}}\n  \\toprule\n  \\textbf{Propriedade} & \\textbf{Valor} & \\textbf{Propriedade} & \\textbf{Valor} \\\\\n  \\midrule\n  $f_{m,k}$    & ')
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
    parts.append(': estrutura aberta nas laterais / exposição a intempérie.}\n\n\\vspace{4pt}\n\\begin{tabular}{@{}lll@{}}\n  \\toprule\n  \\textbf{Duração} & $k_{mod}$ (CS')
    parts.append(f'{mat.classe_servico}')
    parts.append(') & \\textbf{Combinação} \\\\\n  \\midrule\n  Curta       & ')
    parts.append(_br(GlulamMaterial(mat.classe, mat.classe_servico, 'curta').k_mod, 2))
    parts.append(' & ELU com vento dominante (\\textbf{adotado}) \\\\\n  Instantânea & ')
    parts.append(_br(GlulamMaterial(mat.classe, mat.classe_servico, 'instantanea').k_mod, 2))
    parts.append(' & Alternativa normativa para vento -- \\textbf{não} adotada \\\\\n  Longa       & ')
    parts.append(_br(GlulamMaterial(mat.classe, mat.classe_servico, 'longa').k_mod, 2))
    parts.append(' & ELS / ações de longa duração \\\\\n  Permanente  & ')
    parts.append(_br(GlulamMaterial(mat.classe, mat.classe_servico, 'permanente').k_mod, 2))
    parts.append(' & Comb. quase-permanente (fluência) \\\\\n  \\bottomrule\n\\end{tabular}\n\n')

    # Critério de duração do vento — EC5 §2.3.1.2 / Tab. 3.1
    _k_curta = GlulamMaterial(mat.classe, mat.classe_servico, 'curta').k_mod
    _k_inst  = GlulamMaterial(mat.classe, mat.classe_servico, 'instantanea').k_mod
    parts.append('\\vspace{4pt}\n\\textbf{Critério adotado -- $k_{mod}$ para vento ')
    parts.append('(EC5~\\S2.3.1.2 + Tab.~3.1):}\n\n')
    parts.append(
        'A EN~1995-1-1 permite enquadrar a ação do vento como duração '
        '\\textbf{curta} ou \\textbf{instantânea}. '
        'Neste projeto adota-se explicitamente a duração \\textbf{curta} '
        f'($k_{{mod}} = {_br(_k_curta, 2)}$ em CS{mat.classe_servico}), '
        'e \\textbf{não} a instantânea '
        f'($k_{{mod}} = {_br(_k_inst, 2)}$). '
        'O critério é \\textbf{conservador}: $k_{mod}$ menor reduz as '
        'resistências de cálculo $f_d = k_{mod}\\,f_k/\\gamma_M$ nas '
        'combinações ELU com vento dominante. '
        'A classificação como instantânea seria admissível pela norma, '
        'mas não é utilizada neste memorial.\n\n'
    )

    parts.append('% ── 4. Ações e Combinações ────────────────────────────────────\n\\section*{4. Ações e Combinações}\n\n\\textbf{Cargas características (pórtico intermediário):}\n\n\\begin{tabular}{@{}llll@{}}\n  \\toprule\n  \\textbf{Ação} & \\textbf{Valor por área} & \\textbf{Valor linear} & \\textbf{Norma} \\\\\n  \\midrule\n  Permanente $g_k$ & ')
    parts.append(_br(g_area, 2))
    parts.append('~kN/m² & ')
    parts.append(_br(g_k, 3))
    parts.append('~kN/m & EN 1991-1-1 \\S4 \\\\\n  Sobrecarga $q_k$ & ')
    parts.append(_br(q_area, 2))
    parts.append('~kN/m² & ')
    parts.append(_br(q_k, 3))
    parts.append('~kN/m & EN 1991-1-1 \\\\\n  \\multicolumn{3}{l}{Área tributária $= L_t = ')
    parts.append(_br(area_trib, 2))
    parts.append('$~m (pórtico intermediário)} & Geometria \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{6pt}\n'
    )
    _pp = meta.get("peso_proprio", {})
    if isinstance(_pp, dict) and _pp:
        parts.append(
            '\\textbf{Peso próprio $g_k$ -- discriminado (EN~1991-1-1~\\S4 + '
            'EN~14080; $\\gamma=\\rho_{mean}\\cdot g'
            f'={_br(_pp.get("gamma_kNm3", 0), 2)}$~kN/m$^3$):}}\n\n'
            '\\begin{tabular}{@{}llp{6.2cm}@{}}\n  \\toprule\n'
            '  \\textbf{Parcela} & \\textbf{kN/m$^2$} & \\textbf{Origem} \\\\\n'
            '  \\midrule\n'
            f'  Viga MLC (duplo-bisel) & {_br(_pp.get("g_mlc_kNm2", 0), 3)} & '
            '$\\int A(x)\\,\\mathrm{d}x\\cdot\\gamma / L_{viga} / L_t$ (integração exata) \\\\\n'
            f'  Terças & {_br(_pp.get("g_tercas_kNm2", 0), 3)} & '
            '$\\gamma\\cdot b_t h_t / s$ \\\\\n'
            f'  Telha & {_br(_pp.get("g_telha_kNm2", 0), 3)} & ficha técnica (declarado) \\\\\n'
            f'  Instalações & {_br(_pp.get("g_instalacoes_kNm2", 0), 3)} & estimativa de projeto \\\\\n'
            '  \\midrule\n'
            f'  \\textbf{{Total viga}} & \\textbf{{{_br(_pp.get("g_k_viga_kNm2", 0), 3)}}} & MLC + terças + cobertura \\\\\n'
            f'  Total terça & {_br(_pp.get("g_k_terca_kNm2", 0), 3)} & terças + cobertura (a terça não carrega a viga) \\\\\n'
            '  \\bottomrule\n\\end{tabular}\n\n\\vspace{6pt}\n'
        )
    parts.append(
        '\\textbf{Vento -- NBR 6123 (cobertura isolada 2 águas):}\n\n\\begin{tabular}{@{}lll@{}}\n  \\toprule\n  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Ref.} \\\\\n  \\midrule\n  $V_0$ (Londrina/PR) & 45{,}0~m/s & Fig.~1 \\\\\n  $S_1$ & 1{,}0 & \\S5.2 \\\\\n  $S_2$ (Cat.~IV, Cl.~B) & 0{,}83 & Tab.~3 \\\\\n  $S_3$ & 1{,}0 & \\S5.5 \\\\\n  $H_1 = h_{ap}-h_0$ & ')
    parts.append(_br(geo.h_ap - geo.h0, 3))
    parts.append('~m & Geometria ')
    parts.append(cand)
    parts.append(' \\\\\n  $\\tan\\beta = H_1/(L/2)$ & ')
    parts.append(_br((geo.h_ap - geo.h0) / (geo.L / 2), 4))
    parts.append(' & \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{6pt}\n\\textbf{Combinações de ações -- EN 1990 (valores do pipeline):}\n\n{\\small\\begin{tabular}{@{}p{2.8cm}p{8.2cm}r@{}}\n  \\toprule\n  \\textbf{Combinação} & \\textbf{Descrição} & \\textbf{$q_{tot}$ (kN/m)} \\\\\n  \\midrule\n')
    parts.append(comb_lines)
    parts.append(
        '  \\bottomrule\n\\end{tabular}}\n\n\\vspace{4pt}\n'
        '\\textit{Concomitância (categoria H):} a cobertura é \\textbf{não '
        'acessível} (categoria~H, EN 1991-1-1 Tab.~6.9/6.10). Pela EN~1990 '
        'Tab.~A1.1, $\\psi_0=\\psi_1=\\psi_2=0$ para a sobrecarga; e a '
        'EN~1991-1-1~\\S3.3.2(1) determina que a sobrecarga de cobertura '
        '\\textbf{não atua simultaneamente com o vento}. Logo $Q$ e $W$ são '
        'ações variáveis \\textbf{alternativas}: combinações com vento dominante '
        'não incluem $Q$, e a combinação de sobrecarga não inclui vento '
        '(vento pela NBR~6123:2023).\n\n'
        '\\textit{Sobrecarga (categoria H):} $q_k=0{,}40$~kN/m$^2$ '
        '(EN~1991-1-1 Tab.~6.10, valor recomendado; issue~2). A norma prevê '
        'também uma carga concentrada $Q_k=1{,}0$~kN de manutenção, para '
        '\\textbf{verificação local} (terça/telha), \\textbf{não concomitante} '
        'com a UDL nem com o vento (\\S6.3.4.2). '
        + (
            'Verificada como combinação alternativa (issue~34): terça a meio-vão '
            f'$M_d={_br(r_qk.get("M_d_kNm", 0), 2)}$~kN·m (duração média, '
            f'$k_{{mod}}={_br(r_qk.get("k_mod", 0.65), 2)}$) $\\Rightarrow$ '
            f'$\\eta={_br(r_qk.get("eta", 0), 3)}$ '
            f'({_tex_escape(str(r_qk.get("verif_gov", "")))}), abaixo da UDL '
            f'($\\eta_{{flex}}={_br((r_ter or {}).get("eta_flexao", 0), 3)}$) '
            '$\\Rightarrow$ a UDL governa. Telha: $M_{local,d}='
            f'{_br(r_qk.get("M_telha_d_kNm", 0), 3)}$~kN·m/m a confrontar com a '
            'ficha do fabricante (issue~17).'
            if r_qk else
            'Não incluída no modelo global -- ver issue~34.'
        )
        + '\n\n'
        '% ── 5. Sistema Estrutural ─────────────────────────────────────\n'
        '\\section*{5. Sistema Estrutural -- Viga Biarticulada (MLC monolítica)}\n\n\\begin{itemize}\n  \\item Peça única de duplo-bisel: extradorso em duas águas, intradorso reto.\n  \\item \\textbf{Sem rótula na cumeeira} (continuidade física da MLC).\n  \\item Rótulas apenas nos apoios (bases).\n  \\item Grau de hiperestaticidade: 1 -- empuxo $H$ por \\textbf{compatibilidade}\n        (Castigliano / força unitária no eixo centroidal $y_c$).\n  \\item Integração em projeção horizontal $\\mathrm{d}x$ (autorizada no projeto).\n  \\item $M$ na cumeeira em geral $\\neq 0$ $\\Rightarrow$ EC5 \\S6.4.3 ativo.\n  \\item Classe de serviço ')
    parts.append(f'{mat.classe_servico}')
    parts.append(': galpão aberto nas laterais.\n  \\item \\textbf{Contraventamento horizontal} (cruzes de St.~André + terças-biela):\n        garante a função estrutural da cobertura e valida $l_1=s$ no LTB\n        (EC5~\\S9.2.5) -- ver \\S9.\n')
    if com_tirante:
        parts.append(
            '  \\item \\textbf{Tirante de base} ao nível do piso: fecha o empuxo $H$ '
            'entre bases de cada vão; $H_{\\mathrm{sapata}}\\approx 0$, '
            '$T_{\\mathrm{tirante}}\\approx H$ (EN~1993-1-1~\\S6.2.3).\n'
        )
    parts.append('\\end{itemize}\n\n\\textbf{Análise (combinação governante ')
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
    parts.append('~\\text{kN}\n\\]\n\n')

    # ── 5b. Durabilidade — classe de uso / adesivo / tratamento (issue 30) ────
    _dur = meta.get("durabilidade", {})
    if _dur:
        parts.append(
            '% ── 5b. Durabilidade ──────────────────────────────────────\n'
            '\\subsection*{Durabilidade -- classe de uso, adesivo e tratamento '
            '(EN~335 / EN~301 / EN~351)}\n\n'
            'Coerente com a \\textbf{Classe de Serviço~3} (EC5~\\S2.3.1.3) adotada '
            '(estrutura coberta mas aberta nas laterais):\n'
            '\\begin{itemize}\n'
            f'  \\item \\textbf{{Classe de uso (EN~335):}} '
            f'UC~{_tex_escape(_dur.get("classe_uso_en335", "3.1"))} -- exterior '
            'acima do solo, umedecimento limitado (protegida da chuva direta pelo '
            'telhado; peças plenamente abrigadas poderiam ser UC~2). Mapeia na '
            'CS3 do EC5.\n'
            f'  \\item \\textbf{{Adesivo (EN~301):}} '
            f'{_tex_escape(_dur.get("adesivo_en301", "Tipo I"))} -- exigido para '
            'CS3 (EN~14080~\\S5.3), apto a exposição exterior/alta umidade '
            f'(ex.: {_tex_escape(_dur.get("adesivo_exemplos", "MUF ou RF/PRF"))}).\n'
            f'  \\item \\textbf{{Espécie / durabilidade natural:}} '
            f'{_tex_escape(_dur.get("especie", "conífera"))}, EN~350 '
            f'{_tex_escape(_dur.get("durab_natural_en350", "classe 4"))} '
            '$\\Rightarrow$ requer tratamento e/ou proteção por detalhamento em UC3.\n'
            f'  \\item \\textbf{{Tratamento preservativo:}} '
            f'{_tex_escape(_dur.get("tratamento", ""))}\n'
            '\\end{itemize}\n\n'
        )

    parts.append('% ── 6. Geometria da Viga (candidata de projeto) ──────────────\n\\section*{6. Geometria da Viga -- Candidata ')
    parts.append(cand)
    parts.append('}\n\n\\begin{tabular}{@{}lll@{}}\n  \\toprule\n  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Observação} \\\\\n  \\midrule\n  Vão $L$ & ')
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
    parts.append('~m & Geometria de cobertura \\\\\n  $l_1$ efetivo (LTB) & ')
    parts.append(_br(l_1_ef, 2))
    parts.append('~m & ')
    parts.append('Cobertura OK $\\Rightarrow l_1=s$' if cob_ok else 'Cobertura falha $\\Rightarrow l_1=\\ell$ (penalizado)')
    parts.append(' \\\\\n  $l_{ef}$ flambagem & ')
    parts.append(_br(0.9 * l_1_ef, 3))
    parts.append('~m & EC5 Tab.~6.1 ($0{,}9\\,l_1$) \\\\\n  Placa de apoio $l_{ap}$ & ')
    parts.append(_br(l_ap, 2))
    parts.append('~m & \\\\\n  \\bottomrule\n\\end{tabular}\n\n% ── 7. Verificações ELU ───────────────────────────────────────\n\\section*{7. Verificações ELU -- Viga}\n\n\\begin{tabular}{@{}p{5.5cm}lcc@{}}\n  \\toprule\n  \\textbf{Verificação} & \\textbf{Norma} & $\\eta$ & \\textbf{Status} \\\\\n  \\midrule\n')
    parts.append(eta_row('Zona do ápice ($t_{90}$ e $\\sigma_{m}$, $M\\neq 0$)', 'EC5 \\S6.4.3', _eta(r_cum), _ok(r_cum)))
    parts.append(eta_row('Mísula -- face inclinada ($\\sigma_{m,\\alpha,d}$)', 'EC5 \\S6.4.2', _eta(r_mis), _ok(r_mis)))
    parts.append(eta_row('Flambagem lateral', 'EC5 \\S6.3.3', _eta(r_fl), _ok(r_fl)))
    parts.append(eta_row('Flexo-compressão viga', 'EC5 \\S6.3.2+\\S6.3.3', _eta(r_fx), _ok(r_fx)))
    parts.append(eta_row('Cisalhamento ($b_{ef}=k_{cr}b$)', 'EC5 \\S6.1.7', _eta(r_ci), _ok(r_ci)))
    parts.append(eta_row('Compressão no apoio', 'EC5 \\S6.1.5+\\S6.2.2', _eta(r_ap), _ok(r_ap)))
    parts.append('  \\bottomrule\n\\end{tabular}\n\n')

    # ── Convenção de eixos e esforços no apoio (issue 12) ─────────────────────
    if r_ci:
        parts.append(
            '\\vspace{4pt}\n\\subsection*{Convenção de eixos e esforços no apoio '
            '(EC5~\\S6.1.5/\\S6.1.7)}\n\n'
            'Adota-se o \\textbf{eixo da peça} como referencial. O eixo centroidal '
            f'da viga duplo-bisel inclina-se $\\theta=\\arctan(\\tfrac{{\\tan\\alpha}}{{2}})'
            f'={_br(r_ci.get("theta_eixo_deg",0),2)}^\\circ$. A reação de apoio '
            'decompõe-se em:\n'
            '\\[\n'
            '  N = H\\cos\\theta + R_v\\sin\\theta \\quad(\\text{axial, } \\parallel'
            f'\\text{{ fibras}})={_br(r_ci.get("N_axis_kN",0),1)}~\\text{{kN}},\\qquad\n'
            '  V = R_v\\cos\\theta - H\\sin\\theta \\quad(\\perp\\text{ eixo})'
            f'={_br(r_ci.get("V_d_kN",0),1)}~\\text{{kN}}\n'
            '\\]\n'
            'No arco abatido o empuxo $H$ é grande, de modo que $V\\ll R_v$ '
            f'($R_v={_br(r_ci.get("R_v_vertical_kN",0),1)}$~kN): a reação é quase toda '
            'axial. Consequências no referencial:\n'
            '\\begin{itemize}\n'
            '  \\item \\textbf{Cisalhamento} (\\S6.1.7): atua na seção transversal '
            '($\\perp$ eixo) $\\Rightarrow$ usa-se $V$ (⊥ eixo), não a reação vertical. '
            f'Governa a comb.\\ {_tex_escape(str(r_ci.get("comb_V_gov","")))} '
            '(vento assimétrico maximiza $V$, $\\neq$ da comb.\\ de $|M|$).\n'
            '  \\item \\textbf{Compressão no apoio} (\\S6.1.5): atua na face '
            'horizontal do intradorso $\\Rightarrow$ usa-se a reação vertical $R_v$ '
            '(plano distinto). Não é incoerência: são planos diferentes.\n'
            '\\end{itemize}\n\n'
            '\\vspace{2pt}\n\\subsection*{Detalhes -- Flexo-compressão viga (EC5~\\S6.3.2 Eq.~6.23)}\n\n\\[\n  \\frac{\\sigma_{c,0,d}}{k_c \\cdot f_{c,0,d}}\n  + \\frac{\\sigma_{m,d}}{f_{m,d}} \\leq 1{,}0\n\\]\n\n\\textit{Termo de compressão \\textbf{linear} ($\\div k_c$): \\S6.3.2 (peça esbelta, \\S6.3.2(3)); a forma quadrática seria a de \\S6.2.4, só para $\\lambda_{rel}\\leq0{,}3$ (issue~16).}\n\n\\begin{tabular}{@{}lllll@{}}\n  \\toprule\n  $M_d$ (kN·m) & $N_d$ (kN) & $\\sigma_{c,0,d}$ (MPa) & $\\sigma_{m,d}$ (MPa) & $k_c$ \\\\\n  \\midrule\n')
    parts.append(f'  {r_viga.get('M_max_kNm', 0):.2f} & ')
    parts.append(f'{r_viga.get('N_d_kN', 0):.2f} & ')
    parts.append(f'{r_viga.get('sigma_c_MPa', 0):.4f} & ')
    parts.append(f'{r_viga.get('sigma_m_MPa', 0):.4f} & ')
    parts.append(f'{r_viga.get('k_c_y', 0):.4f} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n')

    # ── Detalhe: flambagem lateral / LTB (EC5 §6.3.3) — memória (issue 11) ─────
    if r_fl:
        parts.append(
            '\\subsection*{Detalhes -- Flambagem lateral / LTB (EC5~\\S6.3.3)}\n\n'
            'Estabilidade lateral por flexo-torção do banzo comprimido. '
            'Hipótese de restrição: '
            f'\\textbf{{{_tex_escape(str(r_fl.get("restricao", "")))}}}, carga '
            f'{_tex_escape(str(r_fl.get("tipo_carga", "distribuida")))} '
            '(EC5 Tab.~6.1):\n'
            '\\[\n'
            f'  l_{{ef}} = 0{{,}}9\\,l_1 = 0{{,}}9\\cdot{_br(r_fl.get("l_1_m",0),3)}'
            f' = {_br(r_fl.get("l_ef_m",0),3)}~\\text{{m}}\n'
            '\\]\n'
            f'com $l_1={_br(r_fl.get("l_1_m",0),3)}$~m = {_tex_escape(str(r_fl.get("l_1_origem","")))}. '
            'A validade de $l_1$ (restrição das terças) depende do contraventamento '
            'de cobertura (\\S9.2.5, issues 15/16).\n\n'
            'Seção de referência (ponto de $M_{max}$): '
            f'$h={_br(r_fl.get("h_crit_m",0),3)}$~m, $b={_br(r_fl.get("b_m",0),3)}$~m, '
            f'$E_{{0,05}}={_br(r_fl.get("E0_05_MPa",0),0)}$~MPa. Seção retangular de '
            'coníferas (Eq.~6.32):\n'
            '\\[\n'
            '  \\sigma_{m,crit}=\\frac{0{,}78\\,b^2 E_{0,05}}{h\\,l_{ef}}'
            f'={_br(r_fl.get("sigma_m_crit_MPa",0),3)}~\\text{{MPa}},\\quad '
            '\\lambda_{rel,m}=\\sqrt{\\frac{f_{m,k}}{\\sigma_{m,crit}}}'
            f'={_br(r_fl.get("lambda_rel_m",0),3)}\n'
            '\\]\n'
            'Fator de instabilidade (Eq.~6.34) -- '
            f'{_tex_escape(str(r_fl.get("regime","")))}:\n'
            '\\[\n'
            '  k_{crit}=\\begin{cases}1{,}0 & \\lambda_{rel,m}\\leq0{,}75\\\\'
            '1{,}56-0{,}75\\,\\lambda_{rel,m} & 0{,}75<\\lambda_{rel,m}\\leq1{,}4\\\\'
            '1/\\lambda_{rel,m}^2 & \\lambda_{rel,m}>1{,}4\\end{cases}'
            f'\\;=\\;{_br(r_fl.get("k_crit",0),3)}\n'
            '\\]\n'
            'Verificação (Eq.~6.33): '
            f'$\\sigma_{{m,d}}={_br(r_fl.get("sigma_md_MPa",0),3)}\\leq '
            f'k_{{crit}}f_{{m,d}}={_br(r_fl.get("resist_MPa",0),3)}$~MPa '
            f'$\\Rightarrow\\eta={_br(r_fl.get("eta",0),3)}$.\n\n'
        )

    # ── Detalhe: mísula / borda inclinada (EC5 §6.4.2) ────────────────────────
    if r_mis:
        _reg = r_mis.get("regime", "")
        _eq  = '6.39' if _reg == "tracao" else '6.40'
        _regtxt = ('tração paralela à borda (topo em hogging)'
                   if _reg == "tracao"
                   else 'compressão paralela à borda (topo em sagging)')
        parts.append(
            '\\subsection*{Detalhes -- Mísula / borda inclinada (EC5~\\S6.4.2)}\n\n'
            'O extradorso é cortado em ângulo $\\alpha$ face às lâminas. Na borda '
            'inclinada verifica-se a tensão de flexão majorada pelo estado '
            'multiaxial local:\n'
            '\\[\n'
            '  \\sigma_{m,\\alpha,d} = \\frac{6\\,M_d}{b\\,h^2} \\leq k_{m,\\alpha}\\,f_{m,d}\n'
            '\\]\n'
            'com (Eq.~6.39 tração / Eq.~6.40 compressão):\n'
            '\\[\n'
            '  k_{m,\\alpha}^{\\text{trac}}=\\Big[1+\\big(\\tfrac{f_{m,d}}{0{,}75 f_{v,d}}\\tan\\alpha\\big)^2'
            '+\\big(\\tfrac{f_{m,d}}{f_{t,90,d}}\\tan^2\\alpha\\big)^2\\Big]^{-1/2},\\quad\n'
            '  k_{m,\\alpha}^{\\text{comp}}=\\Big[1+\\big(\\tfrac{f_{m,d}}{1{,}5 f_{v,d}}\\tan\\alpha\\big)^2'
            '+\\big(\\tfrac{f_{m,d}}{f_{c,90,d}}\\tan^2\\alpha\\big)^2\\Big]^{-1/2}\n'
            '\\]\n\n'
            f'Para $\\alpha={_br(r_mis.get("alpha_deg",0),1)}^\\circ$: '
            f'$k_{{m,\\alpha}}^{{\\text{{comp}}}}={_br(r_mis.get("k_m_alpha_compressao",0),3)}$, '
            f'$k_{{m,\\alpha}}^{{\\text{{trac}}}}={_br(r_mis.get("k_m_alpha_tracao",0),3)}$. '
            f'Governa a {_regtxt} (Eq.~{_eq}), na seção $x={_br(r_mis.get("x_gov_m",0),2)}$~m '
            f'($h={_br(r_mis.get("h_gov_m",0),3)}$~m, $M_d={_br(r_mis.get("M_gov_kNm",0),1)}$~kN·m, '
            f'comb.\\ {_tex_escape(str(r_mis.get("comb_gov","")))}):\n'
            '\\[\n'
            f'  \\sigma_{{m,\\alpha,d}}={_br(r_mis.get("sigma_m_alpha_MPa",0),3)}~\\text{{MPa}}'
            f'\\leq k_{{m,\\alpha}} f_{{m,d}}={_br(r_mis.get("resistencia_MPa",0),3)}~\\text{{MPa}}'
            f'\\;\\Rightarrow\\;\\eta={_br(r_mis.get("eta",0),3)}\n'
            '\\]\n\n'
            'A zona do ápice (perpendicular à fibra, $\\sigma_{t,90}$) é tratada '
            'à parte pela \\S6.4.3 (cumeeira); esta é a verificação complementar '
            'da tensão de flexão na face em bisel.\n\n'
        )

    # ── Detalhe: zona do ápice / cumeeira (EC5 §6.4.3) ────────────────────────
    if r_cum:
        parts.append(
            '\\subsection*{Detalhes -- Zona do ápice / cumeeira (EC5~\\S6.4.3)}\n\n'
            'Viga de duplo-bisel: raio $r\\to\\infty$ $\\Rightarrow$ $h_{ap}/r=0$, '
            f'$k_r={_br(r_cum.get("k_r",1.0),2)}$ (\\S6.4.3(5)) e $k_l=k_1='
            f'{_br(r_cum.get("k_l",0),3)}$ '
            f'($=1+1{{,}}4\\tan\\alpha_{{ap}}+5{{,}}4\\tan^2\\alpha_{{ap}}$, '
            f'$\\alpha_{{ap}}={_br(r_cum.get("alpha_ap_deg",0),1)}^\\circ$). '
            f'Momento no ápice $M_{{ap,d}}={_br(r_cum.get("M_cumeeira_kNm",0),1)}$~kN·m.\n\n'
            'Volumes da zona do ápice (Fig.~6.9):\n'
            '\\[\n'
            f'  V_b=b L\\big[h_{{ap}}-0{{,}}25 L\\tan\\alpha_{{ap}}\\big]={_br(r_cum.get("V_b_m3",0),3)}~\\text{{m}}^3,'
            f'\\quad V=b h_{{ap}}^2\\big[1-0{{,}}25\\tan\\alpha_{{ap}}\\big]={_br(r_cum.get("V_m3",0),3)}~\\text{{m}}^3'
            f'\\;(\\leq \\tfrac{{2}}{{3}}V_b)\n'
            '\\]\n\n'
            '\\begin{tabular}{@{}lll@{}}\n'
            '  \\toprule\n'
            '  \\textbf{Verificação} & \\textbf{Tensão vs resistência} & $\\eta$ \\\\\n'
            '  \\midrule\n'
            f'  Flexão ápice (Eq.~6.42) $\\sigma_m=k_l\\tfrac{{6M_{{ap}}}}{{b h_{{ap}}^2}}$ & '
            f'${_br(r_cum.get("sigma_m_ap_MPa",0),3)}\\leq k_r f_{{m,d}}={_br(r_cum.get("resist_m_MPa",0),2)}$~MPa & '
            f'{_br(r_cum.get("eta_flexao_ap",0),3)} \\\\\n'
            f'  Tração $\\perp$ (Eq.~6.54) $\\sigma_{{t,90}}=k_p\\tfrac{{6M_{{ap}}}}{{b h_{{ap}}^2}}$ & '
            f'${_br(r_cum.get("sigma_t90d_MPa",0),3)}\\leq k_{{dis}}k_{{vol}}f_{{t,90,d}}={_br(r_cum.get("resist_t90_MPa",0),3)}$~MPa & '
            f'{_br(r_cum.get("eta_t90",0),3)} \\\\\n'
            '  \\bottomrule\n'
            '\\end{tabular}\n\n'
            f'\\vspace{{2pt}}\nParâmetros: $k_p={_br(r_cum.get("k_p",0),4)}$ '
            f'($=0{{,}}2\\tan\\alpha_{{ap}}$), $k_{{dis}}={_br(r_cum.get("k_dis",1.4),1)}$ '
            f'(duplo-bisel), $k_{{vol}}=(V_0/V)^{{0{{,}}2}}={_br(r_cum.get("k_vol",0),3)}$ '
            f'($V_0=0{{,}}01$~m³). Governa: {_tex_escape(str(r_cum.get("verif_gov","")))}.\n\n'
        )

    parts.append('% ── 8. Verificações ELU -- Pilares ────────────────────────────\n\\section*{8. Verificações ELU -- Pilares}\n\nCompressão simples EC5~\\S6.3.2; $l_{ef}=1{,}0\\cdot H$ (rótulas nas extremidades).\n\n\\begin{tabular}{@{}llllllc@{}}\n  \\toprule\n  \\textbf{Pilar} & Seção (m) & $N_d$ (kN) & $\\lambda$ & $\\lambda_{rel}$ & $k_c$ & $\\eta$ \\\\\n  \\midrule\n  Lateral & ')
    parts.append(f'{r_pilar.get('b_m', 0.22):.2f}$\\times${r_pilar.get('h_m', 0.26):.2f} & ')
    parts.append(f'{r_pilar.get('N_d_kN', 0):.2f} & ')
    parts.append(f'{r_pilar.get('lambda', 0):.1f} & ')
    parts.append(f'{r_pilar.get('lambda_rel', 0):.4f} & ')
    parts.append(f'{r_pilar.get('k_c', 0):.4f} & ')
    parts.append(f'{_eta(r_pilar):.4f} \\\\\n')
    parts.append('  Central ($N\\approx 2R_v$) & ')
    parts.append(f'{r_pc.get('b_m', 0.28):.2f}$\\times${r_pc.get('h_m', 0.28):.2f} & ')
    parts.append(f'{r_pc.get('N_d_kN', 0):.2f} & ')
    parts.append(f'{r_pc.get('lambda', 0):.1f} & ')
    parts.append(f'{r_pc.get('lambda_rel', 0):.4f} & ')
    parts.append(f'{r_pc.get('k_c', 0):.4f} & ')
    parts.append(f'{_eta(r_pc):.4f} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n')
    parts.append(
        '\\textbf{Definição de $N_d$ e combinação governante (issue 13):} '
        '$N_d$ é a \\textbf{reação vertical de ELU} '
        '($N_d=\\mathrm{fator}\\cdot R_v$; fator~$=1$ no pilar de extremidade e '
        '$=2$ no central, soma das reações dos dois vãos). Verifica-se o pilar '
        'contra \\textbf{todas} as combinações ELU, cada uma com o seu $k_{mod}$ '
        '(EC5~\\S3.1.3~/~\\S2.4.1), reportando-se a governante ($\\eta$ máximo):\n'
        '\\begin{itemize}\n'
        f'  \\item Lateral: governa \\texttt{{{_tex_escape(r_pilar.get("comb_gov", "--"))}}} '
        f'($k_{{mod}}={_br(r_pilar.get("k_mod", 0), 2)}$), '
        f'$N_d={_br(r_pilar.get("N_d_kN", 0), 1)}$~kN, $\\eta={_br(_eta(r_pilar), 4)}$;\n'
        f'  \\item Central: governa \\texttt{{{_tex_escape(r_pc.get("comb_gov", "--"))}}} '
        f'($k_{{mod}}={_br(r_pc.get("k_mod", 0), 2)}$), '
        f'$N_d={_br(r_pc.get("N_d_kN", 0), 1)}$~kN, $\\eta={_br(_eta(r_pc), 4)}$.\n'
        '\\end{itemize}\n'
        '\\textit{Origem dos dois valores de $N$:} a reação vertical de ELU '
        '($\\approx$210~kN, ELU\\_C2) é o $N$ do pilar; o esforço normal do '
        '\\textbf{eixo da viga} ($\\approx$1{,}6~MN, que inclui o empuxo $H$) vai '
        'ao tirante/sapata e \\textbf{não} ao pilar; e $\\approx$87~kN é a reação '
        'de \\textbf{ELS} (quase-permanente, só $G$) -- valor de serviço, não de '
        'dimensionamento ELU.\n\n'
        '\\textit{Nota (duração / $k_{mod}$):} a combinação governante usa o '
        '$k_{mod}$ declarado para cada combinação em \\texttt{loads.py}. A '
        'classificação estrita por EC5~\\S3.1.3 ($k_{mod}$ da ação de menor '
        'duração) é objeto da issue~5; se a combinação Q-dominante for '
        'reclassificada como \\emph{curta}, passa a governar ELU\\_C2 '
        '(vento dominante) com $\\eta\\approx0{,}68$. Em ambos os casos o pilar '
        'central é adequado ($\\eta<1{,}0$).\n\n'
    )

    # ── 8b. Estabilidade global ────────────────────────────────
    _ok_imp = r_eg.get('ok_nocional', True)
    _ok_acr = r_eg.get('ok_alpha_cr', True)
    _ok_geo = r_eg.get('ok_geometria', True)
    _non_sway = bool(r_eg.get('sistema_non_sway', False))
    _ns_l = bool(r_eg.get('non_sway_long', False))
    _ns_t = bool(r_eg.get('non_sway_transv', False))
    def _sim_eg(o):
        return r'\checkmark' if o else r'$\times$'
    # Item 1 — classificação sway/non-sway condicionada aos contraventamentos
    # nas DUAS direções: longitudinal (issue 14, \S8b.1) e transversal (issue 31,
    # \S8b.2). Pórtico biarticulado SEM esses sistemas é mecanismo sway.
    if _non_sway:
        _item_nonsway = (
            '  \\item Sistema \\textbf{non-sway} nas duas direções: '
            'contraventamento \\textbf{vertical} (\\S8b.1) e '
            '\\textbf{transversal} (\\S8b.2) verificados '
            + _sim_eg(True) + ';\n'
        )
    else:
        _falhas = []
        if not _ns_l:
            _falhas.append('longitudinal (\\S8b.1)')
        if not _ns_t:
            _falhas.append('transversal (\\S8b.2)')
        _item_nonsway = (
            '  \\item \\textbf{Estabilidade lateral não demonstrada} '
            '(\\emph{mecanismo sway}, $\\alpha_{cr,sway}\\to 0$) na(s) direção(ões): '
            + ', '.join(_falhas) + ' '
            + _sim_eg(False) + ';\n'
        )
    parts.append(
        '% ── 8b. Estabilidade global ────────────────────────────\n'
        '\\section*{8b. Estabilidade Global -- P-$\\Delta$, '
        'Forças Nocionais e $\\alpha_{cr}$}\n\n'
        'A análise adotada é de \\textbf{1.\\textsuperscript{a} ordem} '
        '(Castigliano biarticulada). '
        'A estabilidade de \\textbf{barra} está coberta por EC5~\\S6.3.2 '
        '($k_c$) e \\S6.3.3 ($k_{crit}$). '
        'A escala \\textbf{global} verifica-se por analogia com '
        'EN~1993-1-1~\\S5.2.1 ($\\alpha_{cr}$) e \\S5.3.2 '
        '(forças nocionais $\\varphi$), face ao silêncio do EC5 sobre '
        'limiares numéricos de pórtico. O $\\alpha_{cr,arco}$ abaixo é o modo de '
        '\\emph{snap-through} do arco abatido -- \\textbf{não} o modo de '
        'deslocamento lateral (\\emph{sway}) do pórtico.\n\n'
        '\\textbf{Critérios de dispensa de 2.\\textsuperscript{a} ordem \\emph{global}:}\n'
        '\\begin{enumerate}\n'
        + _item_nonsway +
        '  \\item $\\alpha_{cr,arco}\\geq 10$ com $L_{ef}\\approx L/2$ (modo de arco);\n'
        '  \\item $w_{Ed}/f_c \\leq 0{,}05$ (abaixamento do freche);\n'
        '  \\item $H_{imp}/H_{Ed} \\leq 0{,}10$ (nocional coberta pelo empuxo).\n'
        '\\end{enumerate}\n'
        'A 2.\\textsuperscript{a} ordem de \\textbf{barra} ($\\alpha_{cr}$ com $L_{ef}=L$ ou $H$) pode ser $<10$ e está coberta por $k_c$ (EC5~\\S6.3.2) -- não exige, por si, análise global de 2.\\textsuperscript{a} ordem.\n\n'
        '\\begin{tabular}{@{}lll@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Limite / ref.} \\\\\n'
        '  \\midrule\n'
    )
    parts.append(
        f'  $H_{{Ed}}$ (empuxo 1.\\textsuperscript{{a}} ordem) & '
        f'{_br(r_eg.get("H_Ed_kN", 0), 1)}~kN & Castigliano \\\\\n'
    )
    parts.append(
        f'  $V_{{portal}}=2R_v$ & '
        f'{_br(r_eg.get("V_portal_kN", 0), 1)}~kN & \\\\\n'
    )
    parts.append(
        f'  $\\varphi=\\varphi_0\\alpha_h\\alpha_m$ & '
        f'{float(r_eg.get("phi", 0)):.5f} & EN~1993-1-1~\\S5.3.2 \\\\\n'
    )
    parts.append(
        f'  $H_{{imp}}=\\varphi\\,V$ & '
        f'{_br(r_eg.get("H_imp_kN", 0), 2)}~kN & \\\\\n'
    )
    parts.append(
        f'  $H_{{imp}}/H_{{Ed}}$ & '
        f'{float(r_eg.get("H_imp_over_H", 0)):.4f} & '
        f'$\\leq {_br(r_eg.get("lim_H_imp", 0.10), 2)}$ '
        f'{_sim_eg(_ok_imp)} \\\\\n'
    )
    parts.append(
        f'  $\\alpha_{{cr}}$ (governante) & '
        f'{_br(r_eg.get("alpha_cr", 0), 1)} & '
        f'$\\geq {_br(r_eg.get("alpha_cr_min", 10), 0)}$ '
        f'{_sim_eg(_ok_acr)} \\\\\n'
    )
    parts.append(
        f'  $k_{{II}}=1/(1-1/\\alpha_{{cr}})$ & '
        f'{_br(r_eg.get("k_II", 1), 4)} & amplificação \\\\\n'
    )
    parts.append(
        f'  $w_{{Ed}}/f_c$ & '
        f'{float(r_eg.get("w_over_f", 0)):.5f} & '
        f'$\\leq {_br(r_eg.get("lim_w_over_f", 0.05), 2)}$ '
        f'{_sim_eg(_ok_geo)} \\\\\n'
    )
    parts.append(
        f'  $e_0$ (pilar, nocional) & '
        f'{_br(r_eg.get("e_0_mm", 0), 2)}~mm & $\\varphi\\cdot H$ \\\\\n'
    )
    parts.append(
        f'  $M_{{imp}}$ pilar & '
        f'{_br(r_eg.get("M_imp_pilar_kNm", 0), 3)}~kN·m & $N\\cdot e_0$ \\\\\n'
    )
    _conc = _tex_escape(r_eg.get("conclusao", "—"))
    parts.append('  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n')
    parts.append(f'\\textbf{{Conclusão:}} {_conc}\n\n')
    # Registro explícito no memorial: análise feita e resultado
    _eg_ok = bool(r_eg) and bool(r_eg.get("ok", False))
    _eg_sim = r"\checkmark" if _eg_ok else r"$\times$"
    _eg_met = str(r_eg.get("metodo_analise", "—")).replace("_", r"\_")
    _eg_st = (
        r"\textbf{Verificado -- OK}"
        if _eg_ok
        else r"\textbf{Não conforme -- rever}"
    )
    _eg_body = (
        f"{_eg_sim}\\ {_eg_st}"
        f"\\quad método: \\texttt{{{_eg_met}}}"
        f"\\quad $\\alpha_{{cr,arco}}={_br(r_eg.get('alpha_cr', 0), 1)}$"
        f"\\quad $H_{{imp}}/H_{{Ed}}={float(r_eg.get('H_imp_over_H', 0)):.4f}$"
        f"\\quad $\\eta_{{crit}}={float(r_eg.get('eta', 0)):.4f}$"
        "\\\\[0.35em]\n"
        "Análise de estabilidade global \\textbf{executada} no pipeline "
        "e \\textbf{registrada} neste memorial. "
        + (
            "Dispensa-se análise de 2.\\textsuperscript{a} ordem global; "
            "mantém-se a análise de 1.\\textsuperscript{a} ordem (Castigliano) "
            "com estabilidade de barra por $k_c$."
            if _eg_ok
            else "Requer reanálise com efeitos de 2.\\textsuperscript{a} ordem."
        )
    )
    parts.append(
        "\\registonota{Registro -- Estabilidade global "
        "(P-$\\Delta$ / nocionais / $\\alpha_{cr}$)}{"
        + _eg_body
        + "}\n\n"
    )
    parts.append(
        '\\textit{Nota:} num pórtico biarticulado baixo ($H\\approx 7$~m) com '
        'empuxo $H$ já da ordem de $1{,}6$~MN, a força nocional e o P-$\\Delta$ '
        'global são tipicamente desprezáveis. O empuxo de 1.\\textsuperscript{a} '
        'ordem governa fundações e L1/L3.\n\n'
    )

    # ── 8b.1 Contraventamento vertical (issue 14) ──────────────
    if r_cvv:
        _cvv_okN = bool(r_cvv.get('ok_diag', False))
        _cvv_okd = bool(r_cvv.get('ok_delta', False))
        parts.append(
            '% ── 8b.1 Contraventamento vertical ─────────────────────\n'
            '\\subsection*{8b.1 Contraventamento Vertical -- '
            'Caminho de Carga Lateral à Fundação '
            '(EN~1993-1-1~\\S5.3.2+\\S6.2.3)}\n\n'
            'Com pilares biarticulados (topo e base) e ligações viga-pilar '
            'rotuladas não há ação de pórtico: a estabilidade lateral longitudinal '
            'é provida por \\textbf{cruzes de St.\\ André} nas paredes, que '
            'conduzem a força de vento $\\theta=0^\\circ$ (mais a força nocional '
            'EN~1993-1-1~\\S5.3.2) do nível da cobertura \\textbf{até a fundação}.\n\n'
            '\\begin{tabular}{@{}lll@{}}\n'
            '  \\toprule\n'
            '  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Ref./limite} \\\\\n'
            '  \\midrule\n'
            f'  $F_{{w,\\theta=0}}$ (vento long.) & {_br(r_cvv.get("F_vento0_kN", 0), 1)}~kN & NBR 6123 \\\\\n'
            f'  $H_{{imp}}=\\varphi\\,V$ (nocional) & {_br(r_cvv.get("H_imp_kN", 0), 1)}~kN & \\S5.3.2 \\\\\n'
            f'  $V_{{lat}}$ total & {_br(r_cvv.get("V_lat_total_kN", 0), 1)}~kN & {_i(r_cvv.get("n_paineis", 2))} painéis \\\\\n'
            f'  $V$ por painel & {_br(r_cvv.get("V_painel_kN", 0), 1)}~kN & \\\\\n'
            f'  Diagonal & $d={_i(r_cvv.get("d_mm", 0))}$~mm {r_cvv.get("aco", "S235")} & $\\beta={_br(r_cvv.get("beta_deg", 0), 1)}^\\circ$ \\\\\n'
            f'  $N_{{diag}}\\leq N_{{t,Rd}}$ & {_br(r_cvv.get("N_diag_kN", 0), 1)} $\\leq$ {_br(r_cvv.get("N_t_Rd_kN", 0), 1)}~kN & $\\eta={_br(r_cvv.get("eta_diag_N", 0), 3)}$ {_sim_eg(_cvv_okN)} \\\\\n'
            f'  $H_{{base}}$ (cortante) & {_br(r_cvv.get("H_base_kN", 0), 1)}~kN & à fundação \\\\\n'
            f'  $N_{{uplift}}$ (arrancamento) & {_br(r_cvv.get("N_uplift_kN", 0), 1)}~kN & ancoragem \\\\\n'
            f'  $\\delta\\leq H/300$ & {_br(r_cvv.get("delta_mm", 0), 2)} $\\leq$ {_br(r_cvv.get("delta_lim_mm", 0), 2)}~mm & $\\eta={_br(r_cvv.get("eta_delta", 0), 3)}$ {_sim_eg(_cvv_okd)} \\\\\n'
            '  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n'
            '\\textbf{Direção transversal (no plano do pórtico):} tratada na '
            '\\S8b.2 (diafragma de cobertura + frontões contraventados).\n\n'
        )

    # ── 8b.2 Contraventamento transversal (issue 31) ──────────
    if r_cvt:
        _cvt_okN = bool(r_cvt.get('ok_diag', False))
        _cvt_okd = bool(r_cvt.get('ok_delta', False))
        parts.append(
            '% ── 8b.2 Contraventamento transversal ──────────────────\n'
            '\\subsection*{8b.2 Contraventamento Transversal -- '
            'Diafragma de Cobertura + Frontões (EN~1993-1-1~\\S5.3.2+\\S6.2.3)}\n\n'
            'No plano do pórtico ($\\perp$ cumeeira), os pilares birotulados '
            'formam um mecanismo \\emph{sway}. A estabilidade é provida pelo '
            '\\textbf{diafragma de cobertura} (viga horizontal ao longo do '
            'comprimento), que conduz o vento $\\theta=90^\\circ$ (mais a força '
            'nocional) aos \\textbf{frontões contraventados} (cruzes de St.\\ '
            'André) e destes \\textbf{à fundação}. Com os topos travados pelo '
            'diafragma, $l_{ef}=1{,}0\\,H$ (non-sway) fica \\textbf{legítimo} '
            'para os pilares.\n\n'
            '\\begin{tabular}{@{}lll@{}}\n'
            '  \\toprule\n'
            '  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Ref./limite} \\\\\n'
            '  \\midrule\n'
            f'  Arrasto $\\theta=90^\\circ$ (topo) & {_br(r_cvt.get("H_vento_topo_kN", 0), 1)}~kN & {_i(r_cvt.get("n_colunas", 0))} pilares, NBR 6123 \\\\\n'
            f'  $H_{{imp}}=\\varphi\\,V$ (nocional) & {_br(r_cvt.get("H_imp_kN", 0), 1)}~kN & \\S5.3.2 \\\\\n'
            f'  $H_{{tr}}$ total & {_br(r_cvt.get("H_tr_kN", 0), 1)}~kN & \\\\\n'
            f'  $N_{{corda}}$ diafragma & {_br(r_cvt.get("N_corda_kN", 0), 1)}~kN & $M/B$ (ao beiral) \\\\\n'
            f'  $R_{{frontão}}$ & {_br(r_cvt.get("R_gable_kN", 0), 1)}~kN & $H_{{tr}}/2$ \\\\\n'
            f'  Diagonal frontão & $d={_i(r_cvt.get("d_mm", 0))}$~mm {r_cvt.get("aco", "S235")} & $\\beta={_br(r_cvt.get("beta_deg", 0), 1)}^\\circ$ \\\\\n'
            f'  $N_{{diag}}\\leq N_{{t,Rd}}$ & {_br(r_cvt.get("N_diag_kN", 0), 1)} $\\leq$ {_br(r_cvt.get("N_t_Rd_kN", 0), 1)}~kN & $\\eta={_br(r_cvt.get("eta_diag_N", 0), 3)}$ {_sim_eg(_cvt_okN)} \\\\\n'
            f'  $H_{{base}}$ (cortante) & {_br(r_cvt.get("H_base_kN", 0), 1)}~kN & à fundação \\\\\n'
            f'  $N_{{uplift}}$ (arrancamento) & {_br(r_cvt.get("N_uplift_kN", 0), 1)}~kN & ancoragem \\\\\n'
            f'  $\\delta\\leq H/300$ & {_br(r_cvt.get("delta_mm", 0), 2)} $\\leq$ {_br(r_cvt.get("delta_lim_mm", 0), 2)}~mm & $\\eta={_br(r_cvt.get("eta_delta", 0), 3)}$ {_sim_eg(_cvt_okd)} \\\\\n'
            '  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n'
            'Com o diafragma verificado, o dimensionamento dos pilares '
            '(\\S8) e o modelo $pilar\\_vento\\_90$ (biapoiado, topo travado) '
            'são legítimos nesta direção.\n\n'
        )
        # Corda do diafragma = elemento de beiral (issue 32)
        if r_cb:
            parts.append(
                '\\textit{Corda do diafragma (elemento de beiral -- issue~32):} '
                'a \\textbf{terça de beiral} (MLC~GL24h, contínua) atua como banzo '
                f'do diafragma, com $N_{{corda}}={_br(r_cb.get("N_corda_kN", 0), 1)}$~kN '
                '($\\pm$, inverte com o sentido do vento). Verificada como '
                'flexo-axial: flexo-\\textbf{compressão} (EC5~\\S6.3.2, '
                f'$\\eta={_br(r_cb.get("eta_compressao", 0), 3)}$) e flexo-'
                f'\\textbf{{tração}} (\\S6.2.3, $\\eta={_br(r_cb.get("eta_tracao", 0), 3)}$) '
                f'-- $\\eta_{{\\mathrm{{gov}}}}={_br(r_cb.get("eta", 0), 3)}$. '
                f'\\textbf{{Continuidade obrigatória}}: {_i(r_cb.get("n_emendas", 0))} '
                f'emenda(s) ao longo de {_br(r_cb.get("L_comp_m", 46), 0)}~m, cada uma '
                f'transferindo $N_{{corda}}$ (chapa/parafusos, EC5~\\S8) -- sem '
                'continuidade o diafragma não funciona.\n\n'
            )

    # ── 8b.3 Auditoria do empuxo acoplado (issue 38) ───────────
    r_emp = _clean_dict(resultados.get("empuxo_acoplado", {}))
    if r_emp:
        parts.append(
            '% ── 8b.3 Empuxo acoplado (issue 38) ────────────────────\n'
            '\\subsection*{8b.3 Auditoria do Empuxo Acoplado -- Coerência do '
            'Modelo (issue~38)}\n\n'
            'O empuxo $H$ do modelo é obtido por Castigliano assumindo '
            '\\textbf{apoio horizontal indeslocável} no springing (topo do '
            'pilar). Auditou-se quanto desse empuxo \\emph{realmente} se '
            'desenvolve dada a rigidez horizontal real do apoio '
            '(\\texttt{empuxo\\_acoplado.py}).\n\n'
        )
        parts.append(
            'A rigidez horizontal do arco no springing é '
            f'$k_{{arco}}={_br(r_emp.get("k_arco_kNm", 0), 0)}$~kN/m; o pilar '
            '\\textbf{biarticulado} é um mecanismo lateral no plano '
            f'($k_{{pilar}}=0$; mesmo engastado $k\\approx{_br(r_emp.get("k_pilar_eng_kNm", 0), 0)}$~kN/m, '
            f'${_br(r_emp.get("razao_k_arco_pilar", 0), 0)}\\times$ mais mole). '
            'Por duas molas em série $H_{dev}=H_{rig}\\,k/(k+k_{arco})$, só se '
            f'desenvolve $H_{{dev}}\\approx{_br(r_emp.get("H_dev_engastada_kN", 0), 1)}$~kN de '
            f'${_br(r_emp.get("H_rigido_kN", 0), 0)}$~kN '
            f'(${_br(r_emp.get("frac_desenvolvida", 0) * 100, 1)}\\%$) -- o empuxo '
            '\\textbf{praticamente não se desenvolve}.\n\n'
        )
        parts.append(
            '\\textbf{Consequências:} a viga tende a \\textbf{biapoiada} -- $M$ '
            f'passa de ${_br(r_emp.get("M_modelo_kNm", 0), 0)}$ (modelo, empuxo '
            f'rígido) para ${_br(r_emp.get("M0_biapoiada_kNm", 0), 0)}$~kN·m '
            f'($+{_br(r_emp.get("delta_M_pct", 0), 0)}\\%$). O pilar recebe '
            'esforço horizontal $\\approx 0$: o cenário de \\emph{colapso do pilar} '
            '($M\\sim1300$~kN·m) \\textbf{não ocorre} (o pilar não atrai o empuxo).\n\n'
        )
        parts.append(
            '\\registonota{Decisão de modelo (issue~38/35 -- IMPLEMENTADA)}{'
            '\\textbf{Opção B adotada e implementada} -- a viga é dimensionada '
            f'\\textbf{{BIAPOIADA}} ($M=M_0\\approx{_br(r_emp.get("M0_biapoiada_kNm", 0), 0)}$~kN·m, '
            'sem o alívio do empuxo). O \\textbf{tirante de base foi removido} (não '
            'fecha empuxo que não se desenvolve, não resiste ao \\emph{uplift} '
            'vertical). A ancoragem responde ao \\emph{uplift} (chumbadores, mín. '
            'construtivo 4). Sem o empuxo o cortante do beiral sobe e a ligação '
            'L1/L1c exige \\textbf{reforço $\\perp$ às fibras} (parafusos, §8.7.2). '
            'A flecha é a da viga biapoiada (ELS reavaliado).}\n\n'
        )

    # ── 8c. Impacto de veículo ─────────────────────────────────
    _iv_ok = bool(r_iv) and bool(r_iv.get("ok", False))
    _iv_f = r_iv.get("forcas", {}) if isinstance(r_iv.get("forcas"), dict) else {}
    _iv_casos = r_iv.get("casos", []) if isinstance(r_iv.get("casos"), list) else []
    parts.append(
        '% ── 8c. Impacto de veículo ─────────────────────────────\n'
        '\\section*{8c. Impacto de Veículo em Pilares '
        '(Estacionamento)}\n\n'
        'Tratando-se de \\textbf{estacionamento coberto} com pilares '
        'acessíveis a veículos (laterais abertas), a verificação de '
        'choque é aplicável como \\textbf{ação acidental} '
        '(EN~1991-1-7). Não se combina com vento ELU.\n\n'
        '\\textbf{Forças estáticas equivalentes de projeto '
        '(veículos ligeiros):}\n'
        '\\begin{itemize}\n'
        f'  \\item $F_{{dx}} = {_br(_iv_f.get("F_dx_kN", 50), 0)}$~kN '
        '(direção de marcha);\n'
        f'  \\item $F_{{dy}} = {_br(_iv_f.get("F_dy_kN", 25), 0)}$~kN '
        '(transversal);\n'
        f'  \\item $h_{{\\mathrm{{imp}}}} = {_br(_iv_f.get("h_imp_m", 0.5), 2)}$~m '
        'acima do pavimento.\n'
        '\\end{itemize}\n'
        'Combinação EN~1990~\\S6.4.3.3: $A_d + G + \\psi_2 Q$ '
        '($\\psi_2\\approx 0$ na cobertura). '
        f'$k_{{\\mathrm{{mod}}}} = {_br(r_iv.get("k_mod", 0.9), 2)}$ '
        '(duração \\textbf{instantânea}).\n\n'
        '\\begin{tabular}{@{}llcccc@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Pilar / caso} & $N_d$ & $M_d$ & $V_d$ & '
        '$\\eta$ & \\\\\n'
        '  \\midrule\n'
    )
    for _c in _iv_casos:
        if not isinstance(_c, dict):
            continue
        _cok = bool(_c.get("ok", False))
        parts.append(
            f'  {_c.get("rotulo", "—").replace("_", " ")} & '
            f'{_br(_c.get("N_d_kN", 0), 1)}~kN & '
            f'{_br(_c.get("M_d_kNm", 0), 2)}~kN·m & '
            f'{_br(_c.get("V_d_kN", 0), 2)}~kN & '
            f'{_eta(_c):.4f} & '
            f'{"\\checkmark" if _cok else "$\\\\times$"} \\\\\n'
        )
    parts.append('  \\bottomrule\n\\end{tabular}\n\n')
    _iv_sim = r"\checkmark" if _iv_ok else r"$\times$"
    _iv_st = (
        r"\textbf{Verificado -- OK}"
        if _iv_ok
        else r"\textbf{Não conforme -- proteger / reforçar}"
    )
    _iv_rec = _tex_escape(r_iv.get("recomendacao", "—"))
    _iv_body = (
        f"{_iv_sim}\\ {_iv_st}"
        f"\\quad $\\eta_{{\\mathrm{{gov}}}}={_eta(r_iv):.4f}$"
        f"\\quad gov: {_tex_escape(str(r_iv.get('gov', '—')).replace('_', ' '))}"
        "\\\\[0.35em]\n"
        f"{_iv_rec}"
    )
    parts.append(
        "\\registonota{Registro -- Impacto de veículo (EN~1991-1-7)}{"
        + _iv_body
        + "}\n\n"
    )
    parts.append(
        '\\textit{Nota:} mesmo com $\\eta\\leq 1$, recomenda-se '
        'defensas ou pilaretes junto a pilares em corredores de '
        'circulação (limitação de dano local e proteção da MLC). '
        'Confirmar $F_{dx}/F_{dy}$ com AN nacional ou especificação '
        'do cliente se veículos pesados forem admitidos.\n\n'
    )

    # ── Situação transitória de içamento (issue 26) ───────────────────────────
    if r_ic:
        _ic_ok = bool(r_ic.get("ok", True))
        parts.append(
            '\\vspace{4pt}\n'
            '\\subsection*{Situação transitória -- Içamento da viga '
            '(montagem, EN~1991-1-6)}\n\n'
            'Fase de montagem: a viga maciça é içada em \\textbf{2 pontos} a '
            f'$0{{,}}207\\,L$ ({_tex_escape(r_ic.get("esquema", ""))}), '
            'sem contraventamento lateral (terças ainda não montadas). '
            'Combinação: $w_d=\\gamma_G\\,\\varphi_{dyn}\\,g$ com '
            f'$\\gamma_G={_br(r_ic.get("gamma_G", 1.35), 2)}$, '
            f'$\\varphi_{{dyn}}={_br(r_ic.get("phi_dyn", 1.1), 2)}$ '
            '(amplificação dinâmica do içamento); duração instantânea '
            f'($k_{{mod}}={_br(r_ic.get("k_mod", 0.9), 2)}$).\n\n'
            '{\\small\\begin{tabular}{@{}lll@{}}\n  \\toprule\n'
            '  \\textbf{Efeito} & \\textbf{Valor} & $\\eta$ \\\\\n  \\midrule\n'
            f'  Peso de cálculo $W$ / reação & '
            f'{_br(r_ic.get("W_total_kN", 0), 1)}~kN / '
            f'{_br(r_ic.get("R_ponto_kN", 0), 1)}~kN/ponto & \\\\\n'
            f'  Flexão ($M^-={_br(r_ic.get("M_neg_kNm", 0), 1)}$, '
            f'$M^+={_br(r_ic.get("M_pos_kNm", 0), 1)}$~kN·m) & '
            f'$\\sigma_m={_br(r_ic.get("sigma_m_pos_MPa", 0), 2)}$~MPa & '
            f'{_br(r_ic.get("eta_flexao", 0), 4)} \\\\\n'
            f'  Cortante & $\\tau={_br(r_ic.get("tau_MPa", 0), 3)}$~MPa & '
            f'{_br(r_ic.get("eta_cisalhamento", 0), 4)} \\\\\n'
            f'  LTB s/ contravento (Eq.~6.35) & '
            f'$l_{{ef}}={_br(r_ic.get("l_ef_LTB_m", 0), 1)}$~m, '
            f'$k_{{crit}}={_br(r_ic.get("k_crit", 0), 3)}$ & '
            f'{_br(r_ic.get("eta_LTB", 0), 4)} \\\\\n'
            '  \\bottomrule\n\\end{tabular}}\n\n'
            f'$\\eta_{{\\mathrm{{gov}}}}={_br(r_ic.get("eta", 0), 4)}$ '
            f'({_tex_escape(str(r_ic.get("eta_gov_key", "")))}) -- '
            + ('\\textbf{OK}' if _ic_ok else '\\textbf{verificar}')
            + '. Os momentos de peso próprio na montagem são pequenos face aos '
            'de serviço; a LTB sem contraventamento reduz a capacidade '
            '($k_{crit}<1$) mas a solicitação é baixa. \\textit{Confirmar o '
            'esquema de rigging (pontos, ângulo das lingas) no plano de '
            'montagem.}\n\n'
        )

    parts.append(
        '% ── 9. Contraventamento / integridade da cobertura ────────────\n'
        '\\section*{9. Contraventamento -- Integridade Estrutural da Cobertura}\n\n'
        'O contraventamento horizontal \\textbf{não é acessório}: é o que torna as\n'
        'terças apoios laterais válidos da viga principal. Sem ele, a hipótese\n'
        '$l_{ef}=0{,}9s$ da flambagem lateral (EC5~\\S6.3.3) deixa de ser legítima.\n\n'
        '\\textbf{Cadeia de forças (plano da cobertura):}\n'
        '\\begin{enumerate}\n'
        '  \\item Viga MLC comprimida ($N$ + $M$) gera força de estabilização\n'
        '        (EC5~\\S9.2.5).\n'
        '  \\item Terças atuam como \\textbf{bielas} (compressão + rigidez $EA/L$).\n'
        '  \\item Cruzes de St.~André nos módulos extremos (diagonal tracionada).\n'
        '  \\item Reações no pórtico de extremidade $\\rightarrow$ fundação.\n'
        '\\end{enumerate}\n\n'
        '\\vspace{4pt}\n'
        '\\subsection*{9.1 Compressão a estabilizar e sistema (EC5~\\S9.2.5)}\n\n'
        '\\begin{tabular}{@{}lll@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Ref.} \\\\\n'
        '  \\midrule\n'
        '  $N_{axial}$ (biarticulada) & '
    )
    parts.append(_br(r_cv.get('N_axial_kN', 0), 2))
    parts.append('~kN & Análise \\\\\n  $N_{flex}=(1-k_{crit})M_d/h$ & ')
    parts.append(_br(r_cv.get('N_flex_kN', 0), 2))
    parts.append('~kN & \\S9.2.5.2 \\\\\n  $N_d$ (estabilizar) & ')
    parts.append(_br(r_cv.get('N_d_kN', 0), 2))
    parts.append('~kN & \\\\\n  N.º de vigas $n$ (por plano) & ')
    parts.append(f'{_i(r_cv.get('n_por_plano', 9))}')
    parts.append(f' & {_i(r_cv.get("n_planos", 2))} planos independentes \\\\\n  $\\ell$ (vão do sistema) & ')
    parts.append(_br(r_cv.get('ell_m', 46), 1))
    parts.append('~m & Entre baías rígidas \\\\\n  $k_\\ell=\\min(1,\\sqrt{15/\\ell})$ & ')
    parts.append(_br(r_cv.get('k_ell', 0), 3))
    parts.append(' & \\S9.2.5.3 Eq.~9.38 \\\\\n  $q_d=k_\\ell n N_d/(k_{f,3}\\ell)$ & ')
    parts.append(_br(r_cv.get('q_d_kNpm', 0), 4))
    parts.append('~kN/m &\n    $k_{f,3}=')
    parts.append(_br(r_cv.get('k_f3', 30), 0))
    parts.append('$ (Tab.~9.2) \\\\\n  $R_{ext}=q_d\\ell/2$ (por plano) & ')
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
    parts.append('$ \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n')
    parts.append(
        '\\textit{Fatores de modificação} (EC5 Tab.~9.2, valores recomendados '
        'sublinhados na norma): $k_s=4$ ($1$--$4$), $k_{f,2}=80$ ($80$--$100$, MLC), '
        '$k_{f,3}=30$ ($30$--$80$). \\textbf{Dois planos de cobertura independentes} '
        '(um por vão), cada um estabilizando $n=9$ vigas com o seu próprio '
        'contraventamento; a força de estabilização de um plano \\textbf{não} '
        'transita pelo outro — não há duplicação. Aumentar o número de baías com '
        'cruzes reduz $\\ell$ mas eleva $k_\\ell$ e a reação, logo mantêm-se apenas '
        'as \\textbf{baías extremas}.\n\n'
    )
    parts.append('\\subsection*{9.2 Diagonal de aço (EN~1993-1-1~\\S6.2.3)}\n\n')
    parts.append('\\begin{tabular}{@{}lll@{}}\n  \\toprule\n  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Obs.} \\\\\n  \\midrule\n  Layout & Cruzes nos ')
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
    parts.append(f'{r_cv.get('d_barra_mm', 18):.0f}')
    parts.append('~mm ')
    parts.append(f'{r_cv.get('aco', 'S235')}')
    parts.append(' &\n    $A=')
    parts.append(_br(r_cv.get('A_mm2', 0), 1))
    parts.append('$~mm² \\\\\n  $F_{diag}$ & ')
    parts.append(_br(r_cv.get('F_diag_kN', 0), 2))
    parts.append('~kN & Tração (1 diagonal ativa) \\\\\n  $N_{t,Rd}$ & ')
    parts.append(_br(r_cv.get('N_t_Rd_kN', 0), 2))
    parts.append('~kN & $A f_y/\\gamma_{M0}$ \\\\\n  $\\eta_N$ (diagonal) & ')
    parts.append(f'{_eta(r_cv, "eta_diag_N"):.4f}')
    parts.append(' & \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\subsection*{9.3 Flecha do sistema e terça-biela}\n\n\\begin{tabular}{@{}lll@{}}\n  \\toprule\n  \\textbf{Verificação} & \\textbf{Valor} & $\\eta$ \\\\\n  \\midrule\n  $\\delta\\leq\\ell/500$ (rigidez global) &\n    ')
    parts.append(f'{r_cv.get('delta_mm', 0):.2f}')
    parts.append('~mm $\\leq$ ')
    parts.append(f'{r_cv.get('delta_lim_mm', 0):.1f}')
    parts.append('~mm & ')
    parts.append(f'{_eta(r_cv, "eta_delta"):.4f}')
    parts.append(' \\\\\n  Terça-biela flexo-compr. \\textbf{combinada} (EC5~\\S6.3.2, Eq.~6.23/6.24) &\n    $\\sigma_{c}=')
    parts.append(_br(r_tfc.get('sigma_c_MPa', 0), 3))
    parts.append('$, $\\sigma_{m,y}=')
    parts.append(_br(r_tfc.get('sigma_my_MPa', 0), 3))
    parts.append('$~MPa;\n    $k_{c,z}=')
    parts.append(_br(r_tfc.get('k_c_z', 0), 3))
    _vg = {"Eq.6.23": "Eq.~6{,}23", "Eq.6.24": "Eq.~6{,}24"}.get(
        str(r_tfc.get('verif_gov', '--')), '--')
    parts.append('$ (' + _vg + ') & ')
    parts.append(f'{_eta(r_tfc):.4f}')
    parts.append(' \\\\\n  Rigidez terça $EA/L\\geq C_{\\min}$ &\n    ')
    parts.append(_br(r_cv.get('C_terca_kNpm', 0), 0))
    parts.append(' $\\geq$ ')
    parts.append(_br(r_cv.get('C_min_kNpm', 0), 0))
    parts.append('~kN/m & ')
    parts.append(f'{_eta(r_cv, "eta_C_terca"):.4f}')
    parts.append(' \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\subsection*{9.4 Função estrutural da cobertura (acoplamento ao LTB)}\n\n\\begin{tabular}{@{}ll@{}}\n  \\toprule\n  \\textbf{Indicador} & \\textbf{Resultado} \\\\\n  \\midrule\n  $\\mathtt{cobertura\\_ok}$ & ')
    parts.append('\\textbf{Sim}' if cob_ok else '\\textbf{Não}')
    parts.append(' \\\\\n  Restrição lateral das terças & ')
    parts.append(cob_txt)
    parts.append(' para LTB \\\\\n  $l_1$ efetivo adotado & ')
    parts.append(_br(l_1_ef, 3))
    parts.append('~m \\\\\n  $\\eta$ governante (contravent.) & ')
    parts.append(f'{_eta(r_cv):.4f}')
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
    parts.append('~kg) \\\\\n  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n\\textit{Nota:} vento no sentido do comprimento do galpão (eixo~$Y$) e\ncontraventamento vertical de frontões \\textbf{não} estão neste módulo --\nsão sistema global distinto (contraventamento vertical em \\S8b.1; transversal em \\S8b.2). Aqui trata-se apenas da estabilização das\nvigas e da integridade do plano da cobertura (EC5~\\S9.2.5).\n\n% ── 10. Verificações ELS ──────────────────────────────────────\n\\section*{10. Verificações ELS -- Flechas}\n\n\\begin{tabular}{@{}lllcc@{}}\n  \\toprule\n  \\textbf{Verificação} & \\textbf{Valor} & \\textbf{Limite} & $\\eta$ & \\\\\n  \\midrule\n  $w_{inst}(S1) \\leq L/300$ & ')
    parts.append(f'{r_els.get('w_S1_mm', 0):.2f}~mm & ')
    parts.append(f'{r_els.get('lim_inst_mm', 67.5):.2f}~mm & ')
    parts.append(f'{eta_S1:.4f} & ')
    parts.append(f'{sim_S1} \\\\\n')
    parts.append('  $w_{net,fin} \\leq L/250$ & ')
    parts.append(f'{r_els.get('w_net_fin_mm', 0):.2f}~mm & ')
    parts.append(f'{r_els.get('lim_fin_mm', 81.0):.2f}~mm & ')
    parts.append(f'{eta_nf:.4f} & ')
    parts.append(f'{sim_nf} \\\\\n')
    parts.append('  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n')
    parts.append(
        f'Característico (cat.~H, $Q$ e vento \\textbf{{não}} concomitantes -- '
        f'issue 3): governa \\textbf{{{_tex_escape(r_els.get("gov_caracteristico", "vento"))}}} '
        f'($G{{+}}Q={_br(r_els.get("w_char_Q_mm", 0), 2)}$~mm; '
        f'$G{{+}}W={_br(r_els.get("w_char_W_mm", 0), 2)}$~mm, vento pela NBR~6123). '
        f'Sucção (uplift) $G{{+}}W_{{suc}}={_br(r_els.get("w_char_up_mm", 0), 2)}$~mm '
        f'(informativo).\n\n'
        f'Deformação por cisalhamento (EC5~\\S2.2.3(2) e Anexo~B, '
        f'$\\kappa_s={_br(r_els.get("k_s", 1.2), 1)}$, '
        f'$G_{{mean}}={_br(r_els.get("G_mean_GPa", 0), 2)}$~GPa): a flecha inclui '
        f'a parcela de cortante $w_v=\\int \\kappa_s V/(G\\,A(x))\\,dx$. Em S1: '
        f'flexão $={_br(r_els.get("w_S1_flex_mm", 0), 2)}$~mm, '
        f'cisalhamento $={_br(r_els.get("w_S1_cis_mm", 0), 2)}$~mm '
        f'(${_br(r_els.get("pct_cis_S1", 0), 1)}\\%$ do total).\n\n'
        f'Fluência (EC5~\\S2.3.2.2, $\\psi_2=0$): '
        f'$w_{{fin}} = {_br(r_els.get("w_G_mm", 0), 2)}(1+{k_def:.2f}) + '
        f'{_br(r_els.get("w_var_fin_mm", 0), 2)} = {_br(r_els.get("w_fin_mm", 0), 2)}$~mm '
        f'(variável dominante: {_tex_escape(r_els.get("var_gov_fin", "vento"))}).\n\n'
    )
    # ── Tirante de base (se ativo) ─────────────────────────────
    if com_tirante and r_tir:
        parts.append(
            '\n% ── 10b. Tirante de base ─────────────────────────────────\n'
            '\\section*{10b. Tirante de Base -- Fecho do Empuxo}\n\n'
            'O pórtico biarticulado gera empuxo horizontal $H$ nas bases '
            '(Castigliano). Em vez de transmitir $H$ à sapata (chumbadores L3), '
            'adota-se \\textbf{tirante de aço ao nível do piso} ligando as bases '
            'de cada vão -- solução usual em coberturas MLC / arcos abatidos.\n\n'
            '\\begin{tabular}{@{}lll@{}}\n'
            '  \\toprule\n'
            '  \\textbf{Parâmetro} & \\textbf{Valor} & \\textbf{Obs.} \\\\\n'
            '  \\midrule\n'
        )
        parts.append(
            f'  $H_{{\\mathrm{{arco}}}}$ (ELU gov.) & '
            f'{_br(r_tir.get("H_arco_kN", r_tir.get("T_d_kN", 0)), 1)}~kN & '
            f'Castigliano \\\\\n'
        )
        parts.append(
            f'  $T_d$ (tirante) & '
            f'{_br(r_tir.get("T_d_kN", 0), 1)}~kN & $=H_{{\\mathrm{{arco}}}}$ \\\\\n'
        )
        parts.append(
            f'  $H_{{\\mathrm{{sapata}}}}$ & '
            f'{_br(r_tir.get("H_sapata_kN", 0), 1)}~kN & residual $\\approx 0$ \\\\\n'
        )
        parts.append(
            f'  Comprimento $L$ & {_br(r_tir.get("L_m", geo.L), 2)}~m & '
            f'vão do pórtico \\\\\n'
        )
        parts.append(
            f'  Aço / $\\varnothing$ & {r_tir.get("aco", "S355")} / '
            f'{_br(r_tir.get("d_mm", 0), 0)}~mm & '
            f'{"auto" if r_tir.get("d_auto") else "fixo"} \\\\\n'
        )
        parts.append(
            f'  $A$ & {_br(r_tir.get("A_mm2", 0), 0)}~mm$^2$ & \\\\\n'
        )
        parts.append(
            f'  $N_{{t,Rd}}=A f_y/\\gamma_{{M0}}$ & '
            f'{_br(r_tir.get("N_t_Rd_kN", 0), 1)}~kN & EN~1993-1-1~\\S6.2.3 \\\\\n'
        )
        parts.append(
            f'  $\\eta$ & {_eta(r_tir):.4f} & '
            f'alvo {_br(r_tir.get("eta_alvo", 0.75), 2)} \\\\\n'
        )
        parts.append(
            f'  $\\delta_{{\\mathrm{{el}}}}$ & '
            f'{_br(r_tir.get("delta_el_mm", 0), 1)}~mm & '
            f'$TL/(EA)$ \\\\\n'
        )
        parts.append(
            f'  Quantitativo & {r_tir.get("n_barras", 0)} barras / '
            f'{_br(r_tir.get("peso_total_kg", 0), 0)}~kg & '
            f'2 vãos $\\times$ n pórticos \\\\\n'
        )
        parts.append(
            '  \\bottomrule\n'
            '\\end{tabular}\n\n'
            '\\textit{Nota:} com tirante, a L3 (sapata lateral) deixa de ser '
            'governada por $H$ -- chumbadores construtivos e $\\eta=\\eta_N$ '
            '(compressão $N$). Ancoragem do tirante e proteção a impacto '
            'no estacionamento a detalhar em projeto de execução.\n\n'
        )
        # Hipótese de modelagem + flexibilidade (issue 24)
        _imp = r_tir.get("impacto_flexibilidade", {})
        parts.append(
            '\\textit{Hipótese de modelagem (empuxo $H$):} o empuxo foi obtido '
            'por \\textbf{Castigliano assumindo apoio horizontal indeslocável} '
            'nas bases (arco 1$\\times$ hiperestático); a \\textbf{flexibilidade '
            'axial do tirante} ($\\delta=TL/EA$) \\textbf{não} foi realimentada '
            'na análise. É conservador para o tirante ($H_{\\mathrm{rígido}}$ é '
            'o máximo).\n\n'
        )
        if _imp:
            parts.append(
                '\\textit{Avaliação da flexibilidade (issue 24):} rigidez '
                f'horizontal do arco ${_br(_imp.get("k_arco_kNmm", 0), 0)}$~kN/mm '
                f'vs. do tirante ${_br(_imp.get("k_tirante_kNmm", 0), 0)}$~kN/mm '
                f'($\\delta_{{\\mathrm{{tir}}}}={_br(_imp.get("delta_tirante_mm", 0), 1)}$~mm). '
                'Um modelo de 2 molas em série (tirante como único apoio) daria '
                f'$H\\approx{_br(_imp.get("H_flex_2molas_kN", 0), 0)}$~kN, mas '
                '\\textbf{ignora} a restrição paralela de ancoragem e '
                'contraventamento das bases; na estrutura real $H$ permanece '
                'próximo do rígido. \\textbf{Não é necessário acoplar} para o '
                'dimensionamento do tirante ($T=H$ máximo, conservador); um '
                'modelo de pórtico acoplado só refinaria a flexão da viga.\n\n'
            )

        # ── 10c. Robustez do tirante no piso (issue 37) ──────────
        r_rob = r_tir.get("robustez_piso", {})
        if r_rob:
            r_imp = r_rob.get("impacto", {})
            r_cor = r_rob.get("corrosao", {})
            r_fog = r_rob.get("incendio", {})
            r_tro = r_rob.get("tropeco", {})
            parts.append(
                '\n% ── 10c. Robustez do tirante no piso ─────────────────────\n'
                '\\subsection*{10c. Robustez do tirante ao nível do piso '
                '(estacionamento -- issue~37)}\n\n'
            )
            parts.append(
                'O tirante está ao nível do piso ($z\\approx 0{,}08$~m) atravessando '
                'estacionamento coberto. Além da tração (\\S10b), verifica-se a '
                '\\textbf{exposição física} do elemento -- antes delegada a '
                '\\emph{"detalhar em execução"}. \\textbf{Proteção adotada:} '
                + _tex_escape(str(r_rob.get("protecao", "embutido"))) +
                ' (canaleta no contrapiso); o tirante é tratado como '
                '\\textbf{primário} (fecho de empuxo), postura conservadora enquanto '
                'a coerência do caminho de carga (issue~38) não é fechada.\n\n'
            )
            parts.append('\\begin{itemize}\n')
            parts.append(
                '  \\item \\textbf{Impacto de veículo (EN~1991-1-7):} força de '
                f'projeto $F_d={_br(r_imp.get("F_gov_kN", 0), 0)}$~kN. Uma barra nua '
                f'$d={_br(r_imp.get("d_mm", 0), 0)}$~mm no vão livre '
                f'($L={_br(r_imp.get("L_livre_m", 0), 2)}$~m) teria '
                f'$M_{{Ed}}={_br(r_imp.get("M_Ed_kNm", 0), 1)}$~kN·m contra '
                f'$M_{{pl,Rd}}={_br(r_imp.get("M_pl_Rd_kNm", 0), 1)}$~kN·m '
                f'($\\eta={_br(r_imp.get("eta_barra_nua", 0), 0)}$ -- \\textbf{{não '
                'resiste}). Com o tirante \\textbf{embutido}, a laje '
                '\\textbf{intercepta} o choque ($\\eta=0$): a proteção é o elemento '
                'verificado, não a barra.\n'
            )
            parts.append(
                '  \\item \\textbf{Corrosão (EN~335 UC3 / EN~ISO~12944 C3):} '
                f'sobreespessura de sacrifício $\\Delta r={_br(r_cor.get("delta_corr_mm", 0), 1)}$~mm '
                f'reduz $d={_br(r_cor.get("d_mm", 0), 0)}\\to{_br(r_cor.get("d_ef_mm", 0), 0)}$~mm '
                f'($-{_br(r_cor.get("perda_pct", 0), 0)}$\\% de $N_{{t,Rd}}$); a '
                'tração reverificada na seção efetiva dá '
                f'$\\eta={_br(r_cor.get("eta", 0), 3)}$ \\textbf{{(governa a robustez)}}.\n'
            )
            parts.append(
                '  \\item \\textbf{Incêndio (EN~1993-1-2):} '
                + _tex_escape(str(r_fog.get("verdito", ""))) + '\n'
            )
            parts.append(
                '  \\item \\textbf{Tropeço/serventia:} '
                + _tex_escape(str(r_tro.get("verdito", ""))) + '\n'
            )
            parts.append('\\end{itemize}\n\n')
            parts.append(
                '\\registonota{Requisitos de projeto -- tirante no piso (issue~37)}{'
                + _tex_escape("; ".join(str(x) for x in r_rob.get("requisitos", [])))
                + '}\n\n'
            )

    parts.append('\n% ── 11. Ligações ──────────────────────────────────────────────\n\\section*{11. Ligações}\n\n\\textit{Critério de projeto (uso público):} $\\eta_{\\mathrm{alvo}}=')
    parts.append(_br(eta_lig_alvo, 2))
    parts.append(
        '$ aplica-se aos modos de falha \\textbf{FRÁGEIS} (sem redistribuição '
        'plástica): ruptura da madeira no grupo de cavilhas (embutimento/$n_{ef}$, '
        'corte de bloco Anexo~A, fendilhamento \\S8.1.4) e ancoragem frágil no '
        'concreto (chumbadores sem tirante). EC5 exige $\\eta\\leq 1{,}0$; o alvo '
        f'{eta_lig_alvo:.2f}'.replace('.', '{,}') +
        ' é margem de projeto (issue~22).\n\n'
        '\\textit{Exceções justificadas} (limite normativo $\\eta\\leq 1{,}0$, '
        'pois \\textbf{não} são ruptura frágil da madeira): compressão localizada '
        'no \\textbf{concreto} sob a chapa de base (L3/L3c -- esmagamento, EN~1992), '
        'compressão da \\textbf{madeira} na cumeeira (verificação de SEÇÃO, '
        '\\S6.1.4/\\S6.1.5/\\S6.4.3 -- sem ligação, peça monolítica) e '
        'componentes de \\textbf{aço} dúcteis (chapa, furo, solda -- EN~1993). '
        'Por isso L3/L3c aparecem com $\\eta=1{,}00$ (apoio no concreto) sem '
        'contrariar o alvo.\n\n'
        '$n_{ef}$ por fileira // fibras: EC5~\\S8.5.1.1\n'
        '($n_{ef}=n^{0,9}(a_1/(13d))^{1/4}\\leq n$).\n\n'
        '\\textit{Escopo das cavilhas (EC5~\\S8.6(2)):} '
        f'$6 \\leq d \\leq 30$~mm. Adota-se $d={_i(r_L1.get("d_mm", 24))}$~mm em '
        'L1/L1c (dentro do escopo; os 36~mm anteriores estavam fora). '
        'O código rejeita diâmetros fora dessa faixa (issue 18).\n\n'
        '\\vspace{4pt}\n'
        '{\\small\n'
        '\\begin{tabularx}{\\textwidth}{@{}'
        '>{\\raggedright\\arraybackslash}p{3.6cm}'
        '>{\\raggedright\\arraybackslash}X'
        'cc@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Ligação} & \\textbf{Norma} & '
        '$\\eta$ & \\textbf{Status} \\\\\n'
        '  \\midrule\n'
    )
    parts.append(eta_row('L1 -- Viga-pilar (base)', 'EC5 \\S8.2+\\S8.5.1.1+\\S8.6', _eta(r_L1), _ok(r_L1)))
    _l3_lab = (
        'L3 -- Sapata (com tirante, $H\\approx 0$)'
        if com_tirante or r_L3.get('com_tirante')
        else 'L3 -- Sapata (fundação)'
    )
    parts.append(eta_row(_l3_lab, 'EN 1993-1-8+EN 1992-4', _eta(r_L3), _ok(r_L3)))
    parts.append(eta_row('L1c -- Base pilar central', 'EC5 \\S8.2+\\S8.3+\\S8.6', _eta(r_L1c), _ok(r_L1c)))
    parts.append(eta_row('L3c -- Sapata central', 'EN 1993-1-8+EN 1992-4', _eta(r_L3c), _ok(r_L3c)))
    # Tabela de detalhes §11: largura = \textwidth (margens 2,5 cm)
    parts.append(
        '  \\bottomrule\n'
        '\\end{tabularx}}\n\n'
        '\\vspace{4pt}\n'
        '{\\small\\setlength{\\tabcolsep}{5pt}\n'
        '\\begin{tabularx}{\\textwidth}{@{}'
        '>{\\raggedright\\arraybackslash}p{2.3cm}'
        '>{\\raggedright\\arraybackslash}p{3.0cm}'
        '>{\\raggedright\\arraybackslash}p{3.4cm}'
        '>{\\raggedright\\arraybackslash}X'
        '@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Ligação} & \\textbf{Detalhe} & '
        '\\textbf{Parâmetro} & \\textbf{Valor} \\\\\n'
        '  \\midrule\n'
        '  L1 -- Viga-pilar & Pinos em chapa embutida &\n'
        '    $d$, $n$, layout &\n    '
    )
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
    parts.append(f'{_eta(r_L1):.4f}, {r_L1.get('eta_alvo', 0.75):.2f} \\\\\n')
    if com_tirante or r_L3.get('com_tirante'):
        parts.append(
            '  \\midrule\n  L3 -- Sapata & Com tirante ($H\\approx 0$) &\n'
            '    $H_{\\mathrm{arco}}$, $H_d$ &\n    '
        )
        parts.append(
            f'{r_L3.get("H_arco_kN", 0):.1f}~kN, '
            f'{r_L3.get("H_d_kN", 0):.1f}~kN \\\\\n'
        )
        parts.append('  & Chumbadores construtivos & $n$ & ')
        parts.append(f'{r_L3.get("n_chumbadores", 0)} \\\\\n')
        parts.append('  & Compressão $N$ & $\\sigma_c$, $\\eta_N$ & ')
        parts.append(
            f'{r_L3.get("sigma_c_MPa", 0):.3f}~MPa, '
            f'{r_L3.get("eta_N", r_L3.get("eta", 0)):.4f} \\\\\n'
        )
        parts.append('  & Chapa de base & Dimensões & ')
        parts.append(
            f'{r_L3.get("lado_chapa_cm", 0):.1f}$\\times$'
            f'{r_L3.get("lado_chapa_cm", 0):.1f}~cm \\\\\n'
        )
    else:
        parts.append('  \\midrule\n  L3 -- Sapata & Chumbadores & $n$, $F_{chu}$ & ')
        parts.append(f'{r_L3.get('n_chumbadores', 0)}, {r_L3.get('F_chu_kN', 0):.0f}~kN/chu \\\\\n')
        parts.append('  & & $n_{\\eta\\leq 1}$, $n_{\\times 4}$ & ')
        parts.append(f'{r_L3.get('n_chu_eta1', r_L3.get('n_chumbadores', 0))}, ')
        parts.append(f'{r_L3.get('n_chu_x4', r_L3.get('n_chumbadores', 0))} \\\\\n')
        parts.append('  & Chapa de base & Dimensões & ')
        parts.append(f'{r_L3.get('lado_chapa_cm', 0):.1f}$\\times${r_L3.get('lado_chapa_cm', 0):.1f}~cm \\\\\n')
        parts.append('  & & $H_d$, $\\eta$, $\\eta_{alvo}$ & ')
        parts.append(f'{r_L3.get('H_d_kN', 0):.1f}~kN, {_eta(r_L3):.4f}, ')
        parts.append(f'{r_L3.get('eta_alvo', 0.75):.2f} \\\\\n')
    parts.append('  \\midrule\n  L1c -- Central & 2 chapas independentes &\n    $d$, $n$/chapa, layout &\n    ')
    parts.append(f'{r_L1c.get('d_mm', 0):.0f}~mm, {r_L1c.get('n_pinos', 0)}, {r_L1c.get('n_linha', 0)}$\\times${r_L1c.get('n_linhas', 0)} \\\\\n')
    parts.append('  & & $\\eta$ & ')
    parts.append(f'{_eta(r_L1c):.4f} \\\\\n')
    parts.append(
        '  \\midrule\n'
        '  L3c -- Sapata central &\n'
        '    Compressão $N{=}2R_v$ (H$\\approx$0) &\n'
        '    $N_d$, $\\sigma_c$, $\\eta_N$ &\n    '
    )
    parts.append(
        f'{r_L3c.get("N_d_kN", 0):.1f}~kN, '
        f'{r_L3c.get("sigma_c_MPa", 0):.3f}~MPa, '
        f'{r_L3c.get("eta_N", r_L3c.get("eta", 0)):.4f} \\\\\n'
    )
    parts.append('  & Chumbadores (só construtivo) & $n$ & ')
    parts.append(f'{r_L3c.get("n_chumbadores", 0)} '
                 f'(H$\\approx$0 $\\Rightarrow$ $\\eta_H{{=}}0$) \\\\\n')
    parts.append(
        '  \\bottomrule\n'
        '\\end{tabularx}}\n\n'
    )

    # ── Memória da ligação L1 — Johansen (issue 29) ───────────────────────────
    if r_L1:
        _modo_lbl = {
            "modo_I_N": "I -- esmagamento da madeira",
            "modo_IIIb_N": "IIIb -- 1 rótula plástica no pino",
            "modo_IV_N": "IV -- 2 rótulas plásticas no pino",
        }
        _mg = _modo_lbl.get(str(r_L1.get("modo_gov", "")), str(r_L1.get("modo_gov", "")))
        parts.append(
            '\\vspace{6pt}\n'
            '\\subsection*{Memória da ligação L1 (Johansen -- EC5~\\S8.2/\\S8.5)}\n\n'
            'Cavilhas de aço em \\textbf{chapa embutida central}; dois planos de '
            'corte, madeira de espessura $t_1=b/2$ por lado; chapa de aço de '
            'espessura $t_2$ (grossa, $\\geq d$ -- ver Esquadro). Resistência lateral '
            'por Johansen (EC5~\\S8.2 Tab.~8.2), reduzida por $n_{ef}$ (\\S8.5.1.1).\n\n'
            '{\\small\\begin{tabular}{@{}lll@{}}\n  \\toprule\n'
            '  \\textbf{Parâmetro} & \\textbf{Símbolo} & \\textbf{Valor} \\\\\n'
            '  \\midrule\n'
            f'  Diâmetro do pino & $d$ & {_i(r_L1.get("d_mm", 0))}~mm \\\\\n'
            f'  Espessura da madeira & $t_1=b/2$ & '
            f'{_br(r_L1.get("t1_madeira_mm", 0), 0)}~mm \\\\\n'
            f'  Embutimento característico & $f_{{h,0,k}}$ & '
            f'{_br(r_L1.get("f_h0k_MPa", 0), 2)}~MPa \\\\\n'
            f'  Momento de plastificação & $M_{{y,Rk}}$ & '
            f'{_br(r_L1.get("M_y_Rk_Nmm", 0)/1000.0, 1)}~kN·mm \\\\\n'
            '  \\midrule\n'
            f'  Modo I (esmagamento) & $F_{{v,Rk}}^{{I}}$ & '
            f'{_br(r_L1.get("modo_I_kN", 0), 1)}~kN/plano \\\\\n'
            f'  Modo IIIb (1 rótula) & $F_{{v,Rk}}^{{IIIb}}$ & '
            f'{_br(r_L1.get("modo_IIIb_kN", 0), 1)}~kN/plano \\\\\n'
            f'  Modo IV (2 rótulas) & $F_{{v,Rk}}^{{IV}}$ & '
            f'{_br(r_L1.get("modo_IV_kN", 0), 1)}~kN/plano \\\\\n'
            f'  \\textbf{{Governante}} & $F_{{v,Rk}}$ & '
            f'\\textbf{{{_br(r_L1.get("F_v_Rk_plano_kN", 0), 1)}~kN/plano '
            f'({_tex_escape(_mg)})}} \\\\\n'
            f'  Cálculo (2 planos) & $F_{{v,Rd}}$ & '
            f'{_br(r_L1.get("F_v_Rd_kN", 0), 2)}~kN/pino '
            f'($k_{{mod}}={_br(r_L1.get("k_mod", 0.7), 2)}$, '
            f'$\\gamma_M={_br(r_L1.get("gamma_M", 1.3), 2)}$) \\\\\n'
            '  \\midrule\n'
            f'  Espaçamentos & $a_1$/$a_2$ & '
            f'{_i(r_L1.get("a1_mm", 0))}/{_i(r_L1.get("a2_mm", 0))}~mm \\\\\n'
            f'  Distâncias de borda & $a_{{3,t}}$/$a_{{4,t}}$ & '
            f'{_i(r_L1.get("a3t_mm", 0))}/{_i(r_L1.get("a4t_mm", 0))}~mm \\\\\n'
            f'  Nº efetivo por fileira & $n_{{ef,row}}$ & '
            f'{_br(r_L1.get("n_ef_row", 0), 2)} (de {_i(r_L1.get("n_linha", 0))}) \\\\\n'
            f'  Nº efetivo total & $n_{{ef}}$ & '
            f'{_br(r_L1.get("n_ef", 0), 1)} (de {_i(r_L1.get("n_pinos", 0))}) \\\\\n'
            f'  Módulo de deslizamento & $K_{{ser}}$ & '
            f'{_br(r_L1.get("K_ser_Nmm", 0), 0)}~N/mm (pino$\\cdot$plano) \\\\\n'
            f'  Resistência do grupo & $R$ & '
            f'{_br(r_L1.get("R_total_kN", 0), 0)}~kN $\\geq F_{{res}}='
            f'{_br(r_L1.get("F_res_kN", 0), 0)}$~kN \\\\\n'
            '  \\bottomrule\n\\end{tabular}}\n\n'
            f'$f_{{h,0,k}}=0{{,}}082(1-0{{,}}01\\,d)\\rho_k$ (\\S8.5.1.1 Eq.~8.32); '
            f'$M_{{y,Rk}}=0{{,}}3\\,f_{{u,k}}\\,d^{{2,6}}$ (Eq.~8.30, '
            f'$f_{{u,k}}={_i(400)}$~MPa); '
            f'$K_{{ser}}=\\rho_m^{{1,5}}d/23$ (\\S7.1 Tab.~7.1). '
            'Modos frágeis complementares: ruptura de bloco (\\S11.3) e '
            'fendilhamento (\\S8.1.4); componente metálico em EN~1993-1-8. '
            'Diâmetro dentro do escopo \\S8.6(2) (6--30~mm; issue~18).\n\n'
        )

    # ── Esquadro de chapas (issue 23) — dimensões e espessuras ────────────────
    if r_esq:
        parts.append(
            '\\vspace{6pt}\n'
            '\\subsection*{Esquadro de chapas -- dimensões e espessuras}\n\n'
            f'\\textit{{Aço {r_esq.get("aco", "S275")}}}. A \\textbf{{espessura não é '
            'arbitrada}: sai do dimensionamento. Nas chapas embutidas (L1/L1c) '
            'governa $t\\geq d$ (chapa central rígida, para o pino desenvolver a '
            'rótula plástica -- base dos modos de Johansen); nas chapas de base '
            '(L3/L3c), a flexão do balanço (EN~1993-1-8~\\S6.2.5).\n\n'
            '{\\small\\setlength{\\tabcolsep}{5pt}\n'
            '\\begin{tabularx}{\\textwidth}{@{}'
            'l l >{\\raggedright\\arraybackslash}p{2.6cm} '
            'c c >{\\raggedright\\arraybackslash}X@{}}\n'
            '  \\toprule\n'
            '  \\textbf{Chapa} & \\textbf{Tipo} & \\textbf{Larg.$\\times$Alt. (mm)} '
            '& $t_{req}$ & $t_{adot}$ & \\textbf{Furação / governa} \\\\\n'
            '  \\midrule\n'
        )
        for k in ("L1", "L1c", "L3", "L3c"):
            c = r_esq.get(k, {})
            if not c:
                continue
            parts.append(
                f'  {k} & {c.get("tipo", "")} & '
                f'{_i(c.get("largura_mm", 0))}$\\times${_i(c.get("altura_mm", 0))} & '
                f'{_br(c.get("t_req_mm", 0), 1)} & '
                f'\\textbf{{{_br(c.get("t_adotada_mm", 0), 1)}}} & '
                f'{_tex_escape(c.get("furacao", ""))} '
                f'({_tex_escape(c.get("t_governa", ""))}) \\\\\n'
            )
        parts.append('  \\bottomrule\n\\end{tabularx}}\n\n')

    parts.append(
        '\\vspace{6pt}\n'
        '\\subsection*{11.1 Fadiga e deslizamento '
        '(EC5 \\S7.1 + \\S8.1.5)}\n\n'
        '{\\small\\setlength{\\tabcolsep}{5pt}\n'
        '\\begin{tabularx}{\\textwidth}{@{}'
        'l'
        '>{\\raggedright\\arraybackslash}X'
        'cccc@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Lig.} & \\textbf{Descrição} & '
        '$u_{inst}$ & $u_{fin}$ &\n'
        '  $\\eta_{slip}$ & $\\eta_{alt}$ \\\\\n'
        '  \\midrule\n'
    )
    parts.append(
        f'  L1 & {_tex_escape(r_fL1.get("descricao", "Base lateral"))} & '
        f'{r_fL1.get("u_inst_mm", 0):.3f}~mm & {r_fL1.get("u_fin_mm", 0):.3f}~mm & '
        f'{_eta(r_fL1, "eta_slip"):.4f} & {_eta(r_fL1, "eta_alt"):.4f} \\\\\n'
        f'  L1c & {_tex_escape(r_fL1c.get("descricao", "Base central"))} & '
        f'{r_fL1c.get("u_inst_mm", 0):.3f}~mm & {r_fL1c.get("u_fin_mm", 0):.3f}~mm & '
        f'{_eta(r_fL1c, "eta_slip"):.4f} & {_eta(r_fL1c, "eta_alt"):.4f} \\\\\n'
    )
    parts.append(
        '  \\bottomrule\n'
        '\\end{tabularx}}\n\n'
    )
    # ── 11.2 Sucção — uplift e empuxo invertido (issue 33) ─────
    if r_succ:
        _su_ok = bool(r_succ.get("ok", False))
        parts.append(
            '% ── 11.2 Sucção — uplift e empuxo invertido ───────────\n'
            '\\subsection*{11.2 Combinação de Sucção -- Uplift e Empuxo '
            'Invertido (EN~1990 + EN~1992-4)}\n\n'
            'Com o peso próprio correto (\\S4), a combinação de sucção '
            f'(\\texttt{{{_tex_escape(r_succ.get("comb", "ELU_C3"))}}}, $0{{,}}9G+1{{,}}5W_{{suc}}$) '
            'apresenta \\textbf{esforços inversos}: reação vertical negativa '
            '\\footnote{O uplift é uma situação de \\textbf{equilíbrio} (EQU): '
            'adota-se $\\gamma_G=0{,}90$ para o permanente estabilizante conforme '
            '\\textbf{EN~1990 Tab.~A1.2(A)} -- valor \\emph{do EN~1990}, não da NBR '
            '(issue 4). Para resistência do membro (STR, Tab.~A1.2(B)) o favorável '
            'seria $1{,}00$, mas a sucção não governa a resistência.} '
            '(\\emph{uplift}) e empuxo horizontal invertido. Como o tirante é '
            'tração-apenas, sob sucção fica \\textbf{frouxo} e o empuxo invertido '
            '$|H|$ vai à \\textbf{fundação} (cortante na base de extremidade, sem '
            'atrito -- base tracionada).\n\n'
            '\\begin{tabular}{@{}lll@{}}\n  \\toprule\n'
            '  \\textbf{Grandeza} & \\textbf{Valor} & \\textbf{Obs.} \\\\\n  \\midrule\n'
            f'  $q_{{suc}}$ & {_br(r_succ.get("q_suc_kNpm", 0), 2)}~kN/m & líquido (0,9G+1,5W) \\\\\n'
            f'  $R_v$ (uplift/apoio) & {_br(r_succ.get("R_A_kN", 0), 1)}~kN & $<0$ = tração \\\\\n'
            f'  $H$ (invertido) & {_br(r_succ.get("H_suc_kN", 0), 1)}~kN & tirante frouxo \\\\\n'
            '  \\midrule\n'
            f'  Extremidade: $N_{{uplift}}$ & {_br(r_succ.get("N_uplift_ext_kN", 0), 1)}~kN & '
            f'$-\\gamma_{{G,inf}}W_{{pilar}}$ ($\\eta_N={_br(r_succ.get("eta_N_ext", 0), 3)}$) \\\\\n'
            f'  Extremidade: $V_{{base}}$ & {_br(r_succ.get("V_base_ext_kN", 0), 1)}~kN & '
            f'empuxo invertido ($\\eta_V={_br(r_succ.get("eta_V_ext", 0), 3)}$) \\\\\n'
            f'  Central: $N_{{uplift}}$ & {_br(r_succ.get("N_uplift_cen_kN", 0), 1)}~kN & '
            f'$\\eta={_br(r_succ.get("eta_cen", 0), 3)}$ ($V\\approx0$) \\\\\n'
            '  \\midrule\n'
            f'  Ancoragem & {_i(r_succ.get("n_chu", 4))}$\\times${_br(r_succ.get("F_chu_kN", 80), 0)}'
            f'~=~{_br(r_succ.get("R_anc_kN", 320), 0)}~kN & interação $N$--$V$ linear \\\\\n'
            f'  $\\eta$ governante ({_tex_escape(r_succ.get("base_gov", "extremidade"))}) & '
            f'\\textbf{{{_br(r_succ.get("eta", 0), 3)}}} & '
            + (r'\checkmark' if _su_ok else r'$\times$') + ' \\\\\n'
            '  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n'
            '\\textit{Nota:} interação $N$--$V$ linear (conservadora); o '
            'dimensionamento definitivo dos chumbadores (aço + cone de concreto + '
            'arrancamento + interação) segue EN~1992-4/EN~1993-1-8. O peso da '
            'fundação (favorável, EN~1997) não está incluído. A ancoragem sob '
            'sucção \\textbf{não} é meramente construtiva.\n\n'
        )
    # ── 11.3 Ruptura de bloco — EC5 Anexo A (issue 19) ─────────
    if r_bloco:
        _rbl = r_bloco
        parts.append(
            '% ── 11.3 Ruptura de bloco (EC5 Anexo A) ───────────────\n'
            '\\subsection*{11.3 Ruptura de Bloco -- Grupos de Cavilhas '
            '(EN~1995-1-1 Anexo~A)}\n\n'
            'Falha \\textbf{frágil} do bloco de madeira delimitado pelo grupo de '
            'cavilhas sob força paralela às fibras (Fig.~A.1):\n'
            '\\[\n  F_{bs,Rk}=\\max\\{\\,1{,}5\\,A_{net,t}\\,f_{t,0,k}\\ ;\\ '
            '0{,}7\\,A_{net,v}\\,f_{v,k}\\,\\}\\quad(A.1)\n\\]\n'
            'com $A_{net,t}=L_{net,t}\\,t_1$, $A_{net,v}=L_{net,v}\\,t_1$; '
            '$L_{net,t}=(n_\\perp-1)a_2$, $L_{net,v}=2[(n_\\parallel-1)a_1+a_{3,t}]$, '
            '$t_1=b$ (fenda da chapa a descontar -- issue 21).\n\n'
            '\\begin{tabular}{@{}lccc@{}}\n  \\toprule\n'
            '  \\textbf{Ligação} & \\textbf{L1} & \\textbf{L1c} & \\textbf{Ref.} \\\\\n'
            '  \\midrule\n'
            f'  Grupo ($n_\\parallel\\times n_\\perp$) & '
            f'{_i(_rbl.get("n_par",0))}$\\times${_i(_rbl.get("n_perp",0))} & '
            f'{_i(r_bloco_c.get("n_par",0))}$\\times${_i(r_bloco_c.get("n_perp",0))} & -- \\\\\n'
            f'  $1{{,}}5A_{{net,t}}f_{{t,0,k}}$ & {_br(_rbl.get("term_tracao_kN",0),0)}~kN & '
            f'{_br(r_bloco_c.get("term_tracao_kN",0),0)}~kN & tração \\\\\n'
            f'  $0{{,}}7A_{{net,v}}f_{{v,k}}$ & {_br(_rbl.get("term_cisalh_kN",0),0)}~kN & '
            f'{_br(r_bloco_c.get("term_cisalh_kN",0),0)}~kN & cisalh. \\\\\n'
            f'  $F_{{bs,Rd}}$ & {_br(_rbl.get("F_bs_Rd_kN",0),0)}~kN & '
            f'{_br(r_bloco_c.get("F_bs_Rd_kN",0),0)}~kN & (A.1) \\\\\n'
            f'  $F_{{//,Ed}}$ & {_br(_rbl.get("F_par_kN",0),0)}~kN & '
            f'{_br(r_bloco_c.get("F_par_kN",0),0)}~kN & $|N_d|$ \\\\\n'
            f'  $\\eta$ (Anexo~A) & \\textbf{{{_br(_rbl.get("eta",0),3)}}} & '
            f'\\textbf{{{_br(r_bloco_c.get("eta",0),3)}}} & $\\leq 1$ \\\\\n'
            f'  $\\eta$ só-cisalh. & {_br(_rbl.get("eta_so_cisalh",0),3)} & '
            f'{_br(r_bloco_c.get("eta_so_cisalh",0),3)} & (transparência) \\\\\n'
            '  \\bottomrule\n\\end{tabular}\n\n\\vspace{4pt}\n'
            '\\textit{Nota crítica:} a Eq.~(A.1) usa $\\max\\{\\}$ e é governada '
            'pelo mecanismo de \\textbf{tração} (bloco largo $\\Rightarrow$ '
            'grande $A_{net,t}$), resultando $\\eta<1$. Porém o mecanismo de '
            '\\textbf{cisalhamento isolado} da L1 dá $\\eta\\approx'
            f'{_br(_rbl.get("eta_so_cisalh",0),2)}$ -- a formulação $\\max\\{{\\}}$ do '
            'Anexo~A é reconhecidamente pouco conservadora para grupos grandes. '
            'Recomenda-se, no detalhamento, distribuir o grupo / usar múltiplas '
            'chapas (mais planos de corte) para trazer o mecanismo de cisalhamento '
            'para $\\eta\\leq1$ (ver issue 18).\n\n'
        )
    parts.append(
        '% ── 12. Resumo ────────────────────────────────────────────────\n'
        '\\section*{12. Resumo das Taxas de Utilização}\n\n'
        '{\\small\n'
        '\\begin{tabularx}{\\textwidth}{@{}'
        '>{\\raggedright\\arraybackslash}p{4.2cm}'
        '>{\\raggedright\\arraybackslash}X'
        'cc@{}}\n'
        '  \\toprule\n'
        '  \\textbf{Verificação} & \\textbf{Norma} & '
        '$\\eta$ & \\textbf{Status} \\\\\n'
        '  \\midrule\n'
    )
    # Resumo a partir do catálogo único (igual terminal/Excel)
    _tab_resumo = tabela_verificacoes(
        resultados,
        nao_aplicaveis=set(
            (resultados.get("meta") or {}).get("nao_aplicaveis", ())
        ),
    )
    for _row in _tab_resumo:
        _ok_r = bool(_row.get("ok_bool", False))
        _rot = str(_row["Verificação"]).replace("_", " ")
        if _row.get("status") not in (None, STATUS_OK):
            _rot = f"{_rot} [{_row['status']}]"
        parts.append(eta_row(
            _tex_escape(_rot),
            _tex_escape(str(_row["Norma"])),
            float(_row["η"]),
            _ok_r,
        ))
    # F-04: fonte única do carimbo — inclui as verificações sem resultado.
    _est_resumo = estatisticas_resumo(_tab_resumo)
    _eta_max_tab = _est_resumo["eta_max"]
    _all_ok_tab = _est_resumo["all_ok"] and not _est_resumo["pendentes"]
    parts.append('  \\midrule\n  \\multicolumn{2}{l}{\\textbf{$\\eta$ máximo}} &\n  \\multicolumn{2}{c}{\\textbf{')
    parts.append(f'{_eta_max_tab:.4f}')
    parts.append('}} \\\\\n')
    _status_global = (
        'APROVADO' if _all_ok_tab and _eta_max_tab <= 1.0 else 'REPROVADO'
    )
    parts.append(
        '  \\multicolumn{2}{l}{\\textbf{Status global}} &\n'
        '  \\multicolumn{2}{c}{\\textbf{'
        + _status_global
        + '}} \\\\\n'
    )
    parts.append(
        '  \\bottomrule\n'
        '\\end{tabularx}}\n\n'
    )

    # ── Anexo A — Análise (Castigliano) + diagramas M/V/N (issue 27) ──────────
    _fig_MVN = resultados.get("_fig_MVN")
    _alpha = _br(getattr(geo, "alpha_deg", 10.0), 2)
    parts.append(
        '\\clearpage\n'
        '% ── Anexo A — Análise ─────────────────────────────────────────\n'
        '\\section*{Anexo A -- Análise estrutural (Castigliano) e diagramas}\n\n'
        '\\textit{Anexo de reprodutibilidade (issue~27): definições, sistema de '
        'eixos, convenção de sinais e a integral de Castigliano com seus limites.}\n\n'
        '\\subsection*{A.1 Sistema de eixos e convenção de sinais (issue~12)}\n'
        '\\begin{itemize}\n'
        '  \\item $x$: coordenada \\textbf{horizontal}, $0\\to L$ (apoio~A à '
        'esquerda, apoio~B à direita); cumeeira em $x=L/2$.\n'
        '  \\item Eixo da peça inclinado do ângulo local '
        '$\\theta(x)=\\arctan(\\mathrm{d}y_c/\\mathrm{d}x)$; a inclinação do eixo '
        'centroidal é $\\pm\\tan\\alpha/2$ (muda de sinal no ápice).\n'
        '  \\item $N$: força normal \\textbf{ao longo do eixo} da peça, '
        '\\textbf{compressão positiva}; $V$: cortante \\textbf{perpendicular} ao '
        'eixo; $M$: positivo tracionando a fibra inferior (intradorso).\n'
        '\\end{itemize}\n\n'
        '\\subsection*{A.2 Geometria da seção variável}\n'
        '\\[\n  x_{sim}=\\min(x,\\,L-x),\\quad\n'
        '  h(x)=h_0+x_{sim}\\tan\\alpha,\\quad\n'
        '  y_c(x)=\\tfrac{1}{2}x_{sim}\\tan\\alpha,\\quad\n'
        '  I(x)=\\frac{b\\,h(x)^3}{12}\n\\]\n'
        f'com $b={_br(getattr(geo, "b", 0.32), 2)}$~m, '
        f'$h_0={_br(getattr(geo, "h0", 1.0), 2)}$~m, '
        f'$h_{{ap}}={_br(getattr(geo, "h_ap", 2.79), 3)}$~m e '
        f'$\\alpha={_alpha}^\\circ$.\n\n'
        '\\subsection*{A.3 Grau de hiperestaticidade e Castigliano}\n'
        'Estrutura primária: viga biapoiada (rótulas só nos apoios); grau~1, com '
        'a \\textbf{redundante} sendo o empuxo horizontal $H$. Pelo teorema de '
        'Castigliano (força unitária), $\\partial U/\\partial H=0$ com '
        '$M(x)=M_0(x)-H\\,y_c(x)$ dá, integrando de $0$ a $L$ (o módulo $E$ '
        'cancela-se; integração em projeção horizontal $\\mathrm{d}x$):\n'
        '\\[\n  H=\\frac{\\displaystyle\\int_0^{L} \\frac{M_0(x)\\,y_c(x)}{I(x)}'
        '\\,\\mathrm{d}x}{\\displaystyle\\int_0^{L} \\frac{y_c(x)^2}{I(x)}'
        '\\,\\mathrm{d}x}\n\\]\n'
        'onde $M_0(x)$ é o momento da viga simples sob a carga da combinação '
        'governante. Obtém-se então:\n'
        '\\[\n  M(x)=M_0(x)-H\\,y_c(x),\\quad\n'
        '  S(x)=\\frac{\\mathrm{d}M_0}{\\mathrm{d}x},\\quad\n'
        '  N(x)=H\\cos\\theta+S\\sin\\theta,\\quad\n'
        '  V(x)=S\\cos\\theta-H\\sin\\theta\n\\]\n'
        f'Combinação governante: $M_{{max}}={_br(meta.get("M_max_kNm", 0), 1)}$~kN·m, '
        f'$H={_br(meta.get("H_arco_kN", meta.get("H_ELU_kN", 0)), 1)}$~kN.\n\n'
        '\\textit{Hipótese (issue~24):} $H$ obtido com \\textbf{apoio horizontal '
        'indeslocável} (sem a flexibilidade axial do tirante) -- é o $H$ máximo, '
        'conservador para o tirante.\n\n'
    )
    if _fig_MVN:
        parts.append(
            '\\subsection*{A.4 Diagramas de esforços $M(x)$, $V(x)$, $N(x)$}\n\n'
            '\\begin{center}\n'
            f'\\includegraphics[width=0.92\\textwidth]{{{_fig_MVN}}}\n'
            '\\end{center}\n'
            '\\textit{Nota:} $V(x)$ e $N(x)$ são derivados do $M(x)$ real (não da '
            'aproximação de viga simples); o \\textbf{salto} em $V$ e $N$ no ápice '
            'decorre da mudança de sinal de $\\theta$ (quina do eixo centroidal).\n\n'
        )

    # ── Anexo B — Tabela completa das combinações + Cpe (issue 28) ────────────
    _tab_comb = []
    if load is not None and hasattr(load, "tabela_combinacoes"):
        try:
            _tab_comb = load.tabela_combinacoes()
        except Exception:
            _tab_comb = []
    if _tab_comb:
        _pad_lbl = {
            "asimetrico": "assim.", "assimetrico": "assim.",
            "assimetrico_reverso": "rev.", "uniforme_barlavento": "unif.bv",
            "uniforme_sotavento": "unif.st",
        }
        parts.append(
            '\\clearpage\n'
            '% ── Anexo B — Combinações completas ───────────────────────────\n'
            '\\section*{Anexo B -- Combinações completas por padrão de vento}\n\n'
            '\\textit{Reprodutibilidade (issue~28).} As '
            f'{len(_tab_comb)} combinações ELU (não só o envelope). Cada um dos 8 '
            'padrões Cpe da Tab.~25 (NBR~6123) -- casos C1/C2 $\\times$ '
            '\\{assim., rev., unif.bv, unif.st\\} -- gera ELU\\_W ($1{,}35G{+}1{,}5W$) '
            'e ELU\\_S ($0{,}9G{+}1{,}5W$); mais ELU\\_Q ($1{,}35G{+}1{,}5Q$, sem '
            'vento). A cat.~H reduziu de 24 para '
            f'{len(_tab_comb)} (Q e vento não concomitantes -- issue~3). '
            '$C_{esq}/C_{dir}$ = Cpe em cada meia-água (Cpb/Cps conforme o padrão).\n\n'
            '{\\scriptsize\\setlength{\\tabcolsep}{3.2pt}\n'
            '\\begin{tabular}{@{}llcrrrrrl@{}}\n'
            '  \\toprule\n'
            '  \\textbf{Padrão} & \\textbf{Comb.} & \\textbf{caso} & '
            '$C_{esq}$ & $C_{dir}$ & $q_{esq}$ & $q_{dir}$ & '
            '$M_{max}$ & \\textbf{Gov.} \\\\\n'
            '   & & & & & \\multicolumn{2}{c}{\\scriptsize kN/m} & '
            '\\scriptsize kN·m & \\\\\n'
            '  \\midrule\n'
        )
        _caso_atual = None
        for r in _tab_comb:
            if r["caso"] != _caso_atual and r["caso"] != "—":
                _caso_atual = r["caso"]
                parts.append(f'  \\multicolumn{{9}}{{@{{}}l}}{{\\textit{{Caso '
                             f'{_caso_atual} da Tab.~25}}}} \\\\\n')
            _pad = (f'{r["caso"]} {_pad_lbl.get(r["tipo_pad"], r["tipo_pad"])}'
                    if r["caso"] != "—" else "sem vento")
            _ce = "--" if r["C_esq"] is None else _br(r["C_esq"], 2)
            _cd = "--" if r["C_dir"] is None else _br(r["C_dir"], 2)
            _gov = r["governa"].replace("|", "$|$") if r["governa"] else ""
            _gov_tex = f'\\textbf{{{_gov}}}' if _gov else ''
            parts.append(
                f'  {_tex_escape(_pad)} & {r["grupo"]} & {r["caso"]} & '
                f'{_ce} & {_cd} & {_br(r["q_esq"], 2)} & {_br(r["q_dir"], 2)} & '
                f'{_br(r["M_max_kNm"], 1)} & {_gov_tex} \\\\\n'
            )
        parts.append(
            '  \\bottomrule\n\\end{tabular}}\n\n'
            '\\textit{Governantes:} $|M|$ (flexão/LTB), \\textit{uplift} '
            '(sucção/ancoragem) e $|H|$ (empuxo/fundação/tirante). '
            'Todas as combinações de vento têm duração \\textit{curta}; ELU\\_Q, '
            '\\textit{média}. O empuxo $H$ de cada linha é o da respectiva '
            'combinação (ver Anexo~A).\n\n'
        )

    parts.append(
        '\\vspace{1.6em}\n'
        '{\\small\n'
        'Documento gerado por pipeline automatizado em Python '
        '(EC5 + EN~1990 + NBR~6123).\\\\\n'
        'Valores sujeitos a conferência do engenheiro responsável '
        'antes da emissão.\n'
        '}\n\n'
        '\\end{document}\n'
    )

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
        geo, mat   : geometria e material de projeto
        load       : Carregamentos (combinações e esforços no memorial)
        nome       : nome base dos arquivos de saída
    """
    import pandas as pd

    OUTPUT_DIR.mkdir(exist_ok=True)

    # ── Excel (mesma tabela que o terminal / resumo) ──────────
    tab = tabela_verificacoes(
        resultados,
        nao_aplicaveis=set((resultados.get("meta") or {}).get("nao_aplicaveis", ())),
    )
    linhas_xlsx = [
        {
            "Verificação": r["Verificação"],
            "Norma":       r["Norma"],
            # F-04: η indeterminado sai como célula vazia + Estado explícito,
            # nunca como 0 (que se leria como aprovação folgada).
            "η":           None if math.isnan(float(r["η"])) else r["η"],
            "OK":          r["OK"],
            "Estado":      r.get("status", ""),
            "chave":       r["chave"],
        }
        for r in tab
    ]
    xlsx_path = OUTPUT_DIR / f"{nome}.xlsx"
    if linhas_xlsx:
        pd.DataFrame(linhas_xlsx).to_excel(xlsx_path, index=False)
    else:
        pd.DataFrame(
            columns=["Verificação", "Norma", "η", "OK", "Estado", "chave"]
        ).to_excel(
            xlsx_path, index=False
        )
    print(f"  Excel: {xlsx_path}")

    # ── Figura: diagramas M/V/N (anexo de análise — issue 27) ──
    try:
        from mlc_projeto.output.figuras import plot_diagramas_MVN
        _fig = plot_diagramas_MVN(load, geo, OUTPUT_DIR / f"{nome}_diagrama_MVN.pdf")
        if _fig is not None:
            resultados = {**resultados, "_fig_MVN": _fig.name}
            print(f"  Figura: {_fig}")
    except Exception as _e:                       # figura é opcional (não bloqueia)
        print(f"  Figura: diagramas M/V/N não gerados ({_e})")

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
