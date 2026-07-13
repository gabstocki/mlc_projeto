"""
visualization/viz_3d.py — Visualização 3D estilo SAP2000. v4

ATUALIZAÇÃO v4 — Sistema biarticulado (alinhado ao modelo de cálculo):
    - Viga MLC monolítica de duplo-bisel — continuidade na cumeeira
    - Sem rótula na cumeeira (as águas não se articulam ao centro)
    - Rótulas apenas nos apoios (base e topo do pilar / ligação viga–pilar)

v3 — Dois pórticos lado a lado (vão total 40,5 m):
    - 2 pórticos × 20,25 m = 40,50 m
    - Pilar central compartilhado 0,26×0,26 m (N = 2×R_v)
    - Pilares laterais 0,20×0,20 m
    - Empuxos horizontais se cancelam no pilar central
    - 8 módulos × 5,75 m = 46 m de comprimento

Representação estilo SAP2000:
    Seções transversais reais extrudadas ao longo do eixo.
    Coloração por η de cada tipo de elemento.
"""

from __future__ import annotations
import math
import numpy as np

try:
    import pyvista as pv
    PYVISTA_OK = True
except ImportError:
    PYVISTA_OK = False

from mlc_projeto.core.geometry import GeometriaViga


# ── Escala de cores ───────────────────────────────────────────────────────────

def eta_cor(eta: float) -> tuple:
    if eta < 0.50:  return (0.18, 0.62, 0.18)
    if eta < 0.80:  return (0.95, 0.78, 0.05)
    if eta < 0.95:  return (0.92, 0.42, 0.07)
    return              (0.82, 0.07, 0.07)


# ── Primitivas geométricas ────────────────────────────────────────────────────

def _prisma_segmento(
    p0: np.ndarray, p1: np.ndarray,
    b0: float, h0: float,
    b1: float, h1: float,
    up: np.ndarray = None,
) -> pv.PolyData:
    """Prisma hexaédrico entre p0 e p1 com seção b×h."""
    vec = p1 - p0
    L   = np.linalg.norm(vec)
    if L < 1e-9:
        return None

    ex = vec / L
    if up is None:
        up = np.array([0.0, 0.0, 1.0])

    ez = up - np.dot(up, ex) * ex
    if np.linalg.norm(ez) < 1e-9:
        ez = np.array([0.0, 1.0, 0.0])
    ez = ez / np.linalg.norm(ez)
    ey = np.cross(ez, ex)
    ey = ey / np.linalg.norm(ey)

    def secao(pt, b, h):
        hb, hh = b/2, h/2
        return np.array([
            pt - hb*ey - hh*ez,
            pt + hb*ey - hh*ez,
            pt + hb*ey + hh*ez,
            pt - hb*ey + hh*ez,
        ])

    s0 = secao(p0, b0, h0)
    s1 = secao(p1, b1, h1)
    pts = np.vstack([s0, s1])

    faces = np.array([
        [4, 0,1,2,3], [4, 4,5,6,7],
        [4, 0,1,5,4], [4, 2,3,7,6],
        [4, 0,3,7,4], [4, 1,2,6,5],
    ]).ravel()

    return pv.PolyData(pts, faces)


def _viga_sap(x0, y0, z_base, L, h0, h_ap, alpha_rad, b, n_seg=24):
    """Viga duplo-bisel com seção b×h(x) variável."""
    x_pts = np.linspace(0, L, n_seg + 1)
    x_sim = np.where(x_pts <= L/2, x_pts, L - x_pts)
    h_pts = h0 + x_sim * math.tan(alpha_rad)

    pts_eixo = np.column_stack([
        x0 + x_pts,
        np.full(n_seg + 1, y0),
        z_base + h_pts / 2,
    ])

    meshes = []
    for i in range(n_seg):
        seg = _prisma_segmento(
            pts_eixo[i], pts_eixo[i+1],
            b0=b, h0=h_pts[i],
            b1=b, h1=h_pts[i+1],
            up=np.array([0.0, 0.0, 1.0]),
        )
        if seg:
            meshes.append(seg)

    if not meshes:
        return pv.PolyData()
    combined = meshes[0]
    for m in meshes[1:]:
        combined = combined.merge(m)
    return combined


