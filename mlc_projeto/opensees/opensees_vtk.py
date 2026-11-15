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
#
# Os parâmetros NÃO são fixados aqui: derivam de `mlc_projeto.main`, que é a
# fonte única da geometria e das cargas do projeto. Antes desta alteração o
# módulo carregava uma cópia manual (h0=0,60 m, α=4,5°, pilar 0,20×0,20 m) que
# divergira da geometria adotada, e os .vtk em output/vtk/ representavam uma
# estrutura que o projeto já havia descartado. Importando de `main`, qualquer
# mudança de geometria propaga-se para cá.

from mlc_projeto.main import (                                    # noqa: E402
    GEO_PARAMS, MAT_CURTA,
    B_PILAR, H_PILAR, H_PILAR_ALT,
    B_TERCA, H_TERCA, S, L_T as L_TERCA,
    L_COMP_GALPAO, Q_AREA, G_TELHA_KNM2, G_INSTALACOES_KNM2,
    EMPUXO_DESENVOLVE, A_BEIRAL_M, B_LAMINA, H_LAMINA, N_PAINEIS_CV_VERT,
    N_PAINEIS_CV_CENTRAL,
)
from mlc_projeto.checks.elu.pilar_bipartido import geometria as _geo_bip  # noqa: E402
from mlc_projeto.core.geometry import GeometriaViga               # noqa: E402
from mlc_projeto.core.materials import GlulamMaterial             # noqa: E402

_geo = GeometriaViga(**GEO_PARAMS)
# Duração «média»: a combinação que governa o momento é 1,35G + 1,5Q
# (categoria H, sem vento concomitante) — ver capítulo de modelagem.
_mat = GlulamMaterial(**{**MAT_CURTA, "duracao": "media"})

L        = _geo.L
H_PIL    = H_PILAR_ALT
h0       = _geo.h0
h_ap     = _geo.h_ap
ALPHA    = _geo.alpha_rad
B_V      = _geo.b
B_PIL     = B_PILAR      # largura do pilar (paralela à largura da viga)
H_PIL_SEC = H_PILAR      # profundidade do pilar no plano do pórtico
E        = _mat.E0_mean / 1e6          # MPa → kN/m² na convenção do módulo
F_MD     = _mat.f_m_d / 1e6            # MPa
N_V      = 40

B_T      = B_TERCA
H_T      = H_TERCA
S_TERCA  = S
L_T      = L_TERCA
N_T      = 20

DIST_MOD = L_TERCA
N_PORT   = round(L_COMP_GALPAO / DIST_MOD) + 1
N_X      = 2                            # dois vãos por pórtico

UP = np.array([0.0, 0.0, 1.0])

# Cargas lineares sobre a viga (kN/m), na área tributária de um pórtico
# intermediário. ψ₂ da sobrecarga é nulo na categoria H, pelo que a combinação
# quase permanente coincide com a ação permanente isolada.
def _cargas_lineares() -> dict[str, float]:
    from mlc_projeto.core.loads import peso_proprio_gk
    pp = peso_proprio_gk(
        geo=_geo, mat=_mat, L_t=L_TERCA,
        b_terca=B_TERCA, h_terca=H_TERCA, s_terca=S,
        g_telha_kNm2=G_TELHA_KNM2, g_instalacoes_kNm2=G_INSTALACOES_KNM2,
    )
    g = pp["g_k_viga_kNm2"] * L_TERCA
    q = Q_AREA * L_TERCA
    # (carga média, fator de G): o fator multiplica a correção do peso próprio
    # variável da viga (issue 114), aplicada elemento a elemento
    return {
        "ELU_C2": (1.35 * g + 1.50 * q, 1.35),   # ELU governante
        "ELS_S1": (g + q, 1.0),                  # combinação característica
        "ELS_S3": (g, 1.0),                      # quase permanente (ψ₂ = 0)
        "G_only": (g, 1.0),                      # ação permanente isolada
    }


COMBOS = _cargas_lineares()

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


def _esforcos_fem(rv: dict, x: float) -> tuple[float, float, float]:
    """M, V, N do modelo OpenSees na abscissa x (simetria: V antissimétrico)."""
    xs = x if x <= L/2 else L - x
    s = 1.0 if x <= L/2 else -1.0
    M = float(np.interp(xs, rv["xm"], rv["M_el"]))
    V = float(np.interp(xs, rv["xm"], rv["V_el"]))
    N = float(np.interp(xs, rv["xm"], rv["N_el"]))
    return M, s * V, N


# ── Análise OpenSeesPy — Viga ─────────────────────────────────────────────────

