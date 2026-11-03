import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL E CONEXÃO
# =============================================================================
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

NOME_ABA = "Ordens de Serviço"

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Lê a partir da linha 4 (onde ficam os cabeçalhos na folha)
        df = conn.read(worksheet=NOME_ABA, header=3, ttl=0)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
            return df
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def formatar_moeda_br(valor_float):
    return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

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
    except Exception:
        return 0.0

df_os = carregar_dados()

def identificar_colunas(df):
    cols = list(df.columns)
    
    c_os = next((c for c in cols if "NÚMERO" in str(c).upper() or "OS" in str(c).upper()), cols[0] if cols else None)
    
    # Data de Emissão (evitando capturar Data do Pagamento)
    c_data = next((c for c in cols if str(c).strip().upper() == "DATA"), None)
    if not c_data:
        c_data = next((c for c in cols if "DATA" in str(c).upper() and "PAG" not in str(c).upper()), None)
        
    c_cli = next((c for c in cols if "CLIENTE" in str(c).upper() or "NOME" in str(c).upper()), None)
    c_desc = next((c for c in cols if "DESC" in str(c).upper() or "SERVI" in str(c).upper()), None)
    
    # Valores
    c_val_tot = next((c for c in cols if "VALOR TOT" in str(c).upper() or str(c).strip().upper() == "VALOR"), None)
    c_val_pago = next((c for c in cols if "VALOR PAG" in str(c).upper() or "PAGO" in str(c).upper()), None)
    c_val_pend = next((c for c in cols if "PEND" in str(c).upper() or "ABERTO" in str(c).upper()), None)
    
    c_sit = next((c for c in cols if "SITUA" in str(c).upper() or "STATUS" in str(c).upper()), None)
    c_pag = next((c for c in cols if "FORMA" in str(c).upper()), None)
    c_tel = next((c for c in cols if "TEL" in str(c).upper() or "WHATS" in str(c).upper() or "FONE" in str(c).upper()), None)
    
    return c_os, c_data, c_cli, c_desc, c_val_tot, c_val_pago, c_val_pend, c_sit, c_pag, c_tel

