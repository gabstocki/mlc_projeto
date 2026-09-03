"""
opensees/opensees_model.py — Validação FEM da viga BIARTICULADA monolítica.

Modelo OpenSeesPy de meia viga com condição de SIMETRIA de peça CONTÍNUA.
Eixo de referência: CENTROIDE da viga (intradorso HORIZONTAL, bi-chanfrada).

FORMULAÇÃO (coerente com core/loads.py — Castigliano com termo AXIAL):
    z_centroide(x) = H_pilar + h(x)/2,  h(x) = h0 + x·tan(α),  0 ≤ x ≤ L/2
    Flecha do eixo (braço do empuxo): y_c(x) = x·tan(α)/2
    H por compatibilidade: δ11 = ∫ y_c²/(EI) ds + ∫ cos²θ/(EA) ds  (axial INCLUÍDO)
    M(x) = M_0(x) − H·y_c(x),  com M na cumeeira ≠ 0 (continuidade, sem rótula).

CONDIÇÕES DE CONTORNO (meia viga):
    Apoio (x=0):      fix Ux, Uy; livre Rz          ← rótula do apoio
    Cumeeira (x=L/2): fix Ux, Rz; livre Uy          ← SIMETRIA de peça contínua
                                                      (Rz FIXO ⇒ sem rótula no ápice)

NOTA — modelo triarticulado (legado, REMOVIDO):
    A versão anterior liberava Rz na cumeeira (rótula) e usava o intradorso como
    linha de pressão (braço f = h_ap−h0). Isso modelava um pórtico de 3 rótulas,
    incompatível com a peça monolítica de MLC dos cálculos. Corrigido.
"""

from __future__ import annotations
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

try:
    import openseespy.opensees as ops
    OPENSEES_OK = True
except ImportError:
    OPENSEES_OK = False

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def analisar_analitico(q: float, L: float, h0: float, h_ap: float,
                       alpha_rad: float, b: float) -> dict:
    """
    Solução analítica — viga BIARTICULADA monolítica (Castigliano c/ axial).

    Delega para core.loads.analisar_biarticulada (fonte única da verdade), de
    modo que a validação FEM confira exatamente o modelo de cálculo.
    """
    from mlc_projeto.core.loads import analisar_biarticulada
    r = analisar_biarticulada(q, L, h0, h_ap, alpha_rad, b)
    return dict(Rv=r["R_v_kN"], H=r["H_kN"], N=r["N_apoio_kN"],
                Mmax=r["M_max_kNm"], xMmax=r["x_Mmax_m"],
                Mcum=r["M_cumeeira_kNm"], f=round((h_ap - h0) / 2.0, 4))


