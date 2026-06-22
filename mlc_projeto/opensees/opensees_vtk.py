import pyvista as pv, numpy as np, math, os

try:
    import openseespy.opensees as ops
    OPENSEES_OK=True
except: OPENSEES_OK=False

# ── Parâmetros ────────────────────────────────────────────────
L=20.25; H_PIL=7.0; h0=0.60; h_ap=1.397
ALPHA=math.radians(4.5); B_V=0.26; B_PIL=0.20; H_PIL_SEC=0.20
E=11.5e6; F_MD=17.28
N_V=40; N_PORT=9; DIST=5.75; N_X=2; AMP=200
B_T=0.20; H_T=0.58; S_TERCA=2.53; L_T=5.75; N_T=20
W_T=B_T*H_T**2/6; A_T=B_T*H_T; I_T=B_T*H_T**3/12
COMBOS={"ELU_C2":9.6634,"ELS_S1":6.2660,"ELS_S3":4.3125,"G_only":3.0187}
UP = np.array([0.0, 0.0, 1.0])  # vetor vertical global

def z_int(x): xs=x if x<=L/2 else L-x; return H_PIL+xs*math.tan(ALPHA)
def h_x(x):   xs=x if x<=L/2 else L-x; return h0+xs*math.tan(ALPHA)

def posicoes_tercas():
    n=round((L/2)/S_TERCA)
    xh=[i*(L/2)/n for i in range(n+1)]
    return sorted(set(xh+[L-x for x in xh]+[0.0,L]))

def M_viga(x,Rv,H,q):
    xs=x if x<=L/2 else L-x
    return Rv*xs-H*xs*math.tan(ALPHA)-q*xs**2/2

def V_viga(x,Rv,H,q):
    if x<=L/2: return Rv-H*math.tan(ALPHA)-q*x
    else:      return -(Rv-H*math.tan(ALPHA)-q*(L-x))

def N_viga(x,Rv,H,q):
    xs=x if x<=L/2 else L-x
    return H*math.cos(ALPHA)+Rv*math.sin(ALPHA)-q*xs*math.sin(ALPHA)

def sigma_viga(x,Rv,H,q):
    Mx=M_viga(x,Rv,H,q); Nx=N_viga(x,Rv,H,q)
    hx=h_x(x); Wx=B_V*hx**2/6; Ax=B_V*hx
    return (abs(Mx)/Wx+abs(Nx)/Ax)*1e-3

def analisar_viga(q):
    ops.wipe(); ops.model('basic','-ndm',2,'-ndf',3)
    xn=[i*(L/2)/N_V for i in range(N_V+1)]
    for i,x in enumerate(xn): ops.node(i+1,x,z_int(x))
    ops.fix(1,1,1,0); ops.fix(N_V+1,1,0,0)
    ops.geomTransf('Linear',1)
    for i in range(N_V):
        xm=(xn[i]+xn[i+1])/2; hm=h_x(xm)
        ops.element('elasticBeamColumn',i+1,i+1,i+2,B_V*hm,E,B_V*hm**3/12,1)
    ops.timeSeries('Linear',1); ops.pattern('Plain',1,1)
    F=q*(L/2)/N_V/2
    for i in range(N_V): ops.load(i+1,0,-F,0); ops.load(i+2,0,-F,0)
    ops.system('BandGeneral'); ops.numberer('RCM'); ops.constraints('Plain')
    ops.integrator('LoadControl',1.0); ops.algorithm('Linear'); ops.analysis('Static')
    if ops.analyze(1)!=0: ops.wipe(); return None
    ops.reactions()
    Ry=ops.nodeReaction(1,2); H=ops.nodeReaction(1,1)
    ux_h=[ops.nodeDisp(i+1,1) for i in range(N_V+1)]
    uz_h=[ops.nodeDisp(i+1,2) for i in range(N_V+1)]
    ops.wipe()
    xfull=xn+[L-x for x in xn[-2::-1]]
    ux=ux_h+[u for u in ux_h[-2::-1]]
    uz=uz_h+[u for u in uz_h[-2::-1]]
    return dict(Ry=Ry,H=H,xfull=xfull,ux=ux,uz=uz)