# =============================================================================
# 2. MENU LATERAL
# =============================================================================
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
        col_os, col_data, col_cliente, col_desc, col_total, col_pago, col_pend, col_status, col_pagto, col_tel = identificar_colunas(df_os)

        df_calc = df_os.copy()
        
        df_calc['VALOR_TOTAL_NUM'] = df_calc[col_total].apply(converter_para_numero) if col_total else 0.0
        df_calc['VALOR_PAGO_NUM'] = df_calc[col_pago].apply(converter_para_numero) if col_pago else 0.0
        df_calc['VALOR_PEND_NUM'] = df_calc[col_pend].apply(converter_para_numero) if col_pend else (df_calc['VALOR_TOTAL_NUM'] - df_calc['VALOR_PAGO_NUM'])

        if not col_pago and col_status:
            mask_pago = df_calc[col_status].astype(str).str.upper().str.contains("CONCLUÍDO|CONCLUIDO|PAGO|ENTREGUE|PAGA", na=False)
            df_calc['VALOR_PAGO_NUM'] = df_calc['VALOR_TOTAL_NUM'].where(mask_pago, 0.0)
            df_calc['VALOR_PEND_NUM'] = df_calc['VALOR_TOTAL_NUM'].where(~mask_pago, 0.0)

        # Parsing de data sem trocar dia por mês
        if col_data:
            df_calc['DATA_DT'] = pd.to_datetime(df_calc[col_data], errors='coerce', format='mixed')
            df_calc['MES_ANO'] = df_calc['DATA_DT'].dt.strftime('%m/%Y')
            
            meses_disponiveis = [m for m in df_calc['MES_ANO'].dropna().unique() if str(m).strip() != ""]
            try:
                meses_disponiveis.sort(key=lambda x: datetime.strptime(x, '%m/%Y'), reverse=True)
            except Exception:
                meses_disponiveis.sort(reverse=True)
            
            opcoes_mes = ["📅 Todos os Meses (Geral)"] + meses_disponiveis
        else:
            opcoes_mes = ["📅 Todos os Meses (Geral)"]

        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            mes_selecionado = st.selectbox("📆 **Filtrar Período do Dashboard:**", opcoes_mes)

        if mes_selecionado != "📅 Todos os Meses (Geral)" and col_data:
            df_filtrado = df_calc[df_calc['MES_ANO'] == mes_selecionado].copy()
            st.caption(f"Exibindo dados consolidados referentes a **{mes_selecionado}**")
        else:
            df_filtrado = df_calc.copy()
            st.caption("Exibindo dados acumulados de **todo o período**")

        st.markdown("<br>", unsafe_allow_html=True)

        total_faturado = df_filtrado['VALOR_TOTAL_NUM'].sum()
        val_recebido = df_filtrado['VALOR_PAGO_NUM'].sum()
        val_aberto = df_filtrado['VALOR_PEND_NUM'].sum()
        total_qtd_os = len(df_filtrado)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Total OS Lançadas", total_qtd_os)
        m2.metric("💵 Faturamento Total", formatar_moeda_br(total_faturado))
        m3.metric("✅ Valor Recebido", formatar_moeda_br(val_recebido))
        m4.metric("⏳ Valor em Aberto", formatar_moeda_br(val_aberto))

        st.markdown("---")
        label_periodo_pagto = "Geral" if mes_selecionado == "📅 Todos os Meses (Geral)" else mes_selecionado
        st.markdown(f"##### 💳 Faturamento Por Forma de Pagamento ({label_periodo_pagto})")

        # Localização de colunas específicas de pagamento
        col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
        col_cred = next((c for c in df_os.columns if "CRÉD" in str(c).upper() or "CRED" in str(c).upper()), None)
        col_deb = next((c for c in df_os.columns if "DÉB" in str(c).upper() or "DEB" in str(c).upper()), None)
        col_cartao_geral = next((c for c in df_os.columns if "CART" in str(c).upper() and not col_cred and not col_deb), None)
        col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
        col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

        pix = credito = debito = dinheiro = boleto = 0.0

        if col_pix:
            pix = df_filtrado[col_pix].apply(converter_para_numero).sum()
        elif col_pagto:
            pix = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("PIX", na=False)]['VALOR_TOTAL_NUM'].sum()

        if col_cred:
            credito = df_filtrado[col_cred].apply(converter_para_numero).sum()
        elif col_pagto:
            credito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("CRÉDITO|CREDITO", na=False)]['VALOR_TOTAL_NUM'].sum()

        if col_deb:
            debito = df_filtrado[col_deb].apply(converter_para_numero).sum()
        elif col_pagto:
            debito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("DÉBITO|DEBITO", na=False)]['VALOR_TOTAL_NUM'].sum()

        # Se houver coluna de Cartão geral mas sem separação no cabeçalho
        if col_cartao_geral and not col_cred and not col_deb:
            if col_pagto:
                credito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("CRÉDITO|CREDITO", na=False)]['VALOR_TOTAL_NUM'].sum()
                debito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("DÉBITO|DEBITO", na=False)]['VALOR_TOTAL_NUM'].sum()
            else:
                credito = df_filtrado[col_cartao_geral].apply(converter_para_numero).sum()

        if col_dinheiro:
            dinheiro = df_filtrado[col_dinheiro].apply(converter_para_numero).sum()
        elif col_pagto:
            dinheiro = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("DINHEIRO|ESPÉCIE", na=False)]['VALOR_TOTAL_NUM'].sum()

        if col_boleto:
            boleto = df_filtrado[col_boleto].apply(converter_para_numero).sum()
        elif col_pagto:
            boleto = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("BOLETO", na=False)]['VALOR_TOTAL_NUM'].sum()

        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("📱 Pix", formatar_moeda_br(pix))
        p2.metric("💳 Cartão de Crédito", formatar_moeda_br(credito))
        p3.metric("💳 Cartão de Débito", formatar_moeda_br(debito))
        p4.metric("💵 Dinheiro", formatar_moeda_br(dinheiro))
        p5.metric("📄 Boleto", formatar_moeda_br(boleto))

        st.markdown("---")
        st.markdown("##### 🗓️ Resumo Comparativo Mês a Mês")

        if col_data:
            df_fluxo_dados = df_calc.dropna(subset=['DATA_DT']).copy()
            if not df_fluxo_dados.empty:
                df_fluxo = df_fluxo_dados.groupby('MES_ANO').agg(
                    Qtd_OS=('VALOR_TOTAL_NUM', 'count'),
                    Faturamento=('VALOR_TOTAL_NUM', 'sum'),
                    Recebido=('VALOR_PAGO_NUM', 'sum'),
                    Aberto=('VALOR_PEND_NUM', 'sum')
                ).reset_index()

                try:
                    df_fluxo['ORDEM_DT'] = pd.to_datetime(df_fluxo['MES_ANO'], format='%m/%Y')
                    df_fluxo = df_fluxo.sort_values('ORDEM_DT', ascending=False).drop(columns=['ORDEM_DT'])
                except Exception:
                    pass

                df_fluxo['Faturamento (R$)'] = df_fluxo['Faturamento'].apply(formatar_moeda_br)
                df_fluxo['Recebido (R$)'] = df_fluxo['Recebido'].apply(formatar_moeda_br)
                df_fluxo['Em Aberto (R$)'] = df_fluxo['Aberto'].apply(formatar_moeda_br)

                df_fluxo = df_fluxo.rename(columns={'MES_ANO': 'Mês / Ano', 'Qtd_OS': 'Qtd. OS Lançadas'})
                st.dataframe(df_fluxo[['Mês / Ano', 'Qtd. OS Lançadas', 'Faturamento (R$)', 'Recebido (R$)', 'Em Aberto (R$)']], use_container_width=True)
            else:
                st.info("Nenhuma OS com data válida encontrada.")
    else:
        st.info("Nenhuma OS cadastrada ainda. Cadastre a sua primeira Ordem de Serviço pelo menu lateral.")

