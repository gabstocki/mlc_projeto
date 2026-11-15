"""Issue 108 — estudo: tirante por lâmina no pilar bipartido (sela e pé).

Rotas comparadas, por pilar (canto/lateral montante e central montante):
  A — tirante por lâmina: furo central na lâmina, luva na borda inferior da aba da sela,
      porca dentro do pilarete Ø114,3. Tira a tração do pé; a sela continua levando a
      gravidade por cavilhas (governa a sela).
  B — A + sela por contato: a sela apoia num dente (entalhe) na face interna de cada
      lâmina, compressão paralela às fibras. As cavilhas da sela só posicionam.
  C — tirante único entre as lâminas: barra no vão livre (a = 340 mm), da sela à chapa de
      base, atravessando os espaçadores; lâminas sem furo e sem tração.
Execução:  .venv/bin/python issues/108-estudo-tirante-lamina.py
"""
import math
import mlc_projeto.main as M
from mlc_projeto.connections.tirante_interno import dimensionar_tirante
from mlc_projeto.core.materials import GlulamMaterial

M.gerar_relatorio = lambda *a, **k: None
r = M._main_impl(rodar_varredura=False, abrir_viz=False)
mat = GlulamMaterial("GL24h", 3, "media")
f_c0d = mat.f_c0_d / 1e6
F90 = r["base_L3a_canto"]["F_v_Rd_90_pino_kN"]          # cavilha do pé, ⊥ fibras (kN)
V_pe = r["base_L3a_canto"]["pilarete"]["V_kN"]           # choque por lâmina (espaçador)

print("\n" + "=" * 78 + "\nISSUE 108 — tirante por lâmina\n" + "=" * 78)
tot = {"atual": 0, "A": 0, "B": 0, "C": 0}
for chave, base, npil in (("pilar_contraventado", "base_L3a_canto", 8),
                          ("pilar_central_contraventado", "base_L3a_central", 6)):
    p, b = r[chave], r[base]
    sela_n, pe_n = p["sela"]["n_pinos"], b["pe_pilar"]["n_pinos"]
    Nt_lam, R_up, R_g = p["N_t_lamina_kN"], p["R_up_kN"], p["R_grav_kN"]
    # pé só ao cortante do choque (metade, pelo espaçador): η ≤ 0,75, mínimo 2×2 (contorna o furo)
    pe_v = max(4, 2 * math.ceil(math.ceil(V_pe / (0.75 * F90)) / 2))
    tir_l = dimensionar_tirante(rotulo="lâmina", N_t_kN=Nt_lam)
    tir_c = dimensionar_tirante(rotulo="central", N_t_kN=R_up)
    # dente de apoio da sela: compressão ∥ fibras sobre (prof × 320 mm); η ≤ 0,75
    F_dente = R_g / 2.0
    prof = next(t for t in range(20, 81, 5) if F_dente * 1e3 / (t * 320) / f_c0d <= 0.75)
    sig_net = p["N_lamina_kN"] * 1e3 / ((160 - prof) * 320) / f_c0d
    atual = 2 * (sela_n + pe_n)
    A = 2 * (sela_n + pe_v)
    B = 2 * (2 + pe_v)
    C = 2 * (sela_n + pe_v)
    for k, v in (("atual", atual), ("A", A), ("B", B), ("C", C)):
        tot[k] += v * npil
    print(f"\n{p['rotulo']} ({npil} pilares): R_grav {R_g:.0f} kN | R_up {R_up:.0f} kN | "
          f"N_t por lâmina {Nt_lam:.0f} kN")
    print(f"  hoje: sela {sela_n} + pé {pe_n} por lâmina → {atual} Ø20 por pilar")
    print(f"  A: tirante M{tir_l['d_mm']} por lâmina (η {tir_l['partes']['barra']:.2f}); pé ao cortante "
          f"{V_pe:.1f} kN → {pe_v} Ø20; sela inalterada (gravidade) → {A} por pilar")
    print(f"  B: A + dente de {prof} mm na face interna (σ∥ η 0,75; seção líquida da lâmina "
          f"{160 - prof}×320, η_N {sig_net:.2f} sem flambagem); sela 2 de posição → {B} por pilar")
    print(f"  C: tirante central M{tir_c['d_mm']} (η {tir_c['partes']['barra']:.2f}) entre as lâminas; "
          f"pé {pe_v}; sela inalterada → {C} por pilar")
print("\nTotal nos 14 bipartidos: " + " | ".join(f"{k}: {v}" for k, v in tot.items()))
print("Obra inteira (hoje 928): " + " | ".join(f"{k}: {928 - tot['atual'] + v}" for k, v in tot.items()))
