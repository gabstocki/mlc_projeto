"""
output/quadro_espacamentos.py — Requerido × adotado dos espaçamentos (issue 43).

Reúne, para cada ligação, os espaçamentos e as distâncias exigidos pelas
normas e os adotados no detalhe (os mesmos dos desenhos da issue 52):

  · madeira  — EN 1995-1-1 Tab. 8.5 (cavilhas) e Tab. 8.6 (parafusos axiais);
  · chapas   — EN 1993-1-8 Tab. 3.3 (furos; ovalizados: e3, e4) e Tab. 3.9 (olhais);
  · concreto — EN 1992-4 (s_min, cone pleno, fendilhamento).

Gera o quadro como tabelas LaTeX para a tese (tese/tab_espacamentos.tex),
regenerado a cada execução do pipeline. Nenhum valor é digitado à mão: o
requerido vem da norma aplicada pelo próprio programa e o adotado, do detalhe.
"""

from __future__ import annotations

from pathlib import Path

from mlc_projeto.connections.connections import distancias_minimas
from mlc_projeto.output.desenhos import detalhe_topo_pf

T85 = "EC5 Tab. 8.5"
T86 = "EC5 Tab. 8.6"
T33 = "EN 1993-1-8 Tab. 3.3"


def _l(lig, peca, grandeza, req, adot, norma):
    return {"ligacao": lig, "peca": peca, "grandeza": grandeza, "req": float(req),
            "adot": float(adot), "norma": norma, "ok": float(adot) >= float(req) - 1e-6}


def _cavilhas_axiais(lig: str, peca: str, r: dict, h_mm: float) -> list[dict]:
    """Grupo de cavilhas com força // às fibras (escoras, pé do pilar, montante)."""
    d = float(r["d_mm"])
    req = distancias_minimas(d, 0.0)
    nv = int(r["n_vert"])
    a4 = (h_mm - (nv - 1) * float(r["a2_mm"])) / 2.0
    out = []
    if int(r["n_horiz"]) > 1:
        out.append(_l(lig, peca, "$a_1$", req["a1_mm"], r["a1_mm"], T85))
    if nv > 1:
        out.append(_l(lig, peca, "$a_2$", req["a2_mm"], r["a2_mm"], T85))
    out += [_l(lig, peca, "$a_{3,t}$", req["a3t_mm"], r["a3t_mm"], T85),
            _l(lig, peca, "$a_{4,c}$", req["a4c_mm"], a4, T85)]
    return out


