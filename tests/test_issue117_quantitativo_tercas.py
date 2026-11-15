"""Issue 117 — terças por lista de peças, espaçadores e terças como linhas de carga."""

import pytest

from mlc_projeto.core.loads import analisar_biarticulada
from mlc_projeto.output.custo import volume_espacadores_m3, volume_tercas_m3

GEO = dict(L=20.25, h0=1.0, h_ap=2.785, alpha_rad=0.1745, b=0.32, desenvolve_empuxo=False)


def test_volume_das_tercas_por_lista():
    # revisão: 19 linhas × 48,32 m × 0,20 × 0,40 = 73,4 m³ (+ escoras centrais mais largas)
    v = volume_tercas_m3(n_linhas=19, L_m=48.32, b_m=0.20, h_m=0.40)
    assert v == pytest.approx(73.4, abs=0.05)
    v2 = volume_tercas_m3(n_linhas=19, L_m=48.32, b_m=0.20, h_m=0.40,
                          n_escoras_largas=4, L_escora_m=5.75, b_escora_m=0.24)
    assert v2 - v == pytest.approx(4 * 5.75 * 0.04 * 0.40)


def test_volume_dos_espacadores():
    # 14 pilares, lâmina de 7.725 mm, um espaçador a cada 1.500 mm (6), 340 × 320 × 450
    v = volume_espacadores_m3(n_bipartidos=14, L_lamina_mm=7725, l1_mm=1500, a_mm=340, h_l_mm=320)
    assert v == pytest.approx(14 * 6 * 0.34 * 0.32 * 0.45)
    assert v == pytest.approx(4.11, abs=0.01)


def test_linhas_de_terca_nao_mudam_o_momento_do_vao_sem_beiral():
    """Sem beiral, a correção só acrescenta 0,5·P à reação A; o momento é o mesmo."""
    q, P, s = 5.0, 2.0, 20.25 / 8
    a = analisar_biarticulada(q=q, **GEO)
    b = analisar_biarticulada(q=q, P_terca_kN=P, s_terca_m=s, **GEO)
    assert b["M_max_kNm"] == pytest.approx(a["M_max_kNm"], rel=1e-9)
    assert b["R_A_kN"] - a["R_A_kN"] == pytest.approx(0.5 * P)
    assert b["R_B_kN"] == pytest.approx(a["R_B_kN"])


def test_terca_de_ponta_no_beiral():
    q, P, s, a_bal = 5.0, 2.0, 20.25 / 8, 1.135
    a = analisar_biarticulada(q=q, a_bal=a_bal, **GEO)
    b = analisar_biarticulada(q=q, a_bal=a_bal, P_terca_kN=P, s_terca_m=s, **GEO)
    dF = P - P / s * a_bal                          # força na ponta menos o distribuído
    dM = -(P * a_bal - P / s * a_bal ** 2 / 2)      # momento adicional no apoio A
    assert b["M_apoio_A_kNm"] - a["M_apoio_A_kNm"] == pytest.approx(dM, abs=2e-3)
    assert (b["R_A_kN"] + b["R_B_kN"]) - (a["R_A_kN"] + a["R_B_kN"]) == pytest.approx(0.5 * P + dF, abs=1e-3)
    assert b["M_max_kNm"] < a["M_max_kNm"]          # beiral mais pesado alivia o vão
