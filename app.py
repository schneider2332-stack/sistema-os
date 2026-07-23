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

# Mapeamento dinâmico e inteligente das colunas da planilha
def identificar_colunas(df):
    cols = list(df.columns)
    c_os = next((c for c in cols if ("OS" in str(c).upper() or "NUMERO" in str(c).upper() or "Nº" in str(c).upper() or "CÓDIGO" in str(c).upper()) and "DATA" not in str(c).upper()), cols[0] if cols else "Número da OS")
    c_data = next((c for c in cols if "DATA" in str(c).upper()), None)
    c_cli = next((c for c in cols if "CLIENTE" in str(c).upper() or "NOME" in str(c).upper()), None)
    c_desc = next((c for c in cols if "DESC" in str(c).upper() or "SERVIÇO" in str(c).upper() or "SERVICO" in str(c).upper()), None)
    c_val = next((c for c in cols if "VALOR" in str(c).upper() or "TOTAL" in str(c).upper() or "PREÇO" in str(c).upper()), None)
    c_sit = next((c for c in cols if "STATUS" in str(c).upper() or "SITUAÇÃO" in str(c).upper() or "SITUACAO" in str(c).upper()), None)
    c_pag = next((c for c in cols if "PAG" in str(c).upper() or "FORMA" in str(c).upper()), None)
    c_tel = next((c for c in cols if "TEL" in str(c).upper() or "WHATS" in str(c).upper() or "FONE" in str(c).upper()), None)
    return c_os, c_data, c_cli, c_desc, c_val, c_sit, c_pag, c_tel

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
        col_os, col_data, col_cliente, col_desc, col_valor, col_status, col_pagto, col_tel = identificar_colunas(df_os)

        df_calc = df_os.copy()
        df_calc['VALOR_NUM'] = df_calc[col_valor].apply(converter_para_numero) if col_valor else 0.0

        total_faturado = df_calc['VALOR_NUM'].sum()
        total_qtd_os = len(df_calc)

        if col_status:
            mask_pago = df_calc[col_status].astype(str).str.upper().str.contains("CONCLUÍDO|CONCLUIDO|PAGO|ENTREGUE", na=False)
            val_recebido = df_calc[mask_pago]['VALOR_NUM'].sum()
            val_aberto = df_calc[~mask_pago]['VALOR_NUM'].sum()
        else:
            val_recebido = total_faturado
            val_aberto = 0.0

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
        col_os, _, _, _, _, _, _, _ = identificar_colunas(df_os)
        lista_os = df_os[col_os].dropna().astype(str).unique()
        
        os_sel = st.selectbox("Selecione o Número da OS:", lista_os)
        if os_sel:
            detalhe = df_os[df_os[col_os].astype(str) == os_sel]
            st.dataframe(detalhe, use_container_width=True)