def analisar_fem(q: float, L: float, h0: float, h_ap: float,
                 alpha_rad: float, b: float, E: float,
                 H_pilar: float = 7.0, n_v: int = 40) -> dict:
    """
    Modelo FEM de meia estrutura — pórtico de 3 rótulas.
    Eixo no intrados: z(x) = H_pilar + x·tan(α).
    """
    if not OPENSEES_OK:
        return {"erro": "OpenSeesPy não disponível"}

    # Unidades consistentes: forças em kN, comprimentos em m ⇒ E em kN/m².
    E_kN = E / 1e3
    tan_a = math.tan(alpha_rad)

    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    xnodes = [i*(L/2)/n_v for i in range(n_v+1)]
    # Eixo no CENTROIDE (intradorso horizontal): z = H_pilar + h(x)/2.
    znodes = [H_pilar + (h0 + x*tan_a)/2.0 for x in xnodes]

    for i,(x,z) in enumerate(zip(xnodes, znodes)):
        ops.node(i+1, x, z)

    ops.fix(1,      1, 1, 0)   # rótula do apoio (Rz livre)
    ops.fix(n_v+1,  1, 0, 1)   # SIMETRIA de peça contínua: Rz FIXO (sem rótula)

    ops.geomTransf('Linear', 1)
    for i in range(n_v):
        xm = (xnodes[i]+xnodes[i+1])/2
        hm = h0 + xm*tan_a
        ops.element('elasticBeamColumn', i+1, i+1, i+2,
                    b*hm, E_kN, b*hm**3/12, 1)

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    F = q*(L/2)/n_v/2
    for i in range(n_v):
        ops.load(i+1, 0,-F,0)
        ops.load(i+2, 0,-F,0)

    ops.system('BandGeneral'); ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear'); ops.analysis('Static')
    ok = ops.analyze(1)

    if ok != 0:
        ops.wipe()
        return {"erro": "Análise falhou"}

    ops.reactions()
    Ry = ops.nodeReaction(1,  2)
    H  = ops.nodeReaction(1,  1)   # empuxo horizontal no apoio

    # Momento biarticulado: M(x) = M_0(x) − H·y_c(x), y_c = x·tan(α)/2.
    y_c = [x*tan_a/2.0 for x in xnodes]
    Meq = [0.5*q*x*(L-x) - H*y_c[i] for i,x in enumerate(xnodes)]
    Mmax = max(Meq, key=abs)
    xMmax = xnodes[Meq.index(Mmax)]

    # Deslocamentos verticais (flecha do eixo) em mm
    w_vals = [-ops.nodeDisp(i+1, 2)*1e3 for i in range(n_v+1)]
    w_max  = max(w_vals, key=abs)
    xwmax  = xnodes[w_vals.index(w_max)]

    # Força axial no elemento do apoio (kN)
    N_ax = abs(ops.eleForce(1)[0])

    ops.wipe()
    return dict(
        Ry=round(Ry,4), H=round(H,4), N=round(N_ax,4),
        Mmax=round(Mmax,4), xMmax=round(xMmax,4),
        wmax=round(w_max,4), xwmax=round(xwmax,4),
        xnodes=xnodes, wnodes=w_vals, Meq=Meq,
    )


