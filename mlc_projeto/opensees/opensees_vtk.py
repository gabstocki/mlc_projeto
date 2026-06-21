"""
opensees/opensees_vtk.py — OpenSeesPy → VTK XML (.vtu) + PVD para ParaView.

Exporta resultados do pórtico de 3 rótulas em formato VTK XML UnstructuredGrid
(.vtu), compatível com o vtkPVDReader do ParaView (versões 5.x e 6.x).

ARQUIVOS GERADOS (output/vtk/):
    portico_ELU_C2.vtu
    portico_ELS_S1.vtu
    portico_ELS_S3.vtu
    portico_G_only.vtu
    portico.pvd          ← índice — abrir este no ParaView

CAMPOS VTK:
    Point Data:
        displacement [3D]  — deslocamento amplificado ×200 (para Warp By Vector)
        w_mm               — flecha vertical (mm)

    Cell Data:
        M_kNm              — momento fletor (kN·m)
        V_kN               — cortante (kN)
        N_kN               — força axial (kN)
        sigma_MPa          — tensão normal máxima (MPa)
        eta_M              — taxa de utilização em flexão (adimensional)

GEOMETRIA 3D:
    2 pórticos lado a lado (x = 0..20.25 e x = 20.25..40.50 m)
    9 planos Y (y = 0, 5.75, 11.50, ..., 46.00 m)
    Cada pórtico: viga duplo-bisel (linha de barras) + 2 pilares
"""

from __future__ import annotations
import math
from pathlib import Path

try:
    import openseespy.opensees as ops
    OPENSEES_OK = True
except ImportError:
    OPENSEES_OK = False

# ── Parâmetros do projeto ─────────────────────────────────────────────────────

L            = 20.25          # m — vão de cada pórtico
H_PIL        = 7.0            # m — altura do pilar
h0           = 0.60           # m — altura da seção no apoio
h_ap         = 1.397          # m — altura na cumeeira
ALPHA        = math.radians(4.5)
B_VIGA       = 0.26           # m — largura da seção da viga
B_PIL        = 0.20           # m — largura da seção do pilar
E_MEAN       = 11.5e6         # kN/m² — E_mean GL24h
F_MD         = 17.28          # MPa = 17280 kN/m² — f_m,d ELU_C2
N_PORTICOS   = 9              # ao longo de Y (8 módulos + 1)
DIST_MOD     = 5.75           # m — espaçamento entre pórticos
N_PORTICOS_X = 2              # dois pórticos lado a lado
N_V          = 40             # elementos por meia viga
AMP          = 200            # fator de amplificação da deformada

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "vtk"

COMBOS = {
    "ELU_C2": 9.6634,
    "ELS_S1": 6.2660,
    "ELS_S3": 4.3125,
    "G_only": 3.0187,
}


# ── Geometria local ───────────────────────────────────────────────────────────

def z_intrados(x: float) -> float:
    xs = x if x <= L/2 else L - x
    return H_PIL + xs * math.tan(ALPHA)

def h_em(x: float) -> float:
    xs = x if x <= L/2 else L - x
    return h0 + xs * math.tan(ALPHA)


# ── Análise OpenSeesPy ────────────────────────────────────────────────────────