# =============================================================================
# 2. LISTA DE OS CADASTRADAS
# =============================================================================
elif menu == "📊 OS Cadastradas (Lista)":
    st.subheader("📋 Tabela Geral de Ordens de Serviço")
    if not df_os.empty:
        st.dataframe(df_os, use_container_width=True)
    else:
        st.info("Nenhum registro localizado.")

# =============================================================================
# 3. CONSULTAR OS
# =============================================================================
elif menu == "🔍 Consultar OS":
    st.subheader("🔍 Consultar Detalhes da OS")
    if not df_os.empty:
        col_os, _, _, _, _, _, _, _, _, _ = identificar_colunas(df_os)
        lista_os = df_os[col_os].dropna().astype(str).unique()
        os_sel = st.selectbox("Selecione o Número da OS:", lista_os)
        if os_sel:
            detalhe = df_os[df_os[col_os].astype(str) == os_sel]
            st.dataframe(detalhe, use_container_width=True)
    else:
        st.info("Nenhuma OS cadastrada para consulta.")

# =============================================================================
# 4. CADASTRAR NOVA OS
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Cadastrar Nova OS")
    st.caption("Preencha os dados abaixo e clique em 'Salvar Ordem de Serviço'.")

    # Próximo número sequencial
    proximo_num = (len(df_os) + 1001) if not df_os.empty else 1001

    col1, col2 = st.columns(2)
    with col1:
        num_os = st.text_input("Número da OS", value=str(proximo_num))
        cliente = st.text_input("Nome do Cliente")
        telefone = st.text_input("Telefone / WhatsApp")
        servico = st.text_area("Descrição do Serviço")

    with col2:
        valor_input = st.text_input("Valor Total (R$)", value="0,00")
        forma_pagto = st.selectbox(
            "Forma de Pagamento", 
            ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
        )
        status = st.selectbox("Situação Inicial", ["Paga", "Em Aberto", "Parcial"])
        data_entrada = st.date_input("Data de Entrada", datetime.now())

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Salvar Ordem de Serviço", type="primary", use_container_width=True):
        if not cliente.strip():
            st.warning("⚠️ Por favor, informe o Nome do Cliente antes de salvar.")
        else:
            val_formatado = converter_para_numero(valor_input)
            col_os, col_data, col_cli, col_desc, col_total, col_pago, col_pend, col_sit, col_pag, col_tel = identificar_colunas(df_os)

            nova_linha = {col: "" for col in df_os.columns}
            if col_os: nova_linha[col_os] = str(num_os).strip()
            if col_data: nova_linha[c_data] = data_entrada.strftime('%Y-%m-%d')
            if col_cli: nova_linha[col_cli] = cliente
            if col_desc: nova_linha[col_desc] = servico
            if col_total: nova_linha[col_total] = val_formatado
            
            if status == "Paga":
                if col_pago: nova_linha[col_pago] = val_formatado
                if col_pend: nova_linha[col_pend] = 0.0
            else:
                if col_pago: nova_linha[col_pago] = 0.0
                if col_pend: nova_linha[col_pend] = val_formatado

            if col_sit: nova_linha[col_sit] = str(status).strip()
            if col_pag: nova_linha[col_pag] = forma_pagto
            if col_tel: nova_linha[col_tel] = telefone

            # Distribuição nas colunas auxiliares se existirem
            col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
            col_cred = next((c for c in df_os.columns if "CRÉD" in str(c).upper() or "CRED" in str(c).upper()), None)
            col_deb = next((c for c in df_os.columns if "DÉB" in str(c).upper() or "DEB" in str(c).upper()), None)
            col_cartao_geral = next((c for c in df_os.columns if "CART" in str(c).upper() and not col_cred and not col_deb), None)
            col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
            col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

            if "PIX" in forma_pagto.upper() and col_pix:
                nova_linha[col_pix] = val_formatado
            elif "CRÉDITO" in forma_pagto.upper() or "CREDITO" in forma_pagto.upper():
                if col_cred:
                    nova_linha[col_cred] = val_formatado
                elif col_cartao_geral:
                    nova_linha[col_cartao_geral] = val_formatado
            elif "DÉBITO" in forma_pagto.upper() or "DEBITO" in forma_pagto.upper():
                if col_deb:
                    nova_linha[col_deb] = val_formatado
                elif col_cartao_geral:
                    nova_linha[col_cartao_geral] = val_formatado
            elif "BOLETO" in forma_pagto.upper() and col_boleto:
                nova_linha[col_boleto] = val_formatado
            elif "DINHEIRO" in forma_pagto.upper() and col_dinheiro:
                nova_linha[col_dinheiro] = val_formatado

            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                client = getattr(conn, "_instance", None) or getattr(conn, "client", None)
                if client is None and hasattr(conn, "_connect"):
                    client = conn._connect()

                spreadsheet_url = st.secrets.connections.gsheets.spreadsheet
                sh = client.open_by_url(spreadsheet_url)
                ws = sh.worksheet(NOME_ABA)

                valores_linha = [nova_linha.get(col, "") for col in df_os.columns]
                ws.append_row(valores_linha)

                st.cache_data.clear()
                st.success(f"✅ Ordem de Serviço {num_os} gravada com sucesso com pagamento via **{forma_pagto}**!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar no Google Sheets: {e}")

