"""Issue 22 — Critério η-alvo 0,75 aplicado de forma CONSISTENTE por modo de falha.

O alvo 0,75 é margem para modos FRÁGEIS (madeira: embutimento/bloco/fendilhamento;
ancoragem frágil no concreto). Modos dúcteis/compressão (concreto sob a chapa,
compressão da madeira, aço) usam η≤1,0 — exceções justificadas.
"""

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.connections.connections import (
    classificar_criterio_eta,
    aplicar_criterio_eta,
    ETA_ALVO_LIGACAO,
    dimensionar_ligacoes,
    dimensionar_ligacoes_central,
)


def test_classificacao_fragil_vs_ductil():
    frag = classificar_criterio_eta(True)
    duc = classificar_criterio_eta(False)
    assert frag["eta_limite"] == ETA_ALVO_LIGACAO
    assert frag["alvo_aplica"] is True
    assert duc["eta_limite"] == 1.0
    assert duc["alvo_aplica"] is False


def test_aplicar_fragil_reprova_acima_do_alvo():
    """Modo frágil com η entre 0,75 e 1,0 → ok=False (alvo manda)."""
    res = {"eta": 0.85}
    aplicar_criterio_eta(res, modo_fragil=True)
    assert res["eta_limite"] == 0.75
    assert res["ok"] is False           # 0,85 > 0,75
    assert res["ok_alvo"] is False


def test_aplicar_ductil_aprova_ate_1():
    """Modo dúctil (ex.: compressão no concreto) aprova η=1,0."""
    res = {"eta": 1.0}
    aplicar_criterio_eta(res, modo_fragil=False)
    assert res["eta_limite"] == 1.0
    assert res["ok"] is True            # 1,0 ≤ 1,0
    assert res["ok_alvo"] is False      # mas não cumpre 0,75 (transparência)


def test_aplicar_preserva_geometria():
    """Se houver ok_geometria=False, ok final é False mesmo com η baixo."""
    res = {"eta": 0.30, "ok_geometria": False}
    aplicar_criterio_eta(res, modo_fragil=True)
    assert res["ok"] is False


def test_fragil_abaixo_do_alvo_aprova():
    res = {"eta": 0.50}
    aplicar_criterio_eta(res, modo_fragil=True)
    assert res["ok"] is True
    assert res["ok_alvo"] is True


# ── Integração: política completa nas ligações reais ─────────────────────────

def _ligacoes_reais():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    gov = load.combinacao_ELU_governante()
    m = mat.com_duracao(gov.duracao)
    L = dimensionar_ligacoes(m, load, geo, d_base_mm=24, com_tirante=True,
                             eta_alvo=ETA_ALVO_LIGACAO)
    Lc = dimensionar_ligacoes_central(m, load, geo, d_base_mm=24,
                                      eta_alvo=ETA_ALVO_LIGACAO)
    return L, Lc


def test_L1_L1c_sob_alvo_075():
    """L1/L1c (madeira, frágil) devem estar ≤ 0,75 e aprovados sob o alvo."""
    L, Lc = _ligacoes_reais()
    for r in (L["L1"], Lc["L1c"]):
        aplicar_criterio_eta(r, modo_fragil=True)
        assert r["eta_limite"] == 0.75
        assert r["eta"] <= 0.75 + 1e-9
        assert r["ok"] is True


def test_L3_L3c_excecao_concreto():
    """L3/L3c (compressão no concreto) são exceção: η pode ir a 1,0.

    Revisto no redimensionamento: `aplicar_criterio_eta` deixou de poder
    PROMOVER um `ok` que já era False — o critério de η só acrescenta motivo de
    reprovação. O L3 carrega agora o bloqueio de ancoragem (AUD-017,
    status_ancoragem="NOT VALIDATED"), pelo que o seu `ok` é False por um
    motivo alheio a η. O que este teste verifica é o LIMITE de η aplicado, que
    é a exceção em causa — e verifica-se explicitamente que o bloqueio de
    ancoragem sobrevive à aplicação do critério.
    """
    L, Lc = _ligacoes_reais()
    r3 = L["L3"]
    r3c = Lc["L3c"]
    aplicar_criterio_eta(r3, modo_fragil=False)   # com tirante → bearing concreto
    aplicar_criterio_eta(r3c, modo_fragil=False)
    assert r3["eta_limite"] == 1.0 and r3c["eta_limite"] == 1.0
    assert r3["alvo_aplica"] is False
    # A exceção vale para o critério de η (η ≤ 1,0 é satisfeito nos dois)...
    assert r3["eta"] <= 1.0 + 1e-9 and r3c["eta"] <= 1.0 + 1e-9
    assert r3c["ok"] is True
    # ...mas não apaga o bloqueio de ancoragem por dados insuficientes.
    assert r3["status_ancoragem"] == "NOT VALIDATED"
    assert r3["ok"] is False


def test_criterio_eta_nunca_promove_um_ok_falso():
    """Regressão: o critério de η só pode acrescentar reprovação.

    Uma verificação bloqueada por motivo não numérico (p.ex. ancoragem sem
    dados certificados) tem η baixo e passaria no limite — antes, isso
    reescrevia `ok` para True e a falsa aprovação chegava ao memorial.
    """
    r = {"eta": 0.0, "ok": False}
    aplicar_criterio_eta(r, modo_fragil=False)
    assert r["ok"] is False


def test_nenhum_modo_fragil_aprovado_acima_do_alvo():
    """Critério de aceite da issue: nenhuma ligação frágil OK com η>0,75."""
    L, Lc = _ligacoes_reais()
    frageis = [L["L1"], Lc["L1c"]]
    for r in frageis:
        aplicar_criterio_eta(r, modo_fragil=True)
        if r["ok"]:
            assert r["eta"] <= 0.75 + 1e-9