def analisar(q: float) -> dict | None:
    """
    Analisa o pórtico de 3 rótulas.
    Retorna dicionário com campos por nó para a viga completa.
    """
    if not OPENSEES_OK:
        return None

    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    xnodes = [i*(L/2)/N_V for i in range(N_V+1)]
    znodes = [z_intrados(x) for x in xnodes]

    for i, (x, z) in enumerate(zip(xnodes, znodes)):
        ops.node(i+1, x, z)

    ops.fix(1,      1, 1, 0)
    ops.fix(N_V+1,  1, 0, 0)

    ops.geomTransf('Linear', 1)
    for i in range(N_V):
        xm = (xnodes[i]+xnodes[i+1])/2
        hm = h_em(xm)
        ops.element('elasticBeamColumn', i+1, i+1, i+2,
                    B_VIGA*hm, E_MEAN, B_VIGA*hm**3/12, 1)

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
    ok = ops.analyze(1)
    if ok != 0:
        ops.wipe(); return None

    ops.reactions()
    Ry = ops.nodeReaction(1, 2)
    H  = ops.nodeReaction(1, 1)

    # Deslocamentos meia esquerda
    ux_h = [ops.nodeDisp(i+1, 1) for i in range(N_V+1)]
    uz_h = [ops.nodeDisp(i+1, 2) for i in range(N_V+1)]
    ops.wipe()

    # Campos por nó via equilíbrio externo (meia esquerda)
    M_h=[]; V_h=[]; N_h=[]; sig_h=[]; eta_h=[]
    for x in xnodes:
        M  = Ry*x - H*x*math.tan(ALPHA) - q*x**2/2
        V  = Ry - H*math.tan(ALPHA) - q*x
        Na = H*math.cos(ALPHA) + Ry*math.sin(ALPHA) - q*x*math.sin(ALPHA)
        hx = h_em(x)
        Wx = B_VIGA*hx**2/6; Ax = B_VIGA*hx
        sig = (abs(M)/Wx + abs(Na)/Ax) * 1e-3   # MPa
        M_h.append(M); V_h.append(V); N_h.append(Na)
        sig_h.append(sig); eta_h.append(sig/F_MD)

    # Espelhar para viga completa
    def esp(v): return v + v[-2::-1]

    xfull = xnodes + [L-x for x in xnodes[-2::-1]]
    zfull = znodes + [z_intrados(x) for x in xnodes[-2::-1]]
    # V é antissimétrico — invertemos no lado direito
    V_full = V_h + [-v for v in V_h[-2::-1]]

    return dict(
        Ry=Ry, H=H, q=q,
        xfull=xfull, zfull=zfull,
        ux=esp(ux_h), uz=esp(uz_h),
        M=esp(M_h), V=V_full,
        N=esp(N_h), sig=esp(sig_h), eta=esp(eta_h),
    )


# ── Exportação VTU XML ────────────────────────────────────────────────────────

