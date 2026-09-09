"""
connections/ligacao_diagonal.py — Ligações de EXTREMIDADE das diagonais de
contraventamento (EN 1993-1-8 §3.13 · §4.5).

Achado A3 da auditoria de conformidade ao Eurocódigo
----------------------------------------------------
A BARRA estava verificada — `checks/elu/contraventamento_vertical.py` resolveu
o [F-11] e passou a fazer `N_t,Rd = min(N_pl,Rd ; 0,9·A_net·f_u/γ_M2)` com a
área resistente da rosca. Mas o que segura a barra não existia em lado nenhum:

    barra (η = 0,79)  →  rosca/manilha  →  PINO  →  chapa-olhal  →  solda  →  ✗

Numa cruz de Santo André com tirantes roscados, o elo fraco é quase sempre a
extremidade, não o fuste. Ter a barra a 0,79 e a extremidade por dimensionar é
publicar uma taxa de utilização que não descreve o sistema.

Detalhe adotado
---------------
Barra redonda roscada → manilha (forquilha) → **pino** → chapa-olhal soldada ao
pilar/chapa de base. É o detalhe corrente para tirantes de contraventamento e é
o único totalmente coberto pelo Eurocódigo: §3.13 dá as ligações por pino com
tabela de geometria e de resistências, §4.5 dá a solda de ângulo.

    ┌── chapa-olhal (espessura t_eye)  ← soldada à estrutura
    │   ╱ pino Ø d_p, corte DUPLO
    └── manilha: duas abas de espessura t_fork, folga c

Verificações implementadas (EN 1993-1-8 Tab. 3.10 e §4.5.3.3)
--------------------------------------------------------------
    corte do pino          F_v,Rd = 0,6·A·f_up/γ_M2         (por plano)
    esmagamento chapa/pino F_b,Rd = 1,5·t·d·f_y/γ_M0
    flexão do pino         M_Rd   = 1,5·W_el·f_yp/γ_M0
                           M_Ed   = F_Ed/8 · (b + 4c + 2a)   Fig. 3.11
    interação              (M_Ed/M_Rd)² + (F_v,Ed/F_v,Rd)² ≤ 1
    geometria do olhal     Tab. 3.9, tipo B (espessura dada):
                           a ≥ F_Ed·γ_M0/(2·t·f_y) + 2·d_0/3
                           c ≥ F_Ed·γ_M0/(2·t·f_y) + d_0/3
    solda de ângulo        F_w,Rd = a_w·f_u/(√3·β_w·γ_M2) por unidade de
                           comprimento — §4.5.3.3 (método simplificado)

Critério de dimensionamento — CAPACIDADE, não esforço
-----------------------------------------------------
Por omissão a ligação é dimensionada para a RESISTÊNCIA DE CÁLCULO DA BARRA
(`criterio="capacidade"`), não para `N_Ed`. Razão de engenharia, não de
conservadorismo cego: num sistema de contraventamento quer-se que a plastificação
aconteça no tirante — dúctil, visível, com aviso — e não no pino ou na solda,
que rompem de forma frágil. É também o que torna a ligação indiferente à
combinação que governa, e portanto imune ao resíduo do [F-06].

`criterio="esforco"` dimensiona para `N_Ed` e fica disponível para quem queira
justificar a economia; a saída declara sempre qual foi usado e a razão
`N_conexao,Rd / N_barra,Rd`.

A manilha (forquilha) é peça de catálogo: NÃO se dimensiona aqui. A saída
publica a força que ela tem de garantir, para especificação com o fabricante —
declarar o requisito é verificação; inventar a resistência de um produto não é.

Referências: EN 1993-1-8:2005 §3.13 (Tab. 3.9, Tab. 3.10, Fig. 3.11),
             §4.5.3.3 e Tab. 4.1 (β_w); EN 1993-1-1 §6.1 (γ_M0, γ_M2).
"""

from __future__ import annotations

import math

# ── Coeficientes parciais e materiais (EN 1993-1-1 §6.1 / EN 1993-1-8) ───────
GAMMA_M0 = 1.00
GAMMA_M2 = 1.25

