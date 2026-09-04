"""
checks/elu/tirante_piso_robustez.py — Robustez do tirante ao nível do piso.

Contexto (issue 37)
-------------------
O tirante que fecha o empuxo está ao nível do piso (z ≈ 0,08 m, L = vão),
atravessando um **estacionamento coberto**. O empuxo em si (coerência do
caminho de carga) é tratado nas issues 35/38; AQUI trata-se da **exposição
física** desse elemento, hoje delegada a "detalhar em execução"
(tirante_base.py). O projeto já verifica o impacto de veículo nos PILARES
(impacto_veiculo.py); o TIRANTE via a mesma ação acidental e não era verificado.

Quatro frentes:
  1. Impacto de veículo (EN 1991-1-7) — F_dx=50 kN / F_dy=25 kN.
  2. Corrosão (EN 335 UC3 / EN ISO 12944 C3+) — sobreespessura de sacrifício.
  3. Incêndio (EN 1993-1-2) — aço nu perde capacidade; se primário, proteger.
  4. Tropeço / serventia — barra a 8 cm em piso de circulação.

Decisão de projeto adotada (issue 37, confirmada com a usuária)
---------------------------------------------------------------
  · PROTEÇÃO = tirante EMBUTIDO em canaleta no contrapiso. A laje intercepta o
    impacto (não chega à barra), resolve o tropeço (barra sob o piso acabado) e
    o cobrimento de argamassa/graute dá proteção ao fogo e à corrosão.
  · PAPEL = tirante PRIMÁRIO (fecho de empuxo) — postura conservadora enquanto a
    issue 38 (decisão A/B da issue 35) não fecha; torna fogo/impacto críticos.

Norma
-----
  EN 1991-1-7:2006 §4.3  — impacto de veículo (força estática equivalente)
  EN 1990 §6.4.3.3       — combinação de ação acidental
  EN 1993-1-1 §6.2.3     — tração da barra (seção efetiva pós-corrosão)
  EN 1993-1-5/§6.2.5     — flexão plástica da seção redonda (M_pl = f_y·d³/6)
  EN 335 / EN ISO 12944  — classe de uso / corrosividade
  EN 1993-1-2            — aço em situação de incêndio
"""

from __future__ import annotations

from mlc_projeto.checks.elu.tirante_base import ACO, GAMMA_M0, _n_t_rd_kN
from mlc_projeto.checks.elu.impacto_veiculo import F_DX_KN, F_DY_KN


# ── Parâmetros de projeto (issue 37) ────────────────────────────────────────
DELTA_CORR_MM_DEFAULT = 1.0    # sobreespessura radial de sacrifício (embutido+revestido)
VIDA_UTIL_ANOS        = 50     # vida de projeto (EN 1990)
CLASSE_USO            = "UC3 (EN 335) / C3 (EN ISO 12944)"

PROTECOES = ("embutido", "guarda_rodas", "nenhuma")


# ── 1) Impacto de veículo sobre o tirante ────────────────────────────────────

