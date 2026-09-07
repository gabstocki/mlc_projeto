"""
Testes de regressão — F-01 (auditoria adversarial v2).

Achado
------
A pressão de vento atua PERPENDICULARMENTE à superfície do telhado. O modelo
aplicava corretamente a componente VERTICAL (a projeção horizontal cancela o
1/cos α), mas a componente HORIZONTAL

    H_cob = Σ c_i · q · A_água,i · sen α

— que NÃO se cancela entre as duas águas quando c_esq ≠ c_dir — não era
calculada em lado nenhum. Todos os padrões de Cpe usados (Tab. 10 e Tab. 25)
têm c_esq ≠ c_dir.

Medida na auditoria: 57,8 kN de cálculo omitidos contra 38,3 kN incluídos
(1,51×) na demanda do contraventamento transversal.

Forma fechada (por pórtico, área tributária já embutida em w):
    H_cob = (w_esq − w_dir) · (L/2) · tan α          [kN]
sendo w_esq/w_dir as cargas lineares (kN/m de projeção horizontal) de CADA
meia-água. O peso próprio, sendo simétrico e vertical, não contribui.
"""
import math

import pytest

from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento, GAMMA_Q
from mlc_projeto.checks.elu.contraventamento_transversal import demanda_transversal


def _setup(g_area: float = 0.82):
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial("GL24h", 3, "curta")
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=geo.h_ap - geo.h0, h=7.0, dist_portico=5.75,
        l2=40.5, n_tramos=2, obstrucoes_sob_cobertura=True,
    )
    load = carregamentos_com_vento(
        geo, mat, g_area, 0.40, 5.75, pv,
        b_pilar=0.32, h_pilar=0.27, n_pilares_linha=9, n_linhas_portico=3,
        L_cob_m=46.0, B_cob_m=40.5, empuxo_desenvolve=False,
    )
    return geo, mat, load, pv


# ── A componente existe e vale a forma fechada ────────────────────────────────

def test_combinacao_expoe_componente_horizontal_da_cobertura():
    geo, mat, load, pv = _setup()
    tan_a = math.tan(geo.alpha_rad)
    achou_assimetrico = False
    for nome, c in load.combinacoes_ELU().items():
        esperado = (c.q_esq - c.q_dir) * (geo.L / 2.0) * tan_a
        assert c.H_cob_kN == pytest.approx(esperado, abs=1e-6), nome
        if abs(c.q_esq - c.q_dir) > 1e-9:
            achou_assimetrico = True
            assert abs(c.H_cob_kN) > 0.0, nome
    assert achou_assimetrico, "nenhum padrão assimétrico — teste não exercita o achado"


def test_h_cob_reconstruido_dos_coeficientes_de_pressao():
    """Reconstrução independente a partir de c_pe, q e da área REAL da água."""
    geo, mat, load, pv = _setup()
    q = pv.q
    A_agua = (geo.L / 2.0) / math.cos(geo.alpha_rad) * load.area_trib
    sen_a = math.sin(geo.alpha_rad)

    for p in load.padroes_vento:
        c = load.combinacoes[f"ELU_W_{p['id']}"]
        esperado = GAMMA_Q * (p["C_esq"] - p["C_dir"]) * q * A_agua * sen_a
        assert c.H_cob_kN == pytest.approx(esperado, rel=1e-9)


def test_h_cob_nulo_sem_vento_e_para_carga_simetrica():
    geo, mat, load, pv = _setup()
    assert load.combinacoes["ELU_Q"].H_cob_kN == pytest.approx(0.0, abs=1e-12)
    for nome in ("ELS_S1", "ELS_S2", "ELS_S3"):
        assert load.combinacoes[nome].H_cob_kN == pytest.approx(0.0, abs=1e-12)


def test_h_cob_independe_do_peso_proprio():
    """G é simétrico e vertical: não gera força horizontal na cobertura."""
    _, _, load_a, _ = _setup(g_area=0.82)
    _, _, load_b, _ = _setup(g_area=1.64)
    for nome, ca in load_a.combinacoes_ELU().items():
        cb = load_b.combinacoes_ELU()[nome]
        assert ca.H_cob_kN == pytest.approx(cb.H_cob_kN, abs=1e-9), nome


def test_envelope_h_cobertura_e_o_maximo_absoluto():
    geo, mat, load, pv = _setup()
    esperado = max(abs(c.H_cob_kN) for c in load.combinacoes_ELU().values())
    assert load.H_cobertura_max_ELU() == pytest.approx(esperado, abs=1e-9)
    assert load.H_cobertura_max_ELU() > 0.0


# ── A componente entra na demanda transversal ─────────────────────────────────

def test_demanda_transversal_inclui_componente_da_cobertura():
    geo, mat, load, pv = _setup()
    dem = demanda_transversal(
        load, pv, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        n_frames=9, n_porticos=2,
    )
    assert dem["H_cob_kN"] > 0.0
    assert dem["H_tr_kN"] == pytest.approx(
        dem["H_vento_topo_kN"] + dem["H_cob_kN"] + dem["H_imp_kN"], abs=5e-3
    )
    # A força omitida é da mesma ordem (maior, de facto) que a considerada.
    assert dem["H_cob_kN"] > dem["H_vento_topo_kN"]


def test_h_cob_total_e_por_portico_vezes_n_frames():
    geo, mat, load, pv = _setup()
    n_frames = 9
    dem = demanda_transversal(
        load, pv, H_pilar_m=7.0, b_pilar=0.32, h_pilar=0.27,
        n_frames=n_frames, n_porticos=2,
    )
    assert dem["H_cob_kN"] == pytest.approx(
        load.H_cobertura_max_ELU() * n_frames, rel=1e-9
    )