def analisar_viga(q: float, fG: float = 0.0) -> dict:
    """
    Meia viga com simetria. A carga é a média q mais a correção do peso próprio
    variável, fG·γ·b·(h(x) − h̄), elemento a elemento (issue 114). Devolve também
    M, V e N dos próprios elementos (localForce), que colorem a malha 3D e aferem o
    integrador do pipeline de forma independente.
    """
    ops.wipe()
    ops.model('basic', '-ndm', 2, '-ndf', 3)

    xn = [i*(L/2)/N_V for i in range(N_V+1)]
    for i, x in enumerate(xn):
        ops.node(i+1, x, z_centro(x))        # eixo no centroide (intr. horizontal)

    # Condição de contorno horizontal no apoio: segue a mesma decisão de modelo
    # do pipeline (main.EMPUXO_DESENVOLVE). Na Opção B adotada o pilar
    # biarticulado não restringe o afastamento, o grau de liberdade horizontal
    # fica livre e nenhum empuxo se desenvolve; a viga trabalha como biapoiada.
    # Prender esse grau de liberdade produziria o modelo de arco, que a análise
    # de rigidez relativa refutou.
    _fix_x = 1 if EMPUXO_DESENVOLVE else 0
    ops.fix(1,      _fix_x, 1, 0)             # rótula do apoio (Rz livre)
    ops.fix(N_V+1,  1, 0, 1)                  # SIMETRIA de peça contínua: Rz FIXO

    ops.geomTransf('Linear', 1)
    for i in range(N_V):
        xm = (xn[i]+xn[i+1])/2
        hm = h_secao(xm)
        ops.element('elasticBeamColumn', i+1, i+1, i+2,
                    B_V*hm, E, B_V*hm**3/12, 1)

    ops.timeSeries('Linear', 1)
    ops.pattern('Plain', 1, 1)
    gamma = _mat.rho_mean * 9.81 / 1000.0                     # kN/m³
    xs_m = [(xn[i] + xn[i+1]) / 2 for i in range(N_V)]
    h_med = sum(h_secao(x) for x in xs_m) / N_V
    dx = (L/2) / N_V
    for i in range(N_V):
        qi = q + fG * gamma * B_V * (h_secao(xs_m[i]) - h_med)
        F = qi * dx / 2
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
    Mel, Vel, Nel = [], [], []
    for i in range(N_V):
        N1, V1, M1, N2, V2, M2 = ops.eleResponse(i+1, 'localForce')
        Mel.append((-M1 + M2) / 2.0)      # momento no meio do elemento (tração embaixo +)
        Vel.append((V1 - V2) / 2.0)
        Nel.append((-N1 + N2) / 2.0 * -1.0)   # compressão +
    ops.wipe()

    xfull = xn + [L-x for x in xn[-2::-1]]
    return dict(
        Ry=Ry, H=H, xfull=xfull, xm=xs_m, M_el=Mel, V_el=Vel, N_el=Nel,
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
                Mx, Vx, Nx = _esforcos_fem(rv, xm)
                hx = h_secao(xm)
                sm = (abs(Mx)/(B_V*hx**2/6) + abs(Nx)/(B_V*hx)) * 1e-3
                add_hex([x_off+xi,y,z_intrados(xi)],
                        [x_off+xj,y,z_intrados(xj)],
                        B_V, h_secao(xi), h_secao(xj),
                        Mx, Vx, Nx, sm, sm/F_MD)

    # Beirais (A e C): a viga continua em balanço além do pilar, com a altura
    # decrescendo com a inclinação do extradorso; momento de balanço −q·d²/2.
    a_b = A_BEIRAL_M + H_PIL_SEC / 2.0
    nb = 6
    for x_ap, sg in ((0.0, -1.0), (N_X * L, 1.0)):
        for i in range(nb):
            d0, d1 = a_b * i / nb, a_b * (i + 1) / nb
            hi, hj = h0 - d0 * math.tan(ALPHA), h0 - d1 * math.tan(ALPHA)
            dm = (d0 + d1) / 2
            Mb = -q * (a_b - dm) ** 2 / 2.0
            W = B_V * ((hi + hj) / 2) ** 2 / 6.0
            sb = abs(Mb) / W * 1e-3
            for iy in range(N_PORT):
                y = iy * DIST_MOD
                add_hex([x_ap + sg * d0, y, H_PIL + hi / 2], [x_ap + sg * d1, y, H_PIL + hj / 2],
                        B_V, hi, hj, Mb, q * (a_b - dm), 0.0, sb, sb / F_MD)

    # Pilares montantes das baías contraventadas: bipartidos (duas lâminas dos
    # lados da viga, até a escora); demais pilares maciços.
    gb = _geo_bip(B_V, B_LAMINA, H_LAMINA)
    y_l = gb["y_l_mm"] / 1000.0
    baias_f = (1, N_PORT - 1)
    baias_c = (1, 2, N_PORT - 2, N_PORT - 1)
    mont_f = {e for b in baias_f for e in (b, b + 1)}
    mont_c = {e for b in baias_c for e in (b, b + 1)}

    def _montante(x_pil, eixo):
        central = 0.0 < x_pil < N_X * L
        return eixo in (mont_c if central else mont_f)

    # Pilares — uma peça por posição. O laço anterior percorria os dois vãos e
    # criava DUAS células coincidentes no apoio partilhado (x = L): além de
    # inflar a malha, os hexaedros sobrepostos anulavam-se na renderização e o
    # pilar central desaparecia das figuras. As posições são desduplicadas.
    x_pilares = sorted({ix*L + xp for ix in range(N_X) for xp in (0.0, L)})
    for x_pil in x_pilares:
        # O pilar central recebe a reação dos dois vãos; os de extremidade, de um.
        n_vaos = 2 if 0.0 < x_pil < N_X*L else 1
        Np = n_vaos * abs(Ry)
        sp = Np / (B_PIL*H_PIL_SEC) * 1e-3
        for iy in range(N_PORT):
            y = iy*DIST_MOD
            if _montante(x_pil, iy + 1):
                sl = Np / 2 / (B_LAMINA * H_LAMINA) * 1e-3
                for sg in (-1.0, 1.0):
                    add_hex([x_pil, y + sg * y_l, 0.0], [x_pil, y + sg * y_l, H_PIL + h0],
                            B_LAMINA, H_LAMINA, H_LAMINA, 0.0, abs(H), Np / 2, sl, sl / F_MD,
                            up=up_pil)
            else:
                add_hex([x_pil, y, 0.0],
                        [x_pil, y, H_PIL],
                        B_PIL, H_PIL_SEC, H_PIL_SEC,
                        0.0, abs(H), Np, sp, sp/F_MD, up=up_pil)
    # Pilares de frontão (PF1 no eixo 1, junto a A; PF2 no eixo 9, junto a C)
    for x_pf, y_pf in ((L_TERCA, 0.0), (N_X * L - L_TERCA, (N_PORT - 1) * DIST_MOD)):
        add_hex([x_pf, y_pf, 0.0], [x_pf, y_pf, H_PIL], B_PIL, H_PIL_SEC, H_PIL_SEC,
                0.0, 0.0, 0.0, 0.0, 0.0, up=up_pil)

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
    print(f"  Pilar: {B_PIL}x{H_PIL_SEC}m  |  Terca: {B_T}x{H_T}m")
    print(f"  Porticos: {N_PORT}xY x {N_X}xX  |  "
          f"Tercas: {len(posicoes_tercas())} por modulo")
    print(f"  Saida: {OUTPUT_DIR}\n")

    for nome, (q, fG) in COMBOS.items():
        print(f"  [{nome}] q={q:.4f} kN/m ... ", end="", flush=True)

        rv = analisar_viga(q, fG)
        rt = analisar_terca((q/L_T)*S_TERCA)
        malha = construir_malha(rv, rt, q)

        arq = OUTPUT_DIR / f"portico_{nome}.vtk"
        malha.save(str(arq))

        # Aferição do FEM contra a solução analítica do MESMO modelo de apoio.
        # Comparar com o empuxo do arco quando se roda a Opção B (H≡0) produziria
        # sempre 100% de erro, o que não afere coisa nenhuma.
        from mlc_projeto.core.loads import analisar_biarticulada
        ref = analisar_biarticulada(q, L, h0, h_ap, ALPHA, B_V,
                                    desenvolve_empuxo=EMPUXO_DESENVOLVE,
                                    g_var_kNm3=fG * _mat.rho_mean * 9.81 / 1000.0)
        M_fem = max(abs(m) for m in rv["M_el"])
        print(f"M_FEM={M_fem:.1f} × M_integrador={abs(ref['M_cumeeira_kNm']):.1f} kN·m | ",
              end="")
        if EMPUXO_DESENVOLVE:
            grandeza, obtido, esperado = "H", rv["H"], ref["H_kN"]
        else:
            grandeza, obtido, esperado = "Rv", abs(rv["Ry"]), q * L / 2
        err   = abs(abs(obtido) - esperado) / esperado * 100 if esperado else 0.0
        eta_m = float(np.max(np.abs(malha.cell_data['eta_M'])))

        print(f"OK | Ry={rv['Ry']:.2f} H={rv['H']:.2f} kN "
              f"err({grandeza})={err:.3f}% | {malha.n_cells} hex | "
              f"eta_max={eta_m:.4f} | {arq.stat().st_size//1024} KB")

    print(f"\n  ParaView: File -> Open -> portico_ELU_C2.vtk -> Apply -> R")
    print(f"  Coloring -> eta_M / M_kNm / sigma_MPa")
    print("=" * 64)


if __name__ == "__main__":
    gerar_vtk()