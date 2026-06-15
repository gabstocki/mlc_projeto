"""
main.py — Orquestrador do pipeline de verificação MLC.

Executa todas as fases em sequência e chama report.py ao final.
"""

from mlc_projeto.core.geometry   import GeometriaViga
from mlc_projeto.core.materials  import GlulamMaterial
from mlc_projeto.core.loads      import Carregamentos
from mlc_projeto.core.wind       import ParametrosVento, calcular_vento, ResultadoVento
from mlc_projeto.predim.predim   import pre_dimensionar
from mlc_projeto.checks.elu.flexao            import verifica_flexao
from mlc_projeto.checks.elu.cumeeira          import verifica_cumeeira
from mlc_projeto.checks.elu.cisalhamento      import verifica_cisalhamento
from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral
from mlc_projeto.checks.elu.flexo_compressao  import verifica_flexo_compressao
from mlc_projeto.checks.elu.apoio             import verifica_apoio
from mlc_projeto.checks.els.deflection        import calcular_flecha
from mlc_projeto.checks.els.creep             import calcular_flecha_final
from mlc_projeto.connections.connections      import dimensionar_ligacao
from mlc_projeto.output.report                import gerar_relatorio


def main() -> None:
    """Executa o pipeline completo de verificação."""

    # ── Fase 0: Dados de entrada ──────────────────────────────
    # Fase 0: Dados de entrada
    geo = GeometriaViga(L=20.25, h0=7.0, alpha_deg=5.64, b=0.20)
    mat = GlulamMaterial(classe="GL28h", classe_servico=1)

    params_vento = ParametrosVento(
    V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
    L=20.25, H1=1.0, h=7.0, dist_portico=5.75,
)
    vento = calcular_vento(params_vento)

    load = Carregamentos(geo=geo, mat=mat, vento=vento)

    # ── Fase 1: Pré-dimensionamento ───────────────────────────
    predim = pre_dimensionar(geo, mat, load)
    print(f"Pré-dim OK: η_max = {predim['eta_max']:.3f}")

    # ── Fase 2: ELU ───────────────────────────────────────────
    resultados_elu = {
        "flexao":            verifica_flexao(geo, mat, load),
        "cumeeira":          verifica_cumeeira(geo, mat, load),
        "cisalhamento":      verifica_cisalhamento(geo, mat, load),
        "flambagem_lateral": verifica_flambagem_lateral(geo, mat, load),
        "flexo_compressao":  verifica_flexo_compressao(geo, mat, load),
        "apoio":             verifica_apoio(geo, mat, load),
    }

    # ── Fase 3: ELS ───────────────────────────────────────────
    resultados_els = {
        "deflection": calcular_flecha(geo, mat, load),
        "creep":      calcular_flecha_final(geo, mat, load),
    }

    # ── Fase 4: Ligações ──────────────────────────────────────
    resultados_lig = dimensionar_ligacao(geo, mat, load)

    # ── Fases 5–6: Relatório ──────────────────────────────────
    todos = {**resultados_elu, **resultados_els, "ligacoes": resultados_lig}
    gerar_relatorio(todos, geo, mat)
    print("Pipeline concluído. Relatório gerado em output/")


if __name__ == "__main__":
    main()
