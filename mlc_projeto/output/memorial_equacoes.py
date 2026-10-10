"""
output/memorial_equacoes.py — Memória de cálculo por equações (issue 50).

Gera, a partir dos resultados do pipeline, o apêndice da monografia com as
verificações GOVERNANTES de cada elemento escritas como equações:

    expressão normativa  →  substituição dos valores  →  resultado

O arquivo é regenerado a cada execução do pipeline; os números saem dos mesmos
dicionários que produzem o memorial, de modo que texto e cálculo não divergem.
Não editar o .tex gerado à mão.
"""

from __future__ import annotations

import math
from pathlib import Path

from mlc_projeto.output.formatacao import fmt_eta, fmt_sig


def _n(x: float, d: int | None = None) -> str:
    """
    Grandeza em modo matemático com três algarismos significativos (issue 53);
    `d` é mantido por compatibilidade e ignorado.
    """
    return fmt_sig(float(x)).replace(",", "{,}")


def _e(eta: float) -> str:
    """Taxa de utilização: duas casas, arredondada para cima (issue 53)."""
    return fmt_eta(float(eta)).replace(",", "{,}")


def _eq(rotulo: str, linhas: list[str]) -> str:
    """
    Bloco de equações com um único número, na última linha. Usa `align` (e não
    `equation` + `aligned`) para que o bloco possa quebrar entre linhas no fim
    da página, sem deixar meia página em branco.
    """
    corpo = " \\nonumber \\\\\n    ".join(linhas)
    return (
        "\\begin{align}\n"
        f"    {corpo}\n"
        f"    \\label{{eq:mem-{rotulo}}}\n"
        "\\end{align}\n"
    )


