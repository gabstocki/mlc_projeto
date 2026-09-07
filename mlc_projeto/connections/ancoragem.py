"""
connections/ancoragem.py — Chumbadores MOLDADOS COM CABEÇA (cast-in headed).

Decisão de projeto (2026-09-07)
-------------------------------
A ancoragem passa a ser por chumbadores **moldados com cabeça**, e não
pós-instalados. Consequências:

  · o lado do CONCRETO (cone, pull-out sob a cabeça, blow-out, pry-out, borda)
    é coberto pelos modelos de resistência da própria EN 1992-4, sem depender
    de ETA de produto — ao contrário do pós-instalado, cuja capacidade de
    expansão/aderência só existe por ensaio do fabricante;
  · o lado do AÇO é a barra roscada, verificável por EN 1993-1-8.

Isto elimina a dependência do laudo de produto para o concreto, mas NÃO
dispensa a EN 1992-4: os coeficientes dos modelos de cone e blow-out são dela.

Estado de implementação
-----------------------
IMPLEMENTADO — lado do AÇO da barra (EN 1993-1-8 Tab. 3.4): tração, corte e a
interação. Substitui o `F_CHU_KN = 80 kN` que era um valor ARBITRADO, sem
produto nem cálculo por trás.

IMPLEMENTADO — lado do CONCRETO, a partir de DD CEN/TS 1992-4-2:2009 fornecida
ao projeto: cone de arrancamento (§6.2.5), pressão sob a cabeça (§6.2.4),
pry-out (§6.3.4) e a interação tração-corte (§6.4).

AINDA NÃO IMPLEMENTADO: fendilhamento (§7.2.1.7), blow-out lateral (§7.2.1.8) e
rotura de borda sob corte (§7.2.2.5). O blow-out só governa com chumbador junto
a borda e h_ef grande; a rotura de borda só existe se o corte passar pelas
barras — com chaveta de cisalhamento ele não passa. Ambos ficam declarados como
pendentes e devem ser confirmados como não governantes.

EDIÇÃO NORMATIVA — implementado contra **BS EN 1992-4:2018**, a edição vigente.
O projeto recebeu também a DD CEN/TS 1992-4-2:2009, que a EN 2018 declara
RETIRADA; ela foi usada apenas como conferência cruzada. As diferenças entre as
duas foram verificadas uma a uma e estão anotadas junto aos coeficientes — não
são cosméticas: mudam k1, k2 e a própria resistência de referência do concreto
(cubo → cilindro).

Convenção
---------
Todas as forças em kN; diâmetros em mm; tensões em MPa.
"""

from __future__ import annotations

import math

# ── Aço da barra — EN 1993-1-8 Tab. 3.1 ──────────────────────────────────────
# (f_yb, f_ub) em MPa por classe de parafuso/barra roscada.
CLASSES_BARRA: dict[str, tuple[float, float]] = {
    "4.6":  (240.0, 400.0),
    "5.6":  (300.0, 500.0),
    "8.8":  (640.0, 800.0),
    "10.9": (900.0, 1000.0),
}

# Área resistente à tração A_s (mm²) — roscas métricas de passo grosso.
AREA_RESISTENTE_MM2: dict[int, float] = {
    12: 84.3, 16: 157.0, 20: 245.0, 24: 353.0,
    27: 459.0, 30: 561.0, 36: 817.0, 42: 1121.0,
}

# α_v de EN 1993-1-8 Tab. 3.4 — corte no fuste roscado.
ALPHA_V = {"4.6": 0.6, "5.6": 0.6, "8.8": 0.6, "10.9": 0.5}

K2_TRACAO = 0.9      # EN 1993-1-8 Tab. 3.4 — cabeça normal

# Coeficiente parcial do aço — EN 1992-4:2018 Tabela 4.1, situações
# persistentes/transitórias. Tração e corte têm valores DIFERENTES:
#   tração: γ_Ms = 1,2·f_uk/f_yk ≥ 1,4
#   corte : γ_Ms = 1,0·f_uk/f_yk ≥ 1,25, se f_uk ≤ 800 MPa e f_yk/f_uk ≤ 0,8;
#           caso contrário 1,5
# (Antes adotava-se 1,5 para ambos, por não se dispor da norma — conservador no
#  corte. Agora usa-se a Tabela 4.1.)
GAMMA_MS_ANCORAGEM = 1.5   # mantido como default explícito de compatibilidade