def robustez_impacto_tirante(
    d_mm:        float,
    aco:         str,
    L_livre_m:   float,
    protecao:    str = "embutido",
    F_dx_kN:     float = F_DX_KN,
    F_dy_kN:     float = F_DY_KN,
) -> dict:
    """
    Impacto de veículo (EN 1991-1-7) sobre o tirante ao nível do piso.

    Modelo da BARRA NUA (justificativa da necessidade de proteção):
      força transversal F no vão livre L, sem restrição lateral próxima ⇒ o modo
      crítico é a FLEXÃO local. Majorante clássico (carga pontual a meio-vão de
      viga biapoiada):  M_Ed = F · L_livre / 4.
      Resistência plástica da seção redonda (acidental, γ_M0=1,0):
          W_pl = d³/6 ;  M_pl,Rd = f_y · W_pl / γ_M0.
      η_barra_nua = M_Ed / M_pl,Rd.

    Efeito da proteção:
      · 'embutido' / 'guarda_rodas': o impacto é INTERCEPTADO (laje / defensa) e
        NÃO chega à barra ⇒ η_efetivo = 0 (a proteção é o elemento verificado ao
        choque, EN 1991-1-7); a barra nua fica registrada como justificativa.
      · 'nenhuma': η_efetivo = η_barra_nua (em geral ≫ 1 para barra esbelta em vão
        grande ⇒ exige seção muito maior).
    """
    if protecao not in PROTECOES:
        raise ValueError(f"protecao deve ser um de {PROTECOES}")
    if d_mm <= 0 or L_livre_m <= 0:
        raise ValueError("d_mm e L_livre_m devem ser positivos")

    f_y = ACO[aco]["f_y"]                       # MPa = N/mm²
    F_gov = max(F_dx_kN, F_dy_kN)               # kN — direção mais desfavorável
    W_pl_mm3 = d_mm ** 3 / 6.0                  # mm³ (seção redonda maciça)
    M_pl_Rd_kNm = f_y * W_pl_mm3 / GAMMA_M0 / 1e6   # kN·m
    M_Ed_kNm = F_gov * L_livre_m / 4.0          # kN·m (majorante pontual a meio-vão)
    eta_nua = M_Ed_kNm / M_pl_Rd_kNm if M_pl_Rd_kNm > 0 else 999.0

    intercepta = protecao in ("embutido", "guarda_rodas")
    eta_ef = 0.0 if intercepta else eta_nua
    ok = eta_ef <= 1.0

    if protecao == "embutido":
        mecanismo = (
            "Barra EMBUTIDA em canaleta no contrapiso: a laje intercepta o choque "
            "de veículo (EN 1991-1-7) — a força não é aplicada à barra."
        )
    elif protecao == "guarda_rodas":
        mecanismo = (
            "Guarda-rodas/mureta (defensa) mantém o veículo afastado; a defensa é o "
            "elemento verificado ao choque (EN 1991-1-7), não a barra."
        )
    else:
        mecanismo = (
            "Barra NUA exposta ao choque — verificada diretamente à força acidental "
            "transversal (flexão plástica)."
        )

    return {
        "aspecto":       "impacto_veiculo",
        "protecao":      protecao,
        "F_dx_kN":       F_dx_kN,
        "F_dy_kN":       F_dy_kN,
        "F_gov_kN":      F_gov,
        "L_livre_m":     round(L_livre_m, 3),
        "d_mm":          d_mm,
        "M_Ed_kNm":      round(M_Ed_kNm, 3),
        "M_pl_Rd_kNm":   round(M_pl_Rd_kNm, 3),
        "eta_barra_nua": round(eta_nua, 3),
        "intercepta":    intercepta,
        "eta":           round(eta_ef, 4),
        "ok":            ok,
        "norma":         "EN 1991-1-7 §4.3 + EN 1990 A_d + EN 1993-1-1 §6.2.5",
        "mecanismo":     mecanismo,
        "requisito": (
            "Canaleta/duto no contrapiso cobrindo o tirante em todo o vão; tampa de "
            "piso ou preenchimento capaz de transmitir o choque à laje."
            if protecao == "embutido" else
            "Defensa/guarda-rodas contínuo a ≥ 0,5 m da barra, dimensionado ao choque "
            "de projeto (EN 1991-1-7)."
            if protecao == "guarda_rodas" else
            f"Barra nua NÃO resiste ao choque de projeto (η={eta_nua:.0f}); adotar "
            "proteção (embutir/defensa) ou seção muitíssimo maior."
        ),
    }


# ── 2) Corrosão — seção efetiva ──────────────────────────────────────────────

def robustez_corrosao(
    d_mm:            float,
    aco:             str,
    T_d_kN:          float,
    eta_alvo:        float = 0.75,
    delta_corr_mm:   float = DELTA_CORR_MM_DEFAULT,
    vida_util_anos:  int = VIDA_UTIL_ANOS,
) -> dict:
    """
    Corrosão (EN 335 UC3 / EN ISO 12944 C3+): reduz o raio por sobreespessura de
    sacrifício Δr ao longo da vida de projeto e reverifica a tração na seção
    efetiva (EN 1993-1-1 §6.2.3).

        d_ef   = d − 2·Δr
        N_t,Rd(d_ef) = A(d_ef)·f_y / γ_M0
        η_corr = T_d / N_t,Rd(d_ef)

    Δr default = 1,0 mm (embutido em canaleta + revestido — ambiente C3
    protegido). Ajustar conforme o revestimento e a AN.
    """
    if d_mm <= 0:
        raise ValueError("d_mm deve ser positivo")
    d_ef = max(d_mm - 2.0 * delta_corr_mm, 0.0)
    N_t_Rd_0 = _n_t_rd_kN(d_mm, aco)
    N_t_Rd_ef = _n_t_rd_kN(d_ef, aco) if d_ef > 0 else 0.0
    eta = T_d_kN / N_t_Rd_ef if N_t_Rd_ef > 0 else 999.0
    perda_pct = (1.0 - N_t_Rd_ef / N_t_Rd_0) * 100.0 if N_t_Rd_0 > 0 else 100.0

    return {
        "aspecto":        "corrosao",
        "classe_uso":     CLASSE_USO,
        "vida_util_anos": vida_util_anos,
        "delta_corr_mm":  delta_corr_mm,
        "d_mm":           d_mm,
        "d_ef_mm":        round(d_ef, 2),
        "N_t_Rd_0_kN":    round(N_t_Rd_0, 2),
        "N_t_Rd_ef_kN":   round(N_t_Rd_ef, 2),
        "perda_pct":      round(perda_pct, 1),
        "T_d_kN":         round(T_d_kN, 3),
        "eta":            round(eta, 4),
        "eta_alvo":       eta_alvo,
        "ok":             eta <= 1.0 + 1e-9,
        "ok_alvo":        eta <= eta_alvo + 1e-9,
        "norma":          "EN 335 / EN ISO 12944 + EN 1993-1-1 §6.2.3",
        "requisito": (
            f"Proteção anticorrosiva (galvanização a fogo ou pintura C3) + Δr={delta_corr_mm:.1f} mm "
            f"de sacrifício em {vida_util_anos} anos; canaleta preenchida (evita acúmulo de água)."
        ),
    }


