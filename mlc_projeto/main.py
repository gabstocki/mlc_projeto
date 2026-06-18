"""
main.py — Orquestrador do pipeline de verificação MLC. v4

Sistema estrutural: Pórtico de 3 rótulas
    - Rótulas nas bases dos pilares
    - Rótula na cumeeira
    - M_max viga ≈ 75% menor que pórtico rígido
    - Ligações simples — sem transmissão de momento

Pipeline completo:
    Fase 0 — Dados de entrada
    Fase 1 — Pré-dimensionamento (varredura opcional)
    Fase 2 — Verificações ELU (viga + pilar)
    Fase 3 — Verificações ELS
    Fase 4 — Ligações
    Fase 5 — Relatório

Dados do projeto:
    Galpão estacionamento em MLC GL24h
    Vão 20,25 m | EC5 + EN 1990 + NBR 6123
    STOCKI Engenharia Estrutural | Gabriel Stocki CREA-PR 195315/D
"""

from mlc_projeto.core.geometry   import GeometriaViga
from mlc_projeto.core.materials  import GlulamMaterial
from mlc_projeto.core.wind       import ParametrosVento
from mlc_projeto.core.loads      import carregamentos_com_vento

from mlc_projeto.predim.predim   import pre_dimensionar, relatorio

from mlc_projeto.checks.elu.cumeeira          import verifica_cumeeira
from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral
from mlc_projeto.checks.elu.flexao            import verifica_flexao
from mlc_projeto.checks.elu.cisalhamento      import verifica_cisalhamento
from mlc_projeto.checks.elu.apoio             import verifica_apoio
from mlc_projeto.checks.elu.flexo_compressao  import verifica_flexo_compressao
from mlc_projeto.checks.els.deflection_els    import verificar_ELS

from mlc_projeto.connections.connections      import (
    dimensionar_ligacoes, relatorio_ligacoes
)
from mlc_projeto.output.report                import gerar_relatorio
from mlc_projeto.visualization.viz_3d         import visualizar_galpao


# ── Dados do projeto ──────────────────────────────────────────────────────────

GEO_PARAMS = dict(
    L         = 20.25,   # m — vão de cada pórtico
    h0        = 0.60,    # m — altura da seção no apoio
    alpha_deg = 4.5,     # graus — inclinação da cumeeira
    b         = 0.26,    # m — largura da seção
)

MAT_CURTA = dict(
    classe         = "GL24h",
    classe_servico = 2,
    duracao        = "curta",   # vento dominante — ELU_C2
)

MAT_LONGA = dict(
    classe         = "GL24h",
    classe_servico = 2,
    duracao        = "longa",   # ELS — fluência
)

VENTO_PARAMS = dict(
    V0           = 45.0,
    S1           = 1.0,
    categoria    = "IV",
    classe       = "B",
    S3           = 1.0,
    L            = 20.25,
    H1           = 1.0,
    h            = 7.0,
    dist_portico = 5.75,
)

G_AREA = 1.50   # kN/m²
Q_AREA = 0.25   # kN/m²
L_T    = 5.75   # m — vão das terças
S      = 2.53   # m — espaçamento entre terças (3 apoios por meia água)

# Pilares
B_PILAR = 0.20   # m
H_PILAR = 0.20   # m
H_PILAR_ALT = 7.0  # m — altura do pilar

# Terças
B_TERCA = 0.20   # m — largura da seção
H_TERCA = 0.58   # m — altura da seção

# Ligações
D_BASE_MM = 20    # mm — pinos na ligação base
D_CUM_MM  = 30    # mm — pino passante na cumeeira
F_CHU_KN  = 80.0  # kN — resistência por chumbador
L_AP      = 0.50  # m  — placa de apoio

# ── Orquestrador ──────────────────────────────────────────────────────────────

