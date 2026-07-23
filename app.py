import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Gestão de OS & Finanças", layout="wide")

# Conexão com o Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    """Lê os dados do Google Sheets e trata os tipos."""
    try:
        df = conn.read(ttl="0")  # ttl=0 garante dados em tempo real sem cache travado
        df = df.dropna(how="all")  # Remove linhas totalmente vazias
        
        # Garante colunas mínimas e formatação adequada
        if not df.empty:
            df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0.0)
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Carrega os dados atualizados
df = load_data()

st.title("🛠️ Sistema de Gestão de Ordens de Serviço")

# Menu de navegação lateral
menu = st.sidebar.radio("Navegação", ["Dashboard Financeiro", "Consultar / Editar OS", "Nova OS"])

# -------------------------------------------------------------------
# 1. DASHBOARD FINANCEIRO
# -------------------------------------------------------------------
if menu == "Dashboard Financeiro":
    st.header("📊 Fluxo de Caixa e Métricas")
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        
        total_faturado = df[df["Status"] == "Concluída"]["Valor"].sum()
        pendente = df[df["Status"] == "Em Aberto"]["Valor"].sum()
        total_os = len(df)
        
        col1.metric("Faturamento (Concluídas)", f"R$ {total_faturado:,.2f}")
        col2.metric("A Receber (Em Aberto)", f"R$ {pendente:,.2f}")
        col3.metric("Total de OSs Registradas", total_os)
        
        st.divider()
        st.subheader("Visão Geral do Histórico")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma Ordem de Serviço encontrada na planilha.")

# -------------------------------------------------------------------
# 2. CONSULTAR E EDITAR OS
# -------------------------------------------------------------------
elif menu == "Consultar / Editar OS":
    st.header("🔍 Consultar e Atualizar OS")
    
    if not df.empty:
        os_id = st.selectbox("Selecione o Código/ID da OS:", df["ID_OS"].unique())
        
        # Filtra os dados da OS selecionada
        dados_os = df[df["ID_OS"] == os_id].iloc[0]
        
        with st.form("form_edicao"):
            col1, col2 = st.columns(2)
            cliente = col1.text_input("Cliente", value=str(dados_os["Cliente"]))
            servico = col2.text_input("Serviço", value=str(dados_os["Serviço"]))
            
            col3, col4, col5 = st.columns(3)
            valor = col3.number_input("Valor (R$)", value=float(dados_os["Valor"]), step=10.0)
            
            # Garante opções do status
            status_opcoes = ["Em Aberto", "Em Andamento", "Concluída", "Cancelada"]
            idx_status = status_opcoes.index(dados_os["Status"]) if dados_os["Status"] in status_opcoes else 0
            status = col4.selectbox("Status", status_opcoes, index=idx_status)
            
            data_cad = col5.date_input("Data", value=dados_os["Data"])
            
            btn_atualizar = st.form_submit_button("Atualizar Ordem de Serviço")
            
            if btn_atualizar:
                # Atualiza a linha no DataFrame local
                df.loc[df["ID_OS"] == os_id, ["Cliente", "Serviço", "Valor", "Status", "Data"]] = [
                    cliente, servico, valor, status, data_cad
                ]
                
                # Salva de volta no Google Sheets
                conn.update(data=df)
                st.success("OS atualizada com sucesso!")
                st.rerun()
    else:
        st.info("Não há registros disponíveis para alteração.")

# -------------------------------------------------------------------
# 3. CADASTRAR NOVA OS (COM LIMPEZA AUTOMÁTICA DE FORMULÁRIO)
# -------------------------------------------------------------------
elif menu == "Nova OS":
    st.header("➕ Cadastrar Nova Ordem de Serviço")
    
    # Inicializa variáveis no session_state para permitir a limpeza automática dos campos
    if "novo_cliente" not in st.session_state:
        st.session_state.novo_cliente = ""
    if "novo_servico" not in st.session_state:
        st.session_state.novo_servico = ""
    if "novo_valor" not in st.session_state:
        st.session_state.novo_valor = 0.0

    def limpar_campos():
        """Reseta as variáveis do formulário após o envio."""
        st.session_state.novo_cliente = ""
        st.session_state.novo_servico = ""
        st.session_state.novo_valor = 0.0

    with st.form("form_cadastro", clear_on_submit=False):
        col1, col2 = st.columns(2)
        cliente = col1.text_input("Nome do Cliente", key="novo_cliente")
        servico = col2.text_input("Descrição do Serviço", key="novo_servico")
        
        col3, col4, col5 = st.columns(3)
        valor = col3.number_input("Valor Total (R$)", min_value=0.0, step=10.0, key="novo_valor")
        status = col4.selectbox("Status Inicial", ["Em Aberto", "Em Andamento", "Concluída"])
        data_cad = col5.date_input("Data de Entrada")
        
        btn_salvar = st.form_submit_button("Salvar Ordem de Serviço")
        
        if btn_salvar:
            if not cliente or not servico:
                st.warning("Por favor, preencha o nome do cliente e a descrição do serviço.")
            else:
                # Gerador simples de ID único para a OS
                novo_id = f"OS-{len(df) + 1:04d}"
                
                nova_linha = pd.DataFrame([{
                    "ID_OS": novo_id,
                    "Cliente": cliente,
                    "Serviço": servico,
                    "Valor": valor,
                    "Status": status,
                    "Data": data_cad
                }])
                
                # Concatena a nova linha e atualiza a planilha
                df_atualizado = pd.concat([df, nova_linha], ignore_index=True)
                conn.update(data=df_atualizado)
                
                st.success(f"Ordem de Serviço **{novo_id}** cadastrada com sucesso!")
                
                # Limpa os campos e recarrega a tela
                limpar_campos()
                st.rerun()