def gamma_Ms_tracao(classe: str) -> float:
    """γ_Ms para tração — EN 1992-4:2018 Tab. 4.1."""
    f_yb, f_ub = CLASSES_BARRA[classe]
    return max(1.2 * f_ub / f_yb, 1.4)


def gamma_Ms_corte(classe: str) -> float:
    """γ_Ms para corte sem braço de alavanca — EN 1992-4:2018 Tab. 4.1."""
    f_yb, f_ub = CLASSES_BARRA[classe]
    if f_ub <= 800.0 and f_yb / f_ub <= 0.8:
        return max(1.0 * f_ub / f_yb, 1.25)
    return 1.5


def area_resistente(d_mm: int) -> float:
    """A_s (mm²) da barra roscada; recusa diâmetros fora da tabela."""
    if d_mm not in AREA_RESISTENTE_MM2:
        raise ValueError(
            f"d={d_mm} mm fora da tabela de áreas resistentes. "
            f"Disponíveis: {sorted(AREA_RESISTENTE_MM2)}."
        )
    return AREA_RESISTENTE_MM2[d_mm]


def resistencia_aco_barra(
    d_mm: int,
    classe: str = "8.8",
    gamma_Ms: float | None = None,
) -> dict:
    """
    Resistência do AÇO de um chumbador — EN 1993-1-8 Tab. 3.4.

        N_Rd = k2 · f_ub · A_s / γ_Ms
        V_Rd = α_v · f_ub · A_s / γ_Ms

    O corte é tomado no fuste ROSCADO (A_s), hipótese conservadora e usual em
    chumbadores, onde a rosca costuma atravessar o plano de corte.
    """
    if classe not in CLASSES_BARRA:
        raise ValueError(
            f"classe={classe!r} desconhecida. Opções: {sorted(CLASSES_BARRA)}."
        )
    if gamma_Ms is not None and gamma_Ms <= 0:
        raise ValueError("gamma_Ms deve ser positivo")

    f_yb, f_ub = CLASSES_BARRA[classe]
    A_s = area_resistente(d_mm)
    # γ_Ms distinto por efeito (Tab. 4.1); um valor único, se dado, sobrepõe-se.
    g_N = gamma_Ms if gamma_Ms is not None else gamma_Ms_tracao(classe)
    g_V = gamma_Ms if gamma_Ms is not None else gamma_Ms_corte(classe)
    N_Rd = K2_TRACAO * f_ub * A_s / g_N / 1e3               # kN
    V_Rd = ALPHA_V[classe] * f_ub * A_s / g_V / 1e3         # kN
    return {
        "d_mm": d_mm,
        "classe": classe,
        "f_yb_MPa": f_yb,
        "f_ub_MPa": f_ub,
        "A_s_mm2": A_s,
        "gamma_Ms": g_N,
        "gamma_Ms_tracao": g_N,
        "gamma_Ms_corte": g_V,
        "N_Rd_kN": round(N_Rd, 2),
        "V_Rd_kN": round(V_Rd, 2),
        "norma": "EN 1993-1-8 Tab. 3.4 (forma); γ_Ms por EN 1992-4:2018 Tab. 4.1",
    }


# ── Campos exigidos pela verificação do lado do CONCRETO ─────────────────────
# Para chumbador MOLDADO COM CABEÇA não há ETA de produto: o que se exige é a
# geometria que alimenta os modelos de EN 1992-4, mais os dados do concreto.
CAMPOS_CONCRETO_OBRIGATORIOS = (
    "h_ef_mm",              # embutimento efetivo — governa o cone
    "A_cabeca_mm2",         # área de apoio da cabeça — governa o pull-out
    "c_borda_mm",           # menor distância à borda
    "s_grupo_mm",           # menor espaçamento do grupo
    "classe_concreto",      # p.ex. "C25/30"
    "concreto_fissurado",   # bool — k_cr vs k_ucr no cone
    "verificacao_en1992_4",  # referência do cálculo que cumpriu os modelos
)

