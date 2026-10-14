import streamlit as st
import pandas as pd
from datetime import datetime
import re
from streamlit_gsheets import GSheetsConnection

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL E CONEXÃO
# =============================================================================
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Ordens de Serviço", ttl=0)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
            return df
        return pd.DataFrame()
    except Exception:
        # Fallback de leitura CSV com o link da sua planilha atual
        try:
            url_csv = "https://docs.google.com/spreadsheets/d/1IHmxCEP3VdPK7eKR3aoKTsDb-3z6u5auIqlhZoGtRnU/export?format=csv&gid=0"
            df_csv = pd.read_csv(url_csv)
            df_csv = df_csv.dropna(how='all')
            return df_csv
        except Exception:
            return pd.DataFrame()

# Formatação monetária padrão brasileiro (R$ 1.300,00)
def formatar_moeda_br(valor_float):
    return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Conversão monetária segura (Ex: R$ 1.300,00 -> 1300.0)
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

# Decomposição exata de pagamentos puros e mistos (aplicada apenas para valores recebidos)
def extrair_totais_pagamento(df_escopo, col_pagto, col_val_num):
    totais = {
        'pix': 0.0,
        'credito': 0.0,
        'debito': 0.0,
        'dinheiro': 0.0,
        'boleto': 0.0,
        'cartao_generico': 0.0
    }
    
    if not col_pagto or df_escopo.empty:
        return totais

    for _, row in df_escopo.iterrows():
        forma = str(row.get(col_pagto, '')).strip()
        val_total = float(row.get(col_val_num, 0.0))
        
        if "MISTO" in forma.upper():
            partes = forma.split('|')
            for parte in partes:
