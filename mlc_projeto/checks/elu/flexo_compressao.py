"""
checks/elu/flexo_compressao.py — Flexo-compressão de pilares.

Referência: EC5 §6.3.2, Eq. 6.23 e 6.24
"""

from mlc_projeto.core.geometry  import GeometriaViga
from mlc_projeto.core.materials import GlulamMaterial
from mlc_projeto.core.loads     import Carregamentos


def verifica_flexo_compressao(
    geo:  GeometriaViga,
    mat:  GlulamMaterial,
    load: Carregamentos,
    N_d:  float = 0.0,
    l_ef: float | None = None,
) -> dict:
    """
    (σ_c,0,d / (k_c · f_c,0,d))² + σ_m,d / f_m,d ≤ 1,0
    (EC5 §6.3.2 Eq. 6.23)

    Returns:
        dict com lambda_rel_c, k_c, eta e ok
    """
    # TODO: implementar
    raise NotImplementedError(
        "flexo_compressao.verifica_flexo_compressao — a implementar"
    )