def analisar_terca(q_t):
    ops.wipe(); ops.model('basic','-ndm',2,'-ndf',3)
    for i in range(N_T+1): ops.node(i+1,i*L_T/N_T,0.0)
    ops.fix(1,1,1,0); ops.fix(N_T+1,0,1,0)
    ops.geomTransf('Linear',1)
    for i in range(N_T):
        ops.element('elasticBeamColumn',i+1,i+1,i+2,A_T,E,I_T,1)
    ops.timeSeries('Linear',1); ops.pattern('Plain',1,1)
    F=q_t*L_T/N_T/2
    for i in range(N_T): ops.load(i+1,0,-F,0); ops.load(i+2,0,-F,0)
    ops.system('BandGeneral'); ops.numberer('RCM'); ops.constraints('Plain')
    ops.integrator('LoadControl',1.0); ops.algorithm('Linear'); ops.analysis('Static')
    if ops.analyze(1)!=0: ops.wipe(); return None
    uz=[ops.nodeDisp(i+1,2) for i in range(N_T+1)]
    ops.wipe()
    yn=[i*L_T/N_T for i in range(N_T+1)]
    M_c=[q_t*(yn[i]+yn[i+1])/2*(L_T-(yn[i]+yn[i+1])/2)/2 for i in range(N_T)]
    V_c=[q_t*(L_T/2-(yn[i]+yn[i+1])/2) for i in range(N_T)]
    s_c=[abs(M_c[i])/W_T*1e-3 for i in range(N_T)]
    return dict(yn=yn,uz=uz,M_c=M_c,V_c=V_c,sig_c=s_c,
                eta_c=[s/F_MD for s in s_c])

# ── Núcleo: extrusão de seção retangular em hexaedro ─────────
def hex_nos(p_i,p_j,b,h_i,h_j,up=UP):
    """
    Gera 8 nós do hexaedro para um elemento barra.
    Ordem VTK_HEXAHEDRON: 0-3 face i, 4-7 face j.
    """
    p_i=np.array(p_i,dtype=float); p_j=np.array(p_j,dtype=float)
    ex=(p_j-p_i); Le=np.linalg.norm(ex)
    if Le<1e-10: return None
    ex=ex/Le
    ez=up-np.dot(up,ex)*ex
    if np.linalg.norm(ez)<1e-10:
        ez=np.array([0,1,0])-np.dot(np.array([0,1,0]),ex)*ex
    ez=ez/np.linalg.norm(ez)
    ey=np.cross(ez,ex); ey=ey/np.linalg.norm(ey)

    def face(p,h):
        return [p-ey*(b/2)-ez*(h/2),
                p+ey*(b/2)-ez*(h/2),
                p+ey*(b/2)+ez*(h/2),
                p-ey*(b/2)+ez*(h/2)]

    return np.array(face(p_i,h_i)+face(p_j,h_j))

