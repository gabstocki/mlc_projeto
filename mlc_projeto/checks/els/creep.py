"""
checks/els/creep.py — Flecha final com fluência.

w_fin = w_G(1+k_def) + w_Q1(1+ψ₂·k_def) + Σw_Qi(ψ₀+ψ₂·k_def)

Referência: EC5 §2.3.2.2, Tab. 3.2, Tab. 7.2
"""

from mlc_projeto.core.geometry       import GeometriaViga
from mlc_projeto.core.materials      import GlulamMaterial
from mlc_projeto.core.loads          import Carregamentos
from mlc_projeto.checks.els.deflection import calcular_flecha


def calcular_flecha_final(
    geo:   GeometriaViga,
    mat:   GlulamMaterial,
    load:  Carregamentos,
    psi_2: float = 0.0,
) -> dict:
    """
    Flecha final com fluência (EC5 §2.3.2.2).

    w_fin = w_G·(1+k_def) + w_Q1·(1+ψ₂·k_def)
    w_net,fin ≤ L/250  (EC5 Tab. 7.2)

    Returns:
        dict com w_g_inst, w_q_inst, w_fin (m), limite L/250 (m), eta e ok
    """
    # TODO: implementar separação de componentes e cálculo de w_fin
    raise NotImplementedError("creep.calcular_flecha_final — a implementar")
