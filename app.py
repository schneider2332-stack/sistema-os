import streamlit as st
import pandas as pd
from datetime import datetime
import re
from streamlit_gsheets import GSheetsConnection

# 1. Configuração Inicial da Página
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

# Formatação monetária padrão brasileiro (R$ 1.300,00)
def formatar_moeda_br(valor_float):
    return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Conversão monetária segura
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

# 2. Carregamento dos dados
@st.cache_data(ttl=0)
def carregar_dados():
    # Tentativa 1: Via conexão oficial GSheets (lendo a partir da linha 4)
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Ordens de Serviço", ttl=0)
        if df is not None and not df.empty:
            # Se a linha de cabeçalho estiver abaixo, localiza a linha com 'Número da OS'
            if 'Número da OS' not in df.columns:
                for idx, row in df.iterrows():
                    if row.astype(str).str.contains('Número da OS|Numero da OS', case=False).any():
                        df.columns = df.iloc[idx]
                        df = df.iloc[idx+1:].reset_index(drop=True)
                        break
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
            return df
    except Exception:
        pass

    # Tentativa 2: Fallback direto via CSV lendo os cabeçalhos da linha 4
    try:
        url_csv = "https://docs.google.com/spreadsheets/d/1IHmxCEP3VdPK7eKR3aoKTsDb-3z6u5auIqlhZoGtRnU/gviz/tq?tqx=out:csv&sheet=Ordens%20de%20Servi%C3%A7o"
        df_csv = pd.read_csv(url_csv, skiprows=3) # Pula as 3 linhas em branco do topo
        df_csv = df_csv.dropna(how='all')
        df_csv = df_csv.loc[:, ~df_csv.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        return df_csv
    except Exception:
        pass

    return pd.DataFrame()

# Identificação inteligente das colunas
def identificar_colunas(df):
    cols = list(df.columns)
    c_os = next((c for c in cols if ("OS" in str(c).upper() or "NUMERO" in str(c).upper() or "Nº" in str(c).upper() or "CÓDIGO" in str(c).upper()) and "DATA" not in str(c).upper()), cols[0] if cols else "Número da OS")
    c_data = next((c for c in cols if "DATA" in str(c).upper() and "PAGAMENTO" not in str(c).upper()), None)
    c_cli = next((c for c in cols if "CLIENTE" in str(c).upper() or "NOME" in str(c).upper()), None)
    c_desc = next((c for c in cols if "DESC" in str(c).upper() or "SERVIÇO" in str(c).upper() or "SERVICO" in str(c).upper()), None)
    c_val = next((c for c in cols if str(c).strip().upper() in ["VALOR TOTAL", "TOTAL", "VALOR"]), None)
    c_pago = next((c for c in cols if str(c).strip().upper() in ["VALOR PAGO", "PAGO"]), None)
    c_pend = next((c for c in cols if str(c).strip().upper() in ["VALOR PENDENTE", "PENDENTE"]), None)
    c_sit = next((c for c in cols if "STATUS" in str(c).upper() or "SITUAÇÃO" in str(c).upper() or "SITUACAO" in str(c).upper()), None)
    c_tel = next((c for c in cols if "TEL" in str(c).upper() or "WHATS" in str(c).upper() or "FONE" in str(c).upper()), None)
    
    # Colunas diretas de formas de pagamento na planilha
    c_pix = next((c for c in cols if str(c).strip().upper() == "PIX"), None)
    c_cartao = next((c for c in cols if "CART" in str(c).upper()), None)
    c_boleto = next((c for c in cols if "BOLETO" in str(c).upper()), None)
    c_dinheiro = next((c for c in cols if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

    return c_os, c_data, c_cli, c_desc, c_val, c_pago, c_pend, c_sit, c_tel, c_pix, c_cartao, c_boleto, c_dinheiro

df_os = carregar_dados()

# Menu Lateral
st.sidebar.title("🛠️ Sistema OS")
menu = st.sidebar.radio(
    "Navegação",
    [
        "📈 Dashboard Financeiro",
        "📊 OS Cadastradas (Lista)",
        "🔍 Consultar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar OS / Pagamento"
    ]
)

# =============================================================================
# 1. DASHBOARD FINANCEIRO & FLUXO DE CAIXA MENSAL
# =============================================================================
if menu == "📈 Dashboard Financeiro":
    st.subheader("📈 Dashboard Executivo & Fluxo de Caixa")
    
    if not df_os.empty:
        c_os, c_data, c_cli, c_desc, c_val, c_pago, c_pend, c_sit, c_tel, c_pix, c_cartao, c_boleto, c_dinheiro = identificar_colunas(df_os)

        df_calc = df_os.copy()
        df_calc['VALOR_NUM'] = df_calc[c_val].apply(converter_para_numero) if c_val else 0.0
        df_calc['PAGO_NUM'] = df_calc[c_pago].apply(converter_para_numero) if c_pago else 0.0
        df_calc['PEND_NUM'] = df_calc[c_pend].apply(converter_para_numero) if c_pend else 0.0

        if c_pix: df_calc['PIX_NUM'] = df_calc[c_pix].apply(converter_para_numero)
        if c_cartao: df_calc['CARTAO_NUM'] = df_calc[c_cartao].apply(converter_para_numero)
        if c_boleto: df_calc['BOLETO_NUM'] = df_calc[c_boleto].apply(converter_para_numero)
        if c_dinheiro: df_calc['DINHEIRO_NUM'] = df_calc[c_dinheiro].apply(converter_para_numero)

        if c_data:
            df_calc['DATA_DT'] = pd.to_datetime(df_calc[c_data], errors='coerce')
            df_calc['MES_ANO'] = df_calc['DATA_DT'].dt.strftime('%m/%Y')
            
            meses_disponiveis = df_calc['MES_ANO'].dropna().unique().tolist()
            try:
                meses_disponiveis.sort(key=lambda x: datetime.strptime(x, '%m/%Y'), reverse=True)
            except Exception:
                pass
            
            opcoes_mes = ["📅 Todos os Meses (Geral)"] + meses_disponiveis
        else:
            opcoes_mes = ["📅 Todos os Meses (Geral)"]

        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            mes_selecionado = st.selectbox("📆 **Filtrar Período do Dashboard:**", opcoes_mes)

        if mes_selecionado != "📅 Todos os Meses (Geral)" and c_data:
            df_filtrado = df_calc[df_calc['MES_ANO'] == mes_selecionado].copy()
            st.caption(f"Exibindo dados consolidados referentes a **{mes_selecionado}**")
        else:
            df_filtrado = df_calc.copy()
            st.caption("Exibindo dados acumulados de **todo o período**")

        st.markdown("<br>", unsafe_allow_html=True)

        total_faturado = df_filtrado['VALOR_NUM'].sum()
        total_qtd_os = len(df_filtrado)
        val_recebido = df_filtrado['PAGO_NUM'].sum() if c_pago else total_faturado
        val_aberto = df_filtrado['PEND_NUM'].sum() if c_pend else (total_faturado - val_recebido)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Total OS Lançadas", total_qtd_os)
        m2.metric("💵 Faturamento Total", formatar_moeda_br(total_faturado))
        m3.metric("✅ Valor Recebido", formatar_moeda_br(val_recebido))
        m4.metric("⏳ Valor em Aberto", formatar_moeda_br(val_aberto))

        st.markdown("---")
        st.markdown(f"##### 💳 Faturamento Efetivado por Forma de Pagamento ({'Geral' if mes_selecionado == '📅 Todos os Meses (Geral)' else mes_selecionado})")

        tot_pix = df_filtrado['PIX_NUM'].sum() if c_pix else 0.0
        tot_cartao = df_filtrado['CARTAO_NUM'].sum() if c_cartao else 0.0
        tot_boleto = df_filtrado['BOLETO_NUM'].sum() if c_boleto else 0.0
        tot_dinheiro = df_filtrado['DINHEIRO_NUM'].sum() if c_dinheiro else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📱 Pix (Recebido)", formatar_moeda_br(tot_pix))
        p2.metric("💳 Cartão", formatar_moeda_br(tot_cartao))
        p3.metric("💵 Dinheiro", formatar_moeda_br(tot_dinheiro))
        p4.metric("📄 Boleto", formatar_moeda_br(tot_boleto))

        st.
