# mlc_projeto

Verificação estrutural de cobertura para estacionamento em madeira lamelada colada (MLC/glulam)  
**Eurocode 5 — EN 1995-1-1** · Vigas de duplo-bisel · Vão 40,5 m

**Engenheiro:** Gabriel Stocki — CREA-PR 195315/D  
**Empresa:** STOCKI Engenharia Estrutural

---

## Instalação

```bash
# 1. Clonar o repositório
git clone https://github.com/SEU_USUARIO/mlc_projeto.git
cd mlc_projeto

# 2. Criar ambiente virtual
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# 3. Instalar dependências
pip install -e ".[dev]"
```

## Uso

```bash
python -m mlc_projeto.main
```

## Estrutura

```
mlc_projeto/
├── core/               # Dados de entrada (geometria, materiais, cargas)
├── predim/             # Pré-dimensionamento
├── checks/
│   ├── elu/            # Verificações ELU
│   └── els/            # Verificações ELS
├── connections/        # Dimensionamento de ligações
├── output/             # Geração de relatório
└── main.py             # Orquestrador
```

## Fases do projeto

| Fase | Módulo(s) | Norma |
|------|-----------|-------|
| 0 — Dados de entrada | core/ | EN 14080, EN 1991 |
| 1 — Pré-dimensionamento | predim/ | EC5 §6 |
| 2 — ELU | checks/elu/ | EC5 §6.1–§6.5, §9 |
| 3 — ELS | checks/els/ | EC5 §7, §2.3 |
| 4 — Ligações | connections/ | EC5 §8 |
| 5–6 — Relatório | output/ | — |
