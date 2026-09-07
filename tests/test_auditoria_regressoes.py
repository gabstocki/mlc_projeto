"""Regressões da auditoria técnica independente (2026-09-04).

Os casos estão marcados ``xfail(strict=True)`` porque documentam defeitos
confirmados no código de produção ainda não corrigido.  A marcação mantém a
suíte executável sem transformar achados conhecidos em falsos sucessos; após a
correção, um XPASS estrito falhará e obrigará a promover o caso a teste normal.

Os valores esperados são obtidos por equações fechadas ou reconstruções
independentes, não pela função de produção sob teste.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pytest

from mlc_projeto.checks.els.creep import calcular_flecha_inst
from mlc_projeto.checks.elu.estabilidade_global import verificar_estabilidade_global
from mlc_projeto.checks.elu.fixacao_telha import verificar_fixacao_telha_succao
from mlc_projeto.checks.elu.flexao import verifica_flexao
from mlc_projeto.checks.elu.icamento import verificar_icamento
from mlc_projeto.checks.elu.misula import verifica_misula
from mlc_projeto.checks.elu.pilares import verifica_pilar
from mlc_projeto.connections.connections import dimensionar_sapata
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.loads import carregamentos_com_vento
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import (
    ParametrosVento,
    calcular_vento,
    validar_dominio_cobertura_isolada,
    coeficientes_tabela25,
    forca_vento_paralelo_cumeeira,
    padroes_cpe_tabela25,
)
from mlc_projeto.predim.predim import eta_flexo_compressao_viga


AUDIT_XFAIL = pytest.mark.xfail(
    strict=True,
    reason="achado confirmado; código de produção ainda não corrigido",
)


def _modelo(*, empuxo: bool = False):
    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32, n_pts=1001)
    mat = GlulamMaterial("GL24h", 3, "curta")
    vento = ParametrosVento(
        V0=45.0,
        S1=1.0,
        categoria="IV",
        classe="B",
        S3=1.0,
        L=geo.L,
        H1=geo.h_ap - geo.h0,
        h=7.0,
        dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo,
        mat=mat,
        g_area=0.80,
        q_area=0.40,
        L_t=5.75,
        params_vento=vento,
        empuxo_desenvolve=empuxo,
    )
    return geo, mat, vento, load


def test_aud_001_s2_depende_da_altura_de_referencia():
    """NBR 6123:2023: S2=b_m*F_r*(z/10)^p, não uma tabela sem z."""
    # Categoria IV, classe B: b_m=0,85; F_r=0,98; p=0,125.
    p = ParametrosVento(categoria="IV", classe="B", h=29.0, H1=1.0)
    esperado = 0.85 * 0.98 * (30.0 / 10.0) ** 0.125
    assert p.S2 == pytest.approx(esperado, rel=1e-12)


def test_aud_002_tabela25_rejeita_geometria_fora_do_dominio():
    """Cobertura a duas águas: h deve ser pelo menos 0,5·ℓ2.

    O relatório da auditoria admite DUAS saídas para este achado: "erro de
    domínio **ou** rota normativa alternativa documentada". A Onda 2
    implementou a segunda, que é a que a norma de facto prescreve — §7.2.1,
    último parágrafo: fora do domínio, a cobertura é calculada como edificação
    fechada de mesma cobertura, com c_pi = +0,8 ou −0,3. O teste passou a
    verificar essa saída, mais forte que a simples recusa.

    O contrato essencial permanece: com h < 0,5·ℓ2 os coeficientes da Tabela 25
    NÃO podem ser usados.
    """
    p = ParametrosVento(L=20.25, H1=1.785, h=7.0)
    assert p.h < 0.5 * p.l2_efetivo                    # fora do domínio
    assert p.rota_normativa == "edificacao_fechada"    # Tab.25 não se aplica

    res = calcular_vento(p)
    assert res.padroes_90, "a rota alternativa deve produzir padrões de carga"
    assert all(pad["tipo"] == "edificacao_fechada_com_cpi" for pad in res.padroes_90)
    assert all(pad["c_pi"] in (0.8, -0.3) for pad in res.padroes_90)

    # Forçar a rota da Tabela 25 fora do domínio continua sendo erro explícito.
    with pytest.raises(ValueError, match="h.*0,5"):
        validar_dominio_cobertura_isolada(p)


def test_aud_003_atrito_longitudinal_usa_equacao_especifica_da_cobertura_isolada():
    """NBR 6123:2023 7.2.2: Ft=0,5*q*a*b, englobando as duas faces."""
    p = ParametrosVento()
    a, b = 46.0, 40.50
    r = forca_vento_paralelo_cumeeira(
        p,
        b_pilar=0.32,
        h_pilar=0.27,
        n_pilares_linha=9,
        n_linhas_portico=3,
        L_cob_m=a,
        B_cob_m=b,
    )
    esperado = 0.5 * p.q * a * b
    assert r["F_friccao_kN"] == pytest.approx(esperado, rel=1e-4)


def test_aud_004_tabela25_gera_somente_pares_simultaneos_normativos():
    """Cada Cpb deve atuar simultaneamente com o Cps do mesmo carregamento."""
    tg = math.tan(math.radians(10.0))
    coef = coeficientes_tabela25(tg)
    esperados = {
        (coef[c]["Cpb"], coef[c]["Cps"])
        for c in ("C1", "C2")
    } | {
        (coef[c]["Cps"], coef[c]["Cpb"])
        for c in ("C1", "C2")
    }
    obtidos = {(p["C_esq"], p["C_dir"]) for p in padroes_cpe_tabela25(tg)}
    assert obtidos == esperados


def test_aud_005_fixacao_local_exige_s2_classe_a():
    """Elementos de vedação e suas fixações usam a classe A do fator S2."""
    p_global = ParametrosVento(categoria="IV", classe="B")
    with pytest.raises(ValueError, match="classe A"):
        verificar_fixacao_telha_succao(p_global, s_terca=2.53, e_fix_m=0.20)


def _m0_biapoiada(x: np.ndarray, L: float, qe: float, qd: float) -> np.ndarray:
    """Momento isostático independente para UDL por meia-viga."""
    wa = qe * L / 2.0
    wb = qd * L / 2.0
    rb = (wa * (L / 4.0) + wb * (3.0 * L / 4.0)) / L
    ra = wa + wb - rb
    left = ra * x - qe * x**2 / 2.0
    right = (
        ra * x
        - wa * (x - L / 4.0)
        - qd * (x - L / 2.0) ** 2 / 2.0
    )
    return np.where(x <= L / 2.0, left, right)


def test_aud_006_misula_respeita_o_modelo_sem_empuxo():
    """A verificação local deve usar o mesmo desenvolve_empuxo do gerador."""
    geo, mat, _, load = _modelo(empuxo=False)
    atual = verifica_misula(geo, mat, load)

    x = geo.x
    h = geo.h(x)
    tan_a = math.tan(geo.alpha_rad)
    esperado = 0.0
    for comb in load.combinacoes_ELU().values():
        if abs(comb.q_esq) < 1e-12 and abs(comb.q_dir) < 1e-12:
            continue
        mc = mat.com_duracao(comb.duracao)
        k_cmp = 1.0 / math.sqrt(
            1.0
            + (mc.f_m_d / (1.5 * mc.f_v_d) * tan_a) ** 2
            + (mc.f_m_d / mc.f_c90_d * tan_a**2) ** 2
        )
        k_tra = 1.0 / math.sqrt(
            1.0
            + (mc.f_m_d / (0.75 * mc.f_v_d) * tan_a) ** 2
            + (mc.f_m_d / mc.f_t90_d * tan_a**2) ** 2
        )
        moment = _m0_biapoiada(x, geo.L, comb.q_esq, comb.q_dir) * 1e3
        sigma = 6.0 * np.abs(moment) / (geo.b * h**2)
        k = np.where(moment >= 0.0, k_cmp, k_tra)
        esperado = max(esperado, float(np.max(sigma / (k * mc.f_m_d))))

    assert atual["eta"] == pytest.approx(esperado, rel=5e-4)


def test_aud_007_forca_nocional_nao_passa_quando_h_de_referencia_e_zero():
    """Himp/Hed com Hed=0 é indefinido/infinito, nunca zero."""
    geo, mat, _, load = _modelo(empuxo=False)
    r = verificar_estabilidade_global(
        geo,
        mat,
        load,
        H_pilar_m=7.0,
        b_pilar=0.32,
        h_pilar=0.27,
        contravento_vertical_ok=True,
        contravento_transversal_ok=True,
    )
    assert math.isinf(r["H_imp_over_H"])
    assert r["ok_nocional"] is False
    assert r["ok"] is False


def test_aud_008_integracao_els_reproduz_viga_biapoiada_com_udl():
    """Benchmark: wmax=5*q*L^4/(384*E*I), erro numérico menor que 0,1%."""
    L, b, h, q = 10.0, 0.20, 0.40, 1000.0
    geo = GeometriaViga(L=L, h0=h, alpha_deg=0.0, b=b, n_pts=2001)
    mat = GlulamMaterial("GL24h", 3, "longa")
    x = geo.x
    moment = q * x * (L - x) / 2.0
    obtido, _ = calcular_flecha_inst(geo, mat, moment)
    esperado = 5.0 * q * L**4 / (384.0 * mat.E0_mean * (b * h**3 / 12.0))
    assert obtido == pytest.approx(esperado, rel=1e-3)


def test_aud_009_predimensionamento_usa_interacao_linear_de_estabilidade():
    """EC5 6.3.2: termo axial é linear quando k_c é aplicado."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    b, h, L = 0.30, 0.60, 8.0
    moment, normal = 120e3, 350e3
    obtido = eta_flexo_compressao_viga(mat, b, h, L, 2.0, moment, normal)

    area = b * h
    inertia = b * h**3 / 12.0
    radius = math.sqrt(inertia / area)
    slender = L / radius
    rel = slender / math.pi * math.sqrt(mat.f_c0_k / mat.E0_05)
    k = 0.5 * (1.0 + 0.1 * (rel - 0.3) + rel**2)
    kc = min(1.0 / (k + math.sqrt(k**2 - rel**2)), 1.0)
    sigma_c = normal / area
    sigma_m = moment / (b * h**2 / 6.0)
    esperado = sigma_c / (kc * mat.f_c0_d) + sigma_m / mat.f_m_d
    assert obtido == pytest.approx(esperado, rel=1e-12)


