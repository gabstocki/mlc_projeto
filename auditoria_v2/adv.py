# -*- coding: utf-8 -*-
"""Testes adversariais — dominio, sinais, extremos, NaN/inf, monotonicidade."""
import math, warnings
import numpy as np
warnings.filterwarnings("ignore")
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.wind import ParametrosVento, calcular_vento, coeficientes_tabela10, coeficientes_tabela25
from mlc_projeto.core.loads import analisar_biarticulada, carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.checks.elu.cumeeira import verifica_cumeeira, calcular_k_vol
from mlc_projeto.checks.elu.cisalhamento import verifica_cisalhamento
from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral, calcular_k_crit
from mlc_projeto.output.report import extrair_eta_ok, tabela_verificacoes

def t(nome, fn, espera):
    try:
        r = fn(); res = f"retornou {r!r}"
        veredito = "XX FALHA-SILENCIOSA" if espera=="raise" else "OK "
    except Exception as e:
        res = f"{type(e).__name__}: {str(e)[:60]}"
        veredito = "OK " if espera=="raise" else "XX EXCECAO-INESPERADA"
    print(f"  [{veredito}] {nome:<58} {res}")

print("="*104); print("ADV-A  DOMINIO DA GEOMETRIA / MATERIAL"); print("="*104)
t("GeometriaViga(L=0)",            lambda: GeometriaViga(L=0,h0=1,alpha_deg=10,b=.32), "raise")
t("GeometriaViga(b=-0,32)",        lambda: GeometriaViga(L=20,h0=1,alpha_deg=10,b=-.32),"raise")
t("GeometriaViga(alpha=NaN)",      lambda: GeometriaViga(L=20,h0=1,alpha_deg=float('nan'),b=.32),"raise")
t("GeometriaViga(alpha=90)",       lambda: GeometriaViga(L=20,h0=1,alpha_deg=90,b=.32),"raise")
t("GeometriaViga(h0=inf)",         lambda: GeometriaViga(L=20,h0=float('inf'),alpha_deg=10,b=.32),"raise")
t("GlulamMaterial(classe='GL99z')",lambda: GlulamMaterial(classe="GL99z",classe_servico=3),"raise")
t("GlulamMaterial(CS=4)",          lambda: GlulamMaterial(classe="GL24h",classe_servico=4),"raise")
t("GlulamMaterial(duracao='xx')",  lambda: GlulamMaterial(classe="GL24h",classe_servico=3,duracao="xx"),"raise")

print(); print("="*104); print("ADV-B  analisar_biarticulada FORA DO DOMINIO (funcao publica, sem guarda de validacao)"); print("="*104)
t("h0=0 (secao nula no apoio)",
  lambda: round(analisar_biarticulada(q=10,L=20,h0=0.0,h_ap=2.0,alpha_rad=0.2,b=.32,desenvolve_empuxo=True)["H_kN"],3), "raise")
t("b=0",
  lambda: analisar_biarticulada(q=10,L=20,h0=1,h_ap=2,alpha_rad=0.2,b=0.0,desenvolve_empuxo=True)["H_kN"], "raise")
t("q=NaN",
  lambda: analisar_biarticulada(q=float('nan'),L=20,h0=1,h_ap=2,alpha_rad=0.2,b=.32,desenvolve_empuxo=True)["M_max_kNm"],"raise")
t("L negativo",
  lambda: round(analisar_biarticulada(q=10,L=-20,h0=1,h_ap=2,alpha_rad=0.2,b=.32,desenvolve_empuxo=True)["M_max_kNm"],3),"raise")

print(); print("="*104); print("ADV-C  VENTO — dominio das tabelas"); print("="*104)
t("Tab.25 com tg(beta)=0,03 (<0,07)", lambda: coeficientes_tabela25(0.03), "raise")
t("Tab.25 com tg(beta)=0,90 (>0,60)", lambda: coeficientes_tabela25(0.90), "raise")
t("Tab.10 com theta=2 deg (<5)",      lambda: coeficientes_tabela10(2.0), "raise")
t("Tab.10 com theta=60 deg (>45)",    lambda: coeficientes_tabela10(60.0),"raise")
t("S2 acima de z_g (z=500, cat IV)",
  lambda: ParametrosVento(categoria="IV",classe="B").S2_em(500.0), "raise")
t("V0 negativo -> q",
  lambda: round(ParametrosVento(V0=-45.0,categoria="IV",classe="B").q,5), "raise")