#: β_w — fator de correlação da solda de ângulo (EN 1993-1-8 Tab. 4.1).
BETA_W = {"S235": 0.80, "S275": 0.85, "S355": 0.90}

ACO = {
    "S235": {"f_y": 235.0, "f_u": 360.0},
    "S275": {"f_y": 275.0, "f_u": 430.0},
    "S355": {"f_y": 355.0, "f_u": 510.0},
}

#: Diâmetros comerciais de pino (mm).
D_PINO_COMERCIAL_MM = (16, 20, 24, 27, 30, 33, 36, 39, 42, 45, 48, 52, 56, 60)

#: Espessuras comerciais de chapa (mm).
T_CHAPA_COMERCIAL_MM = (8, 10, 12, 15, 16, 20, 22, 25, 30, 35, 40)

#: Gargantas comerciais de solda de ângulo (mm). O mínimo de 3 mm é o usual
#: de execução; a EN 1993-1-8 §4.5.1(1) só exige a > 3 mm para a garganta
#: efetiva ser considerada.
A_SOLDA_COMERCIAL_MM = (4, 5, 6, 7, 8, 10, 12)

#: Folga do furo do pino (mm) — pino maquinado, ajuste normal.
FOLGA_FURO_PINO_MM = 1.0

#: Folga entre a chapa-olhal e cada aba da manilha (mm) — `c` da Fig. 3.11.
FOLGA_MANILHA_MM = 2.0


def _aco(nome: str) -> dict:
    if nome not in ACO:
        raise ValueError(f"Aço '{nome}' não reconhecido. Use {sorted(ACO)}.")
    return ACO[nome]


# ── Resistências elementares (EN 1993-1-8 Tab. 3.10) ─────────────────────────

def resistencia_corte_pino(d_pino_mm: float, aco_pino: str) -> float:
    """
    Corte do pino, POR PLANO de corte — Tab. 3.10.

        F_v,Rd = 0,6 · A · f_up / γ_M2

    Returns:
        F_v,Rd (kN) por plano.
    """
    A = math.pi * float(d_pino_mm) ** 2 / 4.0                 # mm²
    return 0.6 * A * _aco(aco_pino)["f_u"] / GAMMA_M2 / 1e3


def resistencia_esmagamento(t_mm: float, d_pino_mm: float, aco_chapa: str) -> float:
    """
    Esmagamento da chapa (e do pino) — Tab. 3.10.

        F_b,Rd = 1,5 · t · d · f_y / γ_M0

    Returns:
        F_b,Rd (kN).
    """
    return (1.5 * float(t_mm) * float(d_pino_mm)
            * _aco(aco_chapa)["f_y"] / GAMMA_M0 / 1e3)


def momento_resistente_pino(d_pino_mm: float, aco_pino: str) -> float:
    """
    Flexão do pino — Tab. 3.10: M_Rd = 1,5 · W_el · f_yp / γ_M0.

    Returns:
        M_Rd (kN·m).
    """
    W_el = math.pi * float(d_pino_mm) ** 3 / 32.0             # mm³
    return 1.5 * W_el * _aco(aco_pino)["f_y"] / GAMMA_M0 / 1e6


def momento_atuante_pino(
    F_Ed_kN: float, t_eye_mm: float, t_fork_mm: float, c_mm: float,
) -> float:
    """
    Momento de cálculo no pino — EN 1993-1-8 Fig. 3.11.

        M_Ed = F_Ed/8 · (b + 4c + 2a)

    com `b` a espessura da chapa interior (o olhal), `a` a espessura de CADA
    aba exterior (a manilha) e `c` a folga entre elas.

    Returns:
        M_Ed (kN·m).
    """
    braco_mm = float(t_eye_mm) + 4.0 * float(c_mm) + 2.0 * float(t_fork_mm)
    return float(F_Ed_kN) * braco_mm / 8.0 / 1e3


