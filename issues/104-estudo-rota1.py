"""Estudo da rota 1 da issue 104: nó do painel CV-V no nível da escora (terça)."""
import io, contextlib, math, json
import mlc_projeto.main as M
from mlc_projeto.connections.oblongo_L1 import ALPHA_PERP, U_MONTAGEM, U_SERVICO
from mlc_projeto.connections.ligacao_diagonal import dimensionar_ligacao_diagonal
M.gerar_relatorio = lambda *a, **k: None
with contextlib.redirect_stdout(io.StringIO()):
    r = M._main_impl(rodar_varredura=False, abrir_viz=False)

cvv = r["contraventamento_vertical"]
E_ACO = 210_000.0                       # MPa
E90 = 300.0                             # MPa, GL24h E90,g,mean (EN 14080)
h0 = M.GEO_PARAMS["h0"] * 1000          # mm
H = cvv["H_col_m"] * 1000               # altura atual do painel (base → topo do pilar)
b_baia = cvv["b_baia_m"] * 1000
V = cvv["V_painel_kN"]
d = cvv["d_mm"]; A = math.pi * d**2 / 4
NtRd = cvv["N_t_Rd_kN"]
lim = H / 300.0                          # limite atual de deslocamento (H/300)

def painel(dy, dz):
    L = math.hypot(dy, dz); cb, sb = dy / L, dz / L
    N = V / cb; Vv = N * sb
    k_ax = E_ACO * A / L / 1e3          # kN/mm
    return dict(L=L, beta=math.degrees(math.atan2(dz, dy)), N=N, Vv=Vv, k_ax=k_ax,
                C_h=k_ax * cb**2, K_v=k_ax * sb**2, tan=dz / dy)

atual = painel(b_baia, H)
# rota 1: nó sob a terça, ao lado da face da viga (y = b/2 + 90 mm), 100 mm abaixo do extradorso
y_no = M.GEO_PARAMS["b"] * 1000 / 2 + 90
r1 = painel(b_baia - y_no, H + h0 - 100)

# rigidez vertical da viga ⊥ às fibras entre o apoio da terça (topo) e o contato na chapa de topo
A_top = M.B_TERCA * 1000 * M.GEO_PARAMS["b"] * 1000                 # terça sobre a viga
A_bot = 2 * 145.5 * 330.0                                            # duas faixas × l_ef
flex = h0 / (E90 * (A_bot - A_top)) * math.log(A_bot / A_top)      # mm/N
K_b = 1 / flex / 1e3                                                 # kN/mm

# 1) deslocamento do painel
d_atual = V / atual["C_h"]
dv_no = r1["Vv"] / K_b
d_r1 = V / r1["C_h"] + dv_no * r1["tan"]

# 2) inchamento restringido: viga entre o topo do pilar e a terça
du = U_SERVICO[1] - U_MONTAGEM[0]
dl_livre = ALPHA_PERP * du * h0
K_eq = r1["K_v"] * K_b / (r1["K_v"] + K_b)
F_v = dl_livre * K_eq
dN_umid = F_v / math.sin(math.radians(r1["beta"]))
du2 = U_SERVICO[1] - U_MONTAGEM[1]                     # montagem úmida (17 %)
dN_umid2 = ALPHA_PERP * du2 * h0 * K_eq / math.sin(math.radians(r1["beta"]))

# 3) levantamento da viga (sucção, sem vento longitudinal): a diagonal segura a viga
R_up = abs(r["oblongo_L1"].get("R_up_kN", 100.5)) if isinstance(r.get("oblongo_L1"), dict) else 100.5
dN_up = R_up / math.sin(math.radians(r1["beta"]))

# 4) fendilhamento da terça se a componente vertical entrasse por cavilhas no rasgo inferior
mat = r["terca"].get("mat") if isinstance(r.get("terca"), dict) else None
kmod_g = 0.90 / 1.30                                      # instantânea / γ_M
b_t, h_t = M.B_TERCA * 1000, M.H_TERCA * 1000
h_e = 150.0
F90 = kmod_g * 14 * b_t * math.sqrt(h_e / (1 - h_e / h_t)) / 1e3

# rota 3 / variante: pórtico metálico sobre o topo do pilar → V excêntrico no pilar
e = y_no / 1000
M_exc = r1["Vv"] * e
W_cen = M.H_PILAR * M.B_PILAR**2 / 6
W_can = M.H_PILAR_CANTO * M.B_PILAR_CANTO**2 / 6
sig_cen = M_exc / W_cen / 1e3; sig_can = M_exc / W_can / 1e3

out = dict(
    painel_atual=dict(beta=round(atual["beta"], 1), N=round(atual["N"], 1), Vv=round(atual["Vv"], 1),
                      eta_N=round(atual["N"] / NtRd, 3), delta=round(d_atual, 1), lim=round(lim, 1)),
    rota1=dict(beta=round(r1["beta"], 1), L=round(r1["L"]), N=round(r1["N"], 1), Vv=round(r1["Vv"], 1),
               eta_N=round(r1["N"] / NtRd, 3), K_b=round(K_b, 1), K_rod_v=round(r1["K_v"], 1),
               dv_no=round(dv_no, 1), delta=round(d_r1, 1), delta_so_barra=round(V / r1["C_h"], 1),
               lim=round(lim, 1), lim_8m=round((H + h0) / 300, 1)),
    umidade=dict(du=du, dl_livre=round(dl_livre, 1), K_eq=round(K_eq, 2), F_v=round(F_v, 1),
                 dN=round(dN_umid, 1), N_total=round(r1["N"] + dN_umid, 1), NtRd=round(NtRd, 1),
                 du_montagem_umida=du2, dN_montagem_umida=round(dN_umid2, 1)),
    levantamento=dict(R_up=R_up, dN=round(dN_up, 1), eta=round(dN_up / NtRd, 3),
                      dz=round(R_up / r1["K_v"], 1)),
    fendilhamento_terca=dict(h_e=h_e, F90_Rd=round(F90, 1), Vv=round(r1["Vv"], 1)),
    portico_metalico=dict(e_m=e, M=round(M_exc, 1), sig_central=round(sig_cen, 2),
                          sig_canto=round(sig_can, 2)),
)
print(json.dumps(out, indent=1, ensure_ascii=False))