def test_aud_010_icamento_aplica_expoentes_da_equacao_635():
    """EC5 6.35: (sigma_m/(kcrit*fmd))^2 + sigma_c/(kc*fc0d)."""
    geo, mat, _, _ = _modelo(empuxo=False)
    r = verificar_icamento(geo, mat)
    bend = r["sigma_m_pos_MPa"] / (r["k_crit"] * r["f_m_d_MPa"])
    comp = r["sigma_c_MPa"] / (r["k_c_z"] * (mat.com_duracao("instantanea").f_c0_d / 1e6))
    esperado = bend**2 + comp
    assert r["eta_LTB"] == pytest.approx(esperado, rel=2e-2, abs=2e-4)


def test_aud_011_pilar_verifica_as_duas_interacoes_623_624():
    """Flexão em z ainda requer a equação conjugada governada por kc,y.

    CORREÇÃO DO VALOR ESPERADO DA AUDITORIA (Onda 1) — único caso em toda a
    suíte em que o esperado foi alterado, e não para acompanhar o código.

    A auditoria codificou k_m no termo de flexão da Eq. (6.24) e omitiu-o na
    (6.23). EN 1995-1-1:2004 §6.3.2(3) faz o oposto: em cada equação, k_m
    reduz o termo de flexão do eixo SECUNDÁRIO — o mesmo padrão de (6.19)/
    (6.20) em §6.2.4:

        (6.23)  σc/(kc,y·fc0d) + σm,y/fm,d + km·σm,z/fm,d ≤ 1
        (6.24)  σc/(kc,z·fc0d) + km·σm,y/fm,d + σm,z/fm,d ≤ 1

    Com σm,y = 0 e σm,z ≠ 0 (este caso), a (6.23) recebe km·σm,z e a (6.24)
    recebe σm,z pleno. O esperado da auditoria dava η = 0,594640; a aplicação
    correta da norma dá η = 0,580026 — ambas governadas pela (6.23), diferença
    de 2,52%. O esperado continua vindo da fonte normativa e não da função sob
    teste, que é o que a regra "não alterar o esperado" protege.
    """
    mat = GlulamMaterial("GL24h", 3, "curta")
    b, h, length, normal, moment = 0.32, 0.27, 7.0, 282.172, 3.017
    r = verifica_pilar(mat, b, h, length, normal, M_d_kNm=moment, eixo="z")

    area = b * h
    iy = math.sqrt((b * h**3 / 12.0) / area)
    iz = math.sqrt((h * b**3 / 12.0) / area)

    def kc(radius: float) -> float:
        rel = (length / radius) / math.pi * math.sqrt(mat.f_c0_k / mat.E0_05)
        k = 0.5 * (1.0 + 0.1 * (rel - 0.3) + rel**2)
        return min(1.0 / (k + math.sqrt(k**2 - rel**2)), 1.0)

    sigma_c = normal * 1e3 / area
    sigma_mz = moment * 1e3 / (h * b**2 / 6.0)
    k_m = 0.7  # seção retangular — EN 1995-1-1:2004 §6.1.6(2)
    eta_623 = sigma_c / (kc(iy) * mat.f_c0_d) + k_m * sigma_mz / mat.f_m_d
    eta_624 = sigma_c / (kc(iz) * mat.f_c0_d) + sigma_mz / mat.f_m_d
    assert r["eta"] == pytest.approx(max(eta_623, eta_624), rel=5e-4)
    # O achado original permanece verificado: uma única equação não basta.
    assert r["eta_6_23"] == pytest.approx(eta_623, rel=5e-4)
    assert r["eta_6_24"] == pytest.approx(eta_624, rel=5e-4)