def geometria_olhal_requerida(
    F_Ed_kN: float, t_mm: float, d_0_mm: float, aco_chapa: str,
) -> dict:
    """
    Geometria mínima do olhal — EN 1993-1-8 Tab. 3.9, tipo B (espessura dada).

        a ≥ F_Ed·γ_M0/(2·t·f_y) + 2·d_0/3      (borda na direção da força)
        c ≥ F_Ed·γ_M0/(2·t·f_y) + d_0/3        (borda transversal)

    O termo comum `F·γ_M0/(2·t·f_y)` é a largura de chapa que plastifica de cada
    lado do furo; os termos em d_0 garantem a distância ao furo. É esta cláusula
    que substitui, no olhal, a verificação de seção líquida de §6.2.3.

    Returns:
        dict com a_req_mm, c_req_mm e o termo comum.
    """
    f_y = _aco(aco_chapa)["f_y"]
    termo = float(F_Ed_kN) * 1e3 * GAMMA_M0 / (2.0 * float(t_mm) * f_y)   # mm
    return {
        "termo_plastificacao_mm": termo,
        "a_req_mm": termo + 2.0 * float(d_0_mm) / 3.0,
        "c_req_mm": termo + float(d_0_mm) / 3.0,
        "norma": "EN 1993-1-8 Tab. 3.9 (tipo B — espessura dada)",
    }


def resistencia_solda_angulo(
    a_solda_mm: float, l_solda_mm: float, n_cordoes: int, aco_chapa: str,
) -> float:
    """
    Solda de ângulo pelo método SIMPLIFICADO — EN 1993-1-8 §4.5.3.3.

        f_vw,d = (f_u/√3) / (β_w · γ_M2)
        F_w,Rd = f_vw,d · a  (por unidade de comprimento) × Σ comprimentos

    O método simplificado dispensa a decomposição de tensões do §4.5.3.2 e é
    conservador para qualquer direção da força — que é o que se quer num
    cordão de olhal, onde a direção depende da diagonal ativa.

    Returns:
        F_w,Rd (kN).
    """
    if aco_chapa not in BETA_W:
        raise ValueError(f"β_w não tabelado para '{aco_chapa}'. "
                         f"EN 1993-1-8 Tab. 4.1: {sorted(BETA_W)}.")
    f_u = _aco(aco_chapa)["f_u"]
    f_vw_d = (f_u / math.sqrt(3.0)) / (BETA_W[aco_chapa] * GAMMA_M2)   # MPa
    return f_vw_d * float(a_solda_mm) * float(l_solda_mm) * int(n_cordoes) / 1e3


# ── Verificação completa de uma ligação ──────────────────────────────────────

