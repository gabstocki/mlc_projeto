"""
visualization/viz_3d.py — Visualização 3D do galpão MLC.

Constrói a geometria 3D completa do galpão a partir dos parâmetros
do projeto e coloriza cada elemento pelo η calculado pelo pipeline.

Estrutura visualizada:
    - 2 pórticos principais (vigas duplo-bisel + pilares)
    - 8 módulos × 5,75 m = 46 m de comprimento
    - Terças entre os pórticos
    - Superfície de cobertura translúcida

Escala de cores por η:
    Verde       η < 0,50   — confortável
    Amarelo     0,50 ≤ η < 0,80  — atenção
    Laranja     0,80 ≤ η < 0,95  — próximo do limite
    Vermelho    η ≥ 0,95   — crítico

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

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial


# ── Escala de cores ───────────────────────────────────────────────────────────

def eta_para_cor(eta: float) -> tuple:
    """Retorna cor RGB para um dado η."""
    if eta < 0.50:
        return (0.20, 0.70, 0.20)    # verde
    elif eta < 0.80:
        return (0.95, 0.80, 0.10)    # amarelo
    elif eta < 0.95:
        return (0.95, 0.45, 0.10)    # laranja
    else:
        return (0.85, 0.10, 0.10)    # vermelho


# ── Construtores de geometria ─────────────────────────────────────────────────

def _tubo_reta(p0, p1, raio=0.05):
    """Cria um tubo cilíndrico entre dois pontos."""
    linha = pv.Line(p0, p1)
    return linha.tube(radius=raio)


def _viga_duplo_bisel(
    x0: float, y0: float,
    L: float, h0: float, h_ap: float,
    alpha_rad: float, b: float,
    z_base: float = 0.0,
    n_pts: int = 40,
) -> pv.PolyData:
    """
    Cria a geometria 3D da viga de duplo-bisel como sólido extrudado.

    Constrói o perfil da viga no plano XZ e extruda na direção Y (largura b).
    A linha do eixo segue h(x) = h0 + x·tan(α) para x ≤ L/2.
    """
    x = np.linspace(0, L, n_pts)
    x_sim = np.where(x <= L/2, x, L - x)
    h_x = h0 + x_sim * math.tan(alpha_rad)

    # Pontos do contorno superior (linha de cumeeira inclinada)
    topo  = np.column_stack([
        x0 + x,
        np.full(n_pts, y0),
        h_x
    ])
    # Pontos do contorno inferior (base reta)
    base  = np.column_stack([
        x0 + x,
        np.full(n_pts, y0),
        np.zeros(n_pts)
    ])

    # Eixo da viga (linha central)
    eixo = np.column_stack([
        x0 + x,
        np.full(n_pts, y0),
        z_base + h_x / 2
    ])

    # Simplificação: representar como tubo ao longo do eixo
    pts   = eixo
    cells = np.hstack([
        np.full(n_pts - 1, 2),
        np.column_stack([
            np.arange(n_pts - 1),
            np.arange(1, n_pts)
        ]).ravel()
    ])
    linha = pv.PolyData()
    linha.points = pts
    linha.lines  = np.hstack([
        np.full((n_pts-1, 1), 2),
        np.column_stack([np.arange(n_pts-1), np.arange(1, n_pts)])
    ]).ravel()

    # Raio proporcional à altura média
    raio = (h0 + h_ap) / 4 * 0.8
    return linha.tube(radius=raio, n_sides=8)


def _pilar(x, y, H, b=0.20, h=0.20):
    """Cria a geometria 3D de um pilar retangular."""
    p0 = np.array([x, y, 0.0])
    p1 = np.array([x, y, float(H)])
    raio = (b + h) / 4 * 0.8
    return _tubo_reta(p0, p1, raio=raio)


def _terca(x_viga, y0, y1, z):
    """Cria uma terça horizontal entre dois pórticos."""
    p0 = np.array([x_viga, y0, z])
    p1 = np.array([x_viga, y1, z])
    return _tubo_reta(p0, p1, raio=0.04)


def _superficie_cobertura(
    x_inicio: float, x_fim: float,
    y_inicio: float, y_fim: float,
    L: float, h0: float, h_ap: float,
    alpha_rad: float,
    z_base: float = 0.0,
    n_x: int = 30, n_y: int = 10,
) -> pv.StructuredGrid:
    """Cria a superfície de cobertura (malha estruturada)."""
    x_pts = np.linspace(x_inicio, x_fim, n_x)
    y_pts = np.linspace(y_inicio, y_fim, n_y)

    XX, YY = np.meshgrid(x_pts, y_pts)

    # Altura da cobertura em cada ponto x
    x_rel  = XX - x_inicio
    x_sim  = np.where(x_rel <= L/2, x_rel, L - x_rel)
    ZZ     = z_base + h0 + x_sim * math.tan(alpha_rad)

    grid = pv.StructuredGrid(XX, YY, ZZ)
    return grid


# ── Visualização principal ────────────────────────────────────────────────────

def visualizar_galpao(
    geo:        GeometriaViga,
    resultados: dict,
    H_pilar:    float = 7.0,
    n_modulos:  int   = 8,
    dist_mod:   float = 5.75,
    b_pilar:    float = 0.20,
    h_pilar:    float = 0.20,
    b_terca:    float = 0.20,
    h_terca:    float = 0.58,
    salvar_imagem: str | None = None,
) -> None:
    """
    Visualiza o galpão MLC completo em 3D com PyVista.

    Cada elemento é colorido pelo η da verificação correspondente.

    Args:
        geo            : Geometria da viga principal
        resultados     : Dict com todos os resultados do pipeline
        H_pilar        : Altura dos pilares (m)
        n_modulos      : Número de módulos ao longo do comprimento
        dist_mod       : Espaçamento entre pórticos (m)
        b_pilar/h_pilar: Seção dos pilares (m)
        b_terca/h_terca: Seção das terças (m)
        salvar_imagem  : Caminho para salvar screenshot (None = não salvar)
    """
    if not PYVISTA_OK:
        print("PyVista não instalado. Rode: pip install pyvista")
        return

    # Extrair ηs dos resultados
    eta_viga   = max(
        resultados.get("apoio",       {}).get("eta", 0.0),
        resultados.get("cisalhamento",{}).get("eta", 0.0),
        resultados.get("flexao",      {}).get("eta", 0.0),
        resultados.get("flambagem",   {}).get("eta", 0.0),
    )
    eta_pilar  = resultados.get("flexo_comp", {}).get("pilar", {}).get("eta", 0.0)
    eta_terca  = resultados.get("terca",      {}).get("eta",   0.0)
    eta_L1     = resultados.get("L1",         {}).get("eta",   0.0)
    eta_L2     = resultados.get("L2",         {}).get("eta",   0.0)
    eta_L3     = resultados.get("L3",         {}).get("eta",   0.0)

    cor_viga   = eta_para_cor(eta_viga)
    cor_pilar  = eta_para_cor(eta_pilar)
    cor_terca  = eta_para_cor(eta_terca)
    cor_L1     = eta_para_cor(eta_L1)
    cor_L2     = eta_para_cor(eta_L2)

    L       = geo.L
    h0      = geo.h0
    h_ap    = geo.h_ap
    alpha   = geo.alpha_rad
    comp    = n_modulos * dist_mod   # comprimento total

    # Posições Y dos pórticos
    y_porticos = [i * dist_mod for i in range(n_modulos + 1)]
    # Os 2 pórticos principais ficam no início e no fim
    # As terças conectam todos os módulos

    plotter = pv.Plotter(window_size=[1400, 800])
    plotter.set_background("white")
    plotter.add_axes()

    # ── Vigas principais ──────────────────────────────────────
    for y in y_porticos:
        mesh = _viga_duplo_bisel(
            x0=0, y0=y, L=L,
            h0=h0, h_ap=h_ap, alpha_rad=alpha, b=geo.b,
            z_base=H_pilar,
        )
        plotter.add_mesh(mesh, color=cor_viga, smooth_shading=True,
                         label=f"Viga η={eta_viga:.3f}" if y == y_porticos[0] else "")

        # Rótula na cumeeira — esfera
        x_cum = L / 2
        z_cum = H_pilar + h_ap
        plotter.add_mesh(
            pv.Sphere(radius=0.08, center=(x_cum, y, z_cum)),
            color=(0.3, 0.3, 0.9)
        )

    # ── Pilares ───────────────────────────────────────────────
    for y in y_porticos:
        for x_p in [0.0, L]:
            mesh = _pilar(x_p, y, H_pilar, b_pilar, h_pilar)
            plotter.add_mesh(mesh, color=cor_pilar, smooth_shading=True,
                             label=f"Pilar η={eta_pilar:.3f}" if (y == y_porticos[0] and x_p == 0) else "")

            # Rótula na base — esfera
            plotter.add_mesh(
                pv.Sphere(radius=0.08, center=(x_p, y, 0.0)),
                color=(0.3, 0.3, 0.9)
            )

    # ── Terças ────────────────────────────────────────────────
    n_tercas_por_vao = int(L / 1.0)   # s = 1,00 m
    x_tercas = np.linspace(0, L, n_tercas_por_vao + 1)

    for i in range(len(y_porticos) - 1):
        y0_t = y_porticos[i]
        y1_t = y_porticos[i + 1]
        for x_t in x_tercas:
            x_sim = x_t if x_t <= L/2 else L - x_t
            z_t   = H_pilar + h0 + x_sim * math.tan(alpha)
            mesh  = _terca(x_t, y0_t, y1_t, z_t)
            plotter.add_mesh(mesh, color=cor_terca, smooth_shading=True,
                             label=f"Terça η={eta_terca:.3f}" if (i == 0 and x_t == x_tercas[0]) else "")

    # ── Superfície de cobertura ───────────────────────────────
    sup = _superficie_cobertura(
        x_inicio=0, x_fim=L,
        y_inicio=0, y_fim=comp,
        L=L, h0=h0, h_ap=h_ap, alpha_rad=alpha,
        z_base=H_pilar,
    )
    plotter.add_mesh(
        sup, color=(0.7, 0.85, 0.95),
        opacity=0.25, show_edges=False,
        label="Cobertura"
    )

    # ── Piso de referência ────────────────────────────────────
    piso = pv.Plane(
        center=(L/2, comp/2, -0.05),
        direction=(0, 0, 1),
        i_size=L + 2, j_size=comp + 2,
    )
    plotter.add_mesh(piso, color=(0.85, 0.85, 0.85), opacity=0.5)

    # ── Legenda de cores ──────────────────────────────────────
    legenda = [
        ["η < 0,50  Confortável",  (0.20, 0.70, 0.20)],
        ["η 0,50–0,80  Atenção",   (0.95, 0.80, 0.10)],
        ["η 0,80–0,95  Próx. lim.",(0.95, 0.45, 0.10)],
        ["η ≥ 0,95  Crítico",      (0.85, 0.10, 0.10)],
        ["Rótulas",                 (0.30, 0.30, 0.90)],
    ]
    plotter.add_legend(legenda, bcolor=(1,1,1), border=True, size=(0.22, 0.16))

    # ── Texto de informação ───────────────────────────────────
    info = (
        f"STOCKI Engenharia Estrutural\n"
        f"Galpão MLC GL24h — Pórtico de 3 Rótulas\n"
        f"L={L}m | h0={h0}m | α={geo.alpha_deg}° | b={geo.b}m\n"
        f"η máximo = {max(eta_viga,eta_pilar,eta_terca,eta_L1,eta_L2):.4f}"
    )
    plotter.add_text(info, position="upper_left", font_size=9, color="black")

    # ── Câmera ────────────────────────────────────────────────
    plotter.camera_position = [
        (L * 1.8, -comp * 0.4, H_pilar * 2.5),
        (L / 2,    comp / 2,   h_ap / 2),
        (0, 0, 1),
    ]

    if salvar_imagem:
        plotter.show(auto_close=False)
        plotter.screenshot(salvar_imagem)
        plotter.close()
        print(f"  Imagem 3D salva: {salvar_imagem}")
    else:
        plotter.show(title="Galpão MLC — Visualização 3D")


# ── Execução direta ───────────────────────────────────────────────────────────

if __name__ == "__main__":

    from mlc_projeto.core.geometry  import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind      import ParametrosVento
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
    from mlc_projeto.core.wind                    import calcular_vento

    geo = GeometriaViga(L=20.25, h0=0.60, alpha_deg=4.5, b=0.26)
    mat = GlulamMaterial("GL24h", 2, "curta")
    mat_l = GlulamMaterial("GL24h", 2, "longa")

    params = ParametrosVento(V0=45,S1=1,categoria="IV",classe="B",
                              S3=1,L=20.25,H1=1,h=7,dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo,mat=mat,g_area=1.5,
                                    q_area=0.25,L_t=5.75,params_vento=params)

    w = calcular_vento(params).pressoes["C1"]["barlavento_kNm2"]
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
        "L1":          lig["L1"],
        "L2":          lig["L2"],
        "L3":          lig["L3"],
    }

    print("Abrindo visualização 3D...")
    visualizar_galpao(geo, resultados, H_pilar=7.0)