def gerar_apendice_memoria(res: dict, out_path: Path) -> Path:
    """Escreve o apêndice LaTeX com as equações das verificações governantes."""
    P: list[str] = []
    a = P.append
    a("% =============================================================================\n"
      "% apendiceB.tex — MEMÓRIA DE CÁLCULO DAS VERIFICAÇÕES GOVERNANTES\n"
      "% GERADO AUTOMATICAMENTE por mlc_projeto/output/memorial_equacoes.py a cada\n"
      "% execução do pipeline (issue 50). NÃO EDITAR À MÃO.\n"
      "% =============================================================================\n\n"
      "\\chapter{MEMÓRIA DE CÁLCULO DAS VERIFICAÇÕES GOVERNANTES}"
      "\\label{ap:memoria-calculo}\n"
      "\\allowdisplaybreaks[1]\n\n"
      "Este apêndice apresenta, para cada elemento, as verificações que governam o "
      "seu dimensionamento, na forma de equações: a expressão normativa, a "
      "substituição dos valores e o resultado. Os valores são os da execução do "
      "programa que produziu o memorial, de onde este apêndice é gerado. Forças "
      "em kN, momentos em kN$\\cdot$m, tensões em MPa e comprimentos em metros, "
      "salvo indicação. As cláusulas são da EN 1995-1-1 \\cite{EN1995-1-1:2004}, "
      "salvo indicação.\n\n")

    # ── Viga ────────────────────────────────────────────────────────────
    ci, cu, mi, fx, els = (res.get(k, {}) for k in
                           ("cisalhamento", "cumeeira", "misula", "flexao", "ELS"))
    a("\\section{VIGA PRINCIPAL}\\label{sec:mem-viga}\n\n")
    if ci:
        a("\\subsection*{Cisalhamento no apoio (item 6.1.7)}\n\n"
          "A largura efetiva considera o coeficiente de fissuração $k_{cr}$; a "
          "força é o cortante no eixo da peça.\n\n")
        a(_eq("cisalhamento", [
            "\\tau_d &= \\frac{1{,}5\\,V_d}{k_{cr}\\,b\\,h}"
            f" = \\frac{{1{{,}}5 \\times {_n(ci['V_d_kN'])}}}{{{_n(ci['k_cr'])} \\times "
            f"{_n(ci['b_m'])} \\times {_n(ci['h_ef_m'])}}} \\times 10^{{-3}}"
            f" = {_n(ci['tau_d_MPa'], 3)}",
            f"f_{{v,d}} &= \\frac{{k_{{mod}}\\,f_{{v,k}}}}{{\\gamma_M}} = {_n(ci['f_vd_MPa'], 2)}",
            f"\\eta &= \\frac{{\\tau_d}}{{f_{{v,d}}}} = \\frac{{{_n(ci['tau_d_MPa'], 3)}}}"
            f"{{{_n(ci['f_vd_MPa'], 2)}}} = {_e(ci['eta'])}",
        ]))
    if cu:
        a("\\subsection*{Tração perpendicular às fibras na cumeeira (itens 6.4.3, "
          "fórmulas 6.54 e 6.55)}\n\n")
        a(_eq("cumeeira", [
            "\\sigma_{t,90,d} &= k_p\\,\\frac{6\\,M_{ap,d}}{b\\,h_{ap}^2}"
            f" = {_n(cu['k_p'], 4)} \\times \\frac{{6 \\times {_n(cu['M_cumeeira_kNm'])}}}"
            f"{{{_n(cu['b_m'])} \\times {_n(cu['h_ap_m'], 3)}^2}} \\times 10^{{-3}}"
            f" = {_n(cu['sigma_t90d_MPa'], 3)}",
            "k_{dis}\\,k_{vol}\\,f_{t,90,d} &="
            f" {_n(cu['k_dis'])} \\times {_n(cu['k_vol'], 3)} \\times {_n(cu['f_t90d_MPa'], 2)}"
            f" = {_n(cu['resist_t90_MPa'], 3)}",
            f"\\eta &= {_e(cu['eta_t90'])}",
        ]))
    if mi:
        a("\\subsection*{Tensão na borda inclinada (item 6.4.2)}\n\n"
          f"Governa a seção a {_n(mi['x_gov_m'])} m do apoio, sob sucção, com a borda "
          "inclinada tracionada.\n\n")
        a(_eq("borda-inclinada", [
            "\\sigma_{m,\\alpha,d} &= \\frac{6\\,|M_d|}{b\\,h^2}"
            f" = \\frac{{6 \\times {_n(abs(mi['M_gov_kNm']))}}}{{{_n(mi['b_m'])} \\times "
            f"{_n(mi['h_gov_m'], 3)}^2}} \\times 10^{{-3}} = {_n(mi['sigma_m_alpha_MPa'], 3)}",
            "k_{m,\\alpha} &= \\left[1 + \\left(\\frac{f_{m,d}}{0{,}75\\,f_{v,d}}"
            "\\operatorname{tg}\\alpha\\right)^2 + \\left(\\frac{f_{m,d}}{f_{t,90,d}}"
            f"\\operatorname{{tg}}^2\\alpha\\right)^2\\right]^{{-1/2}} = {_n(mi['k_m_alpha'], 3)}",
            f"\\eta &= \\frac{{\\sigma_{{m,\\alpha,d}}}}{{k_{{m,\\alpha}}\\,f_{{m,d}}}}"
            f" = \\frac{{{_n(mi['sigma_m_alpha_MPa'], 3)}}}{{{_n(mi['k_m_alpha'], 3)} \\times "
            f"{_n(mi['f_md_MPa'])}}} = {_e(mi['eta'])}",
        ]))
    if fx:
        a("\\subsection*{Flexo-compressão (item 6.3.2, fórmula 6.23)}\n\n")
        a(_eq("flexocompressao", [
            "\\eta &= \\frac{\\sigma_{c,0,d}}{k_{c,y}\\,f_{c,0,d}}"
            " + \\frac{\\sigma_{m,y,d}}{f_{m,d}}"
            f" = \\frac{{{_n(fx['sigma_c_MPa'], 4)}}}{{{_n(fx['k_c_y'], 3)} \\times "
            f"{_n(fx['f_c0d_MPa'])}}} + \\frac{{{_n(fx['sigma_m_MPa'], 3)}}}"
            f"{{{_n(fx['f_md_MPa'])}}} = {_e(fx['eta'])}",
        ]))
    if els:
        a("\\subsection*{Flecha final líquida (itens 2.3.2.2 e 7.2)}\n\n")
        a(_eq("flecha", [
            "w_{net,fin} &= w_G\\,(1 + k_{def}) + w_Q\\,(1 + \\psi_2\\,k_{def})"
            f" = {_n(els['w_G_mm'])} \\times (1 + {_n(els['k_def'], 1)}) + {_n(els['w_Q1_mm'])}"
            f" = {_n(els['w_net_fin_mm'])}~\\text{{mm}}",
            f"\\eta &= \\frac{{w_{{net,fin}}}}{{L/250}} = \\frac{{{_n(els['w_net_fin_mm'])}}}"
            f"{{{_n(els['lim_fin_mm'], 1)}}} = {_e(els['eta'])}",
        ]))

    # ── Pilares ─────────────────────────────────────────────────────────
    pc = res.get("pilar_central_contraventado", {})
    if pc:
        a("\\section{PILARES}\\label{sec:mem-pilares}\n\n"
          "\\subsection*{Pilar central montante (item 6.3.2, fórmula 6.23)}\n\n"
          "O pilar recebe as reações das duas vigas e o esforço descendente do "
          "painel de contraventamento.\n\n")
        i_m = pc["h_m"] / math.sqrt(12.0)
        a(_eq("pilar-central", [
            "N_{c,d} &= 2\\,R_v + V_{Ed}\\,\\operatorname{tg}\\beta"
            f" = {_n(pc['N_comp_kN'] - pc['download_total_kN'])} + "
            f"{_n(pc['download_total_kN'])} = {_n(pc['N_comp_kN'])}",
            "\\lambda &= \\frac{\\ell_{ef}}{i}"
            f" = \\frac{{{_n(pc['H_m'])}}}{{{_n(i_m, 4)}}} = {_n(pc['lambda'], 1)}"
            f",\\quad \\lambda_{{rel}} = {_n(pc['lambda_rel'], 3)}"
            f",\\quad k_c = {_n(pc['k_c'], 3)}",
            "\\eta &= \\frac{N_{c,d}/(b\\,h)}{k_c\\,f_{c,0,d}} + \\frac{\\sigma_{m,d}}{f_{m,d}}"
            f" = \\frac{{{_n(pc['sigma_c_MPa'], 3)}}}{{{_n(pc['k_c'], 3)} \\times "
            f"{_n(pc['f_c0d_MPa'])}}} + \\frac{{{_n(pc['sigma_m_comp_MPa'], 3)}}}"
            f"{{{_n(pc['f_md_MPa'])}}} = {_e(pc['eta'])}",
        ]))

    # ── Terças e cobertura ─────────────────────────────────────────────
    tb, ft = res.get("terca_flexocomp", {}), res.get("fixacao_telha", {})
    if tb or ft:
        a("\\section{TERÇAS E COBERTURA}\\label{sec:mem-tercas}\n\n")
    if tb:
        a("\\subsection*{Terça como biela do contraventamento (item 6.3.2, fórmula 6.24)}\n\n")
        a(_eq("terca", [
            "\\sigma_{c,0,d} &= \\frac{N_d}{b\\,h}"
            f" = \\frac{{{_n(tb['N_c_kN'])}}}{{{_n(tb['b_m'])} \\times {_n(tb['h_m'])}}}"
            f" \\times 10^{{-3}} = {_n(tb['sigma_c_MPa'], 3)}"
            f",\\quad \\lambda_z = {_n(tb['lambda_z'], 1)}"
            f",\\quad k_{{c,z}} = {_n(tb['k_c_z'], 3)}",
            "\\eta &= \\frac{\\sigma_{c,0,d}}{k_{c,z}\\,f_{c,0,d}}"
            " + k_m\\,\\frac{\\sigma_{m,y,d}}{f_{m,d}} + \\frac{\\sigma_{m,z,d}}{f_{m,d}}"
            f" = \\frac{{{_n(tb['sigma_c_MPa'], 3)}}}{{{_n(tb['k_c_z'], 3)} \\times "
            f"{_n(tb['f_c0d_MPa'])}}} + 0{{,}}7\\,\\frac{{{_n(tb['sigma_my_MPa'], 3)}}}"
            f"{{{_n(tb['f_md_MPa'])}}} + \\frac{{{_n(tb['sigma_mz_MPa'], 3)}}}"
            f"{{{_n(tb['f_md_MPa'])}}} = {_e(tb['eta'])}",
        ]))
    if ft:
        a("\\subsection*{Fixação da telha à terça (ABNT NBR 6123, item 7.2.6)}\n\n")
        a(_eq("telha", [
            "F_{d} &= \\left(\\gamma_Q\\,|c_p|\\,q - \\gamma_{G,fav}\\,g\\right) s\\,e",
            f"&= (1{{,}}5 \\times {_n(ft['cp_vedacao'], 1)} \\times {_n(ft['q_kNm2'], 3)}"
            f" - 0{{,}}9 \\times {_n(ft['g_telha_kNm2'])}) \\times {_n(ft['s_terca_m'])}"
            f" \\times {_n(ft['e_fix_m'])} = {_n(ft['F_fix_d_kN'], 3)}",
            f"\\eta &= \\frac{{F_d}}{{R_k/\\gamma_M}} = \\frac{{{_n(ft['F_fix_d_kN'], 3)}}}"
            f"{{{_n(ft['R_fix_k_kN'], 1)}/{_n(ft['gamma_M_fix'], 1)}}} = {_e(ft['eta'])}",
        ]))

    # ── Contraventamento ───────────────────────────────────────────────
    cv, cvv = res.get("contraventamento", {}), res.get("contraventamento_vertical", {})
    if cv or cvv:
        a("\\section{CONTRAVENTAMENTO}\\label{sec:mem-contraventamento}\n\n")
    if cv:
        a("\\subsection*{Diagonal do contraventamento da cobertura (item 9.2.5.3; "
          "EN 1993-1-1, item 6.2.3)}\n\n")
        a(_eq("cv-cobertura", [
            f"k_\\ell &= \\min\\left(1;\\ \\sqrt{{15/\\ell}}\\right) = \\sqrt{{15/{_n(cv['ell_m'])}}}"
            f" = {_n(cv['k_ell'], 3)}",
            "q_d &= \\frac{k_\\ell\\,n\\,N_d}{k_{f,3}\\,\\ell}"
            f" = \\frac{{{_n(cv['k_ell'], 3)} \\times {cv['n_por_sistema']} \\times "
            f"{_n(cv['N_d_kN'])}}}{{{_n(cv['k_f3'], 0)} \\times {_n(cv['ell_m'])}}}"
            f" = {_n(cv['q_d_kNpm'], 4)}~\\text{{kN/m}}",
            "V_{Ed} &= \\frac{q_d\\,\\ell}{2} + R_w"
            f" = {_n(cv['R_ext_estab_kN'])} + {_n(cv['R_vento0_kN'])} = {_n(cv['R_ext_proj_kN'])}",
            "N_{Ed} &= \\frac{V_{Ed}}{\\cos\\theta}"
            f" = \\frac{{{_n(cv['R_ext_proj_kN'])}}}{{\\cos {_n(cv['theta_deg'])}^\\circ}}"
            f" = {_n(cv['F_diag_kN'])}",
            "\\eta &= \\frac{N_{Ed}}{A\\,f_y/\\gamma_{M0}}"
            f" = \\frac{{{_n(cv['F_diag_kN'])}}}{{{_n(cv['A_mm2'], 1)} \\times 235 \\times 10^{{-3}}}}"
            f" = {_e(cv['eta_diag_N'])}",
        ]))
    if cvv:
        a("\\subsection*{Diagonal do contraventamento vertical (EN 1993-1-1, item 6.2.3)}\n\n")
        a(_eq("cv-vertical", [
            "V_{Ed} &= \\frac{f\\,(F_w + H_{imp})}{n}"
            f" = \\frac{{{_n(cvv['fracao_demanda'])} \\times ({_n(cvv['F_vento0_kN'], 1)} + "
            f"{_n(cvv['H_imp_kN'])})}}{{{cvv['n_paineis']}}} = {_n(cvv['V_painel_kN'])}",
            "N_{Ed} &= \\frac{V_{Ed}}{\\cos\\beta}"
            f" = \\frac{{{_n(cvv['V_painel_kN'])}}}{{\\cos {_n(cvv['beta_deg'], 1)}^\\circ}}"
            f" = {_n(cvv['N_diag_kN'])}",
            "N_{t,Rd} &= \\min\\left(\\frac{A\\,f_y}{\\gamma_{M0}};\\ "
            "\\frac{0{,}9\\,A_s\\,f_u}{\\gamma_{M2}}\\right)"
            f" = \\min({_n(cvv['N_pl_Rd_kN'], 1)};\\ {_n(cvv['N_u_Rd_kN'], 1)})"
            f" = {_n(cvv['N_t_Rd_kN'], 1)}",
            f"\\eta &= \\frac{{{_n(cvv['N_diag_kN'])}}}{{{_n(cvv['N_t_Rd_kN'], 1)}}}"
            f" = {_e(cvv['eta_diag_N'])}",
        ]))

    # ── Ligações ───────────────────────────────────────────────────────
    L1, an = res.get("L1", {}), res.get("ancoragem_canto", {})
    if L1 or an:
        a("\\section{LIGAÇÕES E ANCORAGEM}\\label{sec:mem-ligacoes}\n\n")
    if L1:
        a("\\subsection*{Pinos da ligação L1 (itens 8.2.3 e 8.5.1.1)}\n\n"
          "Chapa de aço central, corte duplo; o modo governante de Johansen é o de "
          "uma rótula plástica no pino.\n\n")
        a(_eq("l1", [
            "F_{v,Rk} &= f_{h,\\alpha,k}\\,t_1\\,d\\left[\\sqrt{2 + \\frac{4\\,M_{y,Rk}}"
            "{f_{h,\\alpha,k}\\,d\\,t_1^2}} - 1\\right]",
            f"&= {_n(L1['f_h0k_MPa'])} \\times {_n(L1['t1_madeira_mm'], 0)} \\times "
            f"{L1['d_mm']}\\left[\\sqrt{{2 + \\frac{{4 \\times {_n(L1['M_y_Rk_Nmm'], 0)}}}"
            f"{{{_n(L1['f_h0k_MPa'])} \\times {L1['d_mm']} \\times "
            f"{_n(L1['t1_madeira_mm'], 0)}^2}}}} - 1\\right] \\times 10^{{-3}}"
            f" = {_n(L1['F_v_Rk_plano_kN'])}",
            "R_d &= n_{ef}\\,\\frac{2\\,k_{mod}\\,F_{v,Rk}}{\\gamma_M}"
            f" = {_n(L1['n_ef'], 1)} \\times \\frac{{2 \\times {_n(L1['k_mod'])} \\times "
            f"{_n(L1['F_v_Rk_plano_kN'])}}}{{{_n(L1['gamma_M'])}}} = {_n(L1['R_total_kN'], 1)}",
            "\\eta &= \\frac{\\sqrt{N_d^2 + V_d^2}}{R_d}"
            f" = \\frac{{\\sqrt{{{_n(L1['N_d_kN'])}^2 + {_n(L1['V_d_kN'])}^2}}}}"
            f"{{{_n(L1['R_total_kN'], 1)}}} = {_e(L1['eta'])} \\leq 0{{,}}75",
        ]))
    if an:
        a("\\subsection*{Ancoragem da base de canto, cone de arrancamento "
          "(EN 1992-4, fórmulas 7.1 a 7.7)}\n\n")
        a(_eq("ancoragem", [
            "N^0_{Rk,c} &= k_1\\,\\sqrt{f_{ck}}\\,h_{ef}^{1{,}5}"
            f" = {_n(an['cone_k'], 1)} \\times \\sqrt{{{_n(an['cone_f_ck_MPa'], 0)}}} \\times "
            "400^{1{,}5} \\times 10^{-3}"
            f" = {_n(an['cone_N0_Rk_c_kN'], 1)}",
            "N_{Rd,c} &= \\frac{N^0_{Rk,c}}{\\gamma_{Mc}}\\,\\frac{A_{c,N}}{A^0_{c,N}}"
            "\\,\\psi_{s,N}\\,\\psi_{re,N}\\,\\psi_{ec,N}"
            f" = \\frac{{{_n(an['cone_N0_Rk_c_kN'], 1)}}}{{{_n(an['gamma_Mc'], 1)}}} \\times "
            f"\\frac{{{_n(an['cone_A_c_N_mm2'] / 1e6, 2)}}}{{{_n(an['cone_A0_c_N_mm2'] / 1e6, 2)}}}"
            f" \\times 1 = {_n(an['N_Rd_cone_kN'], 1)}",
            f"\\eta &= \\frac{{N_{{Ed}}}}{{N_{{Rd,c}}}} = \\frac{{{_n(an['N_Ed_kN'], 1)}}}"
            f"{{{_n(an['N_Rd_cone_kN'], 1)}}} = {_e(an['eta_concreto'])}",
        ]))

    out_path = Path(out_path)
    # restaura o padrão (equações indivisíveis) para o restante do documento
    P.append("\n\\allowdisplaybreaks[0]\n")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(P), encoding="utf-8")
    return out_path
