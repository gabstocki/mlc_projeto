"""
main.py — Orquestrador do pipeline de verificação MLC.

Executa todas as fases em sequência usando as interfaces v2:
    — Carregamentos com área tributária correta (L_t/2)
    — Combinações EN 1990 completas com vento NBR 6123
    — Varredura paramétrica com s varrido e l_ef recalculado

Dados do projeto:
    Galpão em MLC GL24h | Vão 20,25 m | EC5 + EN 1990 + NBR 6123
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
from mlc_projeto.checks.els.deflection_els    import verificar_ELS

from mlc_projeto.output.report                import gerar_relatorio


# ── Dados do projeto ──────────────────────────────────────────────────────────

# Geometria — definida após varredura paramétrica
# Atualizar com o resultado do pre_dimensionar() quando executado
GEO_PARAMS = dict(
    L         = 20.25,   # m — vão de cada pórtico
    h0        = 0.60,    # m — altura da seção no apoio
    alpha_deg = 4.5,     # graus — inclinação da cumeeira
    b         = 0.26,    # m — largura da seção
)

# Material
MAT_PARAMS = dict(
    classe         = "GL24h",
    classe_servico = 2,
    duracao        = "curta",   # vento dominante — combinação C2
)

# Vento NBR 6123
VENTO_PARAMS = dict(
    V0          = 45.0,
    S1          = 1.0,
    categoria   = "IV",
    classe      = "B",
    S3          = 1.0,
    L           = 20.25,
    H1          = 1.0,
    h           = 7.0,
    dist_portico= 5.75,
)

# Carregamentos por área
G_AREA = 1.50   # kN/m² — permanente
Q_AREA = 0.25   # kN/m² — sobrecarga

# Geometria das terças
L_T = 5.75      # m — vão das terças = espaçamento entre pórticos
S   = 1.00      # m — espaçamento entre terças (resultado varredura terças)
L_AP = 0.55     # m — comprimento placa de apoio (resultado varredura)


def main(rodar_varredura: bool = False) -> None:
    """
    Executa o pipeline completo de verificação.

    Args:
        rodar_varredura: Se True, roda a varredura paramétrica completa
                         antes das verificações pontuais. Pode demorar.
    """

    print("=" * 70)
    print("  PIPELINE MLC — STOCKI Engenharia Estrutural")
    print("  EC5 EN 1995-1-1 | EN 1990 | NBR 6123")
    print("=" * 70)

    # ── Fase 0: Dados de entrada ──────────────────────────────
    print("\n[FASE 0] Dados de entrada...")

    params_vento = ParametrosVento(**VENTO_PARAMS)

    geo = GeometriaViga(**GEO_PARAMS)
    mat = GlulamMaterial(**MAT_PARAMS)
    mat_longa = GlulamMaterial(
        classe=MAT_PARAMS["classe"],
        classe_servico=MAT_PARAMS["classe_servico"],
        duracao="longa",
    )

    load = carregamentos_com_vento(
        geo=geo, mat=mat,
        g_area=G_AREA, q_area=Q_AREA,
        L_t=L_T,
        params_vento=params_vento,
    )

    print(f"  Geometria : L={geo.L}m | h0={geo.h0}m | "
          f"α={geo.alpha_deg}° | b={geo.b}m | h_ap={geo.h_ap:.3f}m")
    print(f"  Material  : {mat.classe} | CS{mat.classe_servico} | "
          f"k_mod={mat.k_mod:.2f} | k_def={mat_longa.k_def:.2f}")
    print(f"  ELU gov.  : {load.combinacao_ELU_governante().nome} | "
          f"M={load.M_max_ELU():.2f} kN·m | "
          f"V={load.V_max_ELU():.2f} kN")
    print(f"  Área trib.: {load.area_trib:.3f} m (L_t/2)")

    # ── Fase 1: Pré-dimensionamento (opcional) ────────────────
    if rodar_varredura:
        print("\n[FASE 1] Varredura paramétrica (pode demorar)...")
        df = pre_dimensionar(
            g_area        = G_AREA,
            q_area        = Q_AREA,
            params_vento  = params_vento,
            L_v           = geo.L,
            L_t           = L_T,
            classe        = MAT_PARAMS["classe"],
            classe_servico= MAT_PARAMS["classe_servico"],
            h0_range      = (0.40, 1.20, 0.10),
            alpha_range   = (3.0,  9.0,  0.5),
            b_range       = (0.10, 0.28, 0.02),
            l_ap_range    = (0.20, 0.60, 0.05),
            s_range       = (1.00, 2.10, 0.25),
        )
        relatorio(df, n=10)
    else:
        print("\n[FASE 1] Usando geometria pré-definida "
              "(passe rodar_varredura=True para rodar a varredura)")

    # ── Fase 2: Verificações ELU ──────────────────────────────
    print("\n[FASE 2] Verificações ELU...")

    resultados_elu = {}

    resultados_elu["cumeeira"] = verifica_cumeeira(geo, mat, load)
    _print_eta("Cumeeira §6.4.3", resultados_elu["cumeeira"])

    resultados_elu["flambagem"] = verifica_flambagem_lateral(
        geo, mat, load, l_1=S
    )
    _print_eta("Flambagem lat. §6.3.3", resultados_elu["flambagem"])

    resultados_elu["flexao"] = verifica_flexao(geo, mat, load)
    _print_eta("Flexão §6.1.6", resultados_elu["flexao"])

    resultados_elu["cisalhamento"] = verifica_cisalhamento(geo, mat, load)
    _print_eta("Cisalhamento §6.1.7", resultados_elu["cisalhamento"])

    resultados_elu["apoio"] = verifica_apoio(geo, mat, load, l_ap=L_AP)
    _print_eta("Apoio §6.1.5+§6.2.2", resultados_elu["apoio"])

    # ── Fase 3: Verificações ELS ──────────────────────────────
    print("\n[FASE 3] Verificações ELS...")

    resultados_els = {}
    resultados_els["ELS"] = verificar_ELS(geo, mat_longa, load)
    _print_eta("ELS §2.3.2.2+Tab.7.2", resultados_els["ELS"])

    # ── Resumo ────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESUMO DE TAXAS DE UTILIZAÇÃO")
    print("=" * 70)
    todos = {**resultados_elu, **resultados_els}
    eta_max = 0.0
    for nome, res in todos.items():
        eta = res["eta"]
        ok  = "✓" if res["ok"] else "✗"
        bar = "█" * int(eta * 20)
        print(f"  {ok} {nome:<22} η = {eta:.4f}  {bar}")
        eta_max = max(eta_max, eta)
    print(f"\n  η máximo = {eta_max:.4f}")
    status = "APROVADO" if eta_max <= 1.0 else "REPROVADO"
    print(f"  Status   = {status}")
    print("=" * 70)

    # ── Fase 5-6: Relatório ───────────────────────────────────
    gerar_relatorio(todos, geo, mat)
    print("\nPipeline concluído. Relatório gerado em output/")


def _print_eta(nome: str, res: dict) -> None:
    """Imprime resultado de uma verificação de forma compacta."""
    ok  = "✓" if res["ok"] else "✗"
    print(f"  {ok} {nome:<25} η = {res['eta']:.4f}  "
          f"({'OK' if res['ok'] else 'REPROVADO'})")


if __name__ == "__main__":
    main(rodar_varredura=False)