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
from pathlib import Path
from dataclasses import replace
from mlc_projeto.core.geometry   import GeometriaViga
from mlc_projeto.core.materials  import GlulamMaterial
from mlc_projeto.core.wind       import ParametrosVento
from mlc_projeto.core.loads      import carregamentos_com_vento, peso_proprio_gk
from mlc_projeto.core.normativo  import (
    NDP_SOURCE, CONFIG_NORMATIVA, parametros_a_confirmar,
    OMISSOES_CONSERVADORAS,
)

from mlc_projeto.predim.predim   import pre_dimensionar, relatorio

from mlc_projeto.checks.elu.cumeeira          import verifica_cumeeira
from mlc_projeto.checks.elu.misula            import verifica_misula
from mlc_projeto.checks.elu.flambagem_lateral import (
    verifica_flambagem_lateral, verifica_flambagem_lateral_succao,
)
from mlc_projeto.checks.elu.flexao            import verifica_flexao
from mlc_projeto.checks.elu.cisalhamento      import verifica_cisalhamento
from mlc_projeto.checks.elu.apoio             import (
    reacao_arrancamento_max, verifica_apoio_contato, verifica_sela_central,
)
from mlc_projeto.checks.elu.flexo_compressao  import verifica_flexo_compressao
from mlc_projeto.checks.els.deflection_els    import verificar_ELS

from mlc_projeto.checks.elu.contraventamento  import verificar_contraventamento
from mlc_projeto.checks.elu.contraventamento_vertical import (
    verificar_contraventamento_vertical,
    reparticao_alinhamentos,
)
from mlc_projeto.checks.elu.contraventamento_transversal import (
    verificar_contraventamento_transversal,
)
from mlc_projeto.checks.elu.estabilidade_global import (
    verificar_estabilidade_global, relatorio_estabilidade_global,
)
from mlc_projeto.checks.elu.fogo import (
    verificar_fogo, reacao_vertical_incendio,
)
from mlc_projeto.connections.ligacao_diagonal import dimensionar_ligacao_diagonal
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

# Referência à função real: o apêndice de memória (issue 50) só é escrito quando
# o relatório é gerado de fato — os testes substituem `gerar_relatorio`.
_gerar_relatorio_real = gerar_relatorio

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

# --- Incêndio: tempo requerido (EN 1995-1-2 dá o MÉTODO, não o R) -------------
# O R vem do regulamento nacional (ABNT NBR 14432 / IT do CBM estadual), não do
# Eurocódigo. Fica declarado em NDP_SOURCE como PROJETO-A-CONFIRMAR e é lido
# daqui para que exista UM só valor no projeto.
R_FOGO_REQ_MIN = float(NDP_SOURCE["R_fogo_req_min"].valor)   # min

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
H_PILAR_ALT = 7.0      # m — do topo da chapa de base ao apoio da viga (nó a nó)
# Pilarete metálico (issue 87): eleva a madeira acima da zona de respingo. O pé
# do pilar de madeira fica no topo do pilarete, H_PILARETE_M acima do piso
# acabado (= topo do bloco de fundação); a madeira mede H_PILAR_ALT − H_PILARETE_M.
# Painéis de contraventamento, estabilidade global e caminho à fundação seguem
# com H_PILAR_ALT (as diagonais ligam-se à chapa de base, abaixo do pilarete).
H_PILARETE_M = 0.30    # m — topo da chapa de topo do pilarete acima do piso
H_PILAR_MAD  = H_PILAR_ALT - H_PILARETE_M   # m — comprimento da peça de madeira
H_IMP_PISO_M = 0.50    # m — altura do choque de veículo acima do piso (EN 1991-1-7)
B_PILAR_C   = 0.32     # m — central idêntico
H_PILAR_C   = 0.27     # m
# Pilar de CANTO — montante do painel longitudinal E do frontão transversal.
# Recebe os dois downloads de contraventamento além da reação de gravidade,
# somando ~3× a carga do pilar lateral. Até aqui reutilizava a seção do lateral,
# o que o tornava o gargalo do sistema. Passa a ter seção própria.
B_PILAR_CANTO = 0.32   # m — mantém a largura da viga (fabricação/ligação)
H_PILAR_CANTO = 0.32   # m — engrossado de 0,27 (ver varredura no bloco do CV)
# Pilar BIPARTIDO dos 14 montantes das baías rígidas (issue 104): duas lâminas de
# MLC, uma de cada lado da viga, da base até a escora; a diagonal CV-V e a escora
# concorrem no topo da lâmina, e a componente vertical desce // às fibras. Os
# montantes de canto, laterais e centrais deixam de ser pilares maciços.
from mlc_projeto.checks.elu.pilar_bipartido import FOLGA_ESCORA_VIGA_MM  # noqa: E402
from mlc_projeto.checks.elu.pilar_bipartido import (  # noqa: E402
    B_LAMINA_M as B_LAMINA, H_LAMINA_M as H_LAMINA, geometria as _geo_bipartido,
)
#: nó da diagonal CV-V 100 mm abaixo do extradorso no apoio (sob a escora)
DZ_NO_ESCORA_M = 0.10

# --- Terças — seção DIMENSIONADA (issue 101; predim/varredura_terca.py) -------
# Espaçamento fixo s = L/8 (painéis do contraventamento, l_1 da viga); seção
# única para correntes, de ponta, corda do diafragma e escoras. Varredura de
# seções comerciais com o pipeline completo; critério: APROVADO e η ≤ 0,75 em
# todas as verificações que dependem da terça. Menor área aprovada:
#   0,20×0,36 → η 0,83 (nó)   0,18×0,40 → 0,96   0,20×0,40 → 0,74  ← adotada
#   0,20×0,58 (anterior, dado de entrada) → 0,74, com 45 % a mais de madeira
# Governa a ligação da escora central ao nó de topo (altura para as fileiras de
# cavilhas); as verificações da barra ficam abaixo de 0,44.
B_TERCA = 0.20
H_TERCA = 0.40
B_ESCORA_CENTRAL = 0.24  # m — escora central (T9 nas baías contraventadas da linha B): com o
                         # vento majorado (issue 109), N ≈ 351 kN e a flambagem no eixo fraco
                         # pede peça mais larga que a terça corrente (decisão do autor)

# --- Beiral e oitões (issue 82) -----------------------------------------------
# Projeção da cobertura além da face externa dos pilares de perímetro, para
# proteger da chuva os topos das vigas e das terças, as ligações de topo e o
# trecho superior dos pilares, sem alterar a área interna:
#   · beirais (alinhamentos A e C): a viga prolonga-se em balanço além do apoio;
#   · oitões (eixos 1 e 9): as terças prolongam-se em balanço além do frontão.
# Os balanços medem-se do EIXO do apoio: projeção + meia dimensão do pilar.
A_BEIRAL_M = 1.00   # m — projeção do beiral além da face do pilar (A e C)
A_OITAO_M  = 1.00   # m — projeção do oitão além da face do pilar (eixos 1 e 9)
A_BAL_VIGA_M  = A_BEIRAL_M + H_PILAR / 2.0        # 1,135 m — balanço da viga
A_BAL_TERCA_M = A_OITAO_M + B_PILAR_CANTO / 2.0   # 1,160 m — balanço da terça
GEO_PARAMS["a_bal"] = A_BAL_VIGA_M

# --- Içamento da viga (montagem — EN 1991-1-6; issue 26) ----------------------
# Esquema confirmado: 2 pontos a 0,207·L (|M⁻|=|M⁺|); lingas inclinadas (compressão
# axial), viga SEM contraventamento (LTB no vão entre pontos). Confirmar no plano de
# montagem/rigging. γ_G peso próprio, φ_dyn amplificação dinâmica do içamento.
A_ICAM_REL = None      # pontos de içamento: posição que iguala |M⁻| e |M⁺| (issue 100)
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
# Cruzes de St. André nas DUAS baías de extremidade, em TODOS os painéis do vão
# (8 painéis de s=2,53 m por água): cada baía é uma treliça paralela às vigas
# que vence ℓ = vão da viga = 20,25 m (EC5 §9.2.5.3, Fig. 9.10) — issue 41.
# ℓ NÃO é o comprimento da edificação (46 m) nem a distância entre baías:
# k_ℓ = min(1,√(15/20,25)) = 0,86. O número de baías rígidas só altera n
# (vigas estabilizadas por sistema: ⌈9/2⌉ = 5), e mais baías reduzem a força.
#
# A diagonal do painel extremo é governada pelo vento θ=0° (§7.2.2), não pela
# estabilização (N_d pequeno no modelo biapoiado). Varredura de diâmetro:
#   Ø22 → η=1,28, cobertura_ok=False   (reprova)
#   Ø25 → η=0,99, cobertura_ok=True    (sem margem)
#   Ø28 → η=0,79, cobertura_ok=True    ← adotado
#   Ø30 → η=0,69
L_COMP_GALPAO   = 46.0    # m — comprimento do galpão
N_MODULOS_CV    = 2       # baías rígidas (extremos) — define n por sistema (issue 41)
D_BARRA_CV_MM   = 28.0    # mm — diâmetro MÍNIMO da diagonal da cobertura; o pipeline
                          # escolhe o menor comercial com η ≤ ETA_CV_COB (issue 109)
ETA_CV_COB      = 0.90    # alvo do aço (dúctil, rosca recalcada)
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
#
# ── ISSUE 64 (Opção A) — linha central contraventada ─────────────────────────
# As treliças da cobertura (issue 41) apoiam-se no beiral E no alinhamento
# central, que não tinha caminho longitudinal à fundação. Agora a força
# longitudinal reparte-se 1/2 fachadas (1/4 por beiral) + 1/2 linha central.
# Varredura (pipeline real, diagonal auto η ≤ 0,90):
#   fachada/central   η pilar central montante   η canto   status
#        8 / 2              1,01                  0,34     REPROVA (Ø48 central)
#        8 / 4              0,74                  0,34     aprova, 12 baías ocupadas
#        4 / 4              0,74                  0,43     aprova, 8 baías ← adotado
#        4 / 2              1,01                  0,43     REPROVA
# Adota-se 4 + 4: as mesmas 8 baías ocupadas de antes e a mesma força por
# painel (≈106 kN). Fachadas: 1 painel por extremidade em cada fachada, sob as
# baías rígidas da cobertura. Linha central: 2 painéis por extremidade.
N_PAINEIS_CV_VERT = 4       # painéis de cruz nas FACHADAS (força longitudinal)
N_PAINEIS_CV_CENTRAL = 4    # painéis de cruz na LINHA CENTRAL (2 por extremidade)
# Bases centrais montantes: somam o uplift central de sucção (2 vãos) ao
# arrancamento do painel e recebem o cortante dele — ancoragem própria igual à
# do canto (6 chumbadores M24 + chaveta), verificada pela EN 1992-4.
N_CHU_CENTRAL_CV = 6
# Escoras do nó de topo das baías contraventadas (issue 66): a terça sobre o
# apoio (beiral / linha central) leva a reação longitudinal da treliça da
# cobertura ao nó metálico do topo do pilar; ligação axial por cavilhas.
D_ESCORA_MM = 20
D_BARRA_CVV_MM    = None    # mm — None → auto (comercial, η ≤ ETA_CVV_ALVO)
ACO_CVV           = "S235"
ETA_CVV_ALVO      = 0.90    # margem de projeto na diagonal vertical

# --- Contraventamento TRANSVERSAL (issue 31, Opção 2) — diafragma + frontões
# Diafragma de cobertura leva o vento θ=90° + nocional aos frontões
# contraventados (cruzes de St. André), e destes à fundação. Valida l_ef=1H
# (non-sway) dos pilares no plano do pórtico.
N_PAINEIS_CV_TRANSV = 1     # painéis de cruz por frontão
# Pilar de frontão (issue 52): 2º montante da cruz, a L_T do canto, um por
# frontão. Não apoia a viga; entra no arrasto de vento das duas direções.
N_PILARES_FRONTAO   = 2 * N_PAINEIS_CV_TRANSV
D_BARRA_CVT_MM      = None  # mm — None → auto (comercial, η ≤ ETA_CVT_ALVO)
ACO_CVT             = "S235"
ETA_CVT_ALVO        = 0.90  # margem de projeto na diagonal do frontão
# Rigidez (issue 110, decisão do autor): o diâmetro da CV-T é também o menor que leva
# o deslocamento transversal do SISTEMA (painel do frontão + diafragma da cobertura) a
# η ≤ ETA_DESLOC_TRANSV do limite H/300, para dar folga ao α_cr transversal.
ETA_DESLOC_TRANSV   = 0.75

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
# Espessura do bloco de fundação — REQUISITO publicado ao projetista de
# fundações, não um dado que a superestrutura conheça (achado A4). O
# fendilhamento de §7.2.1.7 só deixa de reduzir a resistência do cone quando
# h >= 2·h_ef; abaixo disso ψ_h,sp < 1 e a ancoragem tem de ser reverificada.
H_BLOCO_FUND_MM = 2.0 * H_EF_CHU_MM       # 800 mm
# Chaveta de cisalhamento (bloco soldado sob a chapa de base). Desacopla o
# corte dos chumbadores — e cria a verificação de esmagamento do concreto
# (EN 1992-1-1 §6.7), que estava declarada como pendente.
CHAVETA_L_MM = 200.0    # comprimento em contacto com o concreto
CHAVETA_H_MM = 80.0     # altura embutida
T_CHAVETA_MM = 30.0     # espessura da chaveta (barra chata) — braço entre cordões
# Bases correntes (L3, L3c, L3f) — issue 74: chaveta CRUCIFORME (dois braços de
# 200 × 80 mm), porque o choque de veículo pode vir de qualquer direção; com ela,
# o cortante não passa pelos chumbadores, que sem chaveta, sobre graute e porca de
# nivelamento, trabalhariam com braço de alavanca (EN 1992-4 §6.2.2.3).
CHAVETA_CRUZ = {"l_mm": CHAVETA_L_MM, "h_mm": CHAVETA_H_MM, "classe_concreto": "C25/30",
                "tipo": "cruciforme"}
DADOS_ANCORAGEM = {
    "h_ef_mm": H_EF_CHU_MM,
    "h_bloco_mm": H_BLOCO_FUND_MM,
    "A_cabeca_mm2": A_CABECA_CHU_MM2,
    "c_borda_mm": C_BORDA_CHU_MM,
    "s_grupo_mm": S_GRUPO_CHU_MM,
    "classe_concreto": CLASSE_CONC_FUND,
    "concreto_fissurado": CONCRETO_FISSURADO,
    "verificacao_en1992_4": "EN 1992-4:2018 §7.2.1.4/7.2.1.5/7.4.1.4/7.2.3",
}
# Bases ancoradas dos MONTANTES (canto e central montante): com o vento longitudinal
# majorado (issue 109) o arrancamento passa de ~357 para ~449 kN e o cone com h_ef=400
# chega a η≈0,85 > 0,75 (modo frágil). Embutimento maior e chaveta mais longa só nelas;
# as bases correntes mantêm h_ef=400 e a chaveta cruciforme de 200 mm.
H_EF_CHU_MONT_MM    = 500.0
C_BORDA_CHU_MONT_MM = 1.5 * H_EF_CHU_MONT_MM          # 750 mm
H_BLOCO_FUND_MONT_MM = 2.0 * H_EF_CHU_MONT_MM         # 1.000 mm
CHAVETA_L_MONT_MM   = 260.0
DADOS_ANCORAGEM_MONT = dict(DADOS_ANCORAGEM, h_ef_mm=H_EF_CHU_MONT_MM,
                            c_borda_mm=C_BORDA_CHU_MONT_MM, h_bloco_mm=H_BLOCO_FUND_MONT_MM)
ETA_LIG_ALVO = 0.75    # margem de projeto L1/L3 (uso público; frágil em madeira)
# --- Apoio da viga no pilar — CONTATO DIRETO (issue 42) ----------------------
# A reação vertical de gravidade vai por contato (viga sobre chapa de topo do
# pilar; no pilar central, sobre SELA metálica), não pelos pinos — elimina a
# força ⊥ às fibras nos pinos que levava o fendilhamento a η≈0,96 e exigia
# parafusos de reforço. Os pinos (furos ovalizados verticais na chapa) ficam só
# para o arrancamento (sucção) e o esforço axial, no terço superior da viga.
# (Antes: L_AP = 0,90 m — placa fictícia, maior que o pilar de 0,27 m.)
L_AP            = H_PILAR   # m — apoio no pilar lateral = dimensão no plano (0,27)
L_SELA_POR_VIGA = 0.25      # m — apoio de cada viga na sela do pilar central
# Detalhamento (issue 52) — valores construtivos declarados:
T_CHAPA_TOPO_MM = 16.0      # mm — chapa de topo do pilar lateral e do PF (como a sela)
# Curso vertical dos furos ovalizados de L1/L1c: CALCULADO (issue 72,
# connections/oblongo_L1.py) — para baixo, retração + fluência ⊥ + elástica;
# para cima, inchamento; montagem a 15 ± 2 % de umidade.
FOLGA_SELA_M    = 0.02      # m — folga entre as duas vigas sobre a sela
FOLGA_RASGO_MM  = 2.0       # mm — folga de cada lado da chapa embutida no rasgo (issue 70)

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


from mlc_projeto.output.formatacao import fmt_eta  # noqa: E402


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
    # issue 53: η com duas casas, arredondado para cima (output/formatacao.py)
    print(f"  {ok} {nome:<30} η = {fmt_eta(eta, decimal='.')}  {bar}")


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
        eta_txt = "       —" if math.isnan(eta) else f"{fmt_eta(eta, decimal='.'):>8}"
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
    print(f"  η máximo     = {fmt_eta(eta_max, decimal='.')}")
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
        "n_executadas": est["n_executadas"],
        "n_nao_aplicaveis": len(est["nao_aplicaveis"]),
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


