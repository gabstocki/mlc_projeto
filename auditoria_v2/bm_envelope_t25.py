# -*- coding: utf-8 -*-
"""BM-14 — ENVELOPE REAL sobre TODAS as combinacoes ELU vs a combinacao unica
que o software escolhe (max|M| entre as de sentido gravitico)."""
import math, numpy as np
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento
from mlc_projeto.core.loads import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.checks.elu.cumeeira import verifica_cumeeira
from mlc_projeto.checks.elu.apoio import verifica_apoio
from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral

L,h0,AL,B = 20.25,1.00,10.0,0.32
geo = GeometriaViga(L=L,h0=h0,alpha_deg=AL,b=B)
matm= GlulamMaterial(classe="GL24h",classe_servico=3,duracao="media")
pv  = ParametrosVento(V0=45.0,S1=1.0,categoria="IV",classe="B",S3=1.0,L=L,
        H1=geo.h_ap-geo.h0,h=7.0,dist_portico=5.75,l2=13.0,n_tramos=1,
        obstrucoes_sob_cobertura=False)
gs  = peso_proprio_gk(geo,matm,L_t=5.75,b_terca=.20,h_terca=.58,s_terca=2.53,
                      g_telha_kNm2=.10,g_instalacoes_kNm2=.10)
load= carregamentos_com_vento(geo=geo,mat=matm,g_area=gs["g_k_viga_kNm2"],q_area=0.40,
        L_t=5.75,params_vento=pv,b_pilar=.32,h_pilar=.27,n_pilares_linha=9,
        n_linhas_portico=3,L_cob_m=46.0,B_cob_m=40.5,empuxo_desenvolve=False)

FM,FT90,FV,FC90 = 24e6,0.5e6,3.5e6,2.5e6
KMOD={"permanente":.50,"longa":.55,"media":.65,"curta":.70,"instantanea":.90}
GM=1.25
tan_a=math.tan(math.radians(AL)); h_ap=geo.h_ap
k_p=0.2*tan_a; k_l=1+1.4*tan_a+5.4*tan_a**2
V_b=B*L*(h_ap-0.25*L*tan_a); V_ap=min(B*h_ap**2*(1-0.25*tan_a),2*V_b/3)
k_vol=min((0.01/V_ap)**0.2,1.0)
l_ef=0.9*2.53; sig_crit=0.78*B**2*9600e6/(h_ap*l_ef)
lam=math.sqrt(FM/sig_crit); kcrit=1.0 if lam<=.75 else (1.56-.75*lam if lam<=1.4 else 1/lam**2)
W_ap=B*h_ap**2/6; L_AP=0.90

rows=[]
for nome,c in load.combinacoes_ELU().items():
    if nome.startswith("ELU_C"):   # aliases: nao sao combinacoes fisicas novas
        continue
    km=KMOD[c.duracao]
    e_t90 = (k_p*6*abs(c.M_cumeeira_kNm)*1e3/(B*h_ap**2))/(1.4*k_vol*km*FT90/GM)
    e_ltb = (abs(c.M_max_kNm)*1e3/W_ap)/(kcrit*km*FM/GM)
    e_c90 = (abs(c.V_max_kN)*1e3/(B*L_AP))/(km*FC90/GM)
    e_cis = (1.5*abs(c.V_viga_kN)*1e3/(0.67*B*h0))/(km*FV/GM)
    F_lig = math.hypot(c.N_viga_kN,c.V_viga_kN)
    rows.append((nome,c.duracao,c.q_tot,c.M_max_kNm,c.M_cumeeira_kNm,c.V_max_kN,
                 e_t90,e_ltb,e_c90,e_cis,F_lig))

gov = load.combinacao_ELU_governante()
matm = GlulamMaterial(classe="GL24h",classe_servico=3,duracao=gov.duracao)  # como main.py sincroniza
print(f"Combinacao escolhida pelo software (max|M| com q_tot>0): {gov.descricao[:50]!r} dur={gov.duracao}")
print()
hdr=f"{'combinacao':<28}{'dur':<6}{'q_tot':>8}{'M_max':>9}{'M_cum':>9}{'R_v':>8}{'et90':>8}{'eLTB':>8}{'ec90':>8}{'ecis':>8}{'F_lig':>8}"
print(hdr); print("-"*len(hdr))
for r in sorted(rows,key=lambda r:-r[6]):
    print(f"{r[0]:<28}{r[1]:<6}{r[2]:>8.2f}{r[3]:>9.1f}{r[4]:>9.1f}{r[5]:>8.1f}"
          f"{r[6]:>8.4f}{r[7]:>8.4f}{r[8]:>8.4f}{r[9]:>8.4f}{r[10]:>8.1f}")
print("-"*len(hdr))
env = {k: max(r[i] for r in rows) for i,k in ((6,"t90"),(7,"LTB"),(8,"c90"),(9,"cis"),(10,"F_lig"))}
soft = {"t90": verifica_cumeeira(geo,matm,load)["eta"],
        "LTB": verifica_flambagem_lateral(geo,matm,load,l_1=2.53)["eta"],
        "c90": verifica_apoio(geo,matm,load,l_ap=L_AP)["eta_c90"],
        "cis": None, "F_lig": math.hypot(load.N_max_ELU(),load.V_viga_ELU())}
for k in ("t90","LTB","c90","F_lig"):
    s=soft[k]
    if s is None: continue
    print(f"  ENVELOPE {k:<6} = {env[k]:8.4f}   |  SOFTWARE = {s:8.4f}   "
          f"{'>>> SUBESTIMA %.1f%%' % ((env[k]/s-1)*100) if env[k]>s*1.0005 else '(coincide)'}")