def test_aud_011b_pilar_compressao_pura_usa_utilizacao_linear():
    """Compressão com flambagem: eta=sigma_c/(k_c*f_c0d), sem quadrado."""
    mat = GlulamMaterial("GL24h", 3, "curta")
    r = verifica_pilar(mat, b=0.32, h=0.27, H=7.0, N_d=282.172)
    esperado = r["sigma_c_MPa"] / (r["k_c"] * r["f_c0_d_MPa"])
    assert r["eta"] == pytest.approx(esperado, rel=5e-4)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"L": 0.0, "h0": 1.0, "alpha_deg": 10.0, "b": 0.30},
        {"L": 10.0, "h0": 1.0, "alpha_deg": 10.0, "b": 0.0},
        {"L": 10.0, "h0": 1.0, "alpha_deg": float("nan"), "b": 0.30},
    ],
)
def test_aud_012_geometria_invalida_e_rejeitada(kwargs):
    with pytest.raises(ValueError):
        GeometriaViga(**kwargs)


def test_aud_013_secao_nula_nunca_e_aprovada():
    mat = GlulamMaterial("GL24h", 3, "curta")
    with pytest.raises(ValueError):
        verifica_pilar(mat, b=0.0, h=0.30, H=7.0, N_d=100.0)


def test_aud_014_viga_variavel_procura_maximo_de_tensao_nao_de_momento():
    """Em seção variável, max|M| e max|M/W(x)| não são equivalentes."""
    geo, mat, _, load = _modelo(empuxo=False)
    atual = verifica_flexao(geo, mat, load)
    gov = load.combinacao_ELU_governante()
    moment = _m0_biapoiada(geo.x, geo.L, gov.q_esq, gov.q_dir) * 1e3
    sigma_max = float(np.max(6.0 * np.abs(moment) / (geo.b * geo.h(geo.x) ** 2)))
    assert atual["sigma_m_MPa"] == pytest.approx(sigma_max / 1e6, rel=5e-4)


