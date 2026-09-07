# -*- coding: utf-8 -*-
"""BM-10 (Johansen L1) e BM-13 (alpha_cr global real) — reconstrucao independente."""
import math
print("="*100); print("BM-10  EC5 8.2.3 / 8.5.1.1 — LIGACAO L1 (cavilhas, chapa CENTRAL embutida)"); print("="*100)
d=24.0; rho_k=385.0; fu=400.0; b=320.0; t_chapa=25.0
t1_codigo = b/2.0
t1_real   = (b-t_chapa)/2.0
fh0 = 0.082*(1-0.01*d)*rho_k
My  = 0.3*fu*d**2.6
k90 = 1.35+0.015*d
Vd, Nd = 99.2225, 8.7478
alpha = math.degrees(math.atan2(abs(Vd),abs(Nd)))
fh_a = fh0/(k90*math.sin(math.radians(alpha))**2 + math.cos(math.radians(alpha))**2)
print(f"  f_h,0,k = {fh0:.3f} MPa | M_y,Rk = {My:.0f} N.mm | k90 = {k90:.3f}")
print(f"  angulo forca-fibras alpha = {alpha:.2f} deg  ->  f_h,alpha,k = {fh_a:.3f} MPa  ({(fh_a/fh0-1)*100:+.1f}%)")
def modos_8_11(fh,t1):
    a = fh*t1*d
    bb= fh*t1*d*(math.sqrt(2+4*My/(fh*d*t1**2))-1)
    c = 2.3*math.sqrt(My*fh*d)
    return a,bb,c
def modo_codigo(fh,t1):
    return fh*t1*d, 1.15*math.sqrt(2*My*fh*d), 2.3*math.sqrt(My*fh*d)
for rot,fh,t1 in (("CODIGO   (f_h,0 ; t1=b/2 ; 1,15*sqrt(2 M f d))",fh0,t1_codigo),):
    m=modo_codigo(fh,t1); print(f"  {rot}\n     I={m[0]/1e3:7.2f}  IIIb={m[1]/1e3:7.2f}  IV={m[2]/1e3:7.2f}  -> min={min(m)/1e3:7.2f} kN/plano")
    ref_cod=min(m)
for rot,fh,t1 in (("EC5 8.11 (f_h,0 ; t1=(b-t)/2)",fh0,t1_real),
                  ("EC5 8.11 (f_h,alpha; t1=(b-t)/2)  <-- CORRETO",fh_a,t1_real)):
    m=modos_8_11(fh,t1); print(f"  {rot}\n     (f)={m[0]/1e3:7.2f}  (g)={m[1]/1e3:7.2f}  (h)={m[2]/1e3:7.2f}  -> min={min(m)/1e3:7.2f} kN/plano")
    if "CORRETO" in rot: ref_cor=min(m)
kmod, gM = 0.65, 1.30
n=5
for rot,Fvrk in (("CODIGO",ref_cod),("CORRETO (8.11 + f_h,alpha)",ref_cor)):
    Frd = kmod*2*Fvrk/gM
    R   = n*Frd
    print(f"  {rot:<28}: F_Rd/pino={Frd/1e3:6.2f} kN | R(5 pinos)={R/1e3:7.2f} kN | eta={math.hypot(Vd,Nd)*1e3/R:.4f}")
# --- Verificacao da CORRECAO de F-14 (+F-03) -------------------------------
from mlc_projeto.connections.connections import johansen_chapa_central
t1_cod = (b - d) / 2.0        # o codigo adota t_chapa = d (chapa rigida, t>=d)
soft = johansen_chapa_central(rho_k, d, t1_cod, fu, theta_deg=alpha)
ref = min(modos_8_11(fh_a, t1_cod))
print()
print("     CORRECAO F-14 — modos da chapa CENTRAL (EC5 8.2.3) no software:")
print(f"       ref (independente) = {ref/1e3:7.3f} kN/plano | "
      f"software = {soft['F_v_Rk_N']/1e3:7.3f} kN/plano | "
      f"dif = {abs(ref-soft['F_v_Rk_N'])/ref*100:.4f}%")
print(f"       modo governante = {soft['modo_gov']} | t1 = {soft['t1_mm']} mm | "
      f"F_ax,Rk = {soft['F_ax_Rk_N']} N (cavilha lisa)")
print()
print("  Tabela 8.5 — distancia a_4,t (borda carregada):")
print(f"     EC5: max((2+2*sin(alpha))*d , 3d) = max({(2+2*math.sin(math.radians(alpha)))*d:.1f} , {3*d:.1f}) = {max((2+2*math.sin(math.radians(alpha)))*d,3*d):.1f} mm")
print(f"     codigo: 3d = {3*d:.1f} mm   -> deficit de {(1-3*d/max((2+2*math.sin(math.radians(alpha)))*d,3*d))*100:.1f}%")

print(); print("="*100); print("BM-13  alpha_cr GLOBAL REAL (EN 1993-1-1 5.2.1) — sistema contraventado"); print("="*100)
E=210000.0  # MPa
def Ch(d_mm,H,bbaia):
    A=math.pi*d_mm**2/4.0; Ld=math.hypot(H,bbaia); cb=bbaia/Ld
    return E*A/(Ld*1e3)*cb**2   # kN/m
H_col, b_baia = 7.0, 5.75
n_frames=9; R_v=99.607
N_total = 4.0*R_v*n_frames     # 2 vaos -> 4 apoios equivalentes por portico
print(f"  Carga vertical ELU total do galpao  SUM(N_Ed) = {N_total:.0f} kN")
for rot,dmm,npain in (("LONGITUDINAL (4 paineis, O45)",45.0,4),
                      ("TRANSVERSAL  (2 frontoes, O16 - ANTES de F-01)",16.0,2),
                      ("TRANSVERSAL  (2 frontoes, O24 - DEPOIS de F-01)",24.0,2)):
    K = npain*Ch(dmm,H_col,b_baia)
    acr = K*H_col/N_total
    kII = 1/(1-1/acr) if acr>1 else float("inf")
    print(f"  {rot:<32} K={K:9.0f} kN/m | alpha_cr = K*h/SUM(N) = {acr:7.2f} "
          f"| {'OK (>=10)' if acr>=10 else 'ABAIXO DE 10 -> 2a ordem exigida'} | k_II={kII:.3f}")
