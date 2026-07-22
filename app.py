import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime

# 1. Configuração da página do Streamlit
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🛠️",
    layout="wide"
)

# 2. Autenticação e Conexão com Google Sheets
@st.cache_resource
def conectar_google_sheets():
    # Define os escopos de acesso do Google Drive/Sheets
    escopos = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Carrega as credenciais a partir dos segredos do Streamlit (.streamlit/secrets.toml)
    # ou de um arquivo JSON local se preferir
    try:
        credenciais = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=escopos
        )
    except Exception:
        # Fallback para arquivo local 'credentials.json' se não estiver usando secrets
        credenciais = Credentials.from_service_account_file(
            "credentials.json",
            scopes=escopos
        )
        
    client = gspread.authorize(credenciais)
    return client

# Conecta ao arquivo no Google Drive pelo nome exato do arquivo/planilha
@st.cache_data(ttl=60)
def carregar_dados_aba(nome_aba):
    client = conectar_google_sheets()
    # Nome exato da sua planilha no Google Drive:
    planilha = client.open("Sistema-Ordem-Serviço")
    aba = planilha.worksheet(nome_aba)
    dados = aba.get_all_records()
    return pd.DataFrame(dados), aba

# Função auxiliar para limpar seleções do estado e recarregar a aplicação
def limpar_estado():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------
# Carga dos dados das abas da planilha
# ---------------------------------------------------------
try:
    df_os, aba_os = carregar_dados_aba("Ordens de Serviço")
    df_clientes, aba_clientes = carregar_dados_aba("Clientes")
    df_servicos, aba_servicos = carregar_dados_aba("Serviços")
except Exception as e:
    st.error(f"Erro ao conectar com o Google Sheets: {e}")
    st.stop()

# ---------------------------------------------------------
# Interface Principal - Menu Lateral
# ---------------------------------------------------------
st.sidebar.title("🛠️ Gestão de OS")
opcao_menu = st.sidebar.radio(
    "Navegação",
    ["Painel / Listagem", "Nova Ordem de Serviço", "Editar / Alterar OS"]
)

# ---------------------------------------------------------
# ABA 1: Painel / Listagem de OS
# ---------------------------------------------------------
if opcao_menu == "Painel / Listagem":
    st.title("📋 Ordens de Serviço Cadastradas")
    
    # Métricas Rápidas
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de OS", len(df_os))
    os_abertas = len(df_os[df_os["Status"] != "Concluído"]) if "Status" in df_os.columns else 0
    col2.metric("OS em Aberto", os_abertas)
    
    st.divider()
    
    # Tabela com filtro simples
    busca = st.text_input("🔍 Pesquisar por Cliente ou N° OS:")
    if busca and not df_os.empty:
        df_filtrado = df_os[
            df_os.astype(str).apply(lambda row: row.str.contains(busca, case=False).any(), axis=1)
        ]
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.dataframe(df_os, use_container_width=True)

# ---------------------------------------------------------
# ABA 2: Cadastrar Nova OS
# ---------------------------------------------------------
elif opcao_menu == "Nova Ordem de Serviço":
    st.title("➕ Nova Ordem de Serviço")
    
    lista_clientes = df_clientes["Nome"].dropna().unique().tolist() if "Nome" in df_clientes.columns else []
    lista_servicos = df_servicos["Serviço"].dropna().unique().tolist() if "Serviço" in df_servicos.columns else []

    with st.form("form_nova_os", clear_on_submit
