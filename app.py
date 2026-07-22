import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sistema de Gestão de OS", layout="wide")

st.title("🛠️ Sistema de Gestão de Ordens de Serviço (OS)")

# =============================================================================
# CONFIGURAÇÃO E CARREGAMENTO DA PLANILHA
# =============================================================================
SHEET_ID = "19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA"
GID_ORDENS_SERVICO = "417364075"

URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ORDENS_SERVICO}"

@st.cache_data(ttl=2)
def carregar_dados():
    try:
        df_raw = pd.read_csv(URL_CSV, header=None)
        
        if df_raw.empty:
            return pd.DataFrame()
        
        linha_cabecalho = None
        for idx, row in df_raw.iterrows():
            linha_texto = [str(val).upper().strip() for val in row.values if pd.notna(val)]
            if any("OS" in item or "CLIENTE" in item or "SERVIÇO" in item or "STATUS" in item for item in linha_texto):
                linha_cabecalho = idx
                break
        
        if linha_cabecalho is not None:
            df = df_raw.iloc[linha_cabecalho + 1:].copy()
            df.columns = [str(val).strip() for val in df_raw.iloc[linha_cabecalho].values]
        else:
            df = df_raw.copy()
            df.columns = [f"Coluna_{i}" for i in range(df.shape[1])]

        df = df.dropna(how='all')
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.reset_index(drop=True)
        
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        return pd.DataFrame()

df = carregar_dados()

# =============================================================================
# MENU LATERAL DE NAVEGAÇÃO
# =============================================================================
menu = st.sidebar.radio(
    "📌 Navegação",
    [
        "📈 Dashboard Financeiro",
        "📊 OS Cadastradas (Lista)",
        "🔍 Consultar / Detalhar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar OS / Pagamento"
    ]
)

# Funções auxiliares para cálculo numérico seguro
def converter_valor(val):
    if pd.isna(val):
        return 0.0
    val_str = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(val_str)
    except:
        return 0.0

# =============================================================================
# 1. DASHBOARD FINANCEIRO
# =============================================================================
if menu == "📈 Dashboard Financeiro":
    st.subheader("📈 Painel de Indicadores e Resumo Financeiro")
    
    if not df.empty:
        colunas = [c.upper() for c in df.columns]
        
        # Identifica colunas automaticamente
        col_valor = next((c for c in df.columns if "VALOR" in c.upper() or "PREÇO" in c.
