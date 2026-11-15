"""Issue 90 — DES-05 (L1 + corte A–A), DES-05B (L1c + corte B–B), DES-05C (chapa em VG)."""
import subprocess

from matplotlib.patches import FancyBboxPatch

from mlc_projeto.output import desenhos as D


def test_folhas_novas_registradas():
    nomes = [n for n, _ in D.FOLHAS]
    assert {"des05_ligacao_L1.pdf", "des05b_ligacao_L1c.pdf", "des05c_chapa_L1.pdf"} <= set(nomes)
    assert "des05_ligacoes_L1_L1c.pdf" not in nomes


def test_furo_da_chapa_embutida_em_linha_oculta():
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    D._pino(ax, 0, 0, 24, oblongo=(20, 15))
    furo = [p for p in ax.patches if isinstance(p, FancyBboxPatch)][0]
    assert furo.get_linestyle() not in ("-", "solid")
    assert not furo.get_fill()
    plt.close(fig)


def test_textos_das_folhas(tmp_path):
    from pathlib import Path
    fig = Path(D.__file__).parents[2] / "tese" / "fig"
    for nome, chave in (("des05_ligacao_L1.pdf", "CORTE A–A"), ("des05b_ligacao_L1c.pdf", "CORTE B–B"),
                        ("des05c_chapa_L1.pdf", "MONTAGEM")):
        txt = subprocess.run(["pdftotext", str(fig / nome), "-"], capture_output=True,
                             text=True).stdout
        assert chave in txt