def comparar_e_plotar(geo, mat, load, H_pilar=7.0, n_v=40,
                      salvar="opensees_resultados.png"):
    """
    Compara FEM vs analítico e gera figura com diagrama M(x) e deformada.
    """
    L=geo.L; h0=geo.h0; h_ap=geo.h_ap; al=geo.alpha_rad; b=geo.b
    E=mat.E0_mean

    combos = {
        "ELU_C2": load.combinacoes["ELU_C2"].q_tot,
        "ELS_S1": load.combinacoes["ELS_S1"].q_tot,
        "ELS_S3": load.combinacoes["ELS_S3"].q_tot,
    }

    # ── Tabela de comparação ──────────────────────────────────
    print("=" * 72)
    print("  VALIDAÇÃO FEM — OpenSeesPy vs Analítico")
    print("  Viga Biarticulada monolítica | Eixo: centroide (intradorso horiz.)")
    print("=" * 72)
    rows = []
    for nome, q in combos.items():
        an  = analisar_analitico(q, L, h0, h_ap, al, b)
        fem = analisar_fem(q, L, h0, h_ap, al, b, E, H_pilar, n_v)
        if "erro" in fem: continue

        print(f"\n  {nome}  (q={q:.4f} kN/m)")
        for gnd, va, vf in [
            ("Ry (kN)",     an["Rv"],   fem["Ry"]),
            ("H (kN)",      an["H"],    fem["H"]),
            ("M_max (kN·m)",an["Mmax"], fem["Mmax"]),
            ("N_viga (kN)", an["N"],    fem["N"]),
        ]:
            err = abs(vf-va)/abs(va)*100 if abs(va)>1e-6 else 0
            print(f"  {'':2}{gnd:<18} an={va:>9.4f}  fem={vf:>9.4f}  err={err:.4f}%")
            rows.append({"Comb":nome,"q":q,"Grandeza":gnd,
                         "Analítico":va,"FEM":vf,"Erro(%)":round(err,4)})

    print(f"\n  Erro máximo: {max(r['Erro(%)'] for r in rows):.4f}%")
    print("=" * 72)

    # ── Figura ────────────────────────────────────────────────
    q_ELU = combos["ELU_C2"]; q_ELS = combos["ELS_S1"]
    an_ELU = analisar_analitico(q_ELU, L, h0, h_ap, al, b)
    fem_ELU = analisar_fem(q_ELU, L, h0, h_ap, al, b, E, H_pilar, n_v)
    fem_ELS = analisar_fem(q_ELS, L, h0, h_ap, al, b, E, H_pilar, n_v)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(
        f"Viga Biarticulada monolítica — Validação OpenSeesPy\n"
        f"STOCKI Engenharia Estrutural | L={L}m | h0={h0}m | α={geo.alpha_deg}°",
        fontsize=11, fontweight='bold'
    )

    # Diagrama M(x) — ELU_C2 (biarticulado: M(x) = M_0 − H·y_c, M_cum ≠ 0)
    ax1 = axes[0]
    xan = np.linspace(0, L/2, 400)
    Man = (0.5*q_ELU*xan*(L-xan) - an_ELU["H"]*xan*math.tan(al)/2.0)
    xfull = list(xan) + [L - x for x in xan[::-1]]
    Mfull = list(Man) + list(Man[::-1])

    xfem = fem_ELU["xnodes"]
    Mfem = fem_ELU["Meq"]
    xfem_full = xfem + [L-x for x in xfem[::-1]]
    Mfem_full = Mfem + Mfem[::-1]

    ax1.plot(xfull, Mfull, 'b-', lw=2,
             label=f'Analítico (M_max={an_ELU["Mmax"]:.2f} kN·m)')
    ax1.plot(xfem_full, Mfem_full, 'r--', lw=1.5, marker='.', ms=2,
             label=f'FEM OpenSees (M_max={fem_ELU["Mmax"]:.2f} kN·m)')
    ax1.axhline(0, color='k', lw=0.8); ax1.grid(True,alpha=0.3)
    ax1.set_xlabel('x (m)'); ax1.set_ylabel('M (kN·m)')
    ax1.set_title(f'Diagrama M(x) — ELU_C2 (q={q_ELU:.3f} kN/m)')
    ax1.legend(fontsize=8)

    # Deformada — ELS_S1
    ax2 = axes[1]
    amp = 200
    # Eixo original = centroide (intradorso horizontal): z = H_pilar + h(x)/2
    def z_orig(x): xs=x if x<=L/2 else L-x; return H_pilar+(h0+xs*math.tan(al))/2.0
    xpl = np.linspace(0, L, 200)
    ax2.plot(xpl, [z_orig(x) for x in xpl], 'b-', lw=1.5,
             label='Estrutura original')
    ax2.plot([0,0],[0,H_pilar],'b-',lw=1.5)
    ax2.plot([L,L],[0,H_pilar],'b-',lw=1.5)

    xdef = fem_ELS["xnodes"]; wdef = fem_ELS["wnodes"]
    zdef_L = [z_orig(x)-w*amp/1e3 for x,w in zip(xdef,wdef)]
    xdef_f = xdef + [L-x for x in xdef[-2::-1]]
    zdef_f = zdef_L + [z_orig(L-x)-wdef[i]*amp/1e3
                       for i,x in enumerate(xdef[-2::-1])]
    ax2.plot(xdef_f, zdef_f, 'r--', lw=1.5,
             label=f'Deformada ×{amp} (ELS_S1)\nw_max={fem_ELS["wmax"]:.2f}mm')
    for xr,yr in [(0,0),(L,0),(L/2,z_orig(L/2))]:
        ax2.plot(xr,yr,'bo',ms=7)
    ax2.grid(True,alpha=0.3); ax2.set_aspect('equal')
    ax2.set_xlabel('x (m)'); ax2.set_ylabel('z (m)')
    ax2.set_title(f'Deformada ×{amp} — ELS_S1 (q={q_ELS:.3f} kN/m)')
    ax2.legend(fontsize=8)

    OUTPUT_DIR.mkdir(exist_ok=True)
    caminho = str(OUTPUT_DIR / salvar)
    plt.tight_layout()
    plt.savefig(caminho, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Figura: {caminho}")

    return pd.DataFrame(rows)