def construir_malha_hex(rv,rt,q):
    xfull=rv['xfull']; Ry=rv['Ry']; H=rv['H']
    n_nos_v=len(xfull); n_elem_v=n_nos_v-1
    x_t=posicoes_tercas(); n_elem_t=N_T

    all_pts=[]; inc=[]; tipo=[]
    M_c=[]; V_c=[]; N_c=[]; sig_c=[]; eta_c=[]

    def add_hex(p_i,p_j,b,h_i,h_j, M,V,N,sig,eta, up=UP):
        """Adiciona hexaedro à malha."""
        nos=hex_nos(p_i,p_j,b,h_i,h_j,up)
        if nos is None: return
        base=len(all_pts)
        for n in nos: all_pts.append(n)
        # VTK_HEXAHEDRON = 12
        inc.append([8]+list(range(base,base+8)))
        tipo.append(12)
        M_c.append(M); V_c.append(V); N_c.append(N)
        sig_c.append(sig); eta_c.append(eta)

    # ── Vigas ─────────────────────────────────────────────────
    for ix in range(N_X):
        x_off=ix*L
        for iy in range(N_PORT):
            y=iy*DIST
            for i in range(n_elem_v):
                xi=xfull[i]; xj=xfull[i+1]
                xm=(xi+xj)/2
                p_i=[x_off+xi, y, z_int(xi)]
                p_j=[x_off+xj, y, z_int(xj)]
                hi=h_x(xi); hj=h_x(xj)
                M=M_viga(xm,Ry,H,q)
                V=V_viga(xm,Ry,H,q)
                Nf=N_viga(xm,Ry,H,q)
                sm=sigma_viga(xm,Ry,H,q)
                add_hex(p_i,p_j,B_V,hi,hj,M,V,Nf,sm,sm/F_MD)

    # ── Pilares ───────────────────────────────────────────────
    # Pilar: seção quadrada 0.20×0.20
    # UP local do pilar = eixo X do pórtico (perpendicular ao pilar vertical)
    up_pil=np.array([1.0,0.0,0.0])
    for ix in range(N_X):
        x_off=ix*L
        for iy in range(N_PORT):
            y=iy*DIST
            # Pilar esquerdo
            p_base=[x_off+0.0, y, 0.0]
            p_topo=[x_off+0.0, y, H_PIL]
            Np=abs(Ry); sp=Np/(B_PIL**2)*1e-3
            add_hex(p_base,p_topo,B_PIL,B_PIL,B_PIL,
                    0.0,abs(H),Np,sp,sp/F_MD, up=up_pil)
            # Pilar direito
            p_base=[x_off+L, y, 0.0]
            p_topo=[x_off+L, y, H_PIL]
            add_hex(p_base,p_topo,B_PIL,B_PIL,B_PIL,
                    0.0,abs(H),Np,sp,sp/F_MD, up=up_pil)

    # ── Terças ────────────────────────────────────────────────
    # UP local da terça = vertical global Z
    for ix in range(N_X):
        x_off=ix*L
        for iy in range(N_PORT-1):
            y0=iy*DIST
            for it,xt_loc in enumerate(x_t):
                xt=x_off+xt_loc; zt=z_int(xt_loc)
                yn=rt['yn']
                for i in range(n_elem_t):
                    p_i=[xt, y0+yn[i],   zt]
                    p_j=[xt, y0+yn[i+1], zt]
                    M_c_i=rt['M_c'][i]; V_c_i=rt['V_c'][i]
                    s_c_i=rt['sig_c'][i]; e_c_i=rt['eta_c'][i]
                    add_hex(p_i,p_j,B_T,H_T,H_T,
                            M_c_i,V_c_i,0.0,s_c_i,e_c_i)

    # ── Montar malha pyvista ──────────────────────────────────
    coordenadasNos=np.array(all_pts,dtype=float)
    incidenciaVTK=np.array(inc,dtype=int)
    tipoCelulaVTK=np.array(tipo,dtype=int)

    malha=pv.UnstructuredGrid(incidenciaVTK,tipoCelulaVTK,coordenadasNos)
    malha.cell_data['M_kNm']    =np.array(M_c,  dtype=float)
    malha.cell_data['V_kN']     =np.array(V_c,  dtype=float)
    malha.cell_data['N_kN']     =np.array(N_c,  dtype=float)
    malha.cell_data['sigma_MPa']=np.array(sig_c,dtype=float)
    malha.cell_data['eta_M']    =np.array(eta_c,dtype=float)
    return malha

# ── Pipeline ──────────────────────────────────────────────────
os.makedirs("/output/vtk_hex",exist_ok=True)
for nome,q in COMBOS.items():
    print(f"  [{nome}] q={q:.4f} ... ",end="",flush=True)
    rv=analisar_viga(q)
    if not rv: print("FALHOU"); continue
    rt=analisar_terca((q/L_T)*S_TERCA)
    if not rt: print("FALHOU"); continue
    malha=construir_malha_hex(rv,rt,q)
    arq=f"/output/vtk_hex/portico_{nome}.vtk"
    malha.save(arq)
    eta_max=max(abs(malha.cell_data['eta_M']))
    print(f"OK → {os.path.getsize(arq)//1024} KB | "
          f"{malha.n_points} pts {malha.n_cells} cells | "
          f"eta_max={eta_max:.4f}")