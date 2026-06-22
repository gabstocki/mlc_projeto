"""
opensees/opensees_vtk.py — Análise FEM + exportação VTK para ParaView.

Gera arquivos .vtk Legacy (um por combinação de carga) com toda a estrutura
3D do galpão: vigas duplo-bisel, pilares e terças.

EXECUÇÃO:
    python -m mlc_projeto.opensees.opensees_vtk

ARQUIVOS GERADOS (output/vtk/):
    portico_ELU_C2.vtk   — ELU combinação governante
    portico_ELS_S1.vtk   — ELS deformações em serviço
    portico_ELS_S3.vtk   — ELS permanente (fluência)
    portico_G_only.vtk   — só peso próprio

COMO ABRIR NO PARAVIEW:
    File → Open → portico_ELU_C2.vtk → Apply → R
    Coloring → eta_M  (taxa de utilização)
    Filters → Warp By Vector → displacement → Scale 1.0 → Apply

CAMPOS VTK (Point Data — nodais):
    displacement [3D]  — deslocamento amplificado ×200
    w_mm               — flecha vertical (mm)
    M_kNm              — momento fletor (kN·m)
    V_kN               — cortante (kN)
    N_kN               — força axial (kN)
    sigma_MPa          — tensão normal máxima (MPa)
    eta_M              — taxa de utilização em flexão

GEOMETRIA 3D:
    2 pórticos lado a lado  (x = 0..20.25 e x = 20.25..40.50 m)
    9 planos Y              (y = 0, 5.75, ..., 46.00 m)
    9 terças por módulo     (fechamento + 3 intermediárias + cumeeira + espelho)
    Pilares laterais e centrais

DEPENDÊNCIAS:
    pip install openseespy pyvista numpy
"""

from __future__ import annotations
import math
import os
from pathlib import Path

import numpy as np
import pyvista as pv

try:
    import openseespy.opensees as ops
    OPENSEES_OK = True
except ImportError:
    OPENSEES_OK = False
    print("ERRO: openseespy não instalado. Rode: pip install openseespy")

# ── Parâmetros do projeto ─────────────────────────────────────────────────────

# Viga principal
L        = 20.25          # m — vão de cada pórtico
H_PIL    = 7.0            # m — altura do pilar
h0       = 0.60           # m — altura da seção no apoio
h_ap     = 1.397          # m — altura na cumeeira
ALPHA    = math.radians(4.5)
B_V      = 0.26           # m — largura da viga
E        = 11.5e6         # kN/m² — E_mean GL24h
F_MD     = 17.28          # MPa — resistência de cálculo ELU_C2
N_V      = 40             # elementos por meia viga

# Terças
B_T      = 0.20           # m — largura da terça
H_T      = 0.58           # m — altura da terça
S_TERCA  = 2.53           # m — espaçamento entre terças
L_T      = 5.75           # m — vão da terça (= dist entre pórticos)
N_T      = 20             # elementos por terça

# Pórticos
N_PORT   = 9              # pórticos ao longo de Y (8 módulos + 1)
DIST_MOD = 5.75           # m — espaçamento entre pórticos
N_X      = 2              # pórticos lado a lado (vão total 40.5 m)
AMP      = 200            # fator amplificação deformada

# Combinações de carga (q total na viga, kN/m)
COMBOS = {
    "ELU_C2": 9.6634,
    "ELS_S1": 6.2660,
    "ELS_S3": 4.3125,
    "G_only": 3.0187,
}

# Diretório de saída
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "vtk"


# ── Geometria ─────────────────────────────────────────────────────────────────

def z_intrados(x: float) -> float:
    """Coordenada Z do intrados da viga em x."""
    xs = x if x <= L/2 else L - x
    return H_PIL + xs * math.tan(ALPHA)


def h_secao(x: float) -> float:
    """Altura da seção transversal da viga em x."""
    xs = x if x <= L/2 else L - x
    return h0 + xs * math.tan(ALPHA)


def posicoes_tercas() -> list:
    """
    Retorna todas as posições x das terças por pórtico.

    Inclui: fechamento (x=0), 3 intermediárias por meia água,
    cumeeira (x=L/2) e espelho.
    Total: 9 terças por módulo.
    """
    n_half = round((L/2) / S_TERCA)          # 4 espaços
    x_half = [i*(L/2)/n_half for i in range(n_half+1)]   # 0..L/2
    todas  = sorted(set(
        x_half +
        [L - x for x in x_half] +
        [0.0, L]
    ))
    return todas


