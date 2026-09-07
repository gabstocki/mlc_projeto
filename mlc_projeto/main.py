"""
main.py — Orquestrador do pipeline de verificação MLC.

Sistema estrutural (adotado):
    Viga MLC monolítica de duplo-bisel, biarticulada nos apoios.
    Continuidade na cumeeira (sem rótula real).
    H por Castigliano no eixo centroidal (1× hiperestática).
    Tirante de base ao nível do piso: T≈H, H_sapata≈0 (EN 1993-1-1).
    Classe de serviço 3 (estrutura aberta) — EC5 §2.3.1.3.

Geometria de projeto: candidata R2
    (varredura CS3 — output/varredura_biarticulada_CS3.*)

Pipeline:
    Fase 0 — Dados de entrada
    Fase 1 — Pré-dimensionamento (opcional)
    Fase 2 — ELU (viga, pilar, terças, contraventamento)
    Fase 3 — ELS
    Fase 4 — Ligações + fadiga/deslizamento
    Fase 5 — Relatório
    Fase 6 — Visualização 3D

STOCKI Engenharia Estrutural | Gabriel Stocki CREA-PR 195315/D
EC5 + EN 1990 + NBR 6123
"""

import math
from dataclasses import replace
from mlc_projeto.core.geometry   import GeometriaViga
from mlc_projeto.core.materials  import GlulamMaterial
from mlc_projeto.core.wind       import ParametrosVento
from mlc_projeto.core.loads      import carregamentos_com_vento, peso_proprio_gk

from mlc_projeto.predim.predim   import pre_dimensionar, relatorio

from mlc_projeto.checks.elu.cumeeira          import verifica_cumeeira
from mlc_projeto.checks.elu.misula            import verifica_misula
from mlc_projeto.checks.elu.flambagem_lateral import verifica_flambagem_lateral
from mlc_projeto.checks.elu.flexao            import verifica_flexao
from mlc_projeto.checks.elu.cisalhamento      import verifica_cisalhamento
from mlc_projeto.checks.elu.apoio             import verifica_apoio
from mlc_projeto.checks.elu.flexo_compressao  import verifica_flexo_compressao
from mlc_projeto.checks.els.deflection_els    import verificar_ELS

from mlc_projeto.checks.elu.contraventamento  import verificar_contraventamento
from mlc_projeto.checks.elu.contraventamento_vertical import (
    verificar_contraventamento_vertical,
)
from mlc_projeto.checks.elu.contraventamento_transversal import (
    verificar_contraventamento_transversal,
)
from mlc_projeto.checks.elu.estabilidade_global import (
    verificar_estabilidade_global, relatorio_estabilidade_global,
)
from mlc_projeto.checks.elu.impacto_veiculo import verificar_impacto_veiculo
from mlc_projeto.checks.elu.succao_uplift import verificar_succao_uplift
from mlc_projeto.checks.elu.tirante_piso_robustez import (
    verificar_robustez_tirante_piso, relatorio_robustez_tirante,
)
from mlc_projeto.checks.elu.empuxo_acoplado import (
    analisar_empuxo_acoplado, relatorio_empuxo_acoplado,
)
from mlc_projeto.checks.elu.tirante_base import (
    verificar_tirante_base, relatorio_tirante, impacto_flexibilidade_tirante,
)
from mlc_projeto.connections.connections      import (
    dimensionar_ligacoes, dimensionar_ligacoes_central, relatorio_ligacoes
)
from mlc_projeto.connections.fadiga_ligacoes  import verificar_fadiga_deslizamento
from mlc_projeto.output.report                import (
    gerar_relatorio, tabela_verificacoes, estatisticas_resumo,
    extrair_eta_ok, OUTPUT_DIR,
)
from mlc_projeto.visualization.viz_3d         import visualizar_galpao

import sys


# =============================================================================
# DADOS DE PROJETO — candidata R2 (CS3, biarticulada)
# Ref.: output/varredura_biarticulada_CS3.md
# =============================================================================

# --- Geometria da viga principal (duplo-bisel) --------------------------------
GEO_PARAMS = dict(
    L         = 20.25,   # m — vão do pórtico
    h0        = 1.00,    # m — altura no apoio (h_ap ≈ 2,79 m fixa)
    alpha_deg = 10.0,    # ° — inclinação do extradorso
    # b alinhado à largura do pilar; η_cis≈0,75 (folga ~25%) sem subir cumeeira
    b         = 0.32,    # m — largura da seção
)

# --- Material (EN 14080 + EC5) ------------------------------------------------
# CS3 global: laterais abertas / intempérie (EC5 §2.3.1.3)
#
# Critério de duração do vento (EC5 §2.3.1.2 + Tab. 3.1):
#   A norma permite classificar o vento como «curta» ou «instantânea».
#   Adota-se «curta» (conservador): k_mod,CS3 = 0,70  vs  instantânea = 0,90.
#   (Em CS1/CS2: curta = 0,90 vs instantânea = 1,10 — mesmo critério.)
MAT_CURTA = dict(
    classe         = "GL24h",
    classe_servico = 3,
    duracao        = "curta",      # ELU vento dominante — ver critério acima
)

MAT_LONGA = dict(
    classe         = "GL24h",
    classe_servico = 3,
    duracao        = "longa",      # ELS / k_def
)

# --- Durabilidade: classe de uso / adesivo / tratamento (issue 30) ------------
# Declarações coerentes com a Classe de Serviço 3 (EC5 §2.3.1.3). Valores por
# norma; confirmar espécie/biocida/retenção no projeto executivo.
DURABILIDADE = dict(
    # EN 335 — classe de uso biológica. Estrutura COBERTA mas ABERTA nas laterais:
    # protegida da chuva direta pelo telhado, porém sujeita a umidade/chuva de
    # vento → exterior acima do solo, umedecimento LIMITADO ⇒ UC3.1 (coerente
    # com a CS3 do EC5; peças plenamente abrigadas poderiam ser UC2).
    classe_uso_en335   = "3.1",
    classe_servico_ec5 = 3,
    # EN 301 — adesivo. CS3 exige adesivo Tipo I (EN 14080 §5.3), apto a exposição
    # exterior/alta umidade (ex.: MUF melamina-ureia-formaldeído ou RF/PRF).
    adesivo_en301      = "Tipo I",
    adesivo_exemplos   = "MUF (EN 301) ou resorcina RF/PRF",
    # Espécie e durabilidade natural (EN 350) — conífera de baixa durabilidade
    # ⇒ para UC3 requer tratamento e/ou detalhamento de proteção.
    especie            = "conífera (Picea abies / Pinus spp.)",
    durab_natural_en350 = "classe 4 (baixa)",
    # Tratamento preservativo (EN 335/351) + proteção por projeto (detalhamento).
    tratamento = (
        "impregnação preservativa das lamelas antes da colagem (EN 351, classe "
        "de penetração/retenção conforme UC3.1), COMPLEMENTADA por detalhamento "
        "de proteção — beirais/pingadeiras, drenagem, ventilação, sem acúmulo de "
        "água nas ligações — e acabamento de superfície. Confirmar biocida e "
        "retenção com o tratador no projeto executivo."
    ),
)

# --- Vento NBR 6123 (H1 alinhado a h_ap−h0 no main) ---------------------------
VENTO_PARAMS = dict(
    V0           = 45.0,
    S1           = 1.0,
    categoria    = "IV",
    classe       = "B",
    S3           = 1.0,
    L            = 20.25,
    H1           = 1.785,   # (L/2)·tan(10°) — sobrescrito por geo no main
    h            = 7.0,
    dist_portico = 5.75,
    # Geometria da cobertura para a seleção da rota do §7.2 (Onda 2):
    #   ℓ2 = profundidade TOTAL ⊥ à cumeeira = 2 vãos de 20,25 m;
    #   n_tramos = 2 águas duplas lado a lado (calha central) → telhado
    #   múltiplo, fora do escopo das Tabelas 24/25;
    #   obstruções = veículos sob a cobertura (estacionamento), que por si só
    #   acionam a rota de edificação fechada de §7.2.1.
    l2                       = 40.5,
    n_tramos                 = 2,
    obstrucoes_sob_cobertura = True,
    # ── Atrito longitudinal θ=0° — NBR 6123:2023 §7.2.2 (achado F-13, ENCERRADO)
    # Cláusula transcrita integralmente em core/wind.py:
    #   "Ft = 0,5·q·a·b, onde a e b são as dimensões em planta da cobertura.
    #    Estas forças englobam a ação do vento sobre as duas faces da cobertura."
    # A auditoria adversarial v2 levantou a hipótese de o coeficiente ser 0,05;
    # a cláusula CONFIRMA 0,50 e a hipótese estava errada. Ft é uma ação
    # ENVOLVENTE (cobre as duas faces num só termo) e vale 2,35× o arrasto de
    # bloqueio da silhueta — característica da prescrição, não erro de cálculo.
    # Governa TODO o dimensionamento do contraventamento longitudinal.
    coef_atrito_cobertura    = 0.50,
)

# --- Cargas de área e malha estrutural ----------------------------------------
# Peso próprio g_k é CALCULADO por parcela (issue 1) em peso_proprio_gk():
#   g_MLC (viga, integração de A(x)·ρ_mean) + g_terças + g_cobertura.
#   Cobertura = telha + instalações (valores DECLARADOS — ficha técnica).
# Não se adota mais o valor único G_AREA=1,50 kN/m² (era ~2× o real ≈ 0,80).
G_TELHA_KNM2       = 0.10   # kN/m² — telha metálica trapezoidal (confirmar ficha)
G_INSTALACOES_KNM2 = 0.10   # kN/m² — instalações/serviços (estimativa de projeto)
# Sobrecarga de cobertura — categoria H (não acessível): EN 1991-1-1 Tab. 6.10
#   q_k = 0,40 kN/m² (recomendado; issue 2) e Q_k = 1,0 kN concentrado.
# O Q_k concentrado (verificação LOCAL — terça/telha) não está neste modelo global;
# ver nota da issue 2. Não concomitante com vento (cat. H, issue 3).
Q_AREA   = 0.40        # kN/m² — sobrecarga UDL cat. H (EN 1991-1-1 Tab. 6.10)
QK_CONC_KN = 1.0       # kN — carga concentrada de manutenção (verificação local)
L_T    = 5.75          # m — espaçamento entre pórticos = vão das terças
S      = 2.53          # m — espaçamento entre terças (l_ef viga)

# --- Pilares ------------------------------------------------------------------
# Seção ÚNICA laterais = centrais. Largura (b) = largura da viga (apoio alinhado).
# Profundidade (h) no plano do pórtico otimizada: folga ~25% (η ≤ 0,75).
#   N_cen governa com h=0,27 (η≈0,68); h=0,36 sobrava (N_lat η≈0,03).
# Orientação: b_pilar // largura da viga; h_pilar no plano do pórtico.
B_PILAR     = 0.32     # m — = b da viga
H_PILAR     = 0.27     # m — plano do pórtico
H_PILAR_ALT = 7.0      # m — comprimento
B_PILAR_C   = 0.32     # m — central idêntico
H_PILAR_C   = 0.27     # m
# Pilar de CANTO — montante do painel longitudinal E do frontão transversal.
# Recebe os dois downloads de contraventamento além da reação de gravidade,
# somando ~3× a carga do pilar lateral. Até aqui reutilizava a seção do lateral,
# o que o tornava o gargalo do sistema. Passa a ter seção própria.
B_PILAR_CANTO = 0.32   # m — mantém a largura da viga (fabricação/ligação)
H_PILAR_CANTO = 0.32   # m — engrossado de 0,27 (ver varredura no bloco do CV)

# --- Terças (pré-definidas; verificação no pipeline) --------------------------
B_TERCA = 0.20
H_TERCA = 0.58

# --- Içamento da viga (montagem — EN 1991-1-6; issue 26) ----------------------
# Esquema confirmado: 2 pontos a 0,207·L (|M⁻|=|M⁺|); lingas inclinadas (compressão
# axial), viga SEM contraventamento (LTB no vão entre pontos). Confirmar no plano de
# montagem/rigging. γ_G peso próprio, φ_dyn amplificação dinâmica do içamento.
A_ICAM_REL     = 0.207   # posição dos pontos de içamento (fração de L)
GAMMA_G_ICAM   = 1.35    # coef. do peso próprio (desfavorável)
PHI_DYN_ICAM   = 1.10    # amplificação dinâmica do içamento (EN 1991-1-6)
PSI_LINGA_DEG  = 30.0    # ângulo da linga com a vertical (0 = balancim)
SPREADER_ICAM  = False   # True = balancim (lingas verticais, sem N_c)

