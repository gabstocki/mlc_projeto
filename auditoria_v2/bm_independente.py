# -*- coding: utf-8 -*-
"""
BENCHMARK INDEPENDENTE — nenhuma funcao do repositorio auditado e usada no
calculo de REFERENCIA. Tudo reconstruido da formulacao normativa/matematica.
O repositorio so e importado para LER o resultado a comparar.
"""
import math
import numpy as np

# ============ DADOS DE PROJETO (lidos de main.py, tratados como entrada) ======
L, h0, ALPHA, B = 20.25, 1.00, 10.0, 0.32
V0, S1, S3, CAT, CLASSE = 45.0, 1.0, 1.0, "IV", "B"
H_PD, L2, N_TRAMOS = 7.0, 40.5, 2
LT, S_TERCA = 5.75, 2.53
BT, HT = 0.20, 0.58
G_TELHA, G_INST = 0.10, 0.10
Q_AREA = 0.40
L_COMP, B_COB = 46.0, 40.5
B_PIL, H_PIL, N_PIL_LINHA, N_LINHAS = 0.32, 0.27, 9, 3

tan_a = math.tan(math.radians(ALPHA))
h_ap = h0 + (L/2)*tan_a
RHO_MEAN, RHO_K = 420.0, 385.0
E0_MEAN, E0_05, G_MEAN = 11500e6, 9600e6, 650e6
FM_K, FT0_K, FC0_K, FV_K, FT90_K, FC90_K = 24e6, 19.2e6, 24e6, 3.5e6, 0.5e6, 2.5e6
GAMMA_M, GAMMA_M_LIG = 1.25, 1.30
KMOD = {"permanente":0.50, "longa":0.55, "media":0.65, "curta":0.70, "instantanea":0.90}  # CS3

def ok(nome, ref, soft, tol=1e-3, unid=""):
    if soft is None:
        print(f"  [SKIP] {nome}"); return
    d = abs(ref-soft)/max(abs(ref),1e-30)
    flag = "OK " if d <= tol else "XX "
    print(f"  [{flag}] {nome:<42} ref={ref:>12.5f} soft={soft:>12.5f} {unid:<6} dif={d*100:6.3f}%")

print("="*100); print("BM-01  VENTO NBR 6123 — S2, Vk, q"); print("="*100)
bm_, p_, zg = 0.85, 0.125, 420.0
Fr = 0.98
z_ref = H_PD + (h_ap-h0)
S2 = bm_*Fr*(z_ref/10.0)**p_
Vk = V0*S1*S2*S3
q  = 0.613e-3*Vk**2
from mlc_projeto.core.wind import ParametrosVento, calcular_vento, coeficientes_tabela10, forca_vento_paralelo_cumeeira, forca_vento_pilar_90
pv = ParametrosVento(V0=45.0,S1=1.0,categoria="IV",classe="B",S3=1.0,L=L,
                     H1=h_ap-h0,h=H_PD,dist_portico=LT,l2=L2,n_tramos=N_TRAMOS,
                     obstrucoes_sob_cobertura=True)
ok("z_ref (m)", z_ref, pv.z_ref, unid="m")
ok("S2", S2, pv.S2)
ok("Vk (m/s)", Vk, pv.Vk, unid="m/s")
ok("q (kN/m2)", q, pv.q, unid="kN/m2")
beta = math.degrees(math.atan((h_ap-h0)/(L/2)))
ok("beta (graus)", beta, pv.beta_deg, unid="deg")

print(); print("="*100); print("BM-02  PESO PROPRIO g_k (EN 1991-1-1 4.1)"); print("="*100)
gamma_g = RHO_MEAN*9.81/1000.0
V_viga  = B*(h0+h_ap)/2.0*L                      # integral exata de A(x) (h linear por metade)
g_mlc   = V_viga*gamma_g/L/LT
g_terc  = gamma_g*(BT*HT)/S_TERCA
g_k     = g_mlc+g_terc+G_TELHA+G_INST
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads import peso_proprio_gk, carregamentos_com_vento
geo = GeometriaViga(L=L,h0=h0,alpha_deg=ALPHA,b=B)
mat_l = GlulamMaterial(classe="GL24h",classe_servico=3,duracao="longa")
gs = peso_proprio_gk(geo,mat_l,L_t=LT,b_terca=BT,h_terca=HT,s_terca=S_TERCA,
                     g_telha_kNm2=G_TELHA,g_instalacoes_kNm2=G_INST)
