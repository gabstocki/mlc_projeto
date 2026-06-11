"""
checks/elu/flambagem_lateral.py — Flambagem lateral por flexo-torção.

VERIFICAÇÃO CRÍTICA — governa vigas esbeltas sem restrição lateral contínua.

Referência: EC5 §6.3.3
"""

import numpy as np
from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def sigma_m_crit(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    l_ef: float,
) -> float:
    """
    Tensão crítica de flambagem lateral (EC5 §6.3.3).

    σ_m,crit = π·E_0,05·I_z·G_mean·I_tor / (W_y · l_ef)

    Args:
        l_ef: Comprimento efetivo (m) — EC5 Tabela 6.1
    """
    # TODO: implementar
    raise NotImplementedError("flambagem_lateral.sigma_m_crit — a implementar")


def k_crit(lambda_rel_m: float) -> float:
    """
    Fator de instabilidade k_crit (EC5 §6.3.3).

    λ_rel,m ≤ 0,75          → k_crit = 1,0
    0,75 < λ_rel,m ≤ 1,4   → k_crit = 1,56 - 0,75·λ_rel,m
    λ_rel,m > 1,4            → k_crit = 1/λ_rel,m²
    """
    if lambda_rel_m <= 0.75:
        return 1.0
    elif lambda_rel_m <= 1.4:
        return 1.56 - 0.75 * lambda_rel_m
    else:
        return 1.0 / lambda_rel_m ** 2


def verifica_flambagem_lateral(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    l_ef: float | None = None,
) -> dict:
    """
    σ_m,d ≤ k_crit · f_m,d  (EC5 §6.3.3)

    Returns:
        dict com sigma_md, sigma_m_crit, lambda_rel_m, k_crit, eta e ok
    """
    # TODO: implementar
    raise NotImplementedError(
        "flambagem_lateral.verifica_flambagem_lateral — a implementar"
    )
