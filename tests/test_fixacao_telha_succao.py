"""Fixação telha→terça sob sucção — NBR 6123:2023 (issue 17, revisto em AUD-005).

Reescrito na Onda 2 da auditoria. A versão anterior verificava o modelo da
edição de 1988: C_pe local por zona (campo/borda/canto, Tab. 5 de edificação
fechada) somado a uma pressão interna C_pi = +0,8.

Esse modelo não pertence ao domínio de uma cobertura isolada. A edição de 2023 é
direta em §7.2.6: "Cada elemento de vedação deve ser calculado com cp = ±2,0" —
coeficiente líquido que já engloba as duas faces da cobertura. Pressão interna
é conceito de edificação fechada (§6.3) e não se aplica a uma cobertura sobre
suportes de reduzidas dimensões.

Além disso, §5.3.2 a) classifica "unidades e sistemas de vedação e seus elementos
de fixação" na Classe A (rajada de 3 s), e §5.3.3 recomenda o S2 do topo da
edificação para o estudo desses elementos. O vento GLOBAL da estrutura
(classe B neste projeto) não serve para a verificação local.

Verificação: w_up,d = γ_Q·|cp|·q_A − γ_G,fav·g_telha;
             F_fix,d = w_up,d·(s_terça · e_fix); η = F_fix,d / R_fix,d.
"""

import pytest

from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.checks.elu.fixacao_telha import (
    verificar_fixacao_telha_succao,
    CP_VEDACAO_ISOLADA,
    CLASSE_VEDACAO,
    GAMMA_Q_VENTO,
    GAMMA_G_FAV,
    GAMMA_M_FIX,
)


def _pv(classe: str = CLASSE_VEDACAO) -> ParametrosVento:
    """Vento na altura de referência do projeto, na classe indicada."""
    return ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe=classe, S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )


PV = _pv()


# ── AUD-005 — classe do vento local ───────────────────────────────────────────

def test_exige_classe_a_para_elementos_de_vedacao():
    """§5.3.2 a): vedação e fixações são Classe A; o vento global não serve."""
    with pytest.raises(ValueError, match="classe A"):
        verificar_fixacao_telha_succao(_pv("B"), s_terca=2.53, e_fix_m=0.20)


def test_classe_a_e_mais_severa_que_a_classe_global():
    """A rajada de 3 s (classe A) dá q maior que a de 5 s (classe B)."""
    assert _pv("A").q > _pv("B").q


def test_usa_s2_do_topo_da_cobertura():
    """§5.3.3: para elementos de vedação, S2 é o do topo da edificação."""
    r = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.20)
    assert r["z_ref_m"] == pytest.approx(PV.h + PV.H1, rel=1e-9)
    assert r["q_kNm2"] == pytest.approx(PV.q, rel=1e-3)
    assert r["classe_vento"] == "A"


# ── §7.2.6 — coeficiente do elemento de vedação ──────────────────────────────

def test_coeficiente_normativo_e_dois():
    """§7.2.6: cada elemento de vedação com cp = ±2,0, sem somar C_pi."""
    assert CP_VEDACAO_ISOLADA == 2.0
    r = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.20)
    assert r["zonas"]["vedacao"]["C_net"] == pytest.approx(-2.0, rel=1e-9)


def test_formula_uplift():
    """w_up,d e F_fix,d batem com a equação recalculada à mão."""
    s, e, g = 2.53, 0.33, 0.10
    r = verificar_fixacao_telha_succao(
        PV, s_terca=s, g_telha_kNm2=g, e_fix_m=e, R_fix_k_kN=2.5,
    )
    w_suc = GAMMA_Q_VENTO * CP_VEDACAO_ISOLADA * PV.q
    w_up = w_suc - GAMMA_G_FAV * g
    z = r["zonas"]["vedacao"]
    assert z["w_suc_d_kNm2"] == pytest.approx(w_suc, rel=1e-3)
    assert z["w_up_d_kNm2"] == pytest.approx(w_up, rel=1e-3)
    assert z["F_fix_d_kN"] == pytest.approx(w_up * s * e, rel=1e-3)
    assert r["R_fix_d_kN"] == pytest.approx(2.5 / GAMMA_M_FIX, rel=1e-3)


# ── Invariantes de comportamento ─────────────────────────────────────────────

def test_uplift_escala_linear_com_e_fix():
    """F_fix,d ∝ e_fix (área tributária linear) → η escala com o espaçamento."""
    r1 = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.20)
    r2 = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.40)
    assert r2["eta"] / r1["eta"] == pytest.approx(2.0, rel=1e-3)


def test_e_fix_requerido_leva_eta_a_um():
    """Reaplicar e_fix_req devolve η ≈ 1."""
    r = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33)
    r2 = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=r["e_fix_req_m"])
    assert r2["eta"] == pytest.approx(1.0, abs=5e-3)


def test_peso_telha_alivia_uplift():
    """Maior g_telha reduz o uplift líquido (permanente favorável)."""
    leve = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33, g_telha_kNm2=0.05)
    pesada = verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=0.33, g_telha_kNm2=0.30)
    assert (pesada["zonas"]["vedacao"]["w_up_d_kNm2"]
            < leve["zonas"]["vedacao"]["w_up_d_kNm2"])


def test_entradas_invalidas():
    with pytest.raises(ValueError):
        verificar_fixacao_telha_succao(PV, s_terca=0.0, e_fix_m=0.33)
    with pytest.raises(ValueError):
        verificar_fixacao_telha_succao(PV, s_terca=2.53, e_fix_m=-0.1)
