"""BENCHMARK INDEPENDENTE — flecha de flexao + cisalhamento (Timoshenko).
NAO importa nenhuma funcao do repositorio para o calculo de referencia.
Formulacao pura: viga biapoiada de secao variavel h(x)=h0+x_sim*tan(a),
carga uniforme q. Integracao de Euler-Bernoulli + termo de Timoshenko.
"""
import numpy as np

L, h0, alpha_deg, b = 20.25, 1.00, 10.0, 0.32
E = 11500e6; G = 650e6; ks = 1.2
tan_a = np.tan(np.radians(alpha_deg))

n = 200001
x = np.linspace(0.0, L, n)
x_sim = np.where(x <= L/2, x, L-x)
h = h0 + x_sim*tan_a
I = b*h**3/12.0
A = b*h

def w_timoshenko(q):
    """q em N/m. Retorna (w_total, w_flexao, w_cis) no ponto de |w| max, em m.
    Convencao: para BAIXO positivo."""
    M = 0.5*q*x*(L-x)                     # N.m  (isostatico)
    V = q*(L/2.0 - x)                     # N    (dM/dx analitico)
    # --- Flexao: EI w'' = M  (w para baixo positivo) ---
    kap = M/(E*I)
    th  = np.concatenate(([0.0], np.cumsum(0.5*(kap[1:]+kap[:-1])*np.diff(x))))
    wb  = np.concatenate(([0.0], np.cumsum(0.5*(th[1:]+th[:-1])*np.diff(x))))
    wb -= wb[-1]*x/L
    # --- Cisalhamento: dw_s/dx = +ks*V/(G*A)  (para baixo positivo) ---
    g   = -ks*V/(G*A)   # convencao w"=+M/EI -> descendente NEGATIVO
    ws  = np.concatenate(([0.0], np.cumsum(0.5*(g[1:]+g[:-1])*np.diff(x))))
    ws -= ws[-1]*x/L
    w   = wb+ws
    i   = int(np.argmax(np.abs(w)))
    return w[i], wb[i], ws[i]

# Sanidade: secao CONSTANTE h=h0 -> formulas fechadas
h_c = h0; I_c = b*h_c**3/12; A_c = b*h_c
q_t = 1000.0
I_bak, A_bak = I.copy(), A.copy()
I[:] = I_c; A[:] = A_c
wt, wb_, ws_ = w_timoshenko(q_t)
print("--- Sanidade (secao constante h=1,00 m, q=1 kN/m) ---")
print(f"  w_flexao num = {wb_*1000:.5f} mm | 5qL^4/384EI = {5*q_t*L**4/(384*E*I_c)*1000:.5f} mm")
print(f"  w_cis    num = {ws_*1000:.5f} mm | ks*q*L^2/(8GA) = {ks*q_t*L**2/(8*G*A_c)*1000:.5f} mm")
I[:], A[:] = I_bak, A_bak

gk = 0.8229*5.75*1000.0   # N/m  (peso proprio caracteristico)
qk = 0.40*5.75*1000.0     # N/m

for nome, q in (("G", gk), ("Q", qk), ("G+Q", gk+qk)):
    w, wbb, wss = w_timoshenko(q)
    print(f"{nome:>4}: w_tot={w*1000:8.3f} mm | flexao={wbb*1000:8.3f} | cis={wss*1000:7.3f} "
          f"({abs(wss)/abs(w)*100:.1f}%)")

wG,_,_ = w_timoshenko(gk); wQ,_,_ = w_timoshenko(qk)
kdef = 2.0
w_S1 = wG+wQ
w_fin = wG*(1+kdef) + wQ
print()
print(f"REFERENCIA INDEPENDENTE:")
print(f"  w_S1      = {w_S1*1000:.3f} mm | lim L/300 = {L/300*1000:.2f} mm | eta = {w_S1/(L/300):.4f}")
print(f"  w_net_fin = {w_fin*1000:.3f} mm | lim L/250 = {L/250*1000:.2f} mm | eta = {w_fin/(L/250):.4f}")
