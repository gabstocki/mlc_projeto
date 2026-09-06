"""
checks/elu/fixacao_telha.py — Fixação telha→terça sob sucção (issue 17).

Verificação LOCAL da fixação da telha metálica trapezoidal às terças contra
o arrancamento por sucção de vento (NBR 6123). É uma verificação de elemento
secundário, independente do modelo global do pórtico.

Cadeia
------
  Sucção de vento (NBR 6123)  →  fixador (parafuso autoperfurante + arruela)
       →  terça MLC  →  viga principal

Metodologia (NBR 6123)
----------------------
  Pressão de sucção líquida na cobertura, por zona:

      C_net = C_pe,local − C_pi              (uplift: C_net < 0)
      w_suc,d = γ_Q · |C_net| · q            (kN/m²)
      w_up,d  = w_suc,d − γ_G,fav · g_telha  (peso da telha alivia)

  Força de arrancamento por fixador (área tributária = s_terça × e_fix):

      F_fix,d = w_up,d · (s_terça · e_fix)

  Verificação:  η = F_fix,d / R_fix,d ≤ 1,  R_fix,d = R_fix,k / γ_M

Zonas de C_pe local (NBR 6123 Tab. 5 — telhado a duas águas, baixa inclinação):
  · campo (geral) : C_pe ≈ −1,0
  · borda         : C_pe ≈ −1,5
  · canto/beiral  : C_pe ≈ −2,0   (sucções locais mais severas)

Pressão interna C_pi (NBR 6123 §6.2.5):
  O galpão é ABERTO nas laterais (estacionamento coberto). Com o vento
  entrando pela face aberta, o interior é pressurizado (abertura dominante):
  C_pi = +0,8 — que SOMA ao uplift (empurra a cobertura de baixo para cima).
  É o cenário conservador de arrancamento.

CAVEAT (dado do fabricante — issue 17)
--------------------------------------
  R_fix,k é a resistência característica ao arrancamento do CONJUNTO fixador
  (parafuso autoperfurante Ø6,3 mm com arruela de vedação EPDM sobre chapa
  fina): governa em geral o *pull-over* (a cabeça/arruela atravessa a chapa),
  não o *pull-out* da rosca na madeira (alto em MLC). O valor default (2,5 kN)
  é TÍPICO de catálogo — **confirmar na ficha técnica da telha adotada** e
  substituir. A metodologia e o resultado (espaçamento de fixadores exigido
  por zona) permanecem válidos com o R_fix,k real.

Referência: ABNT NBR 6123 — edição única adotada no projeto: **2023**.
            EN 1995-1-1 §8.7.2 / ETA do fixador (R_fix,k, γ_M=1,3).

ATENÇÃO — AUD-005/AUD-016 (auditoria técnica independente): os coeficientes
locais e o C_pi aqui implementados foram transcritos da edição de **1988**
(§6.2.5 + Tab. 5), enquanto o núcleo declara a edição de 2023. O mapeamento de
itens/tabelas para a edição vigente, o requisito de classe A para elementos de
vedação e a regra cp=±2,0 para cobertura isolada dependem do texto normativo
controlado, ainda não disponível no projeto (Onda 2 do plano de correção).
Enquanto isso, os resultados deste módulo são **NÃO VALIDADOS** — a numeração
de itens da edição anterior foi removida em vez de ser renumerada às cegas.
"""

from __future__ import annotations

from dataclasses import dataclass

from mlc_projeto.core.wind import ParametrosVento


# ── Coeficientes e fatores default (NBR 6123 + EN 1990/EN 1995) ───────────────

CPE_CAMPO = -1.0    # C_pe local — campo geral da cobertura (Tab. 5)
CPE_BORDA = -1.5    # C_pe local — faixa de borda
CPE_CANTO = -2.0    # C_pe local — canto / beiral (sucção máxima)
CPI_ABERTO = 0.8    # C_pi — galpão aberto/abertura dominante (§6.2.5)

GAMMA_Q_VENTO = 1.5   # EN 1990 (coerência com as combinações do modelo)
GAMMA_G_FAV   = 0.9   # permanente favorável (alívio no uplift; EN 1990)
GAMMA_M_FIX   = 1.3   # ligação aço-madeira / ETA do fixador (EN 1995)

R_FIX_K_KN_TIPICO = 2.5   # kN — resistência TÍPICA do fixador (confirmar ficha)


