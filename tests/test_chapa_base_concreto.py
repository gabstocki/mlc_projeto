"""Chapa de base sobre o concreto — EN 1992-1-1 §3.1.6 e §6.7.

Encontrado no redimensionamento pós-Onda 2, ao investigar por que a `L3c sapata
central` aparecia com η = 1,0000 exato — número redondo demais para ser real.

Eram três defeitos encadeados:

  1) CIRCULARIDADE. A chapa era dimensionada por `A = N/f_c` e depois verificada
     contra o mesmo `f_c`. Logo σ_c ≡ f_c e η ≡ 1,0000, para QUALQUER carga e
     QUALQUER resistência. Não era verificação: era tautologia, e aparecia no
     memorial como um item "no limite" que nunca poderia reprovar.

  2) f_c = 1,5 MPa não é resistência de concreto. Para C25/30,
     f_cd = α_cc·f_ck/γ_C = 16,7 MPa — uma ordem de grandeza acima.

  3) Faltava o piso na área do pilar no ramo SEM tirante (que é o do projeto),
     embora o ramo COM tirante o tivesse. Com f_cd realista, a chapa saía com
     7,7 cm de lado sob um pilar de 32×27 cm — fisicamente impossível, e ainda
     assim η = 1,0000 ✓.
"""

from __future__ import annotations

import math

import pytest

from mlc_projeto.connections.connections import (
    ALPHA_CC,
    F_CK_CLASSE,
    GAMMA_C,
    _dimensionar_chapa_base,
    resistencia_apoio_concreto,
)


# ── Resistência de apoio ─────────────────────────────────────────────────────

def test_f_cd_segue_en_1992():
    r = resistencia_apoio_concreto("C25/30")
    # f_cd_MPa é devolvido arredondado a 3 casas — tolerância coerente com isso.
    assert r["f_cd_MPa"] == pytest.approx(ALPHA_CC * 25.0 / GAMMA_C, abs=5e-4)
    assert r["f_Rdu_MPa"] == pytest.approx(r["f_cd_MPa"], rel=1e-9)  # k_conf = 1


def test_confinamento_limitado_a_tres():
    """§6.7: √(A_c1/A_c0) ≤ 3,0."""
    assert resistencia_apoio_concreto("C25/30", 3.0)["f_Rdu_MPa"] > 0
    with pytest.raises(ValueError):
        resistencia_apoio_concreto("C25/30", 3.5)
    with pytest.raises(ValueError):
        resistencia_apoio_concreto("C25/30", 0.5)


def test_classe_desconhecida_e_rejeitada():
    with pytest.raises(ValueError, match="classe_concreto"):
        resistencia_apoio_concreto("C99/99")


def test_todas_as_classes_crescem_monotonicamente():
    fcds = [resistencia_apoio_concreto(c)["f_cd_MPa"]
            for c in sorted(F_CK_CLASSE, key=lambda k: F_CK_CLASSE[k])]
    assert fcds == sorted(fcds)


# ── Não circularidade ────────────────────────────────────────────────────────

def test_eta_nao_e_identicamente_um():
    """Regressão do defeito 1: η tem de VARIAR com a resistência."""
    etas = {
        f_Rd: _dimensionar_chapa_base(199.2, 0.32, 0.27, f_Rd)["eta_N"]
        for f_Rd in (1.5, 5.0, 16.667)
    }
    assert len(set(round(e, 6) for e in etas.values())) > 1
    assert all(e != pytest.approx(1.0, abs=1e-6) for e in etas.values())


def test_eta_cresce_com_a_carga():
    """Com a chapa fixada por dimensão construtiva, mais carga ⇒ mais η."""
    leve = _dimensionar_chapa_base(100.0, 0.32, 0.27, 16.667)
    pesado = _dimensionar_chapa_base(400.0, 0.32, 0.27, 16.667)
    assert pesado["eta_N"] > leve["eta_N"]


# ── Piso na área do pilar ────────────────────────────────────────────────────

def test_chapa_nunca_menor_que_o_pilar():
    """Regressão do defeito 3: a chapa não pode ser menor que o que ela apoia."""
    b, h = 0.32, 0.27
    r = _dimensionar_chapa_base(199.2, b, h, 16.667)
    lado_pilar_equiv_cm = math.sqrt(b * h) * 100.0
    assert r["lado_chapa_cm"] >= lado_pilar_equiv_cm
    assert r["A_chapa_m2"] >= b * h - 1e-9
    assert r["governa_chapa"] == "area_pilar"


def test_resistencia_governa_quando_a_carga_e_alta():
    """Com carga suficiente, é o concreto que passa a governar a chapa."""
    r = _dimensionar_chapa_base(3000.0, 0.32, 0.27, 16.667)
    assert r["governa_chapa"] == "resistencia_concreto"
    assert r["eta_N"] <= 1.0 + 1e-9


def test_lado_e_dimensao_construtiva():
    """A chapa sai em múltiplo de 5 cm — não num decimal de cálculo."""
    r = _dimensionar_chapa_base(199.2, 0.32, 0.27, 16.667)
    assert r["lado_chapa_cm"] % 5.0 == pytest.approx(0.0, abs=1e-9)
