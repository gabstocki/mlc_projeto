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

Coeficiente de pressão adotado (NBR 6123:2023 §7.2.6)
  "Cada elemento de vedação deve ser calculado com cp = ±2,0."
  Cláusula confirmada à letra contra o texto da norma (BM-17). É um coeficiente
  LÍQUIDO, que já engloba as duas faces da cobertura isolada.

  NÃO se soma C_pi: pressão interna é conceito de edificação FECHADA, e esta
  cobertura é isolada — sobre suportes de reduzidas dimensões, com o vento a
  agir diretamente sobre as faces superior e inferior (§7.2).

  [Removido em F-18] Este cabeçalho descrevia antes uma rota por zonas de C_pe
  local (campo/borda/canto) da «Tab. 5» somada a um C_pi de §6.2.5. O código
  nunca fez isso, e a documentação de um método que não é o executado é uma
  armadilha para quem revir o memorial. Na :2023 a Tab. 5 é «Valores de altura
  de camada limite zg e de comprimento de rugosidade z0» — nada que ver.

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

# NBR 6123:2023 §7.2.6 — Elementos de vedação em coberturas isoladas:
# "Cada elemento de vedação deve ser calculado com cp = ±2,0."
# Coeficiente LÍQUIDO, já englobando as duas faces da cobertura isolada. Não se
# soma C_pi: pressão interna é conceito de edificação FECHADA (§6.3), que não
# se aplica a uma cobertura sobre suportes de reduzidas dimensões.
CP_VEDACAO_ISOLADA = 2.0

# Classe exigida para o vento local — §5.3.2 a): a Classe A abrange "unidades e
# sistemas de vedação e seus elementos de fixação". §5.3.3 recomenda ainda o S2
# do TOPO da edificação para o estudo dos elementos de vedação.
CLASSE_VEDACAO = "A"

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
    cp_vedacao:   float = CP_VEDACAO_ISOLADA,
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
        cp_vedacao   : |cp| do elemento de vedação — §7.2.6 exige 2,0
        gamma_Q      : coef. de ação variável (vento)
        gamma_G_fav  : coef. de permanente favorável (uplift)
        R_fix_k_kN   : resistência característica do fixador (ficha do fabricante)
        gamma_M_fix  : coef. de resistência do fixador

    Returns:
        dict com q, R_fix,d, o caso normativo de vedação, η e caveat.

    Raises:
        ValueError: se params_vento não for de Classe A (AUD-005).
    """
    if s_terca <= 0 or e_fix_m <= 0:
        raise ValueError("s_terca e e_fix_m devem ser > 0")

    # ── AUD-005 — vento LOCAL exige classe A ──────────────────────────────
    # O vento global da estrutura (classe B, dimensão frontal > 20 m) tem
    # intervalo de rajada de 5 s; elementos de vedação e suas fixações são
    # governados por rajadas de 3 s sobre área tributária pequena, e a norma
    # os classifica explicitamente na Classe A. Usar o q global subestima a
    # sucção local.
    if params_vento.classe != CLASSE_VEDACAO:
        raise ValueError(
            f"params_vento.classe='{params_vento.classe}': elementos de vedação "
            f"e seus elementos de fixação exigem a classe A "
            f"(NBR 6123:2023 §5.3.2 a)). O vento global da estrutura não serve "
            f"para a verificação local — construa um ParametrosVento com "
            f"classe='A' e a mesma altura de referência."
        )

    q = params_vento.q                       # kN/m² — S2 no topo (§5.3.3)
    R_fix_d = R_fix_k_kN / gamma_M_fix       # kN
    A_trib = s_terca * e_fix_m               # m² por fixador

    def _zona(nome: str, C_net: float) -> ZonaFixacao:
        w_suc_d = gamma_Q * abs(C_net) * q               # kN/m²
        w_up_d  = w_suc_d - gamma_G_fav * g_telha_kNm2   # kN/m² (peso alivia)
        w_up_d  = max(w_up_d, 0.0)
        F_fix   = w_up_d * A_trib                        # kN
        eta     = F_fix / R_fix_d if R_fix_d > 0 else 999.0
        # espaçamento máximo do fixador para η = 1 (mantendo s_terça)
        e_req   = (R_fix_d / (w_up_d * s_terca)) if w_up_d * s_terca > 0 else 1e9
        return ZonaFixacao(
            nome=nome, Cpe=C_net, C_net=round(C_net, 3),
            w_suc_d=round(w_suc_d, 4), w_up_d=round(w_up_d, 4),
            A_trib_m2=round(A_trib, 4), F_fix_d_kN=round(F_fix, 4),
            eta=round(eta, 4), ok=eta <= 1.0, e_fix_req_m=round(e_req, 3),
        )

    # §7.2.6: um único caso normativo — cada elemento com cp = ±2,0. A sucção
    # (−) governa o arrancamento do fixador. As antigas zonas campo/borda/canto
    # vinham da Tab. 5 de edificação fechada e não pertencem ao domínio de
    # cobertura isolada (AUD-005).
    zonas = {"vedacao": _zona("vedacao", -abs(cp_vedacao))}

    z_gov = max(zonas.values(), key=lambda z: z.eta)
    eta_gov = z_gov.eta

    return {
        # Entrada / vento
        "q_kNm2":        round(q, 4),
        "Vk_ms":         round(params_vento.Vk, 3),
        "classe_vento":  params_vento.classe,
        "z_ref_m":       round(params_vento.z_ref, 3),
        "cp_vedacao":    cp_vedacao,
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
        # Recomendação de espaçamento (η ≤ 1)
        "e_fix_req_m":   zonas["vedacao"].e_fix_req_m,
        # Rastreabilidade
        "caveat": (
            "R_fix,k TÍPICO (2,5 kN) — confirmar na ficha técnica da telha; "
            "governa pull-over da chapa fina, não pull-out na madeira."
        ),
        "norma": (
            "NBR 6123:2023 §7.2.6 (cp=±2,0 por elemento de vedação) + "
            "§5.3.2 a)/§5.3.3 (classe A, S2 no topo) | "
            "EN 1995 §8.7.2/ETA do fixador (γ_M=1,3)"
        ),
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