def _pilar_sap(x, y, H, b, h):
    """Pilar retangular b×h altura H."""
    return _prisma_segmento(
        np.array([x, y, 0.0]),
        np.array([x, y, H]),
        b0=b, h0=h, b1=b, h1=h,
        up=np.array([1.0, 0.0, 0.0]),
    )


def _terca_sap(x_t, y0, y1, z, b, h):
    """Terça retangular entre dois pórticos."""
    return _prisma_segmento(
        np.array([x_t, y0, z]),
        np.array([x_t, y1, z]),
        b0=b, h0=h, b1=b, h1=h,
        up=np.array([0.0, 0.0, 1.0]),
    )


def _rotula(cx, cy, cz, raio=0.07):
    return pv.Sphere(radius=raio, center=(cx, cy, cz),
                     theta_resolution=12, phi_resolution=12)



# ── Cruzes de St. André ───────────────────────────────────────────────────────

def _cruz_sap(p0, p1, raio=0.08):
    """Barra de contraventamento entre dois pontos."""
    linha = pv.Line(p0, p1)
    return linha.tube(radius=raio, n_sides=8)


def _cruzes_modulo(x_offset, y0, y1, L, h0, alpha_rad, H_pilar, s_terca, raio=0.08):
    """
    Gera as cruzes de St. André para um módulo de contraventamento.
    Dois painéis por água (junto aos apoios em x=0 e x=L).
    """
    def z(x_loc):
        xs = x_loc if x_loc <= L/2 else L - x_loc
        return H_pilar + h0 + xs * math.tan(alpha_rad)

    meshes = []
    for x_a_loc, x_b_loc in [(0.0, s_terca), (L - s_terca, L)]:
        x_a = x_offset + x_a_loc
        x_b = x_offset + x_b_loc
        z_a = z(x_a_loc)
        z_b = z(x_b_loc)
        # Diagonal 1
        m1 = _cruz_sap(np.array([x_a, y0, z_a]), np.array([x_b, y1, z_b]), raio)
        if m1: meshes.append(m1)
        # Diagonal 2
        m2 = _cruz_sap(np.array([x_b, y0, z_b]), np.array([x_a, y1, z_a]), raio)
        if m2: meshes.append(m2)
    return meshes


# ── Visualização principal ────────────────────────────────────────────────────

