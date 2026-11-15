"""
opensees/diafragma_espacial.py — Modelo em planta do diafragma da cobertura (issue 110).

Pergunta da revisão técnica: como uma força transversal aplicada num pórtico
intermediário (ex.: o 5) chega às fundações dos frontões, se vigas, terças e pilares
são todos rotulados?

Modelo (OpenSeesPy, 2D em planta, ndm=2, ndf=2), com as liberações reais:
  · nós nos cruzamentos de terças (linhas T1…T17, a cada s) e eixos dos pórticos
    (1…9, a cada L_T); a inclinação de 10° das águas é desprezada (cos 10° = 0,985);
  · vigas e terças como barras rotuladas (truss): ligações viga–pilar, terça–viga e
    emendas não transmitem momento no plano da cobertura. Sem diagonais, a grelha de
    retângulos é um MECANISMO — o modelo o detecta (matriz singular);
  · cruzes de St. André só à tração (material Elastic com E_neg = 0), por isso
    análise não linear em passos de carga;
  · frontões: os painéis CV-T (P1–PF1 no eixo 1, PF2–P27 no eixo 9) como molas na
    direção transversal, com a rigidez horizontal C_h do painel;
  · direção longitudinal: os painéis CV-V como molas, só para tirar o movimento de
    corpo rígido no caso transversal;
  · cargas: a força transversal de cálculo H_tr repartida igualmente pelos 9 pórticos
    e, em cada um, pelos três topos de pilar (linhas A, B, C).

Saídas: reações dos frontões, deslocamento máximo (pórtico 5), esforço máximo das
diagonais por baía, força nas cordas (T1/T17) e a rigidez equivalente K = H_tr/δ_max,
que alimenta o α_cr transversal no lugar da rigidez só dos painéis dos frontões.
"""

from __future__ import annotations

import math


