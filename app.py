import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Sistema de OS & Dashboard (Online)", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS (Nuvem)")

# URL pública da sua planilha do Google Sheets (exportada em formato CSV para leitura direta e ágil)
# Substitua o ID abaixo caso utilize outra planilha no futuro
SPREADSHEET_ID = "14x8Q_74Y5N12_1S5r0jXqQ5b7v8m9L0K1J2I3H4G5F" # Pode manter ou colar a URL completa no secrets
GSHEETS_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Ordens%20de%20Servi%C3%A7o"

# Função para carregar os dados diretamente do Google Sheets
@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # Tenta buscar a URL configurada nos secrets, caso contrário usa a URL direta
        try:
            url_planilha = st.secrets["connections"]["gsheets"]["spreadsheet"]
            if "/edit" in url_planilha:
                url_csv = url_planilha.replace("/edit?usp=sharing", "/gviz/tq?tqx=out:csv&sheet=Ordens%20de%20Servi%C3%A7o").replace("/edit", "/gviz/tq?tqx=out:csv&sheet=Ordens%20de%20Servi%C3%A7o")
            else:
                url_csv = url_planilha
        except:
            url_csv = GSHEETS_URL

        # Lê os dados pulando os cabeçalhos das primeiras 3 linhas
        df = pd.read_csv(url_csv, skiprows=3)
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]
        
        colunas_texto = ['Situação', 'Cliente', 'Descrição do Serviço', 'Observações', 'Telefone', 'Cidade']
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '')
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        st.info("💡 Certifique-se de que a planilha no Google Drive está compartilhada como 'Qualquer pessoa com o link'.")
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
        st.subheader("📋 Consultar e Atualizar OS")

        if 'Número da OS' in df.columns:
            df_validas = df.dropna(subset=['Número da OS'])
            lista_os = df_validas['Número da OS'].astype(str).unique()
            
            if len(lista_os) > 0:
                os_selecionada = st.selectbox("Selecione o Número da OS:", lista_os)

                if os_selecionada:
                    idx = df[df['Número da OS'].astype(str) == os_selecionada].index[0]
                    dados_os = df.loc[idx]

                    st.info(f"👤 **Cliente:** {dados_os.get('Cliente', 'N/D')} | 🛠️ **Serviço:** {dados_os.get('Descrição do Serviço', 'N/D')}")

                    with st.form("form_alteracao"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("##### 📌 Dados do Serviço e Situação")
                            situacao_atual = str(dados_os.get('Situação', 'Em Aberto'))
                            opcoes_situacao = ["Em Aberto", "Em Andamento", "Aguardando Pagamento", "Pendente", "Concluída", "Cancelada"]
                            index_padrao = opcoes_situacao.index(situacao_atual) if situacao_atual in opcoes_situacao else 0
                            nova_situacao = st.selectbox("Situação da OS:", opcoes_situacao, index=index_padrao)
                            
                            val_tot = pd.to_numeric(dados_os.get('Valor Total', 0.0), errors='coerce')
                            novo_valor_total = st.number_input("Valor Total (R$):", value=float(0.0 if pd.isna(val_tot) else val_tot))
                            
                            val_pag = pd.to_numeric(dados_os.get('Valor Pago', 0.0), errors='coerce')
                            novo_valor_pago = st.number_input("Valor Pago Total (R$):", value=float(0.0 if pd.isna(val_pag) else val_pag))

                        with col2:
                            st.markdown("##### 💳 Formas de Pagamento")
                            pix = st.number_input("Pago via Pix (R$):", value=float(pd.to_numeric(dados_os.get('Pix', 0.0), errors='coerce') or 0.0))
                            cartao = st.number_input("Pago via Cartão (R$):", value=float(pd.to_numeric(dados_os.get('Cartão', 0.0), errors='coerce') or 0.0))
                            boleto = st.number_input("Pago via Boleto (R$):", value=float(pd.to_numeric(dados_os.get('Boleto', 0.0), errors='coerce') or 0.0))
                            dinheiro = st.number_input("Pago em Dinheiro (R$):", value=float(pd.to_numeric(dados_os.get('Dinheiro', 0.0), errors='coerce') or 0.0))

                        st.markdown("---")
                        novas_obs = st.text_area("Observações:", value=str(dados_os.get('Observações', '')))

                        btn_salvar = st.form_submit_button("💾 Salvar Alterações na Nuvem")

                        if btn_salvar:
                            st.info("Para salvar alterações permanentemente no Google Sheets online, você pode editar diretamente a linha correspondente na sua planilha no Google Drive.")

    # =========================================================================
    # ABA 3: CADASTRAR NOVA OS
    # =========================================================================
    elif aba == "➕ Cadastrar Nova OS":
        st.subheader("➕ Inserir Nova Ordem de Serviço")

        try:
            proxima_os = int(pd.to_numeric(df['Número da OS'], errors='coerce').max() + 1)
        except:
            proxima_os = 1001

        with st.form("form_nova_os"):
            c1, c2 = st.columns(2)

            with c1:
                st.markdown("##### 👤 Informações do Cliente e OS")
                num_os = st.number_input("Número da OS:", value=proxima_os, step=1)
                data_os = st.date_input("Data:", value=date.today())
                cliente = st.text_input("Nome do Cliente:")
                telefone = st.text_input("Telefone:")
                cidade = st.text_input("Cidade:", value="Florianópolis")
                descricao = st.text_area("Descrição do Serviço:")

            with c2:
                st.markdown("##### 💰 Valores e Forma de Pagamento")
                valor_total = st.number_input("Valor Total do Serviço (R$):", value=0.0)
                situacao_inicial = st.selectbox("Situação Inicial:", ["Em Aberto", "Em Andamento", "Aguardando Pagamento", "Concluída"])
                
                st.markdown("**Valores Recebidos (se houver pagamento no ato):**")
                pix = st.number_input("Pix (R$):", value=0.0)
                cartao = st.number_input("Cartão (R$):", value=0.0)
                boleto = st.number_input("Boleto (R$):", value=0.0)
                dinheiro = st.number_input("Dinheiro (R$):", value=0.0)

            obs = st.text_area("Observações da OS:")

            btn_cadastrar = st.form_submit_button("➕ Salvar Nova OS na Nuvem")

            if btn_cadastrar:
                st.info("Para adicionar novas OS diretamente, insira os dados na última linha disponível da sua planilha no Google Sheets.")

    # =========================================================================
    # ABA 4: VISÃO GERAL / LISTA COMPLETA
    # =========================================================================
    elif aba == "📊 Visão Geral / Lista":
        st.subheader("📑 Tabela Completa de Ordens de Serviço")
        st.dataframe(df, use_container_width=True)