def verificar_ligacao_diagonal(
    N_Ed_kN:     float,
    d_pino_mm:   float,
    t_eye_mm:    float,
    t_fork_mm:   float,
    a_borda_mm:  float,
    c_borda_mm:  float,
    a_solda_mm:  float,
    l_solda_mm:  float,
    *,
    aco_chapa:   str = "S235",
    aco_pino:    str = "S355",
    n_cordoes:   int = 2,
    c_folga_mm:  float = FOLGA_MANILHA_MM,
    nome:        str = "ligacao_diagonal",
) -> dict:
    """
    Verifica todos os modos da ligação de extremidade da diagonal.

    Args:
        N_Ed_kN    : força de tração a transmitir (kN)
        d_pino_mm  : diâmetro do pino
        t_eye_mm   : espessura da chapa-olhal (interior, recebe F inteiro)
        t_fork_mm  : espessura de CADA aba da manilha (recebe F/2)
        a_borda_mm : distância do furo à borda na direção da força
        c_borda_mm : distância do furo à borda transversal
        a_solda_mm : garganta do cordão de ângulo
        l_solda_mm : comprimento de CADA cordão
        n_cordoes  : número de cordões (2 = ambos os lados da chapa)

    Returns:
        dict com η por modo, o modo governante, η e ok.
    """
    F = abs(float(N_Ed_kN))
    d_0 = float(d_pino_mm) + FOLGA_FURO_PINO_MM

    # 1) Corte do pino — corte DUPLO: cada plano recebe F/2
    F_v_Rd = resistencia_corte_pino(d_pino_mm, aco_pino)
    eta_corte = (F / 2.0) / F_v_Rd

    # 2) Esmagamento — o olhal recebe F; cada aba da manilha recebe F/2
    F_b_eye = resistencia_esmagamento(t_eye_mm, d_pino_mm, aco_chapa)
    F_b_fork = resistencia_esmagamento(t_fork_mm, d_pino_mm, aco_chapa)
    eta_esm_eye = F / F_b_eye
    eta_esm_fork = (F / 2.0) / F_b_fork

    # 3) Flexão do pino
    M_Ed = momento_atuante_pino(F, t_eye_mm, t_fork_mm, c_folga_mm)
    M_Rd = momento_resistente_pino(d_pino_mm, aco_pino)
    eta_flexao = M_Ed / M_Rd

    # 4) Interação flexão + corte (Tab. 3.10)
    eta_interacao = (M_Ed / M_Rd) ** 2 + ((F / 2.0) / F_v_Rd) ** 2

    # 5) Geometria do olhal (Tab. 3.9 tipo B) — η como razão requerido/existente
    geo = geometria_olhal_requerida(F, t_eye_mm, d_0, aco_chapa)
    eta_a = geo["a_req_mm"] / float(a_borda_mm)
    eta_c = geo["c_req_mm"] / float(c_borda_mm)

    # 6) Solda do olhal à estrutura
    F_w_Rd = resistencia_solda_angulo(a_solda_mm, l_solda_mm, n_cordoes, aco_chapa)
    eta_solda = F / F_w_Rd

    modos = {
        "corte_pino":         eta_corte,
        "esmagamento_olhal":  eta_esm_eye,
        "esmagamento_manilha": eta_esm_fork,
        "flexao_pino":        eta_flexao,
        "interacao_M_V":      eta_interacao,
        "geometria_a":        eta_a,
        "geometria_c":        eta_c,
        "solda":              eta_solda,
    }
    modo_gov = max(modos, key=modos.get)
    eta = modos[modo_gov]

    return {
        "nome":          nome,
        "N_Ed_kN":       round(F, 3),
        "d_pino_mm":     float(d_pino_mm),
        "d_0_mm":        round(d_0, 1),
        "t_eye_mm":      float(t_eye_mm),
        "t_fork_mm":     float(t_fork_mm),
        "a_borda_mm":    round(float(a_borda_mm), 1),
        "c_borda_mm":    round(float(c_borda_mm), 1),
        "a_req_mm":      round(geo["a_req_mm"], 2),
        "c_req_mm":      round(geo["c_req_mm"], 2),
        "a_solda_mm":    float(a_solda_mm),
        "l_solda_mm":    float(l_solda_mm),
        "n_cordoes":     int(n_cordoes),
        "aco_chapa":     aco_chapa,
        "aco_pino":      aco_pino,
        "F_v_Rd_kN":     round(F_v_Rd, 2),
        "F_b_Rd_olhal_kN":  round(F_b_eye, 2),
        "F_b_Rd_manilha_kN": round(F_b_fork, 2),
        "M_Ed_kNm":      round(M_Ed, 4),
        "M_Rd_kNm":      round(M_Rd, 4),
        "F_w_Rd_kN":     round(F_w_Rd, 2),
        "etas":          {k: round(v, 4) for k, v in modos.items()},
        "modo_gov":      modo_gov,
        "eta":           round(eta, 4),
        "ok":            eta <= 1.0,
        "norma": "EN 1993-1-8 §3.13 (Tab. 3.9/3.10, Fig. 3.11) + §4.5.3.3",
    }


