import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# Link do Google Sheets (exportação em formato CSV)
# Caso a sua aba de OSs tenha um gid diferente, troque o 'gid=0' pelo número da sua aba no link do navegador.
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1rq9r6Y4MHAf8QxEzxdCz9ty5mNOM5Q7Vc-KIl4VgH5Y/edit?usp=sharing&gid=0"

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # 1. Lê a planilha bruta sem assumir cabeçalho fixo
        df_bruto = pd.read_csv(URL_PLANILHA, header=None)
        
        # 2. Localiza em qual linha estão os nomes reais das colunas
        linha_cabecalho = None
        for idx, row in df_bruto.iterrows():
            valores_linha = [str(val).strip() for val in row.values if pd.notna(val)]
            # Procura por palavras-chave presentes no cabeçalho das suas OS
            if any("OS" in v.upper() or "CLIENTE" in v.upper() for v in valores_linha):
                linha_cabecalho = idx
                break

        # 3. Se encontrou a linha do cabeçalho, reestrutura o dataframe
        if linha_cabecalho is not None:
            # Define a linha encontrada como cabeçalho
            df = df_bruto.iloc[linha_cabecalho + 1:].copy()
            df.columns = [str(c).strip() for c in df_bruto.iloc[linha_cabecalho].values]
            df = df.reset_index(drop=True)
        else:
            # Caso não ache por palavra-chave, pula as primeiras 3 linhas padrão de cabeçalho formatado
            df = pd.read_csv(URL_PLANILHA, skiprows=3)

        # 4. Remove colunas sem nome (ex: Unnamed: 0, nan) e linhas vazias
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
    2. Confira se os dados das Ordens de Serviço estão na primeira aba da planilha (caso estejam em outra aba, ajuste o parâmetro `gid=` na URL dentro do código `app.py`).
    """)
else:
    # Menu Lateral de Navegação
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
        
        # Tenta identificar colunas de valores para métricas financeiras
        col_valor = [c for c in df.columns if "VALOR" in c.upper() or "TOTAL" in c.upper() or "FATURAMENTO" in c.upper()]
        
        total_faturado = 0
        if col_valor:
            col_target = col_valor[0]
            # Converte valores numéricos caso estejam em formato de moeda R$
            s_limpa = df[col_target].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            total_faturado = pd.to_numeric(s_limpa, errors='coerce').sum()

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total de OS Registradas", total_os)
        col_m2.metric("Faturamento Estimado", f"R$ {total_faturado:,.2f}")

        st.markdown("---")
        st.markdown("##### 📌 Prévia dos Registros Encontrados")
        st.dataframe(df.head(10), use_container_width=True)

    # =========================================================================
    # ABA 2: CONSULTAR OS
    # =========================================================================
    elif aba == "🔍 Consultar OS":
        st.subheader("📋 Consultar Ordem de Serviço")
        
        col_os = [c for c in df.columns if "OS" in c.upper() or "NÚMERO" in c.upper() or "NUMERO" in c.upper()]
        
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
