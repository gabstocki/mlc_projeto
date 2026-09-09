"""
core/materials.py — Propriedades e resistências de cálculo do glulam.

Referência:
    EN 14080:2013 §5.1.6, Tabela 5 (MLC homogéneo — GLxxh)
    EC5 §2.4.1, Tab. 2.3, Tab. 3.1, Tab. 3.2
    EC5 §6.1.7 (k_cr — A1:2008)

IMPORTANTE (issue 8): a antiga EN 1194:1999 foi REVOGADA e substituída pela
EN 14080:2013. Os módulos e resistências abaixo são os da EN 14080:2013 Tab. 5;
NÃO usar os valores da EN 1194:1999 (que ainda circulam em muitas fontes e
diferem, p.ex. GL24h: E0,mean=11600, E0,05=9400, G=720 na EN 1194 vs
11500/9600/650 na EN 14080). Ver nota de rastreabilidade ao fim deste bloco.
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Propriedades características EN 14080:2013 §5.1.6 Tab. 5 (homogéneo) ────────
# Fonte: EN 14080:2013 Table 5 — "Characteristic strength and stiffness
# properties in N/mm² and densities in kg/m³ for homogeneous glulam".
# Constantes p/ todas as classes homogéneas (Tab. 5): f_t90,k=0,5; f_c90,k=2,5;
# f_v,k=3,5 (corte/torção); E90,mean=300; G_mean=650; G_05=540 (N/mm²).
# Unidades aqui: resistências e módulos em Pa; ρ em kg/m³.
_PROPS: dict[str, dict] = {
    "GL20h": dict(
        f_m_k=20e6, f_t0_k=16.0e6, f_c0_k=20.0e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=8400e6, E0_05=7000e6, G_mean=650e6,
        rho_k=340, rho_mean=370,
    ),
    "GL24h": dict(
        f_m_k=24e6, f_t0_k=19.2e6, f_c0_k=24.0e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=11500e6, E0_05=9600e6, G_mean=650e6,
        rho_k=385, rho_mean=420,
    ),
    "GL28h": dict(
        f_m_k=28e6, f_t0_k=22.3e6, f_c0_k=28.0e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=12600e6, E0_05=10500e6, G_mean=650e6,
        rho_k=425, rho_mean=460,
    ),
    "GL32h": dict(
        f_m_k=32e6, f_t0_k=25.6e6, f_c0_k=32.0e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=14200e6, E0_05=11800e6, G_mean=650e6,
        rho_k=440, rho_mean=490,
    ),
}

# ── Rastreabilidade (issue 8) — EN 14080:2013 Tab. 5 vs EN 1194:1999 (revogada)
# Valores CORRIGIDOS para a EN 14080:2013 (os antigos, entre parênteses, eram da
# EN 1194:1999 e estavam no código):
#   GL20h: G_mean 650 (era 540, que é o G_05 da EN 14080)
#   GL24h: E0,mean 11500 (11600) | E0,05 9600 (9400) | G_mean 650 (720)
#   GL28h: E0,05 10500 (10200) | G_mean 650 (780) | f_c0,k 28,0 (26,5)
#          ρ_k 425 (410) | ρ_mean 460 (450)
#   GL32h: E0,05 11800 (11600) | G_mean 650 (850) | f_c0,k 32,0 (29,0)
#          ρ_mean 490 (480)
# f_v,k, f_t90,k, f_c90,k e ρ (parcial) já estavam conforme a EN 14080:2013.

# k_mod — EC5 Tabela 3.1 (glulam)
# chave: (classe_servico, duracao)
#
# Vento (EC5 §2.3.1.2): a ação do vento pode ser enquadrada em duração
# «curta» ou «instantânea». Neste projeto adota-se «curta» (conservador):
#   CS1/CS2: k_mod = 0,90  (instantânea permitiria 1,10)
#   CS3:     k_mod = 0,70  (instantânea permitiria 0,90)
_KMOD: dict[tuple, float] = {
    (1, "permanente"): 0.60, (1, "longa"): 0.70, (1, "media"): 0.80,
    (1, "curta"):      0.90, (1, "instantanea"): 1.10,
    (2, "permanente"): 0.60, (2, "longa"): 0.70, (2, "media"): 0.80,
    (2, "curta"):      0.90, (2, "instantanea"): 1.10,
    (3, "permanente"): 0.50, (3, "longa"): 0.55, (3, "media"): 0.65,
    (3, "curta"):      0.70, (3, "instantanea"): 0.90,
}

# k_def — EC5 Tabela 3.2 (glulam)
_KDEF: dict[int, float] = {1: 0.60, 2: 0.80, 3: 2.00}

# EC5 Tab. 2.3
GAMMA_M = 1.25          # material glulam (peças)
GAMMA_M_LIGACAO = 1.30  # ligações (EC5 Tab. 2.3)

# EC5 §6.1.7 (A1:2008) — fator de fissuração
# b_ef = k_cr · b
# k_cr = 0,67 para madeira maciça e glulam; 1,0 para LVL
K_CR_GLULAM = 0.67


@dataclass
class GlulamMaterial:
    """
    Propriedades de cálculo do glulam para uma combinação
    de classe resistente e classe de serviço.

    Args:
        classe         : Classe resistente (ex: "GL24h")
        classe_servico : Classe de serviço 1, 2 ou 3 (EC5 §2.3.1.3)
        duracao        : Duração do carregamento dominante (EC5 §3.1.3)
    """
    classe:         str
    classe_servico: int
    duracao:        str = "media"

    def __post_init__(self) -> None:
        if self.classe not in _PROPS:
            raise ValueError(
                f"Classe '{self.classe}' não reconhecida. "
                f"Opções: {list(_PROPS)}"
            )
        key = (self.classe_servico, self.duracao)
        if key not in _KMOD:
            raise ValueError(
                f"Combinação classe_servico={self.classe_servico}, "
                f"duracao='{self.duracao}' inválida. "
                f"Durações: permanente, longa, media, curta, instantanea."
            )
        self._p = _PROPS[self.classe]

    def com_duracao(self, duracao: str) -> "GlulamMaterial":
        """
        Novo material com a mesma classe, mas duração (e k_mod) da
        combinação de ações — EC5 §3.1.3.
        """
        return GlulamMaterial(
            classe=self.classe,
            classe_servico=self.classe_servico,
            duracao=duracao,
        )

    # ── Propriedades características ──────────────────────────
    @property
    def f_m_k(self)   -> float: return self._p["f_m_k"]
    @property
    def f_t0_k(self)  -> float: return self._p["f_t0_k"]
    @property
    def f_c0_k(self)  -> float: return self._p["f_c0_k"]
    @property
    def f_v_k(self)   -> float: return self._p["f_v_k"]
    @property
    def f_t90_k(self) -> float: return self._p["f_t90_k"]
    @property
    def f_c90_k(self) -> float: return self._p["f_c90_k"]
    @property
    def E0_mean(self) -> float: return self._p["E0_mean"]
    @property
    def E0_05(self)   -> float: return self._p["E0_05"]
    @property
    def G_mean(self)  -> float: return self._p["G_mean"]
    @property
    def rho_k(self)    -> float: return self._p["rho_k"]
    @property
    def rho_mean(self) -> float: return self._p["rho_mean"]

    @property
    def G_g_05(self) -> float:
        """
        G_g,05 — módulo de distorção característico, EN 14080:2013 Tab. 5.

        Constante para todas as classes homogéneas: 540 N/mm².

        Achado [F-16]
        -------------
        Existia aqui uma propriedade `G_05 = E_0,05/16` (≈ 600 MPa para GL24h)
        que NÃO é uma propriedade do material: é a relação implícita de que o
        EC5 se serve para deduzir a forma SIMPLIFICADA da Eq. (6.32) a partir
        da geral (6.31), com I_tor ≈ h·b³/3. Nunca era consumida — mas era um
        valor 11 % acima do tabelado, com o nome de uma propriedade tabelada,
        a uma chamada de distância de entrar num cálculo.

        Quem quiser usar a Eq. (6.31) geral deve passar ESTE valor; a Eq.
        (6.32) simplificada não precisa de nenhum (a relação está lá dentro).
        """
        return 540e6

    # ── Coeficientes ──────────────────────────────────────────
    @property
    def k_mod(self) -> float:
        """EC5 Tabela 3.1"""
        return _KMOD[(self.classe_servico, self.duracao)]

    @property
    def k_def(self) -> float:
        """EC5 Tabela 3.2"""
        return _KDEF[self.classe_servico]

    @property
    def k_cr(self) -> float:
        """EC5 §6.1.7 — glulam: k_cr = 0,67"""
        return K_CR_GLULAM

    # ── Resistências de cálculo (EC5 §2.4.1) ─────────────────
    @property
    def f_m_d(self)   -> float: return self.k_mod * self.f_m_k   / GAMMA_M
    @property
    def f_t0_d(self)  -> float: return self.k_mod * self.f_t0_k  / GAMMA_M
    @property
    def f_c0_d(self)  -> float: return self.k_mod * self.f_c0_k  / GAMMA_M
    @property
    def f_v_d(self)   -> float: return self.k_mod * self.f_v_k   / GAMMA_M
    @property
    def f_t90_d(self) -> float: return self.k_mod * self.f_t90_k / GAMMA_M
    @property
    def f_c90_d(self) -> float: return self.k_mod * self.f_c90_k / GAMMA_M