def arranjo_kwargs(res: dict) -> dict:
    """Argumentos do arranjo dos desenhos (fonte única para o pipeline e para o
    teste de equivalência cálculo × desenho, issue 116)."""
    ob = res["oblongo_L1"]
    return dict(
        n_eixos=round(L_COMP_GALPAO / L_T) + 1,
        L_T=L_T, H_pilar=H_PILAR_ALT, b_pilar=B_PILAR, h_pilar=H_PILAR,
        b_canto=B_PILAR_CANTO, h_canto=H_PILAR_CANTO, b_terca=B_TERCA,
        h_terca=H_TERCA, d_chu_mm=D_CHU_MM, h_ef_mm=H_EF_CHU_MM,
        c_borda_mm=C_BORDA_CHU_MM, h_bloco_mm=H_BLOCO_FUND_MM,
        chaveta_L_mm=CHAVETA_L_MM, chaveta_H_mm=CHAVETA_H_MM,
        classe_concreto=CLASSE_CONC_FUND, l_sela_viga_m=L_SELA_POR_VIGA,
        folga_sela_m=FOLGA_SELA_M, t_chapa_topo_mm=T_CHAPA_TOPO_MM,
        folga_oblongo_L1_mm=(ob["c_cima_mm"], ob["c_baixo_mm"]),
        a_oit=A_BAL_TERCA_M, a_beiral_mm=A_BEIRAL_M * 1000,
        ancoragem_mont={"h_ef_mm": H_EF_CHU_MONT_MM, "c_borda_mm": C_BORDA_CHU_MONT_MM,
                        "h_bloco_mm": H_BLOCO_FUND_MONT_MM,
                        "chaveta_L_mm": CHAVETA_L_MONT_MM})


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
    vento_kw["l2"] = 2 * geo.L + 2 * geo.a_bal   # profundidade com os beirais (issue 82)
    params_vento = ParametrosVento(**vento_kw)

    # θ=90° Tab.25 completo + θ=0° longitudinal (pilares + contraventamento)
    # n_pilares_linha ≈ L_comp/dist + 1; n_linhas = 3 (2 pórticos + central compartilhado)
    L_COMP = 46.0
    n_pil_linha = max(2, round(L_COMP / L_T) + 1)
    # Dimensões em planta da COBERTURA (atrito §7.2.2), com beirais e oitões
    B_COB_M = 2 * geo.L + 2 * geo.a_bal
    L_COB_M = L_COMP + 2 * A_BAL_TERCA_M
    load = carregamentos_com_vento(
        geo=geo, mat=mat_curta,
        g_area=g_area, q_area=Q_AREA,
        L_t=L_T, params_vento=params_vento,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        n_pilares_linha=n_pil_linha,
        n_linhas_portico=3,
        L_cob_m=L_COB_M,     # com os oitões (issue 82)
        B_cob_m=B_COB_M,     # dois vãos lado a lado + beirais (issue 82)
        empuxo_desenvolve=EMPUXO_DESENVOLVE,   # Opção B (issue 35/38)
        n_pilares_extra=N_PILARES_FRONTAO,     # pilares de frontão (issue 52)
        # issue 117: terças como linhas de carga nas reações e no beiral
        P_terca_linha_kN=pp["gamma_kNm3"] * B_TERCA * H_TERCA * L_T, s_terca_m=S,
    )

    gov = load.combinacao_ELU_governante()
    # k_mod da duração da combinação governante — EC5 §3.1.3
    mat_elu = mat_curta.com_duracao(gov.duracao)

    # Issue 45 — sobrecarga dominante + vento acompanhante (ψ0,W=0,6) dispensada
    # pela EN 1991-1-1:2002/AC:2009 §3.3.2(1); demonstra-se que não altera a viga.
    comb_QW = load.combinacao_Q_com_vento_acompanhante(mat=mat_curta)

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
    print(f"  Q+0,6W    : dispensada (EN 1991-1-1 §3.3.2(1)); {comb_QW['n_padroes_pressao']} "
          f"padrões de pressão → M={comb_QW['M_QW_kNm']:.1f} vs ELU_Q "
          f"{comb_QW['M_ELU_Q_kNm']:.1f} kN·m; M/k_mod relativo "
          f"{comb_QW['razao_utilizacao']:.3f} (altera: "
          f"{'SIM' if comb_QW['altera_dimensionamento'] else 'não'})")
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

    # ── Reservas normativas obrigatórias ──────────────────────────────────────
    # Estavam definidas (ConfiguracaoNormativa.aviso / .aviso_nbr) e não eram
    # emitidas em lado nenhum. Um aviso que não se imprime não é um aviso.
    print(f"\n  RESERVAS NORMATIVAS:")
    print(f"    · {load.aviso_ndp}")
    print(f"    · {load.aviso_nbr}")
    # Achado B2 — o híbrido NBR 6123 (ação) × EN 1990 (combinação). Os γ e ψ do
    # EN 1990 foram calibrados contra a EN 1991-1-4, não contra a rajada de 3 s
    # da NBR. É a decisão de projeto de maior alcance no memorial e não estava
    # escrita em lado nenhum.
    print(f"    · {CONFIG_NORMATIVA.aviso_hibrido()}")
    # Achado B1 — decisões de classificação por tomar. Enquanto existirem, o
    # memorial não pode afirmar a classe de fiabilidade nem o tempo de fogo.
    # Achado A6 — fatores de majoração que o EC5 permite e o projeto NÃO usa.
    # Omitir é conservador, e por isso passa despercebido; não declarar deixa o
    # leitor sem saber se foi decisão ou esquecimento.
    print(f"    · {len(OMISSOES_CONSERVADORAS)} majorações NÃO aplicadas "
          f"(conservador, declarado): "
          + ", ".join(sorted(OMISSOES_CONSERVADORAS)))
    _pend = parametros_a_confirmar()
    if _pend:
        print(f"    · {len(_pend)} PARÂMETRO(S) A CONFIRMAR PELO PROJETISTA: "
              + ", ".join(sorted(_pend)))
        for _k in sorted(_pend):
            print(f"        - {_k} = {_pend[_k].valor!r} ({_pend[_k].clausula})")

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
    print(f"  Layout: {N_MODULOS_CV} baías rígidas (extremos), cruzes em todo o vão | "
          f"ℓ = vão da viga = {geo.L:.2f} m | "
          f"diagonal ≥ ∅{D_BARRA_CV_MM:.0f} mm {ACO_CV} (auto, η ≤ {ETA_CV_COB:.2f})")
    print("  Critério: EC5 §9.2.5.3 — treliça paralela às vigas, ℓ = vão do sistema")

    from mlc_projeto.checks.elu.contraventamento_vertical import D_COMERCIAL_MM as _D_COM

    def _cv_cobertura(k_crit: float) -> dict:
        """Menor diâmetro comercial ≥ D_BARRA_CV_MM com η_diag ≤ ETA_CV_COB (issue 109)."""
        r = None
        for _d in [d for d in _D_COM if d >= D_BARRA_CV_MM]:
            r = verificar_contraventamento(
                geo=geo, mat=mat_elu, load=load,
                L_comp=L_COMP_GALPAO, n_modulos_cv=N_MODULOS_CV,
                s_terca=S, d_barra_mm=float(_d), aco=ACO_CV,
                n_porticos=2, dist_portico=L_T,
                b_terca=B_TERCA, h_terca=H_TERCA, k_crit=k_crit)
            if r["eta_diag_N"] <= ETA_CV_COB + 1e-9:
                break
        return r

    res_elu["contraventamento"] = _cv_cobertura(1.0)   # 1.ª passagem; refinado após LTB
    _print_eta("Cobertura §9.2.5", res_elu["contraventamento"])
    cv0 = res_elu["contraventamento"]
    l_1_ltb = float(cv0["l_1_efetivo_m"])
    print(f"  → l_1 LTB = {l_1_ltb:.3f} m | {cv0['l_1_nota']}")
    print(f"  → diagonal Ø{cv0['d_barra_mm']:.0f}, rosca recalcada M{cv0['d_rosca_mm']} "
          f"(N_u={cv0['N_u_Rd_kN']:.1f} ≥ N_pl={cv0['N_pl_Rd_kN']:.1f} kN)")
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
    res_elu["contraventamento"] = _cv_cobertura(k_crit_ltb)
    l_1_ltb = float(res_elu["contraventamento"]["l_1_efetivo_m"])
    # Se o refinamento mudou a validade, reavaliar LTB uma vez
    if abs(l_1_ltb - float(res_elu["flambagem"]["l_1_m"])) > 1e-6:
        res_elu["flambagem"] = verifica_flambagem_lateral(
            geo, mat_elu, load, l_1=l_1_ltb
        )
        _print_eta("Flambagem §6.3.3 (recalc.)", res_elu["flambagem"])

    # Issue 47 — sucção: momento negativo comprime o INTRADORSO, não contido
    # pelas terças. l_1 = vão (contenção só nos apoios), varredura em x.
    res_elu["flambagem_succao"] = verifica_flambagem_lateral_succao(geo, mat_elu, load)
    _fs = res_elu["flambagem_succao"]
    _print_eta("Flambagem §6.3.3 sucção (intradorso)", _fs)
    if _fs.get("aplicavel"):
        print(f"  · {_fs['comb_gov']} | x={_fs['x_m']:.2f} m, h={_fs['h_m']:.3f} m, "
              f"M={_fs['M_d_kNm']:.1f} kN·m | l_ef={_fs['l_ef_m']:.2f} m (0,9·L) | "
              f"λ_rel={_fs['lambda_rel_m']:.3f} k_crit={_fs['k_crit']:.3f}")

    res_elu["flexao"] = verifica_flexao(geo, mat_elu, load, s=l_1_ltb)
    _print_eta("Flexo-comp. §6.3.2+6.35", res_elu["flexao"])

    # Rasgo da chapa embutida (issue 70): chapa t ≥ d (rígida, Johansen) na série
    # comercial + 2 mm de folga de cada lado; confere-se depois com o esquadro.
    from mlc_projeto.connections.chapas_dim import _adotar_comercial
    T_CHAPA_L1_MM = _adotar_comercial(float(D_BASE_MM))
    T_RASGO_M = (T_CHAPA_L1_MM + 2.0 * FOLGA_RASGO_MM) / 1000.0
    res_elu["cisalhamento"] = verifica_cisalhamento(geo, mat_elu, load, t_rasgo_m=T_RASGO_M)
    _print_eta("Cisalhamento §6.1.7", res_elu["cisalhamento"])

    res_elu["apoio"] = verifica_apoio_contato(
        geo, mat_elu, load, l_apoio_m=L_AP, rotulo="L1 (pilar lateral)", t_rasgo_m=T_RASGO_M,
        a_extremidade_m=A_BEIRAL_M)          # a viga continua no beiral (issue 82)
    # Pilar central: duas vigas sobre a sela — cada uma com L_SELA_POR_VIGA
    res_elu["apoio_central"] = verifica_apoio_contato(
        geo, mat_elu, load, l_apoio_m=L_SELA_POR_VIGA, rotulo="L1c (sela central)",
        t_rasgo_m=T_RASGO_M)
    res_elu["sela_central"] = verifica_sela_central(
        sigma_contato_MPa=res_elu["apoio_central"]["sigma_c90d_MPa"],
        l_apoio_viga_m=L_SELA_POR_VIGA, h_pilar_m=H_PILAR_C, folga_m=FOLGA_SELA_M)
    _print_eta("Apoio L1 contato §6.1.5", res_elu["apoio"])
    _print_eta("Apoio L1c sela §6.1.5", res_elu["apoio_central"])
    # Enrijecedores sob os balanços da sela (issue 73): garantem a pressão de
    # contato uniforme admitida no apoio; a chapa passa a vencer só o vão entre eles.
    from mlc_projeto.checks.elu.apoio import verifica_enrijecedores_sela
    _sl0 = res_elu["sela_central"]
    _enr = verifica_enrijecedores_sela(
        sigma_contato_MPa=res_elu["apoio_central"]["sigma_c90d_MPa"],
        balanco_m=_sl0["balanco_m"], b_contato_m=geo.b - T_RASGO_M,
        t_sela_mm=_sl0["t_adot_mm"],
        f_c90_d_MPa=mat_elu.com_duracao("media").f_c90_d / 1e6,
    )
    _sl0["enrijecedores"] = _enr
    _sl0["eta_sem_enrijecedor"] = _sl0["eta"]
    _sl0["eta"] = _enr["eta"]                   # com enrijecedores, governa o conjunto
    _sl0["ok"] = _enr["ok"]
    _print_eta("Sela central (placa)", res_elu["sela_central"])
    print(f"  · {_enr['n_enrij']} enrijecedores {_enr['dim_enrij_mm'][0]:.0f}×{_enr['dim_enrij_mm'][1]:.0f}"
          f"×{_enr['t_enrij_mm']:g} mm sob cada balanço | chapa entre eles: vão {_enr['vao_chapa_mm']:.0f} mm "
          f"(t_req {_enr['t_req_chapa_mm']:.1f}) | consolo F={_enr['F_enrij_kN']:.1f} kN | "
          f"flecha da ponta {_enr['flecha_ponta_sem_mm']:.2f} → {_enr['flecha_ponta_com_mm']:.3f} mm "
          f"| chapas laterais h={_enr['h_lateral_mm']:.0f}: C={_enr['C_face_kN']:.1f} kN, "
          f"p={_enr['p_face_MPa']:.2f} MPa na face do pilar | governa {_enr['governa']}")
    for _a in (res_elu["apoio"], res_elu["apoio_central"]):
        print(f"  · {_a['rotulo']}: R={_a['R_d_kN']:.1f} kN | l={_a['l_apoio_m']:.3f} → "
              f"l_ef={_a['l_ef_m']:.3f} m | σ={_a['sigma_c90d_MPa']:.3f} ≤ "
              f"{_a['k_c90']:.2f}·{_a['f_c90d_MPa']:.2f} MPa | η={_a['eta']:.3f} "
              f"(sem k_c,90: {_a['eta_sem_kc90']:.3f})")
    _sl = res_elu["sela_central"]
    print(f"  · Sela: {_sl['L_sela_m']:.2f} m sobre pilar {H_PILAR_C:.2f} m, balanço "
          f"{_sl['balanco_m']:.3f} m → t_req={_sl['t_req_mm']:.1f} mm, adota "
          f"{_sl['t_adot_mm']} mm S275")

    res_elu["flexo_comp"] = verifica_flexo_compressao(
        geo=geo, mat=mat_elu, load=load,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        H_pilar=H_PILAR_MAD, s=l_1_ltb,
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
        b=B_PILAR_C, h=H_PILAR_C, H=H_PILAR_MAD,
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
        mat=mat_elu, b=B_PILAR, h=H_PILAR, H=H_PILAR_MAD,
        N_d=_N_lat, params_vento=params_vento, theta_deg=0.0,
    )
    res_elu["pilar_vento_90"] = _pilar_vento(
        mat=mat_elu, b=B_PILAR, h=H_PILAR, H=H_PILAR_MAD,
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
              f"R_apoio treliça={res_elu['contraventamento'].get('R_ext_proj_kN', 0):.1f} kN "
              f"(estab={res_elu['contraventamento'].get('R_ext_estab_kN', 0):.1f}, "
              f"vento0={res_elu['contraventamento'].get('R_vento0_kN', 0):.1f})")

    # Carga vertical de cálculo TOTAL do galpão — base do α_cr de sistema
    # (EN 1993-1-1 Eq. 5.2). Achado F-02 da auditoria adversarial v2.
    _n_frames = max(2, round(L_COMP_GALPAO / L_T) + 1)
    V_ED_TOTAL_KN = 2.0 * 2 * abs(load.V_max_ELU()) * _n_frames

    # Contraventamento VERTICAL — caminho de carga lateral até a fundação (issue 14)
    print("\n[FASE 2] Contraventamento vertical (força lateral → fundação)...")
    # Issue 64 (Opção A): fachadas e linha central repartem a força longitudinal
    # na proporção das reações das treliças da cobertura (1/2 + 1/2).
    _rep_long = reparticao_alinhamentos(n_porticos=2)
    # Issue 104: o nó do painel fica no topo da lâmina do pilar bipartido, no nível
    # da escora — painel mais alto (até h0 − 0,10 acima do topo dos demais pilares)
    # e mais estreito (o nó fica ao lado da viga, y_nó do eixo do pilar)
    _gbp = _geo_bipartido(geo.b)
    H_PAINEL_CVV = H_PILAR_ALT + geo.h0 - DZ_NO_ESCORA_M
    B_BAIA_CVV = L_T - _gbp["y_no_mm"] / 1000.0
    res_elu["contraventamento_vertical"] = verificar_contraventamento_vertical(
        geo=geo, load=load,
        H_pilar_m=H_PAINEL_CVV, b_baia_long_m=B_BAIA_CVV,
        dist_portico=L_T,
        L_comp=L_COMP_GALPAO,
        n_porticos=2,
        n_paineis_long=N_PAINEIS_CV_VERT,
        aco=ACO_CVV,
        d_mm=D_BARRA_CVV_MM,
        eta_alvo=ETA_CVV_ALVO,
        # metade da força longitudinal coletada pelas treliças da cobertura
        # (a função soma as duas extremidades)
        R_ext_cobertura_kN=res_elu["contraventamento"].get("F_cobertura_total_kN", 0.0) / 2.0,
        V_Ed_total_kN=V_ED_TOTAL_KN,
        fracao_demanda=_rep_long["fachadas"], alinhamento="fachadas",
    )
    cvv = res_elu["contraventamento_vertical"]
    _print_eta("Contravento vertical §5.4", cvv)
    print(f"  · F_vento0,d=1,5×{cvv['F_vento0_k_kN']:.1f}={cvv['F_vento0_kN']:.1f} kN + H_imp={cvv['H_imp_kN']:.1f} kN "
          f"→ V_lat={cvv['V_lat_total_kN']:.1f} kN / {cvv['n_paineis']} painéis")
    print(f"  · Diagonal ∅{cvv['d_mm']:.0f} mm {cvv['aco']}, extremidade recalcada "
          f"M{cvv['d_rosca_mm']} (N_u={cvv['N_u_Rd_kN']:.1f} ≥ N_pl={cvv['N_pl_Rd_kN']:.1f} kN"
          f" → {'dúctil' if cvv['ductil'] else 'FRÁGIL'}) | β={cvv['beta_deg']}° | "
          f"N_diag={cvv['N_diag_kN']:.1f} kN | η_N={cvv['eta_diag_N']:.3f} | "
          f"η_δ={cvv['eta_delta']:.3f}")
    print(f"  · Caminho à fundação: H_base={cvv['H_base_kN']:.1f} kN + "
          f"arrancamento N_uplift={cvv['N_uplift_kN']:.1f} kN")
    print(f"  · α_cr,long={cvv['alpha_cr']} ({cvv['regime_alpha_cr']}) | "
          f"K_lat={cvv['K_lat_kNpm']:.0f} kN/m | k_II={cvv['k_II']:.3f}")

    # Linha CENTRAL — recebe a outra metade (issue 64, Opção A)
    res_elu["contraventamento_vertical_central"] = verificar_contraventamento_vertical(
        geo=geo, load=load,
        H_pilar_m=H_PAINEL_CVV, b_baia_long_m=B_BAIA_CVV,
        dist_portico=L_T,
        L_comp=L_COMP_GALPAO,
        n_porticos=2,
        n_paineis_long=N_PAINEIS_CV_CENTRAL,
        aco=ACO_CVV,
        d_mm=D_BARRA_CVV_MM,
        eta_alvo=ETA_CVV_ALVO,
        R_ext_cobertura_kN=res_elu["contraventamento"].get("F_cobertura_total_kN", 0.0) / 2.0,
        V_Ed_total_kN=V_ED_TOTAL_KN,
        fracao_demanda=_rep_long["internos"], alinhamento="central",
    )
    cvc = res_elu["contraventamento_vertical_central"]
    _print_eta("Contravento vertical central", cvc)
    print(f"  · {cvc['fracao_demanda']:.0%} da força longitudinal → "
          f"V_lat={cvc['V_lat_total_kN']:.1f} kN / {cvc['n_paineis']} painéis")
    print(f"  · Diagonal ∅{cvc['d_mm']:.0f} mm {cvc['aco']}, rosca recalcada M{cvc['d_rosca_mm']} | "
          f"N_diag={cvc['N_diag_kN']:.1f} kN | η_N={cvc['eta_diag_N']:.3f} | "
          f"η_δ={cvc['eta_delta']:.3f}")
    print(f"  · Caminho à fundação: H_base={cvc['H_base_kN']:.1f} kN + "
          f"download/arrancamento ±{cvc['N_uplift_kN']:.1f} kN no pilar central")

    # Contraventamento TRANSVERSAL — diafragma + frontões → fundação (issue 31)
    print("\n[FASE 2] Contraventamento transversal (diafragma + frontões → fund.)...")
    from mlc_projeto.checks.elu.diafragma_cobertura import verificar_diafragma_cobertura
    from mlc_projeto.checks.elu.contraventamento_vertical import D_COMERCIAL_MM as _D_COM_T
    from scipy.integrate import trapezoid as _trap_df

    def _cvt(d_mm):
        return verificar_contraventamento_transversal(
            geo=geo, load=load, params_vento=params_vento,
            H_pilar_m=H_PILAR_ALT, dist_portico=L_T, L_comp=L_COMP_GALPAO,
            n_porticos=2, b_pilar=B_PILAR, h_pilar=H_PILAR,
            n_paineis_por_gable=N_PAINEIS_CV_TRANSV, aco=ACO_CVT, d_mm=d_mm,
            eta_alvo=ETA_CVT_ALVO, V_Ed_total_kN=V_ED_TOTAL_KN,
            n_pilares_extra=N_PILARES_FRONTAO)

    def _diaf(cvt_):
        return verificar_diafragma_cobertura(
            L_T=L_T, n_eixos=round(L_COMP_GALPAO / L_T) + 1, s=S,
            n_faixas=2 * round(geo.L / S), A_terca_m2=B_TERCA * H_TERCA,
            A_viga_m2=float(_trap_df(geo.A(geo.x), geo.x)) / geo.L,
            E_mlc_kPa=mat_elu.E0_mean / 1e3,
            d_cvh_mm=float(res_elu["contraventamento"]["d_barra_mm"]),
            C_h_frontao_kNpm=float(cvt_["C_h_kNpm"]), C_h_long_kNpm=float(cvv["C_h_kNpm"]),
            H_tr_kN=float(cvt_["H_tr_kN"]), H_pilar_m=H_PILAR_ALT)

    # resistência (η ≤ ETA_CVT_ALVO) e rigidez do sistema (η_δ ≤ ETA_DESLOC_TRANSV)
    _cvt_r = _cvt(D_BARRA_CVT_MM)
    _df_r = _diaf(_cvt_r)
    for _d in [d for d in _D_COM_T if d > float(_cvt_r["d_mm"])]:
        if _df_r["eta_delta"] <= ETA_DESLOC_TRANSV + 1e-9:
            break
        _cvt_r = _cvt(float(_d))
        _df_r = _diaf(_cvt_r)
    res_elu["contraventamento_transversal"] = _cvt_r
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
    print(f"  · Frontão ∅{cvt['d_mm']:.0f} mm {cvt['aco']}, rosca recalcada M{cvt['d_rosca_mm']} (β={cvt['beta_deg']}°) | "
          f"N_diag={cvt['N_diag_kN']:.1f} kN | η_N={cvt['eta_diag_N']:.3f} | "
          f"η_δ={cvt['eta_delta']:.3f}")
    print(f"  · Caminho à fundação: H_base={cvt['H_base_kN']:.1f} kN + "
          f"N_uplift={cvt['N_uplift_kN']:.1f} kN | l_ef=1H (non-sway) validado")
    print(f"  · α_cr,transv={cvt['alpha_cr']} ({cvt['regime_alpha_cr']}) | "
          f"K_lat={cvt['K_lat_kNpm']:.0f} kN/m | k_II={cvt['k_II']:.3f}")

    # Alma do diafragma da cobertura (issue 110): modelo em planta com as liberações
    # reais; cruzes CV-D nas baías 2–8 além das CV-H. A rigidez equivalente substitui,
    # no α_cr transversal, a dos painéis dos frontões com diafragma rígido.
    print("\n[FASE 2] Diafragma da cobertura — alma nas baías intermediárias (issue 110)...")
    res_elu["diafragma_cobertura"] = _df_r
    # base do modelo em planta, reaproveitada na rigidez ao afastamento (issue 113)
    _N_EIXOS_DF = round(L_COMP_GALPAO / L_T) + 1
    _BASE_DIAF = dict(
        L_T=L_T, n_eixos=_N_EIXOS_DF, s=S, n_faixas=2 * round(geo.L / S),
        A_terca_m2=B_TERCA * H_TERCA, A_viga_m2=float(_trap_df(geo.A(geo.x), geo.x)) / geo.L,
        E_mlc_kPa=mat_elu.E0_mean / 1e3,
        C_h_frontao_kNpm=float(cvt["C_h_kNpm"]), C_h_long_kNpm=float(cvv["C_h_kNpm"]),
        d_diag_mm_por_baia=[float(_df_r["d_cvh_mm"])]
        + [float(_df_r["d_diafragma_mm"])] * (_N_EIXOS_DF - 3) + [float(_df_r["d_cvh_mm"])])
    _df = res_elu["diafragma_cobertura"]
    _print_eta("Diafragma da cobertura (alma)", _df)
    _c5 = _df["portico_central_100kN"]
    print(f"  · sem cruzes nas baías 2–8: {'MECANISMO (matriz singular)' if _df['sem_alma_mecanismo'] else 'estável'}")
    print(f"  · CV-D Ø{_df['d_diafragma_mm']:.0f} ({_df['n_barras_novas']} barras de {_df['L_diag_m']:.2f} m) | "
          f"F_diag máx {_df['F_diag_max_kN']:.1f} kN η={_df['eta_diag']:.3f} | CV-H ao transversal η={_df['eta_cvh_transversal']:.3f}")
    print(f"  · H_tr={cvt['H_tr_kN']:.1f} kN → frontões {_df['R_frontoes_kN']} kN | δ_máx={_df['delta_max_mm']:.1f} mm "
          f"≤ {_df['delta_lim_mm']:.1f} (H/300) η={_df['eta_delta']:.3f} | corda {_df['N_corda_max_kN']:.1f} kN | "
          f"K_eq={_df['K_eq_kNpm']:.0f} kN/m (painéis sós: {cvt['K_lat_kNpm']:.0f})")
    print(f"  · 100 kN no pórtico central → frontões {_c5['R_frontoes_kN']} kN | δ={_c5['delta_max_mm']:.1f} mm")

    # Ligações de EXTREMIDADE das diagonais — EN 1993-1-8 §3.13 (achado A3)
    #
    # A barra estava verificada (F-11: seção líquida da rosca); o que a segura
    # não existia. Detalhe: manilha → pino → chapa-olhal soldada. Dimensionado
    # por CAPACIDADE (N_t,Rd da barra), para que a plastificação fique no
    # tirante — dúctil — e não no pino ou na solda.
    print("\n[FASE 2] Ligações de extremidade das diagonais (EN 1993-1-8 §3.13)...")
    for _chave, _rot, _cv in (
        ("lig_diag_vertical",   "longitudinal", cvv),
        ("lig_diag_vertical_central", "linha central", cvc),
        ("lig_diag_transversal", "frontão",     cvt),
        # cruzes da alma do diafragma (issue 110)
        ("lig_diag_diafragma",   "diafragma",   {
            "N_diag_kN": res_elu["diafragma_cobertura"]["F_diag_max_kN"],
            "N_t_Rd_kN": res_elu["diafragma_cobertura"]["N_t_Rd_kN"],
            "d_mm": res_elu["diafragma_cobertura"]["d_diafragma_mm"]}),
        # diagonais da cobertura (issue 91): terminal pelo mesmo detalhe
        ("lig_diag_cobertura",   "cobertura",   {
            "N_diag_kN": res_elu["contraventamento"]["F_diag_kN"],
            "N_t_Rd_kN": res_elu["contraventamento"]["N_t_Rd_kN"],
            "d_mm": res_elu["contraventamento"]["d_barra_mm"]}),
    ):
        res_elu[_chave] = dimensionar_ligacao_diagonal(
            N_Ed_kN       = float(_cv["N_diag_kN"]),
            N_barra_Rd_kN = float(_cv["N_t_Rd_kN"]),
            d_barra_mm    = float(_cv["d_mm"]),
            aco_chapa     = "S235",
            aco_pino      = "S355",
            nome          = _chave,
        )
        _ld = res_elu[_chave]
        _print_eta(f"Lig. diagonal {_rot} §3.13", _ld)
        print(f"  · barra ∅{_cv['d_mm']:.0f} (N_Ed={_ld['N_Ed_real_kN']:.1f} kN, "
              f"N_t,Rd={_ld['N_barra_Rd_kN']:.1f} kN) → dimensionada por "
              f"{_ld['criterio']} com N={_ld['N_dimensionamento_kN']:.1f} kN "
              f"({_ld['sobre_resistencia']:.2f}× N_Ed)")
        print(f"  · pino ∅{_ld['d_pino_mm']:.0f} {_ld['aco_pino']} (corte duplo) | "
              f"olhal t={_ld['t_eye_mm']:.0f} mm {_ld['aco_chapa']}, "
              f"a={_ld['a_borda_mm']:.0f} (req {_ld['a_req_mm']:.1f}), "
              f"c={_ld['c_borda_mm']:.0f} (req {_ld['c_req_mm']:.1f}) mm")
        print(f"  · solda de ângulo a={_ld['a_solda_mm']:.0f} mm × "
              f"{_ld['l_solda_mm']:.0f} mm × {_ld['n_cordoes']} cordões | "
              f"F_w,Rd={_ld['F_w_Rd_kN']:.1f} kN")
        print(f"  · sob N_Ed: governa {_ld['modo_gov']}, η={_ld['eta']:.4f} | "
              f"sob a capacidade da barra: {_ld['modo_gov_capacidade']}, "
              f"η={_ld['eta_capacidade']:.4f}")
        print(f"  ⚠ {_ld['nota_manilha']}")

    # Montantes de contraventamento: pilar bipartido (issue 104), verificado
    # depois do choque de veículo, que dimensiona o pilarete de cada lâmina.

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
        # terças biapoiadas entre pórticos: uma junta da corda sobre cada viga
        # intermediária (issue 91), dimensionada em ligacao_terca_viga
        L_barra_m=L_T,
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

    # Nó de topo das baías contraventadas — escoras e ligações (issue 66)
    from mlc_projeto.checks.elu.no_contraventamento import verificar_no_contraventamento

    def _verificar_escora(N_kN: float, tipo: str) -> dict:
        # terça como peça flexo-axial: de beiral (tributária s/2) ou sobre a
        # linha central (tributária das duas águas, s)
        return verificar_corda_beiral(
            mat=mat_elu, N_corda_kN=N_kN, L_t=L_T,
            s_eave=(S / 2.0 if tipo == "beiral" else S),
            b=(B_TERCA if tipo == "beiral" else B_ESCORA_CENTRAL), h=H_TERCA,
            alpha_deg=GEO_PARAMS["alpha_deg"], g_k_m2=g_area_terca,
            q_k_m2=Q_AREA, w_kNm2=_w_corda, L_comp=L_COMP_GALPAO,
        )

    res_elu["no_contraventamento"] = verificar_no_contraventamento(
        mat_curta=mat_curta,
        V_painel_fachada_kN=float(cvv["V_painel_kN"]),
        V_painel_central_kN=float(cvc["V_painel_kN"]),
        n_paineis_central_por_extremidade=max(1, N_PAINEIS_CV_CENTRAL // 2),
        N_corda_diafragma_kN=float(cvt["N_corda_kN"]),
        verificar_escora=_verificar_escora,
        d_mm=float(D_ESCORA_MM), b_terca_m=B_TERCA, h_terca_m=H_TERCA,
        b_escora_central_m=B_ESCORA_CENTRAL,
    )
    _nc = res_elu["no_contraventamento"]
    print("\n[FASE 2] Nó de topo das baías contraventadas (issue 66)...")
    _print_eta("Nó contravent. (escoras+lig.)", _nc)
    for _k, _rot in (("beiral", "beiral"), ("central", "central")):
        _e, _l = _nc[f"escora_{_k}"], _nc[f"ligacao_escora_{_k}"]
        print(f"  · Escora {_rot}: N={_nc[f'N_escora_{_k}_kN']:.1f} kN | "
              f"flexo-axial η={_e['eta']:.3f} | ligação {_l['n_pinos']}×Ø{_l['d_mm']:.0f} "
              f"({_l['n_horiz']}×{_l['n_vert']}, R_d={_l['R_d_kN']:.0f} kN) η={_l['eta']:.3f}")

    # Ligação terça–viga (issue 43): arrancamento de sucção, contenção §9.2.5.2,
    # diafragma e, nas baías rígidas, a força de montante da treliça.
    from mlc_projeto.connections.terca_viga import verificar_ligacao_terca_viga
    _cvh = res_elu["contraventamento"]
    _w_suc = min(min(p["w_esq_kNm2"], p["w_dir_kNm2"]) for p in load.padroes_vento)
    _n_tercas_linha = 2 * round(geo.L / S) + 1           # linhas de terças (T1–T17)
    res_elu["ligacao_terca_viga"] = verificar_ligacao_terca_viga(
        mat=mat_curta, w_suc_k_kNm2=_w_suc, g_k_terca_kNm2=float(pp["g_k_terca_kNm2"]),
        s_terca_m=S, L_T_m=L_T, b_terca_m=B_TERCA, h_terca_m=H_TERCA, b_viga_m=geo.b,
        F_contencao_kN=float(_cvh["F_d_apoio_kN"]),
        H_diafragma_kN=float(cvt["R_gable_kN"]) / _n_tercas_linha,
        # montante interior mais solicitado: cortante do 2.º painel da treliça
        N_montante_kN=float(_cvh["R_ext_proj_kN"]) * (1.0 - 1.0 / int(_cvh["n_paineis_vao"])),
        N_corda_kN=float(cvt["N_corda_kN"]),
    )
    _tv = res_elu["ligacao_terca_viga"]
    print("\n[FASE 2] Ligação terça–viga (issue 43)...")
    _print_eta("Ligação terça–viga", _tv)
    _tc = _tv["corrente"]
    print(f"  · corrente: V_up={_tv['V_up_kN']:.1f} kN, H_viga={_tv['H_viga_kN']:.1f} kN, "
          f"H_terça={_tv['H_terca_kN']:.1f} kN → {_tc['n_parafusos']} parafusos "
          f"Ø{_tc['d_mm']:.0f} a 45° ({_tc['n_por_face']} por face) | "
          f"R_ax,d={_tc['R_ax_d_kN']:.2f} R_v,d={_tc['R_v_d_kN']:.2f} kN | "
          f"η_ax={_tc['eta_axial']:.3f} η_v={_tc['eta_lateral']:.3f} → η={_tc['eta']:.3f}")
    _tm = _tv["montante"]
    print(f"  · montante (baías rígidas): N={_tv['N_montante_kN']:.1f} kN → "
          f"{_tm['n_pinos']}×Ø{_tm['d_mm']:.0f} ({_tm['n_vert']}×{_tm['n_horiz']}) "
          f"R_d={_tm['R_d_kN']:.0f} kN η={_tm['eta']:.3f}")
    _te = _tv["emenda_corda"]
    print(f"  · emenda da corda ({_cb['n_emendas']} por linha de beiral): "
          f"N={_te['F_Ed_kN']:.1f} kN → {_te['n_pinos']}×Ø{_te['d_mm']:.0f} de cada lado "
          f"({_te['n_vert']}×{_te['n_horiz']}), chapa {_te['chapa']['L_chapa_mm']:.0f}×"
          f"{_te['chapa']['h_chapa_mm']:.0f} em rasgo superior de "
          f"{_te['chapa']['profundidade_rasgo_mm']:.0f} mm "
          f"(máx. {_tv['rasgo_superior']['profundidade_max_mm']:.0f}) η={_te['eta']:.3f}")

    # Estabilidade global — P-Δ, forças nocionais, α_cr (dispensa 2.ª ordem)
    print("\n[FASE 2] Estabilidade global (P-Δ / nocionais / α_cr)...")
    res_elu["estabilidade_global"] = verificar_estabilidade_global(
        geo=geo, mat=mat_elu, load=load,
        H_pilar_m=H_PILAR_ALT,
        b_pilar=B_PILAR, h_pilar=H_PILAR,
        m_colunas=2,
        contravento_vertical_ok=(cvv["lateral_estavel_long"]
                                 and cvc["lateral_estavel_long"]),
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
        K_lat_long_kNpm=cvv.get("K_lat_kNpm", 0.0) + cvc.get("K_lat_kNpm", 0.0),
        # issue 110: rigidez do conjunto diafragma + frontões (modelo em planta)
        K_lat_transv_kNpm=res_elu["diafragma_cobertura"]["K_eq_kNpm"],
        V_Ed_total_kN=V_ED_TOTAL_KN,
        amplificacao_aplicada=bool(
            cvv.get("amplificacao_aplicada") or cvc.get("amplificacao_aplicada")
            or cvt.get("amplificacao_aplicada")
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
        # o choque (0,50 m acima do piso) atinge a madeira 0,20 m acima do pé,
        # que está no topo do pilarete (issue 87)
        H_pilar_m=H_PILAR_MAD, h_imp_m=H_IMP_PISO_M - H_PILARETE_M,
    )
    iv = res_elu["impacto_veiculo"]
    _print_eta("Impacto veículo (A_d)", iv)
    print(f"  · F_dx={iv['forcas']['F_dx_kN']:.0f} kN / "
          f"F_dy={iv['forcas']['F_dy_kN']:.0f} kN @ "
          f"h={iv['forcas']['h_imp_m']:.2f} m | "
          f"k_mod={iv['k_mod']:.2f} (instantânea)")
    print(f"  · Gov: {iv['gov']} | η={iv['eta']:.4f}")
    print(f"  · {iv['recomendacao'][:90]}…")

    # ── Pilares montantes das baías rígidas: pilar BIPARTIDO (issue 104) ──────
    # Duas lâminas de MLC dos dois lados da viga, da base até a escora; o nó da
    # diagonal CV-V fica no topo da lâmina, no nível da escora (sem binário H·h0),
    # e a componente vertical desce // às fibras até o pilarete da lâmina.
    print("\n[FASE 2] Pilares montantes bipartidos (issue 104)...")
    from mlc_projeto.checks.elu.pilar_bipartido import verificar_pilar_bipartido
    _combs = load.combinacoes_ELU_fisicas().values()
    _Rv_comp = max(abs(float(c.V_max_kN)) for c in _combs)
    _R_up = float(reacao_arrancamento_max(load)["R_up_kN"])
    _M_v0 = float(res_elu.get("pilar_vento_0", {}).get("M_d_kNm", 0.0))
    _V_choque = max(float(c["R_base_kN"]) for c in iv["casos"])
    # arrancamento das duas terças que se apoiam na capa do nó (sucção da cobertura)
    _F_up_no = 2.0 * float(res_elu["ligacao_terca_viga"]["V_up_kN"])
    _kw_bp = dict(mat=mat_elu, b_viga_m=geo.b, L_x_m=H_PILAR_MAD, L_y_m=H_PILAR_MAD + geo.h0 + FOLGA_ESCORA_VIGA_MM / 1000,
                  M_vento_kNm=_M_v0, V_choque_kN=_V_choque, F_up_no_kN=_F_up_no)
    # Choque de veículo na lâmina (issue 106): a mais carregada na acidental é a do
    # central montante, com metade das reações de G de duas vigas.
    from mlc_projeto.checks.elu.pilar_bipartido import verificar_lamina_impacto
    from mlc_projeto.checks.elu.impacto_veiculo import N_acidental_pilar, F_DX_KN, F_DY_KN
    _kw_li = dict(
        mat_inst=mat_elu.com_duracao("instantanea"), b_viga_m=geo.b, L_x_m=H_PILAR_MAD,
        L_y_m=H_PILAR_MAD + geo.h0 + FOLGA_ESCORA_VIGA_MM / 1000, N_d_kN=N_acidental_pilar(load, fator_pilar=2.0) / 2.0,
        F_x_kN=F_DX_KN, F_y_kN=F_DY_KN, h_imp_m=iv["forcas"]["h_imp_m"])
    _lam_imp = verificar_lamina_impacto(**_kw_li)
    _lam_imp["eta_lamina_sozinha"] = verificar_lamina_impacto(repartido=False, **_kw_li)["eta"]
    iv["lamina_bipartido"] = _lam_imp
    if _lam_imp["eta"] > iv["eta"]:
        iv["eta"], iv["gov"] = _lam_imp["eta"], f"lâmina bipartida, {_lam_imp['gov']['direcao']}"
    iv["ok"] = iv["ok"] and _lam_imp["ok"]
    _gl = _lam_imp["gov"]
    print(f"  · choque na lâmina bipartida (repartido pelo espaçador do pé): F={_gl['F_kN']:.0f} kN, "
          f"{_gl['direcao']} | "
          f"M={_gl['M_kNm']:.2f} kN·m V={_gl['V_kN']:.1f} kN | N={_lam_imp['N_d_kN']:.1f} kN "
          f"k_c={_lam_imp['k_c']:.3f} | η_flexo={_gl['eta_flexo']:.3f} η_V={_gl['eta_v']:.3f} "
          f"η_espaçador={max(c['eta_espacador'] for c in _lam_imp['casos']):.3f} "
          f"(lâmina sozinha: η={_lam_imp['eta_lamina_sozinha']:.2f})")
    res_elu["pilar_contraventado"] = verificar_pilar_bipartido(
        rotulo="canto (P1, P3, P25, P27)", R_grav_kN=_Rv_comp, R_up_kN=_R_up,
        D_kN=float(cvv["N_uplift_kN"]), extra_centrado_kN=float(cvt["N_uplift_kN"]), **_kw_bp)
    res_elu["pilar_lateral_montante"] = verificar_pilar_bipartido(
        rotulo="lateral montante (P4, P6, P22, P24)", R_grav_kN=_Rv_comp, R_up_kN=_R_up,
        D_kN=float(cvv["N_uplift_kN"]), **_kw_bp)
    res_elu["pilar_central_contraventado"] = verificar_pilar_bipartido(
        rotulo="central montante (P2, P5, P8, P20, P23, P26)", R_grav_kN=2.0 * _Rv_comp,
        R_up_kN=2.0 * _R_up, D_kN=float(cvc["N_uplift_kN"]), **_kw_bp)
    for _kb, _rb in (("pilar_contraventado", "Pilar canto bipartido"),
                     ("pilar_lateral_montante", "Pilar lateral montante bip."),
                     ("pilar_central_contraventado", "Pilar central montante bip.")):
        _b = res_elu[_kb]
        _print_eta(_rb, _b)
        print(f"  · 2 lâminas {_b['b_lamina_m']:.2f}×{_b['h_lamina_m']:.2f} m | N lâmina="
              f"{_b['N_lamina_kN']:.0f} kN (R/2 + D {_b['D_kN']:.0f}) | λ_x={_b['lambda_x']:.0f} "
              f"λ_ef,y={_b['lambda_ef_y']:.0f} k_c={_b['k_c']:.3f} | η={_b['eta_comp']:.3f}")
        print(f"  · espaçadores: T_d={_b['espacadores']['T_d_kN']:.1f} kN → "
              f"{_b['espacadores']['n_parafusos']}×M16 η={_b['espacadores']['eta']:.3f} | nó "
              f"{_b['no']['n_pinos']}×Ø20 η={_b['no']['eta']:.3f} | sela {_b['sela']['n_pinos']}×Ø20 "
              f"η={_b['sela']['eta']:.3f} (pé e pilarete: base L3a)")

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

    # Calha central sobre a T9 (issue 83): hidráulica e água da calha cheia na terça
    from mlc_projeto.checks.calha import dimensionar_calha
    res_elu["calha"] = dimensionar_calha(L_vao_m=geo.L, alpha_deg=GEO_PARAMS["alpha_deg"],
                                         L_T_m=L_T, s_terca_m=S)
    _ca = res_elu["calha"]
    _print_eta("Calha central e condutores", _ca)
    print(f"  · calha {_ca['B_mm']:.0f}×{_ca['H_mm']:.0f} mm, i = 0,5 %: {_ca['Q_trecho_L_min']:.0f} "
          f"de {_ca['Q_calha_L_min']:.0f} L/min | saída por pórtico ({_ca['A_por_saida_m2']:.0f} m², "
          f"I = {_ca['I_mm_h']:.0f} mm/h) {_ca['Q_saida_L_min']:.0f} L/min → condutor "
          f"Ø{_ca['d_condutor_mm']:.0f} (f ≤ 0,33: {_ca['Q_condutor_L_s']:.1f} L/s, η = {_ca['eta_condutor']:.2f})")
    print(f"  · borda da calha {_ca['borda_sobre_T9_mm']:.0f} mm acima da T9 → último pano a "
          f"{100 * _ca['inclinacao_ultimo_pano']:.1f} % (mín. 5 %)")
    res_elu["terca_calha"] = verifica_terca_flexocompressao(
        mat=mat_elu, L_t=L_T, s=S, b=B_TERCA, h=H_TERCA,
        alpha_deg=GEO_PARAMS["alpha_deg"],
        g_k_m2=g_area_terca + _ca["g_calha_kN_m"] / S,
        q_k_m2=Q_AREA + _ca["q_agua_kN_m"] / S,
        w_kNm2=_w_C1bv_m2, N_c_kN=_F_terca,
    )
    _print_eta("Terça T9 sob a calha cheia", res_elu["terca_calha"])

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

    # Beiral e oitão — balanços da viga e da terça (issue 82)
    print("\n[FASE 2] Beiral e oitão — balanços (issue 82)...")
    from mlc_projeto.checks.elu.beiral import verificar_balanco_terca, verificar_balanco_viga
    # rasgo da L1 na raiz (issue 83): em toda a altura até a geometria do rasgo
    # ser fixada (FASE 4, geometria_rasgo); recalculado lá com o fundo real
    res_elu["balanco_viga"] = verificar_balanco_viga(geo, load, mat_curta,
                                                     t_rasgo_m=T_RASGO_M)
    _bv = res_elu["balanco_viga"]
    _print_eta("Balanço da viga (beiral)", _bv)
    print(f"  · a={_bv['a_m']:.3f} m do eixo do apoio | h {geo.h0:.2f} → {_bv['h_ponta_m']:.3f} m | "
          f"M_raiz={_bv['M_raiz_kNm']:.2f} kN·m ({_bv['comb']}) | k_m,α={_bv['k_m_alpha']:.3f} | "
          f"η_ELU={_bv['eta_ELU']:.3f}")
    print(f"  · ponta: w_inst={_bv['w_inst_mm']:.2f} ≤ {_bv['lim_inst_mm']:.1f} mm | "
          f"w_fin={_bv['w_fin_mm']:.2f} ≤ {_bv['lim_fin_mm']:.1f} mm (para baixo +; Tab. 7.2) | "
          f"η_ELS={_bv['eta_ELS']:.3f}")
    res_elu["balanco_terca"] = verificar_balanco_terca(
        mat_curta, a_m=A_BAL_TERCA_M, L_t=L_T, s=S, b=B_TERCA, h=H_TERCA,
        alpha_deg=GEO_PARAMS["alpha_deg"], g_k_m2=g_area_terca, q_k_m2=Q_AREA,
        w_kNm2=_w_C1bv_m2,
    )
    _bt = res_elu["balanco_terca"]
    _print_eta("Balanço da terça (oitão)", _bt)
    print(f"  · a={_bt['a_m']:.3f} m | M_y={_bt['M_y_kNm']:.2f} kN·m ({_bt['comb']}) | "
          f"w_inst={_bt['w_inst_mm']:.2f}/{_bt['lim_inst_mm']:.1f} mm | "
          f"w_fin={_bt['w_fin_mm']:.2f}/{_bt['lim_fin_mm']:.1f} mm")
    # Sobrecarga só no vão (EN 1990 §6.4.3.2(2): parte variável desfavorável
    # aplicada onde desfavorece): o balanço descarregado de Q deixa de aliviar o vão.
    _gq = load.combinacao_ELU_governante()
    if _gq.duracao == "media" and geo.a_bal > 0:
        _dM = 1.5 * load.q_k * geo.a_bal ** 2 / 2.0
        res_elu["balanco_viga"]["dM_Q_so_vao_kNm"] = round(_dM, 3)
        print(f"  · Q só no vão: +{_dM:.2f} kN·m no vão "
              f"({_dM / abs(_gq.M_max_kNm):.1%} de M_max) — absorvido pela margem; ver flexão")

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

    # Resistência ao fogo — EN 1995-1-2, método da seção reduzida (achado A5)
    #
    # O fogo estava ausente E não declarado. O Eurocódigo dá o método; o tempo
    # requerido R vem do regulamento nacional (NBR 14432 / IT do CBM) e está
    # declarado em NDP_SOURCE["R_fogo_req_min"] como PROJETO-A-CONFIRMAR — o
    # guard `parametros_a_confirmar()` mantém-no visível até o projetista o
    # fixar. Combinação acidental EN 1990 Eq. (6.11b): com ψ1,Q = ψ2,W = 0
    # (categoria H) reduz-se ao permanente sem coeficiente parcial.
    print("\n[FASE 2] Resistência ao fogo (EN 1995-1-2, seção reduzida) — INFORMATIVA...")
    print("  · TRRF exigido = 0: térrea, garagem aberta lateralmente (NPT 008 CBPMPR "
          "A2.3.10 b / A2.4 c); R30 verificado como margem. Item 5.17: retardante ao fogo.")
    _N_fi_lateral = reacao_vertical_incendio(geo, load)
    res_elu["fogo"] = verificar_fogo(
        geo, mat_elu, load, R_req_min=R_FOGO_REQ_MIN, s=S,
        pilares=(
            dict(b=B_PILAR, h=H_PILAR, H_col_m=H_PILAR_MAD,
                 N_fi_kN=_N_fi_lateral, nome="pilar_lateral"),
            dict(b=B_PILAR_C, h=H_PILAR_C, H_col_m=H_PILAR_MAD,
                 N_fi_kN=2.0 * _N_fi_lateral, nome="pilar_central"),
        ),
    )
    _fg = res_elu["fogo"]
    _fgv = _fg["viga"]
    _print_eta(f"Fogo R{int(R_FOGO_REQ_MIN)} EN 1995-1-2", _fg)
    print(f"  · d_ef={_fgv['d_ef_mm']:.1f} mm ({_fgv['faces_expostas']} faces) | "
          f"b: {_fgv['b_inicial_mm']:.0f}→{_fgv['b_fi_mm']:.0f} mm "
          f"(−{_fgv['perda_b_pct']:.1f}%) | q_fi={_fgv['q_fi_kNm']:.3f} kN/m")
    print(f"  · viga: η_M={_fgv['eta_flexao']:.4f} | "
          f"η_LTB={_fgv['eta_ltb']:.4f} (k_crit={_fgv['k_crit']:.4f}) | "
          f"η_V={_fgv['eta_cisalhamento']:.4f} → governa {_fgv['modo_gov']}")
    for _p_fi in _fg["pilares"]:
        print(f"  · {_p_fi['nome']}: {_p_fi['b_mm']:.0f}×{_p_fi['h_mm']:.0f} → "
              f"{_p_fi['b_fi_mm']:.0f}×{_p_fi['h_fi_mm']:.0f} mm "
              f"(−{_p_fi['perda_A_pct']:.1f}% de área) | N_fi={_p_fi['N_fi_kN']:.1f} kN | "
              f"k_c={_p_fi['k_c']:.4f} | η={_p_fi['eta']:.4f}")
    # Lâmina do pilar bipartido (issue 106): 160 mm, quatro faces expostas; a mais
    # carregada é a do central montante, com metade das reações de duas vigas.
    from mlc_projeto.checks.elu.pilar_bipartido import verificar_lamina_fogo
    _kw_lam_fi = dict(mat=mat_elu, b_viga_m=geo.b, L_x_m=H_PILAR_MAD, L_y_m=H_PILAR_MAD + geo.h0 + FOLGA_ESCORA_VIGA_MM / 1000,
                      N_fi_kN=_N_fi_lateral)
    _lam_fi = verificar_lamina_fogo(R_req_min=R_FOGO_REQ_MIN, **_kw_lam_fi)
    _lam_fi["nome"] = "lamina_bipartido"
    _fg["lamina_bipartido"] = _lam_fi
    _fg["eta_por_elemento"]["lamina_bipartido"] = _lam_fi["eta"]
    if _lam_fi["eta"] > _fg["eta"]:
        _fg["eta"], _fg["elemento_gov"] = _lam_fi["eta"], "lamina_bipartido"
    _fg["ok"] = _fg["ok"] and _lam_fi["ok"]
    print(f"  · lâmina bipartida: {B_LAMINA*1e3:.0f}×{H_LAMINA*1e3:.0f} → {_lam_fi['b_fi_mm']:.0f}×"
          f"{_lam_fi['h_fi_mm']:.0f} mm (4 faces) | N_fi={_lam_fi['N_fi_kN']:.1f} kN | "
          f"λ_ef={_lam_fi['lambda_ef_y']:.0f} k_c={_lam_fi['k_c']:.3f} | η={_lam_fi['eta']:.4f}")
    print(f"  · margem por patamar: "
          + " | ".join(f"{k}: η={v}" for k, v in _fg['margem_por_R'].items()))
    print(f"  ⚠ {_fg['nota_R']}")

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

    # AUD-006 (resíduo B) e issue 113: o empuxo nos pórticos de frontão e nos internos
    # sai agora do modelo em planta (rigidez ao afastamento dada pelo sistema), depois
    # das ligações — ver "Empuxo no sistema espacial".

    # ── Fase 4a: Tirante de base (opcional — fecho do empuxo) ─────────────────
    H_arco = float(load.H_ELU())
    n_linhas_port = int(round(L_COMP_GALPAO / L_T)) + 1  # eixos Y (pórticos)

    # Auditoria do empuxo acoplado (issue 38): quanto de H realmente se desenvolve
    # dada a rigidez horizontal real do apoio (pilar biarticulado = mecanismo).
    print("\n[FASE 4a] Auditoria do empuxo acoplado (issue 38 — coerência do modelo)...")
    # Resíduo do [F-06]: a auditoria do empuxo acoplado consome H_rigido, logo
    # é H_rigido que se maximiza — não |M_max|, que era uma procuração.
    _gov_grav, _ = load.envelope_ELU(lambda c: abs(float(c.H_rigido_kN)))
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

    # Issue 42 — gravidade por contato; os pinos só recebem o arrancamento
    _arr = reacao_arrancamento_max(load)
    print(f"  · Apoio por contato (issue 42): pinos dimensionados para o "
          f"arrancamento R_up={_arr['R_up_kN']:.1f} kN ({_arr['comb']})")
    res_lig = dimensionar_ligacoes(
        V_pinos_kN=_arr["R_up_kN"],
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
    # Empuxo no sistema espacial (issue 113): rigidez ao afastamento dos apoios dada
    # pelo diafragma (com as CV-D) e pelos painéis, no modelo em planta.
    from mlc_projeto.checks.elu.empuxo_sistema import empuxo_no_sistema
    res_elu["empuxo_sistema"] = empuxo_no_sistema(
        base_modelo=_BASE_DIAF, n_eixos=_N_EIXOS_DF, n_faixas=_BASE_DIAF["n_faixas"],
        H_rigido_kN=abs(float(load.H_rigido_ELU())),
        k_arco_kNm=float(res_elu["empuxo_acoplado"]["k_arco_kNm"]),
        L_m=geo.L, alpha_rad=geo.alpha_rad,
        R_d_L1_kN=float(res_lig["L1"]["R_total_kN"]))
    _es = res_elu["empuxo_sistema"]
    print("\n[FASE 4a] Empuxo no sistema espacial (issue 113)...")
    _print_eta("Empuxo no sistema (L1 horiz.)", _es)
    print(f"  · k_ap (diafragma + painéis) = {_es['k_ap_min_kNpm']:,.0f} a {_es['k_ap_max_kNpm']:,.0f} kN/m "
          f"vs k_arco = {_es['k_arco_kNm']:,.0f} kN/m")
    print(f"  · H_dev máx = {_es['H_dev_max_kN']:.2f} kN ({100*_es['fracao_max']:.1f}% do rígido "
          f"{_es['H_rigido_kN']:.0f} kN), pórtico {_es['portico_gov']} | ΔM cumeeira {_es['dM_cumeeira_kNm']:+.1f} kN·m "
          f"(favorável) | ΔN viga +{_es['dN_viga_kN']:.1f} kN")
    print("  · por pórtico: " + ", ".join(f"{x['portico']}: {x['H_dev_kN']:.1f}" for x in _es["porticos"]))
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
        V_pinos_kN=_arr["R_up_kN"],
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

    # ── Curso dos furos ovalizados da L1/L1c (issue 72) ───────────────────────
    print("\n[FASE 4] Furos ovalizados da L1/L1c — curso e posição do pino (issue 72)...")
    from mlc_projeto.connections.chapas_aco import d0_furo
    from mlc_projeto.connections.oblongo_L1 import geometria_rasgo
    from mlc_projeto.core.loads import analisar_biarticulada as _ab
    _L1 = res_lig["L1"]

    def _R_apoio(qe, qd):
        r = _ab(q=0.5 * (qe + qd), L=geo.L, h0=geo.h0, h_ap=geo.h_ap,
                alpha_rad=geo.alpha_rad, b=geo.b, q_esq=qe, q_dir=qd,
                desenvolve_empuxo=load.empuxo_desenvolve, a_bal=geo.a_bal)
        return max(float(r["R_A_kN"]), float(r["R_B_kN"]))
    _R_G = _R_apoio(load.g_k, load.g_k)
    _R_var = max([_R_apoio(load.q_k, load.q_k)]
                 + [_R_apoio(pw["w_esq_kNm2"] * load.area_trib, pw["w_dir_kNm2"] * load.area_trib)
                    for pw in load.padroes_vento])
    # Issue 71: o grupo sobe o mais possível, deixando a folga no fundo do rasgo
    # e 100 mm de madeira inteira acima dele (geometria_rasgo)
    res_elu["oblongo_L1"] = geometria_rasgo(
        h0_mm=geo.h0 * 1000, d_mm=float(_L1["d_mm"]), d0_mm=d0_furo(float(_L1["d_mm"])),
        a2_mm=float(_L1["a2_mm"]), n_fileiras=int(_L1["n_linhas"]),
        R_G_kN=_R_G, R_var_kN=max(_R_var, 0.0), b_m=geo.b,
        l_apoio_m=min(H_PILAR, L_SELA_POR_VIGA), k_def=mat_longa.k_def,
    )
    _ob = res_elu["oblongo_L1"]
    for _rl in (res_lig["L1"], res_lig_c["L1c"]):
        _rl["a4c_topo_mm"] = _ob["a4c_topo_mm"]          # lido pelo fendilhamento
    _print_eta("Furos ovalizados L1/L1c (curso)", _ob)
    print(f"  · pino mais alto a {_ob['y_pino_alto_mm']:.0f} mm do apoio | montagem "
          f"{_ob['u_montagem'][0]:.0f}–{_ob['u_montagem'][1]:.0f} %, serviço "
          f"{_ob['u_servico'][0]:.0f}–{_ob['u_servico'][1]:.0f} %")
    print(f"  · para baixo: retração {_ob['retracao_mm']:.1f} + fluência {_ob['fluencia_mm']:.1f} "
          f"+ elástica {_ob['elastica_var_mm']:.1f} + tol. → {_ob['c_baixo_mm']:.0f} mm | "
          f"para cima: inchamento {_ob['inchamento_mm']:.1f} + tol. → {_ob['c_cima_mm']:.0f} mm")
    print(f"  · rasgo: pino mais alto a {_ob['a4c_topo_mm']:.0f} mm do extradorso | topo da chapa "
          f"{_ob['topo_chapa_mm']:.0f} | folga no fundo {_ob['folga_fundo_mm']:.0f} | fundo do rasgo "
          f"{_ob['fundo_rasgo_mm']:.0f} mm | madeira inteira acima {_ob['madeira_sobre_rasgo_mm']:.0f} mm")
    print(f"  · levantamento sob arrancamento antes de o pino alto pegar ≤ "
          f"{_ob['levantamento_max_mm']:.0f} mm (1.º pino {_ob['levantamento_1o_pino_mm']:.0f} mm)")
    C_CIMA_OBL_MM, C_BAIXO_OBL_MM = _ob["c_cima_mm"], _ob["c_baixo_mm"]
    # Issue 111: engajamento sequencial dos pinos sob arrancamento, na umidade
    # mínima de serviço (folga ∝ altura do pino). Mesmo arranjo na L1 e na L1c.
    from mlc_projeto.connections.oblongo_L1 import verificar_engajamento
    _ys_pinos = [float(_ob["y_topo_mm"]) - k * float(_L1["a2_mm"])
                 for k in range(int(_L1["n_linhas"])) for _ in range(int(_L1["n_linha"]))]
    res_elu["engajamento_L1"] = verificar_engajamento(
        y_pinos_mm=_ys_pinos, F_v_Rd_pino_kN=float(_L1["F_v_Rd_kN"]),
        K_ser_plano_Nmm=float(_L1["K_ser_Nmm"]), P_d_kN=float(_L1["V_d_kN"]),
        d_mm=float(_L1["d_mm"]), d0_mm=d0_furo(float(_L1["d_mm"])), b_mm=geo.b * 1000,
        h_mm=geo.h0 * 1000, k_mod=float(_L1["k_mod"]), gamma_M=float(_L1["gamma_M"]))
    _en = res_elu["engajamento_L1"]
    _print_eta("Engajamento dos pinos L1/L1c", _en)
    print(f"  · {_L1['n_linha']}×{_L1['n_linhas']} (por fileira × fileiras) | espalhamento "
          f"Δg = {_en['delta_g_umidade_mm']:.1f} (umidade) + {_en['tol_fab_mm']:.1f} (fabricação) "
          f"= {_en['delta_g_mm']:.1f} mm ≤ d0 − d = {_en['folga_furo_mm']:.0f} mm | sob P_d: "
          f"{_en['n_escoados']} pino(s) no patamar, F_el,máx/F_Rd = {_en['F_el_max_sobre_F_Rd']:.2f}, "
          f"h_e ativo = {_en['h_e_ativo_mm']:.0f} mm")
    res_elu["balanco_viga"] = verificar_balanco_viga(
        geo, load, mat_curta, t_rasgo_m=T_RASGO_M, h_rasgo_m=_ob["fundo_rasgo_mm"] / 1000.0)
    print(f"  · balanço da viga com o rasgo na raiz (W {res_elu['balanco_viga']['W_raiz_m3']:.4f}"
          f" de {res_elu['balanco_viga']['W_bruto_m3']:.4f} m³) → η = "
          f"{res_elu['balanco_viga']['eta']:.3f}")

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
    for _k in ("L1", "L1c"):     # o rasgo das verificações de apoio cabe a chapa adotada
        if float(esquadro[_k]["t_adotada_mm"]) > T_CHAPA_L1_MM + 1e-9:
            raise ValueError(f"{_k}: chapa {esquadro[_k]['t_adotada_mm']} mm > rasgo previsto "
                             f"para {T_CHAPA_L1_MM} mm (issue 70)")
        esquadro[_k]["t_rasgo_mm"] = T_RASGO_M * 1000.0
    # Geometria das chapas embutidas L1/L1c (issues 52 e 43 — a que vai ao
    # desenho): soldada à chapa de topo/sela, sobe do intradorso até e4 = 1,5·d0
    # acima da EXTREMIDADE do furo ovalizado do pino mais alto (EN 1993-1-8
    # Tab. 3.3, furos ovalizados; d0 = d + folga, issue 79) e cobre o apoio.
    for _k, _l_apoio in (("L1", H_PILAR * 1000), ("L1c", L_SELA_POR_VIGA * 1000)):
        _rl = (res_lig if _k == "L1" else res_lig_c)[_k]
        _d = float(_rl["d_mm"])
        _d0 = d0_furo(_d)
        esquadro[_k]["altura_mm"] = float(_ob["topo_chapa_mm"])
        esquadro[_k]["fundo_rasgo_mm"] = float(_ob["fundo_rasgo_mm"])
        # Issue 111: n_linha pinos por fileira, a a1. Na L1 a viga é contínua sobre o
        # pilar (beiral): grupo centrado no apoio, 1,5·d0 às bordas da chapa. Na L1c a
        # viga termina na sela: primeira coluna a a3,t da extremidade.
        _nc, _a1 = int(_rl["n_linha"]), float(_rl["a1_mm"])
        _Lg = (_nc - 1) * _a1
        if _k == "L1":
            _larg = math.ceil(max(_l_apoio, _Lg + 3.0 * _d0))
            _x0 = (_larg - _Lg) / 2.0
        else:
            _larg = math.ceil(max(_l_apoio, float(_rl["a3t_mm"]) + _Lg + 1.5 * _d0))
            _x0 = float(_rl["a3t_mm"])
        esquadro[_k]["largura_mm"] = _larg
        esquadro[_k]["x_pinos_mm"] = [round(_x0 + j * _a1, 1) for j in range(_nc)]
        # issue 116: rasgo além da chapa (ventilação, issue 83) — nos dois lados na L1;
        # na L1c abre-se na extremidade da viga e passa 30 mm além da chapa
        from mlc_projeto.connections.oblongo_L1 import E_RASGO_VENTILACAO_MM as _ev
        esquadro[_k]["L_rasgo_mm"] = _larg + (2 if _k == "L1" else 1) * _ev
    # As chapas de BASE (L3/L3c) saem do detalhe da FASE 4e (issue 52), que
    # substitui aqui as entradas do esquadro.
    for k in ("L1", "L1c"):
        c = esquadro[k]
        print(f"  · {k} ({c['tipo']}): {c['largura_mm']:.0f}×{c['altura_mm']:.0f} mm | "
              f"t_req={c['t_req_mm']:.1f} → t_adot={c['t_adotada_mm']:.1f} mm "
              f"(governa {c['t_governa']})")
    print("  → L1/L1c: t≥d=24 mm (chapa central rígida p/ rótula do pino) → 25 mm; "
          "corrige os 16 mm arbitrados da issue 21.")

    # ── Ruptura de bloco na L1/L1c — informativa (issue 75) ─────────────────
    # A força nos pinos está a ~84° das fibras: o modo pertinente é o
    # fendilhamento (§8.1.4). O Anexo A trata força // às fibras; aqui só a
    # pequena componente axial N_d o solicitaria. Registra-se, fora do catálogo.
    print("\n[FASE 4] Ruptura de bloco L1/L1c — informativa (componente axial; issue 75)...")
    from mlc_projeto.connections.connections import ruptura_de_bloco_ligacao
    res_bloco_L1 = ruptura_de_bloco_ligacao(res_lig["L1"], geo, mat_elu)
    res_bloco_L1c = ruptura_de_bloco_ligacao(res_lig_c["L1c"], geo, mat_elu)
    res_lig["L1"]["bloco_informativo"] = res_bloco_L1
    res_lig_c["L1c"]["bloco_informativo"] = res_bloco_L1c
    for lbl, rb in [("L1", res_bloco_L1), ("L1c", res_bloco_L1c)]:
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

    # Desenho da L1c (issue 42) — gerado dos parâmetros do dimensionamento
    from mlc_projeto.output.figuras import plot_ligacao_L1c
    _L1c = res_lig_c["L1c"]
    plot_ligacao_L1c(
        Path(__file__).resolve().parent.parent / "output" / "ligacao_L1c.png",
        h_viga_m=geo.h0, b_viga_m=geo.b, h_pilar_m=H_PILAR_C,
        l_apoio_viga_m=L_SELA_POR_VIGA, folga_m=FOLGA_SELA_M,
        t_sela_mm=res_elu["sela_central"]["t_adot_mm"], t_chapa_mm=25.0,
        d_pino_mm=float(D_BASE_MM), n_pinos=int(_L1c["n_pinos"]),
        a2_mm=float(_L1c["a2_mm"]), a4c_mm=float(res_elu["oblongo_L1"]["a4c_topo_mm"]),
        a3_mm=float(_L1c["a3t_mm"]), alpha_deg=geo.alpha_deg,
    )
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
        (res_elu["fendilhamento_L1"],  True),
        (res_elu["fendilhamento_L1c"], True),
        (res_elu["chapa_aco_L1"],      False),
        (res_elu["chapa_aco_L1c"],     False),
    ]
    _nomes = ["L1", "L3", "L1c", "L3c",
              "fendilh. L1", "fendilh. L1c",
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
        # Base central montante do painel da linha central (issue 64)
        N_brace_anc_cen_kN=float(
            res_elu.get("contraventamento_vertical_central", {}).get("N_uplift_kN", 0.0)),
        V_brace_cen_kN=float(
            res_elu.get("contraventamento_vertical_central", {}).get("H_base_kN", 0.0)),
        n_chu_cen_cv=N_CHU_CENTRAL_CV,
        chaveta_cen_cv=CHAVETA_CISALHAMENTO_CANTO,
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
    print(f"  · Central montante (issue 64): N={res_succao['N_uplift_cen_kN']:.1f}+"
          f"{res_succao['N_brace_anc_cen_kN']:.1f}={res_succao['N_uplift_cen_cv_kN']:.1f} kN"
          f" + V={res_succao['V_cen_cv_kN']:.1f} kN → η={res_succao['eta_cen_cv']:.3f}")
    print(f"  · Canto (uplift+contravent., issue 36): "
          f"N={res_succao['N_uplift_ext_kN']:.1f}+{res_succao['N_brace_anc_kN']:.1f}="
          f"{res_succao['N_uplift_canto_kN']:.1f} kN → η_canto={res_succao['eta_canto']:.3f} "
          f"| governa: {res_succao['base_gov']}")

    # ── Bases CORRENTES L3 / L3c — arrancamento + impacto (issue 48) ───────
    # Antes, L3 só via o empuxo de arco (nulo na Opção B) e saía com η=0.
    # Duas situações não concomitantes: persistente (sucção: N_t + vento no
    # pilar) e acidental (choque de veículo: R_base nos chumbadores).
    from mlc_projeto.connections.ancoragem import (
        verificar_base_corrente, verificar_grupo_ancoragem,
    )
    _V_vento_base = 0.5 * max(float(res_elu["pilar_vento_0"]["F_d_kN"]),
                              float(res_elu["pilar_vento_90"]["F_d_kN"]))
    _V_impacto = max(float(c["R_base_kN"])
                     for c in res_elu["impacto_veiculo"]["casos"])
    for _chave, _rot, _Nt, _lig in (
        ("ancoragem_L3", "L3 — base de extremidade",
         res_succao["N_uplift_ext_kN"], res_lig["L3"]),
        ("ancoragem_L3c", "L3c — base central",
         res_succao["N_uplift_cen_kN"], res_lig_c["L3c"]),
    ):
        res_elu[_chave] = verificar_base_corrente(
            rotulo=_rot, N_t_persistente_kN=float(_Nt),
            V_persistente_kN=_V_vento_base, V_acidental_kN=_V_impacto,
            n_chumbadores=int(_lig["n_chumbadores"]), d_mm=D_CHU_MM,
            classe=CLASSE_CHU, layout=(2, 2), dados_concreto=DADOS_ANCORAGEM,
            M_persistente_kNm=_V_vento_base * H_PILARETE_M,
            M_acidental_kNm=_V_impacto * H_PILARETE_M, s_mm=S_GRUPO_CHU_MM,
            chaveta=CHAVETA_CRUZ,                  # issue 74: cortante pela chaveta
        )
        _ab = res_elu[_chave]
        # A ligação passa a reportar o maior entre o concreto sob a chapa (η_N)
        # e a ancoragem; a ancoragem no concreto é modo FRÁGIL (alvo 0,75).
        _lig["eta_ancoragem"] = _ab["eta"]
        _lig["caso_ancoragem_gov"] = _ab["caso_gov"]
        _lig["eta"] = round(max(float(_lig.get("eta_N", 0.0)), _ab["eta"]), 4)
        _lig["ok"] = bool(_lig.get("ok", True)) and _ab["ok"]
        aplicar_criterio_eta(_lig, modo_fragil=_ab["eta"] >= float(_lig.get("eta_N", 0.0)),
                             eta_alvo=ETA_LIG_ALVO)
        print(f"\n[FASE 4c] {_rot}: {int(_lig['n_chumbadores'])}×M{D_CHU_MM} + chaveta cruciforme "
              f"{CHAVETA_L_MM:.0f}×{CHAVETA_H_MM:.0f} (cortante fora dos chumbadores)")
        for _nc, _c in _ab["casos"].items():
            print(f"  · {_nc}: N={_c['N_Ed_kN']:.1f} kN V={_c['V_Ed_kN']:.1f} kN → "
                  f"η_aço={_c['eta_aco']:.3f} η_concreto={_c['eta_concreto']:.3f}"
                  + (f" | chaveta η={_c['chaveta']['eta']:.3f}" if "chaveta" in _c else ""))
        _print_eta(f"{_rot.split(' —')[0]} (chapa + ancoragem)", _lig)

    # ── Pilar de frontão PF (issue 52) — 2º montante da cruz do frontão ─────
    # A cruz do frontão tem largura de baía = espaçamento entre pórticos; no
    # plano do frontão não havia pilar a essa distância do canto.
    from mlc_projeto.checks.elu.pilar_frontao import verificar_pilar_frontao
    _cvt = res_elu["contraventamento_transversal"]
    res_elu["pilar_frontao"] = verificar_pilar_frontao(
        mat=mat_elu, b_m=B_PILAR, h_m=H_PILAR, H_m=H_PILAR_MAD,
        gamma_kNm3=float(pp["gamma_kNm3"]),
        download_kN=float(_cvt["N_uplift_kN"]), H_base_kN=float(_cvt["H_base_kN"]),
        M_vento_kNm=max(float(res_elu.get("pilar_vento_0", {}).get("M_d_kNm", 0.0)),
                        float(res_elu.get("pilar_vento_90", {}).get("M_d_kNm", 0.0))),
        V_vento_base_kN=_V_vento_base,
        V_acidental_kN=_V_impacto, b_viga_m=geo.b, h_pilarete_m=H_PILARETE_M,
        chaveta=CHAVETA_CRUZ,
        n_chumbadores=4, d_chumbador_mm=D_CHU_MM, classe_chumbador=CLASSE_CHU,
        dados_concreto=DADOS_ANCORAGEM,
    )
    _pf = res_elu["pilar_frontao"]
    res_elu["pilar_frontao_montante"] = _pf["montante"]
    res_elu["lig_topo_frontao"] = _pf["topo"]
    res_elu["ancoragem_L3f"] = _pf["base"]
    print(f"\n[FASE 4c] Pilar de frontão PF — {B_PILAR:.2f}×{H_PILAR:.2f} m, "
          f"a {_cvt['b_baia_m']:.2f} m do canto (montante da cruz CV-T)")
    _print_eta("Pilar de frontão (montante)", _pf["montante"])
    print(f"  · D={_pf['download_kN']:.1f} kN + G={_pf['G_k_kN']:.1f} kN | "
          f"N_c={_pf['montante']['N_comp_kN']:.1f} kN | "
          f"N_t={_pf['montante']['N_tracao_liq_kN']:.1f} kN | "
          f"M_vento={_pf['montante']['M_vento_kNm']:.1f} kN·m")
    _tp = _pf["topo"]
    _print_eta("L1f topo PF (furo oblongo)", _tp)
    print(f"  · H={_tp['F_Ed_kN']:.1f} kN // fibras da viga | "
          f"{_tp['n_pinos']}×Ø{_tp['d_mm']:.0f} ({_tp['n_vert']}×{_tp['n_horiz']}) | "
          f"R_d={_tp['R_d_kN']:.1f} kN | η_bloco={_tp['eta_bloco']:.3f}")
    _print_eta("L3f base PF (sucção/impacto)", _pf["base"])
    for _nc, _c in _pf["base"]["casos"].items():
        print(f"  · {_nc}: N={_c['N_Ed_kN']:.1f} kN V={_c['V_Ed_kN']:.1f} kN → "
              f"η_aço={_c['eta_aco']:.3f} η_concreto={_c['eta_concreto']:.3f}")

    # ── Ancoragem do canto — chumbadores moldados com cabeça ───────────────
    res_elu["ancoragem_canto"] = verificar_grupo_ancoragem(
        N_Ed_kN=float(res_succao["N_uplift_canto_kN"]),
        V_Ed_kN=float(res_succao["V_canto_kN"]),
        n_chumbadores=N_CHU_CANTO,
        d_mm=D_CHU_MM, classe=CLASSE_CHU,
        chaveta_cisalhamento=CHAVETA_CISALHAMENTO_CANTO,
        layout=LAYOUT_CHU,
        dados_concreto=DADOS_ANCORAGEM_MONT,
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
    print(f"  · Concreto: h_ef={H_EF_CHU_MONT_MM:.0f} c={C_BORDA_CHU_MONT_MM:.0f} "
          f"s={S_GRUPO_CHU_MM:.0f} mm | N_Rd,cone={_anc['N_Rd_cone_kN']:.0f} kN | "
          f"N_Rd,pull-out={_anc['N_Rd_pullout_kN']:.0f} kN → governa {_anc['modo_concreto_gov']}")
    print(f"  · β_N={_anc['beta_N']:.3f} | β_V={_anc['beta_V']:.3f} | "
          f"η_concreto={_anc['eta_concreto']:.3f} ({_anc['norma_concreto']})")
    # [A4] Os três modos deixaram de ser pendências e passaram a ter resultado.
    _bl, _sp, _bo = _anc["blowout"], _anc["fendilhamento"], _anc["borda_corte"]
    print(f"  · Blow-out §7.2.1.9: "
          + (_bl["criterio_dispensa"] if not _bl["aplicavel"]
             else f"N_Rd={_anc['N_Rd_blowout_kN']:.0f} kN"))
    print(f"  · Fendilhamento §7.2.1.7: "
          + (_sp.get("criterio_dispensa") or _sp.get("motivo")
             or f"ψ_h,sp={_sp.get('psi_h_sp')} → N_Rd="
                f"{_anc['N_Rd_fendilhamento_kN']:.0f} kN"))
    print(f"  · Borda sob corte §7.2.2.5: "
          + (_bo.get("criterio_dispensa") or _bo.get("motivo")
             or f"V_Rd={_anc['V_Rd_borda_kN']:.0f} kN"))
    if _anc["modos_nao_verificaveis"]:
        print(f"  ⚠ NÃO VERIFICÁVEIS: {', '.join(_anc['modos_nao_verificaveis'])}")

    # Esmagamento do concreto sob a chaveta — EN 1992-1-1 §6.7 (era pendente)
    from mlc_projeto.connections.ancoragem import (
        esmagamento_chaveta, requisitos_de_fundacao_para_ancoragem,
    )
    res_elu["chaveta_concreto"] = esmagamento_chaveta(
        V_Ed_kN=float(res_succao["V_canto_kN"]),
        l_chaveta_mm=CHAVETA_L_MONT_MM, h_embutida_mm=CHAVETA_H_MM,
        classe_concreto=CLASSE_CONC_FUND,
    )
    _ch = res_elu["chaveta_concreto"]
    _print_eta("Chaveta — esmagamento §6.7", _ch)
    print(f"  · V_Ed={_ch['V_Ed_kN']:.1f} kN sobre "
          f"{_ch['l_chaveta_mm']:.0f}×{_ch['h_embutida_mm']:.0f} mm | "
          f"f_cd={_ch['f_cd_MPa']:.2f} MPa | F_Rdu={_ch['F_Rdu_kN']:.0f} kN")
    print(f"  ⚠ {_ch['nota_confinamento']}")

    _req_fund = requisitos_de_fundacao_para_ancoragem(
        H_EF_CHU_MONT_MM, C_BORDA_CHU_MONT_MM)
    print("  · REQUISITOS À FUNDAÇÃO (EN 1992-4 §7.2.1.7(2)/§7.2.1.9(1)):")
    print(f"      c1 > {_req_fund['c1_min_dispensa_blowout_mm']:.0f} mm "
          f"(blow-out) — declarado {C_BORDA_CHU_MONT_MM:.0f} mm: "
          f"{'OK' if _req_fund['blowout_dispensado_pela_borda_declarada'] else 'NÃO CUMPRE'}")
    print(f"      h_bloco ≥ "
          f"{_req_fund['h_bloco_min_dispensa_fendilhamento_mm']:.0f} mm "
          f"(fendilhamento) — adotado {H_BLOCO_FUND_MONT_MM:.0f} mm")
    print(f"  ⚠ A fundação deve garantir bloco com c ≥ {C_BORDA_CHU_MONT_MM:.0f} mm "
          f"em torno do grupo (≈ {(S_GRUPO_CHU_MM+2*C_BORDA_CHU_MONT_MM)/1000:.2f}×"
          f"{(2*S_GRUPO_CHU_MM+2*C_BORDA_CHU_MONT_MM)/1000:.2f} m em planta)")

    # ── Ancoragem da base central montante (issue 64) ──────────────────────
    res_elu["ancoragem_central_cv"] = verificar_grupo_ancoragem(
        N_Ed_kN=float(res_succao["N_uplift_cen_cv_kN"]),
        V_Ed_kN=float(res_succao["V_cen_cv_kN"]),
        n_chumbadores=N_CHU_CENTRAL_CV,
        d_mm=D_CHU_MM, classe=CLASSE_CHU,
        chaveta_cisalhamento=CHAVETA_CISALHAMENTO_CANTO,
        layout=LAYOUT_CHU,
        dados_concreto=DADOS_ANCORAGEM_MONT,
    )
    _ancc = res_elu["ancoragem_central_cv"]
    print("\n[FASE 4d] Ancoragem da base central montante (issue 64)...")
    _print_eta("Ancoragem central montante", _ancc)
    print(f"  · {_ancc['n_chumbadores']}×M{_ancc['d_mm']} | N_Ed={_ancc['N_Ed_kN']:.1f} kN "
          f"| V_Ed={_ancc['V_Ed_kN']:.1f} kN (chaveta) | η_aço={_ancc['eta_interacao']:.3f} "
          f"| η_concreto={_ancc['eta_concreto']:.3f} ({_ancc['modo_concreto_gov']})")
    res_elu["chaveta_concreto_central"] = esmagamento_chaveta(
        V_Ed_kN=float(res_succao["V_cen_cv_kN"]),
        l_chaveta_mm=CHAVETA_L_MONT_MM, h_embutida_mm=CHAVETA_H_MM,
        classe_concreto=CLASSE_CONC_FUND,
    )
    _print_eta("Chaveta central — esmagamento §6.7",
               res_elu["chaveta_concreto_central"])

    # ── Detalhe das bases (issue 52): chapa a partir da grelha de chumbadores
    # (a mesma s da EN 1992-4), T-stub sob arrancamento e pé do pilar (chapa
    # embutida + cavilhas). O cortante dos painéis vai do olhal da diagonal à
    # chapa; na madeira só passa o do próprio pilar (vento / choque).
    from mlc_projeto.connections.base_pilar import verificar_base_pilar
    print("\n[FASE 4e] Detalhe das bases — chapa, T-stub e pé do pilar...")
    _N_comp = max(abs(float(c.V_max_kN)) for c in load.combinacoes_ELU_fisicas().values())
    _V_pe = max(_V_vento_base, _V_impacto)
    _Ft_chu = float(res_elu["ancoragem_canto"]["N_Rd_kN"])
    _pf_b = res_elu["pilar_frontao"]
    _BASES = (
        ("base_L3",  "L3 — extremidade", res_succao["N_uplift_ext_kN"], _N_comp,
         B_PILAR, H_PILAR, 2, 2),
        ("base_L3c", "L3c — central", res_succao["N_uplift_cen_kN"], 2.0 * _N_comp,
         B_PILAR_C, H_PILAR_C, 2, 2),
        ("base_L3f", "L3f — pilar de frontão", _pf_b["base"]["N_t_persistente_kN"],
         _pf_b["montante"]["N_comp_kN"], B_PILAR, H_PILAR, 2, 2),
        # montantes bipartidos (issue 104): grelha girada (3 ⊥ ao pórtico × 2), um
        # pilarete sob cada lâmina; pé e pilarete com as forças da lâmina
        ("base_L3a_canto", "L3a — canto e lateral montante", res_succao["N_uplift_canto_kN"],
         2 * res_elu["pilar_contraventado"]["N_comp_kN"], B_LAMINA, H_LAMINA,
         LAYOUT_CHU[1], LAYOUT_CHU[0]),
        ("base_L3a_central", "L3a — central montante", res_succao["N_uplift_cen_cv_kN"],
         2 * res_elu["pilar_central_contraventado"]["N_comp_kN"], B_LAMINA, H_LAMINA,
         LAYOUT_CHU[1], LAYOUT_CHU[0]),
    )
    from mlc_projeto.connections.pilarete import TUBOS_CHS_LAMINA
    from mlc_projeto.connections.tirante_interno import dimensionar_tirante
    # Tirante interno (concepção revista): nos pilares correntes, o arrancamento desce
    # por uma barra roscada no furo central do pilar, da chapa de topo ao pilarete; a
    # madeira fica só à compressão, e o topo e o pé só com o cortante.
    res_elu["tirante_interno"] = {
        _k: dimensionar_tirante(rotulo=_r, N_t_kN=float(_Nt))
        for _k, _r, _Nt, *_ in _BASES if _k in ("base_L3", "base_L3c", "base_L3f")}
    _tg = max(res_elu["tirante_interno"].values(), key=lambda x: x["eta"])
    res_elu["tirante_interno"] = {"variantes": res_elu["tirante_interno"], "eta": _tg["eta"],
                                  "governa": _tg["rotulo"],
                                  "ok": all(x["ok"] for x in res_elu["tirante_interno"].values()),
                                  "norma": _tg["norma"]}
    _yl = _gbp["y_l_mm"]
    _EXTRA_BASE = {
        _kb: dict(N_c_pe_kN=float(res_elu[_kp]["N_lamina_kN"]),
                  N_t_pe_kN=float(res_elu[_kp]["N_t_lamina_kN"]),
                  x_tubos_mm=(-_yl, _yl), tubos=TUBOS_CHS_LAMINA)
        for _kb, _kp in (("base_L3a_canto", "pilar_contraventado"),
                         ("base_L3a_central", "pilar_central_contraventado"))}
    for _kb, _tir in res_elu["tirante_interno"]["variantes"].items():
        _EXTRA_BASE[_kb] = dict(N_t_pe_kN=0.0, N_t_pilarete_kN=_tir["N_t_kN"], tirante=_tir)
    for _k, _rot, _Nt, _Nc, _b, _h, _nx, _ny in _BASES:
        res_elu[_k] = verificar_base_pilar(
            # pilar bipartido: o espaçador do pé (C.3.1: lâminas ligadas nas extremidades)
            # reparte o choque, aplicado 0,20 m acima do pé, entre as duas lâminas
            rotulo=_rot, N_t_kN=float(_Nt), N_c_kN=float(_Nc),
            V_madeira_kN=_V_pe / 2.0 if _k in ("base_L3a_canto", "base_L3a_central") else _V_pe,
            b_pilar_m=_b, h_pilar_m=_h, mat=mat_elu, n_x=_nx, n_y=_ny,
            s_mm=S_GRUPO_CHU_MM, d_chu_mm=D_CHU_MM, F_t_Rd_chu_kN=_Ft_chu,
            aco=ACO_CHAPA_LIG,
            f_cd_MPa=float(res_elu["chaveta_concreto"]["f_cd_MPa"]),
            h_pilarete_m=H_PILARETE_M, **_EXTRA_BASE.get(_k, {}),
        )
        _bp = res_elu[_k]
        _print_eta(f"Base {_rot.split(' —')[0]} ({_rot.split('— ')[1]})", _bp)
        _pe, _ts = _bp["pe_pilar"], _bp["tstub"]
        print(f"  · chapa {_bp['B_mm']:.0f}×{_bp['L_mm']:.0f}×{_bp['t_adotada_mm']:g} mm | "
              f"{_nx}×{_ny} M{D_CHU_MM} @ {S_GRUPO_CHU_MM:.0f} | folga arruela–pilarete "
              f"{_bp['geometria']['folga_arruela_pilar_mm']:.0f} mm")
        print(f"  · T-stub: N_t={_Nt:.1f} kN → {_ts['F_Ed_flange_kN']:.1f}/flange, "
              f"m={_ts['m_mm']:.0f} mm, F_T,Rd={_ts['F_T_Rd_kN']:.1f} kN ({_ts['modo']}) "
              f"η={_ts['eta']:.3f} | compressão §6.2.5: c={_bp['c_eff_mm']:.0f} mm, "
              f"N_c,Rd={_bp['N_c_Rd_kN']:.0f} kN η={_bp['eta_compressao']:.3f}")
        print(f"  · pé do pilar: {_pe['n_pinos']}×Ø{_pe['d_mm']:.0f} ({_pe['n_vert']}×"
              f"{_pe['n_horiz']}) em chapa t={_pe['t_chapa_mm']:.0f} | "
              f"tração // η={_pe['eta']:.3f} | cortante ⊥ {_V_pe:.1f} kN "
              f"η={_bp['eta_cortante_pe']:.3f} | L={_pe['L_ocupado_mm']:.0f} mm")
        # arruela-chapa soldada na montagem (issue 80): cortante por chumbador
        from mlc_projeto.connections.base_pilar import verificar_arruela_chapa
        _bp["arruela_chapa"] = verificar_arruela_chapa(
            V_chu_kN=max(_V_pe, 0.0) / (_nx * _ny), N_chu_kN=float(_Nt) / (_nx * _ny),
            d_chu_mm=float(D_CHU_MM))
        _bp["partes"]["arruela_chapa"] = _bp["arruela_chapa"]["eta"]
        _pl = _bp["pilarete"]
        if _pl:
            _ct = _pl["chapa_topo_mm"]
            print(f"  · pilarete: tubo Ø{_pl['D_mm']:g}×{_pl['t_mm']:g} {_pl['aco']} h={_pl['h_m']:.2f} m "
                  f"| N_c={_pl['N_c_kN']:.0f} N_t={_pl['N_t_kN']:.0f} V={_pl['V_kN']:.1f} kN "
                  f"M={_pl['M_base_kNm']:.1f} kN·m | η tubo={max(_pl['etas'].values()):.3f} | "
                  f"chapa de topo {_ct[0]:.0f}×{_ct[1]:.0f}×{_ct[2]:g} η={_pl['partes']['chapa_topo']:.3f} "
                  f"| solda base a={_pl['a_solda_base_mm']:g} topo a={_pl['a_solda_topo_mm']:g} mm")
    # O esquadro de chapas (memorial, issue 23) passa a refletir o detalhe.
    for _k_esq, _k_b in (("L3", "base_L3"), ("L3c", "base_L3c")):
        _bp = res_elu[_k_b]
        res_elu["esquadro_chapas"][_k_esq].update({
            "largura_mm": _bp["B_mm"], "altura_mm": _bp["L_mm"],
            "t_req_mm": _bp["t_adotada_mm"], "t_adotada_mm": _bp["t_adotada_mm"],
            "t_governa": "T-stub §6.2.4 (η ≤ 0,90)",
            "furacao": (f"4 furos alargados Ø{_bp['geometria'].get('d0_furo_base_mm', 0):.0f} "
                        f"+ arruela-chapa p/ M{D_CHU_MM} @ "
                        f"{S_GRUPO_CHU_MM:.0f} mm, borda {_bp['geometria']['e_mm']:.0f} mm"),
        })

    # ── Ligação da chapa de topo / sela ao pilar e nó deslizante (issue 69) ──
    print("\n[FASE 4e'] Chapa de topo e sela → pilar; nó de topo deslizante (issue 69)...")
    from mlc_projeto.connections.ligacao_topo_pilar import (
        verificar_interface_deslizante, verificar_ligacao_topo,
    )
    # cortante do próprio pilar no topo: vento (metade) ou reação de topo do choque
    _V_topo = max(_V_vento_base,
                  float(res_elu["impacto_veiculo"]["forcas"]["F_dx_kN"]) - _V_impacto)
    _TOPOS = {"base_L3": "L1 — pilar lateral", "base_L3c": "L1c — sela, pilar central",
              "base_L3f": "L1f — pilar de frontão", "base_L3a_canto": "L1 — pilar de canto",
              "base_L3a_central": "L1c — pilar central montante"}
    _lt = {}
    for _k, _rot, _Nt, _Nc, _b, _h, _nx, _ny in _BASES:
        if _k in ("base_L3a_canto", "base_L3a_central"):   # bipartido: sela entre lâminas
            continue
        # tirante interno: o topo só posiciona e leva o cortante (N_t → barra)
        _lt[_k] = verificar_ligacao_topo(rotulo=_TOPOS[_k], N_t_kN=0.0, N_c_kN=float(_Nc),
                                         furo_central_mm=res_elu["tirante_interno"]["variantes"]
                                         [_k]["furo_pilar_mm"],
                                         V_kN=_V_topo, b_pilar_m=_b, h_pilar_m=_h, mat=mat_elu)
    _gov_lt = max(_lt.values(), key=lambda x: x["eta"])
    res_elu["ligacao_topo_pilar"] = {"variantes": _lt, "eta": _gov_lt["eta"],
                                     "governa": _gov_lt["rotulo"],
                                     "ok": all(x["ok"] for x in _lt.values()),
                                     "norma": _gov_lt["norma"]}
    _print_eta("Chapa de topo/sela → pilar", res_elu["ligacao_topo_pilar"])
    for _x in _lt.values():
        _cv = _x["cavilhas"]
        print(f"  · {_x['rotulo']}: N_t={_x['N_t_kN']:.0f} kN → {_cv['n_pinos']}×Ø20 "
              f"({_cv['n_vert']}×{_cv['n_horiz']}, {_cv['L_ocupado_mm']:.0f} mm) η={_cv['eta']:.3f} | "
              f"V={_x['V_kN']:.1f} kN η={_x['partes']['cavilhas_cortante']:.3f} | solda a={_x['a_solda_mm']:g} "
              f"η={_x['partes']['solda']:.3f} | σ_c,0={_x['sigma_c0_MPa']:.2f} MPa")
    # Nó de topo (issue 104): a escora apoia-se no topo das lâminas do pilar
    # bipartido e não se move em relação ao nó (a viga, sim, fica livre sob ela).
    # A chapa da escora liga-se à chapa do nó por parafusos 8.8 em furos normais;
    # a verificação reaproveita a da interface com curso nulo, com a pressão de
    # contato reduzida a 60 % (conservador para furo normal).
    _nc = res_elu["no_contraventamento"]
    _nd = {k: verificar_interface_deslizante(rotulo=f"escora {k}", H_kN=float(_nc[f"N_escora_{k}_kN"]),
                                             cima_mm=0.0, baixo_mm=0.0)
           for k in ("beiral", "central")}
    res_elu["no_escora_parafusos"] = {"interfaces": _nd,
                                      "eta": max(x["eta"] for x in _nd.values()),
                                      "ok": all(x["ok"] for x in _nd.values()),
                                      "norma": _nd["central"]["norma"]}
    _print_eta("Nó de topo: escora × chapa do nó", res_elu["no_escora_parafusos"])
    for _x in _nd.values():
        print(f"  · {_x['rotulo']}: H={_x['H_kN']:.0f} kN → {_x['n_parafusos']}×M{_x['d_mm']:.0f} 8.8 "
              f"corte duplo, furo Ø{_x['largura_furo_mm']:.0f} η={_x['eta']:.3f}")

    # ── Incêndio localizado de veículo — robustez (issue 89) ───────────────
    print("\n[FASE 4f'] Incêndio localizado de veículo (EN 1991-1-2 An. C; issue 89)...")
    from mlc_projeto.checks.elu.incendio_veiculo import avaliar_incendio_veiculo
    _pl_ref = res_elu["base_L3c"]["pilarete"]
    res_elu["incendio_veiculo"] = avaliar_incendio_veiculo(
        mat=mat_elu, h_forro_m=H_PILAR_ALT,
        pilarete=(float(_pl_ref["D_mm"]), float(_pl_ref["t_mm"]), float(_pl_ref["h_m"])),
        pilares=tuple(dict(b=_pf["b_mm"] / 1e3, h=_pf["h_mm"] / 1e3, H_col_m=H_PILAR_MAD,
                           N_fi_kN=_pf["N_fi_kN"], nome=_pf["nome"])
                      for _pf in res_elu["fogo"]["pilares"]))
    _iv = res_elu["incendio_veiculo"]
    from mlc_projeto.checks.elu.pilar_bipartido import tempo_colapso_lamina
    _t_lam = tempo_colapso_lamina(**_kw_lam_fi)
    _iv["lamina_bipartido"] = {"nome": "lamina_bipartido", "N_fi_kN": _kw_lam_fi["N_fi_kN"],
                               "t_colapso_min": {"4 faces": _t_lam},
                               "eta": round(_iv["t_exposicao_min"] / max(_t_lam, 1.0), 4)}
    from mlc_projeto.checks.elu.incendio_veiculo import verificar_pilarete_fogo
    _pl_l = res_elu["base_L3a_central"]["pilarete"]
    _iv["lamina_bipartido"]["pilarete"] = verificar_pilarete_fogo(
        N_fi_kN=_kw_lam_fi["N_fi_kN"], D_mm=float(_pl_l["D_mm"]), t_mm=float(_pl_l["t_mm"]),
        t_exp_min=_iv["t_exposicao_min"], h_m=float(_pl_l["h_m"]))
    _iv["lamina_bipartido"]["eta"] = max(_iv["lamina_bipartido"]["eta"],
                                         _iv["lamina_bipartido"]["pilarete"]["eta"])
    _iv["eta"] = max(_iv["eta"], _iv["lamina_bipartido"]["eta"])
    _iv["ok"] = _iv["eta"] <= 1.0
    _print_eta("Incêndio de veículo (robustez)", _iv)
    print(f"  · carro {_iv['Q_MW']:.1f} MW, D={_iv['D_m']:.2f} m: chama L_f={_iv['L_f_m']:.2f} m < "
          f"{_iv['H_forro_m']:.2f} m até a viga; pluma sob a viga {_iv['theta_pluma_forro_C']:.0f} °C | "
          f"{_iv['n_veiculos']} veículos em sequência → {_iv['t_exposicao_min']:.0f} min")
    for _x in _iv["pilares"]:
        _pt = _x["pilarete"]
        print(f"  · {_x['nome']}: madeira colapsa em {_x['t_colapso_min']['4 faces']:.0f} min (4 faces) | "
              f"pilarete sem proteção {_pt['theta_n_veiculos_C']:.0f} °C → η={_pt['eta_sem_protecao_n']:.2f}; "
              f"intumescente R{_pt['R_intumescente_min']:.0f}, θ_cr {_pt['theta_cr_projeto_C']:.0f} °C "
              f"(calc. {_pt['theta_cr_C']:.0f}) → η={_pt['eta']:.2f}")
    print(f"  · lâmina bipartida: madeira colapsa em {_t_lam:.0f} min (4 faces) | "
          f"η={_t_lam and _iv['t_exposicao_min'] / _t_lam:.2f} | pilarete Ø{_pl_l['D_mm']:.1f}×{_pl_l['t_mm']:.0f} "
          f"sem proteção {_iv['lamina_bipartido']['pilarete']['theta_n_veiculos_C']:.0f} °C → "
          f"η={_iv['lamina_bipartido']['pilarete']['eta_sem_protecao_n']:.2f}; intumescente → "
          f"η={_iv['lamina_bipartido']['pilarete']['eta']:.2f}")

    # ── Soldas de todas as ligações (issue 78) ─────────────────────────────
    print("\n[FASE 4g] Soldas de filete (EN 1993-1-8 §4.5.3.3; issue 78)...")
    from mlc_projeto.connections.soldas import filete
    _sd = []
    _esq = res_elu["esquadro_chapas"]
    _sd.append(filete(peca="L1: chapa embutida × chapa de topo", F_norm_kN=float(res_lig["L1"]["V_d_kN"]),
                      F_par_kN=abs(float(res_lig["L1"]["N_d_kN"])), l_mm=float(_esq["L1"]["largura_mm"]),
                      t_min_mm=T_CHAPA_TOPO_MM))
    _sd.append(filete(peca="L1c: chapa embutida × sela", F_norm_kN=float(res_lig_c["L1c"]["V_d_kN"]),
                      F_par_kN=abs(float(res_lig_c["L1c"]["N_d_kN"])), l_mm=L_SELA_POR_VIGA * 1000,
                      t_min_mm=float(res_elu["sela_central"]["t_adot_mm"])))
    _tpf_ = res_elu["pilar_frontao"]["topo"]
    _sd.append(filete(peca="L1f: chapa × chapa de topo do PF", F_par_kN=float(_tpf_["F_Ed_kN"]),
                      l_mm=H_PILAR * 1000, t_min_mm=T_CHAPA_TOPO_MM))
    for _k, _rot, _Nt, _Nc, _b, _h, _nx, _ny in _BASES:
        _pil = res_elu[_k]["pilarete"]
        _Nt_pe = float(_EXTRA_BASE.get(_k, {}).get("N_t_pe_kN", _Nt))
        _sd.append(filete(peca=f"{_rot}: chapa vertical do pé × chapa de topo do pilarete",
                          F_norm_kN=_Nt_pe, F_par_kN=_V_pe, l_mm=_h * 1000 - 60.0,
                          t_min_mm=min(20.0, float(_pil["chapa_topo_mm"][2]))))
        _sd.append({"peca": f"{_rot}: tubo do pilarete × chapa de base",
                    "a_mm": _pil["a_solda_base_mm"], "eta": _pil["partes"]["solda_base"]})
        _sd.append({"peca": f"{_rot}: tubo do pilarete × chapa de topo",
                    "a_mm": _pil["a_solda_topo_mm"], "eta": _pil["partes"]["solda_topo"]})
        if _k in res_elu["tirante_interno"]["variantes"]:
            _ti = res_elu["tirante_interno"]["variantes"][_k]
            _sd.append({"peca": f"{_rot}: luva do tirante × chapa de topo",
                        "a_mm": _ti["a_solda_luva_mm"], "eta": _ti["eta_solda_luva"]})
        if _k in res_elu["ligacao_topo_pilar"]["variantes"]:
            _vt = res_elu["ligacao_topo_pilar"]["variantes"][_k]
            _sd.append({"peca": f"{_TOPOS[_k]}: chapa vertical do topo × chapa de topo",
                        "a_mm": _vt["a_solda_mm"], "eta": _vt["partes"]["solda"]})
    # pilar bipartido (issue 104): aba da sela × chapa da sela (metade da reação por aba)
    # e chapa do nó × chapa da escora não é soldada (parafusos, no_escora_parafusos)
    for _kp, _rp in (("pilar_contraventado", "canto/lateral"), ("pilar_central_contraventado", "central")):
        _sl = res_elu[_kp]["sela"]
        _sd.append(filete(peca=f"pilar bipartido ({_rp}): aba da sela × chapa da sela",
                          F_par_kN=float(_sl["F_Ed_kN"]), l_mm=H_LAMINA * 1000 - 40.0,
                          t_min_mm=float(_sl["t_chapa_mm"])))
    # chavetas: cortante a meia altura embutida → momento no binário dos cordões
    _V_cruz = max(c["V_Ed_kN"] for c in res_elu["pilar_frontao"]["base"]["casos"].values())
    for _rot, _V, _t, _lc in (("chaveta da base de canto (L3a)", float(res_elu["chaveta_concreto"]["V_Ed_kN"]), 16.0, CHAVETA_L_MONT_MM),
                              ("chaveta da base central montante (L3a)",
                               float(res_elu["chaveta_concreto_central"]["V_Ed_kN"]), 16.0, CHAVETA_L_MONT_MM),
                              ("chaveta em cruz das bases correntes", float(_V_cruz), 12.5, CHAVETA_L_MM)):
        _sd.append(filete(peca=_rot, F_par_kN=_V, M_kNm=_V * CHAVETA_H_MM / 2.0 / 1e3,
                          z_mm=T_CHAVETA_MM, l_mm=_lc, t_min_mm=_t))
    _sd.append({"peca": "sela: enrijecedores × chapa", "a_mm": res_elu["sela_central"]["enrijecedores"]["a_solda_mm"],
                "eta": res_elu["sela_central"]["enrijecedores"]["partes"]["solda"]})
    _sd.append({"peca": "arruela-chapa × chapa de base", "a_mm": res_elu["base_L3"]["arruela_chapa"]["a_solda_mm"],
                "eta": res_elu["base_L3"]["arruela_chapa"]["eta"]})
    for _kd, _rd in (("lig_diag_vertical", "olhal das diagonais CV-V"),
                     ("lig_diag_transversal", "olhal das diagonais CV-T"),
                     ("lig_diag_cobertura", "olhal das diagonais CV-H")):
        _dd = res_elu[_kd]
        _sd.append({"peca": _rd, "a_mm": _dd["a_solda_mm"], "l_mm": _dd["l_solda_mm"],
                    # sob a capacidade da barra (dimensionamento por capacidade, issue 44)
                    "eta": float(_dd.get("etas_capacidade", _dd.get("etas", {})).get("solda", 0.0))})
    _sd_gov = max(_sd, key=lambda x: x["eta"])
    res_elu["soldas"] = {"itens": _sd, "eta": _sd_gov["eta"], "governa": _sd_gov["peca"],
                         "ok": all(x["eta"] <= 1.0 for x in _sd),
                         "norma": "EN 1993-1-8 §4.5.2 e §4.5.3.3 (método simplificado)"}
    _print_eta("Soldas de filete (todas)", res_elu["soldas"])
    for _x in _sd:
        print(f"  · {_x['peca']}: a = {_x['a_mm']:g} mm | η = {_x['eta']:.3f}")

    # ── Retração impedida pelas chapas embutidas (issue 81) ────────────────
    print("\n[FASE 4f] Retração impedida pelas chapas embutidas (issue 81)...")
    from mlc_projeto.connections.retracao import avaliar_retracao
    _grupos = [
        ("escora de beiral", res_elu["no_contraventamento"]["ligacao_escora_beiral"], True),
        ("escora central", res_elu["no_contraventamento"]["ligacao_escora_central"], True),
        ("montante terça–viga", res_elu["ligacao_terca_viga"]["montante"], True),
    ] + [(f"{_k.replace('base_', '')}, pé do pilar", res_elu[_k]["pe_pilar"], False)
         for _k in ("base_L3", "base_L3c", "base_L3f", "base_L3a_canto", "base_L3a_central")
         ] + [(f"{_v['rotulo']} (topo)", _v["cavilhas"], False)
              for _v in res_elu["ligacao_topo_pilar"]["variantes"].values()]
    _ret = [avaliar_retracao(rotulo=_r, n_perp=int(_g["n_vert"]), a2_mm=float(_g["a2_mm"]),
                             d_mm=float(_g["d_mm"]), pode_ovalizar=_ov)
            for _r, _g, _ov in _grupos]
    # ── Deslocamento sob sucção e compatibilidade (issue 112) ──────────────────
    from mlc_projeto.checks.elu.apoio import reacao_arrancamento_caracteristica
    from mlc_projeto.checks.els.deslocamento_succao import verificar_deslocamento_succao
    from mlc_projeto.connections.chapas_aco import d0_furo as _d0f
    from mlc_projeto.connections.tirante_interno import comprimento_tirante
    _Rk = reacao_arrancamento_caracteristica(load)
    _tv, _pl3 = res_elu["tirante_interno"]["variantes"], res_elu["base_L3"]["pilarete"]
    for _k, _v in _tv.items():    # issue 116: comprimentos do tirante, fonte única
        _v.update(comprimento_tirante(
            H_madeira_mm=H_PILAR_MAD * 1000, d_mm=float(_v["d_mm"]),
            t_chapa_pilarete_mm=float(res_elu[_k]["pilarete"]["chapa_topo_mm"][2])))
    _acm = res_elu["ancoragem_central_cv"]
    _d_pe = float(res_elu["base_L3a_central"]["pe_pilar"]["d_mm"])
    from mlc_projeto.output.desenhos import detalhe_topo_pf as _dtpf
    _topo_pf = res_elu["pilar_frontao"]["topo"]
    for _it in range(5):          # curso do L1f: flecha descendente e subida (≤ 0,90)
        _tpf = _dtpf(_topo_pf, float(res_els["ELS"]["w_fin_mm"]), L_T, float(geo.L))
        res_els["deslocamento_succao"] = _ds_kw = verificar_deslocamento_succao(
            R_up_k_kN=float(_Rk["R_up_k_kN"]),
            y_fileiras_mm=[float(_ob["y_topo_mm"]) - k * float(_L1["a2_mm"])
                           for k in range(int(_L1["n_linhas"]))],
            n_por_fileira=int(_L1["n_linha"]), K_ser_plano_Nmm=float(_L1["K_ser_Nmm"]),
            h0_mm=geo.h0 * 1000,
            tirantes={f"corrente ({_k.replace('base_', '')})":
                      {"n_vigas": 2 if _k == "base_L3c" else 1, "A_s_mm2": float(_tv[_k]["A_s_mm2"]),
                       "L_mm": float(_tv[_k]["L_livre_mm"]), "r_chapa_mm": float(_pl3["D_mm"]) / 2,
                       "t_chapa_mm": float(_pl3["chapa_topo_mm"][2])}
                      for _k in ("base_L3", "base_L3c")},
            chumb_corrente={"n": int(res_elu["base_L3"]["geometria"]["n_x"])
                            * int(res_elu["base_L3"]["geometria"]["n_y"]),
                            "A_s_mm2": float(_acm["A_s_mm2"]),   # mesma barra M24 (D_CHU_MM)
                            "L_mm": H_EF_CHU_MM + float(res_elu["base_L3"]["t_adotada_mm"])},
            bipartido={"n_vigas": 2, "A_laminas_mm2": 2 * B_LAMINA * H_LAMINA * 1e6,
                       "L_mm": (H_PILAR_MAD + geo.h0) * 1000 + FOLGA_ESCORA_VIGA_MM, "E_MPa": mat_longa.E0_mean / 1e6,          # Pa → MPa
                       "n_cav": int(res_elu["base_L3a_central"]["pe_pilar"]["n_pinos"]),
                       "K_ser_cav_kNpmm": 4.0 * mat_longa.rho_mean ** 1.5 * _d_pe / 23.0 / 1e3,
                       "folga_furo_mm": _d0f(_d_pe) - _d_pe,
                       "chumb": {"n": int(_acm["n_chumbadores"]), "A_s_mm2": float(_acm["A_s_mm2"]),
                                 "L_mm": H_EF_CHU_MONT_MM + float(res_elu["base_L3a_central"]["t_adotada_mm"])}},
            w_up_meio_mm=float(res_els["ELS"]["w_char_up_mm"]), L_m=geo.L,
            pf={"x_m": L_T, "curso_mm": float(_tpf["curso_mm"]),
                "y_pino_topo_mm": float(_tpf["a4c_mm"]) + (int(_tpf["n_vert"]) - 1) * float(_tpf["a2_mm"])},
            folga_escora_mm=FOLGA_ESCORA_VIGA_MM)
        _req = 5.0 * math.ceil(_ds_kw["pf"]["delta_mm"] / 0.90 / 5.0)
        if _req <= float(_tpf["curso_mm"]) + 1e-9:
            break
        _topo_pf["curso_min_mm"] = _req
    _ds = res_els["deslocamento_succao"]
    print("\n[FASE 4] Deslocamento sob sucção — compatibilidade (issue 112)...")
    _print_eta("Deslocamento sob sucção (compat.)", _ds)
    print(f"  · R_up,k = {_ds['R_up_k_kN']:.1f} kN ({_Rk['padrao']}) | K_ser = {_ds['K_ser_pino_kNpmm']:.1f} kN/mm por pino")
    for _rot, _c in _ds["caminhos"].items():
        _cc = _c[min(_c)]
        print(f"  · {_rot}, u = {min(_c):.0f} %: " + " + ".join(
            f"{_k.replace('_mm', '')} {_v:.1f}" for _k, _v in _cc.items() if _k != "total_mm")
            + f" = {_cc['total_mm']:.1f} mm (u = {max(_c):.0f} %: {_c[max(_c)]['total_mm']:.1f})")
    print(f"  · escora: {_ds['escora']['delta_mm']:.1f} de {_ds['escora']['folga_mm']:.0f} mm | PF: "
          f"{_ds['pf']['delta_mm']:.1f} de {_ds['pf']['curso_mm']:.0f} mm | condutor: subida "
          f"{_ds['condutor']['subida_mm']:.1f} → junta deslizante {_ds['condutor']['junta_deslizante_mm']:.0f} mm")
    # L1f: furos já ovalizados ⊥ às fibras da viga para a flecha (DES-08)
    _ret.insert(3, avaliar_retracao(
        rotulo="L1f, topo do pilar de frontão", n_perp=int(_tpf["n_vert"]),
        a2_mm=float(_tpf["a2_mm"]), d_mm=float(_tpf["d_mm"]), pode_ovalizar=True,
        curso_existente_mm=float(_tpf["curso_mm"])))
    _gov_ret = max(_ret, key=lambda x: x["eta"])
    res_elu["retracao_chapas"] = {
        "grupos": _ret, "eta": _gov_ret["eta"], "ok": all(x["ok"] for x in _ret),
        "governa": _gov_ret["rotulo"],
        "norma": "EC5 §8 (detalhe) + EN 1090-2 (folga do furo); Dietsch e Winter (2018)",
    }
    _print_eta("Retração impedida (chapas)", res_elu["retracao_chapas"])
    for _x in _ret:
        print(f"  · {_x['rotulo']}: {_x['n_perp']} fileiras ⊥ a {_x['a2_mm']:.0f} → D⊥={_x['D_perp_mm']:.0f} mm, "
              f"δ=±{_x['delta_mm']:.2f} mm (folga do furo ±{_x['folga_furo_mm']:.0f}) → {_x['solucao']}")

    # ── Quadro de cargas para a fundação ───────────────────────────────────
    # O projeto NÃO dimensiona fundações (não há sondagem). O entregável é o
    # conjunto de esforços que chega a cada base, para o projeto de fundações.
    from mlc_projeto.output.cargas_fundacao import (
        imprimir_quadro, montar_quadro_cargas_fundacao,
    )
    quadro_fund = montar_quadro_cargas_fundacao(
        load=load, res_succao=res_succao,
        cv_vertical=cvv, cv_transversal=cvt,
        cv_vertical_central=cvc,
        n_paineis_central=N_PAINEIS_CV_CENTRAL,
        V_base_corrente_kN=max(_V_vento_base, _V_impacto),
        n_pilares_linha=n_pil_linha, n_linhas_portico=3,
        n_paineis_long=N_PAINEIS_CV_VERT,
        n_paineis_transv=N_PAINEIS_CV_TRANSV,
        pilar_frontao=res_elu["pilar_frontao"], n_pilares_frontao=N_PILARES_FRONTAO,
    )
    imprimir_quadro(quadro_fund)
    # Esforços característicos por ação (issue 102)
    from mlc_projeto.output.cargas_fundacao import esforcos_caracteristicos
    quadro_fund["caracteristicos"] = esforcos_caracteristicos(
        load=load, geo=geo, gamma_kNm3=float(pp["gamma_kNm3"]),
        pilares={"lateral": (B_PILAR, H_PILAR), "central": (B_PILAR_C, H_PILAR_C),
                 "canto": (B_PILAR_CANTO, H_PILAR_CANTO)},
        H_pilar_mad_m=H_PILAR_MAD, cv_vertical=cvv, cv_vertical_central=cvc,
        cv_transversal=cvt, pilar_frontao=res_elu["pilar_frontao"],
        V_impacto_kN=_V_impacto, V_vento_pilar_d_kN=_V_vento_base,
    )
    print("  Característicos por ação (kN): base | G | Q | W compr. | W arranc. | W horiz. | A_d")
    for _l in quadro_fund["caracteristicos"]:
        print(f"  · {_l['base']}: {_l['G']} | {_l['Q']} | {_l['W_c']} | {_l['W_t']} | "
              f"{_l['W_H']} | {_l['A_H']}")

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
            "combinacao_Q_W": comb_QW,   # issue 45 (informativa)
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
    # Memória de cálculo por equações (issue 50) → apêndice da monografia.
    # Junto do relatório: só em execução real (os testes desligam
    # gerar_relatorio e rodam cenários alterados de propósito).
    if gerar_relatorio is _gerar_relatorio_real:
        from mlc_projeto.output.memorial_equacoes import gerar_apendice_memoria
        _tese = Path(__file__).resolve().parent.parent / "tese"
        if _tese.is_dir():
            gerar_apendice_memoria(todos_para_relatorio, _tese / "apendiceB.tex")
            # Contagens e tabela de NDP da tese, da mesma execução (issue 99).
            from mlc_projeto.output.valores_tese import gerar_valores_tese
            from mlc_projeto.output.custo import Quantidades, gerar_custo
            from mlc_projeto.predim.varredura_global import volume_mlc_m3
            _pp = todos_para_relatorio["meta"]["peso_proprio"]
            _rel = todos_para_relatorio
            _n_cen_mont = next((l["n"] for l in quadro_fund["linhas"]
                                if l["Base"].startswith("Central montante")), 0)
            _n_bip = 2 * N_PAINEIS_CV_VERT + int(_n_cen_mont)
            _n_pil = 3 * n_pil_linha + N_PILARES_FRONTAO
            from mlc_projeto.output.custo import volume_espacadores_m3, volume_tercas_m3
            # issue 117: T1–T17 nos dois vãos e as terças de ponta T0 e T18, com os oitões
            _n_lin_t = 2 * round(geo.L / S) + 1 + 2
            _L_terca = L_COMP_GALPAO + 2 * A_BAL_TERCA_M
            _q = Quantidades(
                V_vigas=volume_mlc_m3(geo.alpha_deg, geo.h0, geo.b),
                V_tercas=volume_tercas_m3(
                    n_linhas=_n_lin_t, L_m=_L_terca, b_m=B_TERCA, h_m=H_TERCA,
                    n_escoras_largas=4, L_escora_m=L_T, b_escora_m=B_ESCORA_CENTRAL),
                n_linhas_tercas=_n_lin_t, L_terca=_L_terca,
                V_espacadores=volume_espacadores_m3(
                    n_bipartidos=_n_bip,
                    L_lamina_mm=(H_PILAR_MAD + geo.h0) * 1000 + FOLGA_ESCORA_VIGA_MM,
                    l1_mm=float(_rel["pilar_central_contraventado"]["espacadores"]["l1_mm"]),
                    a_mm=float(_rel["pilar_central_contraventado"]["geometria"]["a_mm"]),
                    h_l_mm=H_LAMINA * 1000),
                V_pilares=(_n_pil - _n_bip) * B_PILAR * H_PILAR * H_PILAR_MAD
                          + _n_bip * 2 * B_LAMINA * H_LAMINA * (H_PILAR_MAD + geo.h0),
                n_vigas=18, n_pilares=_n_pil, n_bipartidos=_n_bip,
                m_cv_vertical=_rel["contraventamento_vertical"]["peso_total_kg"]
                              + _rel["contraventamento_vertical_central"]["peso_total_kg"],
                m_cv_cobertura=_rel["contraventamento"]["peso_total_kg"],
                m_cv_transversal=_rel["contraventamento_transversal"]["peso_total_kg"],
                m_cv_diafragma=(_rel["diafragma_cobertura"]["n_barras_novas"]
                                * _rel["diafragma_cobertura"]["L_diag_m"] * 7850e-6
                                * 3.14159265 * _rel["diafragma_cobertura"]["d_diafragma_mm"] ** 2 / 4),
                d_cv_diafragma=float(_rel["diafragma_cobertura"]["d_diafragma_mm"]),
                d_cv_vertical=_rel["contraventamento_vertical"]["d_mm"],
                d_cv_cobertura=float(_rel["contraventamento"]["d_barra_mm"]),
                d_cv_transversal=_rel["contraventamento_transversal"]["d_mm"],
                area_planta=load.vento_0["A_planta_m2"])
            _csv = OUTPUT_DIR / "varredura_global_consolidada.csv"
            _V_min = None
            if _csv.exists():
                import pandas as _pd
                _dv = _pd.read_csv(_csv)
                _ok = _dv[_dv.status == "APROVADO"]
                _V_min = float(_ok.volume_mlc_m3.min()) if len(_ok) else None
            _cu = gerar_custo(_tese, _q, _V_min)
            print(f"  · custo: {_q.V_mlc:.1f} m³ MLC + {_q.m_aco:.0f} kg aço → "
                  f"R$ {_cu['total']:,.0f} (R$ {_cu['por_m2']:,.0f}/m²)")
            # issue 121: casos de referência independentes, tabela de pacotes e versão
            from mlc_projeto.output.validacao import gerar_tab_referencias
            from mlc_projeto.output.apendice_programa import gerar_apendice_programa
            _refs = gerar_tab_referencias(_tese, todos_para_relatorio, load)
            _falhas = [r["grandeza"] for r in _refs if not r["ok"]]
            if _falhas:
                raise RuntimeError(f"casos de referência fora da tolerância: {_falhas}")
            print(f"  · validação: {len(_refs)} casos de referência independentes conferidos")
            _mac_prog = gerar_apendice_programa(_tese, _tese.parent, len(_refs))
            _vt = gerar_valores_tese(tese=_tese, n_verif=resumo["n_verif"],
                                     n_exec=resumo["n_executadas"],
                                     n_na=resumo["n_nao_aplicaveis"],
                                     eta_max=resumo["eta_max"], extra=_cu["macros"] + _mac_prog)
            print(f"  · valores da tese: {_vt['n_verif']} verificações "
                  f"({_vt['n_exec']} executadas), {_vt['n_ndp']} NDP, "
                  f"{_vt['n_testes']} testes → tese/valores_pipeline.tex, tese/tab_ndp.tex")
            from mlc_projeto.output.tab_retracao import gerar_tab_retracao   # issue 115
            gerar_tab_retracao(_tese, res_elu["retracao_chapas"]["grupos"])
            # Análise estática por combinação (issue 51) → apêndice C.
            from mlc_projeto.output.apendice_analise import gerar_apendice_analise
            gerar_apendice_analise(load, geo, _tese)
            # Desenhos cotados em escala (issue 52) → tese/fig/des*.pdf
            from mlc_projeto.output.desenhos import arranjo_de_resultados, gerar_desenhos
            gerar_desenhos(arranjo_de_resultados(
                todos_para_relatorio, geo, **arranjo_kwargs(todos_para_relatorio)),
                _tese / "fig")
            # Caminho da força transversal pelo diafragma (issue 110)
            from mlc_projeto.output.figura_diafragma import gerar_figura_diafragma
            gerar_figura_diafragma(res_elu["diafragma_cobertura"],
                                   float(res_elu["contraventamento_transversal"]["H_tr_kN"]),
                                   _tese / "fig" / "diafragma_caminho.pdf")
            # Quadro requerido × adotado dos espaçamentos (issue 43)
            from mlc_projeto.output.quadro_espacamentos import gerar_tex, montar_quadro
            _qe = montar_quadro(
                todos_para_relatorio, h0_m=geo.h0, L_T=L_T, L=geo.L,
                folga_oblongo_mm=C_CIMA_OBL_MM, d_chu_mm=D_CHU_MM,
                h_ef_mm=H_EF_CHU_MM, c_borda_mm=C_BORDA_CHU_MM,
                s_grupo_mm=S_GRUPO_CHU_MM, h_bloco_mm=H_BLOCO_FUND_MM,
                h_pilar_mm={"lateral": H_PILAR * 1000, "central": H_PILAR_C * 1000,
                            "PF": H_PILAR * 1000, "canto": H_PILAR_CANTO * 1000,
                "lamina": H_LAMINA * 1000},
                h_terca_mm=H_TERCA * 1000, a_beiral_mm=A_BEIRAL_M * 1000)
            gerar_tex(_qe, _tese / "tab_espacamentos.tex")
            from mlc_projeto.connections.soldas import gerar_tex as _gerar_tex_soldas
            _gerar_tex_soldas(todos_para_relatorio["soldas"]["itens"], _tese / "tab_soldas.tex")
            from mlc_projeto.output.cargas_fundacao import (
                gerar_tex_calculo, gerar_tex_caracteristicos,
            )
            gerar_tex_calculo(todos_para_relatorio["cargas_fundacao"],
                              _tese / "tab_cargas_fundacao.tex")
            gerar_tex_caracteristicos(todos_para_relatorio["cargas_fundacao"]["caracteristicos"],
                                      _tese / "tab_cargas_fundacao_k.tex")
            _falhas = [f"{r['ligacao']} {r['grandeza']}" for r in _qe if not r["ok"]]
            print(f"  Espaçamentos (issue 43): {len(_qe)} itens, "
                  f"{len(_qe) - len(_falhas)} atendidos"
                  + (f" | NÃO ATENDIDOS: {_falhas}" if _falhas else ""))
            # Figuras esquemáticas (issue 63): variáveis da varredura, modelo
            # do pórtico e modelo do apoio horizontal
            from mlc_projeto.output.esquemas import gerar_esquemas
            gerar_esquemas(geo, _tese / "fig", H_pilar=H_PILAR_ALT, faixas=(
                "varredura: α de 6,0° a 16,0° (passo 0,5°); h₀ de 0,40 a 1,20 m "
                "(passo 0,05 m); b de 0,20 a 0,36 m (passo 0,02 m)"))

    gerar_relatorio(
        todos_para_relatorio,
        geo,
        mat_longa,
        nome="relatorio_mlc",
        load=load,
    )
    print("\nPipeline concluído. Relatório gerado em output/")
    print(f"  Status global = {resumo['status']} | η_max = {fmt_eta(resumo['eta_max'], decimal='.')}")

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