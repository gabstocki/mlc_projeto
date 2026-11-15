"""
output/validacao.py — Casos de referência independentes do programa (issue 121).

Cada caso compara um valor do programa com um valor ESPERADO obtido por caminho
independente: solução analítica fechada, fórmula normativa recalculada à mão
(escrita aqui de novo, sem chamar a função do programa), equilíbrio global ou
modelo numérico distinto (OpenSeesPy). Informa a fonte e a tolerância. O teste
`tests/test_issue121_referencias.py` exige que todos passem, e a tabela do
Apêndice A (`tese/tab_referencias.tex`) é gerada desta mesma lista.

Classes:
  · analítico     — solução fechada da resistência dos materiais;
  · normativo     — fórmula da norma recalculada à mão, com números fixos;
  · equilíbrio    — soma das reações × soma das cargas, em todas as combinações;
  · convergência  — discretização refinada não muda o resultado;
  · numérico      — modelo de elementos finitos independente (OpenSeesPy).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from mlc_projeto.output.formatacao import fmt_sig


@dataclass
class Caso:
    classe: str
    grandeza: str
    fonte: str
    esperado: float
    obtido: Callable[[], float]
    tol_rel: float

    def avaliar(self) -> dict:
        ob = float(self.obtido())
        err = abs(ob - self.esperado) / max(abs(self.esperado), 1e-12)
        return {"classe": self.classe, "grandeza": self.grandeza, "fonte": self.fonte,
                "esperado": self.esperado, "obtido": ob, "erro_rel": err,
                "tol_rel": self.tol_rel, "ok": err <= self.tol_rel}


# ── analíticos ───────────────────────────────────────────────────────────────
def _biapoiada(**kw) -> dict:
    from mlc_projeto.core.loads import analisar_biarticulada
    base = dict(L=20.0, h0=1.0, h_ap=1.0 + 1e-9, alpha_rad=1e-9, b=0.32,
                desenvolve_empuxo=False)
    base.update(kw)
    return analisar_biarticulada(**base)


def _k_c_manual(lam_rel: float, beta_c: float = 0.1) -> float:
    k = 0.5 * (1.0 + beta_c * (lam_rel - 0.3) + lam_rel ** 2)
    return 1.0 / (k + math.sqrt(k * k - lam_rel * lam_rel))


def _johansen_g_manual(rho_k: float, d: float, t1: float, f_u: float) -> float:
    """EC5 (8.32), (8.30) e (8.11g), ângulo 0°, em N."""
    f_h = 0.082 * (1.0 - 0.01 * d) * rho_k
    M_y = 0.3 * f_u * d ** 2.6
    g = f_h * t1 * d * (math.sqrt(2.0 + 4.0 * M_y / (f_h * d * t1 * t1)) - 1.0)
    return min(f_h * t1 * d, g, 2.3 * math.sqrt(M_y * f_h * d))


def casos() -> list[Caso]:
    from mlc_projeto.checks.elu.pilares import _kc_ec5
    from mlc_projeto.connections.ancoragem import resistencia_cone
    from mlc_projeto.connections.connections import johansen_chapa_central, n_ef
    q, L, a = 10.0, 20.0, 2.0
    lista = [
        Caso("analítico", "Viga biapoiada prismática: M no meio do vão (kN·m)",
             "$qL^2/8$", q * L * L / 8.0, lambda: _biapoiada(q=q)["M_max_kNm"], 1e-3),
        Caso("analítico", "Viga biapoiada prismática: reação (kN)",
             "$qL/2$", q * L / 2.0, lambda: _biapoiada(q=q)["R_A_kN"], 1e-6),
        Caso("analítico", "Viga com balanço: momento no apoio (kN·m)",
             "$-q\\,a^2/2$", -q * a * a / 2.0,
             lambda: _biapoiada(q=q, a_bal=a)["M_apoio_A_kNm"], 1e-6),
        Caso("analítico", "Viga com balanço: reação do apoio externo (kN)",
             "estática", q * L / 2.0 + q * a + q * a * a / (2.0 * L),
             lambda: _biapoiada(q=q, a_bal=a)["R_A_kN"], 1e-6),
        Caso("analítico", "Carga assimétrica nas águas: reação A (kN)",
             "estática, $q_e = 12$, $q_d = 6$", (12 * 10 * 15 + 6 * 10 * 5) / 20.0,
             lambda: _biapoiada(q=9.0, q_esq=12.0, q_dir=6.0)["R_A_kN"], 1e-3),
        Caso("normativo", "Fator $k_c$ para $\\lambda_{rel} = 1{,}2$, $\\beta_c = 0{,}1$",
             "EN 1995-1-1, (6.27) a (6.29)", _k_c_manual(1.2), lambda: _kc_ec5(1.2), 1e-9),
        Caso("normativo", "Número efetivo, 4 pinos, $a_1 = 100$, $d = 20$",
             "EN 1995-1-1, (8.34)", 4 ** 0.9 * (100 / 260) ** 0.25,
             lambda: n_ef(4, 100.0, 20.0), 1e-9),
        Caso("normativo", "Johansen, chapa central, $d = 24$, $t_1 = 148$ (kN)",
             "EN 1995-1-1, (8.11), (8.30) e (8.32)", _johansen_g_manual(385.0, 24.0, 148.0, 400.0) / 1e3,
             lambda: johansen_chapa_central(385.0, 24.0, 148.0, 400.0, theta_deg=0.0)["F_v_Rk_N"] / 1e3,
             1e-6),
        Caso("normativo", "Cone de arrancamento, $h_{ef} = 400$ mm, C25/30 (kN)",
             "EN 1992-4, (7.2)",
             8.9 * math.sqrt(25.0) * 400 ** 1.5 / 1e3,
             lambda: resistencia_cone(h_ef_mm=400.0, classe_concreto="C25/30", c_borda_mm=600.0,
                                      s_grupo_mm=400.0, n1=1, n2=1)["N0_Rk_c_kN"], 1e-3),
    ]
    return lista


def casos_pipeline(res: dict, load) -> list[Caso]:
    """Casos que dependem da execução: equilíbrio, convergência e o modelo FEM."""
    from mlc_projeto.core.loads import analisar_biarticulada
    geo = load.geo
    pior = [0.0]

    def _equilibrio() -> float:
        # sem as correções de peso próprio (fG = 0): carga total q_e(L/2 + a) + q_d·L/2
        err = 0.0
        for c in load.combinacoes_ELU_fisicas().values():
            r = load._analisar(q_esq=c.q_esq, q_dir=c.q_dir)
            carga = c.q_esq * (geo.L / 2 + geo.a_bal) + c.q_dir * geo.L / 2
            err = max(err, abs(r["R_A_kN"] + r["R_B_kN"] - carga))
        pior[0] = err
        return err

    gov = load.combinacao_ELU_governante()
    q = 0.5 * (gov.q_esq + gov.q_dir)
    kw = dict(L=geo.L, h0=geo.h0, h_ap=geo.h_ap, alpha_rad=geo.alpha_rad, b=geo.b,
              desenvolve_empuxo=load.empuxo_desenvolve)
    kw_bal = dict(kw, q_esq=gov.q_esq, q_dir=gov.q_dir, a_bal=geo.a_bal)
    M401 = analisar_biarticulada(q=q, **kw_bal)["M_max_kNm"]
    M_sim = analisar_biarticulada(q=q, **kw)["M_max_kNm"]      # mesmo caso do FEM

    def _fem() -> float:
        # meia viga com simetria, carga q uniforme, sem beiral (opensees_vtk)
        from mlc_projeto.opensees import opensees_vtk as ov
        return float(max(ov.analisar_viga(q, 0.0)["M_el"]))

    lista = [
        Caso("equilíbrio", "Maior desequilíbrio $|R_A + R_B - \\sum q|$, 29 combinações (kN)",
             "estática", 0.0, _equilibrio, 0.0),
        Caso("convergência", "Momento máximo, 401 contra 3.201 pontos de integração (kN·m)",
             "refino da discretização", analisar_biarticulada(q=q, n_pts=3201, **kw_bal)["M_max_kNm"],
             lambda: M401, 1e-4),
        Caso("numérico", "Momento no meio do vão, carga média da combinação governante, sem beiral (kN·m)",
             "OpenSeesPy, elementos de viga", M_sim, _fem, 0.01),
    ]
    # o equilíbrio tem esperado 0: avaliado por tolerância absoluta (0,01 kN)
    lista[0].tol_rel = 0.01
    return lista


def avaliar_todos(res: dict | None = None, load=None) -> list[dict]:
    cs = casos() + (casos_pipeline(res, load) if load is not None else [])
    out = []
    for c in cs:
        r = c.avaliar()
        if c.esperado == 0.0:                        # equilíbrio: erro absoluto
            r["erro_rel"] = abs(r["obtido"])
            r["ok"] = r["erro_rel"] <= c.tol_rel
        out.append(r)
    return out


def tabela_referencias(linhas: list[dict]) -> str:
    def v(x):
        s = fmt_sig(abs(x), 4) if abs(x) >= 1e-3 else "0"
        return f"$-${s}" if x < -1e-3 else s
    L = ["% tab_referencias.tex — GERADA por mlc_projeto/output/validacao.py (issue 121). NÃO EDITAR À MÃO.",
         r"\tabela{Casos de referência independentes}{\footnotesize",
         r"\begin{tabular}{p{2.2cm}p{3.1cm}p{2.2cm}rrr}", r"\toprule",
         r"    \textbf{Classe} & \textbf{Grandeza} & \textbf{Referência} & \textbf{Esperado} & \textbf{Programa} & \textbf{Erro} \\",
         r"\midrule"]
    for r in linhas:
        if r["esperado"] == 0.0:
            err = "$<$ 0,001 kN" if r["erro_rel"] < 1e-3 else f"{fmt_sig(r['erro_rel'], 2)} kN"
        elif r["erro_rel"] < 1e-6:
            err = "$<10^{-6}$"
        elif r["erro_rel"] < 1e-4:
            err = "$<$ 0,01~\\%"
        else:
            err = f"{100 * r['erro_rel']:.2f}~\\%".replace(".", ",")
        L.append(f"    {r['classe'].capitalize()} & {r['grandeza']} & {r['fonte']} & "
                 f"{v(r['esperado'])} & {v(r['obtido'])} & {err} \\\\")
    L += [r"\bottomrule", r"\end{tabular}}{Elaborado pelo autor (2026)}{referencias}{}{}", ""]
    return "\n".join(L)


def gerar_tab_referencias(tese: Path, res: dict, load) -> list[dict]:
    linhas = avaliar_todos(res, load)
    (Path(tese) / "tab_referencias.tex").write_text(tabela_referencias(linhas), encoding="utf-8")
    return linhas
