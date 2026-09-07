"""Quadro de cargas para a fundação.

O projeto não dimensiona fundações (não há sondagem); entrega os esforços que
chegam a cada base. Estes testes guardam o contrato desse entregável.
"""

from __future__ import annotations

import pytest

from mlc_projeto.output.cargas_fundacao import montar_quadro_cargas_fundacao


def _quadro(**over):
    base = dict(
        res_succao={"N_uplift_ext_kN": 83.9, "N_uplift_cen_kN": 151.8,
                    "N_uplift_canto_kN": 371.3},
        cv_vertical={"H_base_kN": 211.9, "N_uplift_kN": 257.9},
        cv_transversal={"H_base_kN": 24.2, "N_uplift_kN": 29.5},
        n_pilares_linha=9, n_linhas_portico=3,
        n_paineis_long=4, n_paineis_transv=1,
    )
    base.update(over)
    return montar_quadro_cargas_fundacao(**base)


class _LoadFake:
    def __init__(self, v=99.6, h=0.0):
        self._v, self._h = v, h

    def combinacoes_ELU(self):
        class C:
            V_max_kN = self._v
        return {"c": C()}

    def H_ELU(self):
        return self._h


def test_quadro_tem_as_tres_bases():
    q = _quadro(load=_LoadFake())
    tipos = [l["Base"] for l in q["linhas"]]
    assert any("Extremidade" in t for t in tipos)
    assert any("Central" in t for t in tipos)
    assert any("Canto" in t for t in tipos)


def test_canto_e_a_base_mais_solicitada():
    """O canto acumula uplift de sucção + downloads dos dois painéis."""
    q = _quadro(load=_LoadFake())
    por_tipo = {l["Base"]: l for l in q["linhas"]}
    canto = next(v for k, v in por_tipo.items() if "Canto" in k)
    outros = [v for k, v in por_tipo.items() if "Canto" not in k]
    assert all(canto["N_tração (kN)"] > o["N_tração (kN)"] for o in outros)
    assert all(canto["H (kN)"] >= o["H (kN)"] for o in outros)


def test_central_recebe_as_duas_reacoes():
    q = _quadro(load=_LoadFake(v=99.6))
    central = next(l for l in q["linhas"] if "Central" in l["Base"])
    assert central["N_comp (kN)"] == pytest.approx(2 * 99.6, rel=1e-6)


def test_h_total_escala_com_o_numero_de_paineis():
    q4 = _quadro(load=_LoadFake(), n_paineis_long=4)
    q6 = _quadro(load=_LoadFake(), n_paineis_long=6)
    assert (q6["totais"]["H_longitudinal_total_kN"]
            > q4["totais"]["H_longitudinal_total_kN"])


def test_escopo_declara_que_nao_dimensiona_fundacao():
    """O quadro não pode ser confundido com verificação de fundação."""
    q = _quadro(load=_LoadFake())
    escopo = q["escopo"].lower()
    assert "não dimensiona fundações" in escopo
    assert "sondagem" in escopo
    for termo in ("solo", "deslizamento", "tombamento", "recalque", "armadura"):
        assert termo in escopo, f"o escopo deve declarar {termo!r} como não verificado"


def test_premissas_registram_o_que_nao_esta_descontado():
    q = _quadro(load=_LoadFake())
    txt = " ".join(q["premissas"]).lower()
    assert "peso próprio da sapata" in txt   # não descontado no arrancamento
    assert "en 1992-4" in txt                # ancoragem ainda NÃO VALIDADA
