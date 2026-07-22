import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Sistema de OS & Dashboard", layout="wide")

st.title("🛠️ Sistema de Gestão e Dashboard de OS")

# Conexão oficial do Streamlit com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def carregar_dados():
    try:
        # Lê a aba 'Ordens de Serviço' pulando as 3 primeiras linhas de cabeçalho
        df = conn.read(worksheet="Ordens de Serviço", skiprows=3, ttl=0)
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed')]
        
        colunas_texto = ['Situação', 'Cliente', 'Descrição do Serviço', 'Observações', 'Telefone', 'Cidade']
        for col in colunas_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '')
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com a planilha do Google Sheets: {e}")
        return pd.DataFrame()

df = carregar_dados()

if df.empty:
    st.warning("⚠️ Não foi possível carregar os dados. Verifique a configuração dos Secrets ou as permissões da planilha.")
else:
    aba = st.sidebar.radio(
        "Navegação do Sistema", 
        ["📈 Dashboard Executivo", "🔍 Consultar / Alterar OS", "➕ Cadastrar Nova OS", "📊 Visão Geral / Lista"]
    )

    # =========================================================================
    # ABA 1: DASHBOARD EXECUTIVO
    # =========================================================================
    if aba == "📈 Dashboard Executivo":
        st.subheader("📈 Dashboard Executivo de Gestão")
        
        total_os = len(df)
        total_faturado = pd.to_numeric(df.get('Valor Total', 0), errors='coerce').sum()
        total_recebido = pd.to_numeric(df.get('Valor Pago', 0), errors='coerce').sum()
        total_em_aberto = pd.to_numeric(df.get('Valor Pendente', 0), errors='coerce').sum()

        st.markdown("##### 💵 Resumo Financeiro Geral")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento Total", f"R$ {total_faturado:,.2f}")
        m2.metric("Valor Recebido", f"R$ {total_recebido:,.2f}")
        m3.metric("Saldo em Aberto", f"R$ {total_em_aberto:,.2f}")
        m4.metric("Total de OS Emitidas", total_os)

        st.markdown("---")
        st.dataframe(df, use_container_width=True)

    # =========================================================================
    # ABA 2: CONSULTAR / ALTERAR OS
    # =========================================================================
    elif aba == "🔍 Consultar / Alterar OS":
        st.subheader("📋 Consultar e Alterar OS")
        
        if 'Número da OS' in df.columns:
            df_validas = df.dropna(subset=['Número da OS'])
            lista_os = df_validas['Número da OS'].astype(str).unique()
            
            os_selecionada = st.selectbox("Selecione a OS:", lista_os)
            
            if os_selecionada:
                idx = df[df['Número da OS'].astype(str) == os_selecionada].index[0]
                dados_os = df.loc[idx]

                with st.form("form_editar"):
                    nova_situacao = st.selectbox("Situação:", ["Em Aberto", "Em Andamento", "Concluída", "Cancelada"], index=0)
                    novos_obs = st.text_area("Observações:", value=str(dados_os.get('Observações', '')))
                    
                    btn_salvar = st.form_submit_button("💾 Salvar Alterações")
                    
                    if btn_salvar:
                        df.at[idx, 'Situação'] = nova_situacao
                        df.at[idx, 'Observações'] = novos_obs
                        conn.update(worksheet="Ordens de Serviço", data=df)
                        st.success(f"✅ OS Nº {os_selecionada} atualizada com sucesso na nuvem!")
                        st.rerun()

    # =========================================================================
    # ABA 3: CADASTRAR NOVA OS
    # =========================================================================
    elif aba == "➕ Cadastrar Nova OS":
        st.subheader("➕ Cadastrar Nova OS")
        
        with st.form("form_nova_os"):
            cliente = st.text_input("Cliente:")
            servico = st.text_area("Descrição do Serviço:")
            valor = st.number_input("Valor Total (R$):", value=0.0)
            
            btn_cadastrar = st.form_submit_button("➕ Salvar Nova OS")
            
            if btn_cadastrar:
                nova_linha = {
                    'Número da OS': len(df) + 1,
                    'Cliente': cliente,
                    'Descrição do Serviço': servico,
                    'Valor Total': valor,
                    'Situação': 'Em Aberto'
                }
                df_novo = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(worksheet="Ordens de Serviço", data=df_novo)
                st.success("🎉 Nova OS gravada no Google Sheets com sucesso!")
                st.rerun()

    # =========================================================================
    # ABA 4: VISÃO GERAL
    # =========================================================================
    elif aba == "📊 Visão Geral / Lista":
        st.subheader("📑 Tabela Completa")
        st.dataframe(df, use_container_width=True)
