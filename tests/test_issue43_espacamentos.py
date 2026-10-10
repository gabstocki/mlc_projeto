"""Issue 43 — ligação terça–viga e quadro requerido × adotado dos espaçamentos."""
import contextlib
import io

import pytest

import mlc_projeto.main as M
from mlc_projeto.connections.terca_viga import F_ax_Rk, espacamentos_parafusos, f_ax_k
from mlc_projeto.output.quadro_espacamentos import montar_quadro


@pytest.fixture(scope="module")
def res():
    capt = {}
    orig_cv, orig_rel = M.carregamentos_com_vento, M.gerar_relatorio

    def _cv(*a, **k):
        capt["geo"] = k["geo"]
        return orig_cv(*a, **k)

    try:
        M.carregamentos_com_vento = _cv
        M.gerar_relatorio = lambda *a, **k: {}
        with contextlib.redirect_stdout(io.StringIO()):
            capt["res"] = M._main_impl(rodar_varredura=False, abrir_viz=False)
    finally:
        M.carregamentos_com_vento, M.gerar_relatorio = orig_cv, orig_rel
    return capt


def _quadro(r, geo):
    return montar_quadro(
        r, h0_m=geo.h0, L_T=M.L_T, L=geo.L, folga_oblongo_mm=M.FOLGA_OBLONGO_L1_MM,
        d_chu_mm=M.D_CHU_MM, h_ef_mm=M.H_EF_CHU_MM, c_borda_mm=M.C_BORDA_CHU_MM,
        s_grupo_mm=M.S_GRUPO_CHU_MM, h_bloco_mm=M.H_BLOCO_FUND_MM,
        h_pilar_mm={"lateral": M.H_PILAR * 1000, "central": M.H_PILAR_C * 1000,
                    "PF": M.H_PILAR * 1000, "canto": M.H_PILAR_CANTO * 1000},
        h_terca_mm=M.H_TERCA * 1000)


def test_formula_de_arrancamento_do_ec5():
    # Eq. 8.39: f_ax,k = 0,52·d^-0,5·l_ef^-0,1·ρ_k^0,8 ; α = 90° → denominador 1
    f = f_ax_k(8.0, 120.0, 385.0)
    assert f == pytest.approx(0.52 * 8 ** -0.5 * 120 ** -0.1 * 385 ** 0.8)
    assert F_ax_Rk(8.0, 120.0, 385.0, 90.0) == pytest.approx(f * 8 * 120 / 1e3)
    assert F_ax_Rk(8.0, 120.0, 385.0, 0.0) == pytest.approx(f * 8 * 120 / 1.2 / 1e3)


def test_tabela_8_6():
    e = espacamentos_parafusos(8.0)
    assert (e["a1_mm"], e["a2_mm"], e["a1_CG_mm"], e["a2_CG_mm"]) == (56, 40, 80, 32)


def test_ligacao_terca_viga(res):
    tv = res["res"]["ligacao_terca_viga"]
    assert tv["ok"] and tv["eta"] <= 0.75 + 1e-9
    assert tv["V_up_kN"] > 0
    c = tv["corrente"]
    assert c["geometria_ok"]
    # as duas extremidades de terça partilham a largura da viga
    meia_viga = res["geo"].b * 500
    assert c["a2_CG_viga_adotado_mm"] + c["x_p_mm"] + c["deslocamento_faces_mm"] \
        == pytest.approx(meia_viga)


def test_quadro_todos_atendidos(res):
    q = _quadro(res["res"], res["geo"])
    assert len(q) > 60
    falhas = [(r["ligacao"], r["grandeza"]) for r in q if not r["ok"]]
    assert not falhas, falhas


def test_quadro_detecta_chapa_L1_curta(res):
    """A chapa antiga (h0 − 1,5d = 964 mm) deixava e4 = 26 < 1,5·d0 = 36 mm."""
    r = {**res["res"], "esquadro_chapas": {**res["res"]["esquadro_chapas"]}}
    r["esquadro_chapas"]["L1"] = {**r["esquadro_chapas"]["L1"], "altura_mm": 964.0}
    q = _quadro(r, res["geo"])
    e4 = [x for x in q if x["ligacao"] == "L1" and x["grandeza"].startswith("$e_4$")][0]
    assert e4["adot"] == pytest.approx(26.0) and not e4["ok"]
