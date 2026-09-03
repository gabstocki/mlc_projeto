"""
opensees/opensees_vtk.py — Análise FEM + exportação VTK 3D para ParaView.

Gera arquivos .vtk com elementos hexaédricos (seção transversal real):
    - Viga duplo-bisel GL24h (seção variável h0..h_ap)
    - Pilares GL24h (seção quadrada 0.20×0.20m)
    - Terças GL24h (seção retangular 0.20×0.58m)

EXECUÇÃO:
    python -m mlc_projeto.opensees.opensees_vtk

ARQUIVOS GERADOS (output/vtk/):
    portico_ELU_C2.vtk
    portico_ELS_S1.vtk
    portico_ELS_S3.vtk
    portico_G_only.vtk

COMO ABRIR NO PARAVIEW:
    File → Open → portico_ELU_C2.vtk → Apply → R
    Coloring → eta_M  (taxa de utilização, 0..1)
    Coloring → M_kNm  (diagrama de momento)
    Coloring → sigma_MPa (tensão normal)

CAMPOS (Cell Data — por elemento):
    M_kNm      — momento fletor (kN·m)
    V_kN       — cortante (kN)
    N_kN       — força axial (kN)
    sigma_MPa  — tensão normal máxima (MPa)
    eta_M      — taxa de utilização em flexão (adimensional)

DEPENDÊNCIAS:
    pip install openseespy pyvista numpy
"""

from __future__ import annotations
import math
import os
from pathlib import Path

import numpy as np
import pyvista as pv
import openseespy.opensees as ops

# ── Parâmetros do projeto ─────────────────────────────────────────────────────

L        = 20.25
H_PIL    = 7.0
h0       = 0.60
h_ap     = 1.397
ALPHA    = math.radians(4.5)
B_V      = 0.26
B_PIL    = 0.20
E        = 11.5e6
F_MD     = 17.28
N_V      = 40

B_T      = 0.20
H_T      = 0.58
S_TERCA  = 2.53
L_T      = 5.75
N_T      = 20

N_PORT   = 9
DIST_MOD = 5.75
N_X      = 2

UP = np.array([0.0, 0.0, 1.0])

COMBOS = {
    "ELU_C2": 9.6634,
    "ELS_S1": 6.2660,
    "ELS_S3": 4.3125,
    "G_only": 3.0187,
}

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "vtk"


# ── Geometria ─────────────────────────────────────────────────────────────────

def h_secao(x: float) -> float:
    xs = x if x <= L/2 else L - x
    return h0 + xs * math.tan(ALPHA)


def z_centro(x: float) -> float:
    """Eixo do CENTROIDE — viga bi-chanfrada de intradorso HORIZONTAL."""
    return H_PIL + h_secao(x) / 2.0


def z_extra(x: float) -> float:
    """Extradorso (topo da viga) — onde apoiam as terças."""
    return H_PIL + h_secao(x)


# Compatibilidade: o eixo usado para posicionar/extrudar é o centroide.
z_intrados = z_centro


def posicoes_tercas() -> list:
    n  = round((L/2) / S_TERCA)
    xh = [i*(L/2)/n for i in range(n+1)]
    return sorted(set(xh + [L-x for x in xh] + [0.0, L]))


# ── Campos analíticos ─────────────────────────────────────────────────────────

# Inclinação do eixo do centroide (intradorso horizontal): θ = atan(tanα/2).
THETA = math.atan(math.tan(ALPHA) / 2.0)


def y_c(x):
    """Braço do empuxo — flecha do eixo do centroide sobre a corda."""
    xs = x if x <= L/2 else L - x
    return xs * math.tan(ALPHA) / 2.0


def M_viga(x, Rv, H, q):
    """Momento biarticulado: M(x) = M_0(x) − H·y_c(x) (M na cumeeira ≠ 0)."""
    xs = x if x <= L/2 else L - x
    return 0.5*q*xs*(L - xs) - H*y_c(x)


def V_viga(x, Rv, H, q):
    """Cortante ⊥ ao eixo: V = S·cosθ − H·senθ, S = cortante da viga simples."""
    xs = x if x <= L/2 else L - x
    S  = q*(L/2.0 - xs)                       # cortante isostático (≥ 0)
    s  = 1.0 if x <= L/2 else -1.0            # antissimétrico
    return s*(S*math.cos(THETA) - H*math.sin(THETA))


def N_viga(x, Rv, H, q):
    """Normal no eixo (compressão +): N = H·cosθ + S·senθ."""
    xs = x if x <= L/2 else L - x
    S  = q*(L/2.0 - xs)
    return H*math.cos(THETA) + S*math.sin(THETA)


def sigma_viga(x, Rv, H, q):
    Mx = M_viga(x, Rv, H, q)
    Nx = N_viga(x, Rv, H, q)
    hx = h_secao(x)
    return (abs(Mx)/(B_V*hx**2/6) + abs(Nx)/(B_V*hx)) * 1e-3


