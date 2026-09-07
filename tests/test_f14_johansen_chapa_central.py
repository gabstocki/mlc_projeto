"""
Testes de regressão — F-14 (auditoria adversarial v2).

Achado
------
`johansen_chapa_embutida` usava, para o modo de UMA rótula plástica,

    F_v,Rk = 1,15 · √(2 · M_y,Rk · f_h,k · d)

que é o modo de **chapas de aço FINAS como elementos EXTERNOS** de uma ligação
em corte duplo. A ligação deste projeto é uma **chapa de aço embutida numa
ranhura CENTRAL**, atravessada pelas cavilhas — o conjunto de modos aplicável é
o da chapa de qualquer espessura como elemento CENTRAL em corte duplo
(EN 1995-1-1 §8.2.3):

    (f)  f_h,1,k · t₁ · d
    (g)  f_h,1,k · t₁ · d · [ √(2 + 4·M_y,Rk/(f_h,1,k·d·t₁²)) − 1 ]
    (h)  2,3 · √(M_y,Rk · f_h,1,k · d)

(o termo de efeito de corda F_ax,Rk/4 é nulo em cavilhas lisas — §8.2.2(2).)

Defeito secundário: `t₁ = b/2` ignorava a espessura da chapa. Para a chapa
central o correto é `t₁ = (b − t_chapa)/2`.

ATENÇÃO — esta correção REDUZ conservadorismo
---------------------------------------------
Antes de F-03 os dois erros cancelavam-se quase exatamente. Com `f_h,α,k` já
correto, o modo errado deixou o cálculo 18,3 % ABAIXO da resistência normativa.
Corrigi-lo AUMENTA a resistência (20,39 → 25,02 kN/plano) e reduz o número de
cavilhas de 7 para 6. Os testes abaixo ancoram cada modo na sua forma fechada,
calculada aqui de forma independente.
"""
import math

import pytest

from mlc_projeto.connections.connections import (
    F_U_K_PINO,
    M_y_Rk,
    f_h_alpha_k,
    johansen_chapa_central,
    johansen_chapa_embutida,
)

RHO_K, D, FU = 385.0, 24.0, 400.0
B_VIGA, T_CHAPA = 320.0, 24.0
ALPHA = math.degrees(math.atan2(99.2225, 8.7478))     # ≈ 84,96°


def _modos_ref(f_h, t1, d=D, My=None):
    """Eq. (8.11) reconstruída aqui, sem usar o repositório."""
    My = M_y_Rk(FU, d) if My is None else My
    f = f_h * t1 * d
    g = f_h * t1 * d * (math.sqrt(2.0 + 4.0 * My / (f_h * d * t1 ** 2)) - 1.0)
    h = 2.3 * math.sqrt(My * f_h * d)
    return f, g, h


# ── Os três modos da chapa central ───────────────────────────────────────────

@pytest.mark.parametrize("t1", [100.0, 147.5, 160.0, 200.0])
@pytest.mark.parametrize("alpha", [0.0, 45.0, ALPHA, 90.0])
def test_modos_seguem_a_forma_fechada(t1, alpha):
    f_h = f_h_alpha_k(RHO_K, D, alpha)
    f, g, h = _modos_ref(f_h, t1)
    r = johansen_chapa_central(RHO_K, D, t1, FU, theta_deg=alpha)
    assert r["modo_f_N"] == pytest.approx(f, abs=0.1)
    assert r["modo_g_N"] == pytest.approx(g, abs=0.1)
    assert r["modo_h_N"] == pytest.approx(h, abs=0.1)
    assert r["F_v_Rk_N"] == pytest.approx(min(f, g, h), abs=0.1)


def test_modo_da_chapa_externa_fina_nao_e_usado():
    """1,15·√(2·M_y·f_h·d) é de OUTRA configuração — não pode aparecer."""
    f_h = f_h_alpha_k(RHO_K, D, ALPHA)
    externo_fino = 1.15 * math.sqrt(2 * M_y_Rk(FU, D) * f_h * D)
    r = johansen_chapa_central(RHO_K, D, 147.5, FU, theta_deg=ALPHA)
    for k in ("modo_f_N", "modo_g_N", "modo_h_N", "F_v_Rk_N"):
        assert r[k] != pytest.approx(externo_fino, rel=1e-3), k


