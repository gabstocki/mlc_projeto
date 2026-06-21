"""
opensees/opensees_vtk.py — Análise FEM + exportação VTK/PVD para ParaView.

FLUXO:
    1. OpenSeesPy analisa o pórtico de 3 rótulas (meia estrutura + simetria)
    2. Extrai: deslocamentos, M(x), V(x), N(x), σ(x), η(x) por elemento
    3. Replica a geometria e resultados ao longo dos 9 planos Y (pórticos)
    4. Exporta um .vtk por combinação de carga
    5. Exporta .pvd como índice para navegação temporal no ParaView

ARQUIVOS GERADOS (em output/vtk/):
    portico_ELU_C2.vtk   — ELU combinação governante
    portico_ELS_S1.vtk   — ELS deformações
    portico_ELS_S3.vtk   — ELS permanente (fluência)
    portico_G_only.vtk   — carga permanente isolada
    portico.pvd          — índice PVD para ParaView

CAMPOS VTK:
    Point Data (por nó):
        displacement   — vetor deslocamento [Ux, Uy, 0] (m)
        w_mm           — flecha vertical (mm, positivo = para baixo)

    Cell Data (por elemento):
        M_kNm          — momento fletor médio (kN·m)
        V_kN           — cortante médio (kN)
        N_kN           — força axial (kN, positivo = tração)
        sigma_MPa      — tensão normal máxima (MPa)
        eta_M          — taxa de utilização em flexão (σ/f_m,d)

NOTAS:
    - Eixo de referência: intrados da viga (linha de pressão)
    - 9 pórticos ao longo de Y: y = 0, 5.75, 11.50, ..., 46.00 m
    - Dois pórticos lado a lado: x = 0..20.25 e x = 20.25..40.50 m
    - Pilares: incluídos como elementos de barra verticais
    - Tercas: representadas como elementos entre pórticos
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import NamedTuple

import numpy as np

try:
    import openseespy.opensees as ops
    OPENSEES_OK = True
except ImportError:
    OPENSEES_OK = False
    print("ERRO: openseespy não instalado. Rode: pip install openseespy")

# ── Parâmetros do projeto ─────────────────────────────────────────────────────

L       = 20.25    # m — vão de cada pórtico
H_pil   = 7.0      # m — altura do pilar
h0      = 0.60     # m — altura da seção no apoio
h_ap    = 1.397    # m — altura na cumeeira
alpha   = math.radians(4.5)
b       = 0.26     # m — largura da seção
E       = 11.5e6   # kN/m² — módulo de elasticidade GL24h (E_mean)
f_md    = 17.28    # MPa → kN/m² = 17280 kN/m² — resistência de cálculo

N_PORTICOS  = 9    # pórticos ao longo de Y (módulos + 1)
DIST_MOD    = 5.75 # m — espaçamento entre pórticos
N_PORTICOS_X = 2   # dois pórticos lado a lado (vão total 40.5 m)
N_V         = 40   # elementos por meia viga

OUTPUT_DIR = Path(__file__).parent.parent.parent / "output" / "vtk"

# Combinações de carga
COMBOS = {
    "ELU_C2": 9.6634,
    "ELS_S1": 6.2660,
    "ELS_S3": 4.3125,
    "G_only": 4.3125 * 0.70,   # ~carga permanente
}

AMP_DEFORMADA = 200   # fator de amplificação para visualização


# ── Funções de geometria ──────────────────────────────────────────────────────

def z_intrados(x: float) -> float:
    """Coordenada Z do intrados da viga (linha de pressão)."""
    xs = x if x <= L/2 else L - x
    return H_pil + xs * math.tan(alpha)


def h_em(x: float) -> float:
    """Altura da seção transversal em x."""
    xs = x if x <= L/2 else L - x
    return h0 + xs * math.tan(alpha)


def W_em(x: float) -> float:
    """Módulo de resistência à flexão em x (m³)."""
    hx = h_em(x)
    return b * hx**2 / 6


# ── Análise OpenSees ──────────────────────────────────────────────────────────

class ResultadosFEM(NamedTuple):
    """Resultados de uma análise para uma combinação de carga."""
    nome:     str
    q:        float
    Ry:       float       # kN
    H:        float       # kN
    nos_x:    list        # coordenadas x dos nós (meia viga)
    nos_z:    list        # coordenadas z dos nós (intrados)
    ux:       list        # deslocamento horizontal (m)
    uz:       list        # deslocamento vertical (m, positivo = para cima)
    M_nos:    list        # momento fletor nos nós (kN·m) — via equilíbrio
    V_nos:    list        # cortante nos nós (kN)
    N_nos:    list        # força axial nos nós (kN)
    sigma_nos:list        # tensão normal máxima nos nós (kN/m²)
    eta_nos:  list        # taxa de utilização nos nós


def analisar(nome: str, q: float) -> ResultadosFEM | None:
    """
    Analisa o pórtico de 3 rótulas com OpenSeesPy.

    Modelo de meia estrutura com simetria:
        - Nós no intrados da viga: z(x) = H_pil + x·tan(α)
        - fix(0): Ux=0, Uy=0 (rótula base)
        - fix(L/2): Ux=0 (simetria → equivale à rótula na cumeeira)

    Returns:
        ResultadosFEM com todos os campos para exportação VTK
    """
    if not OPENSEES_OK:
        return None

    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    # Nós
    xnodes = [i * (L/2) / N_V for i in range(N_V + 1)]
    znodes = [z_intrados(x) for x in xnodes]

    for i, (x, z) in enumerate(zip(xnodes, znodes)):
        ops.node(i + 1, x, z)

    # Condições de contorno
    ops.fix(1,        1, 1, 0)   # rótula base
    ops.fix(N_V + 1,  1, 0, 0)   # simetria cumeeira

    # Elementos
    ops.geomTransf('Linear', 1)
    for i in range(N_V):
        xm  = (xnodes[i] + xnodes[i+1]) / 2
        hm  = h_em(xm)
        Am  = b * hm
        Im  = b * hm**3 / 12
        ops.element('elasticBeamColumn', i+1, i+1, i+2, Am, E, Im, 1)

    # Carga
    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    F = q * (L/2) / N_V / 2
    for i in range(N_V):
        ops.load(i + 1, 0, -F, 0)
        ops.load(i + 2, 0, -F, 0)

    # Análise
    ops.system('BandGeneral')
    ops.numberer('RCM')
    ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0)
    ops.algorithm('Linear')
    ops.analysis('Static')
    ok = ops.analyze(1)

    if ok != 0:
        ops.wipe()
        print(f"  AVISO: análise {nome} falhou (code={ok})")
        return None

    # Reações
    ops.reactions()
    Ry = ops.nodeReaction(1, 2)
    H  = ops.nodeReaction(1, 1)

    # Deslocamentos por nó
    ux_half = [ops.nodeDisp(i+1, 1) for i in range(N_V+1)]
    uz_half = [ops.nodeDisp(i+1, 2) for i in range(N_V+1)]

    # Campos por nó via equilíbrio externo
    M_half  = []
    V_half  = []
    N_half  = []
    sig_half= []
    eta_half= []

    for i, x in enumerate(xnodes):
        # Momento fletor (equilíbrio a partir do apoio esquerdo)
        M  = Ry * x - H * x * math.tan(alpha) - q * x**2 / 2
        # Cortante: dM/dx = Ry - H*tan(α) - q*x
        V  = Ry - H * math.tan(alpha) - q * x
        # Força axial: projeção da resultante no eixo da viga
        N  = H * math.cos(alpha) + Ry * math.sin(alpha) - q * x * math.sin(alpha)
        # Tensão normal máxima: σ = M/W + N/A
        hx = h_em(x)
        Wx = b * hx**2 / 6
        Ax = b * hx
        # Em kN/m² → converter para MPa dividindo por 1000
        sig_kNm2 = abs(M) / Wx + abs(N) / Ax
        sig_MPa  = sig_kNm2 / 1e3   # 1 MPa = 1 kN/m² × 10⁻³... não
        # Correto: 1 kN/m² = 0.001 MPa → sig_MPa = sig_kNm2 * 0.001
        sig_MPa  = sig_kNm2 * 1e-3
        eta      = sig_MPa / f_md

        M_half.append(round(M,   4))
        V_half.append(round(V,   4))
        N_half.append(round(N,   4))
        sig_half.append(round(sig_MPa, 4))
        eta_half.append(round(eta,     4))

    ops.wipe()

    # Espelhar para viga completa (0..L/2..L)
    # Meia direita: espelho da meia esquerda
    def espelhar(vals):
        """Espelha lista da meia esquerda para a viga completa."""
        return vals + vals[-2::-1]

    xfull   = xnodes + [L - x for x in xnodes[-2::-1]]
    zfull   = znodes + [z_intrados(x) for x in xnodes[-2::-1]]
    ux_full = espelhar(ux_half)   # Ux simétrico (mesma direção)
    uz_full = espelhar(uz_half)   # Uz simétrico
    M_full  = espelhar(M_half)    # M simétrico
    V_full  = [-v for v in espelhar([-v for v in V_half])]  # V antissimétrico
    N_full  = espelhar(N_half)    # N simétrico
    sig_full= espelhar(sig_half)
    eta_full= espelhar(eta_half)

    return ResultadosFEM(
        nome=nome, q=q, Ry=round(Ry,4), H=round(H,4),
        nos_x=xfull, nos_z=zfull,
        ux=ux_full, uz=uz_full,
        M_nos=M_full, V_nos=V_full, N_nos=N_full,
        sigma_nos=sig_full, eta_nos=eta_full,
    )


# ── Exportação VTK ────────────────────────────────────────────────────────────

def exportar_vtk(res: ResultadosFEM, caminho: Path) -> None:
    """
    Exporta resultados para arquivo .vtk (formato Legacy ASCII).

    Estrutura 3D: replica o pórtico 2D ao longo dos N_PORTICOS planos Y
    para cada um dos N_PORTICOS_X pórticos lado a lado (x=0..L e x=L..2L).

    Elementos: LINE (2 nós) representando barras de viga e pilar.

    Point Data:
        displacement: vetor deslocamento amplificado (para deformada)
        w_mm:         flecha vertical (mm)

    Cell Data:
        M_kNm, V_kN, N_kN, sigma_MPa, eta_M
    """
    n_nos_viga  = len(res.nos_x)           # nós por viga (81 para N_V=40)
    n_elem_viga = n_nos_viga - 1           # elementos por viga (80)

    # ── Construir geometria 3D ────────────────────────────────
    # Nós: [viga + pilares] × N_PORTICOS × N_PORTICOS_X
    # Pilar: 2 nós (base e topo = primeiro nó da viga)
    # Base pilar esq: (0, y, 0)
    # Topo pilar esq: (0, y, H_pil) = primeiro nó da viga esq
    # Base pilar dir: (L, y, 0)
    # Topo pilar dir: (L, y, H_pil) = último nó da viga dir

    all_points = []
    all_disp   = []
    all_w_mm   = []

    # Índices dos nós para construção das células
    # Para cada (ix_portico, iy_portico):
    #   nós viga: base_idx .. base_idx + n_nos_viga - 1
    #   nó base esq: base_idx + n_nos_viga
    #   nó base dir: base_idx + n_nos_viga + 1

    NOS_POR_PORTICO = n_nos_viga + 2   # viga + 2 bases de pilar
    node_offset = {}   # (ix, iy) → índice global do primeiro nó da viga

    for ix in range(N_PORTICOS_X):
        x_offset = ix * L
        for iy in range(N_PORTICOS):
            y = iy * DIST_MOD
            base = len(all_points)
            node_offset[(ix, iy)] = base

            # Nós da viga (intrados)
            for i, (x, z) in enumerate(zip(res.nos_x, res.nos_z)):
                all_points.append([x_offset + x, y, z])
                # Deslocamento: espelhar Ux para pórtico 2 (ix=1)
                ux = res.ux[i] * (-1 if ix == 1 else 1)
                uz = res.uz[i]
                all_disp.append([ux * AMP_DEFORMADA,
                                  0.0,
                                  uz * AMP_DEFORMADA])
                all_w_mm.append(-uz * 1e3)   # positivo = para baixo

            # Nó base pilar esquerdo (x_offset, y, 0)
            all_points.append([x_offset + 0.0, y, 0.0])
            all_disp.append([0.0, 0.0, 0.0])    # base fixa
            all_w_mm.append(0.0)

            # Nó base pilar direito (x_offset + L, y, 0)
            all_points.append([x_offset + L, y, 0.0])
            all_disp.append([0.0, 0.0, 0.0])    # base fixa
            all_w_mm.append(0.0)

    n_points = len(all_points)

    # ── Construir células ─────────────────────────────────────
    all_cells   = []   # [n_pts, i, j, ...]
    all_M       = []
    all_V       = []
    all_N       = []
    all_sigma   = []
    all_eta     = []

    for ix in range(N_PORTICOS_X):
        x_offset = ix * L
        for iy in range(N_PORTICOS):
            base = node_offset[(ix, iy)]

            # Elementos de viga
            for i in range(n_elem_viga):
                ni = base + i
                nj = base + i + 1
                all_cells.append([2, ni, nj])

                # Campos médios por elemento
                M_avg   = (res.M_nos[i]     + res.M_nos[i+1])     / 2
                V_avg   = (res.V_nos[i]     + res.V_nos[i+1])     / 2
                N_avg   = (res.N_nos[i]     + res.N_nos[i+1])     / 2
                sig_avg = (res.sigma_nos[i] + res.sigma_nos[i+1]) / 2
                eta_avg = (res.eta_nos[i]   + res.eta_nos[i+1])   / 2

                all_M.append(M_avg)
                all_V.append(V_avg)
                all_N.append(N_avg)
                all_sigma.append(sig_avg)
                all_eta.append(eta_avg)

            # Pilar esquerdo: base_pilar_esq → topo (nó 0 da viga)
            idx_base_esq = base + n_nos_viga      # base pilar esq
            idx_topo_esq = base + 0               # topo = primeiro nó viga
            all_cells.append([2, idx_base_esq, idx_topo_esq])
            # Campos do pilar: força axial = N no apoio, M=0
            all_M.append(0.0)
            all_V.append(0.0)
            all_N.append(res.N_nos[0])
            all_sigma.append(abs(res.N_nos[0]) / (b * h0) / 1e3)   # MPa
            all_eta.append(abs(res.N_nos[0]) / (b * h0) / 1e3 / f_md)

            # Pilar direito: base_pilar_dir → topo (último nó viga)
            idx_base_dir = base + n_nos_viga + 1  # base pilar dir
            idx_topo_dir = base + n_nos_viga - 1  # topo = último nó viga
            all_cells.append([2, idx_base_dir, idx_topo_dir])
            all_M.append(0.0)
            all_V.append(0.0)
            all_N.append(res.N_nos[-1])
            all_sigma.append(abs(res.N_nos[-1]) / (b * h0) / 1e3)
            all_eta.append(abs(res.N_nos[-1]) / (b * h0) / 1e3 / f_md)

    n_cells = len(all_cells)

    # ── Escrever arquivo VTK (Legacy ASCII) ──────────────────
    with open(caminho, 'w') as f:
        # Cabeçalho
        f.write("# vtk DataFile Version 3.0\n")
        f.write(f"Portico 3 Rotulas — {res.nome} q={res.q:.4f} kN/m "
                f"| Rv={res.Ry:.2f} kN H={res.H:.2f} kN\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n\n")

        # Pontos
        f.write(f"POINTS {n_points} float\n")
        for pt in all_points:
            f.write(f"{pt[0]:.6f} {pt[1]:.6f} {pt[2]:.6f}\n")

        # Células
        n_int = sum(len(c) for c in all_cells)
        f.write(f"\nCELLS {n_cells} {n_int}\n")
        for cell in all_cells:
            f.write(" ".join(str(v) for v in cell) + "\n")

        # Tipos de células (3 = VTK_LINE)
        f.write(f"\nCELL_TYPES {n_cells}\n")
        for _ in all_cells:
            f.write("3\n")

        # ── Point Data ────────────────────────────────────────
        f.write(f"\nPOINT_DATA {n_points}\n")

        # Vetor deslocamento (amplificado)
        f.write("VECTORS displacement float\n")
        for d in all_disp:
            f.write(f"{d[0]:.6f} {d[1]:.6f} {d[2]:.6f}\n")

        # Flecha escalar
        f.write("\nSCALARS w_mm float 1\n")
        f.write("LOOKUP_TABLE default\n")
        for w in all_w_mm:
            f.write(f"{w:.4f}\n")

        # ── Cell Data ─────────────────────────────────────────
        f.write(f"\nCELL_DATA {n_cells}\n")

        for nome_campo, vals in [
            ("M_kNm",     all_M),
            ("V_kN",      all_V),
            ("N_kN",      all_N),
            ("sigma_MPa", all_sigma),
            ("eta_M",     all_eta),
        ]:
            f.write(f"SCALARS {nome_campo} float 1\n")
            f.write("LOOKUP_TABLE default\n")
            for v in vals:
                f.write(f"{v:.6f}\n")
            f.write("\n")


def exportar_pvd(combos_exportados: dict, caminho_pvd: Path) -> None:
    """
    Exporta arquivo .pvd — índice de coleção para ParaView.

    Cada combinação de carga é um 'timestep' no PVD.
    No ParaView: abrir o .pvd e usar o slider para navegar entre combinações.
    """
    with open(caminho_pvd, 'w') as f:
        f.write('<?xml version="1.0"?>\n')
        f.write('<VTKFile type="Collection" version="0.1">\n')
        f.write('  <Collection>\n')
        for t, (nome, arquivo) in enumerate(combos_exportados.items()):
            nome_arquivo = arquivo.name
            f.write(f'    <DataSet timestep="{t}" group="" part="0" '
                    f'file="{nome_arquivo}" name="{nome}"/>\n')
        f.write('  </Collection>\n')
        f.write('</VTKFile>\n')


# ── Pipeline principal ────────────────────────────────────────────────────────

def gerar_vtk_paraview() -> None:
    """
    Pipeline completo: análise FEM → exportação VTK/PVD.

    Executa todas as combinações de carga, exporta um .vtk por combinação
    e um .pvd como índice para ParaView.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 64)
    print("  OpenSeesPy → VTK/PVD para ParaView")
    print("  Pórtico de 3 Rótulas — STOCKI Engenharia Estrutural")
    print("=" * 64)
    print(f"\n  Geometria: L={L}m | H_pil={H_pil}m | h0={h0}m | "
          f"α={math.degrees(alpha):.1f}° | b={b}m")
    print(f"  Pórticos: {N_PORTICOS} ao longo Y × {N_PORTICOS_X} lado a lado")
    print(f"  Elementos por meia viga: {N_V}")
    print(f"  Saída: {OUTPUT_DIR}/\n")

    combos_exportados = {}

    for nome, q in COMBOS.items():
        print(f"  [{nome}] q={q:.4f} kN/m ... ", end="", flush=True)

        res = analisar(nome, q)
        if res is None:
            print("FALHOU")
            continue

        # Verificação rápida analítica
        f_geo = h_ap - h0
        Rv_an = q * L / 2
        H_an  = (Rv_an*(L/2) - q*(L/2)**2/2) / f_geo
        err_H = abs(res.H - H_an) / H_an * 100

        print(f"Ry={res.Ry:.2f} H={res.H:.2f} kN "
              f"(err_H={err_H:.3f}%)")

        caminho_vtk = OUTPUT_DIR / f"portico_{nome}.vtk"
        exportar_vtk(res, caminho_vtk)
        combos_exportados[nome] = caminho_vtk

        print(f"    → {caminho_vtk.name} "
              f"({caminho_vtk.stat().st_size / 1024:.1f} KB)")

    # Exportar PVD
    caminho_pvd = OUTPUT_DIR / "portico.pvd"
    exportar_pvd(combos_exportados, caminho_pvd)
    print(f"\n  PVD: {caminho_pvd}")

    print(f"\n  Abrir no ParaView:")
    print(f"    File → Open → {caminho_pvd}")
    print(f"    Apply → usar slider para navegar entre combinações")
    print(f"\n  Campos disponíveis (Cell Data):")
    print(f"    eta_M    — taxa de utilização em flexão")
    print(f"    M_kNm    — momento fletor (kN·m)")
    print(f"    sigma_MPa — tensão normal (MPa)")
    print(f"    N_kN     — força axial (kN)")
    print(f"    V_kN     — cortante (kN)")
    print(f"\n  Point Data:")
    print(f"    displacement — vetor deslocamento amplificado ×{AMP_DEFORMADA}")
    print(f"    w_mm         — flecha vertical (mm)")
    print("=" * 64)


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    gerar_vtk_paraview()
