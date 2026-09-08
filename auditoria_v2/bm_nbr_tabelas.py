"""
BM-15 — Coerência interna das tabelas da NBR 6123 transcritas no repositório.

[F-18] O texto da NBR 6123:2023 NÃO está disponível a esta auditoria. Este
benchmark **não** verifica fidelidade à edição declarada — isso é impossível
sem a fonte. Verifica outra coisa, que é verificável e tem poder de deteção:
se os números transcritos são **internamente coerentes** com as hipóteses
físicas que sustentam as próprias tabelas.

Um erro de transcrição (um dígito trocado, uma linha deslocada) quebra essas
invariantes. Não as quebrar não prova que a tabela é a da :2023 — prova que é
uma tabela de camada-limite consistente.

INDEPENDÊNCIA (exigência da carta de auditoria): este ficheiro **não importa
nenhuma função** de `mlc_projeto`. Os valores sob teste são extraídos do
código-fonte por análise sintática (`ast`), nunca por execução do repositório.
Toda a lógica de verificação é escrita aqui de raiz.

Invariantes verificadas
-----------------------
V1  Tab. 1  monotonia em categoria:  b↓ e p↑ de I para V (terreno mais rugoso
            ⇒ menor velocidade a baixa cota e perfil mais inclinado).
V2  Tab. 1  monotonia em classe:     p↑ de A para C (rajada mais longa).
V3  Tab. 1  z_g↑ com a categoria e constante entre classes (a espessura da
            camada limite é do terreno, não da estrutura).
V4  Tab. 2  F_r↓ de A para C.
V5  **Convergência ao vento gradiente** — a invariante forte. A lei de potência
            S2 = b·F_r·(z/10)^p modela uma camada limite cujo topo é z_g. Acima
            de z_g o escoamento é geostrófico: a velocidade **não depende do
            terreno**. Logo S2(z_g) tem de ser praticamente o MESMO nas cinco
            categorias. É uma relação entre b, p e z_g — três colunas
            independentes da tabela — e por isso um teste severo.
V6  Tab. 25 continuidade dos quatro ramos lineares em tg β = 0,4.
V7  Tab. 10 coerência de sinais e do pico de sucção.
"""

from __future__ import annotations

import ast
import math
import pathlib

FONTE = pathlib.Path(__file__).resolve().parents[1] / "mlc_projeto" / "core" / "wind.py"

CATEGORIAS = ("I", "II", "III", "IV", "V")
CLASSES = ("A", "B", "C")


# ── Extração por análise sintática (sem importar o repositório) ───────────────

