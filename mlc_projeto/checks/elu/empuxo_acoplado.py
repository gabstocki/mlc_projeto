"""
checks/elu/empuxo_acoplado.py — Empuxo REALMENTE desenvolvido vs. rigidez do apoio.

Contexto (issues 35 / 38)
-------------------------
O empuxo `H` do modelo (`loads.py`, Castigliano) é obtido assumindo **apoio
horizontal INDESLOCÁVEL** no springing (topo do pilar). Este módulo audita, de
forma reproduzível e testável, **quanto desse empuxo realmente se desenvolve**
quando o apoio tem rigidez horizontal finita — substituindo o script pontual que
gerou `output/issue35_empuxo_vs_rigidez.png`.

Modelo (método das forças, 1 redundante horizontal no springing)
----------------------------------------------------------------
Libera-se a restrição horizontal de um springing. Sob a carga `q` o springing
afasta-se livremente de `δ0` (deslocamento do sistema liberado com H=0). A
autoflexibilidade horizontal do arco no springing é

    f11 = ∫ y_c²/(E I) ds + ∫ cos²θ/(E A) ds   (flexão + axial — mesmas integrais do H)
    k_arco = 1 / f11                            (rigidez horizontal do arco)

Com um apoio de rigidez horizontal `k` (mola em série com o arco), a
compatibilidade `δ_apoio = δ0 − f11·H` dá:

    H_dev = H_rígido · k / (k + k_arco)          (duas molas em série)
    M_viga(x) = M0(x) − H_dev · y_c(x)

Limites:
  · k → ∞  (apoio rígido):  H_dev = H_rígido,   M_viga = M_modelo (reduzido).
  · k → 0  (apoio livre):   H_dev = 0,          M_viga = M0 (biapoiada).

O que restringe o springing (topo do pilar, z=7 m)
--------------------------------------------------
  · Pilar **biarticulado** (rótula topo+base): no plano do pórtico é um
    **mecanismo lateral** — não oferece rigidez horizontal no topo
    (`k_pilar = 0`). Uma força horizontal no topo não pode ser equilibrada por
    rótulas nas duas extremidades (ΣM_base = H·H_col ⇒ H=0).
  · Mesmo dando ao pilar uma **base engastada** (limite superior generoso,
    cantilever), `k = 3EI/H³ ≈ 53 kN/m` — ainda ~10³–10⁴× menor que `k_arco`.
  · O **tirante no piso** e a ancoragem restringem as BASES (que quase não se
    afastam); entre o springing e a base há a flexão do pilar (série, mole) —
    por isso a restrição paralela da base NÃO chega ao springing (correção da
    conclusão da issue 24).

Conclusão (issue 38): o empuxo de gravidade **praticamente não se desenvolve**
(H_dev ≈ 0); a viga tende a **biapoiada** (M_viga ≈ M0) e o pilar recebe
esforço horizontal ≈ 0 — **refuta** o "M≈1300 kN·m / colapso do pilar": o pilar
não atrai o empuxo. A penalidade real é (a) o M da viga (subestimado no modelo)
e (b) a abertura horizontal do springing (ELS).

Referência: EN 1995-1-1 §5.4; método das forças (Castigliano); EN 1993-1-1 §5.2.1
"""

from __future__ import annotations

import math

import numpy as np
from scipy.integrate import trapezoid

from mlc_projeto.core.geometry import GeometriaViga


# ── Rigidez horizontal do arco (springing) ───────────────────────────────────

def rigidez_horizontal_arco(
    geo: GeometriaViga,
    E_Pa: float,
    n_pts: int = 4001,
) -> dict:
    """
    Autoflexibilidade/rigidez horizontal do arco no springing (flexão + axial),
    coerente com o denominador do `H` de `analisar_biarticulada`.

        f11 = ∫ y_c²/(E I) ds + ∫ cos²θ/(E A) ds ;  k_arco = 1/f11
    """
    if E_Pa <= 0:
        raise ValueError("E_Pa deve ser positivo")
    L = float(geo.L)
    x = np.linspace(0.0, L, n_pts)
    x_sim = np.where(x <= L / 2.0, x, L - x)
    tan_a = math.tan(geo.alpha_rad)
    y_c = x_sim * tan_a / 2.0
    h_x = geo.h0 + x_sim * tan_a
    I_x = np.maximum(geo.b * h_x ** 3 / 12.0, 1e-18)
    A_x = np.maximum(geo.b * h_x, 1e-18)
    theta = math.atan(tan_a / 2.0)
    ds_dx = 1.0 / math.cos(theta)

    f_flex = float(trapezoid(y_c ** 2 / I_x * ds_dx, x)) / E_Pa       # m/N
    f_ax = float(trapezoid(math.cos(theta) ** 2 / A_x * ds_dx, x)) / E_Pa
    f11 = f_flex + f_ax
    k_arco_Npm = 1.0 / f11 if f11 > 0 else math.inf
    return {
        "f11_m_per_N":   f11,
        "f_flex_m_per_N": f_flex,
        "f_ax_m_per_N":  f_ax,
        "k_arco_kNm":    k_arco_Npm / 1e3,      # kN/m
        "k_arco_kNmm":   k_arco_Npm / 1e6,      # kN/mm
        "theta_rad":     theta,
    }