# --- Fixação telha→terça sob sucção (issue 17) --------------------------------
# Parafuso autoperfurante Ø6,3 mm + arruela EPDM; espaçamento ADOTADO = a cada
# nervura (~0,20 m) para cobrir a sucção local de canto (galpão aberto, C_pi=+0,8).
# R_FIX_K_KN é TÍPICO de catálogo — confirmar na ficha técnica da telha adotada.
E_FIX_TELHA_M = 0.20    # m — espaçamento de fixadores ao longo da terça
R_FIX_K_KN    = 2.5     # kN — resistência característica do fixador (típico)

# --- Contraventamento horizontal (EC5 §9.2.5) ---------------------------------
# Layout otimizado: cruzes de St. André SÓ nas baías de EXTREMIDADE
# (linha inicial + linha final ao longo do comprimento). NÃO é necessário
# preencher todas as baías da linha frontal/traseira — isso aumenta aço e,
# com k_ℓ = min(1,√(15/ℓ)), pode AGRAVAR a força por baía (ℓ menor → k_ℓ↑).
#   n_modulos_cv = 2  → ℓ = L_comp = 46 m entre baías rígidas
#
# REDIMENSIONAMENTO (pós-Onda 2): com a ação longitudinal normativa (§7.2.2,
# 6,7× a anterior) a Ø22 passou a reprovar com η_diag = 1,280 E deixou de
# validar a restrição lateral das terças (l_1 da LTB saltava de s=2,53 m para
# ℓ=46 m). Varredura de diâmetro, mantendo n_modulos_cv = 2:
#   Ø22 → η=1,280, cobertura_ok=False   (reprovava)
#   Ø25 → η=0,991, cobertura_ok=True    (sem margem)
#   Ø28 → η=0,790, cobertura_ok=True    ← adotado
#   Ø30 → η=0,688
# Aumentar n_modulos_cv NÃO reduz F_diag (114,3 kN) e agrava η_δ — mantém-se 2.
L_COMP_GALPAO   = 46.0    # m — comprimento do galpão
N_MODULOS_CV    = 2       # baías com cruzes (extremos) — ver nota ell/k_ℓ (issue 15)
D_BARRA_CV_MM   = 28.0    # mm — diagonal tracionada (redimensionada: 22 → 28)
ACO_CV          = "S235"

# --- Contraventamento VERTICAL (issue 14) — caminho de carga lateral à fundação
# Cruzes de St. André nas paredes longitudinais que descem a força de vento
# θ=0° do nível da cobertura até a fundação (EN 1993-1-1 §5.3.2+§6.2.3).
# REDIMENSIONAMENTO (pós-Onda 2): concentrar os 837,3 kN longitudinais em 2
# painéis gerava download de 515,8 kN no montante, o que reprovava o pilar de
# canto (η=1,404) e a sua ancoragem (η=1,966) — e exigia diagonal Ø64 mm.
# Varredura do nº de painéis (diagonal auto-dimensionada a η≤0,90):
#   n=2 → Ø64 | download 515,8 | η_canto 1,404 | η_anc 1,966   (reprovava)
#   n=4 → Ø45 | download 257,8 | η_canto 0,843 | η_anc 1,160   (exigiria 6 chumbadores)
#   n=6 → Ø39 | download 171,9 | η_canto 0,655 | η_anc 0,892
# CONSTRUTIBILIDADE (estacionamento aberto nas 4 faces): cada painel é uma cruz
# de 5,75×7 m entre pilares e obstrui a baía. Com 8 baías por linha, n=6 deixava
# só 2 livres para circulação de veículos — inaceitável no uso previsto.
# Segunda varredura, agora com a seção do pilar de canto como variável:
#   n=4 + canto 0,32×0,27 → η_canto 0,801 (passa, sem folga)
#   n=4 + canto 0,32×0,32 → η_canto 0,509   ← adotado então, 4 baías livres
#   n=3 + canto 0,32×0,32 → η_canto 0,614, mas exige 6 chumbadores no canto
#
# ── TERCEIRA VARREDURA (auditoria adversarial v2, no âmbito de F-13) ─────────
# O pipeline REAL foi corrido para n = 2…16 com a diagonal auto-dimensionada
# (η ≤ 0,90) e o coeficiente de atrito nas duas leituras. Com C = 0,50:
#     n    Ø    V_painel  download  η_canto  N_anc   η_anc   η_max   aço
#     2   64    423,7 kN   580,4 kN   0,936  664,3   1,260  1,3840  915 kg  REPROVA
#     4   45    211,9 kN   322,5 kN   0,598  406,4   0,771  0,8930  905 kg
#     6   39    141,2 kN   236,6 kN   0,485  320,5   0,608  0,7926 1019 kg
#     8   33    105,9 kN   193,6 kN   0,428  277,5   0,526  0,8303  973 kg  ← adotado
#    10   30     84,7 kN   167,8 kN   0,394  251,7   0,477  0,8037 1005 kg
#    16   24     53,0 kN   129,1 kN   0,344  213,0   0,404  0,7902 1029 kg
#
# Constatação que muda a decisão anterior: **o peso de aço é praticamente
# INDEPENDENTE de n** (900–1030 kg em toda a varredura) — mais painéis de barra
# mais fina custam o mesmo aço. O que n compra é margem no CAMINHO DE CARGA:
# download no montante, ancoragem e bloco de fundação. E o que custa são baías.
#
# Baías disponíveis: L_comp/dist_pórtico = 46,0/5,75 = 8 por alinhamento; as duas
# fachadas longitudinais dão 16 baías candidatas (o alinhamento CENTRAL fica no
# interior do estacionamento e não é usado). A nota da varredura anterior contava
# baías livres sobre um universo de 8 — coerente com painéis numa só fachada;
# distribuindo-os pelas duas, n=8 deixa 8 baías livres (4 por fachada).
#
# Adota-se n = 8: diagonal Ø33 em vez de Ø45 (ligações de extremidade muito mais
# exequíveis), download no pilar de canto 322,5 → 193,6 kN (−40 %), ancoragem do
# canto 406,4 → 277,5 kN (η_anc 0,771 → 0,526), ao mesmo peso de aço e ainda com
# metade das baías livres. Acima de n≈6 o η_máximo global deixa de ser governado
# por este sistema e passa ao contraventamento da COBERTURA (§9.2.5, η=0,7902).
# Nota: com n=8 a base de canto já passaria com 4 chumbadores (η_sucção 0,867 em
# vez de 0,578); mantêm-se os 6 para não refazer o bloco de fundação já detalhado
# (c=600, h_ef=400, ≈1,60×2,00 m) — ver N_CHU_CANTO.
N_PAINEIS_CV_VERT = 8       # painéis de cruz que resistem à força longitudinal
D_BARRA_CVV_MM    = None    # mm — None → auto (comercial, η ≤ ETA_CVV_ALVO)
ACO_CVV           = "S235"
ETA_CVV_ALVO      = 0.90    # margem de projeto na diagonal vertical

# --- Contraventamento TRANSVERSAL (issue 31, Opção 2) — diafragma + frontões
# Diafragma de cobertura leva o vento θ=90° + nocional aos frontões
# contraventados (cruzes de St. André), e destes à fundação. Valida l_ef=1H
# (non-sway) dos pilares no plano do pórtico.
N_PAINEIS_CV_TRANSV = 1     # painéis de cruz por frontão
D_BARRA_CVT_MM      = None  # mm — None → auto (comercial, η ≤ ETA_CVT_ALVO)
ACO_CVT             = "S235"
ETA_CVT_ALVO        = 0.90  # margem de projeto na diagonal do frontão

# --- Ligações / apoio ---------------------------------------------------------
D_BASE_MM   = 24       # mm — cavilhas L1/L1c (EC5 §8.6(2): 6–30 mm; issue 18)
F_CHU_KN    = 80.0     # kN — resistência por chumbador (L3)
# Ancoragem da base de CANTO — dimensionada à parte. O n_chu geral vem do
# esforço HORIZONTAL, nulo na Opção B, caindo no mínimo construtivo de 4. Mas o
# canto soma o uplift de sucção aos downloads dos dois painéis de
# contraventamento (~4,4× a demanda da extremidade). Com 4 painéis longitudinais
# a demanda é 371,3 kN ⇒ 371,3/(80·0,90) = 5,2 ⇒ 6 chumbadores.
N_CHU_CANTO = 6        # chumbadores na base de canto (contraventada)
# Ancoragem por chumbadores MOLDADOS COM CABEÇA (cast-in headed) — decisão de
# projeto. O lado do concreto fica coberto pelos modelos da EN 1992-4, sem
# depender de ETA de produto; o lado do aço é a barra roscada (EN 1993-1-8).
D_CHU_MM    = 24       # mm — barra roscada M24
CLASSE_CHU  = "8.8"    # classe do aço da barra
# CHAVETA de cisalhamento sob a chapa de base do canto. No caso governante a
# base está TRACIONADA: sem compressão não há atrito, e os 236 kN de cortante
# dos painéis iriam integralmente para os chumbadores, somando-se à tração na
# interação. A chaveta desacopla os dois efeitos — e passa a exigir a sua
# própria verificação de esmagamento do concreto (pendente, EN 1992-1-1 §6.7).
CHAVETA_CISALHAMENTO_CANTO = True
# Geometria da ancoragem do canto — governada pelo CONE de arrancamento
# (CEN/TS 1992-4-2:2009 §6.2.5). Constatação do dimensionamento: aumentar h_ef
# com borda e espaçamento fixos PIORA o resultado, porque A_c,N fica truncado
# por c e s enquanto A⁰_c,N = (3·h_ef)² cresce ao quadrado. Quem governa é o
# TAMANHO DO BLOCO, não a profundidade. O cone só se desenvolve com
# c ≥ 1,5·h_ef; adota-se o par no limite dessa condição.
#   c=450 h_ef=300 s=400 → η=0,844 | bloco ~1,30×1,70 m
#   c=600 h_ef=400 s=400 → η=0,673 | bloco ~1,60×2,00 m   ← adotado
#   c=800 h_ef=533 s=400 → η=0,518 | bloco ~2,00×2,40 m
H_EF_CHU_MM      = 400.0   # embutimento efetivo
C_BORDA_CHU_MM   = 600.0   # distância à borda EXIGIDA da fundação (= 1,5·h_ef)
S_GRUPO_CHU_MM   = 400.0   # espaçamento do grupo
A_CABECA_CHU_MM2 = 2375.0  # área de apoio da cabeça (d_h≈60 mm para M24)
LAYOUT_CHU       = (2, 3)  # 6 chumbadores em 2×3
CLASSE_CONC_FUND = "C25/30"
CONCRETO_FISSURADO = True  # base tracionada → zona fissurada
# Contrato de ancoragem partilhado pelas verificações (sem ETA — moldado).
DADOS_ANCORAGEM = {
    "h_ef_mm": H_EF_CHU_MM,
    "A_cabeca_mm2": A_CABECA_CHU_MM2,
    "c_borda_mm": C_BORDA_CHU_MM,
    "s_grupo_mm": S_GRUPO_CHU_MM,
    "classe_concreto": CLASSE_CONC_FUND,
    "concreto_fissurado": CONCRETO_FISSURADO,
    "verificacao_en1992_4": "EN 1992-4:2018 §7.2.1.4/7.2.1.5/7.4.1.4/7.2.3",
}
ETA_LIG_ALVO = 0.75    # margem de projeto L1/L3 (uso público; frágil em madeira)
L_AP        = 0.90     # m — comprimento da placa de apoio

# --- Componente metálico das ligações (EN 1993-1-8; issue 21) -----------------
# Aço S275 (escolha do projeto). A ESPESSURA das chapas não é arbitrada: sai do
# dimensionamento no esquadro (chapas_dim.py, issue 23) — L1/L1c ≥ d = 25 mm.
ACO_CHAPA_LIG = "S275"   # f_y=275, f_u=430 MPa (EN 1993-1-1 Tab. 3.1)
A_SOLDA_MM    = 6.0      # mm — garganta da solda de filete chapa↔base

# --- Tirante de base (fecho do empuxo ao nível do piso) ------------------------
# Solução usual: barra de aço ligando as bases de cada vão → H_sapata ≈ 0.
# T_d = H_arco (Castigliano ELU). Diâmetro None = escolha automática η≤eta_alvo.
# ── DECISÃO DE MODELO — empuxo transversal (issue 35/38) ──────────────────────
# EMPUXO_DESENVOLVE = False → Opção B (adotada): o pilar biarticulado é um
# mecanismo lateral e o empuxo NÃO se desenvolve (H_dev≈0, ver empuxo_acoplado.py).
# A viga trabalha BIAPOIADA (M=M0). Consequências: sem tirante de fecho de empuxo;
# a fundação não recebe empuxo de gravidade; a ancoragem responde ao uplift.
# True reativaria o modelo de apoio rígido (Opção A).
EMPUXO_DESENVOLVE = False