# ── Análise OpenSees — Viga principal ────────────────────────────────────────

def analisar_viga(q: float) -> dict | None:
    """
    Analisa o pórtico de 3 rótulas — meia estrutura com simetria.
    Eixo no intrados: z(x) = H_PIL + x·tan(α).

    Args:
        q : Carga distribuída total (kN/m)

    Returns:
        Dict com campos nodais para a viga completa ou None se falhou.
    """
    if not OPENSEES_OK:
        return None

    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    xn = [i*(L/2)/N_V for i in range(N_V+1)]
    for i, x in enumerate(xn):
        ops.node(i+1, x, z_intrados(x))

    ops.fix(1,      1, 1, 0)   # rótula base
    ops.fix(N_V+1,  1, 0, 0)   # simetria cumeeira

    ops.geomTransf('Linear', 1)
    for i in range(N_V):
        xm = (xn[i]+xn[i+1])/2; hm = h_secao(xm)
        ops.element('elasticBeamColumn', i+1, i+1, i+2,
                    B_V*hm, E, B_V*hm**3/12, 1)

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    F = q*(L/2)/N_V/2
    for i in range(N_V):
        ops.load(i+1, 0,-F,0)
        ops.load(i+2, 0,-F,0)

    ops.system('BandGeneral'); ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear'); ops.analysis('Static')
    if ops.analyze(1) != 0:
        ops.wipe(); return None

    ops.reactions()
    Ry = ops.nodeReaction(1, 2)
    H  = ops.nodeReaction(1, 1)
    ux_h = [ops.nodeDisp(i+1, 1) for i in range(N_V+1)]
    uz_h = [ops.nodeDisp(i+1, 2) for i in range(N_V+1)]
    ops.wipe()

    # Viga completa (espelhar meia esquerda)
    xfull = xn + [L-x for x in xn[-2::-1]]
    ux    = ux_h + [u for u in ux_h[-2::-1]]
    uz    = uz_h + [u for u in uz_h[-2::-1]]

    # Campos nodais via equilíbrio externo
    M=[]; V=[]; N=[]; sig=[]; eta=[]
    for x in xfull:
        Mx = Ry*x - H*x*math.tan(ALPHA) - q*x**2/2
        Vx = Ry - H*math.tan(ALPHA) - q*x
        Nx = H*math.cos(ALPHA) + Ry*math.sin(ALPHA) - q*x*math.sin(ALPHA)
        hx = h_secao(x); Wx = B_V*hx**2/6; Ax = B_V*hx
        sx = (abs(Mx)/Wx + abs(Nx)/Ax) * 1e-3   # MPa
        M.append(Mx); V.append(Vx); N.append(Nx)
        sig.append(sx); eta.append(sx/F_MD)

    return dict(Ry=Ry, H=H, xfull=xfull,
                ux=ux, uz=uz, M=M, V=V, N=N, sig=sig, eta=eta)


# ── Análise OpenSees — Terça ─────────────────────────────────────────────────

def analisar_terca(q_terca: float) -> dict | None:
    """
    Analisa uma terça biapoiada de vão L_T com carga uniforme q_terca.

    Args:
        q_terca : Carga linear na terça (kN/m)

    Returns:
        Dict com campos nodais ao longo do vão ou None se falhou.
    """
    if not OPENSEES_OK:
        return None

    A_T = B_T * H_T
    I_T = B_T * H_T**3 / 12
    W_T = B_T * H_T**2 / 6

    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    for i in range(N_T+1):
        ops.node(i+1, i*L_T/N_T, 0.0)

    ops.fix(1,      1, 1, 0)   # pino
    ops.fix(N_T+1,  0, 1, 0)   # rolete

    ops.geomTransf('Linear', 1)
    for i in range(N_T):
        ops.element('elasticBeamColumn', i+1, i+1, i+2, A_T, E, I_T, 1)

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    F = q_terca * L_T / N_T / 2
    for i in range(N_T):
        ops.load(i+1, 0,-F,0)
        ops.load(i+2, 0,-F,0)

    ops.system('BandGeneral'); ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear'); ops.analysis('Static')
    if ops.analyze(1) != 0:
        ops.wipe(); return None

    uz = [ops.nodeDisp(i+1, 2) for i in range(N_T+1)]
    ops.wipe()

    yn  = [i*L_T/N_T for i in range(N_T+1)]
    M   = [q_terca * y * (L_T-y) / 2 for y in yn]
    V   = [q_terca * (L_T/2 - y)     for y in yn]
    sig = [abs(M[i])/W_T * 1e-3       for i in range(N_T+1)]
    eta = [sig[i]/F_MD                 for i in range(N_T+1)]

    return dict(yn=yn, uz=uz, M=M, V=V,
                N=[0.0]*(N_T+1), sig=sig, eta=eta)


