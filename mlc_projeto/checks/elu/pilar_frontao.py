"""
checks/elu/pilar_frontao.py — Pilar de frontão PF (issue 52).

O painel de contraventamento transversal (CV-T) foi dimensionado com largura de
baía igual ao espaçamento entre pórticos (5,75 m), mas no plano do frontão os
pilares do pórtico estão a 0; 20,25 e 40,5 m: não havia montante a 5,75 m do
canto. O desenho cotado tornou isso visível. Acrescenta-se em cada frontão um
PILAR DE FRONTÃO (PF), a 5,75 m do canto, que é o segundo montante da cruz.

O PF NÃO apoia a viga: a ligação de topo (L1f) tem furos oblongos verticais na
chapa embutida, de modo que transmite só a força horizontal no plano do frontão
(a reação do diafragma que a viga, como escora, conduz ao painel) e deixa a
viga fletir livremente. O PF recebe, portanto:

  · peso próprio;
  · o download/arrancamento da cruz, D = V·tanβ (como o pilar de canto);
  · o vento sobre a própria face (momento, como os demais pilares).

E a base (L3f), o cortante do painel H_base mais metade do arrasto do pilar,
o arrancamento líquido e, na situação acidental, o choque de veículo.

Referências: EN 1995-1-1 §6.2.3, §6.3.2, §8.2.3, §8.5.1.1, Anexo A;
             EN 1993-1-8 Tab. 3.4; EN 1992-4:2018; EN 1990 §6.4.3.
"""

from __future__ import annotations

from mlc_projeto.checks.elu.no_contraventamento import dimensionar_ligacao_axial_escora
from mlc_projeto.checks.elu.pilares import verifica_pilar_contraventado
from mlc_projeto.connections.ancoragem import verificar_base_corrente
from mlc_projeto.core.materials import GlulamMaterial

GAMMA_G_SUP = 1.35
GAMMA_G_INF = 0.90      # mesma parcela favorável da combinação de sucção


def verificar_pilar_frontao(
    *,
    mat:            GlulamMaterial,
    b_m:            float,
    h_m:            float,
    H_m:            float,
    gamma_kNm3:     float,
    download_kN:    float,
    H_base_kN:      float,
    M_vento_kNm:    float,
    V_vento_base_kN: float,
    V_acidental_kN: float,
    b_viga_m:       float,
    h_chapa_topo_m: float = 0.40,
    h_pilarete_m:   float = 0.0,
    chaveta:        dict | None = None,
    d_cavilha_mm:   float = 20.0,
    n_chumbadores:  int = 4,
    d_chumbador_mm: int = 24,
    classe_chumbador: str = "8.8",
    dados_concreto: dict | None = None,
) -> dict:
    """
    Verifica o pilar de frontão (montante), a ligação de topo à viga (L1f) e a
    base (L3f). O η do conjunto é o maior dos três.

    Args:
        mat             : material (k_mod da duração adotada para os montantes)
        b_m, h_m, H_m   : seção (h no plano do frontão) e altura do pilar (m)
        gamma_kNm3      : peso específico da MLC (kN/m³)
        download_kN     : D = V_painel·tanβ da cruz do frontão (kN, de cálculo)
        H_base_kN       : cortante do painel na base (kN, de cálculo)
        M_vento_kNm     : momento de vento na face do pilar (kN·m, de cálculo)
        V_vento_base_kN : parcela do arrasto do pilar que vai à base (kN)
        V_acidental_kN  : cortante na base sob choque de veículo (kN)
        b_viga_m        : largura da viga onde se embute a chapa de topo (m)
        h_chapa_topo_m  : altura disponível da chapa embutida na viga (m)
    """
    G_k = gamma_kNm3 * b_m * h_m * H_m                     # kN — peso próprio
    montante = verifica_pilar_contraventado(
        mat=mat, b=b_m, h=h_m, H_pilar=H_m,
        N_grav_comp_kN=GAMMA_G_SUP * G_k,
        N_grav_uplift_kN=GAMMA_G_INF * G_k,
        downloads_kN=[float(download_kN)], eixo="min",
        M_vento_kNm=float(M_vento_kNm),
    )
    # Topo (L1f): força HORIZONTAL do painel, paralela às fibras da viga.
    # Furos oblongos verticais → a cavilha não recebe força vertical.
    topo = dimensionar_ligacao_axial_escora(
        F_Ed_kN=float(H_base_kN), mat=mat, b_m=b_viga_m, h_m=h_chapa_topo_m,
        d_mm=d_cavilha_mm, rotulo="L1f — topo do pilar de frontão",
    )
    # Base (L3f): sem chaveta, como L3; o cortante do painel vai aos chumbadores.
    base = verificar_base_corrente(
        rotulo="L3f — base do pilar de frontão",
        N_t_persistente_kN=float(montante["N_ancoragem_kN"]),
        V_persistente_kN=float(H_base_kN) + float(V_vento_base_kN),
        V_acidental_kN=float(V_acidental_kN),
        n_chumbadores=n_chumbadores, d_mm=d_chumbador_mm,
        classe=classe_chumbador, layout=(2, 2), dados_concreto=dados_concreto,
        # só o cortante do próprio pilar flete o pilarete (issue 87)
        M_persistente_kNm=float(V_vento_base_kN) * h_pilarete_m,
        M_acidental_kNm=float(V_acidental_kN) * h_pilarete_m,
        chaveta=chaveta,                        # issue 74
    )
    partes = {"montante": montante["eta"], "L1f": topo["eta"], "L3f": base["eta"]}
    gov = max(partes, key=partes.get)
    return {
        "G_k_kN":        round(G_k, 3),
        "download_kN":   round(float(download_kN), 3),
        "H_base_kN":     round(float(H_base_kN), 3),
        "montante":      montante,
        "topo":          topo,
        "base":          base,
        "eta_montante":  montante["eta"],
        "eta_topo":      topo["eta"],
        "eta_base":      base["eta"],
        "governa":       gov,
        "eta":           round(partes[gov], 4),
        "ok":            bool(montante["ok"] and topo["ok"] and base["ok"]),
        "norma": ("EC5 §6.2.3+§6.3.2 (montante) | EC5 §8.2.3+§8.5.1.1+An. A (L1f) | "
                  "EN 1993-1-8 + EN 1992-4 (L3f)"),
        "nota": ("Pilar de frontão (issue 52): segundo montante da cruz do frontão, "
                 "a 5,75 m do canto. Topo com furos oblongos verticais — não apoia a viga."),
    }
