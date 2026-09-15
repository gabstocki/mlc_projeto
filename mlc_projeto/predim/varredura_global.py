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
    python -m mlc_projeto.predim.varredura_global --teste    # 3 pontos

Saída:
    output/varredura_global_pipeline.csv
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
    "flexo_comp", "ELS", "abertura_springings", "icamento",
    "L1", "L1c", "fendilhamento_L1", "fendilhamento_L1c",
    "ruptura_bloco_L1", "ruptura_bloco_L1c", "chapa_aco_L1", "chapa_aco_L1c",
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
    alpha_deg=tuple(8.0 + 0.5 * i for i in range(17)),        # 8,0°…16,0°
    h0=tuple(0.70 + 0.05 * i for i in range(11)),             # 0,70…1,20 m
    b=(0.28, 0.30, 0.32, 0.34, 0.36),
)

GRADE_TESTE = Grade(alpha_deg=(10.0,), h0=(0.90, 1.00), b=(0.32,))


def volume_mlc_m3(alpha_deg: float, h0: float, b: float,
                  n_vigas: int = 18) -> float:
    """
    Volume total de MLC das vigas principais (m³).

    Integra A(x) ao longo do vão com a própria geometria do pipeline, em vez
    de usar a altura média, para não presumir linearidade da seção.
    `n_vigas` = 2 vigas por pórtico × 9 pórticos.
    """
    geo = GeometriaViga(L=pipeline.GEO_PARAMS["L"], h0=h0,
                        alpha_deg=alpha_deg, b=b, n_pts=401)
    return float(trapezoid(geo.A(geo.x), geo.x)) * n_vigas


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

    registro.update(
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


def varrer(grade: Grade = GRADE_PADRAO,
           csv: Path | None = None,
           verboso: bool = True) -> pd.DataFrame:
    """Percorre a grade e grava o CSV incrementalmente."""
    csv = csv or (OUTPUT_DIR / "varredura_global_pipeline.csv")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pontos = grade.pontos()
    linhas: list[dict] = []

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

    df = pd.DataFrame(linhas)
    if verboso:
        n_ok = int((df["status"] == "APROVADO").sum())
        print(f"\n{n_ok}/{len(df)} geometrias aprovadas → {csv}")
    return df


# Verificações cuja taxa responde à seção da VIGA em si (sem os sistemas de
# contraventamento nem os pilares), usadas no eixo vertical da figura.
CHECKS_DA_VIGA = (
    "eta_cisalhamento", "eta_flexao", "eta_cumeeira", "eta_misula",
    "eta_flambagem", "eta_apoio", "eta_ELS",
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
    df["eta_viga"] = df[list(CHECKS_DA_VIGA)].max(axis=1)
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
    ax.text(345, 1.02, r"$\eta = 1{,}0$", color="#b22222",
            fontsize=8, ha="right")
    ax.scatter([ad.volume_mlc_m3], [ad.eta_viga], s=150, facecolors="none",
               edgecolors="#b22222", linewidths=2.0, zorder=5)
    ax.annotate("geometria adotada\n"
                r"$\alpha=10{,}0^\circ$; $h_0=1{,}00$ m; $b=0{,}32$ m",
                xy=(ad.volume_mlc_m3, ad.eta_viga), xytext=(258, 0.70),
                fontsize=8, color="#b22222",
                arrowprops=dict(arrowstyle="->", color="#b22222", lw=1.2))
    cb = fig.colorbar(sc, ax=ax, pad=.015)
    cb.set_label(r"Inclinação do extradorso $\alpha$ (graus)", fontsize=9)
    ax.set_xlabel("Volume de MLC das vigas principais (m³)", fontsize=10)
    ax.set_ylabel("Maior taxa de utilização entre as verificações da viga",
                  fontsize=10)
    ax.set_xlim(90, 355)
    ax.set_ylim(0, 1.6)
    ax.grid(alpha=.25, lw=.5)
    ax.legend(loc="upper right", fontsize=8, framealpha=.95)
    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino, dpi=200)
    plt.close(fig)
    print(f"  figura: {destino}")
    return destino


def _cli() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--teste", action="store_true",
                   help="grade reduzida de 2 pontos, para conferência")
    p.add_argument("--figura", action="store_true",
                   help="apenas regenerar a figura a partir do CSV existente")
    args = p.parse_args()
    if args.figura:
        figura()
        return
    varrer(GRADE_TESTE if args.teste else GRADE_PADRAO)


if __name__ == "__main__":
    _cli()
