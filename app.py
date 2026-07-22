import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sistema de Gestão de OS & Fluxo de Caixa", layout="wide")

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
        df_raw = pd.read_csv(URL_CSV, header=None)
        
        if df_raw.empty:
            return pd.DataFrame()
        
        # Localiza dinamicamente a linha de cabeçalho real
        linha_cabecalho = 0
        for idx, row in df_raw.iterrows():
            valores = [str(v).upper().strip() for v in row.values if pd.notna(v)]
            if any("OS" in item or "CLIENTE" in item or "SERVIÇO" in item or "VALOR" in item for item in valores):
                linha_cabecalho = idx
                break
        
        df = df_raw.iloc[linha_cabecalho + 1:].copy()
        df.columns = [str(v).strip() for v in df_raw.iloc[linha_cabecalho].values]
        
        df = df.dropna(how='all')
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.reset_index(drop=True)
        
        return df
    except Exception as e:
        st.error(f"Erro ao acessar e processar a planilha do Google Sheets: {e}")
        return pd.DataFrame()

df = carregar_dados()

def converter_para_numero(valor):
    if pd.isna(valor):
        return 0.0
    val_str = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        return float(val_str)
    except:
        return 0.0

# =============================================================================
# MENU LATERAL DE NAVEGAÇÃO
# =============================================================================
menu = st.sidebar.radio(
    "📌 Navegação do Sistema",
    [
        "📈 Dashboard Financeiro & Fluxo de Caixa",
        "📊 OS Cadastradas (Lista)",
        "🔍 Consultar / Detalhar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar OS / Pagamento"
    ]
)

