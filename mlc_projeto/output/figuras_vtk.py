"""
output/figuras_vtk.py — Figuras do modelo tridimensional para a monografia.

Lê os arquivos gerados por `mlc_projeto.opensees.opensees_vtk` e produz
imagens em modo headless, sem depender do ParaView.

EXECUÇÃO:
    python -m mlc_projeto.output.figuras_vtk [destino]

SAÍDA (destino padrão: tese/fig/):
    modelo_3d.png          vista isométrica do conjunto
    portico_elevacao.png   elevação de um pórtico transversal
    modelo_momento.png     momento fletor na combinação governante de ELU
    modelo_eta.png         taxa de utilização em flexão
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyvista as pv

from mlc_projeto.main import B_TERCA, H_TERCA, H_PILAR_ALT

pv.OFF_SCREEN = True

VTK_DIR = Path(__file__).parent.parent.parent / "output" / "vtk"
DESTINO_PADRAO = Path(__file__).parent.parent.parent / "tese" / "fig"

# Câmera comum às vistas em perspectiva, para que as figuras sejam comparáveis
# entre si (mesma posição, mesmo enquadramento, mesma escala aparente).
CAMERA = [(76.0, -50.0, 31.0), (20.2, 23.0, 5.5), (0.0, 0.0, 1.0)]
ZOOM = 1.22

# Resolução alta: as figuras entram na página com cerca de 14 cm de largura.
TAMANHO = (2400, 1250)
FUNDO = "white"
COR_MADEIRA = "#c8a97e"


def _recortar(arq: Path, margem: int = 12) -> Path:
    """
    Remove a moldura branca em torno do conteúdo renderizado.

    O VTK devolve a janela inteira, com folga variável em torno do modelo.
    Sem o recorte, a figura entra na página menor do que poderia e com
    margens desiguais entre uma vista e outra.
    """
    from PIL import Image, ImageChops

    im = Image.open(arq).convert("RGB")
    fundo = Image.new("RGB", im.size, (255, 255, 255))
    caixa = ImageChops.difference(im, fundo).getbbox()
    if caixa is None:
        return arq
    x0 = max(caixa[0] - margem, 0)
    y0 = max(caixa[1] - margem, 0)
    x1 = min(caixa[2] + margem, im.width)
    y1 = min(caixa[3] + margem, im.height)
    im.crop((x0, y0, x1, y1)).save(arq)
    return arq


def _plotter(tamanho=TAMANHO) -> pv.Plotter:
    p = pv.Plotter(off_screen=True, window_size=tamanho)
    p.set_background(FUNDO)
    p.enable_anti_aliasing("ssaa")
    return p


def _barra() -> dict:
    """
    Barra de escala apenas com os valores.

    O título fica a cargo da legenda em LaTeX: o renderizador do VTK não
    compõe os caracteres acentuados do português, e um rótulo como
    "utilizacao em flexao" seria pior do que rótulo nenhum.
    """
    return dict(
        title="",
        n_labels=6,
        fmt="%.0f",
        color="black",
        vertical=False,
        position_x=0.06,
        position_y=0.045,
        width=0.42,
        height=0.040,
        label_font_size=30,
    )



def _separar(malha: pv.UnstructuredGrid) -> dict[str, pv.UnstructuredGrid]:
    """
    Separa a malha em vigas principais, terças e pilares.

    A distinção é feita pela SEÇÃO transversal, e não pelo comprimento: cada
    elemento é discretizado em hexaedros curtos, de modo que o comprimento do
    hexaedro não identifica a direção da peça. Os pilares são uma peça única de
    7 m de altura; as terças têm seção 0,20 x 0,58 m; as vigas, largura igual à
    da seção principal e altura variável entre h0 e h_ap.

    Sem essa separação a escala de cor fica dominada pelos elementos de momento
    nulo, que ocupam a extremidade escura do mapa e escondem o gradiente das
    vigas principais.
    """
    n = malha.n_cells
    pts = np.asarray(malha.points)
    # Hexaedros: 8 nós por célula, na ordem em que foram gravados.
    conec = np.asarray(malha.cells).reshape(n, 9)[:, 1:]
    cantos = pts[conec]                       # (n, 8, 3)
    extensao = np.ptp(cantos, axis=1)         # (n, 3)
    dx, dy, dz = extensao[:, 0], extensao[:, 1], extensao[:, 2]
    tol = 0.02
    eh_pilar = dz > 0.5 * H_PILAR_ALT
    eh_terca = (~eh_pilar) & (np.abs(dz - H_TERCA) < tol) \
                          & (np.abs(dx - B_TERCA) < tol)
    eh_viga = ~(eh_pilar | eh_terca)
    return {
        "vigas":   malha.extract_cells(np.where(eh_viga)[0]),
        "tercas":  malha.extract_cells(np.where(eh_terca)[0]),
        "pilares": malha.extract_cells(np.where(eh_pilar)[0]),
    }


def vista_isometrica(destino: Path) -> Path:
    """Vista geral do conjunto, sem campo escalar."""
    malha = pv.read(VTK_DIR / "portico_G_only.vtk")
    p = _plotter()
    p.add_mesh(malha, color=COR_MADEIRA, show_edges=False,
               smooth_shading=True, ambient=0.25, diffuse=0.75, specular=0.1)
    p.camera_position = CAMERA
    p.camera.zoom(ZOOM)
    arq = destino / "modelo_3d.png"
    p.screenshot(str(arq))
    p.close()
    return _recortar(arq)


def elevacao_portico(destino: Path) -> Path:
    """Elevação de um pórtico transversal, evidenciando o duplo-bisel."""
    malha = pv.read(VTK_DIR / "portico_G_only.vtk")
    # Recorta uma fatia em torno do primeiro alinhamento de pórtico (y = 0).
    fatia = malha.clip_box(
        bounds=(-1.0, 41.5, -0.40, 0.40, -1.0, 12.0), invert=False)
    p = _plotter(tamanho=(2400, 780))
    p.add_mesh(fatia, color=COR_MADEIRA, show_edges=True,
               edge_color="#6b5636", line_width=1, smooth_shading=False)
    p.view_xz()
    p.camera.zoom(2.6)
    arq = destino / "portico_elevacao.png"
    p.screenshot(str(arq))
    p.close()
    return _recortar(arq)


def _campo(destino: Path, arquivo: str, campo: str, titulo: str,
           nome: str, mapa: str, fmt: str = "%.0f") -> Path:
    malha = pv.read(VTK_DIR / arquivo)
    partes = _separar(malha)
    vigas = partes["vigas"]
    lim = (0.0, float(np.nanmax(np.asarray(vigas.cell_data[campo]))))

    barra = _barra()
    barra["fmt"] = fmt
    p = _plotter()
    # Terças e pilares em cinza neutro: situam o leitor sem disputar a escala.
    for outro in ("tercas", "pilares"):
        if partes[outro].n_cells:
            p.add_mesh(partes[outro], color="#d0ccc6", show_edges=False,
                       smooth_shading=True, ambient=0.35, diffuse=0.6)
    p.add_mesh(vigas, scalars=campo, cmap=mapa, clim=lim, show_edges=False,
               smooth_shading=True, scalar_bar_args=barra)
    p.camera_position = CAMERA
    p.camera.zoom(ZOOM)
    arq = destino / nome
    p.screenshot(str(arq))
    p.close()
    return _recortar(arq)


def campo_momento(destino: Path) -> Path:
    return _campo(destino, "portico_ELU_C2.vtk", "M_kNm",
                  "Momento fletor (kN.m)", "modelo_momento.png", "inferno")


def campo_eta(destino: Path) -> Path:
    return _campo(destino, "portico_ELU_C2.vtk", "eta_M",
                  "Taxa de utilizacao em flexao", "modelo_eta.png",
                  "viridis", fmt="%.2f")


def gerar(destino: Path = DESTINO_PADRAO) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    faltando = [f for f in ("portico_G_only.vtk", "portico_ELU_C2.vtk")
                if not (VTK_DIR / f).exists()]
    if faltando:
        raise FileNotFoundError(
            f"Arquivos VTK ausentes em {VTK_DIR}: {', '.join(faltando)}. "
            "Execute antes: python -m mlc_projeto.opensees.opensees_vtk"
        )

    arquivos = [
        vista_isometrica(destino),
        elevacao_portico(destino),
        campo_momento(destino),
        campo_eta(destino),
    ]
    # Registra a amplitude dos campos, para conferência das legendas no texto.
    elu = pv.read(VTK_DIR / "portico_ELU_C2.vtk")
    for campo in ("M_kNm", "eta_M"):
        v = np.asarray(elu.cell_data[campo])
        print(f"  {campo:10s} {np.nanmin(v):9.3f} .. {np.nanmax(v):9.3f}")
    for a in arquivos:
        print(f"  {a.name:24s} {a.stat().st_size // 1024:5d} KB")
    return arquivos


if __name__ == "__main__":
    alvo = Path(sys.argv[1]) if len(sys.argv) > 1 else DESTINO_PADRAO
    gerar(alvo)
