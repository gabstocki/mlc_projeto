"""
checks/elu/cumeeira.py — Tensão de tração perpendicular na cumeeira.

VERIFICAÇÃO CRÍTICA — frequentemente governa o projeto para α > 5°.

Referência: EC5 §6.4.3, Eq. 6.50, 6.51, 6.54
"""

import numpy as np
from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def k_p(alpha_deg: float) -> float:
    """
    Coeficiente de forma k_p para viga de duplo-bisel (EC5 §6.4.3).

    Args:
        alpha_deg: Ângulo de inclinação da cumeeira (graus)
    """
    # TODO: implementar equação EC5 §6.4.3
    raise NotImplementedError("cumeeira.k_p — a implementar")


def k_vol(V_zona: float, V0: float = 0.01) -> float:
    """
    Fator de volume k_vol = (V0/V)^0,20 (EC5 §6.4.3 Eq. 6.51).

    Args:
        V_zona : Volume da zona estressada na cumeeira (m³)
        V0     : Volume de referência = 0,01 m³
    """
    return (V0 / V_zona) ** 0.20


def verifica_cumeeira(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Verifica tensão de tração perpendicular na cumeeira (EC5 §6.4.3 Eq. 6.50).

    σ_t,90,d = k_p · 6·M_ap,d / (b · h_ap²)
    Condição : σ_t,90,d ≤ k_dis · k_vol · f_t,90,d

    k_dis = 1,4 para vigas de duplo-bisel

    Returns:
        dict com sigma_t90d, k_vol, resistencia, eta e ok
    """
    # TODO: implementar
    raise NotImplementedError("cumeeira.verifica_cumeeira — a implementar")