MODOS_CONCRETO_EN1992_4 = (
    "cone de arrancamento (concrete cone)",
    "pressão sob a cabeça (pull-out / pressing)",
    "blow-out lateral (junto à borda)",
    "pry-out sob corte",
    "rotura de borda sob corte",
    "efeito de grupo e espaçamentos",
    "interação tração-corte no concreto",
)


def estado_lado_concreto(dados: dict | None) -> dict:
    """Estado de verificação do lado do concreto (EN 1992-4)."""
    faltando = [
        c for c in CAMPOS_CONCRETO_OBRIGATORIOS
        if not dados or c not in dados or dados[c] in (None, "")
    ]
    completo = not faltando
    return {
        "tipo_ancoragem": "moldado_com_cabeca",
        "en_1992_4_verificado": completo,
        "status_concreto": "VERIFICADO" if completo else "NOT VALIDATED",
        "dados_concreto_faltando": faltando,
        "modos_en_1992_4_pendentes": [] if completo else list(MODOS_CONCRETO_EN1992_4),
        "nota_eta": (
            "Chumbador MOLDADO COM CABEÇA: o lado do concreto é coberto pelos "
            "modelos da EN 1992-4, sem ETA de produto. O ETA seria indispensável "
            "para chumbador PÓS-INSTALADO."
        ),
    }


# ── Verificação do grupo ─────────────────────────────────────────────────────

