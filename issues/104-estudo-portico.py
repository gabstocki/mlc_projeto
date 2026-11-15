"""Estudo da variante 'pórtico metálico' da issue 104 (montantes de aço ao lado da viga,
da chapa de topo até a escora; diagonal CV-V no topo do montante, ao lado da viga)."""
import io, contextlib, math, json
import mlc_projeto.main as M
from mlc_projeto.checks.elu.pilares import verifica_pilar_contraventado
M.gerar_relatorio = lambda *a, **k: None
with contextlib.redirect_stdout(io.StringIO()):
    r = M._main_impl(rodar_varredura=False, abrir_viz=False)

cvv, cvt, cvc = (r["contraventamento_vertical"], r["contraventamento_transversal"],
                 r["contraventamento_vertical_central"])
from mlc_projeto.core.materials import GlulamMaterial
mat = GlulamMaterial("GL24h", 3, "curta")
# mesmos esforços de gravidade do main
load = None
pcv, pcc = r["pilar_contraventado"], r["pilar_central_contraventado"]
Rv_comp = pcv["N_comp_kN"] - pcv["download_total_kN"]
Rv_min = Rv_comp - 0  # placeholder, recalculado abaixo
# reação mínima: N_t = D - Rv_min ⇒ Rv_min = D - N_t (quando N_t > 0)
Rv_min = pcv["download_total_kN"] - pcv["N_tracao_liq_kN"] if pcv["N_tracao_liq_kN"] > 0 else None
M_v0 = float(r.get("pilar_vento_0", {}).get("M_d_kNm", 0.0))
M_vmax = max(M_v0, float(r.get("pilar_vento_90", {}).get("M_d_kNm", 0.0)))
H = M.H_PILAR_MAD

# geometria da diagonal com o nó no topo do montante metálico
h0 = M.GEO_PARAMS["h0"] * 1000
y_no = M.GEO_PARAMS["b"] * 1000 / 2 + 90          # face da viga + 90 mm
dz = cvv["H_col_m"] * 1000 + h0 - 100
dy = cvv["b_baia_m"] * 1000 - y_no
tanb = dz / dy
D_novo = cvv["V_painel_kN"] * tanb                  # componente vertical no nó
e = y_no / 1000
M_exc = D_novo * e

def M_comb(Me, Mv):
    # topo: Me·ξ (ξ = 1 no topo) + vento na face, parabólico (máx. Mv a meia altura)
    return max(Me * x / 100 + Mv * 4 * (x / 100) * (1 - x / 100) for x in range(101))

def caso(nome, b, h, Ngrav, downloads_extra, Me):
    D = [D_novo] + downloads_extra
    Mt = M_comb(Me, M_v0)
    res = verifica_pilar_contraventado(mat=mat, b=b, h=h, H_pilar=H, N_grav_comp_kN=Ngrav,
                                       N_grav_uplift_kN=Ngrav, downloads_kN=D, eixo="z",
                                       M_vento_kNm=Mt)
    return dict(pilar=nome, b=b, h=h, N=round(res["N_comp_kN"], 1), M=round(Mt, 1),
                eta=round(res["eta_comp"], 3))

out = {"D_atual": round(cvv["N_uplift_kN"], 1), "D_novo": round(D_novo, 1), "e_m": e,
       "M_exc": round(M_exc, 1), "M_vento0": round(M_v0, 1), "Rv_comp": round(Rv_comp, 1),
       "atual": {"canto": pcv["eta"], "central": pcc["eta"]}, "linhas": []}
D_tr = float(cvt["N_uplift_kN"])
grids = {
    "canto (P1,P3,P25,P27)": (Rv_comp, [D_tr]),
    "lateral montante (P4,P6,P22,P24)": (Rv_comp, []),
    "central montante (P2,P5,P8,P20,P23,P26)": (2 * Rv_comp, []),
}
for nome, (Ng, extra) in grids.items():
    for b in (0.32, 0.36, 0.40, 0.44, 0.48, 0.52):
        for h in (0.27, 0.32, 0.36, 0.40):
            if h > b + 1e-9 and h != 0.27:
                continue
            out["linhas"].append(caso(nome, b, h, Ng, extra, M_exc))
# referência: os mesmos pilares sem o momento excêntrico (nó no topo do pilar, geometria atual)
ref = []
for nome, (Ng, extra) in grids.items():
    res = verifica_pilar_contraventado(mat=mat, b=0.32, h=0.32 if "canto" in nome else 0.27,
                                       H_pilar=H, N_grav_comp_kN=Ng, N_grav_uplift_kN=Ng,
                                       downloads_kN=[cvv["N_uplift_kN"]] + extra, eixo="z",
                                       M_vento_kNm=M_v0)
    ref.append((nome, round(res["eta_comp"], 3)))
out["ref_sem_exc_eixo_z"] = ref
print(json.dumps(out, indent=0, ensure_ascii=False))
