"""
core/materials.py — Propriedades e resistências de cálculo do glulam.

Referência:
    EN 14080:2013 Tabela 1 (homogéneo)
    EC5 §2.4.1, Tab. 2.3, Tab. 3.1, Tab. 3.2
    EC5 §6.1.7 (k_cr — A1:2008)
"""

from __future__ import annotations

from dataclasses import dataclass


# ── Propriedades características EN 14080:2013 Tab. 1 (homogéneo) ──────────
# Unidades: resistências e módulos em Pa; ρ_k em kg/m³
_PROPS: dict[str, dict] = {
    "GL20h": dict(
        f_m_k=20e6, f_t0_k=16.0e6, f_c0_k=20.0e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=8400e6, E0_05=7000e6, G_mean=540e6,
        rho_k=340, rho_mean=370,
    ),
    "GL24h": dict(
        f_m_k=24e6, f_t0_k=19.2e6, f_c0_k=24.0e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=11600e6, E0_05=9400e6, G_mean=720e6,
        rho_k=385, rho_mean=420,
    ),
    "GL28h": dict(
        f_m_k=28e6, f_t0_k=22.3e6, f_c0_k=26.5e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=12600e6, E0_05=10200e6, G_mean=780e6,
        rho_k=410, rho_mean=450,
    ),
    "GL32h": dict(
        f_m_k=32e6, f_t0_k=25.6e6, f_c0_k=29.0e6, f_v_k=3.5e6,
        f_t90_k=0.5e6, f_c90_k=2.5e6,
        E0_mean=14200e6, E0_05=11600e6, G_mean=850e6,
        rho_k=440, rho_mean=480,
    ),
}

# k_mod — EC5 Tabela 3.1 (glulam)
# chave: (classe_servico, duracao)
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
    def G_05(self) -> float:
        """
        G_0,05 — relação implícita em EC5 §6.3.3(2) para coníferas:
        a fórmula simplificada (6.32) decorre de G_0,05 = E_0,05 / 16
        na formulação geral (6.31) com I_tor ≈ h·b³/3.
        """
        return self.E0_05 / 16.0

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
