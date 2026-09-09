"""
checks/elu/contraventamento.py — Integridade estrutural da cobertura.

Objetivo
---------
O contraventamento NÃO é um acessório: é o que torna as terças apoios
laterais válidos da viga principal. Sem ele, a cobertura deixa de cumprir
a função estrutural assumida no LTB (l_ef = 0,9·s).

Cadeia de forças (plano da cobertura)
-------------------------------------
  Viga MLC comprimida (N + M)
       ↓  força de estabilização EC5 §9.2.5
  Terça como BIELA (compressão + flambagem)
       ↓  até baía rígida
  Cruz de St. André (diagonal tracionada, aço)
       ↓
  Pórtico de extremidade → fundação

Verificações (EC5 + EN 1993)
----------------------------
  §9.2.5.2  — apoio intermediário individual (força F_d + rigidez C)
  §9.2.5.3  — sistema de n vigas paralelas (carga q_d, δ ≤ ℓ/500)
  §6.3.2    — terça como biela comprimida
  EN 1993-1-1 §6.2.3 — diagonal de aço à tração
  Rigidez horizontal do painel de cruzes

Acoplamento ao resto do pipeline
--------------------------------
  `restricao_lateral_valida`  → se True, LTB pode usar l_1 = s (terças)
  se False, LTB deve usar l_1 penalizado (vão entre baías rígidas)

Referências
-----------
  EN 1995-1-1:2004 §9.2.5.2, §9.2.5.3, §6.3.2, §6.3.3
  EN 1993-1-1 §6.2.3
  Swedish Wood — Design of timber structures Vol. 2, cap. 12
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


# ── Fatores de modificação EC5 §9.2.5 — Tabela 9.2 ────────────────────────────
# EN 1995-1-1:2004+A1:2008 Tabela 9.2 "Recommended values of modification factors"
# (intervalos; o valor RECOMENDADO é o sublinhado na norma; NA pode alterar):
#   k_s   : 1 a 4     → recomendado 4     (Eq. 9.34, rigidez C)
#   k_f,1 : 50 a 80   → recomendado 50    (Eq. 9.35, F_d madeira maciça)
#   k_f,2 : 80 a 100  → recomendado 80    (Eq. 9.35, F_d MLC/LVL)
#   k_f,3 : 30 a 80   → recomendado 30    (Eq. 9.37, q_d do sistema)
# Adotam-se os valores RECOMENDADOS da norma (nenhum NA em contrário assumido).

K_S   = 4.0    # rigidez do apoio intermediário (Tab. 9.2, recomendado)
K_F1  = 50.0   # força — madeira maciça §9.2.5.2 (não usado aqui)
K_F2  = 80.0   # força — MLC / LVL §9.2.5.2 (Tab. 9.2, recomendado)
K_F3  = 30.0   # carga de sistema §9.2.5.3 (Tab. 9.2, RECOMENDADO=30; era 50)

E_ACO_MPA = 210_000.0   # MPa — aço
GAMMA_M0  = 1.00        # EN 1993-1-1 §6.1

ACO = {
    "S235": {"f_y": 235.0, "f_u": 360.0},
    "S355": {"f_y": 355.0, "f_u": 510.0},
}


# ── Layout ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LayoutContraventamento:
    """Geometria do sistema de contraventamento horizontal."""

    L_comp:       float = 46.0    # m — comprimento do galpão (eixo Y)
    dist_portico: float = 5.75    # m — espaçamento entre pórticos = vão terça
    s_terca:      float = 2.53    # m — espaçamento entre terças (ao longo da viga)
    n_porticos:   int   = 2       # pórticos lado a lado (dois vãos de 20,25 m)
    n_modulos_cv: int   = 2       # baías com cruzes (extremos)
    d_barra_mm:   float = 22.0    # mm — adotado no projeto (main.D_BARRA_CV_MM); issue 15
    aco:          str   = "S235"

    @property
    def n_modulos(self) -> int:
        return max(1, round(self.L_comp / self.dist_portico))

    @property
    def n_vigas_por_linha(self) -> int:
        """Número de vigas principais ao longo do comprimento (por pórtico)."""
        return self.n_modulos + 1

    @property
    def n_vigas(self) -> int:
        """Total de vigas principais a estabilizar."""
        return self.n_vigas_por_linha * self.n_porticos

    @property
    def ell_m(self) -> float:
        """
        Vão do sistema estabilizador ℓ (EC5 §9.2.5.3 Fig. 9.9).
        Distância entre baías rígidas de contraventamento.
        Com só extremos: ℓ = L_comp.

        Nota de projeto: aumentar n_modulos_cv (mais baías com cruzes)
        reduz ℓ e sobe k_ℓ=min(1,√(15/ℓ)), o que **aumenta** a reação
        R_ext = k_ℓ·n·N_d/(2·k_f3) enquanto k_ℓ < 1. Por isso encher
        todas as baías da linha frontal/final **não** é, em geral, a
        solução mais económica para §9.2.5 — preferir extremos +
        diagonal dimensionada (e baía intermediária só se robustez/arquitectura).
        """
        if self.n_modulos_cv <= 1:
            return self.L_comp
        return self.L_comp / (self.n_modulos_cv - 1)

    @property
    def a_restricao_m(self) -> float:
        """Espaçamento entre apoios laterais na viga (= s terças) — §9.2.5.2."""
        return self.s_terca

    @property
    def n_paineis_por_mod(self) -> int:
        """
        Painéis de cruz por módulo extremo.
        Por pórtico: dois painéis junto aos beirais (x≈0 e x≈L);
        × n_porticos.
        """
        return 2 * self.n_porticos

    def diagonal(self) -> dict:
        L = self.dist_portico
        s = self.s_terca
        d = math.sqrt(L**2 + s**2)
        th = math.atan(s / L)
        return {
            "L_panel_m": L,
            "s_terca_m": s,
            "d_diag_m":  round(d, 4),
            "theta_deg": round(math.degrees(th), 2),
            "cos_theta": math.cos(th),
            "sin_theta": math.sin(th),
        }


# ── Força de compressão a estabilizar ─────────────────────────────────────────

def forca_compressao_estabilizar(
    load: Carregamentos,
    geo:  GeometriaViga,
    k_crit: float = 1.0,
) -> dict:
    """
    Força normal média de cálculo N_d a estabilizar — EC5 §9.2.5.

    Combina:
      • compressão axial da análise biarticulada (empuxo)
      • compressão equivalente da flexão na aba comprimida
        N_flex = (1 − k_crit)·M_d / h   (EC5 §9.2.5.2, Swedish Wood 12.1)

    N_d = |N_axial| + N_flex   (sobreposição conservadora; MLC biarticulada)

    Envelope sobre as combinações — resíduo do [F-06]
    -------------------------------------------------
    Lia-se `combinacao_ELU_governante()`, que maximiza |M_max|. Mas o que esta
    função precisa de maximizar é `N_d = |N| + (1−k_crit)·M/h`, e essa medida
    não é monótona em |M|: `h` é a altura NA SEÇÃO de M_max e varia com a
    combinação (uma combinação com M menor mas máximo mais perto do apoio, onde
    h é menor, pode dar N_flex maior), e a parcela axial vem do empuxo, que
    segue outro padrão de carga. Passa a usar-se `envelope_ELU` sobre a própria
    medida — que é o que o EN 1990 §6.4.3.2 pede.
    """
    k_c = max(0.0, min(1.0, float(k_crit)))

    def _N_d(comb) -> float:
        h_c = float(geo.h(comb.x_Mmax_m))
        if h_c <= 0:
            h_c = float(geo.h_ap)
        return (abs(float(comb.N_viga_kN))
                + (1.0 - k_c) * abs(float(comb.M_max_kNm)) / h_c)

    gov, N_d = load.envelope_ELU(_N_d)
    N_ax = abs(float(gov.N_viga_kN))
    M_d  = abs(float(gov.M_max_kNm))
    h    = float(geo.h(gov.x_Mmax_m))
    if h <= 0:
        h = float(geo.h_ap)
    N_flex = (1.0 - k_c) * M_d / h          # kN

    return {
        "N_axial_kN": round(N_ax, 3),
        "N_flex_kN":  round(N_flex, 3),
        "N_d_kN":     round(N_d, 3),
        "M_d_kNm":    round(M_d, 3),
        "h_m":        round(h, 4),
        "k_crit":     round(k_c, 4),
        "comb":       gov.nome,
    }


# ── EC5 §9.2.5.2 — apoio intermediário individual ───────────────────────────────

def verifica_apoio_intermediario(
    N_d_kN: float,
    a_m:    float,
    k_s:    float = K_S,
    k_f2:   float = K_F2,
) -> dict:
    """
    Apoio lateral intermediário de peça comprimida (MLC) — EC5 §9.2.5.2.

        C ≥ k_s · N_d / a
        F_d = N_d / k_f,2     (glulam)

    C em kN/m, F_d em kN, a e N_d em m e kN.
    """
    if a_m <= 0:
        raise ValueError("a (espaçamento entre restrições) deve ser > 0")

    C_min = k_s * N_d_kN / a_m     # kN/m
    F_d   = N_d_kN / k_f2          # kN

    return {
        "a_m":        a_m,
        "k_s":        k_s,
        "k_f2":       k_f2,
        "C_min_kNpm": round(C_min, 3),
        "F_d_kN":     round(F_d, 4),
        "norma":      "EC5 §9.2.5.2",
    }


# ── EC5 §9.2.5.3 — sistema de n vigas ─────────────────────────────────────────

def verifica_sistema_vigas(
    N_d_kN:  float,
    n:       int,
    ell_m:   float,
    k_f3:    float = K_F3,
) -> dict:
    """
    Sistema de n peças paralelas estabilizadas em conjunto — EC5 §9.2.5.3.

        k_ℓ = min(1, √(15/ℓ))
        q_d = k_ℓ · n · N_d / (k_f,3 · ℓ)

        δ_lim = ℓ / 500

    q_d em kN/m; reação por baía extrema (simétrica) R = q_d·ℓ/2.
    """
    if ell_m <= 0:
        raise ValueError("ℓ (vão do sistema estabilizador) deve ser > 0")

    k_ell = min(1.0, math.sqrt(15.0 / ell_m))
    q_d   = k_ell * n * N_d_kN / (k_f3 * ell_m)   # kN/m
    R_ext = q_d * ell_m / 2.0                     # kN — cada extremo
    F_tot = q_d * ell_m                           # kN
    d_lim = ell_m / 500.0                         # m

    return {
        "n":          n,
        "ell_m":      ell_m,
        "k_ell":      round(k_ell, 4),
        "k_f3":       k_f3,
        "q_d_kNpm":   round(q_d, 5),
        "F_total_kN": round(F_tot, 4),
        "R_ext_kN":   round(R_ext, 4),
        "delta_lim_m": round(d_lim, 5),
        "delta_lim_mm": round(d_lim * 1000, 2),
        "norma":      "EC5 §9.2.5.3",
    }


# ── Terça como biela ──────────────────────────────────────────────────────────

def verifica_terca_biela(
    F_axial_kN: float,
    L_t:        float,
    b:          float,
    h:          float,
    mat:        GlulamMaterial,
) -> dict:
    """
    Terça como biela de estabilização — compressão EC5 §6.3.2.

    Hipótese: a força de estabilização do sistema é repartida pelas terças
    que afluem a cada baía de contraventamento (caminho Y).

    Flambagem no plano fraco da terça (eixo z, I_z = h·b³/12 se h>b em
    orientação usual de terça deitada…):
      Orientação adotada no projeto: b largura (horizontal no plano da
      cobertura), h altura (perpendicular à cobertura).
      Flambagem crítica no plano da cobertura: esbeltez com i = b/√12.
    """
    A = b * h                          # m²
    i_z = b / math.sqrt(12.0)          # m — raio de giração no plano cobertura
    l_ef = L_t                         # m — biapoiada entre pórticos
    lam = l_ef / i_z if i_z > 0 else 1e9

    # λ_rel — EC5 §6.3.2
    f_c0k = mat.f_c0_k                 # Pa
    E005  = mat.E0_05                  # Pa
    lam_rel = (lam / math.pi) * math.sqrt(f_c0k / E005)

    # k_c — EC5 Eq. (6.25)–(6.28), β_c = 0,10 (MLC)
    beta_c = 0.10
    k = 0.5 * (1 + beta_c * (lam_rel - 0.3) + lam_rel**2)
    k_c = 1.0 / (k + math.sqrt(max(k**2 - lam_rel**2, 0.0)))

    f_c0d = mat.f_c0_d                 # Pa
    N_Rd  = k_c * f_c0d * A / 1e3      # kN
    eta   = F_axial_kN / N_Rd if N_Rd > 0 else 999.0

    return {
        "F_axial_kN":   round(F_axial_kN, 4),
        "b_m":          b,
        "h_m":          h,
        "L_t_m":        L_t,
        "A_m2":         round(A, 6),
        "lambda":       round(lam, 1),
        "lambda_rel":   round(lam_rel, 4),
        "k_c":          round(k_c, 4),
        "N_Rd_kN":      round(N_Rd, 3),
        "eta":          round(eta, 4),
        "ok":           eta <= 1.0,
        "norma":        "EC5 §6.3.2 (terça-biela)",
    }


# ── Diagonal de aço ───────────────────────────────────────────────────────────

def verificar_diagonal_aco(
    F_diag_kN: float,
    d_mm:      float,
    L_diag_m:  float,
    cos_theta: float,
    aco:       str = "S235",
    C_req_kNpm: float | None = None,
) -> dict:
    """
    Diagonal tracionada — resistência EN 1993-1-1 §6.2.3
    e rigidez axial horizontal do painel.

        N_t,Rd = A · f_y / γ_M0
        C_h = (E·A / L) · cos²θ     (kN/m) — uma diagonal ativa
    """
    if aco not in ACO:
        raise ValueError(f"Aço '{aco}' não reconhecido.")

    f_y = ACO[aco]["f_y"]
    A_mm2 = math.pi * d_mm**2 / 4
    A_m2  = A_mm2 * 1e-6

    N_t_Rd = A_mm2 * f_y / GAMMA_M0 / 1e3          # kN
    eta_N  = F_diag_kN / N_t_Rd if N_t_Rd > 0 else 999.0

    # Rigidez axial da barra (kN/m)
    C_axial = E_ACO_MPA * A_mm2 / (L_diag_m * 1e3)  # kN/m
    # Componente horizontal (painel)
    C_h = C_axial * (cos_theta ** 2)                # kN/m

    ok_N = eta_N <= 1.0
    ok_C = True
    eta_C = 0.0
    if C_req_kNpm is not None and C_req_kNpm > 0:
        eta_C = C_req_kNpm / C_h if C_h > 0 else 999.0
        ok_C = C_h >= C_req_kNpm

    return {
        "d_mm":        d_mm,
        "aco":         aco,
        "f_y_MPa":     f_y,
        "A_mm2":       round(A_mm2, 2),
        "N_t_Rd_kN":   round(N_t_Rd, 4),
        "F_diag_kN":   round(F_diag_kN, 4),
        "eta_N":       round(eta_N, 4),
        "ok_N":        ok_N,
        "C_axial_kNpm": round(C_axial, 2),
        "C_h_kNpm":    round(C_h, 2),
        "C_req_kNpm":  None if C_req_kNpm is None else round(C_req_kNpm, 2),
        "eta_C":       round(eta_C, 4),
        "ok_C":        ok_C,
        "ok":          ok_N and ok_C,
        "norma":       "EN 1993-1-1 §6.2.3 + rigidez axial",
    }


# ── Flecha do sistema estabilizador ───────────────────────────────────────────

def flecha_sistema_estabilizador(
    q_d_kNpm:   float,
    ell_m:      float,
    C_h_kNpm:   float,
    n_paineis:  int,
    n_modulos_cv: int,
) -> dict:
    """
    Estimativa da flecha horizontal do sistema de contraventamento.

    Modelo: baías rígidas nas extremidades (molas em paralelo por painel);
    o vão ℓ entre baías é estabilizado. A flecha admissível é ℓ/500
    (EC5 §9.2.5.3).

    Aproximação conservadora:
      • cada baía extrema tem n_paineis diagonais ativas em paralelo
      • rigidez total de uma baía K_bay = n_paineis · C_h
      • sistema simétrico: duas baías; deslocamento relativo sob carga
        uniforme q_d modelado como flecha de viga biapoiada com
        rigidez equivalente de treliça:

        δ ≈ (5/384) · q_d · ℓ⁴ / (EI)_eq   não aplicável directamente;

      Alternativa (usada): reação R = q_d·ℓ/2 em cada baía;
        δ_bay = R / K_bay
        (deslocamento da baía de apoio — conservador se o “meio” se
         desloca mais; para só 2 baías extremas o meio move-se com as
         terças até as baías — δ_mid ≈ δ_bay em modelo de bielas rígidas
         entre baías, OU maior se terças fletem).

      Para terças rígidas axialmente face às diagonais, δ_gov ≈ δ_bay.
      Limite: δ ≤ ℓ/500.
    """
    K_bay = max(n_paineis, 1) * C_h_kNpm          # kN/m
    R     = q_d_kNpm * ell_m / 2.0                # kN
    delta = R / K_bay if K_bay > 0 else 1e9       # m
    d_lim = ell_m / 500.0
    eta   = delta / d_lim if d_lim > 0 else 999.0

    return {
        "K_bay_kNpm":   round(K_bay, 2),
        "R_ext_kN":     round(R, 4),
        "delta_m":      round(delta, 6),
        "delta_mm":     round(delta * 1000, 3),
        "delta_lim_mm": round(d_lim * 1000, 2),
        "eta_delta":    round(eta, 4),
        "ok":           eta <= 1.0,
        "norma":        "EC5 §9.2.5.3 (δ ≤ ℓ/500)",
    }


# ── Verificação completa ──────────────────────────────────────────────────────

def verificar_contraventamento(
    geo:            GeometriaViga,
    mat:            GlulamMaterial,
    load:           Carregamentos,
    L_comp:         float = 46.0,
    n_modulos_cv:   int   = 2,
    s_terca:        float = 2.53,
    d_barra_mm:     float = 18.0,
    aco:            str   = "S235",
    n_porticos:     int   = 2,
    dist_portico:   float = 5.75,
    b_terca:        float = 0.20,
    h_terca:        float = 0.58,
    k_crit:         float = 1.0,
    k_s:            float = K_S,
    k_f2:           float = K_F2,
    k_f3:           float = K_F3,
) -> dict:
    """
    Verificação completa — integridade estrutural da cobertura.

    Returns dict com sub-verificações, η governante, flags de acoplamento:
      restricao_lateral_valida : terças podem ser usadas como l_1 no LTB
      l_1_efetivo_m            : s_terca se OK; senão ell (penalizado)
      cobertura_ok             : sistema cumpre função estrutural
    """
    layout = LayoutContraventamento(
        L_comp=L_comp,
        dist_portico=dist_portico,
        s_terca=s_terca,
        n_porticos=n_porticos,
        n_modulos_cv=n_modulos_cv,
        d_barra_mm=d_barra_mm,
        aco=aco,
    )
    diag = layout.diagonal()

    # 1) Força a estabilizar
    ncomp = forca_compressao_estabilizar(load, geo, k_crit=k_crit)
    N_d = ncomp["N_d_kN"]

    # 2) §9.2.5.2 — cada restrição por terça na viga
    ap = verifica_apoio_intermediario(N_d, layout.a_restricao_m, k_s=k_s, k_f2=k_f2)

    # 3) §9.2.5.3 — DOIS PLANOS INDEPENDENTES de cobertura (um por vão).
    #    Existem n_porticos planos de telhado independentes; cada plano estabiliza
    #    n_por_plano = n_vigas_por_linha vigas (≈9). NÃO é um sistema único de 18.
    #    Cada plano tem o seu próprio contraventamento (cruzes) → sem duplicação:
    #    a força de estabilização de um plano NÃO passa pelo outro.
    n_por_plano = layout.n_vigas_por_linha            # vigas por plano (≈9)
    n_planos    = layout.n_porticos                   # planos independentes (≈2)
    sis = verifica_sistema_vigas(N_d, n_por_plano, layout.ell_m, k_f3=k_f3)

    # 4) Vento θ=0° (// cumeeira) — força longitudinal na estrutura aberta.
    #    Repartida pelos n_planos planos e pelas 2 baías extremas (simetria).
    vento_0 = getattr(load, "vento_0", None) or {}
    F_vento0_kN = float(vento_0.get("F_total_kN", 0.0))
    R_vento0 = F_vento0_kN / (2.0 * max(n_planos, 1))
    # Reação de projeto por baía extrema (POR PLANO) = máx(§9.2.5.3, vento θ=0°)
    R_ext_estab = sis["R_ext_kN"]                     # por plano
    R_ext_proj  = max(R_ext_estab, R_vento0)
    gov_forca   = "vento_0" if R_vento0 > R_ext_estab else "estab_9.2.5"

    # 5) Distribuição às diagonais — painéis POR PLANO (2 aguas por plano)
    n_pan_plano = max(1, layout.n_paineis_por_mod // max(n_planos, 1))  # =2
    n_pan = layout.n_paineis_por_mod                  # total no galpão (quantitativos)
    F_painel = R_ext_proj / n_pan_plano
    F_diag   = F_painel / diag["cos_theta"] if diag["cos_theta"] > 0 else 1e9

    # 6) Diagonal — dimensionada à TRAÇÃO (§6.2.3).
    #    A rigidez do SISTEMA verifica-se por δ ≤ ℓ/500 (§9.2.5.3),
    #    não por C_min de um apoio individual na barra (isso é papel da
    #    terça-biela: EA/L ≥ C_min).
    bar = verificar_diagonal_aco(
        F_diag_kN=F_diag,
        d_mm=d_barra_mm,
        L_diag_m=diag["d_diag_m"],
        cos_theta=diag["cos_theta"],
        aco=aco,
        C_req_kNpm=None,
    )

    # 7) Flecha do sistema (critério de rigidez global §9.2.5.3)
    #    Para vento θ=0°: q_eq = F_total/ℓ  (carga longitudinal repartida)
    q_vento0 = F_vento0_kN / layout.ell_m if layout.ell_m > 0 else 0.0
    q_flecha = max(sis["q_d_kNpm"], q_vento0)
    fl = flecha_sistema_estabilizador(
        q_d_kNpm=q_flecha,
        ell_m=layout.ell_m,
        C_h_kNpm=bar["C_h_kNpm"],
        n_paineis=n_pan_plano,
        n_modulos_cv=n_modulos_cv,
    )

    # 8) Terça como biela (força + flambagem + rigidez local EA/L ≥ C_min)
    F_terca = R_ext_proj / n_pan_plano
    F_terca = max(F_terca, ap["F_d_kN"])

    ter = verifica_terca_biela(
        F_axial_kN=F_terca,
        L_t=dist_portico,
        b=b_terca,
        h=h_terca,
        mat=mat,
    )
    # Rigidez axial da terça-biela vs C_min do apoio §9.2.5.2
    E_mean_kPa = mat.E0_mean / 1e3          # kN/m²  (Pa → kN/m²: /1000)
    A_terca = b_terca * h_terca             # m²
    C_terca = E_mean_kPa * A_terca / dist_portico   # kN/m
    eta_C_terca = ap["C_min_kNpm"] / C_terca if C_terca > 0 else 999.0
    ok_C_terca = C_terca >= ap["C_min_kNpm"]
    ter["C_axial_kNpm"] = round(C_terca, 1)
    ter["C_min_kNpm"]   = ap["C_min_kNpm"]
    ter["eta_C"]        = round(eta_C_terca, 4)
    ter["ok_C"]         = ok_C_terca
    ter["ok"]           = ter["ok"] and ok_C_terca
    ter["eta"]          = max(ter["eta"], eta_C_terca)

    # 9) Agregação — função estrutural da cobertura
    ok_forca_diag = bar["ok_N"]
    ok_flecha     = fl["ok"]
    ok_terca      = ter["ok"]

    cobertura_ok = all([ok_forca_diag, ok_flecha, ok_terca])
    restricao_lateral_valida = cobertura_ok

    # l_1 efetivo para LTB
    if restricao_lateral_valida:
        l_1_ef = s_terca
        l_1_nota = "terças válidas como restrição lateral (cobertura OK)"
    else:
        # Penalização: sem baía rígida fiável, só contam os extremos
        l_1_ef = layout.ell_m
        l_1_nota = (
            "cobertura NÃO valida restrição a s; "
            f"l_1 penalizado = ℓ = {layout.ell_m:.2f} m"
        )

    # η governante do módulo
    etas = {
        "diagonal_N":   bar["eta_N"],
        "flecha_sis":   fl["eta_delta"],
        "terca_biela":  ter["eta"],          # max(N, C) da terça
        "terca_C":      eta_C_terca,
    }
    gov_key = max(etas, key=etas.get)
    eta_gov = etas[gov_key]

    # Quantitativo
    n_barras = n_modulos_cv * n_pan * 2
    L_tot = n_barras * diag["d_diag_m"]
    peso = L_tot * (math.pi * (d_barra_mm / 1000) ** 2 / 4) * 7850

    return {
        # Identificação
        "sistema": "Cruzes St.André + terças-biela — integridade cobertura",
        "posicao": f"{n_modulos_cv} modulos (ell={layout.ell_m:.1f} m entre baias)",
        "norma":   "EC5 §9.2.5.2+§9.2.5.3+§6.3.2 | EN 1993-1-1 §6.2.3 | vento θ=0°",

        # Compressão a estabilizar + vento longitudinal
        "N_d_kN":         ncomp["N_d_kN"],
        "N_axial_kN":     ncomp["N_axial_kN"],
        "F_vento0_kN":    round(F_vento0_kN, 3),
        "R_ext_estab_kN": round(R_ext_estab, 3),
        "R_ext_proj_kN":  round(R_ext_proj, 3),
        "gov_forca":      gov_forca,
        "N_flex_kN":      ncomp["N_flex_kN"],
        "n_vigas":        layout.n_vigas,           # total no galpão (informativo)
        "comb":           ncomp["comb"],

        # §9.2.5.2
        "a_restricao_m":  ap["a_m"],
        "C_min_kNpm":     ap["C_min_kNpm"],
        "F_d_apoio_kN":   ap["F_d_kN"],

        # §9.2.5.3 — POR PLANO (dois planos independentes)
        "n_planos":       n_planos,
        "n_por_plano":    n_por_plano,
        "ell_m":          sis["ell_m"],
        "k_ell":          sis["k_ell"],
        "q_d_kNpm":       sis["q_d_kNpm"],          # por plano
        "F_total_kN":     sis["F_total_kN"],        # por plano
        "R_ext_kN":       sis["R_ext_kN"],          # por plano, por baía
        "n_paineis_por_plano": n_pan_plano,

        # Painel / diagonal
        "L_panel_m":      diag["L_panel_m"],
        "s_terca_m":      diag["s_terca_m"],
        "d_diag_m":       diag["d_diag_m"],
        "theta_deg":      diag["theta_deg"],
        "n_paineis_por_mod": n_pan,
        "F_painel_kN":    round(F_painel, 4),
        "F_diag_kN":      round(F_diag, 4),
        "d_barra_mm":     d_barra_mm,
        "aco":            aco,
        "A_mm2":          bar["A_mm2"],
        "N_t_Rd_kN":      bar["N_t_Rd_kN"],
        "C_h_kNpm":       bar["C_h_kNpm"],
        "eta_diag_N":     bar["eta_N"],
        "ok_diag":        bar["ok_N"],
        "C_terca_kNpm":   ter["C_axial_kNpm"],
        "eta_C_terca":    eta_C_terca,
        "ok_C_terca":     ok_C_terca,

        # Flecha sistema
        "delta_mm":       fl["delta_mm"],
        "delta_lim_mm":   fl["delta_lim_mm"],
        "eta_delta":      fl["eta_delta"],
        "ok_delta":       fl["ok"],

        # Terça-biela
        "F_terca_kN":     ter["F_axial_kN"],
        "eta_terca":      ter["eta"],
        "ok_terca":       ter["ok"],
        "terca":          ter,

        # Sub-etas
        "etas":           etas,
        "eta_gov_key":    gov_key,

        # Acoplamento LTB / cobertura
        "restricao_lateral_valida": restricao_lateral_valida,
        "l_1_efetivo_m":  round(l_1_ef, 3),
        "l_1_nota":       l_1_nota,
        "cobertura_ok":   cobertura_ok,

        # Resultado consolidado (compatível com pipeline)
        "eta":            round(eta_gov, 4),
        "ok":             cobertura_ok,

        # Quantitativo
        "n_barras":       n_barras,
        "L_barra_m":      diag["d_diag_m"],
        "L_total_m":      round(L_tot, 2),
        "peso_total_kg":  round(peso, 1),

        # Fatores usados
        "k_s": k_s, "k_f2": k_f2, "k_f3": k_f3,
    }


def relatorio(res: dict) -> None:
    """Imprime relatório legível da integridade da cobertura."""
    print("=" * 68)
    print("  CONTRAVENTAMENTO — INTEGRIDADE ESTRUTURAL DA COBERTURA")
    print("  EC5 §9.2.5 + §6.3.2 | EN 1993-1-1 §6.2.3")
    print("=" * 68)
    print(f"  Sistema : {res['sistema']}")
    print(f"  Posição : {res['posicao']}")
    print(f"  Comb.   : {res['comb']}")
    print()
    print("  ── Compressão a estabilizar ──")
    print(f"    N_axial = {res['N_axial_kN']:.2f} kN | "
          f"N_flex = {res['N_flex_kN']:.2f} kN")
    print(f"    N_d     = {res['N_d_kN']:.2f} kN  ×  {res['n_vigas']} vigas")
    print()
    print("  ── §9.2.5.2 Apoio intermediário (por terça) ──")
    print(f"    a = {res['a_restricao_m']:.2f} m | "
          f"F_d = {res['F_d_apoio_kN']:.3f} kN | "
          f"C_min = {res['C_min_kNpm']:.1f} kN/m")
    print()
    print("  ── §9.2.5.3 Sistema de vigas ──")
    print(f"    ℓ = {res['ell_m']:.1f} m | k_ℓ = {res['k_ell']:.3f}")
    print(f"    q_d = {res['q_d_kNpm']:.4f} kN/m | "
          f"R_ext = {res['R_ext_kN']:.2f} kN | "
          f"F_tot = {res['F_total_kN']:.2f} kN")
    print()
    print("  ── Diagonal de aço ──")
    print(f"    d={res['d_barra_mm']:.0f} mm {res['aco']} | "
          f"θ={res['theta_deg']}° | F_diag={res['F_diag_kN']:.2f} kN")
    print(f"    η_N = {res['eta_diag_N']:.4f}  "
          f"({'✓' if res['eta_diag_N'] <= 1 else '✗'})  |  "
          f"C_h = {res['C_h_kNpm']:.1f} kN/m (info)")
    print()
    print("  ── Flecha do sistema (δ ≤ ℓ/500) — rigidez global ──")
    print(f"    δ = {res['delta_mm']:.3f} mm ≤ {res['delta_lim_mm']:.2f} mm  "
          f"η = {res['eta_delta']:.4f}  "
          f"({'✓' if res['ok_delta'] else '✗'})")
    print()
    print("  ── Terça como biela (força + C ≥ C_min) ──")
    t = res["terca"]
    print(f"    F = {res['F_terca_kN']:.2f} kN | "
          f"λ_rel = {t['lambda_rel']:.3f} | k_c = {t['k_c']:.3f}")
    print(f"    N_Rd = {t['N_Rd_kN']:.1f} kN | η_N = {t.get('eta', res['eta_terca']):.4f}")
    print(f"    C_terça = {res['C_terca_kNpm']:.0f} kN/m ≥ "
          f"C_min = {res['C_min_kNpm']:.0f} kN/m | "
          f"η_C = {res['eta_C_terca']:.4f}  "
          f"({'✓' if res['ok_C_terca'] else '✗'})")
    print(f"    terça-biela: {'✓' if res['ok_terca'] else '✗'}")
    print()
    print("  ── Função estrutural da cobertura ──")
    ok = res["cobertura_ok"]
    print(f"    cobertura_ok = {'✓ SIM' if ok else '✗ NÃO'}")
    print(f"    restrição lateral válida para LTB: "
          f"{'SIM' if res['restricao_lateral_valida'] else 'NÃO'}")
    print(f"    l_1 efetivo = {res['l_1_efetivo_m']:.3f} m")
    print(f"    ({res['l_1_nota']})")
    print()
    print(f"  η governante ({res['eta_gov_key']}) = {res['eta']:.4f}  "
          f"→ {'APROVADO' if res['ok'] else 'REPROVADO'}")
    print(f"  Quantitativo: {res['n_barras']} barras × "
          f"{res['L_barra_m']:.2f} m = {res['L_total_m']:.1f} m "
          f"({res['peso_total_kg']:.1f} kg)")
    print("=" * 68)


# ── Execução directa ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    from mlc_projeto.core.wind import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.30)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    params = ParametrosVento(
        V0=45, S1=1, categoria="IV", classe="B", S3=1,
        L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=1.5, q_area=0.25,
        L_t=5.75, params_vento=params,
    )
    gov = load.combinacao_ELU_governante()
    mat_elu = mat.com_duracao(gov.duracao)

    res = verificar_contraventamento(
        geo=geo, mat=mat_elu, load=load,
        L_comp=46.0, n_modulos_cv=2, s_terca=2.53,
        d_barra_mm=18.0, aco="S235", n_porticos=2,
        b_terca=0.20, h_terca=0.58,
    )
    relatorio(res)