# ── 3) Incêndio ──────────────────────────────────────────────────────────────

def requisito_fogo(protecao: str = "embutido", primario: bool = True) -> dict:
    """
    Incêndio (EN 1993-1-2): aço nu perde capacidade acima de ~500–600 °C. Se o
    tirante é PRIMÁRIO (fecho de empuxo), sua perda em incêndio compromete o
    caminho de carga → exige proteção ao fogo ou caminho alternativo robusto.

    'embutido': o cobrimento de argamassa/graute na canaleta funciona como
    proteção passiva (analogia à armadura embutida) → requisito atendido por
    cobrimento mínimo. 'nenhuma' + primário: exige proteção R30/R60 explícita.
    """
    if protecao == "embutido":
        ok = True
        verdito = (
            "Cobrimento da canaleta (argamassa/graute) provê proteção passiva ao fogo "
            "— requisito atendido por cobrimento mínimo."
        )
        requisito = "Preenchimento/cobrimento mínimo da canaleta especificado no detalhamento."
    elif not primario:
        ok = True
        verdito = (
            "Tirante não primário (só ancoragem ao uplift, Opção B/issue 38): perda em "
            "incêndio não compromete a gravidade — requisito reduzido."
        )
        requisito = "Registrar dependência da decisão A/B (issue 38)."
    else:
        ok = False
        verdito = (
            "Tirante primário EXPOSTO: em incêndio o aço nu perde capacidade e o fecho "
            "do empuxo pode falhar."
        )
        requisito = "Proteção ao fogo (R30/R60) OU caminho de carga alternativo robusto."

    return {
        "aspecto":   "incendio",
        "protecao":  protecao,
        "primario":  primario,
        "ok":        ok,
        "norma":     "EN 1993-1-2",
        "verdito":   verdito,
        "requisito": requisito,
    }


# ── 4) Tropeço / serventia ───────────────────────────────────────────────────

def requisito_tropeco(protecao: str = "embutido", z_tir_m: float = 0.08) -> dict:
    """Tropeço/serventia: barra a z_tir sobre piso de circulação."""
    if protecao == "embutido":
        ok = True
        verdito = "Barra sob o piso acabado (embutida) — sem obstáculo de circulação."
        requisito = "Canaleta nivelada com o piso (tampa/argamassa a ras)."
    else:
        ok = False
        verdito = f"Barra a {z_tir_m*100:.0f} cm sobre o piso — obstáculo a pessoas/veículos."
        requisito = "Embutir, sinalizar ou proteger; barra saliente não é aceitável em circulação."
    return {
        "aspecto":   "tropeco",
        "protecao":  protecao,
        "z_tir_m":   z_tir_m,
        "ok":        ok,
        "norma":     "Serventia / uso público",
        "verdito":   verdito,
        "requisito": requisito,
    }


# ── Orquestrador ─────────────────────────────────────────────────────────────

