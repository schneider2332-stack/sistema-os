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
        # Lê a planilha sem definir cabeçalho fixo para analisar a estrutura
        df_raw = pd.read_csv(URL_CSV, header=None)
        
        if df_raw.empty:
            return pd.DataFrame()
        
        # Procura a linha que contém as colunas principais
        linha_cabecalho = None
        for idx, row in df_raw.iterrows():
            linha_texto = [str(val).upper().strip() for val in row.values if pd.notna(val)]
            if any("OS" in item or "CLIENTE" in item or "SERVIÇO" in item or "STATUS" in item for item in linha_texto):
                linha_cabecalho = idx
                break
        
        # Se encontrou a linha de cabeçalho, ajusta o DataFrame
        if linha_cabecalho is not None:
            df = df_raw.iloc[linha_cabecalho + 1:].copy()
            df.columns = [str(val).strip() for val in df_raw.iloc[linha_cabecalho].values]
        else:
            df = df_raw.copy()
            df.columns = [f"Coluna_{i}" for i in range(df.shape[1])]

        # Limpeza de linhas e colunas completamente vazias
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
        "📊 OS Cadastradas (Lista)",
        "🔍 Consultar / Detalhar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar OS / Pagamento"
    ]
)

# =============================================================================
# 1. LISTA COMPLETA DE OS CADASTRADAS
# =============================================================================
if menu == "📊 OS Cadastradas (Lista)":
    st.subheader("📋 Lista Geral de Ordens de Serviço")
    
    if not df.empty:
        st.metric("Total de Linhas / OSs Encontradas", len(df))
        st.markdown("---")
        # Exibe a tabela com todas as linhas da planilha
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ Não foram encontrados dados na aba configurada.")
        st.info("Verifique se o GID da aba (417364075) está correto e se o acesso está definido como público no Google Sheets.")

# =============================================================================
# 2. CONSULTAR OS
# =============================================================================
elif menu == "🔍 Consultar / Detalhar OS":
    st.subheader("🔍 Consultar Ordem de Serviço")
    
    if not df.empty:
        colunas = list(df.columns)
        coluna_os = next((c for c in colunas if "OS" in c.upper() or "NUMERO" in c.upper() or "Nº" in c.upper()), colunas[0])
        
        opcoes_os = df[coluna_os].dropna().astype(str).unique()
        os_escolhida = st.selectbox("Selecione o Número da OS:", opcoes_os)
        
        if os_escolhida:
            dados_os = df[df[coluna_os].astype(str) == os_escolhida]
            st.markdown("### 📄 Informações do Registro")
            st.dataframe(dados_os, use_container_width=True)
    else:
        st.warning("Sem dados disponíveis para busca.")

# =============================================================================
# 3. CADASTRAR NOVA OS
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Nova Ordem de Serviço")
    
    with st.form("form_nova_os", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_os = st.text_input("Número da OS", value=f"OS-{len(df)+1:04d}")
            cliente = st.text_input("Nome do Cliente")
            telefone = st.text_input("Telefone / WhatsApp")
            servico = st.text_area("Descrição do Serviço / Defeito")
        
        with col2:
            valor = st.number_input("Valor Total (R$)", min_value=0.0, step=10.0, format="%.2f")
            forma_pagamento = st.selectbox(
                "Forma de Pagamento",
                ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
            )
            detalhe_misto = ""
            if forma_pagamento == "Pagamento Misto":
                detalhe_misto = st.text_input("Detalhamento (Ex: R$ 50 Dinheiro + R$ 100 Pix)")
            
            status = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue"])
            data = st.date_input("Data de Entrada", datetime.now())
            
        btn_salvar = st.form_submit_button("💾 Gerar Registro de OS")
        
        if btn_salvar:
            pagto_final = detalhe_misto if forma_pagamento == "Pagamento Misto" else forma_pagamento
            st.success(f"✅ Registro gerado para a OS {num_os}!")
            st.write(f"**Cliente:** {cliente} | **Valor:** R$ {valor:.2f} | **Pagamento:** {pagto_final}")

# =============================================================================
# 4. ALTERAR OS / FORMA DE PAGAMENTO
# =============================================================================
elif menu == "✏️ Alterar OS / Pagamento":
    st.subheader("✏️ Alterar Status e Forma de Pagamento")
    
    if not df.empty:
        colunas = list(df.columns)
        coluna_os = next((c for c in colunas if "OS" in c.upper() or "NUMERO" in c.upper() or "Nº" in c.upper()), colunas[0])
        
        opcoes_os = df[coluna_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS para alterar:", opcoes_os)
        
        if os_para_editar:
            st.markdown("---")
            with st.form("form_editar_os"):
                col1, col2 = st.columns(2)
                
                with col1:
                    novo_status = st.selectbox(
                        "Alterar Status",
                        ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue", "Cancelado"]
                    )
                    nova_forma_pagto = st.selectbox(
                        "Alterar Forma de Pagamento",
                        [
                            "Pix", 
                            "Cartão de Crédito", 
                            "Cartão de Débito", 
                            "Dinheiro", 
                            "Boleto", 
                            "Misto (Dinheiro + Pix)", 
                            "Misto (Dinheiro + Cartão)", 
                            "Misto (Pix + Cartão)", 
                            "Outro / Especificar"
                        ]
                    )
                
                with col2:
                    obs_pagto = st.text_area("Detalhamento de Valores Parciais (se houver)", placeholder="Ex: R$ 100,00 Pix + R$ 50,00 Dinheiro")
                    novo_valor = st.number_input("Atualizar Valor (R$)", min_value=0.0, step=5.0, format="%.2f")

                btn_atualizar = st.form_submit_button("🔄 Atualizar OS")
                
                if btn_atualizar:
                    st.success(f"✅ Atualização registrada para a OS {os_para_editar}!")
                    st.write(f"**Novo Status:** {novo_status} | **Forma de Pagamento:** {nova_forma_pagto}")
                    if obs_pagto:
                        st.write(f"**Detalhes do Pagamento:** {obs_pagto}")
    else:
        st.warning("Nenhuma OS encontrada para alteração.")
