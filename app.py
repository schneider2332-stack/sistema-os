import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração Inicial do Painel
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

# 2. Conexão com Google Sheets (ttl=0 força a leitura instantânea de dados novos)
@st.cache_data(ttl=0)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl=0)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
            return df
        return pd.DataFrame()
    except Exception as e:
        # Fallback de leitura CSV público caso ocorra oscilação nas credenciais
        try:
            url_csv = "https://docs.google.com/spreadsheets/d/19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA/export?format=csv&gid=417364075"
            df_csv = pd.read_csv(url_csv)
            df_csv = df_csv.dropna(how='all')
            return df_csv
        except:
            return pd.DataFrame()

# Função segura para conversão monetária (Ex: R$ 500,00 -> 500.0)
def converter_para_numero(valor):
    if pd.isna(valor) or str(valor).strip() == "":
        return 0.0
    val_str = str(valor).replace('R$', '').strip()
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try:
        return float(val_str)
    except:
        return 0.0

df_os = carregar_dados()

# 3. Menu Lateral
st.sidebar.title("🛠️ Sistema OS")
menu = st.sidebar.radio(
    "Navegação",
    [
        "📈 Dashboard Financeiro",
        "📊 OS Cadastradas (Lista)",
        "🔍 Consultar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar OS / Pagamento"
    ]
)

