"""Issue 63 — figuras esquemáticas: variáveis da varredura, pórtico e apoio horizontal."""
from mlc_projeto.core.geometry import GeometriaViga
from mlc_projeto.output.esquemas import gerar_esquemas


def test_gera_os_tres_esquemas(tmp_path):
    geo = GeometriaViga(L=20.25, h0=1.0, alpha_deg=10.0, b=0.32)
    paths = gerar_esquemas(geo, tmp_path, H_pilar=7.0, faixas="varredura")
    assert [p.name for p in paths] == ["esq01_variaveis_viga.pdf",
                                       "esq02_modelo_portico.pdf",
                                       "esq03_apoio_horizontal.pdf"]
    for p in paths:
        assert p.read_bytes()[:4] == b"%PDF" and p.stat().st_size > 5000
