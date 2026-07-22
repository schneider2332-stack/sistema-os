import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# Configuração da página
st.set_page_config(
    page_title="Sistema de Ordens de Serviço",
    page_icon="🛠️",
    layout="wide"
)

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Lê a aba 'OS' do Google Sheets
    df = conn.read(worksheet="OS", ttl=0)
    # Garante conversão de datas e valores numéricos
    if "Data" in df.columns:
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    if "Valor Total" in df.columns:
        df["Valor Total"] = pd.to_numeric(df["Valor Total"], errors="coerce").fillna(0.0)
    return df

df_os = load_data()

# Menu Lateral Navigation
st.sidebar.title("📌 Menu de Navegação")
menu = st.sidebar.radio(
    "Selecione uma opção:",
    ["📊 OS Cadastradas (Lista)", "➕ Nova OS", "✏️ Editar OS", "📈 Dashboard Financeiro e Fluxo de Caixa"]
)

# ---------------------------------------------------------
# 1. LISTA DE OS
# ---------------------------------------------------------
if menu == "📊 OS Cadastradas (Lista)":
    st.title("📊 Ordens de Serviço Cadastradas")
    
    if not df_os.empty:
        # Filtros de busca na lista
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            status_filter = st.multiselect("Filtrar por Status:", options=df_os["Status"].dropna().unique() if "Status" in df_os.columns else [])
        with col_f2:
            cliente_filter = st.text_input("Buscar por Cliente:")
        
        df_filtered = df_os.copy()
        if status_filter:
            df_filtered = df_filtered[df_filtered["Status"].isin(status_filter)]
        if cliente_filter and "Cliente" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Cliente"].astype(str).str.contains(cliente_filter, case=False, na=False)]
            
        st.dataframe(df_filtered, use_container_width=True)
    else:
        st.info("Nenhuma Ordem de Serviço encontrada.")

# ---------------------------------------------------------
# 2. NOVA OS
# ---------------------------------------------------------
elif menu == "➕ Nova OS":
    st.title("➕ Cadastrar Nova Ordem de Serviço")
    
    with st.form("form_nova_os", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            numero_os = st.text_input("Número da OS *")
            cliente = st.text_input("Nome do Cliente *")
            data_os = st.date_input("Data de Entrada")
            equipamento = st.text_input("Equipamento / Item")
            
        with col2:
            servico = st.text_area("Descrição do Serviço")
            valor = st.number_input("Valor Total (R$)", min_value=0.0, step=10.0, format="%.2f")
            forma_pagto = st.selectbox("Forma de Pagamento", ["Pix", "Cartão", "Dinheiro", "Boleto", "Outro"])
            status = st.selectbox("Status da OS", ["Pendente", "Em Andamento", "Concluído", "Entregue", "Cancelado"])
            
        submitted = st.form_submit_button("Salvar OS")
        
        if submitted:
            if not numero_os or not cliente:
                st.error("Por favor, preencha os campos obrigatórios (*).")
            else:
                nova_linha = pd.DataFrame([{
                    "Nº OS": numero_os,
                    "Cliente": cliente,
                    "Data": data_os.strftime("%Y-%m-%d"),
                    "Equipamento": equipamento,
                    "Serviço": servico,
                    "Valor Total": valor,
                    "Forma Pagamento": forma_pagto,
                    "Status": status
                }])
                
                df_atualizado = pd.concat([df_os, nova_linha], ignore_index=True)
                conn.update(worksheet="OS", data=df_atualizado)
                st.success(f"OS Nº {numero_os} cadastrada com sucesso!")
                st.rerun()

# ---------------------------------------------------------
# 3. EDITAR OS
# ---------------------------------------------------------
elif menu == "✏️ Editar OS":
    st.title("✏️ Editar Ordem de Serviço")
    
    if not df_os.empty and "Nº OS" in df_os.columns:
        os_list = df_os["Nº OS"].astype(str).tolist()
        selected_os = st.selectbox("Selecione o Número da OS que deseja editar:", [""] + os_list)
        
        if selected_os:
            os_data = df_os[df_os["Nº OS"].astype(str) == selected_os].iloc[0]
            
            with st.form("form_editar_os"):
                col1, col2 = st.columns(2)
                
                with col1:
                    cliente = st.text_input("Cliente",