# ── Análise OpenSeesPy — Viga ─────────────────────────────────────────────────

def analisar_viga(q: float) -> dict:
    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    xn = [i*(L/2)/N_V for i in range(N_V+1)]
    for i, x in enumerate(xn):
        ops.node(i+1, x, z_centro(x))        # eixo no centroide (intr. horizontal)

    ops.fix(1,      1, 1, 0)                  # rótula do apoio (Rz livre)
    ops.fix(N_V+1,  1, 0, 1)                  # SIMETRIA de peça contínua: Rz FIXO

    ops.geomTransf('Linear', 1)
    for i in range(N_V):
        xm = (xn[i]+xn[i+1])/2
        hm = h_secao(xm)
        ops.element('elasticBeamColumn', i+1, i+1, i+2,
                    B_V*hm, E, B_V*hm**3/12, 1)

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    F = q*(L/2)/N_V/2
    for i in range(N_V):
        ops.load(i+1, 0, -F, 0)
        ops.load(i+2, 0, -F, 0)

    ops.system('BandGeneral'); ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear'); ops.analysis('Static')
    ops.analyze(1)

    ops.reactions()
    Ry = ops.nodeReaction(1, 2)
    H  = ops.nodeReaction(1, 1)
    ux_h = [ops.nodeDisp(i+1, 1) for i in range(N_V+1)]
    uz_h = [ops.nodeDisp(i+1, 2) for i in range(N_V+1)]
    ops.wipe()

    xfull = xn + [L-x for x in xn[-2::-1]]
    return dict(
        Ry=Ry, H=H, xfull=xfull,
        ux=ux_h + [u for u in ux_h[-2::-1]],
        uz=uz_h + [u for u in uz_h[-2::-1]],
    )


# ── Análise OpenSeesPy — Terça ────────────────────────────────────────────────

def analisar_terca(q_t: float) -> dict:
    A_T = B_T * H_T
    I_T = B_T * H_T**3 / 12
    W_T = B_T * H_T**2 / 6

    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    for i in range(N_T+1):
        ops.node(i+1, i*L_T/N_T, 0.0)

    ops.fix(1,      1, 1, 0)
    ops.fix(N_T+1,  0, 1, 0)

    ops.geomTransf('Linear', 1)
    for i in range(N_T):
        ops.element('elasticBeamColumn', i+1, i+1, i+2, A_T, E, I_T, 1)

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    F = q_t * L_T / N_T / 2
    for i in range(N_T):
        ops.load(i+1, 0, -F, 0)
        ops.load(i+2, 0, -F, 0)

    ops.system('BandGeneral'); ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear'); ops.analysis('Static')
    ops.analyze(1)

    uz = [ops.nodeDisp(i+1, 2) for i in range(N_T+1)]
    ops.wipe()

    yn  = [i*L_T/N_T for i in range(N_T+1)]
    M_c = [q_t*(yn[i]+yn[i+1])/2*(L_T-(yn[i]+yn[i+1])/2)/2
           for i in range(N_T)]
    V_c = [q_t*(L_T/2-(yn[i]+yn[i+1])/2) for i in range(N_T)]
    s_c = [abs(M_c[i])/W_T*1e-3 for i in range(N_T)]

    return dict(yn=yn, uz=uz,
                M_c=M_c, V_c=V_c,
                sig_c=s_c, eta_c=[s/F_MD for s in s_c])


# ── Extrusão de seção retangular → VTK_HEXAHEDRON ────────────────────────────

def hex_nos(p_i, p_j, b, h_i, h_j, up=UP):
    p_i = np.asarray(p_i, dtype=float)
    p_j = np.asarray(p_j, dtype=float)
    ex  = p_j - p_i
    Le  = np.linalg.norm(ex)
    if Le < 1e-10:
        return None
    ex = ex / Le

    ez = up - np.dot(up, ex)*ex
    if np.linalg.norm(ez) < 1e-10:
        alt = np.array([0.0, 1.0, 0.0])
        ez  = alt - np.dot(alt, ex)*ex
    ez = ez / np.linalg.norm(ez)
    ey = np.cross(ez, ex); ey = ey / np.linalg.norm(ey)

    def face(p, h):
        return [p - ey*(b/2) - ez*(h/2),
                p + ey*(b/2) - ez*(h/2),
                p + ey*(b/2) + ez*(h/2),
                p - ey*(b/2) + ez*(h/2)]

    return np.array(face(p_i, h_i) + face(p_j, h_j))


# ── Malha 3D completa ─────────────────────────────────────────────────────────

