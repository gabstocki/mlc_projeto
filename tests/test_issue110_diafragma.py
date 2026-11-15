"""Issue 110 — caminho da força transversal pelo diafragma da cobertura."""

import pytest

from mlc_projeto.checks.elu.diafragma_cobertura import verificar_diafragma_cobertura
from mlc_projeto.opensees.diafragma_espacial import analisar_diafragma

BASE = dict(L_T=5.75, n_eixos=9, s=20.25 / 8, n_faixas=16, A_terca_m2=0.08,
            A_viga_m2=0.60, E_mlc_kPa=11.5e6, C_h_frontao_kNpm=5347.6,
            C_h_long_kNpm=7071.9, H_tr_kN=139.6)


def test_sem_alma_nas_baias_intermediarias_e_mecanismo():
    r = analisar_diafragma(d_diag_mm_por_baia=[36] + [None] * 6 + [36], **BASE)
    assert r["mecanismo"] is True


def test_reacoes_dos_frontoes_equilibram_a_carga():
    r = analisar_diafragma(d_diag_mm_por_baia=[36] + [12] * 6 + [36], **BASE)
    assert not r["mecanismo"]
    assert sum(r["R_frontoes_kN"]) == pytest.approx(BASE["H_tr_kN"], rel=1e-3)
    # simetria: metade em cada frontão
    assert r["R_frontoes_kN"][0] == pytest.approx(r["R_frontoes_kN"][1], rel=1e-2)


def test_forca_no_portico_central_vai_aos_dois_frontoes():
    r = analisar_diafragma(d_diag_mm_por_baia=[36] + [12] * 6 + [36], F_portico_kN=100.0,
                           portico_carregado=4, **BASE)
    assert r["R_frontoes_kN"] == pytest.approx([50.0, 50.0], abs=0.2)
    assert r["uy_portico_mm"][4] == max(r["uy_portico_mm"])


def test_verificacao_reduz_a_rigidez_frente_ao_diafragma_rigido():
    v = verificar_diafragma_cobertura(d_cvh_mm=36.0, H_pilar_m=7.0, **{
        k: BASE[k] for k in BASE})
    assert v["sem_alma_mecanismo"] is True
    assert v["K_eq_kNpm"] < 2 * BASE["C_h_frontao_kNpm"]
    assert v["d_diafragma_mm"] >= 12.0 and v["eta_diag"] <= 0.90
