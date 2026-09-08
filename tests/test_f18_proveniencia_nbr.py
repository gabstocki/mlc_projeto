"""
F-18 — Proveniência das tabelas da NBR 6123 declarada e auditável.

O achado F-18 não é um erro de cálculo: é a constatação de que **nenhuma tabela
da NBR 6123:2023 está reproduzida com citação verificável no repositório**. Os
números podem estar certos — não é possível demonstrá-lo com o material
disponível.

Estes testes não podem fechar o achado (só o texto da norma o fecha). Fazem
duas coisas que estão ao alcance do código:

1. **Tornam a lacuna enumerável e legível por máquina.** Cada valor de origem
   NBR fica registado no `CATALOGO_NBR6123` com a cláusula alegada, o local no
   código e o estado de confirmação. Um valor NBR novo que entre no projeto sem
   registo faz falhar a suíte — a lacuna não pode voltar a diluir-se.

2. **Fixam a coerência interna já verificada** (BM-15). Isto não prova
   fidelidade à edição :2023; prova que a transcrição é uma tabela de
   camada-limite consistente e que uma edição futura não a degrada em silêncio.
"""

import math

import pytest

from mlc_projeto.core import normativo as nz
from mlc_projeto.core import wind as w


# ── 1. O catálogo existe e é bem formado ──────────────────────────────────────

def test_catalogo_existe_e_nao_esta_vazio():
    assert hasattr(nz, "CATALOGO_NBR6123"), "F-18 exige um catálogo de proveniência"
    assert len(nz.CATALOGO_NBR6123) >= 8


def test_todo_item_declara_clausula_local_estado_e_questao():
    for item in nz.CATALOGO_NBR6123:
        assert item.clausula.startswith("NBR 6123"), item.chave
        if item.simbolos:
            assert ":" in item.local, f"{item.chave}: local sem file:line"
        else:
            # Um item do catálogo pode ser uma LACUNA: algo que a norma tem e o
            # código não (as colunas b1/b2/b3 da Tab. 10, para α = 90°). Não tem
            # símbolos nem linha — mas tem de estar listado, senão a lacuna
            # desaparece do inventário.
            assert item.local == "NÃO IMPLEMENTADO", item.chave
            assert item.estado == "NAO_CONFIRMADO", item.chave
        assert item.estado in ("CONFIRMADO", "NAO_CONFIRMADO"), item.chave
        assert item.designacao.strip(), item.chave
        if item.estado == "NAO_CONFIRMADO":
            assert item.questao.strip(), (
                f"{item.chave}: um item por confirmar tem de dizer QUAL é a "
                f"pergunta a fazer à norma em papel")


def test_chaves_sao_unicas():
    chaves = [i.chave for i in nz.CATALOGO_NBR6123]
    assert len(chaves) == len(set(chaves))


# ── 2. O estado de confirmação é o que a auditoria apurou ─────────────────────

def test_atrito_722_esta_confirmado():
    """O utilizador forneceu o texto literal de §7.2.2 — único item fechado."""
    item = nz.item_nbr("atrito_cobertura")
    assert item.estado == "CONFIRMADO"
    assert "7.2.2" in item.clausula


@pytest.mark.parametrize("chave", [
    "param_meteorologicos", "fator_rajada", "tabela_10_ce", "tabela_25_cp",
    "pressao_dinamica", "s1_topografico", "cpi_obstrucao", "dominio_tab_24_25",
    "cp_vedacao_isolada",
])
def test_tabelas_confirmadas_contra_o_texto(chave):
    """
    ATUALIZADO. A versão anterior deste teste exigia que estas tabelas
    permanecessem `NAO_CONFIRMADO` — «enquanto o texto da :2023 não for
    anexado». O texto ESTAVA anexado: `NBR6123-2023.pdf` está na raiz do
    projeto (fora do git por ser obra protegida, ver `.gitignore`), e a
    auditoria nunca o procurou.

    BM-17 (`auditoria_v2/bm_nbr_texto.py`) lê o PDF e confronta valor a valor.
    Estes itens conferem. O teste passa a exigir o contrário, e a evidência
    tem de estar escrita.
    """
    item = nz.item_nbr(chave)
    assert item.estado == "CONFIRMADO"
    assert "BM-17" in item.evidencia, f"{chave}: confirmado sem citar a evidência"


@pytest.mark.parametrize("chave", [
    "v0_isopleta", "s3_estatistico", "ca_pilar", "tabela_10_alpha_90",
])
def test_itens_que_o_texto_nao_fecha(chave):
    """
    Os quatro que sobram depois de ler a norma — e nenhum é uma tabela:

    · `v0_isopleta`      — a Figura 1 é um mapa e o projeto não declara a
                           localidade da obra.
    · `s3_estatistico`   — [F-21] valor do grupo 3 rotulado «grupo 2».
    · `ca_pilar`         — [F-20] citação inexistente para o fim a que serve.
    · `tabela_10_alpha_90` — lacuna: a norma tem colunas que o código não tem.

    Marcar qualquer um destes CONFIRMADO seria fechar por cansaço.
    """
    assert nz.item_nbr(chave).estado == "NAO_CONFIRMADO"


def test_itens_nao_confirmados_e_o_complemento():
    nao = nz.itens_nbr_nao_confirmados()
    assert nao, "F-18 ainda está aberto — a lista não pode estar vazia"
    assert all(i.estado == "NAO_CONFIRMADO" for i in nao)
    assert len(nao) == 4, f"esperados 4 em aberto, estão {len(nao)}"
    assert len(nao) < len(nz.CATALOGO_NBR6123)


