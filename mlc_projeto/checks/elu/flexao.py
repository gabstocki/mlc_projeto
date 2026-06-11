"""
checks/elu/flexao.py — Verificação de flexão simples e biaxial.

Referência: EC5 §6.1.6, Eq. 6.11 e 6.12
"""

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def verifica_flexao(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
) -> dict:
    """
    Verifica a resistência à flexão na seção crítica (EC5 §6.1.6 Eq. 6.11).

    σ_m,d = M_d / W_y ≤ f_m,d

    Returns:
        dict com sigma_md (Pa), f_md (Pa), eta e ok
    """
    # TODO: implementar
    raise NotImplementedError("flexao.verifica_flexao — a implementar")
