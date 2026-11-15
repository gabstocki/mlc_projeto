"""Estudo do pilar bipartido (issue 104): duas lâminas de MLC dos dois lados da viga,
da base até a escora, pilar composto com espaçadores (EN 1995-1-1 Anexo C.3)."""
import io, contextlib, math, json
import mlc_projeto.main as M
from mlc_projeto.core.materials import GlulamMaterial
M.gerar_relatorio = lambda *a, **k: None
with contextlib.redirect_stdout(io.StringIO()):
    r = M._main_impl(rodar_varredura=False, abrir_viz=False)

mat = GlulamMaterial("GL24h", 3, "curta")
f_c0d, f_c0k, E005 = mat.f_c0_d / 1e6, mat.f_c0_k / 1e6, mat.E0_05 / 1e6   # MPa
cvv, cvt = r["contraventamento_vertical"], r["contraventamento_transversal"]
pcv = r["pilar_contraventado"]
R = pcv["N_comp_kN"] - pcv["download_total_kN"]          # reação de gravidade (pilar lateral)
M_v0 = float(r.get("pilar_vento_0", {}).get("M_d_kNm", 0.0))
b_v = M.GEO_PARAMS["b"] * 1000
h0 = M.GEO_PARAMS["h0"] * 1000
H_mad = M.H_PILAR_MAD * 1000            # base da madeira → apoio da viga
L_y = H_mad + h0                        # até a escora (nó), direção da fachada
L_x = H_mad                             # no plano do pórtico, travado pela viga
FOLGA = 10.0
ETA_C1 = 3.5                            # Tab. C.1, espaçadores parafusados com conectores, longa duração (conservador)
L1_PACK = 1500.0                        # espaçamento dos espaçadores (≥ 3 vãos em 7,7 m)

def k_c(lam):
    lr = lam / math.pi * math.sqrt(f_c0k / E005)
    k = 0.5 * (1 + 0.1 * (lr - 0.3) + lr ** 2)
    return min(1.0, 1 / (k + math.sqrt(k * k - lr * lr)))

# diagonal com o nó no topo da lâmina, no nível da escora
def diag(y_no):
    dz = cvv["H_col_m"] * 1000 + h0 - 100
    dy = cvv["b_baia_m"] * 1000 - y_no
    return cvv["V_painel_kN"] * dz / dy

def caso(nome, R_grav, extra_centrado, bl, h):
    a = b_v + 2 * FOLGA                         # distância livre entre lâminas
    y_l = a / 2 + bl / 2                        # eixo de cada lâmina
    D = diag(y_l + bl / 2)                      # nó na face externa da lâmina
    A = bl * h
    # lâmina do lado do nó: metade da gravidade + D + metade do que chega centrado
    # + parcela axial do momento de vento θ=0° no plano da fachada
    N = R_grav / 2 + D + extra_centrado / 2 + M_v0 * 1e3 / (2 * y_l)
    # x (plano do pórtico): lâmina isolada, l = H_mad (viga trava no apoio)
    lam_x = L_x / (h / math.sqrt(12))
    # y (fachada): composto, λ_ef = √(λ² + η·n/2·λ1²)  (C.10–C.12)
    I_tot = 2 * (h * bl ** 3 / 12 + A * y_l ** 2)
    lam = L_y / math.sqrt(I_tot / (2 * A))
    lam1 = max(30.0, math.sqrt(12) * L1_PACK / bl)
    lam_ef = math.sqrt(lam ** 2 + ETA_C1 * 2 / 2 * lam1 ** 2)
    kc = min(k_c(lam_x), k_c(lam_ef))
    eta = N * 1e3 / A / (kc * f_c0d)
    return dict(pilar=nome, lamina=f"{bl/1000:.2f}x{h/1000:.2f}", largura_total=round((a + 2 * bl) / 1000, 2),
                a_max_ok=a <= 3 * bl, D=round(D, 1), N_lamina=round(N, 1), lam_x=round(lam_x),
                lam_ef=round(lam_ef), k_c=round(kc, 3), eta=round(eta, 3),
                area_m2=round(2 * A / 1e6, 4))

out = []
for nome, Rg, ex in (("canto", R, float(cvt["N_uplift_kN"])), ("lateral montante", R, 0.0),
                     ("central montante", 2 * R, 0.0)):
    for bl in (120.0, 140.0, 160.0):
        for h in (270.0, 320.0):
            out.append(caso(nome, Rg, ex, bl, h))
for o in out:
    print(json.dumps(o, ensure_ascii=False))
print(json.dumps({"R": round(R, 1), "M_v0": M_v0, "L_y": L_y, "L_x": L_x}))
