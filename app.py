import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Sistema de OS com Gravação", layout="wide")

st.title("🛠️ Sistema de Gestão de Ordens de Serviço (OS)")

# =============================================================================
# CONEXÃO COM GOOGLE SHEETS
# =============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dados():
    try:
        # Lê a planilha atualizada sem cache estático
        df = conn.read(ttl=0)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        # Tenta ler a aba principal. Altere "Ordens de Serviço" se a sua guia tiver outro nome!
        df = conn.read(worksheet="Ordens de Serviço", ttl=0)
        df = df.dropna(how='all')
        return df
    except Exception as e:
        st.error(f"⚠️ **Detalhes do Erro do Google:** {e}")
        st.info("""
        **Checklist de Correção:**
        1. Verifique se a guia da planilha se chama exatamente `Ordens de Serviço`.
        2. Garanta que o e-mail `client_email` da Service Account está adicionado como **Editor** no botão Compartilhar da planilha.
        3. Certifique-se de que a **Google Sheets API** está ativada no Google Cloud Console.
        """)
        return pd.DataFrame()

def converter_para_numero(valor):
    if pd.isna(valor):
        return 0.0
    val_str = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(val_str)
    except:
        return 0.0

# =============================================================================
# MENU LATERAL
# =============================================================================
menu = st.sidebar.radio(
    "📌 Navegação",
    [
        "📈 Dashboard Financeiro & Fluxo de Caixa",
        "📊 OS Cadastradas (Lista)",
        "🔍 Consultar / Detalhar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar OS / Pagamento"
    ]
)

