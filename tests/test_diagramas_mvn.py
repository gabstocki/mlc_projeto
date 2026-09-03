"""Issue 27 — Diagramas M(x), V(x), N(x) derivados do M(x) real (anexo de análise).

Verifica a derivação rigorosa no eixo da peça:
    S = dM0/dx ; N = H·cosθ + S·senθ ; V = S·cosθ − H·senθ.
"""

import math

import numpy as np
import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento


def _load():
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(V0=45, S1=1, categoria="IV", classe="B", S3=1,
                         L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75)
    load = carregamentos_com_vento(geo=geo, mat=mat, g_area=0.823, q_area=0.40,
                                   L_t=5.75, params_vento=pv)
    return geo, load


def test_M_bate_com_analise():
    """M_max do diagrama = M_max da combinação governante."""
    geo, load = _load()
    d = load.diagramas_MVN_ELU()
    gov = load.combinacao_ELU_governante()
    assert d["M_max_kNm"] == pytest.approx(gov.M_max_kNm, rel=1e-2)


def test_N_apoio_bate():
    """N nos apoios = N_viga (empuxo projetado no eixo)."""
    geo, load = _load()
    d = load.diagramas_MVN_ELU()
    gov = load.combinacao_ELU_governante()
    assert d["N"][0] == pytest.approx(gov.N_viga_kN, rel=1e-2)
    assert d["N"][-1] == pytest.approx(gov.N_viga_kN, rel=1e-2)


def test_V_apoio_bate():
    """V nos apoios = V_viga (cortante ⊥ ao eixo no apoio)."""
    geo, load = _load()
    d = load.diagramas_MVN_ELU()
    gov = load.combinacao_ELU_governante()
    assert abs(d["V"][0]) == pytest.approx(abs(gov.V_viga_kN), abs=2.0)


def test_V_derivado_nao_e_aproximacao_viga_simples():
    """V_ELU() agora é o V real (⊥ eixo), diferente de q·(L/2−x)."""
    geo, load = _load()
    d = load.diagramas_MVN_ELU()
    V_real = np.asarray(d["V"])
    q = load.combinacao_ELU_governante().q_tot
    V_aprox = q * (geo.L / 2 - d["x"])
    # devem diferir (o real projeta H no eixo inclinado; salto no ápice)
    assert not np.allclose(V_real, V_aprox, atol=1.0)
    assert len(load.V_ELU()) == len(d["x"])   # V_ELU usa o diagrama real


def test_salto_de_V_no_apice():
    """No ápice, θ muda de sinal → V salta ~2·H·sen(θ)."""
    geo, load = _load()
    d = load.diagramas_MVN_ELU()
    x, V, H = d["x"], d["V"], d["H_kN"]
    i_mid = int(np.argmin(np.abs(x - geo.L / 2)))
    theta = math.atan(math.tan(geo.alpha_rad) / 2.0)
    salto = abs(V[i_mid - 2] - V[i_mid + 2])
    assert salto == pytest.approx(2 * H * math.sin(theta), rel=0.15)


def test_arrays_consistentes():
    geo, load = _load()
    d = load.diagramas_MVN_ELU()
    n = len(d["x"])
    assert len(d["M"]) == n and len(d["V"]) == n and len(d["N"]) == n
    assert d["comb"] == load.combinacao_ELU_governante().nome
