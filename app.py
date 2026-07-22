import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# Link formatado para EXPORTAÇÃO CSV direta (necessário para o pandas)
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA/edit?usp=sharing&gid=417364075"

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # 1. Lê a planilha bruta sem assumir cabeçalho fixo
        df_bruto = pd.read_csv(URL_PLANILHA, header=None)
        
        # 2. Localiza em qual linha estão os nomes reais das colunas (procura por "OS" ou "CLIENTE")
        linha_cabecalho = None
        for idx, row in df_bruto.iterrows():
            valores_linha = [str(val).strip().upper() for val in row.values if pd.notna(val)]
            if any("OS" in v or "CLIENTE" in v for v in valores_linha):
                linha_cabecalho = idx
                break

        # 3. Se encontrou a linha do cabeçalho, reestrutura o dataframe
        if linha_cabecalho is not None:
            df = df_bruto.iloc[linha_cabecalho + 1:].copy()
            df.columns = [str(c).strip() for c in df_bruto.iloc[linha_cabecalho].values]
            df = df.reset_index(drop=True)
        else:
            df = pd.read_csv(URL_PLANILHA, skiprows=3)

        # 4. Remove colunas sem nome ou nulas
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.dropna(how='all')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

# Carregamento dos dados
df = carregar_dados()

if df.empty:
    st.warning("⚠️ Nenhum dado foi encontrado ou a aba selecionada está vazia.")
    st.info("""
    **💡 Como verificar:**
    1. Certifique-se de que a planilha no Google Drive está compartilhada como **"Qualquer pessoa com o link"**.
    2. Confira se a aba com os dados é a primeira aba da planilha (`gid=0`).
    """)
else:
    # Menu Lateral
    aba = st.sidebar.radio(
        "Navegação do Sistema", 
        ["📈 Dashboard Executivo", "🔍 Consultar OS", "➕ Cadastrar Nova OS", "📊 Visão Geral / Lista"]
    )

    # =========================================================================
    # ABA 1: DASHBOARD EXECUTIVO
    # =========================================================================
    if aba == "📈 Dashboard Executivo":
        st.subheader("📈 Dashboard Executivo de Gestão")
        
        total_os = len(df)
        
        col_valor = [c for c in df.columns if "VALOR" in str(c).upper() or "TOTAL" in str(c).upper()]
        
        total_faturado = 0
        if col_valor:
            col_target = col_valor[0]
            s_limpa = df[col_target].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            total_faturado = pd.to_numeric(s_limpa, errors='coerce').sum()

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total de OS Registradas", total_os)
        col_m2.metric("Faturamento Estimado", f"R$ {total_faturado:,.2f}")

        st.markdown("---")
        st.markdown("##### 📌 Tabela de Dados Carregada")
        st.dataframe(df.head(10), use_container_width=True)

    # =========================================================================
    # ABA 2: CONSULTAR OS
    # =========================================================================
    elif aba == "🔍 Consultar OS":
        st.subheader("📋 Consultar Ordem de Serviço")
        
        col_os = [c for c in df.columns if "OS" in str(c).upper() or "NÚMERO" in str(c).upper() or "NUMERO" in str(c).upper()]
        
        if col_os:
            nome_col_os = col_os[0]
            lista_os = df[nome_col_os].dropna().astype(str).unique()
            
            os_selecionada = st.selectbox("Selecione o Número da OS:", lista_os)
            
            if os_selecionada:
                dados_os = df[df[nome_col_os].astype(str) == os_selecionada]
                st.write(dados_os)
        else:
            st.warning("Coluna identificadora de Ordem de Serviço não localizada na planilha.")

    # =========================================================================
    # ABA 3: CADASTRAR NOVA OS
    # =========================================================================
    elif aba == "➕ Cadastrar Nova OS":
        st.subheader("➕ Inserir / Editar Ordem de Serviço")
        st.info("💡 Insira ou altere as Ordens de Serviço diretamente na sua planilha compartilhada no Google Drive. Os dados no sistema serão atualizados automaticamente a cada novo carregamento!")

    # =========================================================================
    # ABA 4: VISÃO GERAL / LISTA
    # =========================================================================
    elif aba == "📊 Visão Geral / Lista":
        st.subheader("📑 Tabela Completa de Ordens de Serviço")
        st.dataframe(df, use_container_width=True)
