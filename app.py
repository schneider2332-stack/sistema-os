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
                p_upper = parte.upper()
                match = re.search(r'R\$\s*([\d\.,]+)', parte, re.IGNORECASE) or re.search(r'([\d\.,]+)', parte)
                val_parcial = converter_para_numero(match.group(1)) if match else 0.0
                
                if "PIX" in p_upper:
                    totais['pix'] += val_parcial
                elif "CRÉDITO" in p_upper or "CREDITO" in p_upper:
                    totais['credito'] += val_parcial
                elif "DÉBITO" in p_upper or "DEBITO" in p_upper:
                    totais['debito'] += val_parcial
                elif "DINHEIRO" in p_upper or "ESPÉCIE" in p_upper or "ESPECIE" in p_upper:
                    totais['dinheiro'] += val_parcial
                elif "BOLETO" in p_upper:
                    totais['boleto'] += val_parcial
                elif "CARTÃO" in p_upper or "CARTAO" in p_upper:
                    totais['cartao_generico'] += val_parcial
        else:
            f_upper = forma.upper()
            if "PIX" in f_upper:
                totais['pix'] += val_total
            elif "CRÉDITO" in f_upper or "CREDITO" in f_upper:
                totais['credito'] += val_total
            elif "DÉBITO" in f_upper or "DEBITO" in f_upper:
                totais['debito'] += val_total
            elif "DINHEIRO" in f_upper or "ESPÉCIE" in f_upper or "ESPECIE" in f_upper:
                totais['dinheiro'] += val_total
            elif "BOLETO" in f_upper:
                totais['boleto'] += val_total
            elif "CARTÃO" in f_upper or "CARTAO" in f_upper:
                totais['cartao_generico'] += val_total

    return totais
