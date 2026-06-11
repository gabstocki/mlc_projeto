"""
checks/els/deflection.py — Flecha instantânea por integração numérica.

Integra M(x)/(E·I(x)) para seção de inércia variável.
Usa E_mean (não E_0,05) para ELS (EC5 §2.2.3).

Referência: EC5 §2.2.3, Tab. 7.2
"""

import numpy as np
from scipy.integrate import cumulative_trapezoid
from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def calcular_flecha(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Flecha instantânea por integração numérica de κ(x) = M(x)/(E·I(x)).

    w_inst_max ≤ L/300  (EC5 Tab. 7.2 — recomendação)

    Returns:
        dict com w_inst_max (m), limite L/300 (m), eta e ok
    """
    x   = geo.x
    E   = mat.E0_mean          # Pa — ELS usa E_mean
    I_x = geo.I(x)             # m⁴
    M_x = load.M_ELS_car() * 1e3  # N·m (converter de kN·m)

    kappa = M_x / (E * I_x)   # curvatura (1/m)

    # Integração dupla para obter deflexão (condições de contorno: w(0)=w(L)=0)
    theta = cumulative_trapezoid(kappa, x, initial=0)
    theta -= theta[-1] * x / geo.L   # ajuste BC w(L) = 0

    w = cumulative_trapezoid(theta, x, initial=0)
    w -= w[-1] * x / geo.L

    w_max   = float(np.max(np.abs(w)))
    limite  = geo.L / 300

    return {
        "w_inst_max_m": w_max,
        "limite_m":     limite,
        "L_300":        limite,
        "eta":          w_max / limite,
        "ok":           w_max <= limite,
        "w_x":          w,       # perfil completo para plot
    }
