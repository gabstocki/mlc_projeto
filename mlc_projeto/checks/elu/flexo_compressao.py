from mlc_projeto.checks.elu.pilares import verifica_pilar, esforcos_pilar

def verifica_flexo_compressao(
    geo, mat, load,
    b_pilar:  float = 0.22,
    h_pilar:  float = 0.80,
    H_pilar:  float = 7.0,
    sistema:  str   = "A",
) -> dict:
    """
    Verificação de flexo-compressão do pilar dimensionado.
    Delega para pilares.py que contém a implementação completa.
    """
    # importar vento e calcular esforços
    ...
    return verifica_pilar(mat, b_pilar, h_pilar, H_pilar, N_d, M_d, sistema)