def exportar_vtu(res: dict, caminho: Path) -> None:
    """
    Exporta resultados para arquivo .vtu (VTK XML UnstructuredGrid).
    Compatível com vtkPVDReader do ParaView 5.x e 6.x.
    """
    n_nos_viga  = len(res['xfull'])     # 81 nós por viga completa
    n_elem_viga = n_nos_viga - 1        # 80 elementos por viga

    # ── Construir geometria 3D completa ──────────────────────
    all_pts    = []   # [x, y, z]
    all_ux     = []   # deslocamento amplificado [3 componentes]
    all_w_mm   = []   # flecha escalar

    node_base  = {}   # (ix, iy) → índice do primeiro nó da viga

    for ix in range(N_PORTICOS_X):
        x_off = ix * L
        for iy in range(N_PORTICOS):
            y = iy * DIST_MOD
            base = len(all_pts)
            node_base[(ix, iy)] = base

            # Nós da viga (no intrados)
            for i, (xr, zr) in enumerate(zip(res['xfull'], res['zfull'])):
                all_pts.append([x_off + xr, y, zr])
                # Ux espelhado para pórtico 2 (sentidos opostos)
                ux_amp = res['ux'][i] * AMP * (-1 if ix == 1 else 1)
                uz_amp = res['uz'][i] * AMP
                all_ux.append([ux_amp, 0.0, uz_amp])
                all_w_mm.append(-res['uz'][i] * 1e3)

            # Nó base pilar esquerdo
            all_pts.append([x_off + 0.0, y, 0.0])
            all_ux.append([0.0, 0.0, 0.0])
            all_w_mm.append(0.0)

            # Nó base pilar direito
            all_pts.append([x_off + L, y, 0.0])
            all_ux.append([0.0, 0.0, 0.0])
            all_w_mm.append(0.0)

    n_pts = len(all_pts)
    NOS_POR_PORTICO = n_nos_viga + 2

    # ── Células ───────────────────────────────────────────────
    connectivity = []   # índices dos nós por célula (flat)
    offsets      = []   # offset acumulado
    types        = []   # tipo VTK (3 = LINE)
    all_M        = []
    all_V        = []
    all_N        = []
    all_sig      = []
    all_eta      = []

    off = 0
    for ix in range(N_PORTICOS_X):
        for iy in range(N_PORTICOS):
            base = node_base[(ix, iy)]

            # Elementos da viga
            for i in range(n_elem_viga):
                connectivity += [base+i, base+i+1]
                off += 2; offsets.append(off)
                types.append(3)   # VTK_LINE
                M_avg   = (res['M'][i]   + res['M'][i+1])   / 2
                V_avg   = (res['V'][i]   + res['V'][i+1])   / 2
                N_avg   = (res['N'][i]   + res['N'][i+1])   / 2
                sig_avg = (res['sig'][i] + res['sig'][i+1]) / 2
                eta_avg = (res['eta'][i] + res['eta'][i+1]) / 2
                all_M.append(M_avg); all_V.append(V_avg)
                all_N.append(N_avg); all_sig.append(sig_avg)
                all_eta.append(eta_avg)

            # Pilar esquerdo: base → topo (nó 0 da viga)
            idx_bE = base + n_nos_viga
            idx_tE = base + 0
            connectivity += [idx_bE, idx_tE]
            off += 2; offsets.append(off); types.append(3)
            N_pil = abs(res['N'][0])
            sig_pil = N_pil / (B_PIL**2) * 1e-3
            all_M.append(0.0); all_V.append(abs(res['H']))
            all_N.append(N_pil); all_sig.append(sig_pil)
            all_eta.append(sig_pil / F_MD)

            # Pilar direito: base → topo (último nó da viga)
            idx_bD = base + n_nos_viga + 1
            idx_tD = base + n_nos_viga - 1
            connectivity += [idx_bD, idx_tD]
            off += 2; offsets.append(off); types.append(3)
            all_M.append(0.0); all_V.append(abs(res['H']))
            all_N.append(N_pil); all_sig.append(sig_pil)
            all_eta.append(sig_pil / F_MD)

    n_cells = len(types)

    # ── Escrever VTU XML ──────────────────────────────────────
    def fmt_f(v): return f"{v:.6f}"
    def fmt_i(v): return str(v)

    with open(caminho, 'w') as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<VTKFile type="UnstructuredGrid" version="0.1" '
                'byte_order="LittleEndian">\n')
        f.write('  <UnstructuredGrid>\n')
        f.write(f'    <Piece NumberOfPoints="{n_pts}" '
                f'NumberOfCells="{n_cells}">\n')

        # Points
        f.write('      <Points>\n')
        f.write('        <DataArray type="Float32" '
                'NumberOfComponents="3" format="ascii">\n')
        for p in all_pts:
            f.write(f'          {fmt_f(p[0])} {fmt_f(p[1])} {fmt_f(p[2])}\n')
        f.write('        </DataArray>\n')
        f.write('      </Points>\n')

        # Cells
        f.write('      <Cells>\n')
        f.write('        <DataArray type="Int32" Name="connectivity" '
                'format="ascii">\n')
        line = []
        for v in connectivity:
            line.append(fmt_i(v))
            if len(line) == 10:
                f.write('          ' + ' '.join(line) + '\n'); line=[]
        if line: f.write('          ' + ' '.join(line) + '\n')
        f.write('        </DataArray>\n')

        f.write('        <DataArray type="Int32" Name="offsets" '
                'format="ascii">\n')
        line=[]
        for v in offsets:
            line.append(fmt_i(v))
            if len(line)==10:
                f.write('          '+' '.join(line)+'\n'); line=[]
        if line: f.write('          '+' '.join(line)+'\n')
        f.write('        </DataArray>\n')

        f.write('        <DataArray type="UInt8" Name="types" '
                'format="ascii">\n')
        line=[]
        for v in types:
            line.append(fmt_i(v))
            if len(line)==20:
                f.write('          '+' '.join(line)+'\n'); line=[]
        if line: f.write('          '+' '.join(line)+'\n')
        f.write('        </DataArray>\n')
        f.write('      </Cells>\n')

        # Point Data
        f.write('      <PointData>\n')

        f.write('        <DataArray type="Float32" Name="displacement" '
                'NumberOfComponents="3" format="ascii">\n')
        for d in all_ux:
            f.write(f'          {fmt_f(d[0])} {fmt_f(d[1])} {fmt_f(d[2])}\n')
        f.write('        </DataArray>\n')

        f.write('        <DataArray type="Float32" Name="w_mm" '
                'format="ascii">\n')
        for v in all_w_mm:
            f.write(f'          {fmt_f(v)}\n')
        f.write('        </DataArray>\n')

        f.write('      </PointData>\n')

        # Cell Data
        f.write('      <CellData>\n')
        for nome, vals in [
            ('M_kNm',    all_M),
            ('V_kN',     all_V),
            ('N_kN',     all_N),
            ('sigma_MPa',all_sig),
            ('eta_M',    all_eta),
        ]:
            f.write(f'        <DataArray type="Float32" Name="{nome}" '
                    f'format="ascii">\n')
            line=[]
            for v in vals:
                line.append(fmt_f(v))
                if len(line)==8:
                    f.write('          '+' '.join(line)+'\n'); line=[]
            if line: f.write('          '+' '.join(line)+'\n')
            f.write('        </DataArray>\n')
        f.write('      </CellData>\n')

        f.write('    </Piece>\n')
        f.write('  </UnstructuredGrid>\n')
        f.write('</VTKFile>\n')


