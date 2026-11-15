"""
Concepção revista das ligações: compressão por contato, tração por uma peça de aço.

  · tirante interno nos pilares correntes (EN 1993-1-8 Tab. 3.4);
  · nó do pilar bipartido por contato de topo de fibra;
  · chapas duplas nas escoras e no montante (quatro planos de corte por cavilha).
"""
import math

import pytest

from mlc_projeto.checks.elu.no_contraventamento import dimensionar_ligacao_axial_escora
from mlc_projeto.checks.elu.pilar_bipartido import verificar_pilar_bipartido
from mlc_projeto.connections.pilarete import verificar_pilarete
from mlc_projeto.connections.tirante_interno import A_S_MM2, dimensionar_tirante
from mlc_projeto.core.materials import GlulamMaterial

MAT = GlulamMaterial("GL24h", 3, "curta")


def test_tirante_menor_barra_com_eta_075():
    t = dimensionar_tirante(rotulo="t", N_t_kN=169.0)
    F = 0.9 * 800 * A_S_MM2[t["d_mm"]] / 1.25 / 1e3
    assert t["F_t_Rd_kN"] == pytest.approx(F, abs=0.1)
    assert 169.0 / F <= 0.75
    menores = [d for d in A_S_MM2 if d < t["d_mm"]]
    assert all(169.0 / (0.9 * 800 * A_S_MM2[d] / 1.25 / 1e3) > 0.75 for d in menores)
    assert t["furo_pilar_mm"] == t["d_mm"] + 16


def test_chapa_de_topo_do_pilarete_com_carga_central_e_janela():
    kw = dict(rotulo="t", N_c_kN=200, N_t_kN=169, V_kN=48.5, h_m=0.3, b_pilar_mm=320,
              h_pilar_mm=270)
    linha = verificar_pilarete(**kw)
    ponto = verificar_pilarete(**kw, tirante={"arruela_chapa_mm": 80.0})
    assert "secao_janela" in ponto["etas"]
    # carga concentrada no centro (porca) pede chapa ao menos tão grossa
    assert ponto["chapa_topo_mm"][2] >= linha["chapa_topo_mm"][2]


def test_chapas_duplas_aumentam_a_resistencia_por_cavilha():
    s = dimensionar_ligacao_axial_escora(236.0, MAT, 0.20, 0.40, n_chapas=1)
    d = dimensionar_ligacao_axial_escora(236.0, MAT, 0.20, 0.40, n_chapas=2)
    assert d["F_v_Rd_pino_kN"] > 1.25 * s["F_v_Rd_pino_kN"]
    assert d["n_pinos"] < s["n_pinos"] and d["ok"]


def test_no_do_bipartido_por_contato():
    r = verificar_pilar_bipartido(rotulo="t", mat=MAT, b_viga_m=0.32, L_x_m=6.7, L_y_m=7.7,
                                  R_grav_kN=106.0, R_up_kN=100.0, D_kN=173.0, F_up_no_kN=30.0)
    A = 160 * 320 - 24 * 320
    assert r["no"]["sigma_c0_MPa"] == pytest.approx(173.0e3 / A, rel=1e-3)
    assert r["partes"]["no_contato"] < 0.5
    assert r["no"]["n_pinos"] == 2                       # só posicionamento e arrancamento