# =============================================================================
# 4. CADASTRAR NOVA OS (COM PAGAMENTO MISTO DINÂMICO)
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Cadastrar Nova OS")
    st.caption("Preencha os dados abaixo e clique em 'Salvar Ordem de Serviço'.")

    col1, col2 = st.columns(2)
    
    with col1:
        num_os = st.text_input("Número da OS", value=f"OS-{len(df_os)+1:04d}")
        cliente = st.text_input("Nome do Cliente")
        telefone = st.text_input("Telefone / WhatsApp")
        servico = st.text_area("Descrição do Serviço")

    with col2:
        valor_input = st.text_input("Valor Total (R$)", value="0,00", help="Exemplo: 1.300,00 ou 500,00")
        
        # Seleção reativa da forma de pagamento
        forma_pagto = st.selectbox(
            "Forma de Pagamento", 
            ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
        )
        
        # Se for Misto, expande as opções automaticamente no momento da escolha
        detalhes_misto = []
        if forma_pagto == "Pagamento Misto":
            st.markdown("##### 💳 Detalhamento do Pagamento Misto")
            cm1, cm2 = st.columns(2)
            val_pix = cm1.text_input("Pix (R$)", value="0,00")
            val_dinheiro = cm2.text_input("Dinheiro (R$)", value="0,00")
            
            cm3, cm4 = st.columns(2)
            val_credito = cm3.text_input("Cartão de Crédito (R$)", value="0,00")
            val_debito = cm4.text_input("Cartão de Débito (R$)", value="0,00")
            
            val_boleto = st.text_input("Boleto (R$)", value="0,00")
            
            # Monta o texto legível apenas com os valores preenchidos
            if converter_para_numero(val_pix) > 0: detalhes_misto.append(f"Pix: R$ {val_pix}")
            if converter_para_numero(val_dinheiro) > 0: detalhes_misto.append(f"Dinheiro: R$ {val_dinheiro}")
            if converter_para_numero(val_credito) > 0: detalhes_misto.append(f"Crédito: R$ {val_credito}")
            if converter_para_numero(val_debito) > 0: detalhes_misto.append(f"Débito: R$ {val_debito}")
            if converter_para_numero(val_boleto) > 0: detalhes_misto.append(f"Boleto: R$ {val_boleto}")

        status = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Concluído", "Entregue"])
        data_entrada = st.date_input("Data de Entrada", datetime.now())

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Salvar Ordem de Serviço", type="primary", use_container_width=True):
        if not cliente.strip():
            st.warning("⚠️ Por favor, informe o Nome do Cliente antes de salvar.")
        else:
            val_formatado = converter_para_numero(valor_input)
            
            if forma_pagto == "Pagamento Misto":
                detalhe_pagto = "Misto (" + " | ".join(detalhes_misto) + ")" if detalhes_misto else "Pagamento Misto"
            else:
                detalhe_pagto = forma_pagto

            c_os, c_data, c_cli, c_desc, c_val, c_sit, c_pag, c_tel = identificar_colunas(df_os)
            
            nova_linha = {col: "" for col in df_os.columns}
            if c_os: nova_linha[c_os] = str(num_os).strip()
            if c_data: nova_linha[c_data] = data_entrada.strftime('%d/%m/%Y')
            if c_cli: nova_linha[c_cli] = cliente
            if c_desc: nova_linha[c_desc] = servico
            if c_val: nova_linha[c_val] = f"R$ {val_formatado:,.2f}".replace('.', ',')
            if c_sit: nova_linha[c_sit] = str(status).strip()
            if c_pag: nova_linha[c_pag] = detalhe_pagto
            if c_tel: nova_linha[c_tel] = telefone

            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_atualizado = pd.concat([df_os, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(data=df_atualizado)
                st.cache_data.clear()
                st.success(f"✅ Ordem de Serviço {num_os} gravada com sucesso com status **{status}**!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar no Google Sheets: {e}")

# =============================================================================
# 5. ALTERAR OU EXCLUIR OS / PAGAMENTO
# =============================================================================
elif menu == "✏️ Alterar OS / Pagamento":
    st.subheader("✏️ Alterar ou Excluir Ordem de Serviço")
    
    if not df_os.empty:
        col_os, col_data, col_cli, col_desc, col_val, col_sit, col_pag, col_tel = identificar_colunas(df_os)
        
        lista_os = df_os[col_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS para alterar ou excluir:", ["-- Selecione a OS --"] + list(lista_os))
        
        if os_para_editar != "-- Selecione a OS --":
            dados_os = df_os[df_os[col_os].astype(str) == os_para_editar].iloc[0]
            
            status_atual = str(dados_os.get(col_sit, "Aberto")).strip()
            opcoes_status = ["Aberto", "Em Andamento", "Concluído", "Entregue", "Cancelado"]
            idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0

            with st.form("form_editar_os"):
                st.markdown(f"**Editando Ordem de Serviço:** `{os_para_editar}`")
                
                col1, col2 = st.columns(2)
                with col1:
                    novo_status = st.selectbox("Novo Status", opcoes_status, index=idx_status)
                    nova_forma = st.selectbox("Nova Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
                
                with col2:
                    val_atual = str(dados_os[col_val]) if col_val and col_val in dados_os else "0,00"
                    novo_valor = st.text_input("Atualizar Valor Total (R$)", value=val_atual)
                
                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações na OS")
                
                if btn_salvar_alt:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        idx = df_os[df_os[col_os].astype(str) == os_para_editar].index[0]
                        
                        if col_sit: df_os.at[idx, col_sit] = str(novo_status).strip()
                        if col_pag: df_os.at[idx, col_pag] = nova_forma
                        if col_val: df_os.at[idx, col_val] = novo_valor
                        
                        conn.update(data=df_os)
                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada para **{novo_status}** com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao alterar OS no Google Sheets: {e}")

            # -----------------------------------------------------------------
            # ZONA DE PERIGO: EXCLUSÃO DE OS
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