# =============================================================================
# 5. ALTERAR OU EXCLUIR OS / PAGAMENTO
# =============================================================================
elif menu == "✏️ Alterar OS / Pagamento":
    st.subheader("✏️ Alterar ou Excluir Ordem de Serviço")
    if not df_os.empty:
        col_os, col_data, col_cli, col_desc, col_total, col_pago, col_pend, col_sit, col_pag, col_tel = identificar_colunas(df_os)
        lista_os = df_os[col_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS:", ["-- Selecione a OS --"] + list(lista_os))

        if os_para_editar != "-- Selecione a OS --":
            dados_os = df_os[df_os[col_os].astype(str) == os_para_editar].iloc[0]
            status_atual = str(dados_os.get(col_sit, "Em Aberto")).strip()
            opcoes_status = ["Paga", "Em Aberto", "Parcial"]
            idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0

            with st.form("form_editar_os"):
                st.markdown(f"**Editando Ordem de Serviço:** `{os_para_editar}`")
                c1, c2 = st.columns(2)
                with c1:
                    novo_status = st.selectbox("Novo Status", opcoes_status, index=idx_status)
                    nova_forma = st.selectbox(
                        "Nova Forma de Pagamento", 
                        ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
                    )
                with c2:
                    val_atual = str(dados_os[col_total]) if col_total and col_total in dados_os else "0,00"
                    novo_valor = st.text_input("Atualizar Valor Total (R$)", value=val_atual)

                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações na OS")
                if btn_salvar_alt:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        client = getattr(conn, "_instance", None) or getattr(conn, "client", None)
                        if client is None and hasattr(conn, "_connect"):
                            client = conn._connect()

                        spreadsheet_url = st.secrets.connections.gsheets.spreadsheet
                        sh = client.open_by_url(spreadsheet_url)
                        ws = sh.worksheet(NOME_ABA)

                        idx_relativo = df_os[df_os[col_os].astype(str) == os_para_editar].index[0]
                        linha_planilha = idx_relativo + 5

                        val_num = converter_para_numero(novo_valor)

                        if col_sit:
                            col_idx_sit = list(df_os.columns).index(col_sit) + 1
                            ws.update_cell(linha_planilha, col_idx_sit, str(novo_status).strip())
                        if col_pag:
                            col_idx_pag = list(df_os.columns).index(col_pag) + 1
                            ws.update_cell(linha_planilha, col_idx_pag, str(nova_forma).strip())
                        if col_total:
                            col_idx_val = list(df_os.columns).index(col_total) + 1
                            ws.update_cell(linha_planilha, col_idx_val, val_num)
                        
                        if col_pago and col_pend:
                            col_idx_pago = list(df_os.columns).index(col_pago) + 1
                            col_idx_pend = list(df_os.columns).index(col_pend) + 1
                            if novo_status == "Paga":
                                ws.update_cell(linha_planilha, col_idx_pago, val_num)
                                ws.update_cell(linha_planilha, col_idx_pend, 0.0)
                            else:
                                ws.update_cell(linha_planilha, col_idx_pago, 0.0)
                                ws.update_cell(linha_planilha, col_idx_pend, val_num)

                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao alterar OS no Google Sheets: {e}")
    else:
        st.info("Nenhuma OS disponível para alteração.")