# =============================================================================
# 1. DASHBOARD FINANCEIRO & FLUXO DE CAIXA
# =============================================================================
if menu == "📈 Dashboard Financeiro & Fluxo de Caixa":
    st.subheader("📈 Painel de Indicadores & Fluxo de Caixa Mensal")
    
    if not df.empty:
        col_valor = next((c for c in df.columns if any(p in c.upper() for p in ["VALOR", "TOTAL", "PREÇO"])), None)
        col_status = next((c for c in df.columns if any(p in c.upper() for p in ["STATUS", "SITUAÇÃO"])), None)
        col_pagto = next((c for c in df.columns if any(p in c.upper() for p in ["PAG", "FORMA"])), None)
        col_data = next((c for c in df.columns if "DATA" in c.upper()), None)
        
        df['VALOR_CALC'] = df[col_valor].apply(converter_para_numero) if col_valor else 0.0
        
        if col_data:
            df['DATA_DT'] = pd.to_datetime(df[col_data], errors='coerce', dayfirst=True)
            df['ANO_MES'] = df['DATA_DT'].dt.strftime('%Y-%m').fillna("Sem Data")
        else:
            df['ANO_MES'] = "Sem Data"

        fat_total = df['VALOR_CALC'].sum()
        
        if col_status:
            status_concluido = df[col_status].astype(str).str.upper().str.contains("PAGO|CONCLUÍDO|CONCLUIDO|ENTREGUE|FINALIZADO", na=False)
            val_recebido = df[status_concluido]['VALOR_CALC'].sum()
            val_aberto = df[~status_concluido]['VALOR_CALC'].sum()
        else:
            val_recebido = fat_total
            val_aberto = 0.0

        m1, m2, m3 = st.columns(3)
        m1.metric("💵 Faturamento Total", f"R$ {fat_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        m2.metric("✅ Valor Recebido", f"R$ {val_recebido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        m3.metric("⏳ Valor em Aberto", f"R$ {val_aberto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        st.markdown("---")
        st.markdown("### 🗓️ Fluxo de Caixa Mensal")
        df_fluxo = df[df['ANO_MES'] != "Sem Data"].groupby('ANO_MES')['VALOR_CALC'].sum().reset_index()
        df_fluxo.columns = ['Mês/Ano', 'Faturamento (R$)']
        
        if not df_fluxo.empty:
            st.bar_chart(df_fluxo.set_index('Mês/Ano'))
            st.dataframe(df_fluxo, use_container_width=True)
    else:
        st.warning("⚠️ Nenhum dado encontrado na planilha.")

# =============================================================================
# 2. LISTA DE OS CADASTRADAS
# =============================================================================
elif menu == "📊 OS Cadastradas (Lista)":
    st.subheader("📋 Tabela Geral de Ordens de Serviço")
    if not df.empty:
        st.metric("Total de OSs Registradas", len(df))
        st.markdown("---")
        st.dataframe(df, use_container_width=True)

# =============================================================================
# 3. CONSULTAR OS
# =============================================================================
elif menu == "🔍 Consultar / Detalhar OS":
    st.subheader("🔍 Consultar Ordem de Serviço")
    if not df.empty:
        coluna_os = next((c for c in df.columns if "OS" in c.upper() or "Nº" in c.upper()), df.columns[0])
        opcoes_os = df[coluna_os].dropna().astype(str).unique()
        os_escolhida = st.selectbox("Selecione a OS:", opcoes_os)
        
        if os_escolhida:
            dados = df[df[coluna_os].astype(str) == os_escolhida]
            st.dataframe(dados, use_container_width=True)

# =============================================================================
# 4. CADASTRAR NOVA OS (GRAVAÇÃO DIRETA)
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Nova OS")
    
    with st.form("form_nova_os", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_os = st.text_input("Número da OS", value=f"OS-{len(df)+1:04d}")
            cliente = st.text_input("Nome do Cliente")
            telefone = st.text_input("Telefone / WhatsApp")
            servico = st.text_area("Descrição do Serviço")
        
        with col2:
            valor = st.number_input("Valor Total (R$)", min_value=0.0, step=10.0, format="%.2f")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
            status = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue"])
            data_entrada = st.date_input("Data de Entrada", datetime.now()).strftime("%d/%m/%Y")
            
        btn_salvar = st.form_submit_button("💾 Salvar no Google Sheets")
        
        if btn_salvar:
            nova_os = pd.DataFrame([{
                "OS": num_os,
                "Cliente": cliente,
                "Telefone": telefone,
                "Serviço": servico,
                "Valor Total": f"R$ {valor:.2f}",
                "Forma Pagamento": forma_pagamento,
                "Status": status,
                "Data": data_entrada
            }])
            
            df_atualizado = pd.concat([df, nova_os], ignore_index=True)
            conn.update(data=df_atualizado)
            
            st.success(f"✅ OS {num_os} gravada com sucesso no Google Sheets!")
            st.rerun()

# =============================================================================
# 5. ALTERAR OS / PAGAMENTO (EDIÇÃO DIRETA)
# =============================================================================
elif menu == "✏️ Alterar OS / Pagamento":
    st.subheader("✏️ Alterar Status e Forma de Pagamento")
    
    if not df.empty:
        coluna_os = next((c for c in df.columns if "OS" in c.upper() or "Nº" in c.upper()), df.columns[0])
        opcoes_os = df[coluna_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS para alterar:", opcoes_os)
        
        if os_para_editar:
            idx = df[df[coluna_os].astype(str) == os_para_editar].index[0]
            
            with st.form("form_editar_os"):
                col1, col2 = st.columns(2)
                
                with col1:
                    novo_status = st.selectbox("Alterar Status", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue", "Cancelado"])
                    nova_forma_pagto = st.selectbox("Alterar Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
                
                with col2:
                    novo_valor = st.number_input("Atualizar Valor (R$)", min_value=0.0, step=5.0, format="%.2f")

                btn_atualizar = st.form_submit_button("🔄 Atualizar no Google Sheets")
                
                if btn_atualizar:
                    df.loc[idx, "Status"] = novo_status
                    df.loc[idx, "Forma Pagamento"] = nova_forma_pagto
                    df.loc[idx, "Valor Total"] = f"R$ {novo_valor:.2f}"
                    
                    conn.update(data=df)
                    
                    st.success(f"✅ OS {os_para_editar} atualizada diretamente no Google Sheets!")
                    st.rerun()