# ── Construção da malha 3D ────────────────────────────────────────────────────

def construir_malha(res_v: dict, res_t: dict) -> pv.UnstructuredGrid:
    """
    Constrói a malha 3D completa: vigas + pilares + terças.

    Geometria:
        - N_X pórticos ao longo de X (lado a lado)
        - N_PORT posições ao longo de Y
        - 9 terças por módulo (fechamento + intermediárias + cumeeira)

    Returns:
        pv.UnstructuredGrid com todos os campos nodais.
    """
    xfull       = res_v['xfull']
    n_nos_viga  = len(xfull)
    n_elem_viga = n_nos_viga - 1
    x_tercas    = posicoes_tercas()   # 9 posições
    n_nos_terca = len(res_t['yn'])    # N_T+1
    n_elem_terca= n_nos_terca - 1

    # ── Acumuladores ─────────────────────────────────────────
    coords_list = []
    disp_list   = []
    M_list=[]; V_list=[]; N_list=[]; sig_list=[]; eta_list=[]

    node_base_viga  = {}   # (ix, iy) → índice primeiro nó da viga
    node_base_terca = {}   # (ix, iy, it) → índice primeiro nó da terça

    def add_no(x, y, z, ux, uy, uz, M, V, N, sig, eta):
        coords_list.append([x, y, z])
        disp_list.append([ux, uy, uz])
        M_list.append(M); V_list.append(V); N_list.append(N)
        sig_list.append(sig); eta_list.append(eta)

    # ── Nós: vigas e pilares ─────────────────────────────────
    for ix in range(N_X):
        x_off = ix * L
        for iy in range(N_PORT):
            y    = iy * DIST_MOD
            base = len(coords_list)
            node_base_viga[(ix, iy)] = base
            sx   = -1 if ix == 1 else 1   # espelha Ux para pórtico 2

            # Nós da viga
            for i, xr in enumerate(xfull):
                add_no(x_off+xr, y, z_intrados(xr),
                       res_v['ux'][i]*AMP*sx, 0.0, res_v['uz'][i]*AMP,
                       res_v['M'][i], res_v['V'][i], res_v['N'][i],
                       res_v['sig'][i], res_v['eta'][i])

            # Base pilar esquerdo
            add_no(x_off+0.0, y, 0.0,  0,0,0,
                   0, 0, abs(res_v['Ry']), 0.5, 0.05)

            # Base pilar direito
            add_no(x_off+L,   y, 0.0,  0,0,0,
                   0, 0, abs(res_v['Ry']), 0.5, 0.05)

    # ── Nós: terças ───────────────────────────────────────────
    for ix in range(N_X):
        x_off = ix * L
        for iy in range(N_PORT-1):   # 8 módulos entre pórticos
            y0 = iy * DIST_MOD
            for it, xt_loc in enumerate(x_tercas):
                base_t = len(coords_list)
                node_base_terca[(ix, iy, it)] = base_t

                xt = x_off + xt_loc
                zt = z_intrados(xt_loc)   # altura da terça

                for i, y_loc in enumerate(res_t['yn']):
                    y_abs = y0 + y_loc
                    add_no(xt, y_abs, zt,
                           0.0, 0.0, res_t['uz'][i]*AMP,
                           res_t['M'][i], res_t['V'][i],
                           res_t['N'][i], res_t['sig'][i],
                           res_t['eta'][i])

    # ── Incidências ───────────────────────────────────────────
    inc_list = []

    # Vigas e pilares
    for ix in range(N_X):
        for iy in range(N_PORT):
            base = node_base_viga[(ix, iy)]

            # Elementos da viga
            for i in range(n_elem_viga):
                inc_list.append([2, base+i, base+i+1])

            # Pilar esquerdo: base → topo (nó 0 da viga)
            inc_list.append([2, base+n_nos_viga,    base+0])
            # Pilar direito: base → topo (último nó da viga)
            inc_list.append([2, base+n_nos_viga+1,  base+n_nos_viga-1])

    # Terças
    for ix in range(N_X):
        for iy in range(N_PORT-1):
            for it in range(len(x_tercas)):
                base_t = node_base_terca[(ix, iy, it)]
                for i in range(n_elem_terca):
                    inc_list.append([2, base_t+i, base_t+i+1])

    # ── Criar UnstructuredGrid ────────────────────────────────
    coordenadasNos = np.array(coords_list, dtype=float)
    deslocamentos  = np.array(disp_list,   dtype=float)
    incidenciaVTK  = np.array(inc_list,    dtype=int)
    tipoCelulaVTK  = np.full(len(inc_list), 3, dtype=int)   # VTK_LINE

    malha = pv.UnstructuredGrid(incidenciaVTK, tipoCelulaVTK, coordenadasNos)

    malha['displacement'] = deslocamentos
    malha['w_mm']         = -deslocamentos[:, 2] * 1e3
    malha['M_kNm']        = np.array(M_list)
    malha['V_kN']         = np.array(V_list)
    malha['N_kN']         = np.array(N_list)
    malha['sigma_MPa']    = np.array(sig_list)
    malha['eta_M']        = np.array(eta_list)

    return malha