def visualizar_galpao(
    geo:          GeometriaViga,
    resultados:   dict,
    H_pilar:      float = 7.0,
    n_modulos:    int   = 8,
    dist_mod:     float = 5.75,
    b_pilar:      float = 0.20,
    h_pilar:      float = 0.20,
    b_pilar_c:    float = 0.26,
    h_pilar_c:    float = 0.26,
    b_terca:      float = 0.20,
    h_terca:      float = 0.58,
    salvar_imagem: str | None = None,
) -> None:
    """
    Visualização 3D estilo SAP2000 — dois pórticos lado a lado.

    Viga biarticulada monolítica: rótulas só nos apoios (sem rótula na cumeeira).
    Pilar central compartilhado recebe carga dos dois pórticos.
    Empuxos horizontais se cancelam no pilar central.
    """
    if not PYVISTA_OK:
        print("PyVista não instalado. Rode: pip install pyvista")
        return

    # ── η por elemento ────────────────────────────────────────
    eta_viga = max(
        resultados.get("apoio",       {}).get("eta", 0.0),
        resultados.get("cisalhamento",{}).get("eta", 0.0),
        resultados.get("flexao",      {}).get("eta", 0.0),
        resultados.get("flambagem",   {}).get("eta", 0.0),
    )
    eta_pilar_lat = (resultados.get("flexo_comp", {})
                               .get("pilar", {}).get("eta", 0.0)
                    or resultados.get("flexo_comp", {}).get("eta", 0.0))
    eta_pilar_cen = resultados.get("pilar_central", {}).get("eta", 0.0)
    eta_terca     = resultados.get("terca", {}).get("eta", 0.0)

    cor_viga      = eta_cor(eta_viga)
    cor_pilar_lat = eta_cor(eta_pilar_lat)
    cor_pilar_cen = eta_cor(eta_pilar_cen)
    cor_terca     = eta_cor(eta_terca)
    eta_cv        = resultados.get('contraventamento', {}).get('eta', 0.0)
    cor_cv        = (0.80, 0.35, 0.05)   # laranja aço — contraste com madeira
    cor_rot       = (0.15, 0.35, 0.85)

    L      = geo.L          # vão de cada pórtico = 20,25 m
    h0     = geo.h0
    h_ap   = geo.h_ap
    alpha  = geo.alpha_rad
    b_viga = geo.b
    comp   = n_modulos * dist_mod

    # Dois pórticos: x de 0 a L e de L a 2L
    # Pilar central em x = L
    L_total = 2 * L

    y_pos = [i * dist_mod for i in range(n_modulos + 1)]

    plotter = pv.Plotter(window_size=[1500, 860])
    plotter.set_background("white")
    plotter.add_axes(
        xlabel="X (vão)", ylabel="Y (compr.)", zlabel="Z (alt.)",
        line_width=2,
    )

    # ── Vigas — dois pórticos ─────────────────────────────────
    for y in y_pos:
        # Pórtico 1: x=0 → x=L
        m1 = _viga_sap(0, y, H_pilar, L, h0, h_ap, alpha, b_viga)
        plotter.add_mesh(m1, color=cor_viga, smooth_shading=True,
                         show_edges=False,
                         label=f"Viga GL24h  η={eta_viga:.3f}"
                               if y == y_pos[0] else "")

        # Pórtico 2: x=L → x=2L (espelhado)
        m2 = _viga_sap(L, y, H_pilar, L, h0, h_ap, alpha, b_viga)
        plotter.add_mesh(m2, color=cor_viga, smooth_shading=True,
                         show_edges=False)
        # Cumeeira: continuidade da viga monolítica — sem rótula

    # ── Pilares laterais esquerdo (x=0) e direito (x=2L) ─────
    # Rótulas nos apoios (base e topo = ligação viga–pilar)
    for y in y_pos:
        for x_p, label_flag in [(0.0, True), (L_total, False)]:
            m = _pilar_sap(x_p, y, H_pilar, b_pilar, h_pilar)
            if m:
                plotter.add_mesh(
                    m, color=cor_pilar_lat, smooth_shading=True,
                    show_edges=False,
                    label=f"Pilar lateral  η={eta_pilar_lat:.3f}"
                          if (y == y_pos[0] and label_flag) else "",
                )
            plotter.add_mesh(
                _rotula(x_p, y, 0.0), color=cor_rot,
                label="Rótulas (apoios)" if (y == y_pos[0] and label_flag) else "",
            )
            plotter.add_mesh(_rotula(x_p, y, H_pilar), color=cor_rot)

    # ── Pilar central compartilhado (x=L) ────────────────────
    for y in y_pos:
        m = _pilar_sap(L, y, H_pilar, b_pilar_c, h_pilar_c)
        if m:
            plotter.add_mesh(
                m, color=cor_pilar_cen, smooth_shading=True,
                show_edges=False,
                label=f"Pilar central {b_pilar_c}×{h_pilar_c}m  "
                      f"η={eta_pilar_cen:.3f}"
                      if y == y_pos[0] else "",
            )
        plotter.add_mesh(_rotula(L, y, 0.0),     color=cor_rot)
        plotter.add_mesh(_rotula(L, y, H_pilar), color=cor_rot)

    # ── Terças ────────────────────────────────────────────────
    s_terca  = 2.53
    n_half   = round((L/2) / s_terca)
    x_half   = np.array([i * (L/2) / n_half for i in range(n_half + 1)])
    # Posições para cada pórtico
    x_t_p1   = np.unique(np.concatenate([x_half, L - x_half]))
    x_t_p2   = x_t_p1 + L

    for i in range(len(y_pos) - 1):
        y0_t, y1_t = y_pos[i], y_pos[i+1]
        primeiro = True
        for x_t in np.concatenate([x_t_p1, x_t_p2]):
            # altura da terça: relativa ao pórtico correspondente
            if x_t <= L:
                xs = x_t if x_t <= L/2 else L - x_t
            else:
                xs = (x_t - L) if (x_t - L) <= L/2 else L - (x_t - L)
            z_t = H_pilar + h0 + xs * math.tan(alpha)
            m = _terca_sap(x_t, y0_t, y1_t, z_t, b_terca, h_terca)
            if m:
                plotter.add_mesh(
                    m, color=cor_terca, smooth_shading=True,
                    show_edges=False,
                    label=f"Terça GL24h  η={eta_terca:.3f}"
                          if (i == 0 and primeiro) else "",
                )
                primeiro = False


    # ── Contraventamento horizontal (módulos extremos) ────────
    # Cruzes de St. André — aço S235 d=12mm — 2 módulos extremos
    brace_modules = [(y_pos[0], y_pos[1]), (y_pos[-2], y_pos[-1])]
    first_cv = True
    for x_off in [0, L]:
        for (yb0, yb1) in brace_modules:
            for m in _cruzes_modulo(
                x_offset=x_off, y0=yb0, y1=yb1,
                L=L, h0=h0, alpha_rad=alpha,
                H_pilar=H_pilar, s_terca=2.53,
                raio=0.09,
            ):
                plotter.add_mesh(
                    m, color=cor_cv,
                    smooth_shading=True, show_edges=False,
                    label=f"Contravent. S235  η={eta_cv:.3f}" if first_cv else "",
                )
                first_cv = False

    # ── Cobertura translúcida ─────────────────────────────────
    for x_offset in [0, L]:
        n_x, n_y = 40, 16
        xv = np.linspace(x_offset, x_offset + L, n_x)
        yv = np.linspace(0, comp, n_y)
        XX, YY = np.meshgrid(xv, yv)
        x_rel = XX - x_offset
        x_sim = np.where(x_rel <= L/2, x_rel, L - x_rel)
        ZZ    = H_pilar + h0 + x_sim * math.tan(alpha)
        sup   = pv.StructuredGrid(XX, YY, ZZ)
        plotter.add_mesh(sup, color=(0.65, 0.82, 0.93),
                         opacity=0.20, show_edges=False,
                         label="Cobertura" if x_offset == 0 else "")

    # ── Piso ──────────────────────────────────────────────────
    piso = pv.Plane(
        center=(L_total/2, comp/2, -0.05),
        direction=(0, 0, 1),
        i_size=L_total + 4, j_size=comp + 4,
    )
    plotter.add_mesh(piso, color=(0.88, 0.88, 0.88), opacity=0.6)

    # ── Legenda ───────────────────────────────────────────────
    legenda = [
        [f"Viga           η={eta_viga:.3f}",      cor_viga],
        [f"Pilar lateral  η={eta_pilar_lat:.3f}",  cor_pilar_lat],
        [f"Pilar central  η={eta_pilar_cen:.3f}",  cor_pilar_cen],
        [f"Terça          η={eta_terca:.3f}",      cor_terca],
        [f"Contravent.    η={eta_cv:.3f}",         cor_cv],
        ["η < 0,50  Confortável",   (0.18, 0.62, 0.18)],
        ["η 0,50–0,80  Atenção",    (0.95, 0.78, 0.05)],
        ["η 0,80–0,95  Próx. lim.", (0.92, 0.42, 0.07)],
        ["η ≥ 0,95  Crítico",       (0.82, 0.07, 0.07)],
        ["Rótulas (apoios)",         cor_rot],
    ]
    plotter.add_legend(
        legenda, bcolor=(0.97, 0.97, 0.97),
        border=True, size=(0.26, 0.24),
    )

    # ── Informações ───────────────────────────────────────────
    eta_max = max(eta_viga, eta_pilar_lat, eta_pilar_cen, eta_terca)
    info = (
        f"STOCKI Engenharia Estrutural\n"
        f"Galpão MLC GL24h — Viga biarticulada (2 pórticos)\n"
        f"Sem rótula na cumeeira | Continuidade MLC monolítica\n"
        f"Vão total={L_total}m ({L}+{L}m) | h0={h0}m | α={geo.alpha_deg}°\n"
        f"Pilar lateral {b_pilar}×{h_pilar}m | "
        f"Pilar central {b_pilar_c}×{h_pilar_c}m | "
        f"Contravent. d=12mm S235\n"
        f"η máximo = {eta_max:.4f}"
    )
    plotter.add_text(info, position="upper_left", font_size=9, color="black")

    # ── Câmera ────────────────────────────────────────────────
    plotter.camera_position = [
        ( L_total * 0.90,  -comp * 0.70,  H_pilar * 3.0),
        ( L_total / 2,      comp * 0.15,  (H_pilar + h_ap) / 2),
        (0, 0, 1),
    ]

    if salvar_imagem:
        plotter.show(auto_close=False)
        plotter.screenshot(salvar_imagem)
        plotter.close()
        print(f"  Imagem 3D salva: {salvar_imagem}")
    else:
        plotter.show(
            title="Galpão MLC — Viga biarticulada | Vão total 40,5m"
        )


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento, calcular_vento
    from mlc_projeto.core.loads     import carregamentos_com_vento
    from mlc_projeto.checks.elu.cumeeira          import verifica_cumeeira
    from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral
    from mlc_projeto.checks.elu.flexao            import verifica_flexao
    from mlc_projeto.checks.elu.cisalhamento      import verifica_cisalhamento
    from mlc_projeto.checks.elu.apoio             import verifica_apoio
    from mlc_projeto.checks.elu.flexo_compressao  import verifica_flexo_compressao
    from mlc_projeto.checks.elu.pilares           import verifica_pilar
    from mlc_projeto.checks.els.deflection_els    import verificar_ELS
    from mlc_projeto.connections.connections      import dimensionar_ligacoes
    from mlc_projeto.checks.elu.tercas            import verifica_terca

    geo   = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat   = GlulamMaterial("GL24h", 2, "curta")
    mat_l = GlulamMaterial("GL24h", 2, "longa")
    params= ParametrosVento(V0=45,S1=1,categoria="IV",classe="B",S3=1,
                             L=20.25,H1=1,h=7,dist_portico=5.75)
    load  = carregamentos_com_vento(geo=geo,mat=mat,g_area=1.5,
                                     q_area=0.25,L_t=5.75,params_vento=params)

    w   = calcular_vento(params).pressoes["C1"]["barlavento_kNm2"]
    fc  = verifica_flexo_compressao(geo,mat,load,0.20,0.20,7.0,2.53)
    lig = dimensionar_ligacoes(mat,load,geo,20,30,80)
    t   = verifica_terca(mat,5.75,2.53,0.20,0.58,4.5,1.50,0.25,w)
    t["eta"] = t["eta_gov"]
    pc  = verifica_pilar(mat, 0.26, 0.26, 7.0, 2*load.V_max_ELU())

    resultados = {
        "cumeeira":    verifica_cumeeira(geo,mat,load),
        "flambagem":   verifica_flambagem_lateral(geo,mat,load,2.53),
        "flexao":      verifica_flexao(geo,mat,load,2.53),
        "cisalhamento":verifica_cisalhamento(geo,mat,load),
        "apoio":       verifica_apoio(geo,mat,load,0.50),
        "flexo_comp":  fc,
        "ELS":         verificar_ELS(geo,mat_l,load),
        "terca":       t,
        "pilar_central": pc,
        "L1": lig["L1"], "L2": lig["L2"], "L3": lig["L3"],
    }

    print("Abrindo visualização 3D — vão total 40,5m...")
    visualizar_galpao(geo, resultados, H_pilar=7.0)