def exportar_pvd(combos_dict: dict, caminho_pvd: Path) -> None:
    """Exporta .pvd indexando todos os .vtu por combinação."""
    with open(caminho_pvd, 'w') as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<VTKFile type="Collection" version="0.1">\n')
        f.write('  <Collection>\n')
        for t, (nome, arq) in enumerate(combos_dict.items()):
            f.write(f'    <DataSet timestep="{t}" group="" part="0" '
                    f'file="{arq.name}" name="{nome}"/>\n')
        f.write('  </Collection>\n')
        f.write('</VTKFile>\n')


# ── Pipeline ──────────────────────────────────────────────────────────────────

def gerar_vtk_paraview() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  OpenSeesPy → VTU/PVD para ParaView")
    print("  Pórtico de 3 Rótulas — STOCKI Engenharia Estrutural")
    print("=" * 64)
    print(f"\n  Geometria: L={L}m | H={H_PIL}m | h0={h0}m | "
          f"α={math.degrees(ALPHA):.1f}° | b={B_VIGA}m")
    print(f"  Pórticos: {N_PORTICOS}×Y  ×  {N_PORTICOS_X}×X  "
          f"| {N_V} elem/meia viga | amp×{AMP}\n")

    combos_exportados = {}

    for nome, q in COMBOS.items():
        print(f"  [{nome}] q={q:.4f} kN/m ... ", end="", flush=True)
        res = analisar(q)
        if res is None:
            print("FALHOU"); continue

        f_geo = h_ap - h0
        H_an  = (res['Ry']*(L/2) - q*(L/2)**2/2) / f_geo
        err   = abs(res['H'] - H_an) / H_an * 100
        print(f"Ry={res['Ry']:.2f} H={res['H']:.2f} kN (err={err:.3f}%)")

        arq = OUTPUT_DIR / f"portico_{nome}.vtu"
        exportar_vtu(res, arq)
        combos_exportados[nome] = arq
        print(f"    → {arq.name}  ({arq.stat().st_size/1024:.1f} KB)")

    pvd = OUTPUT_DIR / "portico.pvd"
    exportar_pvd(combos_exportados, pvd)

    print(f"\n  PVD: {pvd}")
    print(f"\n  ── Como abrir no ParaView ────────────────────────")
    print(f"  1. File → Open → portico.pvd → Apply")
    print(f"  2. Slider no topo: navegar entre ELU_C2/ELS_S1/ELS_S3/G_only")
    print(f"  3. Coloring → eta_M  (taxa de utilização)")
    print(f"  4. Filters → Warp By Vector → displacement → Apply")
    print(f"     (deformada amplificada ×{AMP})")
    print("=" * 64)


if __name__ == "__main__":
    gerar_vtk_paraview()