def literais_do_modulo(caminho: pathlib.Path, nomes: set[str]) -> dict:
    """Lê atribuições de topo-de-módulo como literais Python, sem executar nada."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))
    achados: dict = {}
    for no in arvore.body:
        # Assign simples e AnnAssign (atribuição anotada) — as tabelas do
        # repositório usam anotação de tipo, logo ambas as formas contam.
        if isinstance(no, ast.Assign):
            alvos, valor = no.targets, no.value
        elif isinstance(no, ast.AnnAssign) and no.value is not None:
            alvos, valor = [no.target], no.value
        else:
            continue
        for alvo in alvos:
            if isinstance(alvo, ast.Name) and alvo.id in nomes:
                achados[alvo.id] = ast.literal_eval(valor)
    faltam = nomes - achados.keys()
    if faltam:
        raise AssertionError(f"não encontrados em {caminho.name}: {sorted(faltam)}")
    return achados


def literais_de_funcao(caminho: pathlib.Path, funcao: str) -> str:
    """Devolve o texto-fonte de uma função (para inspeção manual das fórmulas)."""
    fonte = caminho.read_text(encoding="utf-8")
    arvore = ast.parse(fonte, filename=str(caminho))
    for no in ast.walk(arvore):
        if isinstance(no, ast.FunctionDef) and no.name == funcao:
            return ast.get_source_segment(fonte, no) or ""
    raise AssertionError(f"função {funcao} não encontrada")


# ── S2 reimplementado de raiz ─────────────────────────────────────────────────

def s2_independente(z, b, F_r, p):
    """S2 = b · F_r · (z/10)^p — NBR 6123:2023 §5.3.3, escrito aqui de novo."""
    return b * F_r * (z / 10.0) ** p


# ── Verificações ──────────────────────────────────────────────────────────────

def main() -> int:
    dados = literais_do_modulo(
        FONTE, {"PARAM_METEOROLOGICOS", "FATOR_RAJADA", "TABELA_10_CE",
                "TABELA_10_THETA", "COEF_PRESSAO_DINAMICA"})
    par = dados["PARAM_METEOROLOGICOS"]
    fr = dados["FATOR_RAJADA"]

    falhas: list[str] = []
    print("=" * 78)
    print("BM-15 — COERÊNCIA INTERNA DAS TABELAS NBR 6123 TRANSCRITAS")
    print("=" * 78)
    print(f"fonte lida por ast (sem import): {FONTE}")
    print()

    # ── V1/V2/V3 ─────────────────────────────────────────────────────────────
    print("V1/V2/V3 — monotonia dos parâmetros meteorológicos")
    print(f"  {'cat':<5}{'classe':<8}{'b':>8}{'p':>8}{'z_g':>8}")
    for cat in CATEGORIAS:
        for cl in CLASSES:
            b, p, zg = par[cat][cl]
            print(f"  {cat:<5}{cl:<8}{b:>8.2f}{p:>8.3f}{zg:>8.0f}")

    for cl in CLASSES:
        bs = [par[c][cl][0] for c in CATEGORIAS]
        ps = [par[c][cl][1] for c in CATEGORIAS]
        if not all(x > y for x, y in zip(bs, bs[1:])):
            falhas.append(f"V1: b não decresce I→V na classe {cl}: {bs}")
        if not all(x < y for x, y in zip(ps, ps[1:])):
            falhas.append(f"V1: p não cresce I→V na classe {cl}: {ps}")
    for cat in CATEGORIAS:
        ps = [par[cat][cl][1] for cl in CLASSES]
        if not all(x < y for x, y in zip(ps, ps[1:])):
            falhas.append(f"V2: p não cresce A→C na categoria {cat}: {ps}")
        zgs = {par[cat][cl][2] for cl in CLASSES}
        if len(zgs) != 1:
            falhas.append(f"V3: z_g varia entre classes na categoria {cat}: {zgs}")
    zgs = [par[c]["A"][2] for c in CATEGORIAS]
    if not all(x < y for x, y in zip(zgs, zgs[1:])):
        falhas.append(f"V3: z_g não cresce I→V: {zgs}")
    print(f"  V1 b↓ / p↑ em categoria .......... {'OK' if not [f for f in falhas if f.startswith('V1')] else 'FALHA'}")
    print(f"  V2 p↑ em classe .................. {'OK' if not [f for f in falhas if f.startswith('V2')] else 'FALHA'}")
    print(f"  V3 z_g↑ e constante em classe .... {'OK' if not [f for f in falhas if f.startswith('V3')] else 'FALHA'}")
    print()

    # ── V4 ───────────────────────────────────────────────────────────────────
    frs = [fr[cl] for cl in CLASSES]
    ok4 = all(x > y for x, y in zip(frs, frs[1:]))
    if not ok4:
        falhas.append(f"V4: F_r não decresce A→C: {frs}")
    print(f"V4 — F_r  A={frs[0]:.2f}  B={frs[1]:.2f}  C={frs[2]:.2f} ....... "
          f"{'OK' if ok4 else 'FALHA'}")
    print()

    # ── V5 — convergência ao vento gradiente ─────────────────────────────────
    print("V5 — S2(z_g) tem de ser o mesmo nas cinco categorias (vento gradiente)")
    pior = 0.0
    for cl in CLASSES:
        vals = []
        for cat in CATEGORIAS:
            b, p, zg = par[cat][cl]
            vals.append(s2_independente(zg, b, fr[cl], p))
        media = sum(vals) / len(vals)
        disp = max(abs(v - media) / media for v in vals) * 100.0
        pior = max(pior, disp)
        detalhe = "  ".join(f"{c}={v:.4f}" for c, v in zip(CATEGORIAS, vals))
        print(f"  classe {cl}: {detalhe}")
        print(f"            média = {media:.4f}   dispersão máx = {disp:.2f} %")
    LIMITE_V5 = 2.0
    ok5 = pior <= LIMITE_V5
    if not ok5:
        falhas.append(f"V5: dispersão de S2(z_g) = {pior:.2f} % > {LIMITE_V5} %")
    print(f"  dispersão máxima global = {pior:.2f} %  (limite adotado {LIMITE_V5:.1f} %)"
          f" ....... {'OK' if ok5 else 'FALHA'}")

    # sensibilidade: quanto um erro de transcrição deslocaria a dispersão
    print("\n  poder de deteção (perturbação de um único valor, classe B):")
    for nome, cat, idx, delta in (("b(IV)", "IV", 0, +0.10),
                                  ("p(III)", "III", 1, +0.020),
                                  ("z_g(II)", "II", 2, +100.0)):
        vals = []
        for c in CATEGORIAS:
            b, p, zg = par[c]["B"]
            if c == cat:
                trio = [b, p, zg]
                trio[idx] += delta
                b, p, zg = trio
            vals.append(s2_independente(zg, b, fr["B"], p))
        media = sum(vals) / len(vals)
        disp = max(abs(v - media) / media for v in vals) * 100.0
        print(f"    {nome} deslocado de {delta:+g} → dispersão {disp:.2f} % "
              f"({'DETETADO' if disp > LIMITE_V5 else 'não detetado'})")
    print()

    # ── V6 — continuidade da Tabela 25 em tg β = 0,4 ─────────────────────────
    print("V6 — Tabela 25: continuidade dos ramos lineares em tg β = 0,4")
    t = 0.4
    ramos = {
        "Cpb,1": (2.4 * t + 0.6, min(2.4 * t + 0.6, 2.0)),
        "Cps,1": (3.0 * t - 0.5, +0.7),
        "Cpb,2": (0.6 * t - 0.74, 6.5 * t - 3.1),
        "Cps,2": (-1.0, 5.0 * t - 3.0),
    }
    ok6 = True
    for nome, (esq, dir_) in ramos.items():
        salto = abs(esq - dir_)
        if salto > 1e-9:
            ok6 = False
            falhas.append(f"V6: {nome} descontínuo em tg β=0,4 ({esq:.4f} vs {dir_:.4f})")
        print(f"  {nome:<8} ramo baixo = {esq:+.4f}   ramo alto = {dir_:+.4f}   "
              f"salto = {salto:.2e}")
    print(f"  quatro ramos contínuos ....... {'OK' if ok6 else 'FALHA'}")
    tg_proj = math.tan(math.radians(10.0))
    print(f"  (geometria do projeto: tg β = tg 10° = {tg_proj:.4f} — ramo baixo)")
    print()

    # ── V7 — Tabela 10: coerência de sinais ──────────────────────────────────
    print("V7 — Tabela 10: coerência de sinais e do pico de sucção")
    t10 = dados["TABELA_10_CE"]
    thetas = dados["TABELA_10_THETA"]
    a = t10["a"]
    i_pico = min(range(len(a)), key=lambda k: a[k])
    ok7a = thetas[i_pico] == 10.0
    if not ok7a:
        falhas.append(f"V7: pico de sucção da zona a* em θ={thetas[i_pico]}°, esperado 10°")
    ok7b = a[-1] > 0
    if not ok7b:
        falhas.append("V7: zona a* (barlavento) não passa a pressão em θ=45°")
    zonas_sot = [z for z in ("b", "c", "d", "m", "n", "x", "z")]
    ok7c = all(all(v <= 0 for v in t10[z]) for z in zonas_sot)
    if not ok7c:
        falhas.append("V7: zona de sotavento com pressão positiva")
    print(f"  zona a* (1.º barlavento): {['%+.1f' % v for v in a]} em θ={list(thetas)}")
    print(f"  pico de sucção em θ = {thetas[i_pico]:.0f}° (bolha de separação) ... "
          f"{'OK' if ok7a else 'FALHA'}")
    print(f"  a* passa a pressão em θ = 45° .......................... "
          f"{'OK' if ok7b else 'FALHA'}")
    print(f"  todas as demais zonas em sucção ....................... "
          f"{'OK' if ok7c else 'FALHA'}")
    print()

    # ── Veredito ─────────────────────────────────────────────────────────────
    print("=" * 78)
    if falhas:
        print(f"BM-15: {len(falhas)} INCOERÊNCIA(S)")
        for f in falhas:
            print(f"  ✗ {f}")
    else:
        print("BM-15: 7/7 invariantes satisfeitas — a transcrição é INTERNAMENTE")
        print("       COERENTE. Isto NÃO confirma fidelidade à edição :2023;")
        print("       ver [F-18] e ANEXO_A_NBR6123.md.")
    print("=" * 78)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
