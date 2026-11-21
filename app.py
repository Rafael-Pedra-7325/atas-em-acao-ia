import os
import pandas as pd
import streamlit as st
from ai_extractor import extrair_tarefas_via_rest
from database import (
    atualizar_status_tarefa,
    excluir_tarefa,
    init_db,
    listar_responsaveis,
    listar_tarefas,
    obter_metricas,
    salvar_reuniao_e_tarefas,
)

st.set_page_config(
    page_title="Atas em Ação | IA + SQL",
    page_icon="📋",
    layout="wide",
)

init_db()

# Inicializa estado para os botões de exemplo rápido
if "titulo_input" not in st.session_state:
    st.session_state.titulo_input = ""
if "notas_input" not in st.session_state:
    st.session_state.notas_input = ""
if "ultimo_json" not in st.session_state:
    st.session_state.ultimo_json = None


def carregar_exemplo_1():
    st.session_state.titulo_input = "Daily Técnica — Integração WhatsApp & IA"
    st.session_state.notas_input = (
        "Na daily de hoje definimos que o Carlos vai corrigir o bug de timeout no endpoint "
        "/mensagens até hoje às 18h, é urgente. A Fernanda vai criar os testes unitários do "
        "parser de intenção até quinta-feira. Também precisamos que o Diego documente o schema "
        "do banco SQL no README até sexta-feira com prioridade baixa."
    )


def carregar_exemplo_2():
    st.session_state.titulo_input = "Comitê de Operações e Finanças"
    st.session_state.notas_input = (
        "Resumo da reunião com Finanças: Ana Paula precisa consolidar os indicadores de inadimplência "
        "do mês até amanhã cedo (urgente). Bruno vai validar a integração com a API de pagamentos "
        "antes do deploy de quarta. Camila ficou encarregada de agendar o treinamento do novo fluxo "
        "com o time de suporte na próxima segunda."
    )


# Barra lateral: configuração da chave REST e arquitetura
with st.sidebar:
    st.header("Configuração da API REST")
    secret_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    env_key = os.getenv("GEMINI_API_KEY", "")
    default_key = secret_key or env_key

    api_key = st.text_input(
        "Gemini API Key",
        value=default_key,
        type="password",
        help="Chave gratuita gerada no Google AI Studio (aistudio.google.com).",
    )
    st.caption(
        "Se o app já estiver configurado com Secret no servidor, basta usar os botões de exemplo ao lado."
    )
    st.divider()
    st.subheader("Arquitetura do Projeto")
    st.markdown(
        """
        - **Linguagem:** Python 3
        - **Integração:** API REST (`requests` + JSON estruturado)
        - **Banco Relacional:** SQLite (`JOIN`, `GROUP BY`, `UPDATE`, `DELETE`)
        - **Interface:** Streamlit
        """
    )

st.title("📋 Atas em Ação — Organizador de Reuniões com IA")
st.markdown(
    "Transforme anotações soltas de reunião em um **plano de ação estruturado em banco SQL** usando **APIs REST e IA Generativa**."
)

# Métricas em tempo real via SQL (GROUP BY)
metricas = obter_metricas()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total de Tarefas", metricas["total"])
c2.metric("Pendentes", metricas["Pendente"])
c3.metric("Em Andamento", metricas["Em Andamento"])
c4.metric("Concluídas", metricas["Concluída"])

st.divider()

col_esquerda, col_direita = st.columns([1, 1.35], gap="large")

# COLUNA 1: Entrada de notas + Extração com IA
with col_esquerda:
    st.subheader("1. Extrair Tarefas com IA")
    st.caption("Teste rápido com 1 clique usando um exemplo pronto:")

    btn1, btn2 = st.columns(2)
    btn1.button("⚡ Exemplo: Daily Tech", on_click=carregar_exemplo_1, use_container_width=True)
    btn2.button("📊 Exemplo: Negócios", on_click=carregar_exemplo_2, use_container_width=True)

    titulo = st.text_input(
        "Título da Reunião",
        key="titulo_input",
        placeholder="Ex: Alinhamento semanal do produto",
    )
    notas = st.text_area(
        "Anotações da Reunião",
        key="notas_input",
        height=170,
        placeholder="Cole aqui o texto livre com responsáveis, ações e prazos...",
    )

    if st.button("🚀 Gerar Plano de Ação e Salvar no SQL", type="primary", use_container_width=True):
        if not titulo.strip() or not notas.strip():
            st.warning("Preencha o título e as anotações da reunião (ou clique em um exemplo acima).")
        else:
            try:
                with st.spinner("Consultando API REST da LLM e gravando no SQLite..."):
                    tarefas_extraidas = extrair_tarefas_via_rest(notas, api_key)
                    salvar_reuniao_e_tarefas(titulo, notas, tarefas_extraidas)
                    st.session_state.ultimo_json = tarefas_extraidas
                st.success(f"{len(tarefas_extraidas)} tarefa(s) extraída(s) e salva(s) no banco SQL!")
                st.rerun()
            except Exception as exc:
                st.error(f"Não foi possível processar: {exc}")

    if st.session_state.ultimo_json:
        with st.expander("🔍 Por baixo dos panos: JSON retornado pela API REST"):
            st.json(st.session_state.ultimo_json)

# COLUNA 2: Quadro CRUD conectado ao SQLite
with col_direita:
    st.subheader("2. Plano de Ação (Banco SQL)")

    f1, f2 = st.columns(2)
    responsaveis = ["Todos"] + listar_responsaveis()
    filtro_resp = f1.selectbox("Filtrar por Responsável (WHERE)", responsaveis)
    filtro_status = f2.selectbox(
        "Filtrar por Status (WHERE)", ["Todos", "Pendente", "Em Andamento", "Concluída"]
    )

    tarefas, sql_executado = listar_tarefas(filtro_resp, filtro_status)

    if not tarefas:
        st.info("Nenhuma tarefa encontrada para os filtros selecionados.")
    else:
        df = pd.DataFrame(tarefas)
        st.dataframe(
            df[["id", "reuniao", "descricao", "responsavel", "prazo", "prioridade", "status"]],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("**Atualizar ou Excluir Tarefa (UPDATE / DELETE)**")
        opcoes_tarefas = {
            f"#{t['id']} — {t['descricao'][:45]} ({t['responsavel']})": t for t in tarefas
        }
        selecionada_label = st.selectbox("Selecione uma tarefa:", list(opcoes_tarefas.keys()))
        tarefa_atual = opcoes_tarefas[selecionada_label]

        act1, act2, act3 = st.columns([2, 1.2, 1])
        status_lista = ["Pendente", "Em Andamento", "Concluída"]
        novo_status = act1.selectbox(
            "Novo Status",
            status_lista,
            index=status_lista.index(tarefa_atual["status"]),
            label_visibility="collapsed",
        )
        if act2.button("💾 Atualizar", use_container_width=True):
            atualizar_status_tarefa(tarefa_atual["id"], novo_status)
            st.toast(f"Tarefa #{tarefa_atual['id']} atualizada para '{novo_status}'!")
            st.rerun()

        if act3.button("🗑️ Excluir", use_container_width=True):
            excluir_tarefa(tarefa_atual["id"])
            st.toast(f"Tarefa #{tarefa_atual['id']} removida do banco.")
            st.rerun()

    with st.expander("🗄️ Por baixo dos panos: Query SQL executada"):
        st.code(sql_executado, language="sql")