# =============================================================================
# 1. DASHBOARD FINANCEIRO & FLUXO DE CAIXA MENSAL
# =============================================================================
if menu == "📈 Dashboard Financeiro":
    st.subheader("📈 Dashboard Executivo & Fluxo de Caixa")
    
    if not df_os.empty:
        col_valor = next((c for c in df_os.columns if "VALOR" in str(c).upper() or "TOTAL" in str(c).upper()), None)
        col_status = next((c for c in df_os.columns if "STATUS" in str(c).upper() or "SITUAÇÃO" in str(c).upper() or "SITUACAO" in str(c).upper()), None)
        col_pagto = next((c for c in df_os.columns if "PAG" in str(c).upper() or "FORMA" in str(c).upper()), None)
        col_data = next((c for c in df_os.columns if "DATA" in str(c).upper()), None)

        df_calc = df_os.copy()
        df_calc['VALOR_NUM'] = df_calc[col_valor].apply(converter_para_numero) if col_valor else 0.0

        # Totais Gerais
        total_faturado = df_calc['VALOR_NUM'].sum()
        total_qtd_os = len(df_calc)

        if col_status:
            mask_pago = df_calc[col_status].astype(str).str.upper().str.contains("CONCLUÍDO|CONCLUIDO|PAGO|ENTREGUE", na=False)
            val_recebido = df_calc[mask_pago]['VALOR_NUM'].sum()
            val_aberto = df_calc[~mask_pago]['VALOR_NUM'].sum()
        else:
            val_recebido = total_faturado
            val_aberto = 0.0

        # Métricas no Topo
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Total OS Lançadas", total_qtd_os)
        m2.metric("💵 Faturamento Total", f"R$ {total_faturado:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        m3.metric("✅ Valor Recebido", f"R$ {val_recebido:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        m4.metric("⏳ Valor em Aberto", f"R$ {val_aberto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        st.markdown("---")
        st.markdown("##### 💳 Faturamento Por Forma de Pagamento")

        if col_pagto:
            pix = df_calc[df_calc[col_pagto].astype(str).str.upper().str.contains("PIX", na=False)]['VALOR_NUM'].sum()
            cartao = df_calc[df_calc[col_pagto].astype(str).str.upper().str.contains("CARTÃO|CARTAO|CRÉDITO|DÉBITO", na=False)]['VALOR_NUM'].sum()
            dinheiro = df_calc[df_calc[col_pagto].astype(str).str.upper().str.contains("DINHEIRO|ESPÉCIE", na=False)]['VALOR_NUM'].sum()
            boleto = df_calc[df_calc[col_pagto].astype(str).str.upper().str.contains("BOLETO", na=False)]['VALOR_NUM'].sum()
        else:
            pix = cartao = dinheiro = boleto = 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📱 Pix", f"R$ {pix:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        p2.metric("💳 Cartão", f"R$ {cartao:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        p3.metric("💵 Dinheiro", f"R$ {dinheiro:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
        p4.metric("📄 Boleto", f"R$ {boleto:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))

        st.markdown("---")
        st.markdown("##### 🗓️ Fluxo de Caixa Mensal (Tabela Mês a Mês)")

        if col_data:
            df_calc['DATA_DT'] = pd.to_datetime(df_calc[col_data], errors='coerce', dayfirst=True)
            df_fluxo_dados = df_calc.dropna(subset=['DATA_DT']).copy()
            
            if not df_fluxo_dados.empty:
                df_fluxo_dados['MES_ANO'] = df_fluxo_dados['DATA_DT'].dt.strftime('%m/%Y')
                
                df_fluxo = df_fluxo_dados.groupby('MES_ANO').agg(
                    Qtd_OS=('VALOR_NUM', 'count'),
                    Faturamento=('VALOR_NUM', 'sum')
                ).reset_index()

                df_fluxo['Faturamento (R$)'] = df_fluxo['Faturamento'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                )
                df_fluxo = df_fluxo.rename(columns={'MES_ANO': 'Mês / Ano', 'Qtd_OS': 'Qtd. OS Lançadas'})
                
                st.dataframe(df_fluxo[['Mês / Ano', 'Qtd. OS Lançadas', 'Faturamento (R$)']], use_container_width=True)
            else:
                st.info("Nenhuma OS com data válida encontrada para o Fluxo Mensal.")
        else:
            st.info("Coluna de Data não identificada para o Fluxo Mensal.")
    else:
        st.warning("Nenhum dado encontrado para carregar o Dashboard.")

# =============================================================================
# 2. LISTA DE OS CADASTRADAS
# =============================================================================
elif menu == "📊 OS Cadastradas (Lista)":
    st.subheader("📋 Tabela Geral de Ordens de Serviço")
    if not df_os.empty:
        st.dataframe(df_os, use_container_width=True)
    else:
        st.warning("Nenhum registro localizado.")

# =============================================================================
# 3. CONSULTAR OS
# =============================================================================
elif menu == "🔍 Consultar OS":
    st.subheader("🔍 Consultar Detalhes da OS")
    if not df_os.empty:
        # Busca a coluna exata do ID/Número da OS evitando colunas de data
        col_os = next(
            (c for c in df_os.columns if str(c).upper().startswith("OS") or "NUMERO" in str(c).upper() or "Nº" in str(c).upper() or "CÓDIGO" in str(c).upper()), 
            df_os.columns[0]
        )
        lista_os = df_os[col_os].dropna().astype(str).unique()
        
        os_sel = st.selectbox("Selecione o Número da OS:", lista_os)
        if os_sel:
            detalhe = df_os[df_os[col_os].astype(str) == os_sel]
            st.dataframe(detalhe, use_container_width=True)

# =============================================================================
# 4. CADASTRAR NOVA OS (COM LIMPEZA AUTOMÁTICA DE CAMPOS)
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Cadastrar Nova OS")
    st.caption("Ao clicar em 'Salvar Ordem de Serviço', todos os campos serão limpos automaticamente para a próxima digitação.")

    with st.form("form_nova_os_limpo", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_os = st.text_input("Número da OS", value=f"OS-{len(df_os)+1:04d}")
            cliente = st.text_input("Nome do Cliente")
            telefone = st.text_input("Telefone / WhatsApp")
            servico = st.text_area("Descrição do Serviço")

        with col2:
            valor_input = st.text_input("Valor Total (R$)", value="0,00", help="Pode digitar 1.300,00 ou 500,00")
            forma_pagto = st.selectbox("Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
            
            val_pix = st.text_input("Valor Pix (Se misto)", value="0,00") if forma_pagto == "Pagamento Misto" else "0"
            val_cartao = st.text_input("Valor Cartão (Se misto)", value="0,00") if forma_pagto == "Pagamento Misto" else "0"
            val_dinheiro = st.text_input("Valor Dinheiro (Se misto)", value="0,00") if forma_pagto == "Pagamento Misto" else "0"

            status = st.selectbox("Status", ["Aberto", "Em Andamento", "Concluído", "Entregue"])
            data_entrada = st.date_input("Data de Entrada", datetime.now())

        btn_gravar = st.form_submit_button("💾 Salvar Ordem de Serviço")

        if btn_gravar:
            val_formatado = converter_para_numero(valor_input)
            
            if forma_pagto == "Pagamento Misto":
                detalhe_pagto = f"Misto (Pix: R$ {val_pix} | Cartão: R$ {val_cartao} | Dinheiro: R$ {val_dinheiro})"
            else:
                detalhe_pagto = forma_pagto

            nova_linha = {
                df_os.columns[0] if len(df_os.columns) > 0 else "Número da OS": num_os,
                df_os.columns[1] if len(df_os.columns) > 1 else "Data": data_entrada.strftime('%d/%m/%Y'),
                df_os.columns[2] if len(df_os.columns) > 2 else "Cliente": cliente,
                df_os.columns[3] if len(df_os.columns) > 3 else "Descrição": servico,
                df_os.columns[4] if len(df_os.columns) > 4 else "Valor Total": f"R$ {val_formatado:,.2f}".replace('.', ','),
                df_os.columns[5] if len(df_os.columns) > 5 else "Situação": status,
                df_os.columns[6] if len(df_os.columns) > 6 else "Forma de Pagamento": detalhe_pagto
            }

            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_atualizado = pd.concat([df_os, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(data=df_atualizado)
                st.cache_data.clear()
                st.success(f"✅ Ordem de Serviço {num_os} gravada com sucesso no Google Sheets!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar diretamente no Google Sheets: {e}")

# =============================================================================
# 5. ALTERAR OU EXCLUIR OS / PAGAMENTO
# =============================================================================
elif menu == "✏️ Alterar OS / Pagamento":
    st.subheader("✏️ Alterar ou Excluir Ordem de Serviço")
    
    if not df_os.empty:
        # Filtro estrito para pegar a coluna do ID da OS sem confundir com colunas de Data
        col_os = next(
            (c for c in df_os.columns if str(c).upper().startswith("OS") or "NUMERO" in str(c).upper() or "Nº" in str(c).upper() or "CÓDIGO" in str(c).upper()), 
            df_os.columns[0]
        )
        
        lista_os = df_os[col_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS para alterar ou excluir:", ["-- Selecione a OS --"] + list(lista_os))
        
        if os_para_editar != "-- Selecione a OS --":
            dados_os = df_os[df_os[col_os].astype(str) == os_para_editar].iloc[0]
            
            with st.form("form_editar_os"):
                st.markdown(f"**Editando Ordem de Serviço:** `{os_para_editar}`")
                
                col1, col2 = st.columns(2)
                with col1:
                    novo_status = st.selectbox("Novo Status", ["Aberto", "Em Andamento", "Concluído", "Entregue", "Cancelado"])
                    nova_forma = st.selectbox("Nova Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
                
                with col2:
                    col_val_nome = next((c for c in df_os.columns if "VALOR" in str(c).upper() or "TOTAL" in str(c).upper()), None)
                    val_atual = str(dados_os[col_val_nome]) if col_val_nome else "0,00"
                    novo_valor = st.text_input("Atualizar Valor Total (R$)", value=val_atual)
                
                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações na OS")
                
                if btn_salvar_alt:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        idx = df_os[df_os[col_os].astype(str) == os_para_editar].index[0]
                        
                        col_sit = next((c for c in df_os.columns if "SIT" in str(c).upper() or "STAT" in str(c).upper()), None)
                        col_pag = next((c for c in df_os.columns if "PAG" in str(c).upper() or "FORMA" in str(c).upper()), None)
                        col_val = next((c for c in df_os.columns if "VALOR" in str(c).upper() or "TOTAL" in str(c).upper()), None)
                        
                        if col_sit: df_os.at[idx, col_sit] = novo_status
                        if col_pag: df_os.at[idx, col_pag] = nova_forma
                        if col_val: df_os.at[idx, col_val] = novo_valor
                        
                        conn.update(data=df_os)
                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao alterar OS no Google Sheets: {e}")

            # -----------------------------------------------------------------
            # EXCLUSÃO DE OS
            # -----------------------------------------------------------------
            st.markdown("---")
            st.warning("⚠️ **Zona de Perigo: Exclusão de Registro**")
            
            confirmar_exclusao = st.checkbox(f"Confirmo que desejo apagar permanentemente a **{os_para_editar}**")
            
            if st.button("🗑️ Excluir esta OS", type="primary", disabled=not confirmar_exclusao):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_filtrado = df_os[df_os[col_os].astype(str) != os_para_editar]
                    
                    conn.update(data=df_filtrado)
                    st.cache_data.clear()
                    st.success(f"🗑️ Ordem de Serviço **{os_para_editar}** excluída com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir OS no Google Sheets: {e}")
