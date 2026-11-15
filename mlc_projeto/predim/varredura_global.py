"""
predim/varredura_global.py — Varredura global (α, h₀, b) sobre o pipeline real.

╔══════════════════════════════════════════════════════════════════════════╗
║ ROTA DE DECISÃO DE PROJETO                                               ║
║                                                                          ║
║ Este módulo NÃO reimplementa verificação nenhuma. Para cada ponto da     ║
║ grade ele monkeypatcha a geometria em `main` e chama `main._main_impl`,  ║
║ de modo que cada ponto é avaliado pela MESMA cadeia consolidada que      ║
║ produz o memorial: modelo Opção B (H = 0, issues 35/38), gerador de      ║
║ combinações EN 1990 de core/loads.py e o integrador de ELS de           ║
║ checks/els/deflection_els.py.                                            ║
║                                                                          ║
║ Substitui, para efeito de seleção de seção, o `predim.py`, que está      ║
║ fora da rota de decisão por AUD-010 (modelo de apoio horizontal rígido,  ║
║ combinações hard-coded e integrador de ELS distinto).                    ║
╚══════════════════════════════════════════════════════════════════════════╝

Uso:
    python -m mlc_projeto.predim.varredura_global            # grade padrão
    python -m mlc_projeto.predim.varredura_global --teste    # 2 pontos
    python -m mlc_projeto.predim.varredura_global -j 6       # 6 processos

Saída:
    output/varredura_global_consolidada.csv  (lida pela figura e pela tese)

Issue 93: refeita com o código atual — beiral (a_bal) na geometria e no volume,
verificações das issues 69–89 e a grade completa da tese (3.213 pontos).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import time
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.integrate import trapezoid

from mlc_projeto import main as pipeline
from mlc_projeto.core.geometry import GeometriaViga

# Diretório de saída do próprio pipeline.
OUTPUT_DIR = pipeline.OUTPUT_DIR

# Atributos de `main` que a varredura substitui em cada ponto. A largura dos
# pilares acompanha a largura da viga por decisão de projeto (apoio alinhado,
# sem excentricidade na transferência da reação vertical): variar `b` sem
# arrastar os pilares avaliaria uma estrutura que o projeto não constrói.
_ATRIBUTOS_LIGADOS_A_B = ("B_PILAR", "B_PILAR_C", "B_PILAR_CANTO")

# Verificações cuja taxa depende da SEÇÃO da viga (h₀, b) e não apenas do
# contorno do telhado. São estas que discriminam a geometria: os sistemas de
# contraventamento respondem à área exposta ao vento, variam com α e são
# insensíveis a h₀ e b, formando um teto que governaria η_max em toda a grade
# e tornaria a varredura cega às variáveis de seção.
CHECKS_DA_SECAO = (
    "cumeeira", "misula", "flambagem", "flexao", "cisalhamento", "apoio",
    "apoio_central", "flexo_comp", "ELS", "abertura_springings", "icamento",
    "balanco_viga", "oblongo_L1",
    "L1", "L1c", "fendilhamento_L1", "fendilhamento_L1c",
    "chapa_aco_L1", "chapa_aco_L1c",
)


@dataclass(frozen=True)
class Grade:
    """Grade de varredura. Valores em graus e metros."""
    alpha_deg: tuple[float, ...]
    h0:        tuple[float, ...]
    b:         tuple[float, ...]

    def pontos(self) -> list[tuple[float, float, float]]:
        return [tuple(round(v, 4) for v in p)          # type: ignore[misc]
                for p in product(self.alpha_deg, self.h0, self.b)]


GRADE_PADRAO = Grade(
    alpha_deg=tuple(6.0 + 0.5 * i for i in range(21)),        # 6,0°…16,0°
    h0=tuple(0.40 + 0.05 * i for i in range(17)),             # 0,40…1,20 m
    b=tuple(0.20 + 0.02 * i for i in range(9)),               # 0,20…0,36 m
)

GRADE_TESTE = Grade(alpha_deg=(10.0,), h0=(0.90, 1.00), b=(0.32,))


def volume_mlc_m3(alpha_deg: float, h0: float, b: float,
                  n_vigas: int = 18, n_balancos: int = 18) -> float:
    """
    Volume total de MLC das vigas principais (m³).

    Integra A(x) ao longo do vão com a própria geometria do pipeline, em vez
    de usar a altura média, para não presumir linearidade da seção. Soma o
    balanço do beiral (issue 82/93), que só existe no apoio externo de cada
    viga: `n_vigas` = 2 vigas por pórtico × 9 pórticos, e um balanço por viga.
    """
    a = float(pipeline.GEO_PARAMS.get("a_bal", 0.0))
    geo = GeometriaViga(L=pipeline.GEO_PARAMS["L"], h0=h0,
                        alpha_deg=alpha_deg, b=b, n_pts=401, a_bal=a)
    V = float(trapezoid(geo.A(geo.x), geo.x)) * n_vigas
    if a > 0:
        u = np.linspace(0.0, a, 101)
        V += float(trapezoid(b * geo.h_balanco(u), u)) * n_balancos
    return V


@contextlib.contextmanager
def _geometria(alpha_deg: float, h0: float, b: float):
    """Substitui a geometria em `main` e restaura ao sair, mesmo com exceção."""
    guardados = {"GEO_PARAMS": pipeline.GEO_PARAMS}
    guardados.update({a: getattr(pipeline, a) for a in _ATRIBUTOS_LIGADOS_A_B})
    guardados["gerar_relatorio"] = pipeline.gerar_relatorio
    try:
        pipeline.GEO_PARAMS = dict(pipeline.GEO_PARAMS,
                                   alpha_deg=alpha_deg, h0=h0, b=b)
        for a in _ATRIBUTOS_LIGADOS_A_B:
            setattr(pipeline, a, b)
        # O export de Excel/LaTeX/PDF não tem função na varredura e
        # sobrescreveria output/relatorio_mlc.* a cada ponto.
        pipeline.gerar_relatorio = lambda *a, **k: None
        yield
    finally:
        for nome, valor in guardados.items():
            setattr(pipeline, nome, valor)


def rodar_ponto(alpha_deg: float, h0: float, b: float) -> dict:
    """
    Executa o pipeline completo para uma geometria e devolve as taxas.

    Um ponto que levante exceção é registrado com `status='ERRO'` e a
    mensagem, em vez de interromper a varredura: geometrias inviáveis
    (ligação que não cabe em h₀, por exemplo) são informação, não falha.
    """
    registro: dict = {"alpha_deg": alpha_deg, "h0": h0, "b": b}
    registro["h_ap"] = h0 + (pipeline.GEO_PARAMS["L"] / 2) * np.tan(
        np.radians(alpha_deg))
    registro["volume_mlc_m3"] = volume_mlc_m3(alpha_deg, h0, b)

    t0 = time.perf_counter()
    try:
        with _geometria(alpha_deg, h0, b), \
             contextlib.redirect_stdout(io.StringIO()):
            res = pipeline._main_impl(rodar_varredura=False, abrir_viz=False)
    except Exception as exc:                       # noqa: BLE001
        registro.update(status="ERRO", erro=f"{type(exc).__name__}: {exc}",
                        eta_max=np.nan, gov="", n_verif=0,
                        segundos=time.perf_counter() - t0)
        return registro

    meta = res["meta"]
    etas = {k: v["eta"] for k, v in res.items()
            if isinstance(v, dict) and v.get("eta") is not None}
    gov = max(etas, key=etas.get) if etas else ""

    etas_secao = {k: v for k, v in etas.items() if k in CHECKS_DA_SECAO}
    gov_secao = max(etas_secao, key=etas_secao.get) if etas_secao else ""

    # `ok` pode vir como numpy.bool_ (comparações com floats do NumPy): `is False`
    # não o reconhece e omitia a causa. Só se ignora `ok` ausente ou None.
    reprova = sorted(k for k, v in res.items()
                     if isinstance(v, dict) and v.get("ok") is not None
                     and not bool(v["ok"]))
    registro.update(
        reprova=";".join(reprova),
        status=meta["status"],
        eta_max=meta["eta_max"],
        n_verif=meta["n_verif"],
        gov=gov,
        eta_secao=etas_secao.get(gov_secao, float("nan")),
        gov_secao=gov_secao,
        erro="",
        segundos=time.perf_counter() - t0,
    )
    registro.update({f"eta_{k}": v for k, v in etas.items()})
    return registro


def _rodar_tupla(p: tuple[float, float, float]) -> dict:
    return rodar_ponto(*p)


def varrer(grade: Grade = GRADE_PADRAO,
           csv: Path | None = None,
           verboso: bool = True, processos: int = 1) -> pd.DataFrame:
    """Percorre a grade e grava o CSV incrementalmente (em paralelo se pedido)."""
    csv = csv or (OUTPUT_DIR / "varredura_global_consolidada.csv")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pontos = grade.pontos()
    linhas: list[dict] = []

    if processos > 1:
        import multiprocessing as mp
        ctx = mp.get_context("fork")        # cada processo tem os seus globais de `main`
        with ctx.Pool(processos) as pool:
            itens = pool.imap_unordered(_rodar_tupla, pontos, chunksize=4)
            for i, linha in enumerate(itens, 1):
                linhas.append(linha)
                if verboso and (i % 50 == 0 or i == len(pontos)):
                    print(f"[{i:4d}/{len(pontos)}]", flush=True)
                if i % 100 == 0:
                    pd.DataFrame(linhas).to_csv(csv, index=False)
    else:
        for i, (a, h, b) in enumerate(pontos, 1):
            linha = rodar_ponto(a, h, b)
            linhas.append(linha)
            if verboso:
                marca = {"APROVADO": "ok", "ERRO": "ERRO"}.get(linha["status"], "X")
                print(f"[{i:3d}/{len(pontos)}] α={a:4.1f}° h0={h:.2f} b={b:.2f} "
                      f"→ {marca:4s} η={linha['eta_max']:.4f} "
                      f"η_seç={linha.get('eta_secao', float('nan')):.4f} "
                      f"gov_seç={linha.get('gov_secao',''):<14s} "
                      f"V={linha['volume_mlc_m3']:5.1f} m³ "
                      f"({linha['segundos']:.1f} s)", flush=True)
            # Grava a cada ponto: uma varredura longa não pode perder tudo no fim.
            pd.DataFrame(linhas).to_csv(csv, index=False)

    df = pd.DataFrame(linhas).sort_values(["alpha_deg", "h0", "b"]).reset_index(drop=True)
    df.to_csv(csv, index=False)
    if verboso:
        n_ok = int((df["status"] == "APROVADO").sum())
        print(f"\n{n_ok}/{len(df)} geometrias aprovadas → {csv}")
    return df


# Verificações cuja taxa responde à seção da VIGA em si (sem os sistemas de
# contraventamento nem os pilares), usadas no eixo vertical da figura.
CHECKS_DA_VIGA = (
    "eta_cisalhamento", "eta_flexao", "eta_cumeeira", "eta_misula",
    "eta_flambagem", "eta_apoio", "eta_apoio_central", "eta_flexo_comp",
    "eta_balanco_viga", "eta_ELS",
)


def figura(csv: Path | None = None, destino: Path | None = None) -> Path:
    """
    Gera a figura do espaço de geometrias percorrido (volume x taxa).

    Lê o CSV consolidado da varredura e grava o PDF usado na monografia.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    csv = csv or (OUTPUT_DIR / "varredura_global_consolidada.csv")
    destino = destino or (Path(__file__).parent.parent.parent
                          / "tese" / "fig" / "varredura_global.pdf")
    df = pd.read_csv(csv)
    df["eta_viga"] = df[[c for c in CHECKS_DA_VIGA if c in df]].max(axis=1)
    ok = df[df.status == "APROVADO"]
    rep = df[df.status != "APROVADO"]
    ad = ok[(ok.alpha_deg == 10.0) & (ok.h0.round(2) == 1.00)
            & (ok.b == 0.32)].iloc[0]

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.scatter(rep.volume_mlc_m3, rep.eta_viga.clip(upper=1.6), s=9,
               c="#cccccc", marker="x", linewidths=.6, label="Reprovada")
    sc = ax.scatter(ok.volume_mlc_m3, ok.eta_viga, s=11, c=ok.alpha_deg,
                    cmap="viridis", alpha=.85, label="Aprovada")
    ax.axhline(1.0, color="#b22222", lw=1.1, ls="--")
    x_max = float(df.volume_mlc_m3.max()) * 1.03
    ax.text(float(df.volume_mlc_m3.min()) * 0.97, 1.02, r"$\eta = 1{,}0$",
            color="#b22222", fontsize=8, ha="left")
    ax.scatter([ad.volume_mlc_m3], [ad.eta_viga], s=150, facecolors="none",
               edgecolors="#b22222", linewidths=2.0, zorder=5)
    ax.annotate("geometria adotada\n"
                r"$\alpha=10{,}0^\circ$; $h_0=1{,}00$ m; $b=0{,}32$ m",
                xy=(ad.volume_mlc_m3, ad.eta_viga),
                xytext=(ad.volume_mlc_m3 * 1.10, ad.eta_viga - 0.38),
                fontsize=8, color="#b22222",
                arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2))
    cb = fig.colorbar(sc, ax=ax, pad=.015)
    cb.set_label(r"Inclinação do extradorso $\alpha$ (graus)", fontsize=9)
    ax.set_xlabel("Volume de MLC das vigas principais (m³)", fontsize=10)
    ax.set_ylabel("Maior taxa de utilização entre as verificações da viga",
                  fontsize=10)
    ax.set_xlim(float(df.volume_mlc_m3.min()) * 0.95, x_max)
    ax.set_ylim(0, 1.6)
    ax.grid(alpha=.25, lw=.5)
    ax.legend(loc="upper right", fontsize=8, framealpha=.95)
    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=200)
    plt.close(fig)
    print(f"  figura: {destino}")
    return destino


