import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# Link formatado para exportação direta de dados em CSV
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1rq9r6Y4MHAf8QxEzxdCz9ty5mNOM5Q7Vc-KIl4VgH5Y/gviz/tq?tqx=out:csv&gid=0"

def identificar_coluna(df, palavras_chave):
    """Auxiliar para encontrar a coluna correta independente de maiúsculas, minúsculas ou espaços."""
    for col in df.columns:
        col_str = str(col).strip().upper()
        if any(p.upper() in col_str for p in palavras_chave):
            return col
    return None

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # 1. Lê a planilha bruta sem cabeçalho pré-definido
        df_bruto = pd.read_csv(URL_PLANILHA, header=None)
        
        # 2. Localiza em qual linha está o cabeçalho das colunas
        linha_cabecalho = None
        for idx, row in df_bruto.iterrows():
            valores_linha = [str(val).strip().upper() for val in row.values if pd.notna(val)]
            if any("OS" in v or "CLIENTE" in v or "SERVIÇO" in v for v in valores_linha):
                linha_cabecalho = idx
                break

        # 3. Reestrutura a tabela se encontrou a linha de cabeçalho
        if linha_cabecalho is not None:
            df = df_bruto.iloc[linha_cabecalho + 1:].copy()
            df.columns = [str(c).strip() for c in df_bruto.iloc[linha_cabecalho].values]
            df = df.reset_index(drop=True)
        else:
            df = pd.read_csv(URL_PLANILHA, skiprows=3)

        # 4. Limpa colunas 'Unnamed' ou vazias
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.dropna(how='all')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

# Carregamento seguro dos dados
df = carregar_dados()

if df.empty:
    st.warning("⚠️ Nenhum dado foi encontrado ou a aba selecionada está vazia.")
    st.info("""
    **💡 Como verificar:**
    1. Certifique-se de que a planilha no Google Drive está compartilhada como **"Qualquer pessoa com o link"**.
    2. Confira se os dados das Ordens de Serviço estão na primeira aba da planilha (`gid=0`).
    """)
else:
    # Identificação flexível de colunas cruciais
    col_os = identificar_coluna(df, ["NÚMERO", "NUMERO", "OS", "Nº"])
    col_cliente = identificar_coluna(df, ["CLIENTE", "NOME"])
    col_valor_total = identificar_coluna(df, ["VALOR TOTAL", "TOTAL", "FATURAMENTO"])
    col_valor_pago = identificar_coluna(df, ["VALOR PAGO", "PAGO", "RECEBIDO"])
    col_situacao = identificar_coluna(df, ["SITUAÇÃO", "SITUACAO", "STATUS"])

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
        
        total_faturado = 0.0
        if col_valor_total:
            s_limpa = df[col_valor_total].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            total_faturado = pd.to_numeric(s_limpa, errors='coerce').sum()

        total_recebido = 0.0
        if col_valor_pago:
            s_pago = df[col_valor_pago].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            total_recebido = pd.to_numeric(s_pago, errors='coerce').sum()

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Total de OS Registradas", total_os)
        col_m2.metric("Faturamento Total Estimado", f"R$ {total_faturado:,.2f}")
        col_m3.metric("Total Recebido Estimado", f"R$ {total_recebido:,.2f}")

        st.markdown("---")
        st.markdown("##### 📌 Tabela de Dados Carregada")
        st.dataframe(df, use_container_width=True)

    # =========================================================================
    # ABA 2: CONSULTAR OS
    # =========================================================================
    elif aba == "🔍 Consultar OS":
        st.subheader("📋 Consultar Ordem de Serviço")
        
        target_col = col_os if col_os else df.columns[0]
        lista_os = df[target_col].dropna().astype(str).unique()
        
        if len(lista_os) > 0:
            os_selecionada = st.selectbox("Selecione a OS:", lista_os)
            
            if os_selecionada:
                dados_os = df[df[target_col].astype(str) == os_selecionada]
                st.dataframe(dados_os, use_container_width=True)
        else:
            st.warning("Nenhum registro de OS encontrado para consulta.")

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