def verificar_robustez_tirante_piso(
    d_mm:           float,
    aco:            str,
    T_d_kN:         float,
    L_m:            float,
    eta_alvo:       float = 0.75,
    protecao:       str = "embutido",
    primario:       bool = True,
    L_livre_m:      float | None = None,
    delta_corr_mm:  float = DELTA_CORR_MM_DEFAULT,
    z_tir_m:        float = 0.08,
    F_dx_kN:        float = F_DX_KN,
    F_dy_kN:        float = F_DY_KN,
) -> dict:
    """
    Robustez do tirante ao nível do piso — impacto, corrosão, incêndio, tropeço.

    η GOVERNANTE (quantificável) = max(η_corrosão, η_impacto_efetivo). Com o
    tirante EMBUTIDO o impacto é interceptado (η_impacto=0) e governa a tração na
    seção corroída. Incêndio e tropeço entram como REQUISITOS de projeto (ok/nok
    qualitativo), rastreáveis no memorial — não mais delegados a "execução".

    L_livre_m: vão livre lateral da barra para o modelo de impacto da barra nua
    (default = L_m, conservador — sem restrições intermediárias).
    """
    L_livre = float(L_livre_m) if L_livre_m is not None else float(L_m)

    r_imp = robustez_impacto_tirante(
        d_mm=d_mm, aco=aco, L_livre_m=L_livre, protecao=protecao,
        F_dx_kN=F_dx_kN, F_dy_kN=F_dy_kN,
    )
    r_cor = robustez_corrosao(
        d_mm=d_mm, aco=aco, T_d_kN=T_d_kN, eta_alvo=eta_alvo,
        delta_corr_mm=delta_corr_mm,
    )
    r_fog = requisito_fogo(protecao=protecao, primario=primario)
    r_tro = requisito_tropeco(protecao=protecao, z_tir_m=z_tir_m)

    aspectos = [r_imp, r_cor, r_fog, r_tro]
    eta_gov = max(r_imp["eta"], r_cor["eta"])
    ok_all = all(a["ok"] for a in aspectos)
    gov = "impacto" if r_imp["eta"] >= r_cor["eta"] else "corrosao"

    requisitos = [
        f"[impacto] {r_imp['requisito']}",
        f"[corrosão] {r_cor['requisito']}",
        f"[incêndio] {r_fog['requisito']}",
        f"[tropeço] {r_tro['requisito']}",
    ]

    return {
        "ativo":       True,
        "sistema":     "Robustez do tirante ao nível do piso (estacionamento)",
        "protecao":    protecao,
        "primario":    primario,
        "d_mm":        d_mm,
        "aco":         aco,
        "T_d_kN":      round(T_d_kN, 3),
        "eta":         round(eta_gov, 4),
        "eta_governa": gov,
        "ok":          ok_all,
        "impacto":     r_imp,
        "corrosao":    r_cor,
        "incendio":    r_fog,
        "tropeco":     r_tro,
        "requisitos":  requisitos,
        "norma": (
            "EN 1991-1-7 | EN 1990 A_d | EN 1993-1-1 §6.2 | "
            "EN 335 / EN ISO 12944 | EN 1993-1-2"
        ),
        "nota": (
            f"Proteção adotada: {protecao}. η quantificável governado por "
            f"{gov} (η={eta_gov:.3f}); incêndio/tropeço como requisitos de projeto. "
            "Substitui a nota genérica 'detalhar em execução' (issue 37)."
        ),
    }


def relatorio_robustez_tirante(res: dict) -> None:
    """Impressão resumida no console."""
    if not res or not res.get("ativo"):
        print("  · Robustez do tirante no piso: N/A")
        return
    ok = "✓" if res.get("ok") else "✗"
    imp, cor = res["impacto"], res["corrosao"]
    print(f"  {ok} Robustez tirante piso (proteção: {res['protecao']})  η={res['eta']:.4f} (governa {res['eta_governa']})")
    print(
        f"  · Impacto EN1991-1-7: barra nua η={imp['eta_barra_nua']:.0f} "
        f"(M_Ed={imp['M_Ed_kNm']:.0f} vs M_pl,Rd={imp['M_pl_Rd_kNm']:.1f} kNm) "
        f"→ {'interceptado pela proteção (η=0)' if imp['intercepta'] else 'barra nua'}"
    )
    print(
        f"  · Corrosão {cor['classe_uso']}: d {cor['d_mm']:.0f}→{cor['d_ef_mm']:.0f} mm "
        f"(−{cor['perda_pct']:.0f}% N_t,Rd) → η_tração={cor['eta']:.3f}"
    )
    print(f"  · Incêndio: {res['incendio']['verdito'][:70]}")
    print(f"  · Tropeço: {res['tropeco']['verdito'][:70]}")
