import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# =============================================================================
# CONFIGURAÇÃO DA PLANILHA DO GOOGLE SHEETS
# =============================================================================
# ID da planilha e GID da aba Ordens de Serviço
SHEET_ID = "19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA"
GID_ORDENS_SERVICO = "417364075"

# URL direta de exportação em formato CSV
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ORDENS_SERVICO}"

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # Lê o CSV baixado diretamente da planilha
        df_bruto = pd.read_csv(URL_CSV, header=None)
        
        # Localiza a linha onde estão os cabeçalhos das colunas
        linha_cabecalho = None
        for idx, row in df_bruto.iterrows():
            valores_linha = [str(val).strip().upper() for val in row.values if pd.notna(val)]
            if any("OS" in v or "CLIENTE" in v or "SERVIÇO" in v for v in valores_linha):
                linha_cabecalho = idx
                break

        if linha_cabecalho is not None:
            df = df_bruto.iloc[linha_cabecalho + 1:].copy()
            df.columns = [str(c).strip() for c in df_bruto.iloc[linha_cabecalho].values]
            df = df.reset_index(drop=True)
        else:
            df = pd.read_csv(URL_CSV)

        # Remove colunas vazias
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.dropna(how='all')

        return df

    except Exception as e:
        st.error(f"Erro ao acessar os dados da planilha: {e}")
        return pd.DataFrame()

df = carregar_dados()

if df.empty:
    st.warning("⚠️ Nenhum dado foi encontrado na aba selecionada.")
    st.info("""
    **💡 Verificação de Acesso (Passo Obrigatório):**
    1. Abra a planilha no **Google Sheets**.
    2. Clique no botão azul **Compartilhar** (canto superior direito).
    3. Em **Acesso Geral**, altere de *Restrito* para **"Qualquer pessoa com o link"**.
    4. Mantenha a permissão como **Leitor** e clique em **Concluído**.
    """)
else:
    # Menu Lateral
    aba = st.sidebar.radio(
        "Navegação do Sistema", 
        ["📈 Dashboard Executivo", "🔍 Consultar OS", "📊 Visão Geral / Lista"]
    )

    if aba == "📈 Dashboard Executivo":
        st.subheader("📈 Dashboard Executivo de Gestão")
        
        st.metric("Total de Registros Carregados", len(df))
        st.markdown("---")
        st.dataframe(df, use_container_width=True)

    elif aba == "🔍 Consultar OS":
        st.subheader("📋 Consultar Registro")
        coluna_busca = st.selectbox("Selecione a coluna para buscar:", df.columns)
        
        opcoes = df[coluna_busca].dropna().astype(str).unique()
        if len(opcoes) > 0:
            item = st.selectbox("Selecione o item:", opcoes)
            st.dataframe(df[df[coluna_busca].astype(str) == item], use_container_width=True)

    elif aba == "📊 Visão Geral / Lista":
        st.subheader("📑 Tabela Completa de Dados")
        st.dataframe(df, use_container_width=True)