ok("gamma glulam (kN/m3)", gamma_g, gs["gamma_kNm3"], unid="kN/m3")
ok("V_viga (m3)", V_viga, gs["V_viga_m3"], tol=2e-4, unid="m3")
ok("g_MLC (kN/m2)", g_mlc, gs["g_mlc_kNm2"], tol=2e-4)
ok("g_tercas (kN/m2)", g_terc, gs["g_tercas_kNm2"], tol=2e-4)
ok("g_k_viga (kN/m2)", g_k, gs["g_k_viga_kNm2"], tol=2e-4)

load = carregamentos_com_vento(geo=geo,mat=mat_l,g_area=gs["g_k_viga_kNm2"],q_area=Q_AREA,
        L_t=LT,params_vento=pv,b_pilar=B_PIL,h_pilar=H_PIL,n_pilares_linha=N_PIL_LINHA,
        n_linhas_portico=N_LINHAS,L_cob_m=L_COMP,B_cob_m=B_COB,empuxo_desenvolve=False)

print(); print("="*100); print("BM-03  COMBINACOES EN 1990 + ANALISE (biapoiada, H=0)"); print("="*100)
gk_lin, qk_lin = g_k*LT, Q_AREA*LT
q_ELU_Q = 1.35*gk_lin + 1.5*qk_lin
M_Q  = q_ELU_Q*L**2/8.0
R_Q  = q_ELU_Q*L/2.0
theta = math.atan(tan_a/2.0)
N_Q  = R_Q*math.sin(theta); V_Q = R_Q*math.cos(theta)
gov = load.combinacao_ELU_governante()
ok("q_ELU_Q (kN/m)", q_ELU_Q, gov.q_tot, unid="kN/m")
ok("M_max (kN.m)", M_Q, gov.M_max_kNm, unid="kN.m")
ok("R_v (kN)", R_Q, gov.V_max_kN, unid="kN")
ok("N_eixo apoio (kN)", N_Q, gov.N_viga_kN, unid="kN")
ok("V_eixo apoio (kN)", V_Q, gov.V_viga_kN, unid="kN")
print(f"     duracao da governante = {gov.duracao!r}  | nome={gov.nome!r}")

# sucção governante, reconstruida
ce = coeficientes_tabela10(beta)
cpi_sot, cpi_bar = 0.8, -0.3
cand=[]
for (zb,zs) in [("a","b"),("c","d")]:
    for (ce_e,ce_d) in [(ce[zb],ce[zs]),(ce[zs],ce[zb])]:
        for cpi in (cpi_sot,cpi_bar):
            we=(ce_e-cpi)*q*LT; wd=(ce_d-cpi)*q*LT
            qe=0.9*gk_lin+1.5*we; qd=0.9*gk_lin+1.5*wd
            RA=(3*qe+qd)*L/8.0
            cand.append((0.5*(qe+qd),RA,ce_e-cpi,ce_d-cpi))
qsuc = min(cand,key=lambda t:t[0])
c3 = load.combinacoes["ELU_C3"]
ok("q_tot sucção gov (kN/m)", qsuc[0], c3.q_tot, unid="kN/m")
ok("R_A sucção gov (kN)", qsuc[1], -abs(c3.V_max_kN) if c3.V_max_kN>0 else c3.V_max_kN, tol=1e-2, unid="kN")

print(); print("="*100); print("BM-04  EC5 6.1.7 CISALHAMENTO"); print("="*100)
kmod_gov = KMOD[gov.duracao]
fvd = kmod_gov*FV_K/GAMMA_M
Vmax = max(abs(c.V_viga_kN) for c in load.combinacoes_ELU().values())
tau = 1.5*(Vmax*1e3)/(0.67*B*h0)
from mlc_projeto.checks.elu.cisalhamento import verifica_cisalhamento
mat_gov = GlulamMaterial(classe="GL24h",classe_servico=3,duracao=gov.duracao)
rc = verifica_cisalhamento(geo,mat_gov,load)
ok("tau_d (MPa)", tau/1e6, rc["tau_d_MPa"], unid="MPa")
ok("f_v,d (MPa)", fvd/1e6, rc["f_vd_MPa"], unid="MPa")
ok("eta cisalhamento", tau/fvd, rc["eta"])