@dataclass(frozen=True)
class ZonaFixacao:
    """Resultado da fixação numa zona de C_pe local."""
    nome:       str
    Cpe:        float
    C_net:      float
    w_suc_d:    float     # kN/m² — sucção de cálculo (γ_Q·|C_net|·q)
    w_up_d:     float     # kN/m² — uplift líquido (desconta peso da telha)
    A_trib_m2:  float
    F_fix_d_kN: float
    eta:        float
    ok:         bool
    e_fix_req_m: float    # espaçamento máx. de fixador p/ η=1 nesta zona


def verificar_fixacao_telha_succao(
    params_vento: ParametrosVento,
    s_terca:      float,
    g_telha_kNm2: float = 0.10,
    e_fix_m:      float = 0.33,
    Cpe_campo:    float = CPE_CAMPO,
    Cpe_borda:    float = CPE_BORDA,
    Cpe_canto:    float = CPE_CANTO,
    Cpi:          float = CPI_ABERTO,
    gamma_Q:      float = GAMMA_Q_VENTO,
    gamma_G_fav:  float = GAMMA_G_FAV,
    R_fix_k_kN:   float = R_FIX_K_KN_TIPICO,
    gamma_M_fix:  float = GAMMA_M_FIX,
) -> dict:
    """
    Verifica a fixação telha→terça ao arrancamento por sucção (NBR 6123).

    Args:
        params_vento : ParametrosVento (fornece q — pressão dinâmica)
        s_terca      : espaçamento entre terças (m) = largura tributária ⊥
        g_telha_kNm2 : peso próprio da telha (kN/m²) — alívio favorável
        e_fix_m      : espaçamento dos fixadores ao longo da terça (m)
        Cpe_*        : C_pe local por zona (NBR 6123 Tab. 5)
        Cpi          : pressão interna (§6.2.5) — positivo soma ao uplift
        gamma_Q      : coef. de ação variável (vento)
        gamma_G_fav  : coef. de permanente favorável (uplift)
        R_fix_k_kN   : resistência característica do fixador (ficha do fabricante)
        gamma_M_fix  : coef. de resistência do fixador

    Returns:
        dict com q, R_fix,d, zonas (campo/borda/canto), η governante e caveat.
    """
    if s_terca <= 0 or e_fix_m <= 0:
        raise ValueError("s_terca e e_fix_m devem ser > 0")

    q = params_vento.q                       # kN/m²
    R_fix_d = R_fix_k_kN / gamma_M_fix       # kN
    A_trib = s_terca * e_fix_m               # m² por fixador

    def _zona(nome: str, Cpe: float) -> ZonaFixacao:
        C_net   = Cpe - Cpi                              # < 0 (uplift)
        w_suc_d = gamma_Q * abs(C_net) * q               # kN/m²
        w_up_d  = w_suc_d - gamma_G_fav * g_telha_kNm2   # kN/m² (peso alivia)
        w_up_d  = max(w_up_d, 0.0)
        F_fix   = w_up_d * A_trib                        # kN
        eta     = F_fix / R_fix_d if R_fix_d > 0 else 999.0
        # espaçamento máximo do fixador para η = 1 (mantendo s_terça)
        e_req   = (R_fix_d / (w_up_d * s_terca)) if w_up_d * s_terca > 0 else 1e9
        return ZonaFixacao(
            nome=nome, Cpe=Cpe, C_net=round(C_net, 3),
            w_suc_d=round(w_suc_d, 4), w_up_d=round(w_up_d, 4),
            A_trib_m2=round(A_trib, 4), F_fix_d_kN=round(F_fix, 4),
            eta=round(eta, 4), ok=eta <= 1.0, e_fix_req_m=round(e_req, 3),
        )

    zonas = {
        "campo": _zona("campo",  Cpe_campo),
        "borda": _zona("borda",  Cpe_borda),
        "canto": _zona("canto",  Cpe_canto),
    }

    z_gov = max(zonas.values(), key=lambda z: z.eta)
    eta_gov = z_gov.eta

    return {
        # Entrada / vento
        "q_kNm2":        round(q, 4),
        "Vk_ms":         round(params_vento.Vk, 3),
        "Cpi":           Cpi,
        "s_terca_m":     s_terca,
        "e_fix_m":       e_fix_m,
        "g_telha_kNm2":  g_telha_kNm2,
        # Fixador
        "R_fix_k_kN":    R_fix_k_kN,
        "gamma_M_fix":   gamma_M_fix,
        "R_fix_d_kN":    round(R_fix_d, 4),
        "A_trib_m2":     round(A_trib, 4),
        # Zonas
        "zonas": {
            k: {
                "Cpe": z.Cpe, "C_net": z.C_net,
                "w_suc_d_kNm2": z.w_suc_d, "w_up_d_kNm2": z.w_up_d,
                "F_fix_d_kN": z.F_fix_d_kN, "eta": z.eta, "ok": z.ok,
                "e_fix_req_m": z.e_fix_req_m,
            }
            for k, z in zonas.items()
        },
        # Governante
        "zona_gov":      z_gov.nome,
        "F_fix_d_kN":    z_gov.F_fix_d_kN,
        "eta":           round(eta_gov, 4),
        "ok":            eta_gov <= 1.0,
        # Recomendação de espaçamento por zona (η ≤ 1)
        "e_fix_req_campo_m": zonas["campo"].e_fix_req_m,
        "e_fix_req_borda_m": zonas["borda"].e_fix_req_m,
        "e_fix_req_canto_m": zonas["canto"].e_fix_req_m,
        # Rastreabilidade
        "caveat": (
            "R_fix,k TÍPICO (2,5 kN) — confirmar na ficha técnica da telha; "
            "governa pull-over da chapa fina, não pull-out na madeira."
        ),
        "norma": "NBR 6123 §6.2.5 + Tab.5 (local) | EN 1995 §8.7.2/ETA (γ_M=1,3)",
    }