def montar_quadro(res: dict, *, h0_m: float, L_T: float, L: float,
                  folga_oblongo_mm: float, d_chu_mm: float, h_ef_mm: float,
                  c_borda_mm: float, s_grupo_mm: float, h_bloco_mm: float,
                  h_pilar_mm: dict, h_terca_mm: float) -> list[dict]:
    """Linhas do quadro (madeira, chapas e concreto) a partir dos resultados."""
    q: list[dict] = []
    # ── L1 / L1c — pinos Ø24 na viga, força a θ ≈ 84° das fibras ─────────
    for k in ("L1", "L1c"):
        r, esq = res[k], res["esquadro_chapas"][k]
        d, n = float(r["d_mm"]), int(r["n_pinos"])
        req = distancias_minimas(d, float(r["theta_deg"]))
        h0 = h0_m * 1000
        y_top = h0 - 3.0 * d
        y_bot = y_top - (n - 1) * float(r["a2_mm"])
        q += [_l(k, "viga", "$a_2$", req["a2_mm"], r["a2_mm"], T85),
              _l(k, "viga", "$a_{3,t}$", req["a3t_mm"], r["a3t_mm"], T85),
              _l(k, "viga", "$a_{4,c}$ (borda superior)", req["a4c_mm"], h0 - y_top, T85),
              _l(k, "viga", "$a_{4,t}$ (borda inferior)", req["a4t_mm"], y_bot, T85)]
        d0 = d                                              # cavilha ajustada
        Lp, Hp = float(esq["largura_mm"]), float(esq["altura_mm"])
        a3 = float(r["a3t_mm"])
        q += [_l(k, "chapa", "$p_1$ (entre furos)", 2.2 * d0, r["a2_mm"], T33),
              _l(k, "chapa", "$e_3$ (eixo do furo ovalizado)", 1.5 * d0, min(a3, Lp - a3), T33),
              _l(k, "chapa", "$e_4$ (extremidade do furo)", 1.5 * d0,
                 Hp - (y_top + folga_oblongo_mm), T33)]
    # ── L1f — topo do pilar de frontão (força // às fibras da viga) ──────
    tp = res["pilar_frontao"]["topo"]
    det = detalhe_topo_pf(tp, float(res["ELS"]["w_fin_mm"]), L_T, L)
    d = det["d_mm"]
    req = distancias_minimas(d, 0.0)
    y_top = det["a4c_mm"] + (det["n_vert"] - 1) * det["a2_mm"]
    Hc = y_top + 1.5 * d + det["curso_mm"]
    q += [_l("L1f", "viga", "$a_2$", req["a2_mm"], det["a2_mm"], T85),
          _l("L1f", "viga", "$a_{4,c}$ (intradorso)", req["a4c_mm"], det["a4c_mm"], T85),
          _l("L1f", "chapa", "$p_1$ (aço entre furos ovalizados)",
             2.0 * det["curso_mm"] + 2.2 * d, det["a2_mm"], T33),
          _l("L1f", "chapa", "$e_3$ (eixo do furo ovalizado)", 1.5 * d,
             h_pilar_mm["PF"] / 2.0, T33),
          _l("L1f", "chapa", "$e_4$ (extremidade do furo)", 1.5 * d,
             Hc - (y_top + det["curso_mm"]), T33)]
    # ── Escoras do nó de topo e terça–viga ────────────────────────────────
    nc = res["no_contraventamento"]
    for k, rot in (("beiral", "escora de beiral"), ("central", "escora central")):
        q += _cavilhas_axiais(f"Nó de topo, {rot}", "terça", nc[f"ligacao_escora_{k}"],
                              h_terca_mm)
    tv = res["ligacao_terca_viga"]
    c, e = tv["corrente"], tv["corrente"]["espacamentos_req"]
    q += [_l("Terça–viga, corrente", "terça", "passo vertical ($a_2$ terça, $a_1$ viga)",
             max(e["a1_mm"], e["a2_mm"]), c["passo_vertical_mm"], T86),
          _l("Terça–viga, corrente", "terça", "$a_{1,CG}$ (extremidade da terça)",
             e["a1_CG_mm"], c["a1_CG_adotado_mm"], T86),
          _l("Terça–viga, corrente", "terça", "$a_{2,CG}$ (faces da terça)",
             e["a2_CG_mm"], c["a2_CG_terca_adotado_mm"], T86),
          _l("Terça–viga, corrente", "viga", "$a_{2,CG}$ (face lateral da viga)",
             e["a2_CG_mm"], c["a2_CG_viga_adotado_mm"], T86)]
    q += _cavilhas_axiais("Terça–viga, montante", "terça", tv["montante"], h_terca_mm)
    # ── Bases: pé do pilar, chapa e concreto ──────────────────────────────
    d0c = d_chu_mm + 2.0
    for k, rot, hp in (("base_L3", "L3", "lateral"), ("base_L3c", "L3c", "central"),
                       ("base_L3f", "L3f", "PF"), ("base_L3a_canto", "L3a canto", "canto"),
                       ("base_L3a_central", "L3a central", "central")):
        b = res[k]
        pe = b["pe_pilar"]
        q += _cavilhas_axiais(f"{rot}, pé do pilar", "pilar", pe, h_pilar_mm[hp])
        nv = int(pe["n_vert"])
        larg_alma = h_pilar_mm[hp] - 60.0
        q += [_l(f"{rot}, pé do pilar", "chapa vertical", "$e_2$",
                 1.2 * float(pe["d_mm"]),
                 (larg_alma - (nv - 1) * float(pe["a2_mm"])) / 2.0, T33),
              _l(rot, "chapa de base", "$e_1 = e_2$", 1.2 * d0c, b["geometria"]["e_mm"], T33),
              _l(rot, "chapa de base", "$p_1 = p_2$", 2.4 * d0c, b["geometria"]["s_mm"], T33),
              _l(rot, "chapa de base", "folga arruela–pilar", 0.0,
                 b["geometria"]["folga_arruela_pilar_mm"], "geometria")]
    q += [_l("Bases", "concreto", "$s$ entre chumbadores", 4.0 * d_chu_mm, s_grupo_mm,
             "EN 1992-4 7.2.2.5(4)"),
          _l("Bases", "concreto", "$c$ à borda (cone pleno)", 1.5 * h_ef_mm, c_borda_mm,
             "EN 1992-4 7.2.1.4"),
          _l("Bases", "concreto", "$h$ do bloco (fendilhamento)", 2.0 * h_ef_mm, h_bloco_mm,
             "EN 1992-4 7.2.1.7")]
    # ── Olhais das diagonais (EN 1993-1-8 Tab. 3.9) ───────────────────────
    for k, rot in (("lig_diag_vertical", "olhal CV-V"), ("lig_diag_transversal", "olhal CV-T")):
        o = res[k]
        q += [_l(rot, "chapa do olhal", "$a$ (borda na direção da força)", o["a_req_mm"],
                 o["a_borda_mm"], "EN 1993-1-8 Tab. 3.9"),
              _l(rot, "chapa do olhal", "$c$ (borda lateral)", o["c_req_mm"],
                 o["c_borda_mm"], "EN 1993-1-8 Tab. 3.9")]
    return q


