[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://api-health-monitor-ia.streamlit.app/)
# 📋 Atas em Ação — Organizador de Reuniões com IA e SQL

Aplicação web que transforma anotações não estruturadas de reuniões em um **plano de ação relacional (CRUD)** utilizando **Python**, **APIs REST (LLM)**, **SQLite (SQL)** e **Streamlit**.

## 🎯 Dor Real Resolvida
Equipes técnicas e de negócio frequentemente terminam reuniões com anotações dispersas, sem clareza sobre responsáveis, prioridades e prazos. Este projeto automatiza a extração estruturada de tarefas a partir de texto livre e centraliza o acompanhamento em um banco de dados relacional.

## 🛠️ Arquitetura e Tecnologias
- **Python 3**: Lógica de aplicação e manipulação de dados.
- **API REST (`requests`)**: Integração direta via HTTP `POST` com a API do Google Gemini (`gemini-3.8-flash`), utilizando saída estruturada (`application/json`) para evitar erros de parsing.
- **Banco de Dados Relacional (`SQLite` / SQL)**:
  - Modelagem com duas tabelas relacionadas (`reunioes` 1:N `tarefas` via `FOREIGN KEY`).
  - Operações completas de **CRUD** (`INSERT` transacional, `SELECT` com `INNER JOIN` e filtros dinâmicos, `GROUP BY` para métricas, `UPDATE` e `DELETE`).
- **Streamlit**: Interface web responsiva com exemplos prontos de 1 clique e visualização transparente das queries SQL e payloads JSON executados.

## 🚀 Como Executar Localmente
```bash
git clone [https://github.com/Rafael-Pedra-7325/atas-em-acao-ia.git](https://github.com/Rafael-Pedra-7325/atas-em-acao-ia.git)
cd atas-em-acao-ia
pip install -r requirements.txt
export GEMINI_API_KEY="sua_chave_aqui"
streamlit run app.py
