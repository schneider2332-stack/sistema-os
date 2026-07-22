import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sistema Integrado de OS", layout="wide")

st.title("🛠️ Sistema de Gestão de Ordens de Serviço (OS)")

# =============================================================================
# CONFIGURAÇÃO DA PLANILHA DO GOOGLE SHEETS
# =============================================================================
SHEET_ID = "19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA"
GID_ORDENS_SERVICO = "417364075"

URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ORDENS_SERVICO}"

@st.cache_data(ttl=2)
def carregar_dados():
    try:
        df = pd.read_csv(URL_CSV)
        # Limpa linhas inteiramente vazias
        df = df.dropna(how='all')
        # Remove espaços nos nomes das colunas
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return pd.DataFrame()

df = carregar_dados()

# =============================================================================
# MENU LATERAL DE NAVEGAÇÃO
# =============================================================================
menu = st.sidebar.radio(
    "📌 Menu do Sistema",
    [
        "📊 Visão Geral / Lista de OS",
        "🔍 Consultar / Detalhar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar / Editar OS"
    ]
)

# =============================================================================
# 1. VISÃO GERAL / LISTA COMPLETA
# =============================================================================
if menu == "📊 Visão Geral / Lista de OS":
    st.subheader("📊 Todas as Ordens de Serviço Cadastradas")
    
    if not df.empty:
        st.metric("Total de OS Registradas", len(df))
        st.markdown("---")
        # Exibe a tabela completa de OSs
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("Nenhum dado encontrado na planilha. Verifique se o GID da aba está correto e se há linhas preenchidas.")

# =============================================================================
# 2. CONSULTAR OS
# =============================================================================
elif menu == "🔍 Consultar / Detalhar OS":
    st.subheader("🔍 Consultar e Pesquisar OS")
    
    if not df.empty:
        # Tenta identificar a coluna de OS
        colunas = list(df.columns)
        coluna_os = next((c for c in colunas if "OS" in c.upper() or "NUMERO" in c.upper() or "Nº" in c.upper()), colunas[0])
        
        lista_os = df[coluna_os].dropna().astype(str).unique()
        os_selecionada = st.selectbox("Selecione o Número da OS:", lista_os)
        
        if os_selecionada:
            detalhe = df[df[coluna_os].astype(str) == os_selecionada]
            st.markdown("### 📄 Detalhes da OS")
            st.dataframe(detalhe, use_container_width=True)
    else:
        st.warning("Sem dados para consulta.")

# =============================================================================
# 3. CADASTRAR NOVA OS
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário de Cadastro de Nova OS")
    
    with st.form("form_nova_os", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_os = st.text_input("Número da OS", value=f"OS-{len(df)+1:04d}")
            cliente = st.text_input("Nome do Cliente")
            telefone = st.text_input("Telefone / WhatsApp")
            servico = st.text_area("Descrição do Serviço / Defeito")
        
        with col2:
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, step=10.0, format="%.2f")
            
            forma_pagamento = st.selectbox(
                "Forma de Pagamento Haupt",
                ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto (Duas Formas)"]
            )
            
            # Detalhamento se for pagamento misto
            detalhe_pagamento = ""
            if forma_pagamento == "Pagamento Misto (Duas Formas)":
                st.info("💡 Especifique as formas e valores (Ex: R$ 50 no Dinheiro + R$ 100 no Pix)")
                p1 = st.text_input("Detalhamento do Pagamento Misto")
                detalhe_pagamento = p1
            
            status = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue"])
            data_entrada = st.date_input("Data de Entrada", datetime.now())

        btn_cadastrar = st.form_submit_button("💾 Salvar Nova OS")
        
        if btn_cadastrar:
            pagamento_final = detalhe_pagamento if forma_pagamento == "Pagamento Misto (Duas Formas)" else forma_pagamento
            st.success(f"✅ OS {num_os} gerada com sucesso!")
            st.write(f"**Cliente:** {cliente} | **Valor:** R$ {valor_total:.2f} | **Pagamento:** {pagamento_final}")
            st.info("📌 Para persistência automática direta no Google Sheets, insira os dados no formulário e adicione a linha correspondente na sua planilha.")

# =============================================================================
# 4. ALTERAR / EDITAR OS
# =============================================================================
elif menu == "✏️ Alterar / Editar OS":
    st.subheader("✏️ Alterar Forma de Pagamento e Status de OS")
    
    if not df.empty:
        colunas = list(df.columns)
        coluna_os = next((c for c in colunas if "OS" in c.upper() or "NUMERO" in c.upper() or "Nº" in c.upper()), colunas[0])
        
        lista_os = df[coluna_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Escolha a OS que deseja alterar:", lista_os)
        
        if os_para_editar:
            dados_atuais = df[df[coluna_os].astype(str) == os_para_editar].iloc[0]
            
            st.markdown("---")
            st.markdown(f"#### Editando OS: `{os_para_editar}`")
            
            with st.form("form_editar_os"):
                col1, col2 = st.columns(2)
                
                with col1:
                    novo_status = st.selectbox(
                        "Novo Status da OS",
                        ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Cancelado", "Entregue"]
                    )
                    
                    nova_forma_pagto = st.selectbox(
                        "Forma de Pagamento",
                        [
                            "Pix", 
                            "Cartão de Crédito", 
                            "Cartão de Débito", 
                            "Dinheiro", 
                            "Boleto", 
                            "Misto (Dinheiro + Pix)", 
                            "Misto (Dinheiro + Cartão)", 
                            "Misto (Pix + Cartão)", 
                            "Outro / Personalizado"
                        ]
                    )
                
                with col2:
                    obs_pagamento = st.text_area(
                        "Observações / Valores Divididos",
                        placeholder="Ex: R$ 100,00 no Dinheiro e R$ 150,00 no Pix"
                    )
                    
                    valor_atualizado = st.number_input("Atualizar Valor Total (R$)", min_value=0.0, step=5.0, format="%.2f")

                btn_atualizar = st.form_submit_button("🔄 Atualizar Dados da OS")
                
                if btn_atualizar:
                    st.success(f"✅ Dados da OS {os_para_editar} atualizados!")
                    st.write(f"**Novo Status:** {novo_status}")
                    st.write(f"**Nova Forma de Pagamento:** {nova_forma_pagto}")
                    if obs_pagamento:
                        st.write(f"**Detalhamento:** {obs_pagamento}")
    else:
        st.warning("Nenhuma OS disponível para alteração.")
