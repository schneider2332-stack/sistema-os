import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# Link do Google Sheets exportado como CSV
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1rq9r6Y4MHAf8QxEzxdCz9ty5mNOM5Q7Vc-KIl4VgH5Y/gviz/tq?tqx=out:csv&gid=0"

def identificar_coluna(df, palavras_chave):
    """Auxiliar para encontrar a coluna correta independente de acentos ou maiúsculas/minúsculas."""
    for col in df.columns:
        col_str = str(col).strip().upper()
        if any(p.upper() in col_str for p in palavras_chave):
            return col
    return None

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # Lê o ficheiro CSV vindo da planilha
        df_bruto = pd.read_csv(URL_PLANILHA, header=None)
        
        # Encontra em qual linha estão os nomes das colunas
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
            df = pd.read_csv(URL_PLANILHA, skiprows=3)

        # Remove colunas vazias/sem nome
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.dropna(how='all')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

df = carregar_dados()

if df.empty:
    st.warning("⚠️ Nenhum dado foi encontrado ou a planilha não pôde ser lida.")
else:
    # Identificação flexível das colunas
    col_os = identificar_coluna(df, ["NÚMERO", "NUMERO", "OS", "Nº"])
    col_cliente = identificar_coluna(df, ["CLIENTE", "NOME"])
    col_valor_total = identificar_coluna(df, ["VALOR TOTAL", "TOTAL", "FATURAMENTO"])
    col_valor_pago = identificar_coluna(df, ["VALOR PAGO", "PAGO", "RECEBIDO"])

    # Navegação Lateral
    aba = st.sidebar.radio(
        "Navegação", 
        ["📈 Dashboard Executivo", "🔍 Consultar OS", "📊 Visão Geral / Lista"]
    )

    # 1. Dashboard Executivo
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
        col_m1.metric("Total de OS Registadas", total_os)
        col_m2.metric("Faturamento Estimado", f"R$ {total_faturado:,.2f}")
        col_m3.metric("Total Recebido Estimado", f"R$ {total_recebido:,.2f}")

        st.markdown("---")
        st.dataframe(df, use_container_width=True)

    # 2. Consultar OS
    elif aba == "🔍 Consultar OS":
        st.subheader("📋 Consultar Ordem de Serviço")
        target_col = col_os if col_os else df.columns[0]
        lista_os = df[target_col].dropna().astype(str).unique()
        
        if len(lista_os) > 0:
            os_selecionada = st.selectbox("Selecione a OS:", lista_os)
            if os_selecionada:
                dados_os = df[df[target_col].astype(str) == os_selecionada]
                st.dataframe(dados_os, use_container_width=True)

    # 3. Visão Geral
    elif aba == "📊 Visão Geral / Lista":
        st.subheader("📑 Tabela Completa de Ordens de Serviço")
        st.dataframe(df, use_container_width=True)