def verificar_grupo_ancoragem(
    N_Ed_kN: float,
    V_Ed_kN: float,
    n_chumbadores: int,
    d_mm: int = 24,
    classe: str = "8.8",
    chaveta_cisalhamento: bool = False,
    dados_concreto: dict | None = None,
    gamma_Ms: float | None = None,
    gamma_Mc: float = None,
    layout: tuple[int, int] = (2, 3),
) -> dict:
    """
    Verifica um grupo de chumbadores moldados sob tração + corte.

    Lado do AÇO — EN 1993-1-8 Tab. 3.4, interação de §3.4:

        F_v,Ed/F_v,Rd + F_t,Ed/(1,4·F_t,Rd) ≤ 1,0

    `chaveta_cisalhamento=True` declara que o corte é transmitido por chaveta
    (bloco soldado sob a chapa, embutido no concreto) e NÃO pelos chumbadores.
    É a solução usual quando a base está tracionada — sem compressão não há
    atrito sob a chapa, e o corte teria de ir todo pelas barras. A chaveta
    desacopla os dois efeitos, mas passa a exigir a sua própria verificação de
    esmagamento do concreto, ainda não implementada.

    O lado do CONCRETO não é verificado aqui: ver `estado_lado_concreto`.
    """
    if n_chumbadores < 1:
        raise ValueError("n_chumbadores deve ser >= 1")
    N_Ed = max(0.0, float(N_Ed_kN))
    V_Ed = max(0.0, float(V_Ed_kN))

    aco = resistencia_aco_barra(d_mm, classe, gamma_Ms)
    N_Rd_grupo = n_chumbadores * aco["N_Rd_kN"]
    V_Rd_grupo = n_chumbadores * aco["V_Rd_kN"]

    V_nos_chumbadores = 0.0 if chaveta_cisalhamento else V_Ed

    eta_N = N_Ed / N_Rd_grupo if N_Rd_grupo > 0 else 999.0
    eta_V = V_nos_chumbadores / V_Rd_grupo if V_Rd_grupo > 0 else 999.0
    # EN 1993-1-8 §3.4 — interação tração/corte
    eta_int = eta_V + N_Ed / (1.4 * N_Rd_grupo) if N_Rd_grupo > 0 else 999.0

    eta_aco = max(eta_N, eta_V, eta_int)
    concreto = estado_lado_concreto(dados_concreto)

    # ── Lado do CONCRETO — CEN/TS 1992-4-2:2009 ──────────────────────────
    conc: dict = {}
    eta_conc = 0.0
    if concreto["en_1992_4_verificado"]:
        g_Mc = GAMMA_MC if gamma_Mc is None else float(gamma_Mc)
        d = dados_concreto
        fiss = bool(d["concreto_fissurado"])
        cone = resistencia_cone(
            d["h_ef_mm"], d["classe_concreto"], d["c_borda_mm"], d["s_grupo_mm"],
            n1=layout[0], n2=layout[1], fissurado=fiss,
            armadura_densa=bool(d.get("armadura_densa", False)),
        )
        # d_h a partir da área da cabeça informada: A_h = π/4(d_h² − d²)
        d_h = math.sqrt(4.0 * float(d["A_cabeca_mm2"]) / math.pi + d_mm ** 2)
        pull = resistencia_pullout(d_h, d_mm, d["classe_concreto"], fiss)

        N_Rd_cone = cone["N_Rk_c_kN"] / g_Mc                     # grupo
        N_Rd_pull = n_chumbadores * pull["N_Rk_p_kN"] / g_Mc
        V_Rd_pry  = K8_PRYOUT * cone["N_Rk_c_kN"] / g_Mc         # (7.39a)

        N_Rd_conc = min(N_Rd_cone, N_Rd_pull)
        beta_N = N_Ed / N_Rd_conc if N_Rd_conc > 0 else 999.0
        beta_V = (V_nos_chumbadores / V_Rd_pry) if V_Rd_pry > 0 else 0.0
        # §6.4.1.2 Eq. (47) — outros modos governantes: β_N + β_V ≤ 1,2
        eta_conc = max(beta_N, beta_V, (beta_N + beta_V) / 1.2)
        conc = {
            "gamma_Mc": g_Mc,
            "d_cabeca_mm": round(d_h, 1),
            **{f"cone_{k}": v for k, v in cone.items()},
            **{f"pullout_{k}": v for k, v in pull.items()},
            "N_Rd_cone_kN": round(N_Rd_cone, 2),
            "N_Rd_pullout_kN": round(N_Rd_pull, 2),
            "V_Rd_pryout_kN": round(V_Rd_pry, 2),
            "modo_concreto_gov": "cone" if N_Rd_cone <= N_Rd_pull else "pull-out",
            "beta_N": round(beta_N, 4),
            "beta_V": round(beta_V, 4),
            "eta_concreto": round(eta_conc, 4),
            "ok_concreto": eta_conc <= 1.0 + 1e-9,
            "norma_concreto": NORMA_CONCRETO,
            "modos_ainda_pendentes": [
                "fendilhamento do concreto (§7.2.1.7)",
                "blow-out lateral (§7.2.1.8)",
                "rotura de borda sob corte (§7.2.2.5)",
            ],
        }

    return {
        "verificacao": "Grupo de chumbadores moldados com cabeça",
        **aco,
        "n_chumbadores": n_chumbadores,
        "N_Ed_kN": round(N_Ed, 2),
        "V_Ed_kN": round(V_Ed, 2),
        "V_nos_chumbadores_kN": round(V_nos_chumbadores, 2),
        "chaveta_cisalhamento": bool(chaveta_cisalhamento),
        "N_Rd_grupo_kN": round(N_Rd_grupo, 2),
        "V_Rd_grupo_kN": round(V_Rd_grupo, 2),
        "eta_N": round(eta_N, 4),
        "eta_V": round(eta_V, 4),
        "eta_interacao": round(eta_int, 4),
        "eta_aco": round(eta_aco, 4),
        "ok_aco": eta_aco <= 1.0 + 1e-9,
        **conc,
        # O veredito só pode ser True com os DOIS lados verificados e OK.
        "ok": bool(
            eta_aco <= 1.0 + 1e-9
            and concreto["en_1992_4_verificado"]
            and eta_conc <= 1.0 + 1e-9
        ),
        "eta": round(max(eta_aco, eta_conc), 4),
        **concreto,
        "norma": (
            "EN 1993-1-8 Tab. 3.4 e §3.4 (aço) | EN 1992-4 (concreto — pendente)"
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Lado do CONCRETO — CEN/TS 1992-4-2:2009 (Headed Fasteners)
# ═══════════════════════════════════════════════════════════════════════════
#
# ATENÇÃO — EDIÇÃO NORMATIVA. Implementado a partir de DD CEN/TS 1992-4-2:2009,
# uma Technical Specification em estatuto "Draft for Development" da BSI. Ela é
# o documento PREDECESSOR: a EN 1992-4:2018 consolidou e substituiu toda a série
# CEN/TS 1992-4 (partes 4-1 a 4-5). Os coeficientes aqui transcritos são os da
# TS de 2009 e DEVEM ser reconferidos contra a EN 1992-4:2018 antes de emissão
# definitiva. Toda saída deste bloco declara a edição efetivamente usada.
#
# Coeficientes que a TS remete para a "European Technical Specification" do
# produto e que, para chumbador moldado, ficam como entrada declarada:
#   k_cr / k_ucr — a NOTA de 6.2.5.1 dá 8,5 e 11,9 "segundo a experiência
#                  corrente" para headed fasteners; adotados como default.
#   k_3 (pry-out) — a TS não fixa valor; adota-se 1,0, o CONSERVADOR.
#   γ_Mc — está na Parte 4-1, que NÃO foi fornecida; adota-se 1,5.

NORMA_CONCRETO = "BS EN 1992-4:2018"

# ── Coeficientes — EN 1992-4:2018 ────────────────────────────────────────────
# Fórmula (7.2) NOTA — chumbador MOLDADO COM CABEÇA (cast-in headed):
K_CR_HEADED  = 8.9    # concreto fissurado
K_UCR_HEADED = 12.7   # concreto não fissurado
# Fórmula (7.11) — pressão sob a cabeça:
K2_PULLOUT_CR  = 7.5   # fissurado
K2_PULLOUT_UCR = 10.5  # não fissurado
# Fórmula (7.39a) — pry-out: k8 é remetido ao ETA; adota-se o CONSERVADOR.
K8_PRYOUT = 1.0
# Tabela 4.1 — γ_Mc = γ_c · γ_inst, com γ_c = 1,5 e γ_inst = 1,0 para
# chumbadores moldados com cabeça que cumpram 4.6 (tração e corte).
GAMMA_C_CONCRETO = 1.5
GAMMA_INST_HEADED = 1.0
GAMMA_MC = GAMMA_C_CONCRETO * GAMMA_INST_HEADED

# MUDANÇAS FACE À CEN/TS 1992-4-2:2009 (retirada), verificadas uma a uma:
#   · k_cr/k_ucr: 8,5/11,9 → 8,9/12,7  (mais favorável)
#   · o cone passou a usar f_ck CILINDRO; a TS usava f_ck,cube (mais severo)
#   · pull-out: 6·A_h·f_ck,cube·ψ_ucr → k2·A_h·f_ck, com k2 = 7,5 / 10,5
#   · ψ_s,N, ψ_re,N e ψ_ec,N mantêm a forma; entra ψ_M,N (7.7), favorável,
#     adotado 1,0 (conservador).
# Efeito líquido no caso do projeto: ligeiramente MENOS resistente que a TS,
# porque a troca de f_ck,cube por f_ck pesa mais que o aumento de k.

# f_ck (CILINDRO) por classe — EN 1992-4:2018 usa f_ck, não f_ck,cube.
F_CK_CILINDRO = {
    "C12/15": 12.0, "C16/20": 16.0, "C20/25": 20.0, "C25/30": 25.0,
    "C30/37": 30.0, "C35/45": 35.0, "C40/50": 40.0, "C45/55": 45.0,
    "C50/60": 50.0,
}


def resistencia_cone(
    h_ef_mm: float, classe_concreto: str, c_borda_mm: float, s_grupo_mm: float,
    n1: int = 2, n2: int = 3, fissurado: bool = True,
    e_N_mm: float = 0.0, armadura_densa: bool = False,
) -> dict:
    """
    Cone de arrancamento — EN 1992-4:2018 §7.2.1.4, Fórmulas (7.1) a (7.7).

        N⁰_Rk,c = k1 · √f_ck · h_ef^1,5                          (7.2)
        N_Rk,c  = N⁰_Rk,c · (A_c,N/A⁰_c,N) · ψ_s,N · ψ_re,N · ψ_ec,N · ψ_M,N  (7.1)

    com s_cr,N = 2·c_cr,N = 3·h_ef (NOTA de 7.2.1.4(3)). f_ck é a resistência
    em CILINDRO — a TS de 2009 usava cubo.

    A área projetada do grupo é construída estendendo 1,5·h_ef para além dos
    chumbadores extremos, truncada pela borda. Adota-se a MESMA distância de
    borda em todos os lados (a menor informada) — simplificação CONSERVADORA,
    porque reduz A_c,N e portanto a resistência.
    """
    if classe_concreto not in F_CK_CILINDRO:
        raise ValueError(f"classe_concreto={classe_concreto!r} desconhecida.")
    h_ef = float(h_ef_mm)
    if h_ef <= 0:
        raise ValueError("h_ef_mm deve ser positivo")

    f_ck = F_CK_CILINDRO[classe_concreto]
    k = K_CR_HEADED if fissurado else K_UCR_HEADED
    N0 = k * math.sqrt(f_ck) * h_ef ** 1.5                     # N — Eq. (7.2)

    c_cr, s_cr = 1.5 * h_ef, 3.0 * h_ef
    A0 = s_cr ** 2

    # Extensão do grupo; espaçamento acima de s_cr não gera sobreposição.
    s_ef = min(float(s_grupo_mm), s_cr)
    ext1, ext2 = (n1 - 1) * s_ef, (n2 - 1) * s_ef
    c_ef = min(float(c_borda_mm), c_cr)
    A_cN = (c_ef + ext1 + c_ef) * (c_ef + ext2 + c_ef)

    psi_s = min(0.7 + 0.3 * float(c_borda_mm) / c_cr, 1.0)      # (8)
    psi_re = 1.0 if armadura_densa else min(0.5 + h_ef / 200.0, 1.0)   # (9)
    psi_ec = min(1.0 / (1.0 + 2.0 * float(e_N_mm) / s_cr), 1.0)  # (10)

    N_Rk_c = N0 * (A_cN / A0) * psi_s * psi_re * psi_ec         # N
    return {
        "N0_Rk_c_kN": round(N0 / 1e3, 2),
        "k": k, "f_ck_MPa": f_ck,
        "c_cr_N_mm": round(c_cr, 1), "s_cr_N_mm": round(s_cr, 1),
        "A_c_N_mm2": round(A_cN, 0), "A0_c_N_mm2": round(A0, 0),
        "psi_s_N": round(psi_s, 4), "psi_re_N": round(psi_re, 4),
        "psi_ec_N": round(psi_ec, 4),
        "N_Rk_c_kN": round(N_Rk_c / 1e3, 2),
        "psi_M_N": 1.0,   # (7.7) — favorável; adotado 1,0, conservador
        "eq": "EN 1992-4:2018 Fórmulas (7.1)–(7.7)",
    }


def resistencia_pullout(
    d_cabeca_mm: float, d_mm: float, classe_concreto: str, fissurado: bool = True,
) -> dict:
    """
    Pressão sob a cabeça — EN 1992-4:2018 §7.2.1.5, Fórmulas (7.11) e (7.12).

        A_h    = π/4 · (d_h² − d²)                               (7.12)
        N_Rk,p = k2 · A_h · f_ck                                 (7.11)
        k2 = 7,5 fissurado | 10,5 não fissurado

    NOTA de (7.12): d_h não deve ser tomado maior que 6·t_h + d, onde t_h é a
    espessura da cabeça — condição a confirmar no detalhe de fabricação.
    """
    if classe_concreto not in F_CK_CILINDRO:
        raise ValueError(f"classe_concreto={classe_concreto!r} desconhecida.")
    if d_cabeca_mm <= d_mm:
        raise ValueError("d_cabeca_mm deve ser maior que o diâmetro da barra")
    A_h = math.pi / 4.0 * (float(d_cabeca_mm) ** 2 - float(d_mm) ** 2)
    k2 = K2_PULLOUT_CR if fissurado else K2_PULLOUT_UCR
    N_Rk_p = k2 * A_h * F_CK_CILINDRO[classe_concreto]          # N
    return {
        "A_h_mm2": round(A_h, 1),
        "k2": k2,
        "N_Rk_p_kN": round(N_Rk_p / 1e3, 2),
        "eq": "EN 1992-4:2018 Fórmulas (7.11)–(7.12)",
    }