def main(rodar_varredura: bool = False) -> None:
    """Executa o pipeline completo — pórtico de 3 rótulas."""

    print("=" * 72)
    print("  PIPELINE MLC — STOCKI Engenharia Estrutural")
    print("  Pórtico de 3 Rótulas | EC5 EN 1995-1-1 | EN 1990 | NBR 6123")
    print("=" * 72)

    # ── Fase 0: Dados de entrada ──────────────────────────────
    print("\n[FASE 0] Dados de entrada...")

    params_vento = ParametrosVento(**VENTO_PARAMS)
    geo          = GeometriaViga(**GEO_PARAMS)
    mat_curta    = GlulamMaterial(**MAT_CURTA)
    mat_longa    = GlulamMaterial(**MAT_LONGA)

    load = carregamentos_com_vento(
        geo=geo, mat=mat_curta,
        g_area=G_AREA, q_area=Q_AREA,
        L_t=L_T, params_vento=params_vento,
    )

    gov = load.combinacao_ELU_governante()
    print(f"  Geometria : L={geo.L}m | h0={geo.h0}m | "
          f"α={geo.alpha_deg}° | b={geo.b}m | h_ap={geo.h_ap:.3f}m")
    print(f"  Material  : {mat_curta.classe} | CS{mat_curta.classe_servico} | "
          f"k_mod={mat_curta.k_mod:.2f} (ELU) | "
          f"k_def={mat_longa.k_def:.2f} (ELS)")
    print(f"  ELU gov.  : {gov.nome} | M={gov.M_max_kNm:.2f} kN·m | "
          f"V={gov.V_max_kN:.2f} kN | H_fund={gov.H_kN:.2f} kN")
    print(f"  Sistema   : Pórtico de 3 rótulas | "
          f"Área trib.={load.area_trib:.3f} m (L_t/2)")

    # ── Fase 1: Pré-dimensionamento ───────────────────────────
    if rodar_varredura:
        print("\n[FASE 1] Varredura paramétrica...")
        df = pre_dimensionar(
            g_area=G_AREA, q_area=Q_AREA,
            params_vento=params_vento,
            L_v=geo.L, L_t=L_T,
            classe=MAT_CURTA["classe"],
            classe_servico=MAT_CURTA["classe_servico"],
            h0_range=(0.40, 1.20, 0.05),
            alpha_range=(3.0, 8.0, 0.5),
            b_range=(0.10, 0.28, 0.02),
            l_ap_range=(0.20, 0.55, 0.05),
            s_range=(1.00, 2.10, 0.25),
        )
        relatorio(df, n=10)
    else:
        print("\n[FASE 1] Geometria pré-definida "
              "(passe rodar_varredura=True para varredura completa)")

    # ── Fase 2: Verificações ELU ──────────────────────────────
    print("\n[FASE 2] Verificações ELU...")

    res_elu = {}

    # Cumeeira — M=0, η=0 documentado
    res_elu["cumeeira"] = verifica_cumeeira(geo, mat_curta, load)
    _print_eta("Cumeeira §6.4.3", res_elu["cumeeira"])

    # Flambagem lateral
    res_elu["flambagem"] = verifica_flambagem_lateral(
        geo, mat_curta, load, l_1=S
    )
    _print_eta("Flambagem §6.3.3", res_elu["flambagem"])

    # Flexo-compressão da viga (M + N)
    res_elu["flexao"] = verifica_flexao(geo, mat_curta, load, s=S)
    _print_eta("Flexo-comp. viga §6.3.2", res_elu["flexao"])

    # Cisalhamento
    res_elu["cisalhamento"] = verifica_cisalhamento(geo, mat_curta, load)
    _print_eta("Cisalhamento §6.1.7", res_elu["cisalhamento"])

    # Apoio
    res_elu["apoio"] = verifica_apoio(geo, mat_curta, load, l_ap=L_AP)
    _print_eta("Apoio §6.1.5+§6.2.2", res_elu["apoio"])

    # Flexo-compressão consolidada (viga + pilar)
    res_elu["flexo_comp"] = verifica_flexo_compressao(
        geo=geo, mat=mat_curta, load=load,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        H_pilar=H_PILAR_ALT, s=S,
    )
    _print_eta(
        f"Pilar {B_PILAR}×{H_PILAR}m §6.3.2",
        res_elu["flexo_comp"]
    )

    # Terças
    print("\n[FASE 2] Verificações ELU — Terças...")
    from mlc_projeto.checks.elu.tercas import verifica_terca
    from mlc_projeto.core.wind import calcular_vento as _calcular_vento
    _w_C1bv_m2 = _calcular_vento(params_vento).pressoes["C1"]["barlavento_kNm2"]
    res_elu["terca"] = verifica_terca(
        mat       = mat_curta,
        L_t       = L_T,
        s         = S,
        b         = B_TERCA,
        h         = H_TERCA,
        alpha_deg = GEO_PARAMS["alpha_deg"],
        g_k_m2    = G_AREA,
        q_k_m2    = Q_AREA,
        w_kNm2    = _w_C1bv_m2,
    )
    # normalizar chave para interface padrão do pipeline
    res_elu["terca"]["eta"] = res_elu["terca"]["eta_gov"]
    _print_eta("Terça §6.1.6+§6.1.7", res_elu["terca"])

    # ── Fase 3: Verificações ELS ──────────────────────────────
    print("\n[FASE 3] Verificações ELS...")

    res_els = {}
    res_els["ELS"] = verificar_ELS(geo, mat_longa, load)
    _print_eta("ELS §2.3.2.2+Tab.7.2", res_els["ELS"])

    # ── Fase 4: Ligações ──────────────────────────────────────
    print("\n[FASE 4] Ligações...")

    res_lig = dimensionar_ligacoes(
        mat=mat_curta, load=load, geo=geo,
        d_base_mm=D_BASE_MM,
        d_cum_mm=D_CUM_MM,
        F_chu_kN=F_CHU_KN,
    )

    for key, label in [
        ("L1", f"L1 base (d={D_BASE_MM}mm)"),
        ("L2", "L2 cumeeira"),
        ("L3", f"L3 sapata (n_chu={res_lig['L3']['n_chumbadores']})"),
    ]:
        _print_eta(label, res_lig[key])

    # ── Resumo ────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  RESUMO DE TAXAS DE UTILIZAÇÃO — Pórtico de 3 Rótulas")
    print("=" * 72)

    todos_para_relatorio = {**res_elu, **res_els}
    eta_max_val = 0.0

    secoes = [
        ("── ELU Viga ──", [
            "cumeeira", "flambagem", "flexao",
            "cisalhamento", "apoio",
        ]),
        ("── ELU Pilar ──", ["flexo_comp"]),
        ("── ELU Terças ──", ["terca"]),
        ("── ELS ──",        ["ELS"]),
    ]

    for titulo, chaves in secoes:
        print(f"\n  {titulo}")
        for chave in chaves:
            if chave not in todos_para_relatorio:
                continue
            res  = todos_para_relatorio[chave]
            eta  = res["eta"]
            ok   = "✓" if res["ok"] else "✗"
            bar  = "█" * int(eta * 20)
            print(f"  {ok} {chave:<26} η = {eta:.4f}  {bar}")
            eta_max_val = max(eta_max_val, eta)

    print(f"\n  ── Ligações ──")
    for key, label in [("L1","base"),("L2","cumeeira"),("L3","sapata")]:
        r   = res_lig[key]
        ok  = "✓" if r["ok"] else "✗"
        eta = r["eta"]
        bar = "█" * int(eta * 20)
        print(f"  {ok} Ligação {label:<22} η = {eta:.4f}  {bar}")
        eta_max_val = max(eta_max_val, eta)

    print(f"\n  η máximo  = {eta_max_val:.4f}")
    print(f"  H_fund    = {load.H_ELU():.2f} kN  (empuxo → sapata)")
    status = "APROVADO" if eta_max_val <= 1.0 else "REPROVADO"
    print(f"  Status    = {status}")
    print("=" * 72)

    # ── Fase 5: Relatório ─────────────────────────────────────
    gerar_relatorio(todos_para_relatorio, geo, mat_curta)
    print("\nPipeline concluído. Relatório gerado em output/")

    # ── Fase 6: Visualização 3D ───────────────────────────────
    print("\n[FASE 6] Abrindo visualização 3D interativa...")
    visualizar_galpao(
        geo        = geo,
        resultados = {**res_elu, **res_els,
                      "L1": res_lig["L1"],
                      "L2": res_lig["L2"],
                      "L3": res_lig["L3"]},
        H_pilar    = H_PILAR_ALT,
        n_modulos  = 8,
        dist_mod   = L_T,
        b_pilar    = B_PILAR,
        h_pilar    = H_PILAR,
        b_terca    = B_TERCA,
        h_terca    = H_TERCA,
    )


def _print_eta(nome: str, res: dict) -> None:
    ok = "✓" if res["ok"] else "✗"
    print(f"  {ok} {nome:<30} η = {res['eta']:.4f}  "
          f"({'OK' if res['ok'] else 'REPROVADO'})")


if __name__ == "__main__":
    main(rodar_varredura=False)