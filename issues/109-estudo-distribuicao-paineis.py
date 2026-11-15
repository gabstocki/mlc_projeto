"""Issue 109 — refaz a tab:distribuicao-paineis (cap. 5) com o vento longitudinal majorado.

Para cada par (painéis nas fachadas, painéis no alinhamento central) roda o pipeline
completo com a diagonal automática (η ≤ 0,90) e registra: diâmetros, cortante por painel,
η da lâmina do bipartido de canto e do central montante, η da ancoragem central montante,
aço das diagonais verticais, baías ocupadas e status.
Uso: .venv/bin/python issues/109-estudo-distribuicao-paineis.py
"""
import contextlib
import io

import mlc_projeto.main as M

M.gerar_relatorio = lambda *a, **k: None
orig = (M.N_PAINEIS_CV_VERT, M.N_PAINEIS_CV_CENTRAL)
linhas = []
for nf, nc in ((4, 2), (8, 2), (4, 4), (8, 4), (12, 4), (4, 8), (8, 8)):
    M.N_PAINEIS_CV_VERT, M.N_PAINEIS_CV_CENTRAL = nf, nc
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            r = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.N_PAINEIS_CV_VERT, M.N_PAINEIS_CV_CENTRAL = orig
    v, c = r["contraventamento_vertical"], r["contraventamento_vertical_central"]
    reprov = [k for k, x in r.items() if isinstance(x, dict) and x.get("ok") is False]
    linhas.append((nf, nc, v["d_mm"], c["d_mm"], v["V_painel_kN"], c["V_painel_kN"],
                   r["pilar_contraventado"]["eta"], r["pilar_central_contraventado"]["eta"],
                   r["ancoragem_central_cv"]["eta"],
                   v["peso_total_kg"] + c["peso_total_kg"], nf + nc, r["meta"]["status"], reprov))
print("fach cen | Ø f/c | V f/c | η canto | η cen.mont | η anc.cen | aço kg | baías | status")
for l in linhas:
    print(f"{l[0]:4d} {l[1]:3d} | {l[2]:.0f}/{l[3]:.0f} | {l[4]:.0f}/{l[5]:.0f} | {l[6]:.2f} | "
          f"{l[7]:.2f} | {l[8]:.2f} | {l[9]:.0f} | {l[10]} | {l[11]} {l[12][:4]}")