#: Nomes legíveis das verificações da viga, para a tabela da tese.
_NOMES = {
    "eta_cisalhamento": "Cisalhamento", "eta_flexao": "Flexão", "eta_cumeeira": "Cumeeira",
    "eta_misula": "Borda inclinada", "eta_flambagem": "Flambagem lateral",
    "eta_apoio": "Apoio", "eta_apoio_central": "Apoio central",
    "eta_flexo_comp": "Flexo-compressão", "eta_balanco_viga": "Balanço",
    "eta_ELS": "Flecha",
}
MARGENS = (1.00, 0.90, 0.75, 0.60, 0.50, 0.40)
ADOTADA = (10.0, 1.00, 0.32)


def fronteira(df: pd.DataFrame) -> list[dict]:
    """Geometria de menor volume, entre as aprovadas, para cada margem na viga."""
    cols = [c for c in CHECKS_DA_VIGA if c in df]
    ok = df[df.status == "APROVADO"].copy()
    ok["eta_viga"] = ok[cols].max(axis=1)
    ok["gov_viga"] = ok[cols].idxmax(axis=1)
    linhas = []
    for m in MARGENS:
        sel = ok[ok.eta_viga <= m + 1e-9]
        if len(sel):
            linhas.append({"margem": m, **sel.loc[sel.volume_mlc_m3.idxmin()].to_dict()})
    a, h, b = ADOTADA
    ad = ok[(ok.alpha_deg == a) & (ok.h0.round(2) == h) & (ok.b.round(2) == b)]
    if len(ad):
        linhas.append({"margem": None, **ad.iloc[0].to_dict()})
    return linhas


