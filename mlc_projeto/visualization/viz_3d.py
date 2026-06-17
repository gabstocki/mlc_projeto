"""
visualization/viz_3d.py — Visualização 3D estilo SAP2000. v2

Representação por extrusão da seção transversal ao longo do eixo
do elemento — padrão SAP2000/Robot Structural Analysis.

Cada elemento mostra sua seção transversal real:
    Viga: seção b × h(x) variável — segmentos prismáticos
    Pilar: seção b × h constante — box vertical
    Terça: seção b × h constante — box inclinado

Escala de cores por η:
    Verde       η < 0,50
    Amarelo     0,50 ≤ η < 0,80
    Laranja     0,80 ≤ η < 0,95
    Vermelho    η ≥ 0,95
    Azul        rótulas

Dependências: pyvista, numpy
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
    if eta < 0.50:  return (0.18, 0.62, 0.18)   # verde
    if eta < 0.80:  return (0.95, 0.78, 0.05)   # amarelo
    if eta < 0.95:  return (0.92, 0.42, 0.07)   # laranja
    return              (0.82, 0.07, 0.07)       # vermelho


# ── Primitivas geométricas ────────────────────────────────────────────────────

def _seccao_retangular(b: float, h: float) -> np.ndarray:
    """
    Retorna os 4 vértices da seção transversal centrada na origem.
    Eixo do elemento ao longo de X.
    Seção no plano YZ: b=Y, h=Z.
    """
    hb, hh = b / 2, h / 2
    return np.array([
        [ 0, -hb, -hh],
        [ 0,  hb, -hh],
        [ 0,  hb,  hh],
        [ 0, -hb,  hh],
    ], dtype=float)


def _prisma_segmento(
    p0: np.ndarray, p1: np.ndarray,
    b0: float, h0: float,
    b1: float, h1: float,
    up: np.ndarray = None,
) -> pv.UnstructuredGrid:
    """
    Cria um prisma hexaédrico entre dois pontos p0 e p1.
    Seção em p0: b0 × h0 | Seção em p1: b1 × h1

    O eixo local X aponta de p0 para p1.
    O eixo local Z aponta para 'up' (direção da altura da seção).
    O eixo local Y é perpendicular (largura da seção).

    Args:
        p0, p1 : pontos extremos (array 3D)
        b0, h0 : largura e altura no ponto p0
        b1, h1 : largura e altura no ponto p1
        up     : vetor "para cima" da seção (padrão: (0,0,1))
    """
    vec = p1 - p0
    L   = np.linalg.norm(vec)
    if L < 1e-9:
        return None

    ex = vec / L   # eixo local X — ao longo do elemento

    if up is None:
        up = np.array([0.0, 0.0, 1.0])

    # Eixo local Z — direção da altura da seção
    ez = up - np.dot(up, ex) * ex
    if np.linalg.norm(ez) < 1e-9:
        ez = np.array([0.0, 1.0, 0.0])
    ez = ez / np.linalg.norm(ez)

    # Eixo local Y — largura da seção
    ey = np.cross(ez, ex)
    ey = ey / np.linalg.norm(ey)

    # Função para construir a seção em um ponto
    def secao(pt, b, h):
        hb, hh = b / 2, h / 2
        return np.array([
            pt - hb*ey - hh*ez,
            pt + hb*ey - hh*ez,
            pt + hb*ey + hh*ez,
            pt - hb*ey + hh*ez,
        ])

    s0 = secao(p0, b0, h0)
    s1 = secao(p1, b1, h1)

    # 8 vértices do hexaedro
    pts = np.vstack([s0, s1])  # shape (8,3)

    # Faces do hexaedro (6 faces, 4 vértices cada)
    faces = np.array([
        [4, 0, 1, 2, 3],     # face p0
        [4, 4, 5, 6, 7],     # face p1
        [4, 0, 1, 5, 4],     # face inferior
        [4, 2, 3, 7, 6],     # face superior
        [4, 0, 3, 7, 4],     # face lateral esq
        [4, 1, 2, 6, 5],     # face lateral dir
    ]).ravel()

    mesh = pv.PolyData(pts, faces)
    return mesh


# ── Construtores de elementos ─────────────────────────────────────────────────

def _viga_sap(
    x0: float, y0: float, z_base: float,
    L: float, h0: float, h_ap: float,
    alpha_rad: float, b: float,
    n_seg: int = 20,
) -> pv.PolyData:
    """
    Viga duplo-bisel estilo SAP2000.

    Seção retangular b × h(x) extrudada ao longo do eixo inclinado.
    Dividida em n_seg segmentos para mostrar a variação de altura.

    O eixo da viga segue a linha de cumeeira inclinada.
    A seção é sempre vertical (ez = (0,0,1)).
    """
    x_pts = np.linspace(0, L, n_seg + 1)
    x_sim = np.where(x_pts <= L/2, x_pts, L - x_pts)
    h_pts = h0 + x_sim * math.tan(alpha_rad)

    # Eixo da viga: centro da seção em cada ponto
    # O centro da seção está em z = z_base + h(x)/2
    pts_eixo = np.column_stack([
        x0 + x_pts,
        np.full(n_seg + 1, y0),
        z_base + h_pts / 2,
    ])

    meshes = []
    for i in range(n_seg):
        p0 = pts_eixo[i]
        p1 = pts_eixo[i + 1]
        seg = _prisma_segmento(
            p0, p1,
            b0=b, h0=h_pts[i],
            b1=b, h1=h_pts[i + 1],
            up=np.array([0.0, 0.0, 1.0]),
        )
        if seg is not None:
            meshes.append(seg)

    if not meshes:
        return pv.PolyData()

    combined = meshes[0]
    for m in meshes[1:]:
        combined = combined.merge(m)
    return combined


def _pilar_sap(
    x: float, y: float,
    H: float, b: float, h: float,
) -> pv.PolyData:
    """
    Pilar retangular b × h, altura H.
    Seção no plano XY (b=X, h=Y), altura em Z.
    Estilo SAP2000: box com seção exata.
    """
    p0 = np.array([x, y, 0.0])
    p1 = np.array([x, y, H])
    # up = eixo X local para o pilar (seção orientada no plano do pórtico)
    return _prisma_segmento(
        p0, p1,
        b0=b, h0=h,
        b1=b, h1=h,
        up=np.array([1.0, 0.0, 0.0]),
    )


def _terca_sap(
    x_t: float, y0: float, y1: float,
    z: float, b: float, h: float,
    alpha_rad: float = 0.0,
) -> pv.PolyData:
    """
    Terça retangular b × h entre dois pórticos.
    Orientada na direção Y (entre pórticos).
    """
    p0 = np.array([x_t, y0, z])
    p1 = np.array([x_t, y1, z])
    # up = direção Z (altura da terça vertical)
    return _prisma_segmento(
        p0, p1,
        b0=b, h0=h,
        b1=b, h1=h,
        up=np.array([0.0, 0.0, 1.0]),
    )


def _rotula_sap(cx, cy, cz, raio=0.07):
    """Esfera representando uma rótula."""
    return pv.Sphere(radius=raio, center=(cx, cy, cz), theta_resolution=12, phi_resolution=12)


# ── Visualização principal ────────────────────────────────────────────────────

def visualizar_galpao(
    geo:           GeometriaViga,
    resultados:    dict,
    H_pilar:       float = 7.0,
    n_modulos:     int   = 8,
    dist_mod:      float = 5.75,
    b_pilar:       float = 0.20,
    h_pilar:       float = 0.20,
    b_terca:       float = 0.20,
    h_terca:       float = 0.58,
    salvar_imagem: str | None = None,
) -> None:
    """
    Visualização 3D estilo SAP2000 do galpão MLC.

    Seções transversais reais extrudadas ao longo dos eixos dos elementos.
    Coloração por η de cada elemento.
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
    eta_pilar = resultados.get("flexo_comp", {}).get("pilar", {}).get("eta", 0.0)
    if not eta_pilar:
        eta_pilar = resultados.get("flexo_comp", {}).get("eta", 0.0)
    eta_terca = resultados.get("terca", {}).get("eta", 0.0)

    cor_viga  = eta_cor(eta_viga)
    cor_pilar = eta_cor(eta_pilar)
    cor_terca = eta_cor(eta_terca)
    cor_rot   = (0.15, 0.35, 0.85)   # azul — rótulas

    L       = geo.L
    h0      = geo.h0
    h_ap    = geo.h_ap
    alpha   = geo.alpha_rad
    b_viga  = geo.b
    comp    = n_modulos * dist_mod

    y_porticos = [i * dist_mod for i in range(n_modulos + 1)]

    plotter = pv.Plotter(window_size=[1400, 820])
    plotter.set_background("white")
    plotter.add_axes(
        xlabel="X (vão)", ylabel="Y (compr.)", zlabel="Z (alt.)",
        line_width=2,
    )

    # ── Vigas ─────────────────────────────────────────────────
    for y in y_porticos:
        mesh = _viga_sap(
            x0=0, y0=y, z_base=H_pilar,
            L=L, h0=h0, h_ap=h_ap,
            alpha_rad=alpha, b=b_viga,
            n_seg=24,
        )
        plotter.add_mesh(
            mesh, color=cor_viga,
            smooth_shading=True,
            show_edges=False,
            label=f"Viga GL24h  η={eta_viga:.3f}" if y == y_porticos[0] else "",
        )

        # Rótula cumeeira
        plotter.add_mesh(
            _rotula_sap(L/2, y, H_pilar + h_ap),
            color=cor_rot,
            label="Rótulas" if y == y_porticos[0] else "",
        )

    # ── Pilares ───────────────────────────────────────────────
    for y in y_porticos:
        for x_p in [0.0, L]:
            mesh = _pilar_sap(x_p, y, H_pilar, b_pilar, h_pilar)
            if mesh:
                plotter.add_mesh(
                    mesh, color=cor_pilar,
                    smooth_shading=True,
                    show_edges=False,
                    label=f"Pilar GL24h  η={eta_pilar:.3f}"
                    if (y == y_porticos[0] and x_p == 0) else "",
                )
            # Rótulas base e topo pilar
            plotter.add_mesh(_rotula_sap(x_p, y, 0.0), color=cor_rot)
            plotter.add_mesh(_rotula_sap(x_p, y, H_pilar), color=cor_rot)

    # ── Terças ────────────────────────────────────────────────
    n_tercas = int(L)   # s=1,00m → 20 terças por módulo + 1
    x_tercas = np.linspace(0, L, n_tercas + 1)

    for i in range(len(y_porticos) - 1):
        y0_t = y_porticos[i]
        y1_t = y_porticos[i + 1]
        for j, x_t in enumerate(x_tercas):
            xs   = x_t if x_t <= L/2 else L - x_t
            z_t  = H_pilar + h0 + xs * math.tan(alpha)
            mesh = _terca_sap(x_t, y0_t, y1_t, z_t, b_terca, h_terca)
            if mesh:
                plotter.add_mesh(
                    mesh, color=cor_terca,
                    smooth_shading=True,
                    show_edges=False,
                    label=f"Terça GL24h  η={eta_terca:.3f}"
                    if (i == 0 and j == 0) else "",
                )

    # ── Cobertura translúcida ─────────────────────────────────
    n_x, n_y = 40, 16
    xv = np.linspace(0, L, n_x)
    yv = np.linspace(0, comp, n_y)
    XX, YY = np.meshgrid(xv, yv)
    x_sim  = np.where(XX <= L/2, XX, L - XX)
    ZZ     = H_pilar + h0 + x_sim * math.tan(alpha)
    sup    = pv.StructuredGrid(XX, YY, ZZ)
    plotter.add_mesh(
        sup,
        color=(0.65, 0.82, 0.93),
        opacity=0.20,
        show_edges=False,
        label="Cobertura",
    )

    # ── Piso ──────────────────────────────────────────────────
    piso = pv.Plane(
        center=(L/2, comp/2, -0.05),
        direction=(0, 0, 1),
        i_size=L + 3, j_size=comp + 3,
    )
    plotter.add_mesh(piso, color=(0.88, 0.88, 0.88), opacity=0.6)

    # ── Legenda ───────────────────────────────────────────────
    legenda = [
        [f"Viga      η={eta_viga:.3f}",  cor_viga],
        [f"Pilar     η={eta_pilar:.3f}", cor_pilar],
        [f"Terça     η={eta_terca:.3f}", cor_terca],
        ["η < 0,50  Confortável",        (0.18, 0.62, 0.18)],
        ["η 0,50–0,80  Atenção",         (0.95, 0.78, 0.05)],
        ["η 0,80–0,95  Próx. limite",    (0.92, 0.42, 0.07)],
        ["η ≥ 0,95  Crítico",            (0.82, 0.07, 0.07)],
        ["Rótulas",                       cor_rot],
    ]
    plotter.add_legend(
        legenda, bcolor=(0.97, 0.97, 0.97),
        border=True, size=(0.24, 0.22),
    )

    # ── Informações ───────────────────────────────────────────
    eta_max = max(eta_viga, eta_pilar, eta_terca)
    info = (
        f"STOCKI Engenharia Estrutural\n"
        f"Galpão MLC GL24h — Pórtico de 3 Rótulas\n"
        f"L={L}m | h0={h0}m | α={geo.alpha_deg}° | "
        f"b={b_viga}m | H_pilar={H_pilar}m\n"
        f"η máximo = {eta_max:.4f}"
    )
    plotter.add_text(info, position="upper_left", font_size=9, color="black")

    # ── Câmera ────────────────────────────────────────────────
    plotter.camera_position = [
        ( L * 1.6,  -comp * 0.35,  H_pilar * 2.2),
        ( L / 2,     comp / 2,     (H_pilar + h_ap) / 2),
        (0, 0, 1),
    ]

    if salvar_imagem:
        plotter.show(auto_close=False)
        plotter.screenshot(salvar_imagem)
        plotter.close()
        print(f"  Imagem 3D salva: {salvar_imagem}")
    else:
        plotter.show(title="Galpão MLC — Visualização 3D (estilo SAP2000)")


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
    from mlc_projeto.checks.els.deflection_els    import verificar_ELS
    from mlc_projeto.connections.connections      import dimensionar_ligacoes
    from mlc_projeto.checks.elu.tercas            import verifica_terca

    geo   = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat   = GlulamMaterial("GL24h", 2, "curta")
    mat_l = GlulamMaterial("GL24h", 2, "longa")
    params= ParametrosVento(V0=45,S1=1,categoria="IV",classe="B",S3=1,
                             L=20.25,H1=1,h=7,dist_portico=5.75)
    load  = carregamentos_com_vento(geo=geo,mat=mat,g_area=1.5,q_area=0.25,
                                     L_t=5.75,params_vento=params)

    w   = calcular_vento(params).pressoes["C1"]["barlavento_kNm2"]
    fc  = verifica_flexo_compressao(geo,mat,load,0.20,0.20,7.0,1.0)
    lig = dimensionar_ligacoes(mat,load,geo,20,30,80)
    t   = verifica_terca(mat,5.75,1.0,0.20,0.58,4.5,1.5,0.25,w)
    t["eta"] = t["eta_gov"]

    resultados = {
        "cumeeira":    verifica_cumeeira(geo,mat,load),
        "flambagem":   verifica_flambagem_lateral(geo,mat,load,1.0),
        "flexao":      verifica_flexao(geo,mat,load,1.0),
        "cisalhamento":verifica_cisalhamento(geo,mat,load),
        "apoio":       verifica_apoio(geo,mat,load,0.50),
        "flexo_comp":  fc,
        "ELS":         verificar_ELS(geo,mat_l,load),
        "terca":       t,
        "L1": lig["L1"], "L2": lig["L2"], "L3": lig["L3"],
    }

    print("Abrindo visualização 3D estilo SAP2000...")
    visualizar_galpao(geo, resultados, H_pilar=7.0)