def test_aud_015_parametros_ndp_possuem_identificacao_do_national_annex():
    """Fatores configuráveis devem registrar a origem EN/NA, sem escolha implícita."""
    _, _, _, load = _modelo(empuxo=False)
    assert load.national_annex
    assert load.ndp_source


def test_aud_016_relatorio_nao_declara_versao_obsoleta_do_vento():
    """O relatório deve declarar uma única edição controlada da NBR 6123."""
    report_path = Path(__file__).parents[1] / "mlc_projeto" / "output" / "report.py"
    source = report_path.read_text(encoding="utf-8")
    assert "NBR 6123:1988" not in source


def test_aud_017_sapata_expoe_verificacao_completa_de_ancoragem():
    """A aprovação não pode omitir modos de falha dos chumbadores/concreto.

    CORREÇÃO DO TESTE DA AUDITORIA (Onda 3) — terceira e última.
    O teste original exigia `en_1992_4_verificado is True` numa chamada SEM
    qualquer dado de ancoragem, o que contradiz o próprio relatório: o achado
    AUD-017 diz "Expected result: **bloqueio por dados insuficientes**" e
    recomenda "exigir dados certificados e propagar NOT VALIDATED ao resultado
    global". Marcar como verificado sem embutimento, borda, grupo, classe de
    concreto nem ETA seria exatamente a falsa aprovação que o achado denuncia.

    O teste passa a verificar o contrato nos dois sentidos.
    """
    geo, _, _, load = _modelo(empuxo=False)

    # Sem dados: bloqueio explícito, e a pré-seleção não vale como aprovação.
    r = dimensionar_sapata(load, geo)
    assert r["en_1992_4_verificado"] is False
    assert r["produto_chumbador_verificado"] is False
    assert r["status_ancoragem"] == "NOT VALIDATED"
    assert r["ok"] is False
    assert r["modos_en_1992_4_pendentes"], "os modos de rotura devem ser listados"

    # Com o conjunto completo de dados certificados: contrato cumprido.
    # O contrato mudou de PÓS-INSTALADO para MOLDADO COM CABEÇA (decisão de
    # projeto): não há ETA de produto — o lado do concreto é coberto pelos
    # modelos da norma — e passa a exigir a área de apoio da cabeça.
    completo = dimensionar_sapata(load, geo, dados_ancoragem={
        "h_ef_mm": 400.0,
        "A_cabeca_mm2": 2375.0,
        "c_borda_mm": 600.0,
        "s_grupo_mm": 400.0,
        "classe_concreto": "C25/30",
        "concreto_fissurado": True,
        "verificacao_en1992_4": "CEN/TS 1992-4-2:2009 §6.2.4/6.2.5/6.3.4/6.4",
    })
    assert completo["en_1992_4_verificado"] is True
    assert completo["produto_chumbador_verificado"] is True
    assert completo["status_ancoragem"] == "VERIFICADO"


def test_aud_018_fem_reproduz_a_condicao_de_contorno_selecionada():
    """O benchmark FEM deve aceitar o mesmo modelo com ou sem desenvolvimento de H."""
    module_path = (
        Path(__file__).parents[1] / "mlc_projeto" / "opensees" / "opensees_model.py"
    )
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    func = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "analisar_fem"
    )
    nomes = [arg.arg for arg in func.args.args]
    assert "desenvolve_empuxo" in nomes
