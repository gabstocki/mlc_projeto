"""
Testes de regressão — F-13 (auditoria adversarial v2), ENCERRADO.

Achado, e o seu desfecho
------------------------
`COEF_ATRITO_COBERTURA_ISOLADA = 0.5` era uma constante de módulo sem origem
verificável no repositório, e o teste de regressão limitava-se a reafirmar o
próprio número — `INVALID BENCHMARK — SELF-REFERENTIAL`. A auditoria levantou a
hipótese de o valor correto ser 0,05.

**A hipótese estava ERRADA.** A NBR 6123:2023 §7.2.2 prescreve literalmente:

    "Para vento paralelo à geratriz da cobertura, devem ser consideradas forças
     horizontais de atrito calculadas pela seguinte equação:  Ft = 0,5·q·a·b
     onde a e b são as dimensões em planta da cobertura. Estas forças englobam
     a ação do vento sobre as duas faces da cobertura."

O que a auditoria acertou foi o defeito de RASTREABILIDADE. Estes testes fecham-o
sem recair no mesmo vício: o número não é comparado consigo próprio, mas com a
**cláusula transcrita** no módulo — se a transcrição desaparecer, o teste falha.

Fixam ainda que `Ft` é uma ação ENVOLVENTE (engloba as duas faces num só termo),
que vale 2,35× o arrasto de bloqueio da silhueta deste galpão, e que essa escala
é reportada como diagnóstico — útil contra erro de ENTRADA, não para contestar
a norma.
"""
import pytest

from mlc_projeto.core.wind import (
    CA_BLOQUEIO_SILHUETA,
    COEF_ATRITO_COBERTURA_ISOLADA,
    ParametrosVento,
    arrasto_bloqueio_silhueta,
    forca_vento_paralelo_cumeeira,
)

L_COMP, B_COB = 46.0, 40.5


def _pv(coef=None):
    return ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,
        coef_atrito_cobertura=coef,
    )


def _f0(coef=None):
    return forca_vento_paralelo_cumeeira(
        _pv(coef), b_pilar=0.32, h_pilar=0.27,
        n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=L_COMP, B_cob_m=B_COB,
    )


# ── 1) O coeficiente é um parâmetro declarado ────────────────────────────────

def test_coeficiente_e_parametrizavel():
    assert _f0(None)["coef_atrito"] == pytest.approx(COEF_ATRITO_COBERTURA_ISOLADA)
    assert _f0(0.05)["coef_atrito"] == pytest.approx(0.05)
    assert _f0(0.05)["F_friccao_kN"] == pytest.approx(
        _f0(0.5)["F_friccao_kN"] / 10.0, rel=1e-4)   # saídas arredondadas


def test_coeficiente_traz_proveniencia_confirmada():
    r = _f0()
    assert r["coef_atrito_clausula"] == "NBR 6123:2023 §7.2.2"
    assert "A CONFIRMAR" not in r["coef_atrito_origem"]
    assert "7.2.2" in r["coef_atrito_origem"]


def test_valor_normativo_esta_ancorado_na_clausula_transcrita():
    """
    NÃO-AUTORREFERENCIAL: o 0,5 é confrontado com o TEXTO da cláusula presente
    no módulo, não consigo próprio. Se a transcrição sair, o teste cai.
    """
    import inspect
    import mlc_projeto.core.wind as W

    fonte = inspect.getsource(W)
    assert "Ft = 0,5 · q · a · b" in fonte
    assert "dimensões em planta da cobertura" in fonte
    assert "duas faces da cobertura" in fonte
    assert W.COEF_ATRITO_COBERTURA_ISOLADA == pytest.approx(0.5)


def test_coeficiente_negativo_e_recusado():
    with pytest.raises(Exception):
        _f0(-0.1)


# ── 2) Limite físico independente de norma ───────────────────────────────────

def test_arrasto_de_bloqueio_e_q_Cd_A():
    pv = _pv()
    r = arrasto_bloqueio_silhueta(pv, B_cob_m=B_COB)
    assert r["A_silhueta_m2"] == pytest.approx(B_COB * pv.H_max, rel=1e-9)
    assert r["F_bloqueio_kN"] == pytest.approx(
        pv.q * CA_BLOQUEIO_SILHUETA * B_COB * pv.H_max, rel=1e-9)


def test_bloqueio_e_um_limite_superior_reportado():
    r = _f0()
    assert r["F_bloqueio_kN"] > 0.0
    assert r["razao_bloqueio"] == pytest.approx(
        r["F_total_kN"] / r["F_bloqueio_kN"], rel=1e-4)


# ── 3) O limite discrimina as duas leituras ──────────────────────────────────

def test_escala_da_acao_normativa_e_reportada():
    """
    Com o coeficiente normativo, a ação vale 2,35× o arrasto de bloqueio da
    silhueta. É o envelope de §7.2.2 — reportado, nunca limitado.
    """
    r = _f0(0.50)
    assert r["razao_bloqueio"] == pytest.approx(2.35, abs=0.02)
    assert r["nota_bloqueio"]
    assert "DUAS faces" in r["nota_bloqueio"]
    assert r["F_friccao_kN"] > r["F_bloqueio_kN"]      # sem clamp


def test_diagnostico_nao_limita_a_acao():
    """O valor de projeto não é tocado pelo diagnóstico — escala linearmente."""
    r05, r50 = _f0(0.05), _f0(0.50)
    assert r50["F_friccao_kN"] == pytest.approx(10.0 * r05["F_friccao_kN"], rel=1e-4)
    assert r05["razao_bloqueio"] < 1.0 < r50["razao_bloqueio"]


def test_razao_e_monotona_no_coeficiente():
    razoes = [_f0(c)["razao_bloqueio"] for c in (0.01, 0.05, 0.1, 0.3, 0.5)]
    assert all(b > a for a, b in zip(razoes, razoes[1:]))


# ── 4) O parâmetro está registado na proveniência normativa ──────────────────

def test_atrito_registado_como_ABNT_confirmada():
    from mlc_projeto.core.normativo import NDP_SOURCE
    p = NDP_SOURCE["coef_atrito_cobertura_isolada"]
    assert p.valor == pytest.approx(COEF_ATRITO_COBERTURA_ISOLADA)
    assert p.origem == "ABNT"
    assert p.clausula == "NBR 6123:2023 §7.2.2"
    assert p.e_ndp is False          # não é NDP: não há anexo nacional a alterar


def test_nao_restam_parametros_com_clausula_por_confirmar():
    """
    Guarda permanente: qualquer parâmetro cuja cláusula não tenha sido
    verificada tem de aparecer aqui e bloquear o memorial. Hoje, nenhum.
    """
    from mlc_projeto.core.normativo import parametros_a_confirmar
    assert parametros_a_confirmar() == {}
