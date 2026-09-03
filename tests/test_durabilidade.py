"""Issue 30 — Declarações de durabilidade coerentes com a CS3.

EN 335 (classe de uso), EN 301 (adesivo) e tratamento preservativo, declarados
no main.DURABILIDADE e coerentes com a Classe de Serviço 3 adotada.
"""

from mlc_projeto.main import DURABILIDADE


def test_classe_servico_3():
    assert DURABILIDADE["classe_servico_ec5"] == 3


def test_classe_uso_en335_coerente_cs3():
    """CS3 (EC5) mapeia em classe de uso EN 335 = 3 (exterior acima do solo)."""
    assert DURABILIDADE["classe_uso_en335"].startswith("3")


def test_adesivo_tipo_I():
    """CS3 exige adesivo Tipo I (EN 14080 §5.3 / EN 301)."""
    assert DURABILIDADE["adesivo_en301"] == "Tipo I"


def test_tratamento_declarado_com_norma_e_detalhamento():
    trat = DURABILIDADE["tratamento"].lower()
    assert "en 351" in trat
    assert "detalhamento" in trat or "drenagem" in trat


def test_durabilidade_natural_exige_tratamento():
    """Conífera de baixa durabilidade (EN 350 classe 4) → tratamento p/ UC3."""
    assert "4" in DURABILIDADE["durab_natural_en350"]
    assert "conífera" in DURABILIDADE["especie"].lower()