# Tirante de base — SÓ existe na Opção A (fecho do empuxo). Na Opção B o empuxo
# não se desenvolve ⇒ tirante horizontal na base não tem função (não fecha empuxo,
# não resiste ao uplift vertical, não limita a abertura do beiral) ⇒ removido.
TIRANTE_BASE     = EMPUXO_DESENVOLVE
ACO_TIRANTE      = "MR315"
D_TIRANTE_MM     = None    # None → auto (comercial, η ≤ ETA_LIG_ALVO)
ETA_TIRANTE_ALVO = 0.75
# Robustez do tirante no piso (issue 37) — só se aplica se houver tirante (Opção A).
PROTECAO_TIRANTE = "embutido"
TIRANTE_PRIMARIO = EMPUXO_DESENVOLVE


# ── Orquestrador ──────────────────────────────────────────────────────────────

class _Tee:
    """Duplica stdout para console e arquivo (export do terminal)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass

    def flush(self):
        for s in self.streams:
            try:
                s.flush()
            except Exception:
                pass


def _print_eta(nome: str, res: dict) -> None:
    """
    Imprime η. F-04: resultado ausente, nulo ou não numérico é INDETERMINADO e
    imprime-se como ✗ «sem η» — nunca como η = 0,0000 ✓ (o antigo `or 0.0`
    convertia `None` numa aprovação visual).
    """
    if not isinstance(res, dict):
        print(f"  ✗ {nome:<30} (sem resultado)")
        return
    eta, ok_flag = extrair_eta_ok(res)
    if math.isnan(eta):
        print(f"  ✗ {nome:<30} η = —      (sem η — não concluída)")
        return
    ok  = "✓" if ok_flag else "✗"
    n_bar = max(0, min(40, int(eta * 20)))
    bar = "█" * n_bar
    print(f"  {ok} {nome:<30} η = {eta:.4f}  {bar}")


def _imprimir_resumo_export(resultados: dict, load, meta: dict) -> dict:
    """
    Resumo unificado terminal = Excel = memorial (§12).
    Devolve estatísticas (eta_max, all_ok, status).
    """
    # F-04: o catálogo é percorrido POR INTEIRO; as exclusões deliberadas têm de
    # ser DECLARADAS (`meta["nao_aplicaveis"]`), nunca inferidas da ausência.
    tab = tabela_verificacoes(
        resultados, nao_aplicaveis=set(meta.get("nao_aplicaveis", ()))
    )
    est = estatisticas_resumo(tab)
    print("\n" + "=" * 72)
    print("  RESUMO DE TAXAS DE UTILIZAÇÃO — Viga biarticulada MLC")
    print("  (mesma tabela exportada para Excel / memorial §12)")
    print("=" * 72)
    print(f"  {'Verificação':<32} {'Norma':<24} {'η':>8}  St  Estado")
    print(f"  {'-'*76}")
    for row in tab:
        eta = float(row["η"])
        eta_txt = "       —" if math.isnan(eta) else f"{eta:>8.4f}"
        estado = "" if row["status"] == "OK" else f"  [{row['status']}]"
        print(
            f"  {row['Verificação']:<32} {row['Norma']:<24} "
            f"{eta_txt}  {row['OK']}{estado}"
        )
    print(f"  {'-'*76}")
    eta_max = est["eta_max"]
    all_ok = est["all_ok"]
    H = float(load.H_ELU()) if load is not None else 0.0
    com_tir = bool(meta.get("com_tirante", False))
    H_sap = 0.0 if com_tir else H
    status = est["status"]
    print(f"  η máximo     = {eta_max:.4f}")
    if com_tir:
        print(f"  H_arco       = {H:.2f} kN  (Castigliano → tirante)")
        print(f"  H_sapata     = {H_sap:.2f} kN  (tirante ativo)")
        print(f"  T_tirante    = {meta.get('T_tirante_kN', H):.2f} kN  "
              f"(∅{meta.get('d_tirante_mm', '?')} mm "
              f"{meta.get('aco_tirante', '')})")
    else:
        print(f"  H_fund      = {H:.2f} kN  (empuxo → sapata)")
    print(f"  η_alvo lig.  = {meta.get('eta_lig_alvo', ETA_LIG_ALVO):.2f}")
    print(f"  k_mod vento  = {meta.get('k_mod_vento', 0):.2f} "
          f"(curta; inst.={meta.get('k_mod_vento_instantanea', 0):.2f} não usada)")
    print(f"  N.º verif.   = {est['n_linhas']} "
          f"({est['n_executadas']} executadas, "
          f"{len(est['nao_aplicaveis'])} não aplicáveis)  |  todas OK = {all_ok}")
    if est["pendentes"]:
        # F-04: uma verificação sem resultado utilizável bloqueia a aprovação e
        # tem de ser NOMEADA — antes desaparecia em silêncio do resumo.
        print(f"  ⚠ SEM RESULTADO ({len(est['pendentes'])}): "
              f"{', '.join(est['pendentes'])}")
    print(f"  Status       = {status}")
    print("=" * 72)
    return {
        "eta_max": eta_max,
        "all_ok": all_ok,
        "status": status,
        "n_verif": est["n_linhas"],
        "pendentes": est["pendentes"],
        "tabela": tab,
    }


def main(rodar_varredura: bool = False, abrir_viz: bool = True) -> dict:
    """
    Executa o pipeline completo.

    Returns:
        dict com resultados (para testes / integração).
    """
    # Export do terminal → output/pipeline_console.txt (UTF-8)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log_path = OUTPUT_DIR / "pipeline_console.txt"
    log_f = open(log_path, "w", encoding="utf-8")
    _stdout_prev = sys.stdout
    sys.stdout = _Tee(_stdout_prev, log_f)

    try:
        return _main_impl(rodar_varredura=rodar_varredura, abrir_viz=abrir_viz)
    finally:
        sys.stdout = _stdout_prev
        log_f.close()
        print(f"  Console export: {log_path}")


def _main_impl(rodar_varredura: bool = False, abrir_viz: bool = True) -> dict:
    """Corpo do pipeline (stdout pode estar em tee)."""

    print("=" * 72)
    print("  PIPELINE MLC — STOCKI Engenharia Estrutural")
    print("  Biarticulada MLC | CS3 | R2 | EC5 + EN 1990 + NBR 6123")
    print("=" * 72)

    # ── Fase 0: Dados de entrada ──────────────────────────────────────────────
    print("\n[FASE 0] Dados de entrada...")

    geo       = GeometriaViga(**GEO_PARAMS)
    mat_curta = GlulamMaterial(**MAT_CURTA)
    mat_longa = GlulamMaterial(**MAT_LONGA)

    # ── Peso próprio característico g_k discriminado (issue 1) ─────────────────
    # EN 1991-1-1 §4.1 + EN 14080 (ρ_mean). g_k_viga = MLC + terças + cobertura;
    # g_k_terça = terças + cobertura (a terça não carrega o peso da viga MLC).
    pp = peso_proprio_gk(
        geo=geo, mat=mat_longa, L_t=L_T,
        b_terca=B_TERCA, h_terca=H_TERCA, s_terca=S,
        g_telha_kNm2=G_TELHA_KNM2, g_instalacoes_kNm2=G_INSTALACOES_KNM2,
    )
    g_area       = pp["g_k_viga_kNm2"]    # kN/m² — carga permanente na VIGA
    g_area_terca = pp["g_k_terca_kNm2"]   # kN/m² — carga permanente na TERÇA
    print(f"  g_k (calc.): viga={g_area:.3f} kN/m² "
          f"[MLC={pp['g_mlc_kNm2']:.3f} + terças={pp['g_tercas_kNm2']:.3f} + "
          f"cobertura={pp['g_cobertura_kNm2']:.3f}] | terça={g_area_terca:.3f} kN/m²")
    print(f"  γ_glulam={pp['gamma_kNm3']:.2f} kN/m³ (ρ_mean={pp['rho_mean_kgm3']} "
          f"kg/m³, EN 14080) | telha={G_TELHA_KNM2:.2f}+instal.={G_INSTALACOES_KNM2:.2f} "
          f"kN/m² (declarados)")

    # H1 do vento = variação real da cobertura (coerente com a geometria)
    vento_kw = dict(VENTO_PARAMS)
    vento_kw["H1"] = geo.h_ap - geo.h0
    vento_kw["L"]  = geo.L
    params_vento = ParametrosVento(**vento_kw)

    # θ=90° Tab.25 completo + θ=0° longitudinal (pilares + contraventamento)
    # n_pilares_linha ≈ L_comp/dist + 1; n_linhas = 3 (2 pórticos + central compartilhado)
    L_COMP = 46.0
    n_pil_linha = max(2, round(L_COMP / L_T) + 1)
    load = carregamentos_com_vento(
        geo=geo, mat=mat_curta,
        g_area=g_area, q_area=Q_AREA,
        L_t=L_T, params_vento=params_vento,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        n_pilares_linha=n_pil_linha,
        n_linhas_portico=3,
        L_cob_m=L_COMP,
        B_cob_m=2 * geo.L,   # dois vãos lado a lado
        empuxo_desenvolve=EMPUXO_DESENVOLVE,   # Opção B (issue 35/38)
    )

    gov = load.combinacao_ELU_governante()
    # k_mod da duração da combinação governante — EC5 §3.1.3
    mat_elu = mat_curta.com_duracao(gov.duracao)

    print(f"  Geometria : L={geo.L}m | h0={geo.h0}m | "
          f"α={geo.alpha_deg}° | b={geo.b}m | h_ap={geo.h_ap:.3f}m")
    print(f"  Material  : {mat_elu.classe} | CS{mat_elu.classe_servico} | "
          f"k_mod={mat_elu.k_mod:.2f} ({gov.duracao}) | "
          f"k_def={mat_longa.k_def:.2f} (ELS)")
    print(f"  Durabilidade (issue 30): CS3 → EN 335 UC{DURABILIDADE['classe_uso_en335']} | "
          f"adesivo {DURABILIDADE['adesivo_en301']} (EN 301) | "
          f"trat. preservativo EN 351 + detalhamento de proteção")
    print(f"  k_mod vento: duração «curta» adotada "
          f"(k_mod={mat_elu.com_duracao('curta').k_mod:.2f}; "
          f"instantânea permitida={mat_elu.com_duracao('instantanea').k_mod:.2f} "
          f"— não usada; critério conservador, EC5 §2.3.1.2)")
    print(f"  ELU gov.  : {gov.nome} | padrao={gov.padrao_vento} | "
          f"M={gov.M_max_kNm:.2f} kN·m | "
          f"V={gov.V_max_kN:.2f} kN | N={gov.N_viga_kN:.2f} kN | "
          f"H_arco={gov.H_kN:.2f} kN"
          + (" → tirante" if TIRANTE_BASE else " → sapata"))
    print(f"  Sistema   : Viga biarticulada MLC (contínua na cumeeira) | "
          f"Área trib.={load.area_trib:.3f} m (L_t×{load.fator_trib})")
    print(f"  M_cumeeira: {gov.M_cumeeira_kNm:.2f} kN·m | "
          f"N={gov.N_viga_kN:.2f} kN | H={gov.H_kN:.2f} kN")

    # Varredura Cpe Tab.25 (θ=90°)
    vv = load.varredura_vento_90
    print(f"\n  Vento θ=90° (⊥ cumeeira) — NBR 6123 Tab.25:")
    print(f"    Padrões Cpe varridos: {vv.get('n_padroes_cpe', 0)} "
          f"({', '.join(vv.get('padroes', []))})")
    print(f"    Comb. ELU com vento: {vv.get('n_combinacoes_elu_vento', 0)} "
          f"| varredura completa={vv.get('completo', False)}")
    print(f"    Gov |M|: {vv.get('gov_M', {}).get('padrao')}  "
          f"M={vv.get('gov_M', {}).get('M_max', 0):.1f} kNm")
    print(f"    Gov |H|: {vv.get('gov_H', {}).get('padrao')}  "
          f"H={vv.get('gov_H', {}).get('H', 0):.1f} kN")
    print(f"    Gov sucção: {vv.get('gov_succao', {}).get('padrao')}  "
          f"q={vv.get('gov_succao', {}).get('q_tot', 0):+.2f} kN/m")
    if load.vento_0:
        print(f"  Vento θ=0° (// cumeeira) — estrutura aberta:")
        print(f"    F_total={load.vento_0['F_total_kN']:.1f} kN "
              f"(pilares={load.vento_0['F_pilares_kN']:.1f} + "
              f"fricção={load.vento_0['F_friccao_kN']:.1f}) | "
              f"w={load.vento_0['w_long_kNpm']:.3f} kN/m")
        print(f"    Atrito §7.2.2: Ft = {load.vento_0['coef_atrito']:g}·q·a·b "
              f"= {load.vento_0['F_friccao_kN']:.1f} kN "
              f"(a×b = {load.vento_0['A_planta_m2']:.0f} m² em planta; "
              f"engloba as duas faces)")
        print(f"    Escala: {load.vento_0['razao_bloqueio']:.2f}× o arrasto de "
              f"bloqueio da silhueta ({load.vento_0['F_bloqueio_kN']:.1f} kN) "
              f"— envelope normativo, ver §7.2.2 transcrito em core/wind.py")

    # ── Fase 1: Pré-dimensionamento ───────────────────────────────────────────
    if rodar_varredura:
        print("\n[FASE 1] Varredura paramétrica...")
        df = pre_dimensionar(
            g_area=g_area, q_area=Q_AREA,
            params_vento=params_vento,
            L_v=geo.L, L_t=L_T,
            classe=MAT_CURTA["classe"],
            classe_servico=MAT_CURTA["classe_servico"],
            h0_range=(0.40, 1.20, 0.05),
            alpha_range=(3.0, 8.0, 0.5),
            b_range=(0.10, 0.28, 0.02),
            l_ap_range=(0.20, 0.55, 0.05),
            s_range=(1.00, 2.10, 0.25),
        )
        relatorio(df, n=10)
    else:
        print("\n[FASE 1] Geometria pré-definida "
              "(passe rodar_varredura=True para varredura completa)")

    # ── Fase 2: Verificações ELU ──────────────────────────────────────────────
    print("\n[FASE 2] Verificações ELU...")

    res_elu = {}

    res_elu["cumeeira"] = verifica_cumeeira(geo, mat_elu, load)
    _print_eta("Cumeeira §6.4.3", res_elu["cumeeira"])

    res_elu["misula"] = verifica_misula(geo, mat_elu, load)
    _mi = res_elu["misula"]
    _print_eta("Mísula face incl. §6.4.2", _mi)
    print(f"  · Borda inclinada α={_mi['alpha_deg']:.0f}°: {_mi['regime']} no topo "
          f"governa em x={_mi['x_gov_m']:.2f} m ({_mi['comb_gov']}) | "
          f"k_m,α={_mi['k_m_alpha']:.3f} (comp={_mi['k_m_alpha_compressao']:.3f}, "
          f"tração={_mi['k_m_alpha_tracao']:.3f})")

    # ── Contraventamento ANTES do LTB ─────────────────────────────────────────
    # A cobertura só valida l_1 = s (terças) se o sistema de estabilização
    # cumprir EC5 §9.2.5 (força + rigidez + terça-biela + δ ≤ ℓ/500).
    # Caso contrário l_1 é penalizado → LTB/flexão usam o valor efetivo.
    print("\n[FASE 2] Contraventamento — integridade da cobertura (§9.2.5)...")
    print(f"  Layout: {N_MODULOS_CV} baías rígidas (extremos) | "
          f"ℓ={L_COMP_GALPAO/(N_MODULOS_CV-1) if N_MODULOS_CV>1 else L_COMP_GALPAO:.1f} m | "
          f"diagonal ∅{D_BARRA_CV_MM:.0f} mm {ACO_CV}")
    print("  Critério: estabilização EC5 §9.2.5 (não exige cruzes em todas as baías)")

    res_elu["contraventamento"] = verificar_contraventamento(
        geo=geo, mat=mat_elu, load=load,
        L_comp=L_COMP_GALPAO, n_modulos_cv=N_MODULOS_CV,
        s_terca=S, d_barra_mm=D_BARRA_CV_MM, aco=ACO_CV,
        n_porticos=2, dist_portico=L_T,
        b_terca=B_TERCA, h_terca=H_TERCA,
        k_crit=1.0,   # 1.ª passagem; refinado após LTB
    )
    _print_eta("Cobertura §9.2.5", res_elu["contraventamento"])
    cv0 = res_elu["contraventamento"]
    l_1_ltb = float(cv0["l_1_efetivo_m"])
    print(f"  → l_1 LTB = {l_1_ltb:.3f} m | {cv0['l_1_nota']}")
    print(f"  → η_diag={cv0['eta_diag_N']:.3f} | η_δ={cv0['eta_delta']:.3f} | "
          f"η_terça={cv0['eta_terca']:.3f} | F_diag={cv0['F_diag_kN']:.1f} kN | "
          f"peso aço≈{cv0['peso_total_kg']:.0f} kg")
    if not cv0["cobertura_ok"]:
        print("  ⚠ Cobertura NÃO valida restrição lateral das terças — "
              "LTB com l_1 penalizado.")

    res_elu["flambagem"] = verifica_flambagem_lateral(
        geo, mat_elu, load, l_1=l_1_ltb
    )
    _print_eta("Flambagem §6.3.3", res_elu["flambagem"])

    # Refinar N_flex do contraventamento com k_crit real do LTB
    k_crit_ltb = float(res_elu["flambagem"].get("k_crit", 1.0))
    res_elu["contraventamento"] = verificar_contraventamento(
        geo=geo, mat=mat_elu, load=load,
        L_comp=L_COMP_GALPAO, n_modulos_cv=N_MODULOS_CV,
        s_terca=S, d_barra_mm=D_BARRA_CV_MM, aco=ACO_CV,
        n_porticos=2, dist_portico=L_T,
        b_terca=B_TERCA, h_terca=H_TERCA,
        k_crit=k_crit_ltb,
    )
    l_1_ltb = float(res_elu["contraventamento"]["l_1_efetivo_m"])
    # Se o refinamento mudou a validade, reavaliar LTB uma vez
    if abs(l_1_ltb - float(res_elu["flambagem"]["l_1_m"])) > 1e-6:
        res_elu["flambagem"] = verifica_flambagem_lateral(
            geo, mat_elu, load, l_1=l_1_ltb
        )
        _print_eta("Flambagem §6.3.3 (recalc.)", res_elu["flambagem"])

    res_elu["flexao"] = verifica_flexao(geo, mat_elu, load, s=l_1_ltb)
    _print_eta("Flexo-comp. §6.3.2+6.35", res_elu["flexao"])

    res_elu["cisalhamento"] = verifica_cisalhamento(geo, mat_elu, load)
    _print_eta("Cisalhamento §6.1.7", res_elu["cisalhamento"])

    res_elu["apoio"] = verifica_apoio(geo, mat_elu, load, l_ap=L_AP)
    _print_eta("Apoio §6.1.5+§6.2.2", res_elu["apoio"])

    res_elu["flexo_comp"] = verifica_flexo_compressao(
        geo=geo, mat=mat_elu, load=load,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        H_pilar=H_PILAR_ALT, s=l_1_ltb,
    )
    _print_eta(
        f"Pilar {B_PILAR}×{H_PILAR}m §6.3.2",
        res_elu["flexo_comp"]
    )

    print("\n[FASE 2] Verificações ELU — Pilar central...")
    from mlc_projeto.checks.elu.pilares import (
        verifica_pilar_governante as _verifica_pilar_gov,
        verifica_pilar_vento_lateral as _pilar_vento,
    )
    # Pilar central: N = soma das reações dos dois vãos (fator_reacao=2),
    # governante entre TODAS as combinações ELU (cada uma com o seu k_mod).
    res_elu["pilar_central"] = _verifica_pilar_gov(
        mat=mat_curta, load=load,
        b=B_PILAR_C, h=H_PILAR_C, H=H_PILAR_ALT,
        fator_reacao=2.0,
    )
    _pc = res_elu["pilar_central"]
    _print_eta(
        f"Pilar central {B_PILAR_C}×{H_PILAR_C}m §6.3.2",
        _pc,
    )
    print(f"  · N_d={_pc['N_d_kN']:.1f} kN (2·R_v) | governa {_pc['comb_gov']} "
          f"({_pc['duracao']}, k_mod={_pc['k_mod']:.2f}) | "
          f"k_c={_pc['k_c']:.3f} | η={_pc['eta']:.4f}")
    print(f"  · Origem dos N (issue 13): R_v ELU = reação vertical = N do pilar; "
          f"N_viga (~{load.N_max_ELU():.0f} kN, com empuxo H) é da VIGA; "
          f"87 kN ≈ R_v de ELS (serviço), não ELU.")

    # Estabilidade lateral dos pilares — vento θ=0° e θ=90° (estrutura aberta)
    print("\n[FASE 2] Pilares — vento lateral (estrutura aberta)...")
    _N_lat = load.V_max_ELU()
    res_elu["pilar_vento_0"] = _pilar_vento(
        mat=mat_elu, b=B_PILAR, h=H_PILAR, H=H_PILAR_ALT,
        N_d=_N_lat, params_vento=params_vento, theta_deg=0.0,
    )
    res_elu["pilar_vento_90"] = _pilar_vento(
        mat=mat_elu, b=B_PILAR, h=H_PILAR, H=H_PILAR_ALT,
        N_d=_N_lat, params_vento=params_vento, theta_deg=90.0,
    )
    _print_eta("Pilar vento θ=0° (// cum.)", res_elu["pilar_vento_0"])
    print(f"  · M_d={res_elu['pilar_vento_0']['M_d_kNm']:.2f} kNm | "
          f"F_d={res_elu['pilar_vento_0']['F_d_kN']:.2f} kN | "
          f"eixo={res_elu['pilar_vento_0']['eixo']}")
    _print_eta("Pilar vento θ=90° (⊥ cum.)", res_elu["pilar_vento_90"])
    print(f"  · M_d={res_elu['pilar_vento_90']['M_d_kNm']:.2f} kNm | "
          f"F_d={res_elu['pilar_vento_90']['F_d_kN']:.2f} kN | "
          f"eixo={res_elu['pilar_vento_90']['eixo']}")
    if res_elu["contraventamento"].get("gov_forca"):
        print(f"  · Contraventamento: força governante = "
              f"{res_elu['contraventamento']['gov_forca']} | "
              f"R_ext={res_elu['contraventamento'].get('R_ext_proj_kN', 0):.1f} kN "
              f"(estab={res_elu['contraventamento'].get('R_ext_estab_kN', 0):.1f}, "
              f"vento0/2={res_elu['contraventamento'].get('F_vento0_kN', 0)/2:.1f})")

    # Carga vertical de cálculo TOTAL do galpão — base do α_cr de sistema
    # (EN 1993-1-1 Eq. 5.2). Achado F-02 da auditoria adversarial v2.
    _n_frames = max(2, round(L_COMP_GALPAO / L_T) + 1)
    V_ED_TOTAL_KN = 2.0 * 2 * abs(load.V_max_ELU()) * _n_frames

    # Contraventamento VERTICAL — caminho de carga lateral até a fundação (issue 14)
    print("\n[FASE 2] Contraventamento vertical (força lateral → fundação)...")
    res_elu["contraventamento_vertical"] = verificar_contraventamento_vertical(
        geo=geo, load=load,
        H_pilar_m=H_PILAR_ALT,
        dist_portico=L_T,
        L_comp=L_COMP_GALPAO,
        n_porticos=2,
        n_paineis_long=N_PAINEIS_CV_VERT,
        aco=ACO_CVV,
        d_mm=D_BARRA_CVV_MM,
        eta_alvo=ETA_CVV_ALVO,
        R_ext_cobertura_kN=res_elu["contraventamento"].get("R_ext_proj_kN"),
        V_Ed_total_kN=V_ED_TOTAL_KN,
    )
    cvv = res_elu["contraventamento_vertical"]
    _print_eta("Contravento vertical §5.4", cvv)
    print(f"  · F_vento0={cvv['F_vento0_kN']:.1f} kN + H_imp={cvv['H_imp_kN']:.1f} kN "
          f"→ V_lat={cvv['V_lat_total_kN']:.1f} kN / {cvv['n_paineis']} painéis")
    print(f"  · Diagonal ∅{cvv['d_mm']:.0f} mm {cvv['aco']} (β={cvv['beta_deg']}°) | "
          f"N_diag={cvv['N_diag_kN']:.1f} kN | η_N={cvv['eta_diag_N']:.3f} | "
          f"η_δ={cvv['eta_delta']:.3f}")
    print(f"  · Caminho à fundação: H_base={cvv['H_base_kN']:.1f} kN + "
          f"arrancamento N_uplift={cvv['N_uplift_kN']:.1f} kN")
    print(f"  · α_cr,long={cvv['alpha_cr']} ({cvv['regime_alpha_cr']}) | "
          f"K_lat={cvv['K_lat_kNpm']:.0f} kN/m | k_II={cvv['k_II']:.3f}")

    # Contraventamento TRANSVERSAL — diafragma + frontões → fundação (issue 31)
    print("\n[FASE 2] Contraventamento transversal (diafragma + frontões → fund.)...")
    res_elu["contraventamento_transversal"] = verificar_contraventamento_transversal(
        geo=geo, load=load, params_vento=params_vento,
        H_pilar_m=H_PILAR_ALT,
        dist_portico=L_T,
        L_comp=L_COMP_GALPAO,
        n_porticos=2,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        n_paineis_por_gable=N_PAINEIS_CV_TRANSV,
        aco=ACO_CVT,
        d_mm=D_BARRA_CVT_MM,
        eta_alvo=ETA_CVT_ALVO,
        V_Ed_total_kN=V_ED_TOTAL_KN,
    )
    cvt = res_elu["contraventamento_transversal"]
    _print_eta("Contravento transversal §5.4", cvt)
    print(f"  · Arrasto θ=90° ({cvt['n_colunas']} pilares)={cvt['H_vento_topo_kN']:.1f} kN"
          f" + cobertura(F-01)={cvt['H_cob_kN']:.1f} kN"
          f" + H_imp={cvt['H_imp_kN']:.1f} kN → H_tr={cvt['H_tr_kN']:.1f} kN")
    print(f"  · Componente ⊥→horizontal da pressão de cobertura: "
          f"{cvt['H_cob_portico_kN']:.2f} kN/pórtico × {cvt['n_frames']} "
          f"({cvt['comb_H_cob']})")
    print(f"  · Diafragma: R_frontão={cvt['R_gable_kN']:.1f} kN | "
          f"N_corda={cvt['N_corda_kN']:.1f} kN (→ beiral)")
    print(f"  · Frontão ∅{cvt['d_mm']:.0f} mm {cvt['aco']} (β={cvt['beta_deg']}°) | "
          f"N_diag={cvt['N_diag_kN']:.1f} kN | η_N={cvt['eta_diag_N']:.3f} | "
          f"η_δ={cvt['eta_delta']:.3f}")
    print(f"  · Caminho à fundação: H_base={cvt['H_base_kN']:.1f} kN + "
          f"N_uplift={cvt['N_uplift_kN']:.1f} kN | l_ef=1H (non-sway) validado")
    print(f"  · α_cr,transv={cvt['alpha_cr']} ({cvt['regime_alpha_cr']}) | "
          f"K_lat={cvt['K_lat_kNpm']:.0f} kN/m | k_II={cvt['k_II']:.3f}")

    # Montante de contraventamento — download ±V_Ed·tanβ no pilar (issue 36)
    print("\n[FASE 2] Pilar montante de contraventamento (download ±V_Ed·tanβ)...")
    from mlc_projeto.checks.elu.pilares import verifica_pilar_contraventado
    # Pilar de CANTO: montante do painel LONGITUDINAL e do FRONTÃO transversal
    # (integra os dois downloads). N_uplift_kN de cada módulo = V_Ed·tanβ por painel.
    _D_long   = float(cvv["N_uplift_kN"])
    _D_transv = float(cvt["N_uplift_kN"])
    _Rv_comp  = max(abs(float(c.V_max_kN)) for c in load.combinacoes_ELU_fisicas().values())
    _Rv_min   = min(abs(float(c.V_max_kN)) for c in load.combinacoes_ELU_fisicas().values())
    # Momento de vento na face (concomitante) — o maior entre θ=0° e θ=90°.
    _M_vento  = max(
        float(res_elu.get("pilar_vento_0", {}).get("M_d_kNm", 0.0)),
        float(res_elu.get("pilar_vento_90", {}).get("M_d_kNm", 0.0)),
    )
    res_elu["pilar_contraventado"] = verifica_pilar_contraventado(
        mat=mat_elu, b=B_PILAR_CANTO, h=H_PILAR_CANTO, H_pilar=H_PILAR_ALT,
        N_grav_comp_kN=_Rv_comp, N_grav_uplift_kN=_Rv_min,
        downloads_kN=[_D_long, _D_transv], eixo="min", M_vento_kNm=_M_vento,
    )
    _pcv = res_elu["pilar_contraventado"]
    _print_eta("Pilar canto (grav+brace+vento) §6.2.3/§6.3.2", _pcv)
    print(f"  · Download: long={_D_long:.1f} + transv={_D_transv:.1f} = "
          f"{_pcv['download_total_kN']:.1f} kN (canto = 2 painéis) | "
          f"M_vento={_pcv['M_vento_kNm']:.1f} kNm")
    print(f"  · Flexo-compressão: N={_pcv['N_comp_kN']:.1f} kN "
          f"(R_v={_Rv_comp:.1f}+download) + M → η={_pcv['eta_comp']:.3f}")
    print(f"  · Flexo-tração (uplift, R_v,min={_Rv_min:.1f}): "
          f"N_t={_pcv['N_tracao_liq_kN']:.1f} kN + M → η={_pcv['eta_tracao']:.3f} "
          f"| ancoragem={_pcv['N_ancoragem_kN']:.1f} kN (→ sucção/issue 33)")
    print(f"  · Governa: {_pcv['regime']} | η={_pcv['eta']:.4f} "
          f"(vs pilar interno ~{res_elu['flexo_comp'].get('eta', 0):.3f})")

    # Corda do diafragma — elemento de beiral verificado como membro (issue 32)
    print("\n[FASE 2] Corda do diafragma — elemento de beiral (issue 32)...")
    from mlc_projeto.checks.elu.corda_beiral import verificar_corda_beiral
    from mlc_projeto.core.wind import calcular_vento as _cv_corda
    _w_corda = _cv_corda(params_vento).pressoes["C1"]["barlavento_kNm2"]
    res_elu["corda_beiral"] = verificar_corda_beiral(
        mat=mat_elu, N_corda_kN=cvt["N_corda_kN"],
        L_t=L_T, s_eave=S / 2.0, b=B_TERCA, h=H_TERCA,
        alpha_deg=GEO_PARAMS["alpha_deg"],
        g_k_m2=g_area_terca, q_k_m2=Q_AREA, w_kNm2=_w_corda,
        L_comp=L_COMP_GALPAO,
    )
    _cb = res_elu["corda_beiral"]
    _print_eta("Corda beiral §6.2.3/§6.3.2", _cb)
    print(f"  · {_cb['elemento']} | N_corda={_cb['N_corda_kN']:.1f} kN (±) | "
          f"seção {_cb['b_m']}×{_cb['h_m']} m")
    print(f"  · flexo-compr §6.3.2 η={_cb['eta_compressao']:.3f} | "
          f"flexo-tração §6.2.3 η={_cb['eta_tracao']:.3f} → "
          f"η={_cb['eta']:.4f} ({_cb['caso_gov']})")
    print(f"  · Continuidade: {_cb['n_emendas']} emenda(s) × "
          f"{_cb['F_emenda_kN']:.1f} kN (obrigatória p/ o diafragma funcionar)")

    # Estabilidade global — P-Δ, forças nocionais, α_cr (dispensa 2.ª ordem)
    print("\n[FASE 2] Estabilidade global (P-Δ / nocionais / α_cr)...")
    res_elu["estabilidade_global"] = verificar_estabilidade_global(
        geo=geo, mat=mat_elu, load=load,
        H_pilar_m=H_PILAR_ALT,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        m_colunas=2,
        contravento_vertical_ok=cvv["lateral_estavel_long"],
        contravento_transversal_ok=cvt["lateral_estavel_transv"],
        # AUD-006/AUD-008: a força nocional (EN 1993-1-1 §5.3.2) entra como caso
        # de carga explícito na demanda do contraventamento transversal
        # (H_tr = arrasto θ=90° no topo + H_imp) e é ali verificada. Só se
        # declara o caminho lateral quando essa verificação passou.
        nocional_no_contraventamento=bool(
            cvt.get("ok") and cvt.get("H_imp_kN", 0.0) > 0.0
        ),
        # F-02: α_cr de SISTEMA por direção, a partir da rigidez real dos
        # painéis de cruz (EN 1993-1-1 Eq. 5.2). Sem estes dados a verificação
        # recusa dispensar a 2.ª ordem — ausência de dado não é aprovação.
        K_lat_long_kNpm=cvv.get("K_lat_kNpm"),
        K_lat_transv_kNpm=cvt.get("K_lat_kNpm"),
        V_Ed_total_kN=V_ED_TOTAL_KN,
        amplificacao_aplicada=bool(
            cvv.get("amplificacao_aplicada") or cvt.get("amplificacao_aplicada")
        ),
    )
    eg = res_elu["estabilidade_global"]
    _print_eta("Estab. global α_cr/P-Δ", eg)
    print(f"  · α_cr,sistema={eg['alpha_cr']:.1f} (mín {eg['alpha_cr_min']:.0f}, "
          f"dir. crítica: {eg['direcao_critica']}) | "
          f"long={eg['alpha_cr_long']} transv={eg['alpha_cr_transv']} | "
          f"k_II={eg['k_II']:.3f} (aplicado: {eg['k_II_aplicado']:.3f})")
    print(f"  · α_cr,arco={eg['alpha_cr_arco']:.1f} (informativo, NÃO é o "
          f"critério) | H_imp={eg['H_imp_kN']:.2f} kN | "
          f"w/f_c={eg['w_over_f']:.5f}")
    print(f"  · {eg['metodo_analise']}: {eg['conclusao'][:80]}…")

    # Impacto de veículo — estacionamento coberto (EN 1991-1-7)
    print("\n[FASE 2] Impacto de veículo em pilares (estacionamento)...")
    res_elu["impacto_veiculo"] = verificar_impacto_veiculo(
        geo=geo, mat=mat_elu, load=load,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        b_pilar_c=B_PILAR_C, h_pilar_c=H_PILAR_C,
        H_pilar_m=H_PILAR_ALT,
    )
    iv = res_elu["impacto_veiculo"]
    _print_eta("Impacto veículo (A_d)", iv)
    print(f"  · F_dx={iv['forcas']['F_dx_kN']:.0f} kN / "
          f"F_dy={iv['forcas']['F_dy_kN']:.0f} kN @ "
          f"h={iv['forcas']['h_imp_m']:.2f} m | "
          f"k_mod={iv['k_mod']:.2f} (instantânea)")
    print(f"  · Gov: {iv['gov']} | η={iv['eta']:.4f}")
    print(f"  · {iv['recomendacao'][:90]}…")

    # Situação transitória de IÇAMENTO da viga (montagem — EN 1991-1-6; issue 26)
    print("\n[FASE 2] Içamento da viga (montagem — EN 1991-1-6)...")
    from mlc_projeto.checks.elu.icamento import verificar_icamento
    res_elu["icamento"] = verificar_icamento(
        geo=geo, mat=mat_elu,
        a_rel=A_ICAM_REL, gamma_G=GAMMA_G_ICAM, phi_dyn=PHI_DYN_ICAM,
        psi_sling_deg=PSI_LINGA_DEG, spreader=SPREADER_ICAM,
    )
    _ic = res_elu["icamento"]
    _print_eta("Içamento §EN1991-1-6", _ic)
    print(f"  · {_ic['esquema']} | W={_ic['W_total_kN']:.0f} kN "
          f"(γ_G·φ_dyn·g) | R/ponto={_ic['R_ponto_kN']:.0f} kN")
    print(f"  · M⁻={_ic['M_neg_kNm']:.0f} | M⁺={_ic['M_pos_kNm']:.0f} kN·m | "
          f"V={_ic['V_max_kN']:.0f} kN | N_c(lingas)={_ic['N_c_kN']:.0f} kN")
    print(f"  · LTB (sem contravento): l_ef={_ic['l_ef_LTB_m']:.1f} m | "
          f"k_crit={_ic['k_crit']:.3f} | η_LTB={_ic['eta_LTB']:.3f}")
    print(f"  · η governante ({_ic['eta_gov_key']}) = {_ic['eta']:.4f}")

    print("\n[FASE 2] Verificações ELU — Terças (flexão cobertura)...")
    from mlc_projeto.checks.elu.tercas import verifica_terca
    from mlc_projeto.core.wind import calcular_vento as _calcular_vento
    _w_C1bv_m2 = _calcular_vento(params_vento).pressoes["C1"]["barlavento_kNm2"]
    res_elu["terca"] = verifica_terca(
        mat       = mat_elu,
        L_t       = L_T,
        s         = S,
        b         = B_TERCA,
        h         = H_TERCA,
        alpha_deg = GEO_PARAMS["alpha_deg"],
        g_k_m2    = g_area_terca,   # terça: cobertura + peso próprio da terça (issue 1)
        q_k_m2    = Q_AREA,
        w_kNm2    = _w_C1bv_m2,
    )
    res_elu["terca"]["eta"] = res_elu["terca"]["eta_gov"]
    _print_eta("Terça flexão §6.1.6+§6.1.7", res_elu["terca"])

    # Terça-biela: flexão + compressão COMBINADAS — EC5 §6.3.2 Eq.6.23/6.24
    # (issue 16). Substitui os dois η isolados (flexão + compressão) por um
    # único η combinado, na MESMA combinação ELU (concomitância real).
    from mlc_projeto.checks.elu.tercas import verifica_terca_flexocompressao
    _F_terca = float(res_elu["contraventamento"].get("F_terca_kN", 0.0))
    res_elu["terca_flexocomp"] = verifica_terca_flexocompressao(
        mat       = mat_elu,
        L_t       = L_T,
        s         = S,
        b         = B_TERCA,
        h         = H_TERCA,
        alpha_deg = GEO_PARAMS["alpha_deg"],
        g_k_m2    = g_area_terca,
        q_k_m2    = Q_AREA,
        w_kNm2    = _w_C1bv_m2,
        N_c_kN    = _F_terca,
    )
    _tfc = res_elu["terca_flexocomp"]
    _print_eta("Terça-biela flexo-comp. §6.3.2", _tfc)
    print(f"  · N_c={_tfc['N_c_kN']:.1f} kN (estab. §9.2.5) + M cobertura "
          f"[{_tfc['comb']}] → interação COMBINADA")
    print(f"  · σ_c={_tfc['sigma_c_MPa']:.3f} | σ_m,y={_tfc['sigma_my_MPa']:.3f} | "
          f"σ_m,z={_tfc['sigma_mz_MPa']:.3f} MPa (f_md={_tfc['f_md_MPa']:.2f})")
    print(f"  · k_c,y={_tfc['k_c_y']:.3f} (λ_y={_tfc['lambda_y']:.0f}) | "
          f"k_c,z={_tfc['k_c_z']:.3f} (λ_z={_tfc['lambda_z']:.0f}) | "
          f"η_6.23={_tfc['eta_623']:.3f} η_6.24={_tfc['eta_624']:.3f} → "
          f"η={_tfc['eta']:.4f} ({_tfc['verif_gov']})")

    # Terça sob carga concentrada Q_k (cat. H — alternativa à UDL; issue 34)
    from mlc_projeto.checks.elu.tercas import verifica_terca_carga_concentrada
    res_elu["terca_Qk_conc"] = verifica_terca_carga_concentrada(
        mat=mat_elu, L_t=L_T, s=S, b=B_TERCA, h=H_TERCA,
        g_k_m2=g_area_terca, Q_k_kN=QK_CONC_KN,
    )
    _qk = res_elu["terca_Qk_conc"]
    _print_eta("Terça Q_k conc. §EN1991-1-1", _qk)
    print(f"  · Q_k={_qk['Q_k_kN']:.1f} kN a meio-vão (não concomit. c/ UDL nem vento) | "
          f"M_d={_qk['M_d_kNm']:.2f} kN·m (dur. média, k_mod={_qk['k_mod']:.2f})")
    print(f"  · η_flex={_qk['eta_flexao']:.4f} | η_cis={_qk['eta_cisalh']:.4f} → "
          f"η={_qk['eta']:.4f} | vs UDL η_flex={res_elu['terca']['eta_flexao']:.3f} "
          f"(a mais desfavorável governa)")
    print(f"  · Telha: M_local,d={_qk['M_telha_d_kNm']:.3f} kN·m/m → ficha do "
          f"fabricante (issue 17)")

    # Fixação telha→terça sob sucção — NBR 6123 (verificação local, issue 17)
    print("\n[FASE 2] Fixação telha→terça (sucção — NBR 6123)...")
    from mlc_projeto.checks.elu.fixacao_telha import verificar_fixacao_telha_succao
    # AUD-005: elementos de vedação e suas fixações são Classe A (§5.3.2 a)),
    # com S2 do topo da edificação (§5.3.3). O vento GLOBAL da estrutura
    # (classe B) não serve para a verificação local.
    params_vento_local = replace(params_vento, classe="A")
    res_elu["fixacao_telha"] = verificar_fixacao_telha_succao(
        params_vento = params_vento_local,
        s_terca      = S,
        g_telha_kNm2 = G_TELHA_KNM2,
        e_fix_m      = E_FIX_TELHA_M,
        R_fix_k_kN   = R_FIX_K_KN,
    )
    _fx = res_elu["fixacao_telha"]
    _print_eta("Fixação telha §NBR6123", _fx)
    print(f"  · q={_fx['q_kNm2']:.3f} kN/m² (classe {_fx['classe_vento']}, "
          f"z={_fx['z_ref_m']:.2f} m) | c_p=±{_fx['cp_vedacao']:.1f} (§7.2.6) | "
          f"R_fix,d={_fx['R_fix_d_kN']:.2f} kN (R_k={_fx['R_fix_k_kN']:.1f} típico)")
    print(f"  · e_fix={_fx['e_fix_m']:.2f} m (a cada nervura) | "
          f"η={_fx['eta']:.3f} | e_fix máx p/ η≤1: {_fx['e_fix_req_m']:.2f} m")
    print(f"  ⚠ {_fx['caveat']}")

    # ── Fase 3: Verificações ELS ──────────────────────────────────────────────
    print("\n[FASE 3] Verificações ELS...")

    res_els = {}
    res_els["ELS"] = verificar_ELS(geo, mat_longa, load)
    _print_eta("ELS §2.3.2.2+Tab.7.2", res_els["ELS"])

    # AUD-006 (resíduo A): contrapartida do modelo H=0 — os springings ABREM.
    # O afastamento simétrico é grau de liberdade distinto do sway: o diafragma
    # trava a translação (legitimando l_ef=1,0·H) mas não o afastamento.
    from mlc_projeto.checks.elu.empuxo_acoplado import (
        empuxo_no_frontao, verificar_abertura_springings,
    )
    res_els["abertura_springings"] = verificar_abertura_springings(
        geo, E_Pa=mat_longa.E0_mean,
        H_rigido_kN=load.H_rigido_ELU(),
        k_apoio_kNpm=0.0,          # Opção B: springing horizontalmente livre
    )
    _ab = res_els["abertura_springings"]
    _print_eta("Abertura springings (ELS)", _ab)
    print(f"  · δ por springing={_ab['delta_springing_mm']:.2f} mm | "
          f"total={_ab['delta_total_mm']:.2f} mm ≤ {_ab['lim_mm']:.1f} mm "
          f"({_ab['lim_rel']}) | k_arco={_ab['k_arco_kNpm']:,.0f} kN/m")

    # AUD-006 (resíduo B): a cruz do frontão liga os dois topos de pilar, logo
    # AQUELE pórtico atrai empuxo — demanda adicional no painel e na fundação
    # do frontão que o modelo H=0 dos pórticos internos não entrega.
    res_els["empuxo_frontao"] = empuxo_no_frontao(
        geo, E_Pa=mat_elu.E0_mean, H_rigido_kN=load.H_rigido_ELU(),
        b_baia_m=geo.L, H_col_m=H_PILAR_ALT, d_diag_mm=D_BARRA_CV_MM,
    )
    _ef = res_els["empuxo_frontao"]
    print(f"  · Frontão atrai H={_ef['H_dev_kN']:.2f} kN "
          f"({100*_ef['fracao_do_rigido']:.1f}% do rígido {_ef['H_rigido_kN']:.1f} kN) | "
          f"k_cruz={_ef['k_cruz_kNpm']:,.0f} vs k_arco={_ef['k_arco_kNpm']:,.0f} kN/m")

    # ── Fase 4a: Tirante de base (opcional — fecho do empuxo) ─────────────────
    H_arco = float(load.H_ELU())
    n_linhas_port = int(round(L_COMP_GALPAO / L_T)) + 1  # eixos Y (pórticos)

    # Auditoria do empuxo acoplado (issue 38): quanto de H realmente se desenvolve
    # dada a rigidez horizontal real do apoio (pilar biarticulado = mecanismo).
    print("\n[FASE 4a] Auditoria do empuxo acoplado (issue 38 — coerência do modelo)...")
    _gov_grav = load.combinacao_ELU_governante()   # max |M| (gravidade)
    res_empuxo = analisar_empuxo_acoplado(
        geo=geo, E_Pa=mat_longa.E0_mean,
        H_rigido_kN=abs(float(_gov_grav.H_rigido_kN)),  # empuxo RÍGIDO (auditoria)
        q_gov_kNpm=abs(float(_gov_grav.q_tot)),
        b_pilar=B_PILAR, h_pilar=H_PILAR, H_pilar=H_PILAR_ALT,
    )
    res_elu["empuxo_acoplado"] = res_empuxo
    relatorio_empuxo_acoplado(res_empuxo)
    res_tirante: dict = {"ativo": False, "ok": True, "eta": 0.0}
    if TIRANTE_BASE:
        print(f"\n[FASE 4a] Tirante de base (H_arco → tirante, H_sapata≈0)...")
        res_tirante = verificar_tirante_base(
            T_d_kN=H_arco,
            L_m=geo.L,
            aco=ACO_TIRANTE,
            d_mm=D_TIRANTE_MM,
            eta_alvo=ETA_TIRANTE_ALVO,
            n_vaos_por_linha=2,          # dois vãos de 20,25 m
            n_linhas=n_linhas_port,
        )
        relatorio_tirante(res_tirante)
        # Impacto da flexibilidade axial do tirante sobre H (issue 24)
        _imp_tir = impacto_flexibilidade_tirante(
            geo, E_glulam_MPa=mat_longa.E0_mean / 1e6,
            H_rigid_kN=H_arco, d_mm=res_tirante["d_mm"], aco=ACO_TIRANTE,
        )
        res_tirante["impacto_flexibilidade"] = _imp_tir
        print(f"  · Hipótese: H por Castigliano com APOIO HORIZONTAL RÍGIDO "
              f"(flexibilidade axial do tirante não realimentada).")
        print(f"  · Rigidez horizontal: arco={_imp_tir['k_arco_kNmm']:.0f} kN/mm | "
              f"tirante={_imp_tir['k_tirante_kNmm']:.0f} kN/mm | "
              f"δ_tirante={_imp_tir['delta_tirante_mm']:.1f} mm")
        print(f"  · H_rígido é conservador p/ o tirante (T=H máx); a restrição "
              f"paralela (ancoragem+contravento) mantém H≈rígido → sem acoplar.")
        # Robustez do tirante no piso — impacto/corrosão/fogo/tropeço (issue 37)
        _rob_tir = verificar_robustez_tirante_piso(
            d_mm=res_tirante["d_mm"], aco=ACO_TIRANTE,
            T_d_kN=res_tirante["T_d_kN"], L_m=geo.L,
            eta_alvo=ETA_TIRANTE_ALVO,
            protecao=PROTECAO_TIRANTE, primario=TIRANTE_PRIMARIO,
        )
        res_tirante["robustez_piso"] = _rob_tir
        res_elu["tirante_piso_robustez"] = _rob_tir
        print(f"  [issue 37] Robustez no piso (estacionamento):")
        relatorio_robustez_tirante(_rob_tir)
    else:
        print("\n[FASE 4a] Tirante de base: inativo (empuxo → sapata)")

    # ── Fase 4: Ligações ──────────────────────────────────────────────────────
    print(f"\n[FASE 4] Ligações (η_alvo = {ETA_LIG_ALVO:.2f} — uso público)...")

    res_lig = dimensionar_ligacoes(
        mat=mat_elu, load=load, geo=geo,
        d_base_mm=D_BASE_MM,
        F_chu_kN=F_CHU_KN,
        eta_alvo=ETA_LIG_ALVO,
        com_tirante=TIRANTE_BASE,
        b_pilar_m=B_PILAR,
        h_pilar_m=H_PILAR,
        dados_ancoragem=DADOS_ANCORAGEM,
    )
    # Sem L2 (cumeeira): peça monolítica contínua no ápice (issue 25).
    for key, label in [
        ("L1", f"L1 base (d={D_BASE_MM}mm, "
               f"{res_lig['L1']['n_linha']}×{res_lig['L1']['n_linhas']})"),
        ("L3", f"L3 sapata (n_chu={res_lig['L3']['n_chumbadores']})"),
    ]:
        _print_eta(label, res_lig[key])
    print(f"  · L1: n={res_lig['L1']['n_pinos']} pinos | "
          f"n_ef,row={res_lig['L1']['n_ef_row']:.2f} | "
          f"n_ef={res_lig['L1']['n_ef']:.1f} | "
          f"F_Rd/pino={res_lig['L1']['F_v_Rd_kN']:.2f} kN | "
          f"R={res_lig['L1']['R_total_kN']:.0f} kN | "
          f"L_lig={res_lig['L1'].get('L_ocupado_mm', 0):.0f} mm")
    L3r = res_lig["L3"]
    if TIRANTE_BASE:
        print(f"  · L3: H_arco={L3r.get('H_arco_kN', H_arco):.1f} kN → tirante | "
              f"H_sapata={L3r['H_d_kN']:.1f} kN | "
              f"n_chu={L3r['n_chumbadores']} constr. | "
              f"η_N={L3r.get('eta_N', L3r['eta']):.4f} | "
              f"σ_c={L3r.get('sigma_c_MPa', 0):.3f} MPa")
    else:
        print(f"  · L3: H={L3r['H_d_kN']:.1f} kN | "
              f"n_chu={L3r['n_chumbadores']} "
              f"(mín η≤1: {L3r.get('n_chu_eta1', '?')}; "
              f"grade×4: {L3r.get('n_chu_x4', '?')}) | "
              f"F_chu={L3r['F_chu_kN']:.0f} kN | "
              f"R={L3r.get('R_chu_kN', L3r['n_chumbadores']*L3r['F_chu_kN']):.0f} kN")

    res_lig_c = dimensionar_ligacoes_central(
        mat=mat_elu, load=load, geo=geo,
        b_pilar_c=B_PILAR_C,
        h_pilar_c=H_PILAR_C,
        d_base_mm=D_BASE_MM,
        eta_alvo=ETA_LIG_ALVO,
    )
    for key, label in [
        ("L1c", f"L1c central (d={D_BASE_MM}mm, 2 chapas)"),
        ("L3c", "L3c sapata central"),
    ]:
        _print_eta(label, res_lig_c[key])
    L3c = res_lig_c["L3c"]
    print(f"  · L3c: N={L3c['N_d_kN']:.1f} kN (2·R_v) | H≈0 (empuxos cancelam) | "
          f"σ_c={L3c.get('sigma_c_MPa', 0):.3f} MPa | "
          f"η_N={L3c.get('eta_N', L3c['eta']):.4f} | "
          f"n_chu={L3c['n_chumbadores']} construtivo (η_H=0)")

    # ── Esquadro de chapas — espessura SAI do dimensionamento (issue 23) ───────
    print("\n[FASE 4] Esquadro de chapas (dimensões + espessura; issue 23)...")
    from mlc_projeto.connections.chapas_dim import esquadro_chapas
    esquadro = esquadro_chapas(
        res_lig, res_lig_c, geo,
        b_pilar_m=B_PILAR, h_pilar_m=H_PILAR,
        b_pilar_c_m=B_PILAR_C, h_pilar_c_m=H_PILAR_C,
        aco=ACO_CHAPA_LIG,   # d do chumbador lido de cada sapata (não é o pino)
    )
    res_elu["esquadro_chapas"] = esquadro
    for k in ("L1", "L1c", "L3", "L3c"):
        c = esquadro[k]
        print(f"  · {k} ({c['tipo']}): {c['largura_mm']:.0f}×{c['altura_mm']:.0f} mm | "
              f"t_req={c['t_req_mm']:.1f} → t_adot={c['t_adotada_mm']:.1f} mm "
              f"(governa {c['t_governa']})")
    print("  → L1/L1c: t≥d=24 mm (chapa central rígida p/ rótula do pino) → 25 mm; "
          "corrige os 16 mm arbitrados da issue 21.")

    # ── Ruptura de bloco (EC5 Anexo A) — grupos de cavilhas L1/L1c (issue 19) ──
    print("\n[FASE 4] Ruptura de bloco (EC5 Anexo A) — L1/L1c...")
    from mlc_projeto.connections.connections import ruptura_de_bloco_ligacao
    res_bloco_L1 = ruptura_de_bloco_ligacao(res_lig["L1"], geo, mat_elu)
    res_bloco_L1c = ruptura_de_bloco_ligacao(res_lig_c["L1c"], geo, mat_elu)
    res_elu["ruptura_bloco_L1"] = res_bloco_L1
    res_elu["ruptura_bloco_L1c"] = res_bloco_L1c
    for lbl, rb in [("L1", res_bloco_L1), ("L1c", res_bloco_L1c)]:
        _print_eta(f"Ruptura bloco {lbl} (Anexo A)", rb)
        print(f"  · {lbl}: F_par={rb['F_par_kN']:.0f} kN | "
              f"tração={rb['term_tracao_kN']:.0f} kN, cisalh={rb['term_cisalh_kN']:.0f} kN "
              f"→ F_bs,Rk={rb['F_bs_Rk_kN']:.0f} (governa {rb['governa']}) | "
              f"F_bs,Rd={rb['F_bs_Rd_kN']:.0f} kN | η={rb['eta']:.3f} "
              f"(η só-cisalh={rb['eta_so_cisalh']:.3f})")

    # ── Fendilhamento (EC5 §8.1.4) — componente ⊥ fibras em L1/L1c (issue 20) ──
    print("\n[FASE 4] Fendilhamento (EC5 §8.1.4) — L1/L1c...")
    from mlc_projeto.connections.connections import fendilhamento_ligacao
    # reforcar=True: se o fendilhamento (frágil) passar do alvo, dimensiona
    # reforço ⊥ às fibras (parafusos §8.7.2) — decisão de projeto (issue 35/38,
    # Opção B: sem empuxo o cortante do beiral sobe e a ligação exige reforço).
    res_fend_L1 = fendilhamento_ligacao(res_lig["L1"], geo, mat_elu,
                                        reforcar=True, eta_reforco_alvo=ETA_LIG_ALVO)
    res_fend_L1c = fendilhamento_ligacao(res_lig_c["L1c"], geo, mat_elu,
                                         reforcar=True, eta_reforco_alvo=ETA_LIG_ALVO)
    res_elu["fendilhamento_L1"] = res_fend_L1
    res_elu["fendilhamento_L1c"] = res_fend_L1c
    for lbl, rf in [("L1", res_fend_L1), ("L1c", res_fend_L1c)]:
        _print_eta(f"Fendilhamento {lbl} §8.1.4", rf)
        print(f"  · {lbl}: F_90,Ed=|V_d|={rf['F_90_Ed_kN']:.0f} kN | "
              f"h_e={rf['h_e_mm']:.0f} mm (h_e/h={rf['h_e_h']:.2f}) | "
              f"F_90,Rd={rf['F_90_Rd_kN']:.0f} kN | η_nu={rf.get('eta_fendilhamento_nu', rf['eta']):.3f}")
        if rf.get("reforcado"):
            rr = rf["reforco"]
            print(f"    ↳ REFORÇADO (§8.7.2): {rr['n_parafusos']}×∅{rr['d_mm']:.0f} mm "
                  f"l_ef={rr['l_ef_mm']:.0f} mm → η_reforço={rr['eta']:.3f} "
                  f"(arranc.={rr['eta_arrancamento']:.2f}, aço={rr['eta_aco']:.2f})")

    # ── Componente metálico (EN 1993-1-8) — chapa, furos, soldas (issue 21) ────
    print("\n[FASE 4] Chapas de aço / furos / soldas (EN 1993-1-8) — L1/L1c...")
    from mlc_projeto.connections.chapas_aco import chapas_aco_ligacao
    # Espessura da chapa SAI do esquadro/dimensionamento (issue 23), não arbitrada.
    _t_L1 = esquadro["L1"]["t_adotada_mm"]
    _t_L1c = esquadro["L1c"]["t_adotada_mm"]
    res_aco_L1 = chapas_aco_ligacao(
        res_lig["L1"], geo, t_p_mm=_t_L1, a_solda_mm=A_SOLDA_MM, aco=ACO_CHAPA_LIG)
    res_aco_L1c = chapas_aco_ligacao(
        res_lig_c["L1c"], geo, t_p_mm=_t_L1c, a_solda_mm=A_SOLDA_MM, aco=ACO_CHAPA_LIG)
    res_elu["chapa_aco_L1"] = res_aco_L1
    res_elu["chapa_aco_L1c"] = res_aco_L1c
    for lbl, ra in [("L1", res_aco_L1), ("L1c", res_aco_L1c)]:
        _print_eta(f"Chapa aço {lbl} EN1993-1-8", ra)
        print(f"  · {lbl} {ra['aco']} t={ra['t_p_mm']:.0f}mm: "
              f"pino η={ra['eta_pino_cisalh']:.3f} | bearing η={ra['eta_furo_bearing']:.3f} | "
              f"sec.líq η={ra['eta_chapa_liquida']:.3f} ({ra['net_gov']}) | "
              f"solda η={ra['eta_solda']:.3f} → gov {ra['eta_gov_key']} η={ra['eta']:.3f}")
    print(f"  ⚠ {res_aco_L1['nota_declarado']}")

    # ── Critério η-alvo 0,75: aplicação CONSISTENTE por modo de falha (issue 22) ──
    print("\n[FASE 4] Critério η-alvo das ligações (issue 22)...")
    from mlc_projeto.connections.connections import (
        aplicar_criterio_eta, ETA_ALVO_LIGACAO,
    )
    _L3_tirante = bool(res_lig["L3"].get("com_tirante", False))
    # (chave em res, modo_frágil?) — frágil: madeira (embutimento/bloco/fendilh.)
    # e ancoragem frágil no concreto (chumbadores sem tirante). Dúctil/compressão:
    # concreto sob a chapa (L3 c/ tirante, L3c), compressão da madeira (cumeeira/seção), aço.
    _classificacao = [
        (res_lig["L1"],          True),
        (res_lig["L3"],          not _L3_tirante),
        (res_lig_c["L1c"],       True),
        (res_lig_c["L3c"],       False),
        (res_elu["ruptura_bloco_L1"],  True),
        (res_elu["ruptura_bloco_L1c"], True),
        (res_elu["fendilhamento_L1"],  True),
        (res_elu["fendilhamento_L1c"], True),
        (res_elu["chapa_aco_L1"],      False),
        (res_elu["chapa_aco_L1c"],     False),
    ]
    _nomes = ["L1", "L3", "L1c", "L3c",
              "bloco L1", "bloco L1c", "fendilh. L1", "fendilh. L1c",
              "chapa L1", "chapa L1c"]
    _viol = []
    print(f"  Alvo {ETA_ALVO_LIGACAO:.2f} = margem p/ modos FRÁGEIS (sem redistribuição):")
    for (rc, frag), nm in zip(_classificacao, _nomes):
        aplicar_criterio_eta(rc, modo_fragil=frag, eta_alvo=ETA_LIG_ALVO)
        _eta = float(rc.get("eta", 0.0))
        tag = "FRÁGIL→0,75" if frag else "dúctil→1,0 "
        flag = "" if rc["ok"] else "  ✗ VIOLA"
        if frag and not rc["ok_alvo"]:
            _viol.append(nm)
        print(f"    {nm:<13} η={_eta:.4f}  [{tag}]  lim={rc['eta_limite']:.2f}  "
              f"{'✓' if rc['ok'] else '✗'}{flag}")
    if _viol:
        print(f"  ⚠ Modos frágeis ACIMA de {ETA_LIG_ALVO:.2f}: {', '.join(_viol)} "
              f"(revisar dimensionamento).")
    else:
        print(f"  ✓ Todos os modos frágeis ≤ {ETA_LIG_ALVO:.2f}; "
              f"exceções (η≤1,0) são compressão no concreto/madeira e aço dúctil.")

    # ── Fase 4b: Fadiga e deslizamento das ligações ───────────────────────────
    print("\n[FASE 4b] Fadiga e deslizamento — EC5 §2.4 + §7.1 + §8.1.5...")

    res_fadiga = verificar_fadiga_deslizamento(
        mat=mat_longa, load=load, geo=geo,
        res_lig=res_lig, res_lig_c=res_lig_c,
        H_pilar=H_PILAR_ALT, psi_2=0.0,
    )

    for cod, r in res_fadiga.items():
        status = "✓" if r["slip_ok"] and r["alternada"]["ok"] else "✗"
        print(f"  {status} {cod:<6}  "
              f"η_slip={r['eta_slip']:.4f}  "
              f"η_alt={r['alternada']['eta_alt']:.4f}")

    # ── Fase 4c: Combinação de sucção — uplift + empuxo invertido (issue 33) ───
    print("\n[FASE 4c] Sucção/uplift — ancoragem e tirante frouxo...")
    # Tração de contraventamento concomitante na base de canto (issue 36):
    # envelope conservador Σ dos dois painéis (long. + transv.).
    _N_brace_anc = float(
        res_elu.get("contraventamento_vertical", {}).get("N_uplift_kN", 0.0)
        + res_elu.get("contraventamento_transversal", {}).get("N_uplift_kN", 0.0)
    )
    res_succao = verificar_succao_uplift(
        load=load, geo=geo,
        F_chu_kN=F_CHU_KN, n_chu=int(res_lig["L3"]["n_chumbadores"]),
        b_pilar=B_PILAR, h_pilar=H_PILAR, H_pilar_m=H_PILAR_ALT,
        rho_mean_kgm3=mat_longa.rho_mean,
        com_tirante=TIRANTE_BASE,
        N_brace_anc_kN=_N_brace_anc,
        # Ancoragem PRÓPRIA do canto: dimensionada pelo uplift + downloads dos
        # dois painéis, e não pelo mínimo construtivo das demais bases.
        n_chu_canto=N_CHU_CANTO,
        # Cortante que os painéis entregam à base de canto, na mesma combinação
        # de vento que produz o arrancamento (antes não era verificado).
        V_brace_kN=float(cvv["H_base_kN"]) + float(cvt["H_base_kN"]),
        chaveta_cisalhamento=CHAVETA_CISALHAMENTO_CANTO,
    )
    res_elu["succao_uplift"] = res_succao
    _print_eta("Sucção/uplift (ancoragem)", res_succao)
    print(f"  · Sucção {res_succao['comb']}: R_v={res_succao['R_A_kN']:+.1f} kN "
          f"(uplift) | H={res_succao['H_suc_kN']:+.1f} kN "
          f"({'invertido → tirante frouxo' if res_succao['tirante_frouxo'] else 'ok'})")
    print(f"  · Extremidade: N_uplift={res_succao['N_uplift_ext_kN']:.1f} kN + "
          f"V_base={res_succao['V_base_ext_kN']:.1f} kN → η_ext={res_succao['eta_ext']:.3f} "
          f"(ancoragem {res_succao['n_chu']}×{res_succao['F_chu_kN']:.0f} kN)")
    print(f"  · Central: N_uplift={res_succao['N_uplift_cen_kN']:.1f} kN → "
          f"η_cen={res_succao['eta_cen']:.3f}")
    print(f"  · Canto (uplift+contravent., issue 36): "
          f"N={res_succao['N_uplift_ext_kN']:.1f}+{res_succao['N_brace_anc_kN']:.1f}="
          f"{res_succao['N_uplift_canto_kN']:.1f} kN → η_canto={res_succao['eta_canto']:.3f} "
          f"| governa: {res_succao['base_gov']}")

    # ── Ancoragem do canto — chumbadores moldados com cabeça ───────────────
    from mlc_projeto.connections.ancoragem import verificar_grupo_ancoragem
    res_elu["ancoragem_canto"] = verificar_grupo_ancoragem(
        N_Ed_kN=float(res_succao["N_uplift_canto_kN"]),
        V_Ed_kN=float(res_succao["V_canto_kN"]),
        n_chumbadores=N_CHU_CANTO,
        d_mm=D_CHU_MM, classe=CLASSE_CHU,
        chaveta_cisalhamento=CHAVETA_CISALHAMENTO_CANTO,
        layout=LAYOUT_CHU,
        dados_concreto=DADOS_ANCORAGEM,
    )
    _anc = res_elu["ancoragem_canto"]
    print("\n[FASE 4d] Ancoragem do canto — chumbadores moldados com cabeça...")
    _print_eta("Ancoragem canto (aço)", _anc)
    print(f"  · {_anc['n_chumbadores']}×M{_anc['d_mm']} classe {_anc['classe']} | "
          f"N_Rd={_anc['N_Rd_grupo_kN']:.0f} kN | V_Rd={_anc['V_Rd_grupo_kN']:.0f} kN "
          f"(γ_Ms={_anc['gamma_Ms']})")
    print(f"  · N_Ed={_anc['N_Ed_kN']:.1f} kN | V_Ed={_anc['V_Ed_kN']:.1f} kN "
          f"→ chaveta={'sim' if _anc['chaveta_cisalhamento'] else 'não'}, "
          f"V nos chumbadores={_anc['V_nos_chumbadores_kN']:.1f} kN")
    print(f"  · η_N={_anc['eta_N']:.3f} | η_V={_anc['eta_V']:.3f} | "
          f"η_interação={_anc['eta_interacao']:.3f} → aço {'OK' if _anc['ok_aco'] else 'FALHA'}")
    print(f"  · Concreto: h_ef={H_EF_CHU_MM:.0f} c={C_BORDA_CHU_MM:.0f} "
          f"s={S_GRUPO_CHU_MM:.0f} mm | N_Rd,cone={_anc['N_Rd_cone_kN']:.0f} kN | "
          f"N_Rd,pull-out={_anc['N_Rd_pullout_kN']:.0f} kN → governa {_anc['modo_concreto_gov']}")
    print(f"  · β_N={_anc['beta_N']:.3f} | β_V={_anc['beta_V']:.3f} | "
          f"η_concreto={_anc['eta_concreto']:.3f} ({_anc['norma_concreto']})")
    print(f"  ⚠ Ainda pendentes: {', '.join(_anc['modos_ainda_pendentes'])}")
    print(f"  ⚠ A fundação deve garantir bloco com c ≥ {C_BORDA_CHU_MM:.0f} mm "
          f"em torno do grupo (≈ {(S_GRUPO_CHU_MM+2*C_BORDA_CHU_MM)/1000:.2f}×"
          f"{(2*S_GRUPO_CHU_MM+2*C_BORDA_CHU_MM)/1000:.2f} m em planta)")

    # ── Quadro de cargas para a fundação ───────────────────────────────────
    # O projeto NÃO dimensiona fundações (não há sondagem). O entregável é o
    # conjunto de esforços que chega a cada base, para o projeto de fundações.
    from mlc_projeto.output.cargas_fundacao import (
        imprimir_quadro, montar_quadro_cargas_fundacao,
    )
    quadro_fund = montar_quadro_cargas_fundacao(
        load=load, res_succao=res_succao,
        cv_vertical=cvv, cv_transversal=cvt,
        n_pilares_linha=n_pil_linha, n_linhas_portico=3,
        n_paineis_long=N_PAINEIS_CV_VERT,
        n_paineis_transv=N_PAINEIS_CV_TRANSV,
    )
    imprimir_quadro(quadro_fund)

    # ── Pacote de resultados (terminal / Excel / memorial) ─────────────────────
    todos_para_relatorio = {
        "cargas_fundacao": quadro_fund,
        **res_elu,
        **res_els,
        **({"tirante_base": res_tirante} if res_tirante.get("ativo") else {}),
        "L1":  res_lig["L1"],
        "L3":  res_lig["L3"],
        "L1c": res_lig_c["L1c"],
        "L3c": res_lig_c["L3c"],
        "fadiga_L1": {
            "eta": res_fadiga["L1"]["eta_slip"],
            "ok":  res_fadiga["L1"]["slip_ok"] and res_fadiga["L1"]["alternada"]["ok"],
            "eta_slip": res_fadiga["L1"]["eta_slip"],
            "eta_alt":  res_fadiga["L1"]["alternada"]["eta_alt"],
            "u_inst_mm": res_fadiga["L1"]["u_inst_mm"],
            "u_fin_mm":  res_fadiga["L1"]["u_fin_mm"],
            "descricao": res_fadiga["L1"]["descricao"],
        },
        "fadiga_L1c": {
            "eta": res_fadiga["L1c"]["eta_slip"],
            "ok":  res_fadiga["L1c"]["slip_ok"] and res_fadiga["L1c"]["alternada"]["ok"],
            "eta_slip": res_fadiga["L1c"]["eta_slip"],
            "eta_alt":  res_fadiga["L1c"]["alternada"]["eta_alt"],
            "u_inst_mm": res_fadiga["L1c"]["u_inst_mm"],
            "u_fin_mm":  res_fadiga["L1c"]["u_fin_mm"],
            "descricao": res_fadiga["L1c"]["descricao"],
        },
        "k_def": mat_longa.k_def,
        "meta": {
            "candidato": "R2",
            "s": S,
            "l_ap": L_AP,
            "area_trib": load.area_trib,
            "g_area": g_area,
            "g_area_terca": g_area_terca,
            "peso_proprio": pp,   # parcelas discriminadas (issue 1)
            "q_area": Q_AREA,
            "sistema": "biarticulada" + (" + tirante base" if TIRANTE_BASE else ""),
            "classe_servico": mat_elu.classe_servico,
            "eta_lig_alvo": ETA_LIG_ALVO,
            "d_base_mm": D_BASE_MM,
            "F_chu_kN": F_CHU_KN,
            "b_pilar": B_PILAR,
            "h_pilar": H_PILAR,
            "b_pilar_c": B_PILAR_C,
            "h_pilar_c": H_PILAR_C,
            "H_pilar": H_PILAR_ALT,
            "gov_nome": gov.nome,
            "gov_padrao_vento": gov.padrao_vento,
            "H_ELU_kN": load.H_ELU(),
            "H_arco_kN": H_arco,
            "H_sapata_kN": 0.0 if TIRANTE_BASE else H_arco,
            "com_tirante": TIRANTE_BASE,
            # Atrito longitudinal §7.2.2 (F-13 encerrado) — coeficiente e a
            # escala da ação face ao arrasto de bloqueio, para o memorial.
            "coef_atrito": load.vento_0.get("coef_atrito"),
            "razao_bloqueio": load.vento_0.get("razao_bloqueio"),
            "nota_bloqueio": load.vento_0.get("nota_bloqueio", ""),
            # F-04: exclusões DECLARADAS. Na Opção B (EMPUXO_DESENVOLVE=False) o
            # tirante de base não tem função — mas a sua ausência tem de ser uma
            # decisão registada no memorial, não uma linha que desaparece.
            "nao_aplicaveis": (
                () if TIRANTE_BASE
                else ("tirante_base", "tirante_piso_robustez")
            ),
            "T_tirante_kN": res_tirante.get("T_d_kN", 0.0),
            "d_tirante_mm": res_tirante.get("d_mm", 0.0),
            "aco_tirante": res_tirante.get("aco", ACO_TIRANTE),
            "M_max_kNm": gov.M_max_kNm,
            # Critério k_mod / vento — memorial
            "duracao_vento": "curta",
            "k_mod_vento": mat_elu.com_duracao("curta").k_mod,
            "k_mod_vento_instantanea": mat_elu.com_duracao("instantanea").k_mod,
            "criterio_kmod_vento": (
                "Vento classificado como duração curta (EC5 §2.3.1.2 / Tab. 3.1), "
                "não como instantânea — critério conservador de projeto."
            ),
            "varredura_vento_90": load.varredura_vento_90,
            "durabilidade": DURABILIDADE,   # issue 30
        },
    }

    # Resumo unificado (terminal = Excel = memorial §12)
    resumo = _imprimir_resumo_export(
        todos_para_relatorio, load, todos_para_relatorio["meta"],
    )
    todos_para_relatorio["meta"]["eta_max"] = resumo["eta_max"]
    todos_para_relatorio["meta"]["status"] = resumo["status"]
    todos_para_relatorio["meta"]["n_verif"] = resumo["n_verif"]

    # ── Fase 5: Relatório ─────────────────────────────────────────────────────
    print("\n[FASE 5] Export relatório (Excel + LaTeX/PDF)...")
    gerar_relatorio(
        todos_para_relatorio,
        geo,
        mat_longa,
        nome="relatorio_mlc",
        load=load,
    )
    print("\nPipeline concluído. Relatório gerado em output/")
    print(f"  Status global = {resumo['status']} | η_max = {resumo['eta_max']:.4f}")

    # ── Fase 6: Visualização 3D (opcional) ────────────────────────────────────
    if abrir_viz:
        print("\n[FASE 6] Abrindo visualização 3D interativa...")
        visualizar_galpao(
            geo        = geo,
            resultados = todos_para_relatorio,
            H_pilar   = H_PILAR_ALT,
            n_modulos = 8,
            dist_mod  = L_T,
            b_pilar   = B_PILAR,
            h_pilar   = H_PILAR,
            b_pilar_c = B_PILAR_C,
            h_pilar_c = H_PILAR_C,
            b_terca   = B_TERCA,
            h_terca   = H_TERCA,
        )
    else:
        print("\n[FASE 6] Visualização 3D omitida (abrir_viz=False)")

    return todos_para_relatorio


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Pipeline MLC UFPR")
    ap.add_argument("--varredura", action="store_true")
    ap.add_argument("--sem-viz", action="store_true",
                    help="Não abrir visualização 3D (útil para export)")
    args = ap.parse_args()
    main(rodar_varredura=args.varredura, abrir_viz=not args.sem_viz)