def dimensionar_ligacao_diagonal(
    N_Ed_kN:      float,
    N_barra_Rd_kN: float,
    d_barra_mm:   float,
    *,
    criterio:     str = "capacidade",
    aco_chapa:    str = "S235",
    aco_pino:     str = "S355",
    eta_alvo:     float = 0.90,
    l_solda_mm:   float | None = None,
    nome:         str = "ligacao_diagonal",
) -> dict:
    """
    Dimensiona a ligação de extremidade e devolve-a verificada.

    O critério de projeto está no docstring do módulo: por omissão dimensiona-se
    para a RESISTÊNCIA DA BARRA, para que a plastificação (dúctil) fique no
    tirante e não no pino ou na solda (frágeis).

    Args:
        N_Ed_kN       : esforço de cálculo na diagonal
        N_barra_Rd_kN : N_t,Rd da barra (EN 1993-1-1 §6.2.3(2))
        d_barra_mm    : diâmetro da barra — o pino não desce abaixo dele
        criterio      : "capacidade" (N_barra_Rd) | "esforco" (N_Ed)
        eta_alvo      : utilização máxima admitida no dimensionamento
        l_solda_mm    : comprimento de cada cordão; None ⇒ derivado da geometria

    Returns:
        dict da verificação, acrescido do critério e da razão de sobre-resistência.
    """
    if criterio not in ("capacidade", "esforco"):
        raise ValueError("criterio deve ser 'capacidade' ou 'esforco'")
    if not 0.0 < eta_alvo <= 1.0:
        raise ValueError("eta_alvo deve estar em (0, 1]")

    N_proj = (abs(float(N_barra_Rd_kN)) if criterio == "capacidade"
              else abs(float(N_Ed_kN)))
    if N_proj <= 0.0:
        raise ValueError("A força de dimensionamento tem de ser positiva.")

    # A manilha é peça de catálogo: as abas seguem a espessura do olhal, que é
    # o que o projeto controla. Regra de detalhe corrente: t_fork ≈ 0,6·t_eye,
    # de modo que 2·t_fork ≥ t_eye (as duas abas juntas nunca são mais fracas
    # que a chapa interior).
    #
    # A varredura NÃO levanta exceção quando nada serve (regra 5 das convenções
    # do projeto: η > 1 regista-se, não se lança). Devolve o MELHOR detalhe
    # comercial com `alvo_atingido = False` — o memorial reprova a linha em vez
    # de rebentar o pipeline, que é o comportamento certo quando a estrutura a
    # montante é que está mal dimensionada.
    pinos = [d for d in D_PINO_COMERCIAL_MM if d >= float(d_barra_mm)]
    pino_menor_que_barra = not pinos
    if pino_menor_que_barra:
        # Nenhum pino comercial chega ao diâmetro da barra. Usa-se o maior e
        # declara-se: é um defeito do detalhe, não um resultado ausente.
        pinos = [D_PINO_COMERCIAL_MM[-1]]

    melhor = None
    for d_p in pinos:
        for t_eye in T_CHAPA_COMERCIAL_MM:
            t_fork = max(T_CHAPA_COMERCIAL_MM[0], round(0.6 * t_eye))
            d_0 = d_p + FOLGA_FURO_PINO_MM
            g = geometria_olhal_requerida(N_proj, t_eye, d_0, aco_chapa)
            # Bordas: o requisito da Tab. 3.9 com folga de 10 %, arredondado
            # para cima ao múltiplo de 5 mm (fabricação).
            a_b = 5.0 * math.ceil(g["a_req_mm"] * 1.1 / 5.0)
            c_b = 5.0 * math.ceil(g["c_req_mm"] * 1.1 / 5.0)
            # Comprimento do cordão: a altura da chapa junto à estrutura, que
            # é pelo menos a largura do olhal (2c + d_0).
            l_w = float(l_solda_mm) if l_solda_mm else max(
                100.0, 5.0 * math.ceil((2.0 * c_b + d_0) / 5.0))
            for a_w in A_SOLDA_COMERCIAL_MM:
                if a_w > t_eye * 0.7:      # garganta não excede 0,7·t da chapa
                    continue
                r_cap = verificar_ligacao_diagonal(
                    N_proj, d_p, t_eye, t_fork, a_b, c_b, a_w, l_w,
                    aco_chapa=aco_chapa, aco_pino=aco_pino, nome=nome,
                )
                cand = (r_cap["eta"], d_p, t_eye, t_fork, a_b, c_b, a_w, l_w)
                if melhor is None or cand[0] < melhor[0]:
                    melhor = cand
                if r_cap["eta"] <= eta_alvo:
                    return _montar_saida(
                        melhor=cand, N_Ed_kN=N_Ed_kN, N_proj=N_proj,
                        N_barra_Rd_kN=N_barra_Rd_kN, criterio=criterio,
                        aco_chapa=aco_chapa, aco_pino=aco_pino, nome=nome,
                        alvo_atingido=True, eta_alvo=eta_alvo,
                        pino_menor_que_barra=pino_menor_que_barra,
                        r_cap=r_cap,
                    )

    # Nada atinge o alvo: devolve-se o melhor, declarado.
    return _montar_saida(
        melhor=melhor, N_Ed_kN=N_Ed_kN, N_proj=N_proj,
        N_barra_Rd_kN=N_barra_Rd_kN, criterio=criterio,
        aco_chapa=aco_chapa, aco_pino=aco_pino, nome=nome,
        alvo_atingido=False, eta_alvo=eta_alvo,
        pino_menor_que_barra=pino_menor_que_barra, r_cap=None,
    )


