"""
checks/elu/apoio.py — Compressão no apoio.

Verifica compressão na fibra inclinada (Hankinson) e
compressão perpendicular na placa de apoio.

Referência: EC5 §6.2.2 (Hankinson), §6.1.5 (compressão perpendicular)
"""

import numpy as np
from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def f_c_alpha_d(mat: GlulamMaterial, alpha_deg: float) -> float:
    """
    Resistência de cálculo na direção α (Hankinson, EC5 §6.2.2).

    f_c,α,d = f_c,0,d · f_c,90,d /
              (f_c,0,d · sin²α + f_c,90,d · cos²α)
    """
    import math
    a = math.radians(alpha_deg)
    return (mat.f_c0_d * mat.f_c90_d /
            (mat.f_c0_d * math.sin(a)**2 + mat.f_c90_d * math.cos(a)**2))


def verifica_apoio(
    geo:      GeometriaViga,
    mat:      GlulamMaterial,
    load:     Carregamentos,
    l_ap:     float = 0.20,
    k_c90:    float = 1.0,
) -> dict:
    """
    Verifica compressão perpendicular na placa de apoio (EC5 §6.1.5).

    σ_c,90,d = R_d / (b · l_ap) ≤ k_c,90 · f_c,90,d

    Args:
        l_ap  : Comprimento da placa de apoio (m)
        k_c90 : Fator de rigidez do apoio (tipicamente 1,0 a 1,75)

    Returns:
        dict com sigma_c90d, resistencia, eta e ok
    """
    # TODO: implementar
    raise NotImplementedError("apoio.verifica_apoio — a implementar")