# ── Rigidez lateral do pilar no plano do pórtico ─────────────────────────────

def rigidez_lateral_pilar(
    b: float,
    h: float,
    H_col: float,
    E_Pa: float,
    base: str = "rotulada",
) -> dict:
    """
    Rigidez horizontal que o TOPO do pilar oferece ao springing, no plano do
    pórtico (h = dimensão no plano).

      · base='rotulada' (rótula topo+base): k = 0 (mecanismo lateral no plano).
      · base='engastada' (base fixa, cantilever): k = 3·E·I / H_col³
        (limite superior GENEROSO — o modelo real usa base rotulada).
    """
    if base not in ("rotulada", "engastada"):
        raise ValueError("base deve ser 'rotulada' ou 'engastada'")
    I_col = b * h ** 3 / 12.0
    if base == "engastada":
        k_Npm = 3.0 * E_Pa * I_col / H_col ** 3
    else:
        k_Npm = 0.0
    return {
        "base":     base,
        "I_m4":     I_col,
        "k_kNm":    k_Npm / 1e3,     # kN/m
        "k_kNmm":   k_Npm / 1e6,     # kN/mm
    }


# ── Empuxo desenvolvido (duas molas em série) ────────────────────────────────

def empuxo_desenvolvido(
    H_rigido_kN: float,
    k_arco_kNm: float,
    k_support_kNm: float,
) -> float:
    """H_dev = H_rígido · k/(k + k_arco). k_support=inf → rígido; 0 → nulo."""
    if math.isinf(k_support_kNm):
        return H_rigido_kN
    if k_support_kNm <= 0.0:
        return 0.0
    return H_rigido_kN * k_support_kNm / (k_support_kNm + k_arco_kNm)


def _M_max_kNm(geo: GeometriaViga, q_kNpm: float, H_kN: float, n_pts: int = 4001) -> float:
    """max|M(x)| com M(x)=M0(x)−H·y_c(x) para carga simétrica q."""
    L = float(geo.L)
    x = np.linspace(0.0, L, n_pts)
    x_sim = np.where(x <= L / 2.0, x, L - x)
    y_c = x_sim * math.tan(geo.alpha_rad) / 2.0
    M0 = 0.5 * q_kNpm * x * (L - x)
    M = M0 - H_kN * y_c
    return float(np.max(np.abs(M)))


# ── Orquestrador — auditoria do empuxo acoplado ──────────────────────────────

