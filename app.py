import streamlit as st
import pandas as pd
import re
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Sistema de Ordem de Serviço", layout="wide")

# Función para converter valores para float
def converter_para_float(valor_str):
    if not valor_str:
        return 0.0
    limpo = re.sub(r'[^\d,.-]', '', str(valor_str))
    limpo = limpo.replace('.', '').replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return 0.0

# Função para carregar os dados
@st.cache_data(ttl=1)
def carregar_dados():
    try:
        df = pd.read_excel("Sistema-Ordem-Servico.xlsx", sheet_name="OS")
    except Exception:
        df = pd.DataFrame(columns=[
            "Nº OS", "Cliente", "Serviço", "Valor", "Forma de Pagamento", 
            "Detalhamento Pagamento", "Status", "Data"
        ])
    return df

df_os = carregar_dados()

# Inicialização de variáveis no session_state para permitir limpar o formulário
if 'cliente_input' not in st.session_state:
    st.session_state.cliente_input = ""
if 'servico_input' not in st.session_state:
    st.session_state.servico_input = ""
if 'valor_input' not in st.session_state:
    st.session_state.valor_input = ""
if 'forma_pagto_input' not in st.session_state:
    st.session_state.forma_pagto_input = "Pix"
if 'status_input' not in st.session_state:
    st.session_state.status_input = "Em Andamento"
if 'data_input' not in st.session_state:
    st.session_state.data_input = datetime.now().date()
if 'val_pix' not in st.session_state:
    st.session_state.val_pix = ""
if 'val_cartao' not in st.session_state:
    st.session_state.val_cartao = ""
if 'val_dinheiro' not in st.session_state:
    st.session_state.val_dinheiro = ""
if 'val_boleto' not in st.session_state:
    st.session_state.val_boleto = ""

def limpar_formulario():
    st.session_state.cliente_input = ""
    st.session_state.servico_input = ""
    st.session_state.valor_input = ""
    st.session_state.forma_pagto_input = "Pix"
    st.session_state.status_input = "Em Andamento"
    st.session_state.data_input = datetime.now().date()
    st.session_state.val_pix = ""
    st.session_state.val_cartao = ""
    st.session_state.val_dinheiro = ""
    st.session_state.val_boleto = ""

# Menu Lateral
st.sidebar.title("Navegação")
menu = st.sidebar.radio("Ir para:", ["Dashboard", "Nova OS / Cadastrar", "Consultar / Editar OS"])

# -----------------------------------------------------------------------------
# 1. DASHBOARD
# -----------------------------------------------------------------------------
if menu == "Dashboard":
    st.title("📊 Dashboard de Ordens de Serviço")
    
    if df_os.empty:
        st.warning("Nenhuma Ordem de Serviço cadastrada até o momento.")
    else:
        # Tratar a coluna Valor
        df_os['Valor_Num'] = df_os['Valor'].apply(converter_para_float)
        
        # MÉTIRICAS PRINCIPAIS
        total_os = len(df_os)
        faturamento_total = df_os['Valor_Num'].sum()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de OS Lançadas 📋", f"{total_os}")
            
        with col2:
            st.metric("Faturamento Total 💰", f"R$ {faturamento_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            
        with col3:
            os_concluidas = len(df_os[df_os['Status'] == "Concluída"]) if 'Status' in df_os.columns else 0
            st.metric("OS Concluídas ✅", f"{os_concluidas}")
            
        with col4:
            os_pendentes = len(df_os[df_os['Status'] == "Em Andamento"]) if 'Status' in df_os.columns else 0
            st.metric("OS Em Andamento ⏳", f"{os_pendentes}")
            
        st.markdown("---")
        
        # RESUMO FLUXO DE CAIXA MÊS A MÊS (TABELA)
        st.subheader("📅 Fluxo de Caixa Mês a Mês")
        
        # Converter coluna de Data para datetime para agrupar por mês/ano
        df_os['Data_Dt'] = pd.to_datetime(df_os['Data'], format="%d/%m/%Y", errors='coerce')
        
        # Criar coluna formatada Mês/Ano (ex: 07/2026, 08/2026)
        df_os['Mes_Ano_Sort'] = df_os['Data_Dt'].dt.to_period('M')
        df_os['Mês / Ano'] = df_os['Data_Dt'].dt.strftime('%m/%Y')
        
        # Agrupar dados por mês
        fluxo_mensal = df_os.groupby(['Mes_Ano_Sort', 'Mês / Ano']).agg(
            Qtd_OS=('Nº OS', 'count'),
            Total_Faturado=('Valor_Num', 'sum')
        ).reset_index()
        
        # Ordenar por data cronológica
        fluxo_mensal = fluxo_mensal.sort_values(by='Mes_Ano_Sort', ascending=True)
        
        # Formatar valor em R$ para exibição
        fluxo_mensal['Faturamento (R$)'] = fluxo_mensal['Total_Faturado'].apply(
            lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        
        # Selecionar apenas colunas necessárias para exibição
        tabela_mensal = fluxo_mensal[['Mês / Ano', 'Qtd_OS', 'Faturamento (R$)']].rename(
            columns={'Qtd_OS': 'Qtd. de OS Lançadas'}
        )
        
        st.dataframe(tabela_mensal, use_container_width=True, hide_index=True)

        st.markdown("---")
        
        # Tabela das últimas OS
        st.subheader("📋 Últimas Ordens de Serviço Lançadas")
        st.dataframe(df_os[['Nº OS', 'Cliente', 'Serviço', 'Valor', 'Forma de Pagamento', 'Status', 'Data']].tail(10), use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 2. NOVA OS / CADASTRAR
# -----------------------------------------------------------------------------
elif menu == "Nova OS / Cadastrar":
    st.title("📝 Cadastrar Nova Ordem de Serviço")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        cliente = st.text_input("Nome do Cliente", key="cliente_input")
        servico = st.text_input("Descrição do Serviço", key="servico_input")
        valor_input = st.text_input("Valor (R$)", placeholder="Ex: 1.300,00 ou 1500", key="valor_input")
        
    with col_b:
        forma_pagto = st.selectbox(
            "Forma de Pagamento", 
            ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"],
            key="forma_pagto_input"
        )
        status = st.selectbox("Status Inicial", ["Em Andamento", "Concluída", "Aguardando Peças"], key="status_input")
        data_os = st.date_input("Data da OS", key="data_input")

    # Detalhamento para Pagamento Misto
    detalhes_misto = ""
    if forma_pagto == "Pag
