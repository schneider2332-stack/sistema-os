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
        # header=3 faz o carregamento considerar a linha 4 da folha como cabeçalho
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
    c_data = next((c for c in cols if str(c).strip().upper() == "DATA" or ("DATA" in str(c).upper() and "PAG" not in str(c).upper())), None)
    c_cli = next((c for c in cols if "CLIENTE" in str(c).upper() or "NOME" in str(c).upper()), None)
    c_desc = next((c for c in cols if "DESC" in str(c).upper() or "SERVI" in str(c).upper()), None)
    c_val = next((c for c in cols if "VALOR TOT" in str(c).upper() or "VALOR" in str(c).upper() or "TOTAL" in str(c).upper() or "PREÇO" in str(c).upper()), None)
    c_sit = next((c for c in cols if "SITUA" in str(c).upper() or "STATUS" in str(c).upper()), None)
    c_pag = next((c for c in cols if "FORMA" in str(c).upper() or "PAG" in str(c).upper()), None)
    c_tel = next((c for c in cols if "TEL" in str(c).upper() or "WHATS" in str(c).upper() or "FONE" in str(c).upper()), None)
    return c_os, c_data, c_cli, c_desc, c_val, c_sit, c_pag, c_tel

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
        col_os, col_data, col_cliente, col_desc, col_valor, col_status, col_pagto, col_tel = identificar_colunas(df_os)

        df_calc = df_os.copy()
        df_calc['VALOR_NUM'] = df_calc[col_valor].apply(converter_para_numero) if col_valor else 0.0

        if col_data:
            df_calc['DATA_DT'] = pd.to_datetime(df_calc[col_data], errors='coerce', dayfirst=True)
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
            st.caption(f"A apresentar dados consolidados referentes a **{mes_selecionado}**")
        else:
            df_filtrado = df_calc.copy()
            st.caption("A apresentar dados acumulados de **todo o período**")

        st.markdown("<br>", unsafe_allow_html=True)

        total_faturado = df_filtrado['VALOR_NUM'].sum()
        total_qtd_os = len(df_filtrado)

        if col_status:
            mask_pago = df_filtrado[col_status].astype(str).str.upper().str.contains("CONCLUÍDO|CONCLUIDO|PAGO|ENTREGUE|PAGA", na=False)
            val_recebido = df_filtrado[mask_pago]['VALOR_NUM'].sum()
            val_aberto = df_filtrado[~mask_pago]['VALOR_NUM'].sum()
        else:
            val_recebido = total_faturado
            val_aberto = 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Total OS Lançadas", total_qtd_os)
        m2.metric("💵 Faturamento Total", formatar_moeda_br(total_faturado))
        m3.metric("✅ Valor Recebido", formatar_moeda_br(val_recebido))
        m4.metric("⏳ Valor em Aberto", formatar_moeda_br(val_aberto))

        st.markdown("---")
        label_periodo_pagto = "Geral" if mes_selecionado == "📅 Todos os Meses (Geral)" else mes_selecionado
        st.markdown(f"##### 💳 Faturamento Por Forma de Pagamento ({label_periodo_pagto})")

        col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
        col_cartao = next((c for c in df_os.columns if "CART" in str(c).upper()), None)
        col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
        col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

        if col_pix or col_cartao or col_boleto or col_dinheiro:
            pix = df_filtrado[col_pix].apply(converter_para_numero).sum() if col_pix else 0.0
            credito = df_filtrado[col_cartao].apply(converter_para_numero).sum() if col_cartao else 0.0
            debito = 0.0
            dinheiro = df_filtrado[col_dinheiro].apply(converter_para_numero).sum() if col_dinheiro else 0.0
            boleto = df_filtrado[col_boleto].apply(converter_para_numero).sum() if col_boleto else 0.0
        elif col_pagto:
            pix = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("PIX", na=False)]['VALOR_NUM'].sum()
            credito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("CRÉDITO|CREDITO", na=False)]['VALOR_NUM'].sum()
            debito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("DÉBITO|DEBITO", na=False)]['VALOR_NUM'].sum()
            dinheiro = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("DINHEIRO|ESPÉCIE", na=False)]['VALOR_NUM'].sum()
            boleto = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("BOLETO", na=False)]['VALOR_NUM'].sum()
        else:
            pix = credito = debito = dinheiro = boleto = 0.0

        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("📱 Pix", formatar_moeda_br(pix))
        p2.metric("💳 Cartão Crédito", formatar_moeda_br(credito))
        p3.metric("💳 Cartão Débito", formatar_moeda_br(debito))
        p4.metric("💵 Dinheiro", formatar_moeda_br(dinheiro))
        p5.metric("📄 Boleto", formatar_moeda_br(boleto))

        st.markdown("---")
        st.markdown("##### 🗓️ Resumo Comparativo Mês a Mês")

        if col_data:
            df_fluxo_dados = df_calc.dropna(subset=['DATA_DT']).copy()
            if not df_fluxo_dados.empty:
                df_fluxo = df_fluxo_dados.groupby('MES_ANO').agg(
                    Qtd_OS=('VALOR_NUM', 'count'),
                    Faturamento=('VALOR_NUM', 'sum')
                ).reset_index()

                df_fluxo['Faturamento (R$)'] = df_fluxo['Faturamento'].apply(formatar_moeda_br)
                df_fluxo = df_fluxo.rename(columns={'MES_ANO': 'Mês / Ano', 'Qtd_OS': 'Qtd. OS Lançadas'})
                st.dataframe(df_fluxo[['Mês / Ano', 'Qtd. OS Lançadas', 'Faturamento (R$)']], use_container_width=True)
            else:
                st.info("Nenhuma OS com data válida encontrada.")
    else:
        st.warning("Nenhum registo carregado. Confirme se a versão foi restaurada na folha de cálculo.")