def _n(x: float) -> str:
    return f"{x:.0f}" if abs(x - round(x)) < 0.05 else f"{x:.1f}".replace(".", ",")


def gerar_tex(linhas: list[dict], caminho: Path) -> Path:
    """Escreve o quadro em tabelas LaTeX: madeira, chapas metálicas e concreto."""
    grupos = (
        ("Espaçamentos na madeira, ligações de topo e da cobertura",
         lambda r: r["peca"] in ("viga", "terça"), "esp-madeira-topo"),
        ("Espaçamentos na madeira, pé dos pilares",
         lambda r: r["peca"] == "pilar", "esp-madeira-pe"),
        ("Espaçamentos e distâncias nas chapas metálicas e no concreto",
         lambda r: r["peca"] not in ("viga", "terça", "pilar"), "esp-chapas-concreto"),
    )
    P = ["% =============================================================================\n"
         "% tab_espacamentos.tex — REQUERIDO × ADOTADO (issue 43)\n"
         "% GERADO AUTOMATICAMENTE por mlc_projeto/output/quadro_espacamentos.py.\n"
         "% NÃO EDITAR À MÃO. Valores em mm.\n"
         "% =============================================================================\n\n"]
    for tit, filtro, lab in grupos:
        rows = [r for r in linhas if filtro(r)]
        P.append(f"\\tabela{{{tit}}}{{\\scriptsize\\setlength{{\\tabcolsep}}{{3pt}}\n"
                 "\\begin{tabular}{@{}lllrrl@{}}\n\\toprule\n"
                 "    \\textbf{Ligação} & \\textbf{Peça} & \\textbf{Grandeza} & "
                 "\\textbf{Req.} & \\textbf{Adot.} & \\textbf{Critério} \\\\\n\\midrule\n")
        ant = None
        for r in rows:
            lig = r["ligacao"] if r["ligacao"] != ant else ""
            ant = r["ligacao"]
            sit = "" if r["ok"] else " \\textbf{(!)}"
            P.append(f"    {lig} & {r['peca']} & {r['grandeza']} & {_n(r['req'])} & "
                     f"{_n(r['adot'])}{sit} & {r['norma']} \\\\\n")
        P.append("\\bottomrule\n\\end{tabular}}{Elaborado pelo autor (2026)}"
                 f"{{{lab}}}{{}}{{}}\n\n")
    caminho = Path(caminho)
    caminho.write_text("".join(P), encoding="utf-8")
    return caminho