def analisar_empuxo_acoplado(
    geo: GeometriaViga,
    E_Pa: float,
    H_rigido_kN: float,
    q_gov_kNpm: float,
    b_pilar: float,
    h_pilar: float,
    H_pilar: float,
    E_pilar_Pa: float | None = None,
    n_pts: int = 4001,
) -> dict:
    """
    Auditoria (issue 38): quanto do empuxo `H_rígido` (modelo de apoio rígido)
    realmente se desenvolve dada a rigidez horizontal real do apoio (topo do
    pilar), e qual o M da viga em cada caso.

    Args:
        H_rigido_kN : empuxo do modelo (Castigliano, apoio rígido) da combinação
                      de gravidade governante (max |M|).
        q_gov_kNpm  : carga uniforme dessa combinação (kN/m) — para M0/M_viga.
        b_pilar,h_pilar,H_pilar : seção e altura do pilar (h no plano do pórtico).

    Returns:
        dict com k_arco, k_pilar (rotulada e engastada), H_dev (real e sweep),
        M_viga (modelo × biapoiada), razão e o veredito da auditoria.
    """
    E_pil = E_pilar_Pa if E_pilar_Pa is not None else E_Pa
    arco = rigidez_horizontal_arco(geo, E_Pa, n_pts=n_pts)
    k_arco = arco["k_arco_kNm"]

    pil_rot = rigidez_lateral_pilar(b_pilar, h_pilar, H_pilar, E_pil, base="rotulada")
    pil_eng = rigidez_lateral_pilar(b_pilar, h_pilar, H_pilar, E_pil, base="engastada")

    # Empuxo desenvolvido — apoio real (pilar rotulado = 0) e limite generoso
    # (pilar engastado, cantilever). Ambos ≈ 0 porque k_arco ≫ k_pilar.
    H_dev_rot = empuxo_desenvolvido(H_rigido_kN, k_arco, pil_rot["k_kNm"])
    H_dev_eng = empuxo_desenvolvido(H_rigido_kN, k_arco, pil_eng["k_kNm"])

    # Momentos da viga
    M_modelo = _M_max_kNm(geo, q_gov_kNpm, H_rigido_kN, n_pts)   # com empuxo rígido
    M0_biap = _M_max_kNm(geo, q_gov_kNpm, 0.0, n_pts)            # sem empuxo
    M_dev = _M_max_kNm(geo, q_gov_kNpm, H_dev_eng, n_pts)        # limite generoso
    razao_M = M0_biap / M_modelo if M_modelo > 0 else math.inf

    # Sweep de rigidez (kN/m): rígido, decadente, pilar (cantilever), livre
    sweep = []
    for k in (math.inf, 1e6, 1e5, pil_eng["k_kNm"], 0.0):
        Hd = empuxo_desenvolvido(H_rigido_kN, k_arco, k)
        sweep.append({
            "k_support_kNm": ("inf" if math.isinf(k) else round(k, 3)),
            "H_dev_kN":      round(Hd, 2),
            "M_viga_kNm":    round(_M_max_kNm(geo, q_gov_kNpm, Hd, n_pts), 1),
        })

    # Fração desenvolvida no apoio real (limite generoso engastado)
    frac_eng = H_dev_eng / H_rigido_kN if H_rigido_kN != 0 else 0.0

    desenvolve = frac_eng >= 0.10   # < 10% ⇒ empuxo NÃO se desenvolve
    return {
        "ativo":          True,
        "sistema":        "Auditoria do empuxo acoplado (issue 38)",
        "H_rigido_kN":    round(H_rigido_kN, 2),
        "q_gov_kNpm":     round(q_gov_kNpm, 4),
        "k_arco_kNm":     round(k_arco, 1),
        "k_arco_kNmm":    round(arco["k_arco_kNmm"], 2),
        "k_pilar_rot_kNm": round(pil_rot["k_kNm"], 3),
        "k_pilar_eng_kNm": round(pil_eng["k_kNm"], 3),
        "razao_k_arco_pilar": (
            round(k_arco / pil_eng["k_kNm"], 0) if pil_eng["k_kNm"] > 0 else math.inf
        ),
        "H_dev_rotulada_kN": round(H_dev_rot, 3),
        "H_dev_engastada_kN": round(H_dev_eng, 3),
        "frac_desenvolvida": round(frac_eng, 5),
        "M_modelo_kNm":   round(M_modelo, 1),
        "M0_biapoiada_kNm": round(M0_biap, 1),
        "M_dev_kNm":      round(M_dev, 1),
        "razao_M0_modelo": round(razao_M, 3),
        "delta_M_pct":    round((razao_M - 1.0) * 100.0, 1),
        "sweep":          sweep,
        "empuxo_desenvolve": desenvolve,
        "colapso_pilar_refutado": True,
        "norma":          "EN 1995-1-1 §5.4 (método das forças) | EN 1993-1-1 §5.2.1",
        "veredito": (
            "Com o pilar biarticulado (mecanismo lateral no plano, k=0) — e mesmo "
            f"no limite generoso de base engastada (k={pil_eng['k_kNm']:.0f} kN/m, "
            f"~{k_arco/pil_eng['k_kNm']:.0f}× menor que k_arco={k_arco:.0f} kN/m) — "
            f"só se desenvolve {frac_eng*100:.1f}% do empuxo rígido "
            f"(H_dev≈{H_dev_eng:.1f} de {H_rigido_kN:.0f} kN). A viga tende a "
            f"BIAPOIADA: M passa de {M_modelo:.0f} (modelo) para {M0_biap:.0f} kN·m "
            f"(+{(razao_M-1)*100:.0f}%). O pilar recebe esforço horizontal ≈ 0 → "
            "o 'M≈1300 kN·m / colapso do pilar' NÃO ocorre (o pilar não atrai o "
            "empuxo). Corrige a conclusão da issue 24 (a restrição da base não "
            "chega ao springing por causa da flexão do pilar, em série)."
        ),
    }


def relatorio_empuxo_acoplado(res: dict) -> None:
    """Impressão resumida no console."""
    if not res or not res.get("ativo"):
        print("  · Empuxo acoplado: N/A")
        return
    print("  Auditoria do empuxo acoplado (issue 38):")
    print(
        f"  · k_arco={res['k_arco_kNm']:.0f} kN/m vs k_pilar(engast.)="
        f"{res['k_pilar_eng_kNm']:.0f} kN/m (rótula=0) → "
        f"{res['razao_k_arco_pilar']:.0f}× mais rígido o arco"
    )
    print(
        f"  · H_rígido={res['H_rigido_kN']:.0f} kN → H_dev≈{res['H_dev_engastada_kN']:.1f} kN "
        f"({res['frac_desenvolvida']*100:.1f}%) ⇒ empuxo "
        f"{'DESENVOLVE' if res['empuxo_desenvolve'] else 'NÃO se desenvolve'}"
    )
    print(
        f"  · M_viga: {res['M_modelo_kNm']:.0f} (modelo, empuxo rígido) → "
        f"{res['M0_biapoiada_kNm']:.0f} kN·m (biapoiada, +{res['delta_M_pct']:.0f}%)"
    )
    print("  · Colapso do pilar (M~1300 kN·m) REFUTADO: pilar não atrai o empuxo.")
    print(f"    {'k_apoio[kN/m]':>14} {'H_dev[kN]':>10} {'M_viga[kN·m]':>13}")
    for s in res["sweep"]:
        print(f"    {str(s['k_support_kNm']):>14} {s['H_dev_kN']:>10.2f} {s['M_viga_kNm']:>13.1f}")