def construir_malha(rv: dict, rt: dict, q: float) -> pv.UnstructuredGrid:
    xfull    = rv['xfull']
    Ry, H    = rv['Ry'], rv['H']
    n_elem_v = len(xfull) - 1
    x_t      = posicoes_tercas()
    up_pil   = np.array([1.0, 0.0, 0.0])

    all_pts=[]; inc=[]; tipo_c=[]
    M_c=[]; V_c=[]; N_c=[]; sig_c=[]; eta_c=[]

    def add_hex(p_i, p_j, b, h_i, h_j, M, V, N, sig, eta, up=UP):
        nos = hex_nos(p_i, p_j, b, h_i, h_j, up)
        if nos is None:
            return
        base = len(all_pts)
        all_pts.extend(nos.tolist())
        inc.append([8] + list(range(base, base+8)))
        tipo_c.append(12)
        M_c.append(M); V_c.append(V); N_c.append(N)
        sig_c.append(sig); eta_c.append(eta)

    # Vigas
    for ix in range(N_X):
        x_off = ix*L
        for iy in range(N_PORT):
            y = iy*DIST_MOD
            for i in range(n_elem_v):
                xi=xfull[i]; xj=xfull[i+1]; xm=(xi+xj)/2
                sm=sigma_viga(xm,Ry,H,q)
                add_hex([x_off+xi,y,z_intrados(xi)],
                        [x_off+xj,y,z_intrados(xj)],
                        B_V, h_secao(xi), h_secao(xj),
                        M_viga(xm,Ry,H,q), V_viga(xm,Ry,H,q),
                        N_viga(xm,Ry,H,q), sm, sm/F_MD)

    # Pilares
    for ix in range(N_X):
        x_off = ix*L
        for iy in range(N_PORT):
            y=iy*DIST_MOD; Np=abs(Ry); sp=Np/(B_PIL**2)*1e-3
            for x_pil in [0.0, L]:
                add_hex([x_off+x_pil,y,0.0],
                        [x_off+x_pil,y,H_PIL],
                        B_PIL, B_PIL, B_PIL,
                        0.0, abs(H), Np, sp, sp/F_MD, up=up_pil)

    # Terças
    yn = rt['yn']
    for ix in range(N_X):
        x_off = ix*L
        for iy in range(N_PORT-1):
            y0=iy*DIST_MOD
            for xt_loc in x_t:
                xt=x_off+xt_loc; zt=z_extra(xt_loc)   # terças sobre o extradorso
                for i in range(N_T):
                    add_hex([xt,y0+yn[i],  zt],
                            [xt,y0+yn[i+1],zt],
                            B_T, H_T, H_T,
                            rt['M_c'][i], rt['V_c'][i], 0.0,
                            rt['sig_c'][i], rt['eta_c'][i])

    malha = pv.UnstructuredGrid(
        np.array(inc,     dtype=int),
        np.array(tipo_c,  dtype=int),
        np.array(all_pts, dtype=float),
    )
    malha.cell_data['M_kNm']     = np.array(M_c,   dtype=float)
    malha.cell_data['V_kN']      = np.array(V_c,   dtype=float)
    malha.cell_data['N_kN']      = np.array(N_c,   dtype=float)
    malha.cell_data['sigma_MPa'] = np.array(sig_c, dtype=float)
    malha.cell_data['eta_M']     = np.array(eta_c, dtype=float)
    return malha


# ── Pipeline ──────────────────────────────────────────────────────────────────

def gerar_vtk() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  OpenSeesPy → VTK 3D (hexaedros) para ParaView")
    print("  Galpão MLC — STOCKI Engenharia Estrutural")
    print("=" * 64)
    print(f"\n  Viga:  L={L}m | H={H_PIL}m | h0={h0}m | "
          f"alfa={math.degrees(ALPHA):.1f}graus | b={B_V}m")
    print(f"  Pilar: {B_PIL}x{B_PIL}m  |  Terca: {B_T}x{H_T}m")
    print(f"  Porticos: {N_PORT}xY x {N_X}xX  |  "
          f"Tercas: {len(posicoes_tercas())} por modulo")
    print(f"  Saida: {OUTPUT_DIR}\n")

    for nome, q in COMBOS.items():
        print(f"  [{nome}] q={q:.4f} kN/m ... ", end="", flush=True)

        rv = analisar_viga(q)
        rt = analisar_terca((q/L_T)*S_TERCA)
        malha = construir_malha(rv, rt, q)

        arq = OUTPUT_DIR / f"portico_{nome}.vtk"
        malha.save(str(arq))

        from mlc_projeto.core.loads import analisar_biarticulada
        H_an  = analisar_biarticulada(q, L, h0, h_ap, ALPHA, B_V)["H_kN"]
        err   = abs(rv['H']-H_an) / H_an * 100
        eta_m = float(np.max(np.abs(malha.cell_data['eta_M'])))

        print(f"OK | Ry={rv['Ry']:.2f} H={rv['H']:.2f} kN "
              f"err={err:.3f}% | {malha.n_cells} hex | "
              f"eta_max={eta_m:.4f} | {arq.stat().st_size//1024} KB")

    print(f"\n  ParaView: File -> Open -> portico_ELU_C2.vtk -> Apply -> R")
    print(f"  Coloring -> eta_M / M_kNm / sigma_MPa")
    print("=" * 64)


if __name__ == "__main__":
    gerar_vtk()