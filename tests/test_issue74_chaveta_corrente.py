"""Issue 74 — bases correntes com chaveta cruciforme: cortante fora dos chumbadores."""

import contextlib
import io

import pytest

import mlc_projeto.main as M


@pytest.fixture(scope="module")
def r():
    orig = M.gerar_relatorio
    M.gerar_relatorio = lambda *a, **k: {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.gerar_relatorio = orig


@pytest.mark.parametrize("k", ["ancoragem_L3", "ancoragem_L3c"])
def test_cortante_vai_a_chaveta(r, k):
    a = r[k]
    assert a["chaveta"]["tipo"] == "cruciforme"
    for c in a["casos"].values():
        assert c["chaveta_cisalhamento"] is True and "chaveta" in c
        assert c["eta"] >= c["chaveta"]["eta"]


def test_L3f_tambem_tem_chaveta(r):
    b = r["pilar_frontao"]["base"]
    assert all("chaveta" in c for c in b["casos"].values())
