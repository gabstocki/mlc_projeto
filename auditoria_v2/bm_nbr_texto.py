"""
BM-17 — Verificação dos valores NBR 6123 contra o TEXTO da norma.

[F-18] Supera o BM-15. Aquele só podia testar a coerência interna da
transcrição, porque a auditoria julgava não ter a norma. Tem: `NBR6123-2023.pdf`
está na raiz do projeto — deliberadamente FORA do git (ver `.gitignore`: obra
protegida, remoto público). O inventário da auditoria percorreu os `.py` e não
viu o resto da árvore.

Este benchmark **lê o PDF** e compara, valor a valor, com o que o repositório
implementa. Não reproduz a norma em lado nenhum: extrai, compara, descarta.
Sem o PDF, aborta com instrução — nunca degrada para uma verificação mais fraca
sem o dizer.

A verificação mais forte é a da **Tabela 3**: a norma dá o S2 tabelado E a
fórmula de 5.3.3. Confrontar uma com a outra em ~280 células testa `bm`, `p`,
`z_g`, `F_r` e a regra especial da Categoria V de uma só vez, contra dados que
não saíram do repositório.

Uso:  python auditoria_v2/bm_nbr_texto.py
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PDF = RAIZ / "NBR6123-2023.pdf"

CATS = ("I", "II", "III", "IV", "V")
CLASSES = ("A", "B", "C")


def texto_da_norma() -> str:
    if not PDF.exists():
        sys.exit(
            f"BM-17 ABORTADO: {PDF.name} não está em {RAIZ}.\n"
            f"É uma cópia licenciada e não é versionada (ver .gitignore).\n"
            f"Coloque-a na raiz do projeto para correr esta verificação."
        )
    try:
        proc = subprocess.run(["pdftotext", "-layout", str(PDF), "-"],
                              capture_output=True, text=True, check=True)
    except FileNotFoundError:
        sys.exit("BM-17 ABORTADO: 'pdftotext' não instalado (poppler-utils).")
    return proc.stdout


def num(s: str) -> float:
    return float(s.replace(",", "."))


# ── Extratores ────────────────────────────────────────────────────────────────

def extrair_tabela_1(txt: str) -> dict:
    """
    {cat: {classe: (bm, p, zg)}} a partir da Tabela 1 da norma.

    O layout intercala as linhas: `bm ...`, depois `<CAT> <zg>`, depois `p ...`,
    e repete por categoria. Lê-se sequencialmente, que é robusto à indentação.
    """
    i = txt.rindex("Tabela 1 – Parâmetros meteorológicos")
    bloco = txt[i:i + 1800]
    bms, ps, cats = [], [], []
    for linha in bloco.splitlines():
        if m := re.match(r"^\s*bm\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$", linha):
            bms.append([num(m.group(k)) for k in (1, 2, 3)])
        elif m := re.match(r"^\s*p\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$", linha):
            ps.append([num(m.group(k)) for k in (1, 2, 3)])
        elif m := re.match(r"^\s*(I{1,3}|IV|V)\s+(\d{3})\s*$", linha):
            cats.append((m.group(1), float(m.group(2))))
    assert len(bms) == len(ps) == len(cats) == 5, (
        f"Tabela 1 mal lida: {len(bms)} bm, {len(ps)} p, {len(cats)} categorias")
    assert [c for c, _ in cats] == list(CATS), f"ordem inesperada: {cats}"
    return {
        cat: {cl: (bms[k][j], ps[k][j], zg) for j, cl in enumerate(CLASSES)}
        for k, (cat, zg) in enumerate(cats)
    }


def extrair_tabela_2(txt: str) -> dict:
    """F_r por classe. Na norma o rótulo 'Fr' e as classes estão no cabeçalho e
    os três valores vêm na linha seguinte."""
    i = txt.rindex("Tabela 2 – Fator de rajada")
    bloco = txt[i:i + 500]
    for linha in bloco.splitlines():
        if m := re.match(r"^\s*([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*$", linha):
            return {cl: num(m.group(k + 1)) for k, cl in enumerate(CLASSES)}
    raise AssertionError("Tabela 2 não lida")


def extrair_tabela_3(txt: str, zg_por_cat: dict) -> list[tuple[float, dict]]:
    """[(z, {(cat,classe): S2})] — as células omitidas acima de z_g ficam de fora."""
    i = txt.rindex("Tabela 3 – Fator S2")
    bloco = txt[i:i + 4000]
    linhas: list[tuple[float, dict]] = []
    for linha in bloco.splitlines():
        m = re.match(r"^\s*(<\s*5|\d{1,3})\s+((?:[\d,]+\s+){2,14}[\d,]+)\s*$", linha)
        if not m:
            continue
        z = 5.0 if m.group(1).startswith("<") else float(m.group(1))
        vals = [num(v) for v in m.group(2).split()]
        # as categorias presentes são as de z_g >= z (a norma trunca o resto)
        presentes = [c for c in CATS if zg_por_cat[c] >= z]
        if len(vals) != 3 * len(presentes):
            continue
        celulas = {}
        for k, cat in enumerate(presentes):
            for j, cl in enumerate(CLASSES):
                celulas[(cat, cl)] = vals[3 * k + j]
        linhas.append((z, celulas))
    assert len(linhas) >= 20, f"Tabela 3: só {len(linhas)} linhas lidas"
    return linhas


def extrair_tabela_10(txt: str) -> dict:
    i = txt.rindex("Tabela 10 – Coeficientes de pressão")
    bloco = txt[i:i + 2500]
    zonas = ("a", "b", "c", "d", "m", "n", "x", "z")
    tab: dict = {z: [] for z in zonas}
    thetas = []
    for linha in bloco.splitlines():
        m = re.match(r"^\s*(5|10|20|30|45)°\s+(?:0°\s+)?((?:[+-][\d,]+\s+){7}[+-][\d,]+)",
                     linha)
        if not m:
            continue
        thetas.append(float(m.group(1)))
        for zona, v in zip(zonas, m.group(2).split()):
            tab[zona].append(num(v))
    assert thetas == [5.0, 10.0, 20.0, 30.0, 45.0], f"Tabela 10: θ lidos {thetas}"
    return {z: tuple(v) for z, v in tab.items()}


def extrair_tabela_25(txt: str) -> dict:
    i = txt.rindex("Tabela 25 – Coeficientes de pressão em coberturas isoladas a duas")
    bloco = txt[i:i + 1200]
    mb = re.search(r"cpb\s+(.+)$", bloco, re.M)
    ms = re.search(r"cps\s+(.+)$", bloco, re.M)
    assert mb and ms, "Tabela 25 não lida"
    return {"cpb": mb.group(1).strip(), "cps": ms.group(1).strip()}


def frase(txt: str, alvo: str) -> bool:
    """A norma contém esta frase (normalizando espaços)?"""
    n = " ".join(txt.split())
    return " ".join(alvo.split()) in n


# ── Verificação ───────────────────────────────────────────────────────────────

def main() -> int:
    txt = texto_da_norma()
    sys.path.insert(0, str(RAIZ))
    from mlc_projeto.core import wind as w
    from mlc_projeto.core.normativo import NDP_SOURCE

    falhas: list[str] = []
    avisos: list[str] = []
    print("=" * 78)
    print("BM-17 — VALORES DO REPOSITÓRIO CONTRA O TEXTO DA ABNT NBR 6123:2023")
    print("=" * 78)
    print(f"fonte: {PDF.name} ({PDF.stat().st_size/1e6:.1f} MB, "
          f"{txt.count(chr(12))+1} páginas de texto)\n")

    # ── Tabela 1 ─────────────────────────────────────────────────────────────
    t1 = extrair_tabela_1(txt)
    n_ok = 0
    for cat in CATS:
        for cl in CLASSES:
            for k, nome in enumerate(("bm", "p", "z_g")):
                norma = t1[cat][k if k < 2 else 2][k] if False else t1[cat][cl][k]
                codigo = w.PARAM_METEOROLOGICOS[cat][cl][k]
                if abs(norma - codigo) > 1e-9:
                    falhas.append(f"Tab.1 {cat}/{cl} {nome}: norma {norma} ≠ código {codigo}")
                else:
                    n_ok += 1
    print(f"Tabela 1 — parâmetros meteorológicos ... {n_ok}/45 valores conferem")

    # ── Tabela 2 ─────────────────────────────────────────────────────────────
    t2 = extrair_tabela_2(txt)
    n_ok = sum(1 for cl in CLASSES if abs(t2[cl] - w.FATOR_RAJADA[cl]) < 1e-9)
    for cl in CLASSES:
        if abs(t2[cl] - w.FATOR_RAJADA[cl]) >= 1e-9:
            falhas.append(f"Tab.2 F_r({cl}): norma {t2[cl]} ≠ código {w.FATOR_RAJADA[cl]}")
    print(f"Tabela 2 — fator de rajada ............. {n_ok}/3 valores conferem")

    # ── Tabela 3 — a verificação forte ───────────────────────────────────────
    zg = {c: t1[c]["A"][2] for c in CATS}
    t3 = extrair_tabela_3(txt, zg)
    n_cel = pior = 0
    pior_cel = ""
    for z, celulas in t3:
        for (cat, cl), s2_norma in celulas.items():
            b, p, _ = w.PARAM_METEOROLOGICOS[cat][cl]
            z_ef = 10.0 if (cat == "V" and z < 10.0) else z   # regra da Cat. V
            s2_form = b * w.FATOR_RAJADA[cl] * (z_ef / 10.0) ** p
            d = abs(s2_form - s2_norma)
            n_cel += 1
            if d > pior:
                pior, pior_cel = d, f"z={z:g} {cat}/{cl} (tab {s2_norma}, fórm {s2_form:.4f})"
            if d > 0.0051:
                falhas.append(f"Tab.3 z={z:g} {cat}/{cl}: tabela {s2_norma} vs "
                              f"fórmula {s2_form:.4f} (Δ={d:.4f})")
    print(f"Tabela 3 — S2 tabelado vs fórmula 5.3.3  {n_cel} células, "
          f"pior Δ = {pior:.4f} (≤ 0,005 = arredondamento)")
    print(f"           pior célula: {pior_cel}")

    # o código, e não só a fórmula
    pv = w.ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                           L=20.25, H1=1.79, h=7.0, dist_portico=5.75)
    alvo = next(v for z, c in t3 if z == 10.0 for k, v in c.items() if k == ("IV", "B"))
    s2_cod = pv.S2_em(10.0)
    if abs(s2_cod - alvo) > 0.0051:
        falhas.append(f"S2_em(10) do código = {s2_cod:.4f} vs Tab.3 IV/B = {alvo}")
    print(f"           S2_em(10) do código = {s2_cod:.4f}  |  Tab.3 IV/B = {alvo}")

    # ── Tabela 10 ────────────────────────────────────────────────────────────
    t10 = extrair_tabela_10(txt)
    n_ok = 0
    for zona, vals in t10.items():
        cod = w.TABELA_10_CE[zona]
        for k, (a, b_) in enumerate(zip(vals, cod)):
            if abs(a - b_) > 1e-9:
                falhas.append(f"Tab.10 zona {zona}* θ={w.TABELA_10_THETA[k]:g}°: "
                              f"norma {a} ≠ código {b_}")
            else:
                n_ok += 1
    print(f"Tabela 10 — telhados múltiplos ......... {n_ok}/40 valores conferem")

    # ── Tabela 25 ────────────────────────────────────────────────────────────
    t25 = extrair_tabela_25(txt)
    esperado_cpb = "2,4 tgθ + 0,6      2,4 tgθ + 0,6 ≤ 2,0   0,6 tgθ - 0,74        6,5 tgθ - 3,1"
    ok25 = True
    for termo in ("2,4 tg", "0,6", "≤ 2,0", "0,6 tg", "- 0,74", "6,5 tg", "- 3,1"):
        if termo not in t25["cpb"]:
            ok25 = False
            falhas.append(f"Tab.25 cpb: termo «{termo}» ausente na norma lida")
    for termo in ("3,0 tg", "- 0,5", "+0,7", "-1,0", "5,0 tg", "- 3,0"):
        if termo not in t25["cps"]:
            ok25 = False
            falhas.append(f"Tab.25 cps: termo «{termo}» ausente na norma lida")
    # confronto numérico das oito expressões
    n_amostras = 0
    for tg in [round(0.07 + k * 0.01, 4) for k in range(54)]:
        c = w.coeficientes_tabela25(tg)
        if tg <= 0.4:
            ref = {"C1": {"Cpb": 2.4*tg+0.6, "Cps": 3.0*tg-0.5},
                   "C2": {"Cpb": 0.6*tg-0.74, "Cps": -1.0}}
        else:
            ref = {"C1": {"Cpb": min(2.4*tg+0.6, 2.0), "Cps": 0.7},
                   "C2": {"Cpb": 6.5*tg-3.1, "Cps": 5.0*tg-3.0}}
        for caso in ("C1", "C2"):
            for comp in ("Cpb", "Cps"):
                n_amostras += 1
                if abs(c[caso][comp] - ref[caso][comp]) > 1e-9:
                    falhas.append(f"Tab.25 {caso}/{comp} em tgθ={tg:.2f}: "
                                  f"código {c[caso][comp]} ≠ norma {ref[caso][comp]}")
    print(f"Tabela 25 — cobertura isolada .......... 8 expressões, "
          f"{n_amostras} amostras {'conferem' if ok25 else 'COM FALHA'}")

    # ── Cláusulas de texto ───────────────────────────────────────────────────
    print("\nCláusulas verificadas no texto:")
    clausulas = [
        ("§4.2 c)  q = 0,613 Vk²",
         "q = 0,613 Vk2, expresso em Newton por metro ao quadrado",
         abs(w.COEF_PRESSAO_DINAMICA - 0.613e-3) < 1e-12),
        ("§5.2 a)  S1 = 1,0 em terreno plano",
         "terreno plano ou fracamente acidentado",
         abs(NDP_SOURCE["S1"].valor - 1.0) < 1e-12),
        ("§7.2.1   domínio da Tab. 25",
         "Coberturas a duas águas (ver a Tabela 25):            0,07 ≤ tg θ ≤ 0,6        h ≥ 0,5 ℓ2",
         True),
        ("§7.2.1   cpi de obstrução",
         "com cpi = +0,8, para obstruções na borda de sotavento, e com cpi = - 0,3, "
         "para obstruções na borda de barlavento",
         w.CPI_OBSTRUCAO_SOTAVENTO == 0.8 and w.CPI_OBSTRUCAO_BARLAVENTO == -0.3),
        ("§7.2.2   Ft = 0,5 q a b",
         "Ft = 0,5 q a b",
         abs(w.COEF_ATRITO_COBERTURA_ISOLADA - 0.5) < 1e-12),
        ("§7.2.2   engloba as duas faces",
         "Estas forças englobam a ação do vento sobre as duas faces da cobertura",
         True),
        ("§7.2.6   cp = ±2,0 por elemento",
         "Cada elemento de vedação deve ser calculado com cp = ±2,0",
         True),
        ("Tab.10   atrito já incluído em α=0°",
         "para α = 0°, as forças horizontais de atrito já estão consideradas nos "
         "valores da Tabela 10",
         True),
    ]
    for rotulo, alvo_txt, valor_bate in clausulas:
        na_norma = frase(txt, alvo_txt)
        estado = "OK" if (na_norma and valor_bate) else "FALHA"
        if not na_norma:
            falhas.append(f"{rotulo}: frase não encontrada no texto da norma")
        elif not valor_bate:
            falhas.append(f"{rotulo}: texto confere mas o valor do código não")
        print(f"  [{estado:>5}] {rotulo}")

    # ── S3: Tabela 4 ─────────────────────────────────────────────────────────
    i4 = txt.rindex("Tabela 4 – Valores mínimos do fator estatístico S3")
    bloco4 = txt[i4:i4 + 2500]
    m2 = re.search(r"^\s*2\s.*?([\d,]+)\s+75\s*$", bloco4, re.M | re.S)
    s3_g2 = num(re.search(r"([\d,]+)\s+75", bloco4).group(1))
    s3_g3 = num(re.search(r"([\d,]+)\s+50", bloco4).group(1))
    s3_cod = NDP_SOURCE["S3"].valor
    nota_cod = NDP_SOURCE["S3"].nota
    print(f"\nTabela 4 — S3: grupo 2 → {s3_g2}   grupo 3 → {s3_g3}")
    print(f"           código: S3 = {s3_cod} rotulado «{nota_cod}»")
    if "grupo 2" in nota_cod.lower() and abs(s3_cod - s3_g2) > 1e-9:
        avisos.append(
            f"S3 = {s3_cod} é o valor do GRUPO 3 ({s3_g3}), mas está rotulado "
            f"«{nota_cod}». O grupo 2 exige S3 = {s3_g2} — o que elevaria toda a "
            f"ação de vento em {(s3_g2/s3_cod)**2 - 1:+.1%}. Ou o rótulo está "
            f"errado (defeito de documentação) ou a classificação está errada "
            f"(defeito NÃO CONSERVATIVO). Só o projetista decide.")

    # ── C_a do pilar ─────────────────────────────────────────────────────────
    tem_t13_cilindrica = frase(
        txt, "Tabela 13 – Distribuição das pressões externas em edificações "
             "cilíndricas de seção circular")
    tem_63_interna = frase(txt, "6.3 Pressões internas em edificações")
    if tem_t13_cilindrica and tem_63_interna:
        avisos.append(
            f"C_a = {w.CA_PILAR_RET} citado como «§6.3 / Tab. 13» (wind.py:507-509). "
            f"Na :2023, §6.3 é «Pressões internas em edificações» e a Tab. 13 é "
            f"«edificações cilíndricas de seção circular». Nenhuma das duas trata "
            f"do arrasto de uma barra prismática livre — isso é §8.1.1 (Tab. 26, "
            f"Cx/Cy) com o fator K de comprimento finito (Tab. 28). CITAÇÃO ERRADA; "
            f"o valor tem de ser refeito por essa rota.")

    # ── Veredito ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 78)
    if falhas:
        print(f"BM-17: {len(falhas)} DIVERGÊNCIA(S) entre o código e a norma")
        for f in falhas:
            print(f"  ✗ {f}")
    else:
        print("BM-17: todos os valores confrontados CONFEREM com o texto da")
        print("       ABNT NBR 6123:2023.")
    if avisos:
        print(f"\n  {len(avisos)} ACHADO(S) que a comparação numérica não apanha:")
        for a in avisos:
            print(f"  ⚠ {a}")
    print("=" * 78)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