print(); print("="*100); print("BM-05  EC5 6.4.2 MISULA (borda inclinada)"); print("="*100)
def kma(fmd,fvd_,f90,coef): 
    return 1.0/math.sqrt(1.0+(fmd/(coef*fvd_)*tan_a)**2+(fmd/f90*tan_a**2)**2)
kmod_c = KMOD["curta"]
fmd_c, fvd_c = kmod_c*FM_K/GAMMA_M, kmod_c*FV_K/GAMMA_M
ft90_c, fc90_c = kmod_c*FT90_K/GAMMA_M, kmod_c*FC90_K/GAMMA_M
k_tra = kma(fmd_c,fvd_c,ft90_c,0.75); k_cmp = kma(fmd_c,fvd_c,fc90_c,1.5)
from mlc_projeto.checks.elu.misula import verifica_misula
rm = verifica_misula(geo,mat_gov,load)
ok("k_m,alpha tracao (curta)", k_tra, rm["k_m_alpha_tracao"])
ok("k_m,alpha compressao (curta)", k_cmp, rm["k_m_alpha_compressao"])

print(); print("="*100); print("BM-06  EC5 6.4.3 APICE (duplo-bisel)"); print("="*100)
k_p = 0.2*tan_a
k_l = 1+1.4*tan_a+5.4*tan_a**2
V_b = B*L*(h_ap-0.25*L*tan_a)
V_ap= min(B*h_ap**2*(1-0.25*tan_a), 2*V_b/3)
k_vol = min((0.01/V_ap)**0.2,1.0)
M_ap = abs(gov.M_cumeeira_kNm)*1e3
sig_t90 = k_p*6*M_ap/(B*h_ap**2)
ft90_d = kmod_gov*FT90_K/GAMMA_M
eta_t90 = sig_t90/(1.4*k_vol*ft90_d)
sig_map = k_l*6*M_ap/(B*h_ap**2)
eta_map = sig_map/(kmod_gov*FM_K/GAMMA_M)
from mlc_projeto.checks.elu.cumeeira import verifica_cumeeira
rcu = verifica_cumeeira(geo,mat_gov,load)
ok("k_p",k_p,rcu["k_p"]); ok("k_l",k_l,rcu["k_l"])
ok("V_b (m3)",V_b,rcu["V_b_m3"],tol=2e-4); ok("V apice (m3)",V_ap,rcu["V_m3"],tol=2e-4)
ok("k_vol",k_vol,rcu["k_vol"],tol=2e-4)
ok("sigma_t90,d (MPa)",sig_t90/1e6,rcu["sigma_t90d_MPa"],tol=2e-3)
ok("eta t90",eta_t90,rcu["eta_t90"],tol=2e-3)
ok("eta flexao apice",eta_map,rcu["eta_flexao_ap"],tol=2e-3)

print(); print("="*100); print("BM-07  EC5 6.3.3 FLAMBAGEM LATERAL"); print("="*100)
l_ef = 0.9*S_TERCA
sig_crit = 0.78*B**2*E0_05/(h_ap*l_ef)
lam = math.sqrt(FM_K/sig_crit)
kcrit = 1.0 if lam<=0.75 else (1.56-0.75*lam if lam<=1.4 else 1/lam**2)
W = B*h_ap**2/6
sig_m = (abs(gov.M_max_kNm)*1e3)/W
from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral
rf = verifica_flambagem_lateral(geo,mat_gov,load,l_1=S_TERCA)
ok("sigma_m,crit (MPa)",sig_crit/1e6,rf["sigma_crit_MPa"] if "sigma_crit_MPa" in rf else None,unid="MPa")
ok("lambda_rel,m",lam,rf["lambda_rel_m"])
ok("k_crit",kcrit,rf["k_crit"])
ok("eta LTB",sig_m/(kcrit*kmod_gov*FM_K/GAMMA_M),rf["eta"],tol=2e-3)

print(); print("="*100); print("BM-09  EC5 6.1.5 APOIO (compressao perpendicular)"); print("="*100)
L_AP=0.90
sig90 = (abs(gov.V_max_kN)*1e3)/(B*L_AP)
fc90d = kmod_gov*FC90_K/GAMMA_M
from mlc_projeto.checks.elu.apoio import verifica_apoio
ra = verifica_apoio(geo,mat_gov,load,l_ap=L_AP)
ok("sigma_c90,d (MPa)",sig90/1e6,ra["sigma_c90d_MPa"],unid="MPa")
ok("eta c90",sig90/fc90d,ra["eta_c90"],tol=2e-3)