def gerar_tex_fronteira(csv: Path | None = None, destino: Path | None = None) -> Path:
    """tese/tab_fronteira_volume.tex — GERADA (issue 93)."""
    from mlc_projeto.output.formatacao import fmt_eta
    csv = csv or (OUTPUT_DIR / "varredura_global_consolidada.csv")
    destino = destino or (Path(__file__).parent.parent.parent / "tese"
                          / "tab_fronteira_volume.tex")
    df = pd.read_csv(csv)
    v = lambda x, d=2: f"{x:.{d}f}".replace(".", ",")
    corpo = []
    for r in fronteira(df):
        cel = [v(r["alpha_deg"], 1), v(r["h0"]), v(r["b"]), v(r["volume_mlc_m3"], 1),
               _NOMES.get(r["gov_viga"], r["gov_viga"]),
               fmt_eta(r["eta_contraventamento_vertical"]), fmt_eta(r["eta_pilar_contraventado"])]
        if r["margem"] is None:
            corpo.append("\\midrule\n    \\textbf{Adotada} & "
                         + " & ".join(f"\\textbf{{{c}}}" for c in cel) + " \\\\\n")
        else:
            corpo.append(f"    $\\eta \\leq {v(r['margem'])}$ & " + " & ".join(cel) + " \\\\\n")
    n_tot, n_ok = len(df), int((df.status == "APROVADO").sum())
    tex = ("% tab_fronteira_volume.tex — GERADA por mlc_projeto/predim/varredura_global.py "
           f"(issue 93): {n_ok} aprovadas de {n_tot}. NÃO EDITAR À MÃO.\n"
           "\\tabela{Geometria de menor volume para cada política de margem na viga}{\\footnotesize\n"
           "\\begin{tabular}{ccccrccc}\n\\toprule\n"
           "    \\textbf{Margem} & \\textbf{$\\alpha$} & \\textbf{$h_0$} & \\textbf{$b$} &\n"
           "    \\textbf{Volume} & \\textbf{Verificação} & \\textbf{Contrav.} & \\textbf{Pilar} \\\\\n"
           "    \\textbf{na viga} & \\textbf{(graus)} & \\textbf{(m)} & \\textbf{(m)} &\n"
           "    \\textbf{(m\\textsuperscript{3})} & \\textbf{governante} & \\textbf{vertical} & "
           "\\textbf{de canto} \\\\\n\\midrule\n"
           + "".join(corpo)
           + "\\bottomrule\n\\end{tabular}}{Elaborado pelo autor (2026)}{fronteira-volume}{}{}\n")
    destino.write_text(tex, encoding="utf-8")
    print(f"  tabela: {destino}")
    return destino


def _cli() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--teste", action="store_true",
                   help="grade reduzida de 2 pontos, para conferência")
    p.add_argument("-j", "--processos", type=int, default=1)
    p.add_argument("--figura", action="store_true",
                   help="apenas regenerar a figura a partir do CSV existente")
    args = p.parse_args()
    if args.figura:
        figura()
        gerar_tex_fronteira()
        return
    varrer(GRADE_TESTE if args.teste else GRADE_PADRAO, processos=args.processos)
    if not args.teste:
        figura()
        gerar_tex_fronteira()


if __name__ == "__main__":
    _cli()
