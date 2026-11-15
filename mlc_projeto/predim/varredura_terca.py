"""
predim/varredura_terca.py — Dimensionamento da seção das terças (issue 101).

A seção das terças deixa de ser dado de entrada. O espaçamento fica fixo em
s = L/8 (2,53 m), porque define os oito painéis do contraventamento da
cobertura e o comprimento de flambagem lateral da viga (l_1 = s). A seção é
única para todas as terças — correntes, de ponta, de beiral (corda do
diafragma) e as que trabalham como escora nas baías contraventadas —, para não
multiplicar os tipos de peça na fabricação.

Método: para cada seção comercial candidata, o pipeline COMPLETO é executado
(a seção altera o peso próprio, logo todas as ações, e as ligações que a
atravessam), e aceita-se a candidata se

  · o pipeline resulta APROVADO, e
  · cada verificação que depende da seção da terça tem η ≤ ETA_ALVO_TERCA, o
    mesmo critério de folga de 25 % adotado para os pilares.

Adota-se a de menor área; no empate, a mais baixa (menor h). As larguras são as
usuais da MLC (EN 14080, lamelas de 40 mm na altura).

Uso: ``python -m mlc_projeto.predim.varredura_terca`` imprime a tabela.
"""

from __future__ import annotations

import contextlib
import io
import itertools

#: Larguras e alturas candidatas (m) — larguras usuais da MLC; h múltiplo de 40 mm.
LARGURAS = (0.115, 0.14, 0.16, 0.18, 0.20)
ALTURAS = tuple(round(0.04 * k, 2) for k in range(6, 16))     # 0,24 … 0,60

ETA_ALVO_TERCA = 0.75

#: Verificações que dependem da seção da terça (chave em res → rótulo).
CHAVES_TERCA = {
    "terca": "flexão",
    "terca_flexocomp": "biela do diafragma",
    "terca_Qk_conc": "carga concentrada",
    "corda_beiral": "corda do diafragma",
    "balanco_terca": "balanço do oitão",
    "no_contraventamento": "escoras e ligações do nó",
    "ligacao_terca_viga": "ligação terça–viga",
}


def _eta(r: dict) -> float:
    for k in ("eta", "eta_gov"):
        if isinstance(r.get(k), (int, float)):
            return float(r[k])
    return float("nan")


def avaliar(b: float, h: float) -> dict:
    """Executa o pipeline com a terça b × h e devolve as taxas pertinentes."""
    import mlc_projeto.main as M
    orig = (M.B_TERCA, M.H_TERCA, M.gerar_relatorio)
    try:
        M.B_TERCA, M.H_TERCA = b, h
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            res = M._main_impl(rodar_varredura=False, abrir_viz=False)
    except Exception as exc:                       # geometria inviável
        return {"b": b, "h": h, "ok": False, "erro": f"{type(exc).__name__}: {exc}"}
    finally:
        M.B_TERCA, M.H_TERCA, M.gerar_relatorio = orig
    etas = {k: _eta(res[k]) for k in CHAVES_TERCA if k in res}
    eta_t = max(etas.values())
    gov = max(etas, key=etas.get)
    meta = res["meta"]
    ok = meta["status"] == "APROVADO" and eta_t <= ETA_ALVO_TERCA + 1e-9
    return {"b": b, "h": h, "A": b * h, "etas": etas, "eta_terca": eta_t,
            "governa": CHAVES_TERCA[gov], "eta_max": float(meta["eta_max"]),
            "status": meta["status"], "ok": ok}


def varrer(larguras=LARGURAS, alturas=ALTURAS) -> list[dict]:
    """Avalia todas as combinações, em ordem crescente de área."""
    cands = sorted(itertools.product(larguras, alturas), key=lambda bh: (bh[0] * bh[1], bh[1]))
    return [avaliar(b, h) for b, h in cands]


def escolher(linhas: list[dict]) -> dict | None:
    """Menor área aprovada (a lista já vem ordenada por área e altura)."""
    return next((r for r in linhas if r["ok"]), None)


if __name__ == "__main__":
    linhas = varrer()
    for r in linhas:
        if "erro" in r:
            print(f"{r['b']:.3f} × {r['h']:.2f}  erro: {r['erro'][:70]}")
            continue
        print(f"{r['b']:.3f} × {r['h']:.2f}  A={r['A']:.4f}  η_terça={r['eta_terca']:.3f} "
              f"({r['governa']})  η_max={r['eta_max']:.3f}  {r['status']}"
              f"{'  ← ok' if r['ok'] else ''}")
    esc = escolher(linhas)
    print("\nAdotada:", f"{esc['b']:.3f} × {esc['h']:.2f} m" if esc else "nenhuma")
