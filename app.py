import streamlit as st
import pandas as pd

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# =============================================================================
# CONFIGURAÇÃO DA PLANILHA DO GOOGLE SHEETS
# =============================================================================
# 1. Cole aqui o ID Principal da sua planilha (o código entre /d/ e /export)
SHEET_ID = "19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA"

# 2. Defina os GIDs de cada aba (copie o número após gid= na URL de cada aba)
GID_ORDENS_SERVICO = "2075083303"  # Cole o GID da aba Ordens de Serviço
GID_CLIENTES       = "2008875883"          # Cole o GID da aba Clientes (se houver)
GID_SERVICOS       = "1837132453"          # Cole o GID da aba Serviços (se houver)

# Função para gerar a URL de exportação CSV direta de uma aba específica
def obter_url_csv(gid):
    return f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"

# =============================================================================
# FUNÇÃO DE CARREGAMENTO INTELIGENTE
# =============================================================================
@st.cache_data(ttl=5)
def carregar_dados_aba(gid):
    try:
        url = obter_url_csv(gid)
        df_bruto = pd.read_csv(url, header=None)
        
        # Localiza a linha onde está o cabeçalho real (com nome das colunas)
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
            df = pd.read_csv(url, skiprows=3)

        # Limpeza de colunas vazias
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.dropna(how='all')

        return df

    except Exception as e:
        st.error(f"Erro ao carregar aba com GID {gid}: {e}")
        return pd.DataFrame()

# Carrega os dados da aba principal de OS
df = carregar_dados_aba(GID_ORDENS_SERVICO)

if df.empty:
    st.warning("⚠️ Nenhum dado foi encontrado na aba selecionada.")
    st.info("""
    **💡 Como resolver:**
    1. Certifique-se de que a planilha no Google Drive está compartilhada como **"Qualquer pessoa com o link"** (Acesso de Leitor).
    2. Verifique se o número do `GID_ORDENS_SERVICO` no topo do código corresponde exatamente ao `gid=` exibido no final da URL ao clicar na aba no Google Sheets.
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
        
        col_valor = [c for c in df.columns if "VALOR" in str(c).upper() or "TOTAL" in str(c).upper()]
        
        total_faturado = 0.0
        if col_valor:
            col_target = col_valor[0]
            s_limpa = df[col_target].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            total_faturado = pd.to_numeric(s_limpa, errors='coerce').sum()

        col_m1, col_m2
