"""Issue 53 — formatador único: η com 2 casas para cima; esforços com 3 alg. sig."""
import pytest

from mlc_projeto.output.formatacao import eta_exibido, fmt_eta, fmt_sig, sig


@pytest.mark.parametrize("eta, txt", [
    (0.8452, "0,85"), (0.85, "0,85"), (0.3814, "0,39"), (0.7492, "0,75"),
    (0.0063, "0,01"), (0.0, "0,00"),
])
def test_eta_duas_casas_para_cima(eta, txt):
    assert fmt_eta(eta) == txt


def test_eta_acima_de_1_nunca_vira_1():
    assert eta_exibido(1.0001) == 1.01
    assert eta_exibido(1.0) == 1.0


def test_eta_exibido_nunca_menor_que_o_calculado():
    for k in range(1, 2000):
        e = k / 1999.0 * 1.2
        assert eta_exibido(e) >= e - 1e-12


@pytest.mark.parametrize("x, txt", [
    (504.26, "504"), (99.61, "99,6"), (8.748, "8,75"), (1016.64, "1.020"),
    (-394.4, "-394"), (0.32, "0,32"), (2.5, "2,5"),
])
def test_tres_algarismos_significativos(x, txt):
    assert fmt_sig(x) == txt


def test_zeros_finais_opcionais_e_ponto_decimal():
    assert fmt_sig(2.1, zeros=True) == "2,10"
    assert fmt_sig(99.61, decimal=".", milhar=False) == "99.6"
    assert sig(0.0) == 0.0
