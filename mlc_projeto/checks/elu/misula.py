"""
checks/elu/misula.py — Tensão de flexão na borda inclinada (bisel) — EC5 §6.4.2.

Viga de duplo-bisel: o EXTRADORSO (topo) é a borda cortada em ângulo α em relação
à direção das lâminas (grão), que segue o intradorso horizontal. Cada meia-água é
uma "single tapered beam" (§6.4.2); a zona do ápice é tratada à parte pela §6.4.3
(cumeeira, issue 10).

Verificação (EC5 §6.4.2):
    σ_m,α,d = 6·|M_d(x)| / (b·h(x)²)                  (Eq. 6.38)
    σ_m,α,d ≤ k_m,α · f_m,d

    k_m,α depende do sinal da tensão paralela à borda inclinada (topo):
      • TRAÇÃO no topo (momento hogging — sucção/uplift) — Eq. (6.39):
        k_m,α = 1/√[1 + (f_m,d/(0,75·f_v,d)·tanα)² + (f_m,d/f_t,90,d·tan²α)²]
      • COMPRESSÃO no topo (momento sagging — gravidade/pressão) — Eq. (6.40):
        k_m,α = 1/√[1 + (f_m,d/(1,5·f_v,d)·tanα)²  + (f_m,d/f_c,90,d·tan²α)²]

O caso de tração é muito mais desfavorável (f_t,90,d ≪ f_c,90,d ⇒ k_m,α menor),
por isso varrem-se TODAS as combinações ELU (pressão e sucção) e TODAS as seções.

Referência: EC5 §6.4.2, Eq. 6.38 a 6.40.
"""

from __future__ import annotations

import math

import numpy as np

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos, analisar_biarticulada


def k_m_alpha_compressao(mat: GlulamMaterial, alpha_rad: float) -> float:
    """k_m,α para tensão de COMPRESSÃO paralela à borda — EC5 Eq. (6.40)."""
    tan_a = math.tan(alpha_rad)
    fmd, fvd, fc90d = mat.f_m_d, mat.f_v_d, mat.f_c90_d
    denom = (
        1.0
        + (fmd / (1.5 * fvd) * tan_a) ** 2
        + (fmd / fc90d * tan_a ** 2) ** 2
    )
    return 1.0 / math.sqrt(denom)


def k_m_alpha_tracao(mat: GlulamMaterial, alpha_rad: float) -> float:
    """k_m,α para tensão de TRAÇÃO paralela à borda — EC5 Eq. (6.39)."""
    tan_a = math.tan(alpha_rad)
    fmd, fvd, ft90d = mat.f_m_d, mat.f_v_d, mat.f_t90_d
    denom = (
        1.0
        + (fmd / (0.75 * fvd) * tan_a) ** 2
        + (fmd / ft90d * tan_a ** 2) ** 2
    )
    return 1.0 / math.sqrt(denom)


