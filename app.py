import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Sistema de OS & Dashboard (Online)", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS (Nuvem)")

# ID da sua planilha extraído do seu link
SPREADSHEET_ID = "14x8Q_74Y5N12_1S5r0jXqQ5b7v8m9L0K1J2I3H4G5F"

# URL de leitura rápida e direta do Google Sheets (formato CSV)
GSHEETS_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Ordens%20de%20Servi%C3%A7o"

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # Lê os dados do Google Sheets ignorando as 3 primeiras linhas do cabeçalho
        df = pd.read_csv(GSHEETS_URL, skiprows=3)
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]
        
        colunas_texto = ['Situação', 'Cliente', 'Descrição do Serviço', 'Observações', 'Telefone', 'Cidade']
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar os dados do Google Sheets: {e}")
        st.info("💡 Verifique se a sua planilha no Google Drive está com o compartilhamento como 'Qualquer pessoa com o link'.")
        return pd.DataFrame()

df = carregar_dados()

if not df.empty:
    aba = st.sidebar.radio(
        "Navegação do Sistema", 
        ["📈 Dashboard Executivo", "🔍 Consultar / Alterar OS", "➕ Cadastrar Nova OS", "📊 Visão Geral / Lista"]
    )

    # =========================================================================
    # ABA 1: DASHBOARD EXECUTIVO
    # =========================================================================
    if aba == "📈 Dashboard Executivo":
        st.subheader("📈 Dashboard Executivo de Gestão")
        st.caption("Acompanhamento em tempo real dos indicadores da empresa")

        total_os = len(df)
        total_faturado = pd.to_numeric(df['Valor Total'], errors='coerce').sum()
        total_recebido = pd.to_numeric(df['Valor Pago'], errors='coerce').sum()
        total_em_aberto = pd.to_numeric(df['Valor Pendente'], errors='coerce').sum()
        total_clientes = df['Cliente'].replace('', pd.NA).dropna().nunique() if 'Cliente' in df.columns else 0

        st.markdown("##### 💵 Resumo Financeiro Geral")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Faturamento Total", f"R$ {total_faturado:,.2f}")
        m2.metric("Valor Recebido", f"R$ {total_recebido:,.2f}")
        m3.metric("Saldo em Aberto", f"R$ {total_em_aberto:,.2f}")
        m4.metric("Total de OS Emitidas", total_os)
        m5.metric("Total de Clientes", total_clientes)

        st.markdown("---")

        total_pix = pd.to_numeric(df.get('Pix', 0), errors='coerce').sum()
        total_cartao = pd.to_numeric(df.get('Cartão', 0), errors='coerce').sum()
        total_boleto = pd.to_numeric(df.get('Boleto', 0), errors='coerce').sum()
        total_dinheiro = pd.to_numeric(df.get('Dinheiro', 0), errors='coerce').sum()

        st.markdown("##### 💳 Recebimentos Por Forma de Pagamento")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Recebido via Pix", f"R$ {total_pix:,.2f}")
        p2.metric("Recebido via Cartão", f"R$ {total_cartao:,.2f}")
        p3.metric("Recebido via Boleto", f"R$ {total_boleto:,.2f}")
        p4.metric("Recebido em Dinheiro", f"R$ {total_dinheiro:,.2f}")

        st.markdown("---")

        col_graf, col_top = st.columns(2)
        with col_graf:
            st.markdown("##### 📌 Distribuição de OS por Situação")
            if 'Situação' in df.columns:
                df_status = df['Situação'].replace('', 'Não Informado').value_counts().reset_index()
                df_status.columns = ['Situação', 'Quantidade']
                st.bar_chart(df_status.set_index('Situação'))

        with col_top:
            st.markdown("##### 🏆 Top Clientes por Faturamento")
            if 'Cliente' in df.columns and 'Valor Total' in df.columns:
                top_clientes = df.groupby('Cliente')['Valor Total'].sum().reset_index()
                top_clientes = top_clientes[top_clientes['Cliente'] != ''].sort_values(by='Valor Total', ascending=False).head(5)
                top_clientes['Valor Total'] = top_clientes['Valor Total'].apply(lambda x: f"R$ {x:,.2f}")
                st.table(top_clientes.reset_index(drop=True))

    # =========================================================================
    # ABA 2: CONSULTAR / ALTERAR OS
    # =========================================================================
    elif aba == "🔍 Consultar / Alterar OS":
        st.subheader("📋 Consultar e Detalhar OS")

        if 'Número da OS' in df.columns:
            df_validas = df.dropna(subset=['Número da OS'])
            lista_os = df_validas['Número da OS'].astype(str).unique()
            
            if len(lista_os) > 0:
                os_selecionada = st.selectbox("Selecione o Número da OS:", lista_os)

                if os_selecionada:
                    idx = df[df['Número da OS'].astype(str) == os_selecionada].index[0]
                    dados_os = df.loc[idx]

                    st.info(f"👤 **Cliente:** {dados_os.get('Cliente', 'N/D')} | 🛠️ **Serviço:** {dados_os.get('Descrição do Serviço', 'N/D')}")

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Situação:** {dados_os.get('Situação', 'N/D')}")
                        st.write(f"**Valor Total:** R$ {pd.to_numeric(dados_os.get('Valor Total', 0), errors='coerce'):,.2f}")
                        st.write(f"**Valor Pago:** R$ {pd.to_numeric(dados_os.get('Valor Pago', 0), errors='coerce'):,.2f}")
                    with col2:
                        st.write(f"**Pix:** R$ {pd.to_numeric(dados_os.get('Pix', 0), errors='coerce'):,.2f}")
                        st.write(f"**Cartão:** R$ {pd.to_numeric(dados_os.get('Cartão', 0), errors='coerce'):,.2f}")
                        st.write(f"**Boleto:** R$ {pd.to_numeric(dados_os.get('Boleto', 0), errors='coerce'):,.2f}")
                        st.write(f"**Dinheiro:** R$ {pd.to_numeric(dados_os.get('Dinheiro', 0), errors='coerce'):,.2f}")

                    st.markdown("---")
                    st.write(f"**Observações:** {dados_os.get('Observações', '')}")

    # =========================================================================
    # ABA 3: CADASTRAR NOVA OS
    # =========================================================================
    elif aba == "➕ Cadastrar Nova OS":
        st.subheader("➕ Inserir Nova Ordem de Serviço")
        st.info("Para cadastrar ou editar registros diretamente no Google Sheets, acesse a sua planilha compartilhada no Google Drive.")

    # =========================================================================
    # ABA 4: VISÃO GERAL / LISTA COMPLETA
    # =========================================================================
    elif aba == "📊 Visão Geral / Lista":
        st.subheader("📑 Tabela Completa de Ordens de Serviço")
        st.dataframe(df, use_container_width=True)
