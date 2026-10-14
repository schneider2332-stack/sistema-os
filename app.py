import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL E CONEXÃO
# =============================================================================
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
            return df
        return pd.DataFrame()
    except Exception:
        # Fallback de leitura CSV público caso ocorra oscilação nas credenciais
        try:
            url_csv = "https://docs.google.com/spreadsheets/d/19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA/export?format=csv&gid=417364075"
            df_csv = pd.read_csv(url_csv)
            df_csv = df_csv.dropna(how='all')
            return df_csv
        except Exception:
            return pd.DataFrame()

# Função para formatação monetária padrão brasileiro (R$ 1.300,00)
def formatar_moeda_br(valor_float):
    return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Função segura para conversão monetária (Ex: R$ 1.300,00 -> 1300.0)
def converter_para_numero(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return 0.0
    val_str = str(valor).replace('R$', '').strip()
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except Exception:
        return 0.0

df_os = carregar_dados()

# Mapeamento dinâmico e inteligente das colunas da planilha
def identificar_colunas(df):
    cols = list(df.columns)
    c_os = next((c for c in cols if ("OS" in str(c).upper() or "NUMERO" in str(c).upper() or "Nº" in str(c).upper() or "CÓDIGO" in str(c).upper()) and "DATA" not in str(c).upper()), cols[0] if cols else "Número da OS")
    c_data = next((c for c in cols if "DATA" in str(c).upper()), None)
    c_cli = next((c for c in cols if "CLIENTE" in str(c).upper() or "NOME" in str(c).upper()), None)
    c_desc = next((c for c in cols if "DESC" in str(c).upper() or "SERVIÇO" in str(c).upper() or "SERVICO" in str(c).upper()), None)
    c_val = next((c for c in cols if "VALOR" in str(c).upper() or "TOTAL" in str(c).upper() or "PREÇO" in str(c).upper()), None)
    c_sit = next((c for c in cols if "STATUS" in str(c).upper() or "SITUAÇÃO" in str(c).upper() or "
