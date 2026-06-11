"""
checks/elu/cisalhamento.py — Verificação de cisalhamento.

Referência: EC5 §6.1.7 Eq. 6.13, §6.5.2 (entalhe)
"""

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def verifica_cisalhamento(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    entalhe: bool = False,
) -> dict:
    """
    τ_d = 1,5 · V_d / (b · h_ef) ≤ f_v,d  (EC5 §6.1.7 Eq. 6.13)

    Se entalhe=True, aplica fator k_v (EC5 §6.5.2).

    Returns:
        dict com tau_d (Pa), f_vd (Pa), eta e ok
    """
    # TODO: implementar
    raise NotImplementedError("cisalhamento.verifica_cisalhamento — a implementar")