print(); print("="*100); print("BM-11  VENTO theta=0 — atrito 7.2.2 vs limite fisico"); print("="*100)
f0 = forca_vento_paralelo_cumeeira(pv,b_pilar=B_PIL,h_pilar=H_PIL,
        n_pilares_linha=N_PIL_LINHA,n_linhas_portico=N_LINHAS,L_cob_m=L_COMP,B_cob_m=B_COB)
A_planta = L_COMP*B_COB
F_fric_05  = 0.5*q*A_planta
F_fric_005 = 0.05*q*A_planta
A_frontal_cobertura = B_COB*(h0+h_ap)/2.0     # borda da cobertura vista pelo vento theta=0
F_drag_bloqueio_total = q*1.2*A_frontal_cobertura
print(f"     q = {q:.4f} kN/m2 | A_planta = {A_planta:.1f} m2")
print(f"     Ft com 0,50 (implementado) = {F_fric_05:8.1f} kN   <- software: {f0['F_friccao_kN']:.1f} kN")
print(f"     Ft com 0,05 (hipotese)     = {F_fric_005:8.1f} kN")
print(f"     LIMITE FISICO: arrasto de bloqueio TOTAL da cobertura")
print(f"        A_frontal = {A_frontal_cobertura:.1f} m2, Cd=1,2 -> F = {F_drag_bloqueio_total:8.1f} kN")
print(f"     razao Ft(0,50)/F_bloqueio = {F_fric_05/F_drag_bloqueio_total:.2f}x  (fisicamente impossivel se >1)")
print(f"     EN 1991-1-4 Tab.7.10: c_fr = 0,01 / 0,02 / 0,04  -> 0,50 e {0.5/0.04:.0f}x o maior valor do EC1")

print(); print("="*100); print("BM-12  COMPONENTE HORIZONTAL DO VENTO NA COBERTURA (theta=90)"); print("="*100)
A_agua = (L/2)/math.cos(math.radians(ALPHA))*LT     # area REAL de uma meia-agua por portico
maxnet=0.0; det=None
for (zb,zs) in [("a","b"),("c","d")]:
    dc = abs(ce[zb]-ce[zs])
    Fh = dc*q*A_agua*math.sin(math.radians(ALPHA))
    if Fh>maxnet: maxnet, det = Fh, (zb,zs,dc)
n_frames = int(round(L_COMP/LT))+1
Fh_d_total = 1.5*maxnet*n_frames
from mlc_projeto.core.wind import forca_vento_pilar_90
w90 = forca_vento_pilar_90(pv,b_pilar=B_PIL,h_pilar=H_PIL)
n_col = n_frames*(N_TRAMOS+1)
H_vento_topo = n_col*1.5*w90["F_pilar_kN"]/2.0
print(f"     zona {det[0]}*/{det[1]}*: |c_pe,bar - c_pe,sot| = {det[2]:.2f}")
print(f"     A de uma meia-agua por portico = {A_agua:.2f} m2 (projecao/cos(alpha))")
print(f"     H_horiz OMITIDO por portico (caract.) = {maxnet:.2f} kN | de calculo = {1.5*maxnet:.2f} kN")
print(f"     n_porticos = {n_frames} -> H_horiz OMITIDO total (calculo) = {Fh_d_total:.1f} kN")
print(f"     H_vento_topo (arrasto nos pilares)         = {H_vento_topo:.1f} kN")
print(f"     RAZAO cobertura/arrasto = {Fh_d_total/H_vento_topo:.2f}x")
# --- Verificacao da CORRECAO de F-01 -----------------------------------------
from mlc_projeto.checks.elu.contraventamento_transversal import demanda_transversal
dem = demanda_transversal(load, pv, H_pilar_m=H_PD, b_pilar=B_PIL, h_pilar=H_PIL,
                          n_frames=n_frames, n_porticos=N_TRAMOS)
print()
print("     CORRECAO F-01 — a componente passou a entrar na demanda transversal:")
ok("H_cob total (kN)", Fh_d_total, dem["H_cob_kN"], tol=2e-3, unid="kN")
ok("H_tr = arrasto + cobertura + nocional", 
   dem["H_vento_topo_kN"]+dem["H_cob_kN"]+dem["H_imp_kN"], dem["H_tr_kN"],
   tol=1e-4, unid="kN")