def relatorio(res: dict) -> None:
    """Imprime relatório legível da fixação telha-terça sob sucção."""
    print("=" * 72)
    print("  FIXAÇÃO TELHA→TERÇA SOB SUCÇÃO — NBR 6123 (verificação local)")
    print("=" * 72)
    print(f"  q = {res['q_kNm2']:.4f} kN/m²  (Vk={res['Vk_ms']:.1f} m/s) | "
          f"C_pi = +{res['Cpi']:.1f} (galpão aberto §6.2.5)")
    print(f"  Fixador: R_fix,k = {res['R_fix_k_kN']:.2f} kN (típico) / "
          f"γ_M={res['gamma_M_fix']:.2f} → R_fix,d = {res['R_fix_d_kN']:.3f} kN")
    print(f"  Tributária: s_terça={res['s_terca_m']:.2f} m × "
          f"e_fix={res['e_fix_m']:.2f} m = {res['A_trib_m2']:.3f} m²/fixador")
    print(f"  {'-'*68}")
    print(f"  {'Zona':<8} {'C_pe':>6} {'C_net':>7} {'w_up,d':>9} "
          f"{'F_fix,d':>9} {'η':>7} {'e_fix req':>10}  St")
    for k in ("campo", "borda", "canto"):
        z = res["zonas"][k]
        st = "✓" if z["ok"] else "✗"
        print(f"  {k:<8} {z['Cpe']:>6.1f} {z['C_net']:>7.2f} "
              f"{z['w_up_d_kNm2']:>7.3f}kN/m² {z['F_fix_d_kN']:>7.3f}kN "
              f"{z['eta']:>7.4f} {z['e_fix_req_m']:>8.3f}m  {st}")
    print(f"  {'-'*68}")
    print(f"  η governante = {res['eta']:.4f} (zona {res['zona_gov']}) → "
          f"{'APROVADO' if res['ok'] else 'REPROVADO'} para e_fix={res['e_fix_m']:.2f} m")
    print(f"  Espaçamento máx. de fixador p/ η≤1: campo="
          f"{res['e_fix_req_campo_m']:.2f} m | borda={res['e_fix_req_borda_m']:.2f} m | "
          f"canto={res['e_fix_req_canto_m']:.2f} m")
    print(f"  ⚠ {res['caveat']}")
    print("=" * 72)


if __name__ == "__main__":
    pv = ParametrosVento(
        V0=45.0, S1=1.0, categoria="IV", classe="B", S3=1.0,
        L=20.25, H1=1.785, h=7.0, dist_portico=5.75,
    )
    res = verificar_fixacao_telha_succao(pv, s_terca=2.53, g_telha_kNm2=0.10, e_fix_m=0.33)
    relatorio(res)