t("V0 = NaN -> q",
  lambda: ParametrosVento(V0=float('nan'),categoria="IV",classe="B").q, "raise")

print(); print("="*104); print("ADV-D  AGREGACAO DO VEREDITO (report.extrair_eta_ok / tabela_verificacoes)"); print("="*104)
print(f"  extrair_eta_ok({{}})                                     -> {extrair_eta_ok({})}")
print(f"  extrair_eta_ok({{'eta': None}})                          -> {extrair_eta_ok({'eta': None})}")
print(f"  extrair_eta_ok({{'eta': float('nan')}})                  -> {extrair_eta_ok({'eta': float('nan')})}")
print(f"  extrair_eta_ok({{'eta': 'erro'}})                        -> {extrair_eta_ok({'eta':'erro'})}")
print(f"  extrair_eta_ok({{'eta': 3.0, 'ok': True}})               -> {extrair_eta_ok({'eta':3.0,'ok':True})}")
tab = tabela_verificacoes({"cumeeira": {"sem_eta": 1}, "cisalhamento": {"eta": 2.5}})
print(f"  tabela_verificacoes com 'cumeeira' SEM eta -> linhas = {[l['chave'] for l in tab]}")
print("    (a verificacao sem eta desaparece do resumo e do all_ok, sem aviso)")

print(); print("="*104); print("ADV-E  PROPRIEDADES (monotonicidade / proporcionalidade / continuidade)"); print("="*104)
geo = GeometriaViga(L=20.25,h0=1.0,alpha_deg=10.0,b=0.32)
matm = GlulamMaterial(classe="GL24h",classe_servico=3,duracao="media")
pv = ParametrosVento(V0=45.0,S1=1.0,categoria="IV",classe="B",S3=1.0,L=20.25,
                     H1=geo.h_ap-geo.h0,h=7.0,dist_portico=5.75,l2=40.5,n_tramos=2,
                     obstrucoes_sob_cobertura=True)
gs = peso_proprio_gk(geo,matm,L_t=5.75,b_terca=.20,h_terca=.58,s_terca=2.53,
                     g_telha_kNm2=.10,g_instalacoes_kNm2=.10)
def mk(q_area):
    return carregamentos_com_vento(geo=geo,mat=matm,g_area=gs["g_k_viga_kNm2"],q_area=q_area,
        L_t=5.75,params_vento=pv,b_pilar=.32,h_pilar=.27,n_pilares_linha=9,
        n_linhas_portico=3,L_cob_m=46.0,B_cob_m=40.5,empuxo_desenvolve=False)
etas=[]
for qa in (0.40,0.80,1.60,3.20):
    ld=mk(qa); etas.append((qa, verifica_cisalhamento(geo,matm,ld)["eta"],
                                verifica_cumeeira(geo,matm,ld)["eta"]))
print("  q_area  eta_cis   eta_cumeeira   (esperado: monotono crescente)")
for a,b_,c in etas: print(f"   {a:5.2f}  {b_:7.4f}   {c:9.4f}")
mono = all(etas[i][1] < etas[i+1][1] for i in range(len(etas)-1)) and \
       all(etas[i][2] < etas[i+1][2] for i in range(len(etas)-1))
print(f"  monotonicidade: {'OK' if mono else 'XX FALHA'}")
print("  continuidade de k_crit em lambda=0,75 e 1,4:")
for l in (0.7499,0.7501,1.3999,1.4001):
    print(f"     k_crit({l}) = {calcular_k_crit(l):.6f}")
print("  continuidade de k_vol (V -> 0):", f"k_vol(V pequeno) = {calcular_k_vol(0.001,0.02,0.05,10.0):.4f} (deve ser <= 1)")

print(); print("="*104); print("ADV-F  INVERSAO DE EIXOS (b <-> h) — a viga deve PIORAR muito"); print("="*104)
geo_ok_ = GeometriaViga(L=20.25,h0=1.0,alpha_deg=10.0,b=0.32)
ld = mk(0.40)
r1 = verifica_flambagem_lateral(geo_ok_,matm,ld,l_1=46.0)
print(f"  l_1 = 2,53 m  -> k_crit={verifica_flambagem_lateral(geo_ok_,matm,ld,l_1=2.53)['k_crit']:.4f}"
      f"  eta={verifica_flambagem_lateral(geo_ok_,matm,ld,l_1=2.53)['eta']:.4f}")
print(f"  l_1 = 46,0 m  -> k_crit={r1['k_crit']:.4f}  eta={r1['eta']:.4f}   (esperado: k_crit cai, eta sobe)")
