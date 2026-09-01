"""Issue 12 — referencial único (eixo da peça): cortante ⊥ ao eixo no §6.1.7,
reação vertical no apoio §6.1.5. Coerência N/V/θ."""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.checks.elu.cisalhamento import verifica_cisalhamento
from mlc_projeto.checks.elu.apoio import verifica_apoio


def _setup():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo, mat, 1.5, 0.40, 5.75, pv)
    return geo, mat, load


def test_identidade_decomposicao_eixo():
    """V = R_v·cosθ − H·senθ e N = H·cosθ + R_v·senθ na combinação gov."""
    geo, mat, load = _setup()
    theta = math.atan(math.tan(geo.alpha_rad) / 2.0)
    gov = load.combinacao_ELU_governante()
    Rv, H = gov.V_max_kN, gov.H_kN
    assert gov.V_viga_kN == pytest.approx(Rv * math.cos(theta) - H * math.sin(theta), abs=0.5)
    assert gov.N_viga_kN == pytest.approx(H * math.cos(theta) + Rv * math.sin(theta), abs=0.5)


def test_cisalhamento_usa_cortante_transversal():
    """§6.1.7 usa o cortante ⊥ ao eixo (V_viga), muito menor que R_v vertical."""
    geo, mat, load = _setup()
    r = verifica_cisalhamento(geo, mat, load)
    # V_d é o transversal, e é bem menor que a reação vertical (arco: H grande)
    assert r["V_d_kN"] < r["R_v_vertical_kN"]
    assert r["V_d_kN"] == pytest.approx(load.V_viga_max_ELU(), abs=1e-3)
    assert r["theta_eixo_deg"] == pytest.approx(
        math.degrees(math.atan(math.tan(geo.alpha_rad) / 2.0)), abs=1e-3)


def test_cortante_transversal_e_o_maximo_entre_combinacoes():
    """V_viga_max_ELU pega o máximo entre TODAS as combinações (pode ≠ da de |M|)."""
    geo, mat, load = _setup()
    v_gov_M = abs(load.combinacao_ELU_governante().V_viga_kN)
    v_max = load.V_viga_max_ELU()
    assert v_max >= v_gov_M                      # o máximo domina o gov-|M|
    # e coincide com o máximo explícito sobre as combinações ELU
    esperado = max(abs(c.V_viga_kN) for c in load.combinacoes_ELU().values())
    assert v_max == pytest.approx(esperado)


def test_apoio_usa_reacao_vertical():
    """§6.1.5: bearing na face horizontal ⇒ R_d = reação vertical R_v."""
    geo, mat, load = _setup()
    r = verifica_apoio(geo, mat, load, l_ap=0.40)
    assert r["R_d_kN"] == pytest.approx(load.V_max_ELU(), abs=1e-3)
    assert "referencial" in r


def test_shear_menos_conservador_que_reacao_vertical():
    """Usar V transversal (correto) dá η menor que usar R_v (antigo, conservador)."""
    geo, mat, load = _setup()
    r = verifica_cisalhamento(geo, mat, load)
    # η com V transversal vs η hipotético com R_v (mesma seção)
    eta_transv = r["eta"]
    eta_Rv = eta_transv * r["R_v_vertical_kN"] / r["V_d_kN"]
    assert eta_transv < eta_Rv
    assert eta_transv < 0.5      # passa folgado (arco: pouco cortante transversal)
