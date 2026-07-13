"""
main.py — Orquestrador do pipeline de verificação MLC.

Sistema estrutural (adoptado):
    Viga MLC monolítica de duplo-bisel, biarticulada nos apoios.
    Continuidade na cumeeira (sem rótula real).
    H por Castigliano no eixo centroidal (1× hiperestática).
    Classe de serviço 3 (estrutura aberta) — EC5 §2.3.1.3.

Geometria de projecto: candidata R2
    (varredura CS3 — output/varredura_biarticulada_CS3.*)

Pipeline:
    Fase 0 — Dados de entrada
    Fase 1 — Pré-dimensionamento (opcional)
    Fase 2 — ELU (viga, pilar, terças, contraventamento)
    Fase 3 — ELS
    Fase 4 — Ligações + fadiga/deslizamento
    Fase 5 — Relatório
    Fase 6 — Visualização 3D

STOCKI Engenharia Estrutural | Gabriel Stocki CREA-PR 195315/D
EC5 + EN 1990 + NBR 6123
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

from mlc_projeto.checks.elu.contraventamento  import verificar_contraventamento
from mlc_projeto.connections.connections      import (
    dimensionar_ligacoes, dimensionar_ligacoes_central, relatorio_ligacoes
)
from mlc_projeto.connections.fadiga_ligacoes  import verificar_fadiga_deslizamento
from mlc_projeto.output.report                import gerar_relatorio
from mlc_projeto.visualization.viz_3d         import visualizar_galpao


# =============================================================================
# DADOS DE PROJECTO — candidata R2 (CS3, biarticulada)
# Ref.: output/varredura_biarticulada_CS3.md
# =============================================================================

# --- Geometria da viga principal (duplo-bisel) --------------------------------
GEO_PARAMS = dict(
    L         = 20.25,   # m — vão do pórtico
    h0        = 1.00,    # m — altura no apoio
    alpha_deg = 10.0,    # ° — inclinação do extradorso
    b         = 0.30,    # m — largura da secção
)

# --- Material (EN 14080 + EC5) ------------------------------------------------
# CS3 global: laterais abertas / intempérie (EC5 §2.3.1.3)
MAT_CURTA = dict(
    classe         = "GL24h",
    classe_servico = 3,
    duracao        = "curta",      # ELU com vento dominante
)

MAT_LONGA = dict(
    classe         = "GL24h",
    classe_servico = 3,
    duracao        = "longa",      # ELS / k_def
)

# --- Vento NBR 6123 (H1 alinhado a h_ap−h0 no main) ---------------------------
VENTO_PARAMS = dict(
    V0           = 45.0,
    S1           = 1.0,
    categoria    = "IV",
    classe       = "B",
    S3           = 1.0,
    L            = 20.25,
    H1           = 1.785,   # (L/2)·tan(10°) — sobrescrito por geo no main
    h            = 7.0,
    dist_portico = 5.75,
)

# --- Cargas de área e malha estrutural ----------------------------------------
G_AREA = 1.50          # kN/m² permanente
Q_AREA = 0.25          # kN/m² sobrecarga cobertura
L_T    = 5.75          # m — espaçamento entre pórticos = vão das terças
S      = 2.53          # m — espaçamento entre terças (l_ef viga)

# --- Pilares ------------------------------------------------------------------
B_PILAR     = 0.22     # m — lateral (R2, N = R_v)
H_PILAR     = 0.26     # m
H_PILAR_ALT = 7.0      # m — comprimento
# Central: N ≈ 2·R_v (dois pórticos). Em CS3, 0,26×0,26 falha (η>1);
# mínimo quadrado comercial com margem: 0,28×0,28 (η≈0,73).
B_PILAR_C   = 0.28     # m — central
H_PILAR_C   = 0.28     # m

# --- Terças (pré-definidas; verificação no pipeline) --------------------------
B_TERCA = 0.20
H_TERCA = 0.58

# --- Ligações / apoio ---------------------------------------------------------
D_BASE_MM   = 36       # mm — pinos L1 (R2)
D_CUM_MM    = 30       # mm — pino L2
F_CHU_KN    = 80.0     # kN — resistência por chumbador (L3)
ETA_LIG_ALVO = 0.85    # margem de projecto L1/L3 (uso público; frágil em madeira)
L_AP        = 0.90     # m — comprimento da placa de apoio


# ── Orquestrador ──────────────────────────────────────────────────────────────

def _print_eta(nome: str, res: dict) -> None:
    ok  = "✓" if res["ok"] else "✗"
    bar = "█" * int(res["eta"] * 20)
    print(f"  {ok} {nome:<30} η = {res['eta']:.4f}  {bar}")


def main(rodar_varredura: bool = False) -> None:
    """Executa o pipeline completo."""

    print("=" * 72)
    print("  PIPELINE MLC — STOCKI Engenharia Estrutural")
    print("  Biarticulada MLC | CS3 | R2 | EC5 + EN 1990 + NBR 6123")
    print("=" * 72)

    # ── Fase 0: Dados de entrada ──────────────────────────────────────────────
    print("\n[FASE 0] Dados de entrada...")

    geo       = GeometriaViga(**GEO_PARAMS)
    mat_curta = GlulamMaterial(**MAT_CURTA)
    mat_longa = GlulamMaterial(**MAT_LONGA)

    # H1 do vento = variação real da cobertura (coerente com a geometria)
    vento_kw = dict(VENTO_PARAMS)
    vento_kw["H1"] = geo.h_ap - geo.h0
    vento_kw["L"]  = geo.L
    params_vento = ParametrosVento(**vento_kw)

    load = carregamentos_com_vento(
        geo=geo, mat=mat_curta,
        g_area=G_AREA, q_area=Q_AREA,
        L_t=L_T, params_vento=params_vento,
    )

    gov = load.combinacao_ELU_governante()
    # k_mod da duração da combinação governante — EC5 §3.1.3
    mat_elu = mat_curta.com_duracao(gov.duracao)

    print(f"  Geometria : L={geo.L}m | h0={geo.h0}m | "
          f"α={geo.alpha_deg}° | b={geo.b}m | h_ap={geo.h_ap:.3f}m")
    print(f"  Material  : {mat_elu.classe} | CS{mat_elu.classe_servico} | "
          f"k_mod={mat_elu.k_mod:.2f} ({gov.duracao}) | "
          f"k_def={mat_longa.k_def:.2f} (ELS)")
    print(f"  ELU gov.  : {gov.nome} | M={gov.M_max_kNm:.2f} kN·m | "
          f"V={gov.V_max_kN:.2f} kN | N={gov.N_viga_kN:.2f} kN | "
          f"H_fund={gov.H_kN:.2f} kN")
    print(f"  Sistema   : Viga biarticulada MLC (contínua na cumeeira) | "
          f"Área trib.={load.area_trib:.3f} m (L_t×{load.fator_trib})")
    print(f"  M_cumeeira: {gov.M_cumeeira_kNm:.2f} kN·m | "
          f"N={gov.N_viga_kN:.2f} kN | H={gov.H_kN:.2f} kN")

    # ── Fase 1: Pré-dimensionamento ───────────────────────────────────────────
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

    # ── Fase 2: Verificações ELU ──────────────────────────────────────────────
    print("\n[FASE 2] Verificações ELU...")

    res_elu = {}

    res_elu["cumeeira"] = verifica_cumeeira(geo, mat_elu, load)
    _print_eta("Cumeeira §6.4.3", res_elu["cumeeira"])

    # ── Contraventamento ANTES do LTB ─────────────────────────────────────────
    # A cobertura só valida l_1 = s (terças) se o sistema de estabilização
    # cumprir EC5 §9.2.5 (força + rigidez + terça-biela + δ ≤ ℓ/500).
    # Caso contrário l_1 é penalizado → LTB/flexão usam o valor efectivo.
    print("\n[FASE 2] Contraventamento — integridade da cobertura (§9.2.5)...")
    # Diâmetro da diagonal: EC5 §9.2.5.3 com N_d biarticulada exige
    # d ≥ 16 mm S235 (d=12 mm → η_N≈1,74 — insuficiente).
    D_BARRA_CV_MM = 16.0

    res_elu["contraventamento"] = verificar_contraventamento(
        geo=geo, mat=mat_elu, load=load,
        L_comp=46.0, n_modulos_cv=2,
        s_terca=S, d_barra_mm=D_BARRA_CV_MM, aco="S235",
        n_porticos=2, dist_portico=L_T,
        b_terca=B_TERCA, h_terca=H_TERCA,
        k_crit=1.0,   # 1.ª passagem; refinado após LTB
    )
    _print_eta("Cobertura §9.2.5", res_elu["contraventamento"])
    l_1_ltb = float(res_elu["contraventamento"]["l_1_efetivo_m"])
    print(f"  → l_1 LTB = {l_1_ltb:.3f} m | "
          f"{res_elu['contraventamento']['l_1_nota']}")
    if not res_elu["contraventamento"]["cobertura_ok"]:
        print("  ⚠ Cobertura NÃO valida restrição lateral das terças — "
              "LTB com l_1 penalizado.")

    res_elu["flambagem"] = verifica_flambagem_lateral(
        geo, mat_elu, load, l_1=l_1_ltb
    )
    _print_eta("Flambagem §6.3.3", res_elu["flambagem"])

    # Refinar N_flex do contraventamento com k_crit real do LTB
    k_crit_ltb = float(res_elu["flambagem"].get("k_crit", 1.0))
    res_elu["contraventamento"] = verificar_contraventamento(
        geo=geo, mat=mat_elu, load=load,
        L_comp=46.0, n_modulos_cv=2,
        s_terca=S, d_barra_mm=D_BARRA_CV_MM, aco="S235",
        n_porticos=2, dist_portico=L_T,
        b_terca=B_TERCA, h_terca=H_TERCA,
        k_crit=k_crit_ltb,
    )
    l_1_ltb = float(res_elu["contraventamento"]["l_1_efetivo_m"])
    # Se o refinamento mudou a validade, reavaliar LTB uma vez
    if abs(l_1_ltb - float(res_elu["flambagem"]["l_1_m"])) > 1e-6:
        res_elu["flambagem"] = verifica_flambagem_lateral(
            geo, mat_elu, load, l_1=l_1_ltb
        )
        _print_eta("Flambagem §6.3.3 (recalc.)", res_elu["flambagem"])

    res_elu["flexao"] = verifica_flexao(geo, mat_elu, load, s=l_1_ltb)
    _print_eta("Flexo-comp. §6.3.2+6.35", res_elu["flexao"])

    res_elu["cisalhamento"] = verifica_cisalhamento(geo, mat_elu, load)
    _print_eta("Cisalhamento §6.1.7", res_elu["cisalhamento"])

    res_elu["apoio"] = verifica_apoio(geo, mat_elu, load, l_ap=L_AP)
    _print_eta("Apoio §6.1.5+§6.2.2", res_elu["apoio"])

    res_elu["flexo_comp"] = verifica_flexo_compressao(
        geo=geo, mat=mat_elu, load=load,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        H_pilar=H_PILAR_ALT, s=l_1_ltb,
    )
    _print_eta(
        f"Pilar {B_PILAR}×{H_PILAR}m §6.3.2",
        res_elu["flexo_comp"]
    )

    print("\n[FASE 2] Verificações ELU — Pilar central...")
    from mlc_projeto.checks.elu.pilares import verifica_pilar as _verifica_pilar
    _N_central = 2 * load.V_max_ELU()
    res_elu["pilar_central"] = _verifica_pilar(
        mat=mat_elu,
        b=B_PILAR_C, h=H_PILAR_C,
        H=H_PILAR_ALT,
        N_d=_N_central,
    )
    _print_eta(
        f"Pilar central {B_PILAR_C}×{H_PILAR_C}m §6.3.2",
        res_elu["pilar_central"]
    )

    print("\n[FASE 2] Verificações ELU — Terças (flexão cobertura)...")
    from mlc_projeto.checks.elu.tercas import verifica_terca
    from mlc_projeto.core.wind import calcular_vento as _calcular_vento
    _w_C1bv_m2 = _calcular_vento(params_vento).pressoes["C1"]["barlavento_kNm2"]
    res_elu["terca"] = verifica_terca(
        mat       = mat_elu,
        L_t       = L_T,
        s         = S,
        b         = B_TERCA,
        h         = H_TERCA,
        alpha_deg = GEO_PARAMS["alpha_deg"],
        g_k_m2    = G_AREA,
        q_k_m2    = Q_AREA,
        w_kNm2    = _w_C1bv_m2,
    )
    res_elu["terca"]["eta"] = res_elu["terca"]["eta_gov"]
    _print_eta("Terça flexão §6.1.6+§6.1.7", res_elu["terca"])
    # η da terça-biela (estabilização) já em contraventamento
    if "terca" in res_elu["contraventamento"]:
        _print_eta(
            "Terça-biela §6.3.2 (estab.)",
            res_elu["contraventamento"]["terca"],
        )

    # ── Fase 3: Verificações ELS ──────────────────────────────────────────────
    print("\n[FASE 3] Verificações ELS...")

    res_els = {}
    res_els["ELS"] = verificar_ELS(geo, mat_longa, load)
    _print_eta("ELS §2.3.2.2+Tab.7.2", res_els["ELS"])

    # ── Fase 4: Ligações ──────────────────────────────────────────────────────
    print(f"\n[FASE 4] Ligações (η_alvo = {ETA_LIG_ALVO:.2f} — uso público)...")

    res_lig = dimensionar_ligacoes(
        mat=mat_elu, load=load, geo=geo,
        d_base_mm=D_BASE_MM,
        d_cum_mm=D_CUM_MM,
        F_chu_kN=F_CHU_KN,
        eta_alvo=ETA_LIG_ALVO,
    )
    for key, label in [
        ("L1", f"L1 base (d={D_BASE_MM}mm, "
               f"{res_lig['L1']['n_linha']}×{res_lig['L1']['n_linhas']})"),
        ("L2", "L2 cumeeira"),
        ("L3", f"L3 sapata (n_chu={res_lig['L3']['n_chumbadores']})"),
    ]:
        _print_eta(label, res_lig[key])
    print(f"  · L1: n={res_lig['L1']['n_pinos']} pinos | "
          f"n_ef,row={res_lig['L1']['n_ef_row']:.2f} | "
          f"n_ef={res_lig['L1']['n_ef']:.1f} | "
          f"F_Rd/pino={res_lig['L1']['F_v_Rd_kN']:.2f} kN | "
          f"R={res_lig['L1']['R_total_kN']:.0f} kN")

    res_lig_c = dimensionar_ligacoes_central(
        mat=mat_elu, load=load, geo=geo,
        b_pilar_c=B_PILAR_C,
        d_base_mm=D_BASE_MM,
        d_cum_mm=D_CUM_MM,
        eta_alvo=ETA_LIG_ALVO,
    )
    for key, label in [
        ("L1c", f"L1c central (d={D_BASE_MM}mm, 2 chapas)"),
        ("L2c", "L2c cumeeira central"),
        ("L3c", "L3c sapata central"),
    ]:
        _print_eta(label, res_lig_c[key])

    # ── Fase 4b: Fadiga e deslizamento das ligações ───────────────────────────
    print("\n[FASE 4b] Fadiga e deslizamento — EC5 §2.4 + §7.1 + §8.1.5...")

    res_fadiga = verificar_fadiga_deslizamento(
        mat=mat_longa, load=load, geo=geo,
        res_lig=res_lig, res_lig_c=res_lig_c,
        H_pilar=H_PILAR_ALT, psi_2=0.0,
    )

    for cod, r in res_fadiga.items():
        status = "✓" if r["slip_ok"] and r["alternada"]["ok"] else "✗"
        print(f"  {status} {cod:<6}  "
              f"η_slip={r['eta_slip']:.4f}  "
              f"η_alt={r['alternada']['eta_alt']:.4f}")

    # ── Resumo ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("  RESUMO DE TAXAS DE UTILIZAÇÃO — Viga biarticulada MLC")
    print("=" * 72)

    # Mesmos dados do console → memorial / Excel / 3D
    todos_para_relatorio = {
        **res_elu,
        **res_els,
        "L1":  res_lig["L1"],
        "L2":  res_lig["L2"],
        "L3":  res_lig["L3"],
        "L1c": res_lig_c["L1c"],
        "L2c": res_lig_c["L2c"],
        "L3c": res_lig_c["L3c"],
        "fadiga_L1": {
            "eta": res_fadiga["L1"]["eta_slip"],
            "ok":  res_fadiga["L1"]["slip_ok"] and res_fadiga["L1"]["alternada"]["ok"],
            "eta_slip": res_fadiga["L1"]["eta_slip"],
            "eta_alt":  res_fadiga["L1"]["alternada"]["eta_alt"],
            "u_inst_mm": res_fadiga["L1"]["u_inst_mm"],
            "u_fin_mm":  res_fadiga["L1"]["u_fin_mm"],
            "descricao": res_fadiga["L1"]["descricao"],
        },
        "fadiga_L2": {
            "eta": res_fadiga["L2"]["eta_slip"],
            "ok":  res_fadiga["L2"]["slip_ok"] and res_fadiga["L2"]["alternada"]["ok"],
            "eta_slip": res_fadiga["L2"]["eta_slip"],
            "eta_alt":  res_fadiga["L2"]["alternada"]["eta_alt"],
            "u_inst_mm": res_fadiga["L2"]["u_inst_mm"],
            "u_fin_mm":  res_fadiga["L2"]["u_fin_mm"],
            "descricao": res_fadiga["L2"]["descricao"],
        },
        "fadiga_L1c": {
            "eta": res_fadiga["L1c"]["eta_slip"],
            "ok":  res_fadiga["L1c"]["slip_ok"] and res_fadiga["L1c"]["alternada"]["ok"],
            "eta_slip": res_fadiga["L1c"]["eta_slip"],
            "eta_alt":  res_fadiga["L1c"]["alternada"]["eta_alt"],
            "u_inst_mm": res_fadiga["L1c"]["u_inst_mm"],
            "u_fin_mm":  res_fadiga["L1c"]["u_fin_mm"],
            "descricao": res_fadiga["L1c"]["descricao"],
        },
        "k_def": mat_longa.k_def,
        "meta": {
            "candidato": "R2",
            "s": S,
            "l_ap": L_AP,
            "area_trib": load.area_trib,
            "g_area": G_AREA,
            "q_area": Q_AREA,
            "sistema": "biarticulada",
            "classe_servico": mat_elu.classe_servico,
            "eta_lig_alvo": ETA_LIG_ALVO,
        },
    }
    eta_max_val = 0.0

    secoes = [
        ("── ELU Viga ──", [
            "cumeeira", "flambagem", "flexao",
            "cisalhamento", "apoio",
        ]),
        ("── ELU Pilar ──", ["flexo_comp", "pilar_central"]),
        ("── ELU Terças ──", ["terca"]),
        ("── ELU Contravent. ──", ["contraventamento"]),
        ("── ELS ──", ["ELS"]),
    ]

    for titulo, chaves in secoes:
        print(f"\n  {titulo}")
        for chave in chaves:
            if chave not in todos_para_relatorio:
                continue
            res = todos_para_relatorio[chave]
            eta = res["eta"]
            ok  = "✓" if res["ok"] else "✗"
            bar = "█" * int(eta * 20)
            print(f"  {ok} {chave:<26} η = {eta:.4f}  {bar}")
            eta_max_val = max(eta_max_val, eta)

    print(f"\n  ── Ligações ──")
    for key, label in [
        ("L1",  "base"),
        ("L2",  "cumeeira"),
        ("L3",  "sapata"),
        ("L1c", "central base"),
        ("L2c", "central cumeeira"),
        ("L3c", "central sapata"),
    ]:
        r   = todos_para_relatorio[key]
        ok  = "✓" if r["ok"] else "✗"
        eta = r["eta"]
        bar = "█" * int(eta * 20)
        print(f"  {ok} Ligação {label:<22} η = {eta:.4f}  {bar}")
        eta_max_val = max(eta_max_val, eta)

    print(f"\n  ── Fadiga (deslizamento ELS) ──")
    for cod in ("L1", "L2", "L1c"):
        r   = todos_para_relatorio[f"fadiga_{cod}"]
        ok  = "✓" if r["ok"] else "✗"
        eta = r["eta"]
        bar = "█" * int(eta * 20)
        print(f"  {ok} Fadiga {cod:<23} η = {eta:.4f}  {bar}")

    print(f"\n  η máximo  = {eta_max_val:.4f}")
    print(f"  H_fund    = {load.H_ELU():.2f} kN  (empuxo → sapata)")
    status = "APROVADO" if eta_max_val <= 1.0 else "REPROVADO"
    print(f"  Status    = {status}")
    print("=" * 72)

    # ── Fase 5: Relatório ─────────────────────────────────────────────────────
    # Material do memorial: CS + k_def (longa); combinações via load
    gerar_relatorio(
        todos_para_relatorio,
        geo,
        mat_longa,
        nome="relatorio_mlc",
        load=load,
    )
    print("\nPipeline concluído. Relatório gerado em output/")

    # ── Fase 6: Visualização 3D ───────────────────────────────────────────────
    print("\n[FASE 6] Abrindo visualização 3D interativa...")
    visualizar_galpao(
        geo        = geo,
        resultados = todos_para_relatorio,
        H_pilar   = H_PILAR_ALT,
        n_modulos = 8,
        dist_mod  = L_T,
        b_pilar   = B_PILAR,
        h_pilar   = H_PILAR,
        b_pilar_c = B_PILAR_C,
        h_pilar_c = H_PILAR_C,
        b_terca   = B_TERCA,
        h_terca   = H_TERCA,
    )


if __name__ == "__main__":
    main(rodar_varredura=False)