def test_valor_do_projeto():
    """d=24, ρ_k=385, α≈85°, t₁=(320−24)/2=148 mm."""
    t1 = (B_VIGA - T_CHAPA) / 2.0
    r = johansen_chapa_central(RHO_K, D, t1, FU, theta_deg=ALPHA)
    assert t1 == pytest.approx(148.0)
    assert r["f_hk_MPa"] == pytest.approx(14.076, abs=1e-3)
    assert r["F_v_Rk_N"] / 1e3 == pytest.approx(25.02, abs=0.05)
    assert r["modo_gov"] == "modo_g_N"          # uma rótula plástica


def test_correcao_aumenta_a_resistencia_face_ao_modo_errado():
    t1 = (B_VIGA - T_CHAPA) / 2.0
    f_h = f_h_alpha_k(RHO_K, D, ALPHA)
    errado = min(
        f_h * (B_VIGA / 2) * D,
        1.15 * math.sqrt(2 * M_y_Rk(FU, D) * f_h * D),
        2.3 * math.sqrt(M_y_Rk(FU, D) * f_h * D),
    )
    certo = johansen_chapa_central(RHO_K, D, t1, FU, theta_deg=ALPHA)["F_v_Rk_N"]
    assert certo > errado
    assert certo / errado == pytest.approx(1.227, abs=0.01)   # +22,7 %


# ── Espessura de madeira: t₁ = (b − t_chapa)/2 ───────────────────────────────

def test_t1_desconta_a_espessura_da_chapa():
    grosso = johansen_chapa_central(RHO_K, D, B_VIGA / 2, FU, theta_deg=ALPHA)
    certo = johansen_chapa_central(
        RHO_K, D, (B_VIGA - T_CHAPA) / 2, FU, theta_deg=ALPHA)
    # menos madeira ⇒ menos resistência: ignorar a chapa era não conservador
    assert certo["F_v_Rk_N"] < grosso["F_v_Rk_N"]


# ── Monotonias físicas ───────────────────────────────────────────────────────

def test_resistencia_cresce_com_t1_e_com_f_h():
    vals = [johansen_chapa_central(RHO_K, D, t, FU, theta_deg=ALPHA)["F_v_Rk_N"]
            for t in (80.0, 120.0, 160.0, 240.0)]
    assert all(b > a for a, b in zip(vals, vals[1:]))
    a0 = johansen_chapa_central(RHO_K, D, 148.0, FU, theta_deg=0.0)["F_v_Rk_N"]
    a90 = johansen_chapa_central(RHO_K, D, 148.0, FU, theta_deg=90.0)["F_v_Rk_N"]
    assert a0 > a90


def test_t1_muito_pequeno_faz_o_embutimento_governar():
    r = johansen_chapa_central(RHO_K, D, 20.0, FU, theta_deg=0.0)
    assert r["modo_gov"] == "modo_f_N"


def test_efeito_de_corda_e_nulo_em_cavilhas():
    """EC5 §8.2.2(2): F_ax,Rk = 0 para cavilhas lisas — nada a somar."""
    r = johansen_chapa_central(RHO_K, D, 148.0, FU, theta_deg=ALPHA)
    assert r["F_ax_Rk_N"] == 0.0


# ── Compatibilidade das chaves antigas ───────────────────────────────────────

def test_chaves_legadas_mapeiam_os_modos_do_EC5():
    t1 = (B_VIGA - T_CHAPA) / 2.0
    r = johansen_chapa_embutida(RHO_K, D, t1, FU, theta_deg=ALPHA)
    assert r["modo_I_N"] == pytest.approx(r["modo_f_N"])      # embutimento
    assert r["modo_IIIb_N"] == pytest.approx(r["modo_g_N"])   # 1 rótula
    assert r["modo_IV_N"] == pytest.approx(r["modo_h_N"])     # 2 rótulas


# ── Efeito na ligação de base ────────────────────────────────────────────────

def _l1():
    from mlc_projeto.core.geometry import GeometriaViga
    from mlc_projeto.core.materials import GlulamMaterial
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento
    from mlc_projeto.connections.connections import dimensionar_ligacao_base

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "media")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,
    )
    load = carregamentos_com_vento(
        geo, mat, 0.8229, 0.40, 5.75, pv, empuxo_desenvolve=False)
    return dimensionar_ligacao_base(mat=mat, load=load, geo=geo, d_mm=24)


def test_ligacao_base_desconta_a_chapa_e_cumpre_o_alvo():
    r = _l1()
    assert r["t1_madeira_mm"] == pytest.approx((320.0 - 24.0) / 2.0, abs=0.1)
    assert r["modo_gov"] in ("modo_g_N", "modo_f_N", "modo_h_N")
    assert r["eta"] <= 0.75 + 1e-9
    assert r["ok"] is True
    assert r["n_pinos"] == 6          # 7 → 6 com a resistência correta