# ── Pipeline principal ────────────────────────────────────────────────────────

def gerar_vtk() -> None:
    """
    Pipeline completo: análise FEM → exportação VTK.

    Para cada combinação de carga:
        1. Analisa a viga principal (OpenSeesPy)
        2. Analisa a terça representativa (OpenSeesPy)
        3. Constrói malha 3D completa (pyvista)
        4. Exporta .vtk Legacy
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  OpenSeesPy → VTK para ParaView")
    print("  Galpão MLC — STOCKI Engenharia Estrutural")
    print("=" * 64)
    print(f"\n  Geometria:")
    print(f"    Vão:    L={L}m | H={H_PIL}m | h0={h0}m | α={math.degrees(ALPHA):.1f}°")
    print(f"    Seção:  b={B_V}m (viga) | {B_T}×{H_T}m (terça)")
    print(f"    Pórticos: {N_PORT}×Y × {N_X}×X | Terças: {len(posicoes_tercas())} por módulo")
    print(f"    Deformada amplificada: ×{AMP}")
    print(f"    Saída: {OUTPUT_DIR}/\n")

    x_t = posicoes_tercas()
    print(f"  Posições das terças (x local): {[round(x,3) for x in x_t]}\n")

    for nome, q in COMBOS.items():
        print(f"  [{nome}] q={q:.4f} kN/m", end=" ... ", flush=True)

        # Carga na terça
        q_area  = q / L_T          # kN/m²
        q_terca = q_area * S_TERCA  # kN/m na terça

        res_v = analisar_viga(q)
        if res_v is None:
            print("FALHOU (viga)"); continue

        res_t = analisar_terca(q_terca)
        if res_t is None:
            print("FALHOU (terça)"); continue

        malha = construir_malha(res_v, res_t)

        # Verificação rápida
        f_geo = h_ap - h0
        H_an  = (res_v['Ry']*(L/2) - q*(L/2)**2/2) / f_geo
        err   = abs(res_v['H'] - H_an) / H_an * 100

        arq = OUTPUT_DIR / f"portico_{nome}.vtk"
        malha.save(str(arq))

        print(f"OK")
        print(f"    Ry={res_v['Ry']:.2f} H={res_v['H']:.2f} kN (err_H={err:.3f}%)")
        print(f"    {malha.n_points} pts | {malha.n_cells} cells | "
              f"{arq.stat().st_size/1024:.1f} KB → {arq.name}")

    print(f"\n  ── Como abrir no ParaView ─────────────────────────")
    print(f"  1. File → Open → portico_ELU_C2.vtk → Apply → R")
    print(f"  2. Coloring → eta_M  (taxa de utilização 0..1)")
    print(f"     Coloring → M_kNm  (diagrama de momento)")
    print(f"     Coloring → sigma_MPa  (tensão normal)")
    print(f"  3. Deformada: Filters → Warp By Vector")
    print(f"     → Vectors: displacement → Scale: 1.0 → Apply")
    print("=" * 64)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    gerar_vtk()