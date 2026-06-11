"""
core/materials.py — Propriedades e resistências de cálculo do glulam.

Referência: EN 14080 Tabela 1 + EC5 §2.4.1 + EC5 Tabela 3.1
"""

from dataclasses import dataclass


# ── Propriedades características (EN 14080 Tab. 1) — valores em Pa e N/m² ──
_PROPS: dict[str, dict] = {
    "GL20h": dict(f_m_k=20e6, f_t0_k=15e6, f_c0_k=20e6, f_v_k=3.5e6,
                  f_t90_k=0.5e6, f_c90_k=2.5e6,
                  E0_mean=8400e6, E0_05=7000e6, G_mean=540e6, rho_k=340),
    "GL24h": dict(f_m_k=24e6, f_t0_k=16.5e6, f_c0_k=24e6, f_v_k=3.5e6,
                  f_t90_k=0.5e6, f_c90_k=2.5e6,
                  E0_mean=11500e6, E0_05=9600e6, G_mean=720e6, rho_k=385),
    "GL28h": dict(f_m_k=28e6, f_t0_k=19.5e6, f_c0_k=26.5e6, f_v_k=3.5e6,
                  f_t90_k=0.5e6, f_c90_k=2.5e6,
                  E0_mean=12600e6, E0_05=10500e6, G_mean=780e6, rho_k=410),
    "GL32h": dict(f_m_k=32e6, f_t0_k=22.5e6, f_c0_k=29e6, f_v_k=3.5e6,
                  f_t90_k=0.5e6, f_c90_k=2.5e6,
                  E0_mean=13700e6, E0_05=11400e6, G_mean=850e6, rho_k=430),
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

GAMMA_M = 1.25  # EC5 Tab. 2.3


@dataclass
class GlulamMaterial:
    """
    Propriedades de cálculo do glulam para uma combinação
    de classe resistente e classe de serviço.

    Args:
        classe         : Classe resistente (ex: "GL28h")
        classe_servico : Classe de serviço 1, 2 ou 3 (EC5 §2.3.1.3)
        duracao        : Duração do carregamento dominante
    """
    classe:         str
    classe_servico: int
    duracao:        str = "media"

    def __post_init__(self) -> None:
        if self.classe not in _PROPS:
            raise ValueError(f"Classe '{self.classe}' não reconhecida. "
                             f"Opções: {list(_PROPS)}")
        self._p = _PROPS[self.classe]

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

    # ── Coeficientes ──────────────────────────────────────────
    @property
    def k_mod(self) -> float:
        """EC5 Tabela 3.1"""
        return _KMOD[(self.classe_servico, self.duracao)]

    @property
    def k_def(self) -> float:
        """EC5 Tabela 3.2"""
        return _KDEF[self.classe_servico]

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
