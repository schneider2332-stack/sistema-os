import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# =============================================================================
# CONFIGURAÇÃO DA PLANILHA DO GOOGLE SHEETS
# =============================================================================
# ID da planilha e GID da aba Ordens de Serviço
SHEET_ID = "19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA"
GID_ORDENS_SERVICO = "417364075"  # Verifique se este gid é exatamente o da aba de OS

# URL de download direto do CSV
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ORDENS_SERVICO}"

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # Lê a planilha CSV diretamente
        df = pd.read_csv(URL_CSV)
        
        # Remove apenas linhas que estiverem inteiramente vazias
        df = df.dropna(how='all')
        
        # Limpa o nome das colunas
        df.columns = [str(c).strip() for c in df.columns]
        
        return df
    except Exception as e:
        st.error(f"Erro ao conectar e ler a planilha: {e}")
        return pd.DataFrame()

df = carregar_dados()

# =============================================================================
# INTERFACE DO STREAMLIT
# =============================================================================
if df.empty:
    st.warning("⚠️ Nenhum dado foi retornado da planilha.")
    st.info("""
    **Checklist de Resolução:**
    1. A sua planilha precisa estar configurada como **"Qualquer pessoa com o link"** (Acesso de Leitor)[cite: 333, 334].
    2. Clique na aba da sua planilha no navegador e veja se no final do link consta exatamente `gid=417364075`.
    """)
else:
    # Menu de Navegação Lateral
    aba = st.sidebar.radio(
        "Navegação do Sistema", 
        ["📊 Visão Geral / Lista Completa", "🔍 Consultar Registro"]
    )

    if aba == "📊 Visão Geral / Lista Completa":
        st.subheader("📑 Tabela de Dados Registrados")
        st.metric("Total de Linhas Carregadas", len(df))
        st.markdown("---")
        # Exibe todos os dados exatamente como vieram do Google Sheets
        st.dataframe(df, use_container_width=True)

    elif aba == "🔍 Consultar Registro":
        st.subheader("📋 Pesquisa de Dados")
        
        coluna_filtro = st.selectbox("Selecione a coluna para pesquisar:", df.columns)
        
        valores_unicos = df[coluna_filtro].dropna().astype(str).unique()
        if len(valores_unicos) > 0:
            item_selecionado = st.selectbox("Selecione o valor:", valores_unicos)
            
            resultado = df[df[coluna_filtro].astype(str) == item_selecionado]
            st.dataframe(resultado, use_container_width=True)