def analisar_diafragma(*, L_T: float, n_eixos: int, s: float, n_faixas: int,
                       A_terca_m2: float, A_viga_m2: float, E_mlc_kPa: float,
                       d_diag_mm_por_baia: list[float] | None,
                       C_h_frontao_kNpm: float, C_h_long_kNpm: float,
                       H_tr_kN: float, F_portico_kN: float | None = None,
                       portico_carregado: int | None = None,
                       sem_viga: tuple[int, int, int] | None = None,
                       cargas: list[tuple[int, int, float, float]] | None = None) -> dict:
    """
    Resolve o diafragma em planta. `d_diag_mm_por_baia[i]` é o diâmetro das cruzes
    da baía i (entre os eixos i+1 e i+2); None numa baía = sem cruzes. Com
    `F_portico_kN` e `portico_carregado`, aplica só essa força (caso do pórtico 5).
    Devolve {"mecanismo": True} se a matriz for singular.
    """
    import openseespy.opensees as ops

    import os
    E_aco = 200e6  # kPa
    ops.wipe()
    ops.logFile(os.devnull, "-noEcho")   # o caso sem alma é singular de propósito
    ops.model("basic", "-ndm", 2, "-ndf", 2)
    nid = lambda i, j: 1000 * (i + 1) + j + 1
    for i in range(n_eixos):
        for j in range(n_faixas + 1):
            ops.node(nid(i, j), i * L_T, j * s)
    # materiais: 1 = MLC (barra), 2.. = aço só à tração por diâmetro
    ops.uniaxialMaterial("Elastic", 1, E_mlc_kPa)
    ele = 0
    for i in range(n_eixos):                     # vigas (direção y)
        for j in range(n_faixas):
            ele += 1
            if sem_viga and i == sem_viga[0] and sem_viga[1] <= j < sem_viga[2]:
                A = 1e-9 * A_viga_m2                 # viga retirada (issue 113)
            else:
                A = A_viga_m2
            ops.element("truss", ele, nid(i, j), nid(i, j + 1), A, 1)
    for i in range(n_eixos - 1):                 # terças (direção x)
        for j in range(n_faixas + 1):
            ele += 1
            ops.element("truss", ele, nid(i, j), nid(i + 1, j), A_terca_m2, 1)
    diag = {}
    mats = {}
    for i, d in enumerate(d_diag_mm_por_baia or []):
        if not d:
            continue
        if d not in mats:
            mats[d] = 10 + len(mats)
            ops.uniaxialMaterial("Elastic", mats[d], E_aco, 0.0, 0.0)   # E_neg = 0
        A = math.pi * (d / 1000.0) ** 2 / 4.0
        for j in range(n_faixas):
            for (a, b) in (((i, j), (i + 1, j + 1)), ((i, j + 1), (i + 1, j))):
                ele += 1
                ops.element("truss", ele, nid(*a), nid(*b), A, mats[d])
                diag[ele] = i
    # molas: frontões (y) e CV-V (x)
    ops.uniaxialMaterial("Elastic", 2, C_h_frontao_kNpm)
    ops.uniaxialMaterial("Elastic", 3, C_h_long_kNpm)
    molas = []
    for (i, j) in ((0, 0), (n_eixos - 1, n_faixas)):          # CV-T: canto A eixo 1, canto C eixo 9
        terra = 900000 + len(molas)
        ops.node(terra, i * L_T, j * s); ops.fix(terra, 1, 1)
        ele += 1
        ops.element("zeroLength", ele, terra, nid(i, j), "-mat", 2, "-dir", 2)
        molas.append((ele, "y", i, j))
    for i in (0, n_eixos - 1):                                 # CV-V nas fachadas e no centro
        for j in (0, n_faixas // 2, n_faixas):
            terra = 900000 + len(molas)
            ops.node(terra, i * L_T, j * s); ops.fix(terra, 1, 1)
            ele += 1
            ops.element("zeroLength", ele, terra, nid(i, j), "-mat", 3, "-dir", 1)
            molas.append((ele, "x", i, j))
    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    if cargas:
        for (i, j, fx, fy) in cargas:
            ops.load(nid(i, j), fx, fy)
    elif F_portico_kN is not None:
        for j in (0, n_faixas // 2, n_faixas):
            ops.load(nid(portico_carregado, j), 0.0, F_portico_kN / 3.0)
    else:
        P = H_tr_kN / n_eixos / 3.0
        for i in range(n_eixos):
            for j in (0, n_faixas // 2, n_faixas):
                ops.load(nid(i, j), 0.0, P)
    ops.system("BandGeneral"); ops.numberer("RCM"); ops.constraints("Plain")
    ops.test("NormDispIncr", 1e-9, 100)
    ops.algorithm("Newton")
    n_passos = 10
    ops.integrator("LoadControl", 1.0 / n_passos)
    ops.analysis("Static")
    ok = 0
    for _ in range(n_passos):
        ok = ops.analyze(1)
        if ok != 0:
            break
    if ok != 0:
        ops.wipe()
        return {"mecanismo": True, "nota": "matriz singular ou sem convergência: "
                "a grelha rotulada sem alma é um mecanismo no plano da cobertura"}
    uy = {(i, j): ops.nodeDisp(nid(i, j), 2) for i in range(n_eixos) for j in range(n_faixas + 1)}
    d_max = max(abs(v) for v in uy.values())
    reac = {f"{dir_}({i},{j})": -ops.eleResponse(e, "force")[0 if dir_ == "x" else 1]
            for (e, dir_, i, j) in molas}
    R_front = [abs(ops.eleResponse(e, "force")[1]) for (e, dir_, i, j) in molas if dir_ == "y"]
    F_diag = {}
    for e, i in diag.items():
        f = ops.eleResponse(e, "axialForce")[0]
        F_diag[i] = max(F_diag.get(i, 0.0), f)
    # corda: maior esforço normal das terças de beiral (j = 0 e j = n_faixas)
    corda = 0.0
    e0 = n_eixos * n_faixas
    for i in range(n_eixos - 1):
        for j in (0, n_faixas):
            e = e0 + i * (n_faixas + 1) + j + 1
            corda = max(corda, abs(ops.eleResponse(e, "axialForce")[0]))
    H_tot = F_portico_kN if F_portico_kN is not None else H_tr_kN
    u_y_no = {(i, j): ops.nodeDisp(nid(i, j), 2) for i in range(n_eixos)
              for j in range(n_faixas + 1)}
    ops.wipe()
    return {"mecanismo": False, "delta_max_mm": round(d_max * 1000, 3),
            "K_eq_kNpm": round(H_tot / d_max, 1) if d_max > 0 else math.inf,
            "R_frontoes_kN": [round(r, 2) for r in R_front],
            "F_diag_max_kN_por_baia": {i + 1: round(f, 2) for i, f in sorted(F_diag.items())},
            "N_corda_max_kN": round(corda, 2), "H_aplicado_kN": round(H_tot, 2),
            "u_y_no_m": u_y_no,
            "uy_portico_mm": [round(max(abs(uy[(i, j)]) for j in range(n_faixas + 1)) * 1000, 3)
                              for i in range(n_eixos)]}