# =============================================================================
# 2. LISTA DE OS CADASTRADAS
# =============================================================================
elif menu == "📊 OS Cadastradas (Lista)":
    st.subheader("📋 Tabela Geral de Ordens de Serviço")
    if not df_os.empty:
        st.dataframe(df_os, use_container_width=True)
    else:
        st.warning("Nenhum registo localizado.")

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
# 4. CADASTRAR NOVA OS (USO SEGURO DE APPEND_ROW)
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Cadastrar Nova OS")
    st.caption("Preencha os dados abaixo e clique em 'Salvar Ordem de Serviço'.")

    col1, col2 = st.columns(2)
    with col1:
        num_os = st.text_input("Número da OS", value=f"{len(df_os)+100000}")
        cliente = st.text_input("Nome do Cliente")
        telefone = st.text_input("Telefone / WhatsApp")
        servico = st.text_area("Descrição do Serviço")

    with col2:
        valor_input = st.text_input("Valor Total (R$)", value="0,00")
        forma_pagto = st.selectbox(
            "Forma de Pagamento", 
            ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
        )
        status = st.selectbox("Status Inicial", ["Em Aberto", "Em Andamento", "Concluído", "Entregue", "Paga"])
        data_entrada = st.date_input("Data de Entrada", datetime.now())

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Salvar Ordem de Serviço", type="primary", use_container_width=True):
        if not cliente.strip():
            st.warning("⚠️ Por favor, informe o Nome do Cliente antes de salvar.")
        else:
            val_formatado = converter_para_numero(valor_input)
            c_os, c_data, c_cli, c_desc, c_val, c_sit, c_pag, c_tel = identificar_colunas(df_os)

            nova_linha = {col: "" for col in df_os.columns}
            if c_os: nova_linha[c_os] = str(num_os).strip()
            if c_data: nova_linha[c_data] = data_entrada.strftime('%Y-%m-%d')
            if c_cli: nova_linha[c_cli] = cliente
            if c_desc: nova_linha[c_desc] = servico
            if c_val: nova_linha[c_val] = val_formatado
            if c_sit: nova_linha[c_sit] = str(status).strip()
            if c_pag: nova_linha[c_pag] = forma_pagto
            if c_tel: nova_linha[c_tel] = telefone

            col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
            col_cartao = next((c for c in df_os.columns if "CART" in str(c).upper()), None)
            col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
            col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

            if "PIX" in forma_pagto.upper() and col_pix: nova_linha[col_pix] = val_formatado
            elif "CART" in forma_pagto.upper() and col_cartao: nova_linha[col_cartao] = val_formatado
            elif "BOLETO" in forma_pagto.upper() and col_boleto: nova_linha[col_boleto] = val_formatado
            elif "DINHEIRO" in forma_pagto.upper() and col_dinheiro: nova_linha[col_dinheiro] = val_formatado

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
                st.success(f"✅ Ordem de Serviço {num_os} gravada com sucesso!")
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
        os_para_editar = st.selectbox("Selecione a OS:", ["-- Selecione a OS --"] + list(lista_os))

        if os_para_editar != "-- Selecione a OS --":
            dados_os = df_os[df_os[col_os].astype(str) == os_para_editar].iloc[0]
            status_atual = str(dados_os.get(col_sit, "Em Aberto")).strip()
            opcoes_status = ["Em Aberto", "Em Andamento", "Concluído", "Entregue", "Paga", "Cancelado"]
            idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0

            with st.form("form_editar_os"):
                st.markdown(f"**A editar Ordem de Serviço:** `{os_para_editar}`")
                c1, c2 = st.columns(2)
                with c1:
                    novo_status = st.selectbox("Novo Status", opcoes_status, index=idx_status)
                    nova_forma = st.selectbox("Nova Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
                with c2:
                    val_atual = str(dados_os[col_val]) if col_val and col_val in dados_os else "0,00"
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

                        if col_sit:
                            col_idx_sit = list(df_os.columns).index(col_sit) + 1
                            ws.update_cell(linha_planilha, col_idx_sit, str(novo_status).strip())
                        if col_pag:
                            col_idx_pag = list(df_os.columns).index(col_pag) + 1
                            ws.update_cell(linha_planilha, col_idx_pag, str(nova_forma).strip())
                        if col_val:
                            col_idx_val = list(df_os.columns).index(col_val) + 1
                            ws.update_cell(linha_planilha, col_idx_val, converter_para_numero(novo_valor))

                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao alterar OS no Google Sheets: {e}")
