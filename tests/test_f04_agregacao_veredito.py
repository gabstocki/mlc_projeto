"""
Testes de regressão — F-04 (auditoria adversarial v2).

Achado
------
A camada que produz o carimbo `APROVADO` convertia AUSÊNCIA DE RESULTADO em
aprovação:

  · `_f(x, default=0.0)` devolvia 0,0 para `None` ou tipo inválido, e
    `extrair_eta_ok` sem chave "ok" concluía `ok = η ≤ 1,0`. Logo:
        extrair_eta_ok({})              -> (0.0, True)
        extrair_eta_ok({"eta": None})   -> (0.0, True)
        extrair_eta_ok({"eta": "erro"}) -> (0.0, True)
  · `tabela_verificacoes` fazia `continue` quando o dicionário não trazia η: a
    verificação DESAPARECIA do resumo do terminal, do `all_ok`, do `eta_max`,
    do Excel e do memorial LaTeX, sem qualquer aviso, e não havia nenhuma
    conferência de que todas as chaves do catálogo tinham sido produzidas.

Princípio adotado (o mesmo de core/validacao.py): **falhar alto, nunca
compensar**. Um resultado ausente, nulo ou não numérico não é η = 0.
"""
import math

import pytest

from mlc_projeto.output.report import (
    VERIFICACOES_EXPORT,
    estatisticas_resumo,
    extrair_eta_ok,
    tabela_verificacoes,
)


# ── extrair_eta_ok: ausência nunca é aprovação ────────────────────────────────

@pytest.mark.parametrize("res", [
    {},
    {"eta": None},
    {"eta": "erro"},
    {"eta": float("nan")},
    {"eta": float("inf")},
    {"eta": True},          # bool não é uma taxa de utilização
    {"outra_chave": 1.0},
    None,
    "nao e dict",
])
def test_resultado_sem_eta_valido_nunca_aprova(res):
    eta, ok = extrair_eta_ok(res)
    assert ok is False, f"{res!r} foi tratado como aprovado"
    assert math.isnan(eta), f"{res!r} devolveu η={eta!r} em vez de indeterminado"


def test_eta_valido_continua_a_funcionar():
    assert extrair_eta_ok({"eta": 0.5}) == (0.5, True)
    assert extrair_eta_ok({"eta": 1.5}) == (1.5, False)
    assert extrair_eta_ok({"eta": 0.5, "ok": False}) == (0.5, False)
    assert extrair_eta_ok({"eta_gov": 0.4})[0] == pytest.approx(0.4)
    assert extrair_eta_ok({"eta_slip": 0.3})[0] == pytest.approx(0.3)
    # ok_alvo continua a somar-se ao limite normativo
    assert extrair_eta_ok({"eta": 0.8, "ok_alvo": False})[1] is False


def test_eta_zero_legitimo_e_aprovacao():
    """Um η genuinamente nulo (ex.: L3 com H=0) continua a ser aprovação."""
    eta, ok = extrair_eta_ok({"eta": 0.0, "ok": True})
    assert (eta, ok) == (0.0, True)


# ── tabela_verificacoes: nada desaparece em silêncio ─────────────────────────

def test_verificacao_sem_eta_aparece_como_reprovada():
    tab = tabela_verificacoes({"cumeeira": {"sem_eta": 1}, "cisalhamento": {"eta": 0.5}})
    linha = next(r for r in tab if r["chave"] == "cumeeira")
    assert linha["status"] == "SEM η"
    assert linha["ok_bool"] is False
    assert math.isnan(linha["η"])


def test_verificacao_ausente_aparece_como_nao_executada():
    tab = tabela_verificacoes({"cisalhamento": {"eta": 0.5}})
    linha = next(r for r in tab if r["chave"] == "cumeeira")
    assert linha["status"] == "NÃO EXECUTADA"
    assert linha["ok_bool"] is False


def test_nao_aplicavel_declarado_aparece_mas_nao_reprova():
    tab = tabela_verificacoes(
        {"cisalhamento": {"eta": 0.5}},
        nao_aplicaveis={"tirante_base", "tirante_piso_robustez"},
    )
    for chave in ("tirante_base", "tirante_piso_robustez"):
        linha = next(r for r in tab if r["chave"] == chave)
        assert linha["status"] == "NÃO APLICÁVEL"
        assert linha["ok_bool"] is True


def test_resumo_cobre_todo_o_catalogo():
    """Nenhuma chave de VERIFICACOES_EXPORT pode faltar na tabela."""
    tab = tabela_verificacoes({"cisalhamento": {"eta": 0.5}})
    chaves = {r["chave"] for r in tab}
    assert {c for c, _, _ in VERIFICACOES_EXPORT} <= chaves


def test_chave_residual_fora_do_catalogo_continua_a_aparecer():
    tab = tabela_verificacoes({"verificacao_nova": {"eta": 0.9, "norma": "X"}})
    linha = next(r for r in tab if r["chave"] == "verificacao_nova")
    assert linha["η"] == pytest.approx(0.9)
    assert linha["ok_bool"] is True


# ── estatísticas do resumo: o carimbo APROVADO ───────────────────────────────

def _tab(**resultados):
    return tabela_verificacoes(
        resultados,
        nao_aplicaveis={c for c, _, _ in VERIFICACOES_EXPORT} - set(resultados),
    )


def test_status_aprovado_quando_tudo_executou_e_passou():
    est = estatisticas_resumo(_tab(cumeeira={"eta": 0.3}, cisalhamento={"eta": 0.6}))
    assert est["eta_max"] == pytest.approx(0.6)
    assert est["all_ok"] is True
    assert est["pendentes"] == []
    assert est["status"] == "APROVADO"


def test_status_reprovado_quando_uma_verificacao_nao_executou():
    tab = tabela_verificacoes({"cumeeira": {"eta": 0.3}})   # sem declarar N/A
    est = estatisticas_resumo(tab)
    assert est["status"] == "REPROVADO"
    assert "cisalhamento" in est["pendentes"]


def test_status_reprovado_quando_uma_verificacao_nao_traz_eta():
    tab = _tab(cumeeira={"eta": 0.3}, cisalhamento={"sem_eta": True})
    est = estatisticas_resumo(tab)
    assert est["status"] == "REPROVADO"
    assert "cisalhamento" in est["pendentes"]


def test_eta_indeterminado_nao_e_engolido_pelo_maximo():
    """max() sobre NaN devolveria o outro valor — o pendente tem de sobreviver."""
    tab = _tab(cumeeira={"eta": 0.3}, cisalhamento={"eta": None})
    est = estatisticas_resumo(tab)
    assert est["eta_max"] == pytest.approx(0.3)   # NaN não entra no máximo
    assert est["status"] == "REPROVADO"           # mas reprova pelo pendente


def test_status_reprovado_com_eta_acima_de_um_mesmo_com_ok_true():
    tab = _tab(cumeeira={"eta": 1.4, "ok": True})
    est = estatisticas_resumo(tab)
    assert est["eta_max"] == pytest.approx(1.4)
    assert est["status"] == "REPROVADO"