def verifica_misula(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Verifica a borda inclinada (extradorso em bisel) — EC5 §6.4.2.

    Varre todas as combinações ELU e todas as seções x; para cada seção usa
    k_m,α de tração (topo hogging) ou de compressão (topo sagging), com o
    material na duração da combinação (k_mod correto por combinação).

    Returns:
        dict com η governante, seção/combinação/regime que governam e os k_m,α.
    """
    b         = geo.b
    alpha_rad = geo.alpha_rad
    x         = geo.x
    h_x       = geo.h(x)              # m — seção variável

    best = {
        "eta": -1.0, "regime": None, "comb": None, "duracao": None,
        "x_m": None, "h_m": None, "M_kNm": None,
        "sigma_MPa": None, "k_m_alpha": None, "f_md_MPa": None,
    }

    # k_m,α por regime não depende de x (só de α e do material da combinação);
    # guardamos também os valores para a combinação governante de cada regime.
    # F-06: só as combinações FÍSICAS — os aliases ELU_C* duplicariam casos
    # de carga e C3/C4 trariam uma duração fixada que não é a de origem.
    for comb in load.combinacoes_ELU_fisicas().values():
        if abs(comb.q_esq) < 1e-12 and abs(comb.q_dir) < 1e-12:
            continue
        matc  = mat.com_duracao(comb.duracao)
        k_cmp = k_m_alpha_compressao(matc, alpha_rad)
        k_tra = k_m_alpha_tracao(matc, alpha_rad)
        f_md  = matc.f_m_d

        # AUD-007: o default `desenvolve_empuxo=True` fazia esta verificação
        # local analisar OUTRA estrutura (apoio horizontal rígido) enquanto o
        # pipeline roda com H=0. Como M(x) = M0(x) − H·y_c(x), o diagrama e a
        # tensão na mísula ficavam subestimados. O modelo de apoio tem de vir
        # sempre do gerador de combinações, nunca de um default de função.
        r = analisar_biarticulada(
            q=0.5 * (comb.q_esq + comb.q_dir),
            L=geo.L, h0=geo.h0, h_ap=geo.h_ap, alpha_rad=alpha_rad, b=b,
            q_esq=comb.q_esq, q_dir=comb.q_dir,
            desenvolve_empuxo=load.empuxo_desenvolve,
            a_bal=geo.a_bal,
        )
        M_x = np.interp(x, r["x"], r["M_x"]) * 1e3       # N·m (sagging > 0)

        sigma = 6.0 * np.abs(M_x) / (b * h_x ** 2)       # Pa — Eq. (6.38)
        # topo comprimido onde M ≥ 0 (sagging); tracionado onde M < 0 (hogging)
        k_x   = np.where(M_x >= 0.0, k_cmp, k_tra)
        eta_x = sigma / (k_x * f_md)

        i = int(np.argmax(eta_x))
        if eta_x[i] > best["eta"]:
            regime = "compressao" if M_x[i] >= 0 else "tracao"
            best = {
                "eta":       float(eta_x[i]),
                "regime":    regime,
                "comb":      comb.nome,
                "duracao":   comb.duracao,
                "x_m":       float(x[i]),
                "h_m":       float(h_x[i]),
                "M_kNm":     float(M_x[i] / 1e3),
                "sigma_MPa": float(sigma[i] / 1e6),
                "k_m_alpha": float(k_x[i]),
                "f_md_MPa":  float(f_md / 1e6),
                "k_cmp":     float(k_cmp),
                "k_tra":     float(k_tra),
            }

    eta = best["eta"]
    return {
        "L_m":          geo.L,
        "b_m":          b,
        "h0_m":         geo.h0,
        "h_ap_m":       geo.h_ap,
        "alpha_deg":    geo.alpha_deg,
        "tan_alpha":    round(math.tan(alpha_rad), 5),
        # Governante
        "comb_gov":     best["comb"],
        "n_combinacoes_varridas": len(load.combinacoes_ELU_fisicas()),
        "duracao":      best["duracao"],
        "regime":       best["regime"],       # 'compressao' | 'tracao'
        "x_gov_m":      round(best["x_m"], 3),
        "h_gov_m":      round(best["h_m"], 4),
        "M_gov_kNm":    round(best["M_kNm"], 3),
        "sigma_m_alpha_MPa": round(best["sigma_MPa"], 4),
        "k_m_alpha":    round(best["k_m_alpha"], 4),
        "k_m_alpha_compressao": round(best["k_cmp"], 4),
        "k_m_alpha_tracao":     round(best["k_tra"], 4),
        "f_md_MPa":     round(best["f_md_MPa"], 4),
        "resistencia_MPa": round(best["k_m_alpha"] * best["f_md_MPa"], 4),
        "eta":          round(eta, 4),
        "ok":           eta <= 1.0,
        "norma":        "EC5 §6.4.2 Eq. 6.38–6.40",
        "justificativa": (
            f"Borda inclinada (extradorso, α={geo.alpha_deg:.1f}°): "
            f"{best['regime']} no topo governa em x={best['x_m']:.2f} m "
            f"({best['comb']}); k_m,α={best['k_m_alpha']:.3f}"
        ),
    }


if __name__ == "__main__":
    from mlc_projeto.core.wind  import ParametrosVento
    from mlc_projeto.core.loads import carregamentos_com_vento

    geo = GeometriaViga(L=20.25, h0=1.00, alpha_deg=10.0, b=0.32)
    mat = GlulamMaterial(classe="GL24h", classe_servico=3, duracao="curta")
    pv = ParametrosVento(
        V0=45, S1=1, categoria="IV", classe="B", S3=1,
        L=20.25, H1=geo.h_ap - geo.h0, h=7, dist_portico=5.75,
    )
    load = carregamentos_com_vento(
        geo=geo, mat=mat, g_area=1.5, q_area=0.40, L_t=5.75, params_vento=pv,
    )
    res = verifica_misula(geo, mat, load)
    print("MÍSULA / BORDA INCLINADA — EC5 §6.4.2")
    print(f"α={res['alpha_deg']}° | k_m,α(comp)={res['k_m_alpha_compressao']:.3f} "
          f"| k_m,α(tração)={res['k_m_alpha_tracao']:.3f}")
    print(f"Governa: {res['regime']} @ x={res['x_gov_m']} m ({res['comb_gov']}, "
          f"{res['duracao']}) | M={res['M_gov_kNm']:.1f} kN·m")
    print(f"σ_m,α,d={res['sigma_m_alpha_MPa']:.3f} MPa ≤ "
          f"k_m,α·f_m,d={res['resistencia_MPa']:.3f} MPa")
    print(f"η={res['eta']:.4f}  {'OK' if res['ok'] else 'FALHA'}")