# =============================================================================
# 1. DASHBOARD FINANCEIRO E FLUXO DE CAIXA MENSAL
# =============================================================================
if menu == "📈 Dashboard Financeiro & Fluxo de Caixa":
    st.subheader("📈 Painel de Indicadores & Fluxo de Caixa Mensal")
    
    if not df.empty:
        # Mapeamento flexível de colunas
        col_valor = next((c for c in df.columns if any(p in c.upper() for p in ["VALOR", "TOTAL", "PREÇO", "PRECO"])), None)
        col_status = next((c for c in df.columns if any(p in c.upper() for p in ["STATUS", "SITUAÇÃO", "SITUACAO"])), None)
        col_pagto = next((c for c in df.columns if any(p in c.upper() for p in ["PAG", "FORMA"])), None)
        col_data = next((c for c in df.columns if "DATA" in c.upper()), None)
        
        if col_valor:
            df['VALOR_CALC'] = df[col_valor].apply(converter_para_numero)
        else:
            df['VALOR_CALC'] = 0.0
            
        if col_data:
            df['DATA_DT'] = pd.to_datetime(df[col_data], errors='coerce', dayfirst=True)
            df['ANO_MES'] = df['DATA_DT'].dt.strftime('%Y-%m').fillna("Sem Data")
        else:
            df['ANO_MES'] = "Sem Data"

        meses_unicos = sorted([m for m in df['ANO_MES'].dropna().unique() if m != "Sem Data"], reverse=True)
        if meses_unicos:
            st.sidebar.subheader("📅 Filtro de Período")
            meses_selecionados = st.sidebar.multiselect("Filtrar por Mês/Ano:", options=meses_unicos, default=meses_unicos)
            if meses_selecionados:
                df_filtered = df[df['ANO_MES'].isin(meses_selecionados)]
            else:
                df_filtered = df.copy()
        else:
            df_filtered = df.copy()

        fat_total = df_filtered['VALOR_CALC'].sum()
        
        if col_status:
            status_concluido = df_filtered[col_status].astype(str).str.upper().str.contains("PAGO|CONCLUÍDO|CONCLUIDO|ENTREGUE|FINALIZADO", na=False)
            val_recebido = df_filtered[status_concluido]['VALOR_CALC'].sum()
            val_aberto = df_filtered[~status_concluido]['VALOR_CALC'].sum()
        else:
            val_recebido = fat_total
            val_aberto = 0.0

        # CARDS MÉTRICOS
        m1, m2, m3 = st.columns(3)
        m1.metric("💵 Faturamento Total", f"R$ {fat_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        m2.metric("✅ Valor Recebido", f"R$ {val_recebido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        m3.metric("⏳ Valor em Aberto", f"R$ {val_aberto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        st.markdown("---")
        st.markdown("### 💳 Faturamento Por Forma de Pagamento")
        
        if col_pagto:
            pix_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("PIX", na=False)]['VALOR_CALC'].sum()
            cartao_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("CARTÃO|CARTAO|CRÉDITO|DÉBITO", na=False)]['VALOR_CALC'].sum()
            dinheiro_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("DINHEIRO|ESPÉCIE", na=False)]['VALOR_CALC'].sum()
            boleto_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("BOLETO", na=False)]['VALOR_CALC'].sum()
        else:
            pix_val = cartao_val = dinheiro_val = boleto_val = 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📱 Pix", f"R$ {pix_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        p2.metric("💳 Cartão", f"R$ {cartao_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        p3.metric("💵 Dinheiro", f"R$ {dinheiro_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        p4.metric("📄 Boleto", f"R$ {boleto_val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        
        st.markdown("---")
        
        # GRÁFICO E TABELA DE FLUXO DE CAIXA MENSAL
        st.markdown("### 🗓️ Fluxo de Caixa Mensal (Evolução por Mês)")
        df_fluxo = df[df['ANO_MES'] != "Sem Data"].groupby('ANO_MES')['VALOR_CALC'].sum().reset_index()
        df_fluxo.columns = ['Mês/Ano', 'Faturamento (R$)']
        
        if not df_fluxo.empty:
            st.bar_chart(df_fluxo.set_index('Mês/Ano'))
            st.markdown("#### 📑 Resumo Mensal Detalhado")
            st.dataframe(df_fluxo, use_container_width=True)
        else:
            st.info("💡 Insira datas no formato DD/MM/AAAA na sua planilha para ver o gráfico de evolução mensal.")
            
    else:
        st.warning("⚠️ Nenhum dado foi retornado para construir o Dashboard.")

# =============================================================================
# 2. OS CADASTRADAS (LISTA COMPLETA)
# =============================================================================
elif menu == "📊 OS Cadastradas (Lista)":
    st.subheader("📋 Tabela Geral de Ordens de Serviço")
    
    if not df.empty:
        st.metric("Total de OSs Registradas", len(df))
        st.markdown("---")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠️ Não foram encontrados dados na aba da planilha.")

# =============================================================================
# 3. CONSULTAR OS
# =============================================================================
elif menu == "🔍 Consultar / Detalhar OS":
    st.subheader("🔍 Consultar Ordem de Serviço")
    
    if not df.empty:
        colunas = list(df.columns)
        coluna_os = next((c for c in colunas if "OS" in c.upper() or "NUMERO" in c.upper() or "Nº" in c.upper()), colunas[0])
        
        opcoes_os = df[coluna_os].dropna().astype(str).unique()
        os_escolhida = st.selectbox("Selecione a OS que deseja visualizar:", opcoes_os)
        
        if os_escolhida:
            dados = df[df[coluna_os].astype(str) == os_escolhida]
            st.markdown("### 📄 Informações do Registro")
            st.dataframe(dados, use_container_width=True)
    else:
        st.warning("Sem dados disponíveis para busca.")

# =============================================================================
# 4. CADASTRAR NOVA OS
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Nova OS")
    
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
                detalhe_misto = st.text_input("Detalhamento do Pagamento (Ex: R$ 50 Dinheiro + R$ 100 Pix)")
            
            status = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue"])
            data = st.date_input("Data de Entrada", datetime.now())
            
        btn_salvar = st.form_submit_button("💾 Gerar Registro de OS")
        
        if btn_salvar:
            pagto_final = detalhe_misto if forma_pagamento == "Pagamento Misto" else forma_pagamento
            st.success(f"✅ Registro gerado para a OS {num_os}!")
            st.write(f"**Cliente:** {cliente} | **Valor:** R$ {valor:.2f} | **Pagamento:** {pagto_final}")

# =============================================================================
# 5. ALTERAR OS / FORMA DE PAGAMENTO
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
                    obs_pagto = st.text_area("Detalhamento de Valores Parciais", placeholder="Ex: R$ 100,00 Pix + R$ 50,00 Dinheiro")
                    novo_valor = st.number_input("Atualizar Valor (R$)", min_value=0.0, step=5.0, format="%.2f")

                btn_atualizar = st.form_submit_button("🔄 Atualizar OS")
                
                if btn_atualizar:
                    st.success(f"✅ Atualização registrada para a OS {os_para_editar}!")
                    st.write(f"**Novo Status:** {novo_status} | **Forma de Pagamento:** {nova_forma_pagto}")
                    if obs_pagto:
                        st.write(f"**Detalhes do Pagamento:** {obs_pagto}")
    else:
        st.warning("Nenhuma OS disponível para alteração.")
