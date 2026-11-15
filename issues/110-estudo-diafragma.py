"""Issue 110 — estudo: alma do diafragma transversal nas baías intermediárias.

O diafragma é uma viga horizontal de 46 m entre os frontões; a força transversal H_tr
entra nos topos dos pilares de cada pórtico e sai pelos frontões (CV-T). Hoje só as
baías 1–2 e 8–9 têm cruzes (CV-H). Opções para a alma nas baías 2–8:
  A — a telha trapezoidal como diafragma (stressed skin, EN 1993-1-3 §10.3);
  B — cruzes leves em todos os painéis das baías intermediárias, nos dois vãos
      (profundidade do diafragma = largura, 40,5 m);
  B1 — cruzes só no vão A–B (profundidade 20,25 m, cordas T1 e T9).
Uso: .venv/bin/python issues/110-estudo-diafragma.py
"""
import contextlib
import io
import math

import mlc_projeto.main as M
from mlc_projeto.checks.elu.contraventamento_vertical import D_COMERCIAL_MM, _n_t_rd_kN

M.gerar_relatorio = lambda *a, **k: None
with contextlib.redirect_stdout(io.StringIO()):
    r = M._main_impl(rodar_varredura=False, abrir_viz=False)
cvt = r["contraventamento_transversal"]
H, Lc, B = cvt["H_tr_kN"], 46.0, 2 * 20.25
L_T, s = M.L_T, M.S
w = H / Lc
baias = [(i * L_T, (i + 1) * L_T) for i in range(8)]          # 8 baías entre eixos 1..9
print(f"H_tr = {H:.1f} kN (cálculo) | w = {w:.2f} kN/m | R frontão = {H/2:.1f} kN")
print(f"M_diaf = {H*Lc/8:.0f} kN·m | corda = {H*Lc/8/B:.1f} kN (B = {B} m)")
ang = math.atan(s / L_T); L_d = math.hypot(s, L_T)
massa_m = lambda d: 7850e-6 * math.pi * d ** 2 / 4
for nome, prof, n_vaos in (("B (dois vãos)", B, 2), ("B1 (só vão A–B)", B / 2, 1)):
    print(f"\n{nome}: profundidade {prof:.2f} m")
    tot_barras, tot_kg = 0, 0.0
    for i, (x0, x1) in enumerate(baias):
        V = max(abs(H / 2 - w * x0), abs(H / 2 - w * x1))       # cortante máximo na baía
        q = V / prof                                            # fluxo de cisalhamento kN/m
        F = q * L_T / math.cos(ang)                             # diagonal tracionada do painel
        d = next(dd for dd in D_COMERCIAL_MM if F <= 0.90 * _n_t_rd_kN(dd, "S235"))
        cv_h = i in (0, 7)
        n_bar = 0 if cv_h else 2 * 8 * n_vaos
        tot_barras += n_bar; tot_kg += n_bar * L_d * massa_m(d)
        print(f"  baía {i+1}–{i+2}: V={V:5.1f} kN  q={q:4.2f} kN/m  F_diag={F:5.1f} kN  "
              f"→ Ø{d}{'  (já tem CV-H)' if cv_h else f', {n_bar} barras'}")
    print(f"  barras novas: {tot_barras} | aço ≈ {tot_kg:.0f} kg | corda: {H*Lc/8/prof:.1f} kN")
print(f"\nA (telha): q_max = {H/2/B:.2f} kN/m ao longo de cada frontão; por fixador da telha "
      f"a 0,20 m: {H/2/B*0.20:.2f} kN de corte, somado à sucção. Exige produto definido, "
      f"conectores de cisalhamento nas bordas (sobre as vigas) e regras de manutenção.")
