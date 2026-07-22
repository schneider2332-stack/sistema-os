import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# ID da sua planilha pública
SPREADSHEET_ID = "1rq9r6Y4MHAf8QxEzxdCz9ty5mNOM5Q7Vc-KIl4VgH5Y"

# Altere '0' pelo número do gid da aba de OS caso a sua aba principal seja outra
GID = "0" 

URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid={0}"

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # Lê o CSV gerado diretamente pelo Google Sheets
        df = pd.read_csv(URL_PLANILHA)
        
        # Remove colunas completamente vazias
        df = df.dropna(how='all', axis=1)
        
        # Procura a linha de cabeçalho válida (que contenha 'OS' ou 'Cliente')
        if not df.empty and not any("OS" in str(c) or "Cliente" in str(c) for c in df.columns):
            for idx, row in df.iterrows():
                valores = [str(v).strip() for v in row.values if pd.notna(v)]
                if any("OS" in v or "Cliente" in v for v in valores):
                    df.columns = df.iloc[idx].values
                    df = df.iloc[idx + 1:].reset_index(drop=True)
                    break

        # Limpeza de nomes de colunas
        df.columns = [str(c).strip() for c in df.columns]
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

# Carregamento
df = carregar_dados()

if df.empty:
    st.warning("⚠️ Nenhum dado foi encontrado ou a aba selecionada está vazia.")
    st.info("""
    **Como corrigir:**
    1. Certifique-se de que a planilha está compartilhada como **"Qualquer pessoa com o link"**.
    2. Verifique se a aba de Ordens de Serviço é a primeira aba da planilha ou atualize a variável `GID` no código `app.py` com o número da aba correta.
    """)
else:
    # Menu Lateral
    aba = st.sidebar.radio(
        "Navegação do Sistema", 
        ["📈 Dashboard Executivo", "🔍 Consultar OS", "➕ Cadastrar Nova OS", "📊 Visão Geral / Lista"]
    )

    # ABA 1: DASHBOARD
    if aba == "📈 Dashboard Executivo":
        st.subheader("📈 Dashboard Executivo de Gestão")
        
        total_os = len(df)
        col_total = [c for c in df.columns if "Total" in c or "Valor" in c]
        
        total_faturado = 0
        if col_total:
            total_faturado = pd.to_numeric(df[col_total[0]].astype(str).str.replace('R$', '').str.replace('.', '').str.replace(',', '.'), errors='coerce').sum()

        m1, m2 = st.columns(2)
        m1.metric("Total de OS Registradas", total_os)
        m2.metric("Faturamento Identificado", f"R$ {total_faturado:,.2f}")

        st.markdown("---")
        st.dataframe(df.head(10), use_container_width=True)

    # ABA 2: CONSULTAR OS
    elif aba == "🔍 Consultar OS":
        st.subheader("📋 Consultar OS")
        col_os = [c for c in df.columns if "OS" in c or "Número" in c]
        
        if col_os:
            os_list = df[col_os[0]].dropna().astype(str).unique()
            os_selecionada = st.selectbox("Selecione a OS:", os_list)
            
            if os_selecionada:
                dados = df[df[col_os[0]].astype(str) == os_selecionada]
                st.write(dados)
        else:
            st.warning("Coluna de Número da OS não identificada.")

    # ABA 3: CADASTRAR NOVA OS
    elif aba == "➕ Cadastrar Nova OS":
        st.subheader("➕ Inserir Nova Ordem de Serviço")
        st.info("💡 Insira ou altere as OS diretamente na sua planilha no Google Drive. O painel atualizará os dados automaticamente em alguns segundos!")

    # ABA 4: VISÃO GERAL
    elif aba == "📊 Visão Geral / Lista":
        st.subheader("📑 Tabela Completa")
        st.dataframe(df, use_container_width=True)