def _montar_saida(
    *, melhor, N_Ed_kN, N_proj, N_barra_Rd_kN, criterio, aco_chapa, aco_pino,
    nome, alvo_atingido, eta_alvo, pino_menor_que_barra, r_cap,
):
    """
    Monta o resultado do dimensionamento a partir do detalhe escolhido.

    A linha do memorial tem de ser comparável às outras: `eta` é E_d/R_d sob o
    ESFORÇO REAL, como em todas as verificações. O η sob a capacidade da barra
    fica ao lado, com o seu próprio modo governante — e o `ok` exige AMBOS ≤ 1,
    senão o critério de capacidade seria decorativo.
    """
    _, d_p, t_eye, t_fork, a_b, c_b, a_w, l_w = melhor
    if r_cap is None:
        r_cap = verificar_ligacao_diagonal(
            N_proj, d_p, t_eye, t_fork, a_b, c_b, a_w, l_w,
            aco_chapa=aco_chapa, aco_pino=aco_pino, nome=nome,
        )
    r = verificar_ligacao_diagonal(
        abs(float(N_Ed_kN)), d_p, t_eye, t_fork, a_b, c_b, a_w, l_w,
        aco_chapa=aco_chapa, aco_pino=aco_pino, nome=nome,
    )
    r["criterio"] = criterio
    r["N_Ed_real_kN"] = round(abs(float(N_Ed_kN)), 3)
    r["N_dimensionamento_kN"] = round(N_proj, 3)
    r["N_barra_Rd_kN"] = round(float(N_barra_Rd_kN), 3)
    r["sobre_resistencia"] = round(N_proj / max(abs(float(N_Ed_kN)), 1e-9), 3)
    r["eta_capacidade"] = r_cap["eta"]
    r["etas_capacidade"] = r_cap["etas"]
    r["modo_gov_capacidade"] = r_cap["modo_gov"]
    r["alvo_atingido"] = bool(alvo_atingido)
    r["eta_alvo"] = float(eta_alvo)
    r["pino_menor_que_barra"] = bool(pino_menor_que_barra)
    r["ok"] = bool(
        r["eta"] <= 1.0 and r_cap["eta"] <= 1.0 and not pino_menor_que_barra
    )
    r["requisito_manilha_kN"] = round(N_proj, 3)
    r["nota_manilha"] = (
        "A manilha/forquilha e a rosca de extremidade são peças de catálogo: "
        f"especificar com resistência de cálculo à tração ≥ {N_proj:.1f} kN, "
        "certificada pelo fabricante. Não são dimensionadas neste memorial."
    )
    if pino_menor_que_barra:
        r["motivo"] = (
            f"Nenhum pino comercial atinge o diâmetro da barra "
            f"(máx {D_PINO_COMERCIAL_MM[-1]} mm). O detalhe não é exequível "
            f"como está: rever a barra ou adotar pino fora de catálogo."
        )
    elif not alvo_atingido:
        r["motivo"] = (
            f"Nenhum detalhe comercial atinge η ≤ {eta_alvo} para "
            f"N = {N_proj:.1f} kN; devolve-se o melhor (η = {r_cap['eta']}). "
            f"Rever chapa, pino ou comprimento de cordão."
        )
    return r
