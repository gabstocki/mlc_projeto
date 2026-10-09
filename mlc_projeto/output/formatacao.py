"""
output/formatacao.py — Formatador único de números apresentados (issue 53).

Os dados de entrada têm dois a três algarismos significativos (q_k = 0,40
kN/m², γ_G = 1,35); o cálculo não aumenta essa precisão. Convenção adotada em
todo o memorial (console, relatório, Excel e tese):

  · taxa de utilização η — duas casas decimais, arredondada SEMPRE PARA CIMA,
    para que a taxa exibida nunca seja menor que a calculada (0,7492 → 0,75;
    1,0001 → 1,01): um valor que reprova nunca aparece como aprovado;
  · forças, momentos e tensões — três algarismos significativos, com
    arredondamento usual (504,26 → 504; 99,61 → 99,6; 8,748 → 8,75).

Os valores guardados nos resultados mantêm a precisão completa; só a
apresentação é arredondada.
"""

from __future__ import annotations

import math
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal


def eta_exibido(eta: float) -> float:
    """η arredondado para cima com duas casas (valor numérico)."""
    # str(round(·, 9)) elimina o ruído binário (0,85 não vira 0,86)
    d = Decimal(str(round(float(eta), 9)))
    return float(d.quantize(Decimal("0.01"), rounding=ROUND_CEILING))


def sig(x: float, n: int = 3) -> float:
    """x com n algarismos significativos (arredondamento usual)."""
    x = float(x)
    if x == 0.0 or not math.isfinite(x):
        return x
    e = math.floor(math.log10(abs(x)))
    q = Decimal(1).scaleb(e - n + 1)
    return float(Decimal(str(x)).quantize(q, rounding=ROUND_HALF_UP))


def _casas_sig(x: float, n: int) -> int:
    if x == 0.0 or not math.isfinite(x):
        return 0
    return max(0, n - 1 - math.floor(math.log10(abs(x))))


def _pt(s: str) -> str:
    """'1,234.5' (formato en) → '1.234,5' (pt-BR)."""
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_eta(eta: float, decimal: str = ",") -> str:
    """η como texto: '0,85' (ou '0.85' com decimal='.')."""
    s = f"{eta_exibido(eta):.2f}"
    return s if decimal == "." else s.replace(".", ",")


def fmt_sig(x: float, n: int = 3, decimal: str = ",", milhar: bool = True,
            zeros: bool = False) -> str:
    """
    Grandeza com n algarismos significativos: '504', '99,6', '8,75', '1.020'.

    Por omissão os zeros finais da parte decimal são omitidos (0,32 e não
    0,320; 2,5 e não 2,50), para não atribuir a um dado precisão que ele não
    tem; `zeros=True` os mantém.
    """
    v = sig(x, n)
    casas = _casas_sig(v if v else x, n)
    s = f"{v:,.{casas}f}" if milhar else f"{v:.{casas}f}"
    if not zeros and "." in s:
        s = s.rstrip("0").rstrip(".")
    return s if decimal == "." else _pt(s)