def test_aviso_nbr_declara_a_reserva_e_conta_os_itens():
    aviso = nz.CONFIG_NORMATIVA.aviso_nbr()
    assert "NBR 6123" in aviso
    assert str(len(nz.itens_nbr_nao_confirmados())) in aviso
    assert "F-18" in aviso
    assert "BM-17" in aviso, "o aviso tem de dizer contra o quê foi verificado"
    for item in nz.itens_nbr_nao_confirmados():
        assert item.chave in aviso, f"{item.chave} não é nomeado no aviso"


# ── 3. Cobertura: nenhum valor NBR fica fora do catálogo ──────────────────────

def test_todas_as_tabelas_de_wind_estao_catalogadas():
    """
    Guarda de cobertura: as constantes tabeladas de `core/wind.py` de origem
    NBR têm de estar todas registadas. Uma tabela nova sem registo falha aqui.
    """
    esperadas = {
        "PARAM_METEOROLOGICOS", "FATOR_RAJADA", "COEF_PRESSAO_DINAMICA",
        "TABELA_10_CE", "CPI_OBSTRUCAO_SOTAVENTO", "CPI_OBSTRUCAO_BARLAVENTO",
        "CA_PILAR_RET", "COEF_ATRITO_COBERTURA_ISOLADA", "CA_BLOQUEIO_SILHUETA",
        "CP_VEDACAO_ISOLADA",
    }
    esperadas.discard("CP_VEDACAO_ISOLADA")   # vive em checks/elu/fixacao_telha.py
    presentes = {n for n in esperadas if hasattr(w, n)}
    assert presentes == esperadas, f"constantes ausentes: {esperadas - presentes}"
    simbolos = {s for i in nz.CATALOGO_NBR6123 for s in i.simbolos}
    assert esperadas <= simbolos, f"fora do catálogo: {esperadas - simbolos}"


# ── 4. Coerência interna congelada (BM-15) ────────────────────────────────────

CATS = ("I", "II", "III", "IV", "V")
CLASSES = ("A", "B", "C")


def test_v1_v2_monotonia_dos_parametros():
    for cl in CLASSES:
        bs = [w.PARAM_METEOROLOGICOS[c][cl][0] for c in CATS]
        ps = [w.PARAM_METEOROLOGICOS[c][cl][1] for c in CATS]
        assert all(x > y for x, y in zip(bs, bs[1:])), f"b não decresce I→V ({cl})"
        assert all(x < y for x, y in zip(ps, ps[1:])), f"p não cresce I→V ({cl})"
    for cat in CATS:
        ps = [w.PARAM_METEOROLOGICOS[cat][cl][1] for cl in CLASSES]
        assert all(x < y for x, y in zip(ps, ps[1:])), f"p não cresce A→C ({cat})"


def test_v3_zg_cresce_e_nao_depende_da_classe():
    zgs = []
    for cat in CATS:
        por_classe = {w.PARAM_METEOROLOGICOS[cat][cl][2] for cl in CLASSES}
        assert len(por_classe) == 1, f"z_g varia entre classes em {cat}"
        zgs.append(por_classe.pop())
    assert all(x < y for x, y in zip(zgs, zgs[1:]))


def test_v4_fator_rajada_decresce_de_A_para_C():
    frs = [w.FATOR_RAJADA[cl] for cl in CLASSES]
    assert all(x > y for x, y in zip(frs, frs[1:]))


def test_v5_convergencia_ao_vento_gradiente():
    """
    A invariante forte (BM-15/V5): acima da camada limite o escoamento é
    geostrófico e não depende do terreno, logo S2(z_g) tem de ser o mesmo nas
    cinco categorias. Liga b, p e z_g — três colunas independentes.

    Dispersão medida: 0,72 %. Limite adotado 2 %.
    """
    pior = 0.0
    for cl in CLASSES:
        vals = []
        for cat in CATS:
            b, p, zg = w.PARAM_METEOROLOGICOS[cat][cl]
            vals.append(b * w.FATOR_RAJADA[cl] * (zg / 10.0) ** p)
        media = sum(vals) / len(vals)
        pior = max(pior, max(abs(v - media) / media for v in vals))
    assert pior * 100.0 == pytest.approx(0.72, abs=0.05)
    assert pior <= 0.02


def test_v6_tabela25_e_continua_no_ponto_de_quebra():
    """Os quatro ramos lineares juntam-se em tg β = 0,4 sem salto."""
    baixo = w.coeficientes_tabela25(0.4 - 1e-9)
    alto = w.coeficientes_tabela25(0.4 + 1e-9)
    for caso in ("C1", "C2"):
        for c in ("Cpb", "Cps"):
            assert baixo[caso][c] == pytest.approx(alto[caso][c], abs=1e-6), \
                f"{caso}/{c} descontínuo em tg β = 0,4"


def test_v7_tabela10_coerencia_de_sinais():
    a = w.TABELA_10_CE["a"]
    i_pico = min(range(len(a)), key=lambda k: a[k])
    assert w.TABELA_10_THETA[i_pico] == 10.0, "pico de sucção fora de θ=10°"
    assert a[-1] > 0, "barlavento do 1.º tramo devia pressurizar a 45°"
    for zona in ("b", "c", "d", "m", "n", "x", "z"):
        assert all(v <= 0 for v in w.TABELA_10_CE[zona]), f"zona {zona} com pressão"


def test_geometria_do_projeto_cai_no_ramo_baixo_da_tab25():
    """Documenta que o projeto usa o ramo 0,07 ≤ tg β ≤ 0,4 — o único que a
    verificação de continuidade cobre em ambos os lados."""
    assert 0.07 <= math.tan(math.radians(10.0)) <= 0.4
