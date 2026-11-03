import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL E ESTRUTURA
# =============================================================================
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

NOME_ABA = "Ordens de Serviço"

def obter_worksheet_gspread():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    secrets_gsheets = st.secrets["connections"]["gsheets"]
    cred_dict = {
        "type": secrets_gsheets.get("type", "service_account"),
        "project_id": secrets_gsheets.get("project_id"),
        "private_key_id": secrets_gsheets.get("private_key_id"),
        "private_key": secrets_gsheets.get("private_key").replace("\\n", "\n"),
        "client_email": secrets_gsheets.get("client_email"),
        "client_id": secrets_gsheets.get("client_id"),
        "auth_uri": secrets_gsheets.get("auth_uri", "https://accounts.google.com/o/oauth2/auth"),
        "token_uri": secrets_gsheets.get("token_uri", "https://oauth2.googleapis.com/token"),
        "auth_provider_x509_cert_url": secrets_gsheets.get("auth_provider_x509_cert_url"),
        "client_x509_cert_url": secrets_gsheets.get("client_x509_cert_url")
    }
    creds = Credentials.from_service_account_info(cred_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(secrets_gsheets["spreadsheet"])
    return sh.worksheet(NOME_ABA)

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet=NOME_ABA, header=3, ttl=0)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            col_os = next((c for c in df.columns if "NÚMERO" in str(c).upper() or "OS" in str(c).upper()), None)
            if col_os:
                df = df[df[col_os].notna() & (df[col_os].astype(str).str.strip() != "")]
                df[col_os] = df[col_os].astype(str).str.replace(r'\.0$', '', regex=True)
            return df.reset_index(drop=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def formatar_moeda_br(valor_float):
    return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def converter_para_numero(valor):
    if pd.isna(valor) or str(valor).strip() == "" or str(valor).strip().lower() == "nan":
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

def formatar_valor_campo(valor):
    num = converter_para_numero(valor)
    return f"{num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

df_os = carregar_dados()

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
        df_calc = df_os.copy()
        
        col_total = next((c for c in df_calc.columns if "TOTAL" in str(c).upper() or "VALOR" in str(c).upper()), None)
        col_pago = next((c for c in df_calc.columns if "VALOR PAG" in str(c).upper() or "PAGO" in str(c).upper()), None)
        col_pend = next((c for c in df_calc.columns if "PEND" in str(c).upper() or "ABERTO" in str(c).upper()), None)
        col_data = next((c for c in df_calc.columns if str(c).strip().upper() == "DATA"), "Data")

        df_calc['VALOR_TOTAL_NUM'] = df_calc[col_total].apply(converter_para_numero) if col_total else 0.0
        df_calc['VALOR_PAGO_NUM'] = df_calc[col_pago].apply(converter_para_numero) if col_pago else 0.0
        df_calc['VALOR_PEND_NUM'] = df_calc[col_pend].apply(converter_para_numero) if col_pend else (df_calc['VALOR_TOTAL_NUM'] - df_calc['VALOR_PAGO_NUM'])

        if col_data in df_calc.columns:
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

        if mes_selecionado != "📅 Todos os Meses (Geral)" and 'MES_ANO' in df_calc.columns:
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

        col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
        col_cred = next((c for c in df_os.columns if "CRÉD" in str(c).upper() or "CRED" in str(c).upper()), None)
        col_deb = next((c for c in df_os.columns if "DÉB" in str(c).upper() or "DEB" in str(c).upper()), None)
        col_cartao_geral = next((c for c in df_os.columns if "CART" in str(c).upper() and not col_cred and not col_deb), None)
        col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
        col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)
        col_obs = next((c for c in df_os.columns if "OBS" in str(c).upper()), None)

        pix = df_filtrado[col_pix].apply(converter_para_numero).sum() if col_pix else 0.0
        credito = df_filtrado[col_cred].apply(converter_para_numero).sum() if col_cred else 0.0
        debito = df_filtrado[col_deb].apply(converter_para_numero).sum() if col_deb else 0.0
        dinheiro = df_filtrado[col_dinheiro].apply(converter_para_numero).sum() if col_dinheiro else 0.0
        boleto = df_filtrado[col_boleto].apply(converter_para_numero).sum() if col_boleto else 0.0

        if col_cartao_geral:
            val_cartao_total = df_filtrado[col_cartao_geral].apply(converter_para_numero).sum()
            if col_obs:
                mask_deb = df_filtrado[col_obs].astype(str).str.upper().str.contains("DÉBITO|DEBITO", na=False)
                debito += df_filtrado[mask_deb][col_cartao_geral].apply(converter_para_numero).sum()
                credito += df_filtrado[~mask_deb][col_cartao_geral].apply(converter_para_numero).sum()
            else:
                debito += val_cartao_total

        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("📱 Pix", formatar_moeda_br(pix))
        p2.metric("💳 Cartão de Crédito", formatar_moeda_br(credito))
        p3.metric("💳 Cartão de Débito", formatar_moeda_br(debito))
        p4.metric("💵 Dinheiro", formatar_moeda_br(dinheiro))
        p5.metric("📄 Boleto", formatar_moeda_br(boleto))

        st.markdown("---")
        st.markdown("##### 🗓️ Resumo Comparativo Mês a Mês")

        if 'DATA_DT' in df_calc.columns:
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
        st.info("Nenhuma OS cadastrada ainda.")

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
        col_os = next((c for c in df_os.columns if "NÚMERO" in str(c).upper() or "OS" in str(c).upper()), df_os.columns[0])
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

    proximo_num = (len(df_os) + 1001) if not df_os.empty else 1001

    col1, col2 = st.columns(2)
    with col1:
        num_os = st.text_input("Número da OS", value=str(proximo_num))
        cliente = st.text_input("Nome do Cliente")
        telefone = st.text_input("Telefone / WhatsApp")
        cidade = st.text_input("Cidade", value="Florianópolis")
        servico = st.text_area("Descrição do Serviço")

    with col2:
        forma_pagto = st.selectbox(
            "Forma de Pagamento", 
            ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
        )
        
        val_pix_input = 0.0
        val_cred_input = 0.0
        val_deb_input = 0.0
        val_din_input = 0.0
        val_bol_input = 0.0
        
        if forma_pagto == "Pagamento Misto":
            st.markdown("##### 💳 Valores Fracionados por Meio de Pagamento")
            cp1, cp2 = st.columns(2)
            pix_txt = cp1.text_input("Pix (R$)", value="0,00")
            din_txt = cp2.text_input("Dinheiro (R$)", value="0,00")
            
            cp3, cp4 = st.columns(2)
            cred_txt = cp3.text_input("Cartão de Crédito (R$)", value="0,00")
            deb_txt = cp4.text_input("Cartão de Débito (R$)", value="0,00")
            
            bol_txt = st.text_input("Boleto (R$)", value="0,00")
            
            val_pix_input = converter_para_numero(pix_txt)
            val_cred_input = converter_para_numero(cred_txt)
            val_deb_input = converter_para_numero(deb_txt)
            val_din_input = converter_para_numero(din_txt)
            val_bol_input = converter_para_numero(bol_txt)
            
            total_misto = val_pix_input + val_cred_input + val_deb_input + val_din_input + val_bol_input
            valor_total_efetivo = total_misto
            st.info(f"**Total Consolidado:** {formatar_moeda_br(total_misto)}")
        else:
            valor_input = st.text_input("Valor Total (R$)", value="0,00")
            valor_total_efetivo = converter_para_numero(valor_input)

        status = st.selectbox("Situação Inicial", ["Paga", "Em Aberto", "Parcial"])
        data_entrada = st.date_input("Data de Entrada", datetime.now())

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Salvar Ordem de Serviço", type="primary", use_container_width=True):
        if not cliente.strip():
            st.warning("⚠️ Por favor, informe o Nome do Cliente antes de salvar.")
        else:
            try:
                ws = obter_worksheet_gspread()
                headers = ws.row_values(4)
                nova_linha = {h: "" for h in headers}

                def set_col(nome_chave, val):
                    for h in headers:
                        if nome_chave.upper() in str(h).upper():
                            nova_linha[h] = val
                            return

                set_col("NÚMERO", str(num_os).strip())
                set_col("DATA", data_entrada.strftime('%Y-%m-%d'))
                set_col("CLIENTE", cliente)
                set_col("TELEFONE", telefone)
                set_col("CIDADE", cidade)
                set_col("DESC", servico)
                set_col("TOTAL", valor_total_efetivo)
                set_col("SITUA", str(status).strip())

                if status == "Paga":
                    set_col("VALOR PAG", valor_total_efetivo)
                    set_col("PEND", 0.0)
                    set_col("DATA DO PAG", data_entrada.strftime('%Y-%m-%d'))
                else:
                    set_col("VALOR PAG", 0.0)
                    set_col("PEND", valor_total_efetivo)

                tem_col_deb = any("DÉB" in str(h).upper() or "DEB" in str(h).upper() for h in headers)
                tem_col_cred = any("CRÉD" in str(h).upper() or "CRED" in str(h).upper() for h in headers)

                if forma_pagto == "Pagamento Misto":
                    set_col("PIX", val_pix_input)
                    set_col("BOLETO", val_bol_input)
                    set_col("DINHEIRO", val_din_input)
                    if tem_col_cred: set_col("CRÉD", val_cred_input)
                    if tem_col_deb: set_col("DÉB", val_deb_input)
                    if not tem_col_cred and not tem_col_deb:
                        set_col("CART", val_cred_input + val_deb_input)
                    set_col("OBS", "Pagamento Misto")
                elif forma_pagto == "Pix":
                    set_col("PIX", valor_total_efetivo)
                elif forma_pagto == "Cartão de Crédito":
                    if tem_col_cred: set_col("CRÉD", valor_total_efetivo)
                    else: set_col("CART", valor_total_efetivo)
                    set_col("OBS", "Cartão de Crédito")
                elif forma_pagto == "Cartão de Débito":
                    if tem_col_deb: set_col("DÉB", valor_total_efetivo)
                    else: set_col("CART", valor_total_efetivo)
                    set_col("OBS", "Cartão de Débito")
                elif forma_pagto == "Boleto":
                    set_col("BOLETO", valor_total_efetivo)
                elif forma_pagto == "Dinheiro":
                    set_col("DINHEIRO", valor_total_efetivo)

                coluna_a = ws.col_values(1)
                primeira_linha_livre = max(5, len(coluna_a) + 1)

                lista_valores = [nova_linha.get(h, "") for h in headers]
                col_fim_letra = chr(64 + len(headers)) if len(headers) <= 26 else "Q"
                alcance = f"A{primeira_linha_livre}:{col_fim_letra}{primeira_linha_livre}"
                ws.update(range_name=alcance, values=[lista_valores])

                st.cache_data.clear()
                st.success(f"✅ Ordem de Serviço {num_os} gravada com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar no Google Sheets: {e}")

# =============================================================================
# 5. ALTERAR OU EXCLUIR OS / PAGAMENTO (CORREÇÃO DE LOCALIZAÇÃO E LIMPEZA)
# =============================================================================
elif menu == "✏️ Alterar OS / Pagamento":
    st.subheader("✏️ Alterar ou Excluir Ordem de Serviço")
    if not df_os.empty:
        col_os = next((c for c in df_os.columns if "NÚMERO" in str(c).upper() or "OS" in str(c).upper()), df_os.columns[0])
        lista_os = df_os[col_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS:", ["-- Selecione a OS --"] + list(lista_os))

        if os_para_editar != "-- Selecione a OS --":
            dados_os = df_os[df_os[col_os].astype(str) == os_para_editar].iloc[0]
            status_atual = str(dados_os.get("Situação", "Em Aberto")).strip()
            opcoes_status = ["Paga", "Em Aberto", "Parcial"]
            idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0

            v_pix_at = converter_para_numero(dados_os.get("Pix", 0.0))
            v_cred_at = converter_para_numero(dados_os.get("Cartão de Crédito", 0.0))
            v_deb_at = converter_para_numero(dados_os.get("Cartão de Débito", 0.0))
            v_din_at = converter_para_numero(dados_os.get("Dinheiro", 0.0))
            v_bol_at = converter_para_numero(dados_os.get("Boleto", 0.0))
            
            if v_cred_at == 0 and v_deb_at == 0 and "Cartão" in dados_os:
                v_cart_geral = converter_para_numero(dados_os.get("Cartão", 0.0))
                obs_texto = str(dados_os.get("Observações", "")).upper()
                if "DÉBITO" in obs_texto or "DEBITO" in obs_texto:
                    v_deb_at = v_cart_geral
                else:
                    v_cred_at = v_cart_geral

            contagem_formas = sum([1 for v in [v_pix_at, v_cred_at, v_deb_at, v_din_at, v_bol_at] if v > 0])
            
            if contagem_formas > 1:
                forma_inicial = "Pagamento Misto"
            elif v_deb_at > 0:
                forma_inicial = "Cartão de Débito"
            elif v_cred_at > 0:
                forma_inicial = "Cartão de Crédito"
            elif v_pix_at > 0:
                forma_inicial = "Pix"
            elif v_din_at > 0:
                forma_inicial = "Dinheiro"
            elif v_bol_at > 0:
                forma_inicial = "Boleto"
            else:
                forma_inicial = "Cartão de Débito"

            opcoes_pag = ["Cartão de Débito", "Cartão de Crédito", "Pix", "Dinheiro", "Boleto", "Pagamento Misto"]
            idx_pag = opcoes_pag.index(forma_inicial) if forma_inicial in opcoes_pag else 0

            with st.form("form_editar_os"):
                st.markdown(f"**Editando Ordem de Serviço:** `{os_para_editar}`")
                c1, c2 = st.columns(2)
                with c1:
                    novo_status = st.selectbox("Novo Status", opcoes_status, index=idx_status)
                    nova_forma = st.selectbox("Forma de Pagamento", opcoes_pag, index=idx_pag)
                with c2:
                    val_atual = formatar_valor_campo(dados_os.get("Valor Total", 0.0))
                    novo_valor = st.text_input("Valor Total (R$)", value=val_atual)

                st.markdown("##### 💳 Valores Parciais (usado se Pagamento Misto)")
                e_col1, e_col2, e_col3 = st.columns(3)
                pix_edit = e_col1.text_input("Pix (R$)", value=formatar_valor_campo(v_pix_at))
                cred_edit = e_col2.text_input("Cartão de Crédito (R$)", value=formatar_valor_campo(v_cred_at))
                deb_edit = e_col3.text_input("Cartão de Débito (R$)", value=formatar_valor_campo(v_deb_at))
                
                e_col4, e_col5 = st.columns(2)
                din_edit = e_col4.text_input("Dinheiro (R$)", value=formatar_valor_campo(v_din_at))
                bol_edit = e_col5.text_input("Boleto (R$)", value=formatar_valor_campo(v_bol_at))

                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações na OS", type="primary", use_container_width=True)

                if btn_salvar_alt:
                    try:
                        ws = obter_worksheet_gspread()
                        
                        # Localização EXATA da linha pela Coluna A do Google Sheets
                        coluna_a_raw = ws.col_values(1)
                        coluna_a_limpa = [str(x).replace('.0', '').strip() for x in coluna_a_raw]
                        alvo_os = str(os_para_editar).replace('.0', '').strip()

                        if alvo_os in coluna_a_limpa:
                            linha_planilha = coluna_a_limpa.index(alvo_os) + 1
                        else:
                            idx_relativo = df_os[df_os[col_os].astype(str) == os_para_editar].index[0]
                            linha_planilha = idx_relativo + 5

                        headers = ws.row_values(4)
                        def set_cell(col_name_part, valor):
                            for idx_h, h in enumerate(headers):
                                if col_name_part.upper() in str(h).upper():
                                    ws.update_cell(linha_planilha, idx_h + 1, valor)
                                    return

                        tem_deb = any("DÉB" in str(h).upper() or "DEB" in str(h).upper() for h in headers)
                        tem_cred = any("CRÉD" in str(h).upper() or "CRED" in str(h).upper() for h in headers)

                        v_pix = converter_para_numero(pix_edit)
                        v_cred = converter_para_numero(cred_edit)
                        v_deb = converter_para_numero(deb_edit)
                        v_din = converter_para_numero(din_edit)
                        v_bol = converter_para_numero(bol_edit)

                        # Zera primeiro todas as colunas de pagamento para evitar resíduos cruzados
                        set_cell("PIX", 0.0)
                        set_cell("BOLETO", 0.0)
                        set_cell("DINHEIRO", 0.0)
                        if tem_cred: set_cell("CRÉD", 0.0)
                        if tem_deb: set_cell("DÉB", 0.0)
                        if not tem_cred and not tem_deb: set_cell("CART", 0.0)

                        if nova_forma == "Pagamento Misto":
                            val_final = v_pix + v_cred + v_deb + v_din + v_bol
                            set_cell("PIX", v_pix)
                            set_cell("BOLETO", v_bol)
                            set_cell("DINHEIRO", v_din)
                            if tem_cred: set_cell("CRÉD", v_cred)
                            if tem_deb: set_cell("DÉB", v_deb)
                            if not tem_cred and not tem_deb:
                                set_cell("CART", v_cred + v_deb)
                            set_cell("OBS", "Pagamento Misto")
                        else:
                            val_final = converter_para_numero(novo_valor)
                            if nova_forma == "Pix":
                                set_cell("PIX", val_final)
                                set_cell("OBS", "Pix")
                            elif nova_forma == "Boleto":
                                set_cell("BOLETO", val_final)
                                set_cell("OBS", "Boleto")
                            elif nova_forma == "Dinheiro":
                                set_cell("DINHEIRO", val_final)
                                set_cell("OBS", "Dinheiro")
                            elif nova_forma == "Cartão de Crédito":
                                if tem_cred: set_cell("CRÉD", val_final)
                                else: set_cell("CART", val_final)
                                set_cell("OBS", "Cartão de Crédito")
                            elif nova_forma == "Cartão de Débito":
                                if tem_deb: set_cell("DÉB", val_final)
                                else: set_cell("CART", val_final)
                                set_cell("OBS", "Cartão de Débito")

                        set_cell("SITUA", str(novo_status).strip())
                        set_cell("TOTAL", val_final)

                        if novo_status == "Paga":
                            set_cell("VALOR PAG", val_final)
                            set_cell("PEND", 0.0)
                        else:
                            set_cell("VALOR PAG", 0.0)
                            set_cell("PEND", val_final)

                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada para **{nova_forma}** com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao alterar OS no Google Sheets: {e}")

            # -----------------------------------------------------------------
            # ZONA DE EXCLUSÃO DE REGISTRO
            # -----------------------------------------------------------------
            st.markdown("---")
            st.warning("⚠️ **Zona de Perigo: Exclusão de Registro**")
            confirmar_exclusao = st.checkbox(f"Confirmo que desejo apagar permanentemente a OS **{os_para_editar}**")
            
            if st.button("🗑️ Excluir esta OS", type="secondary", disabled=not confirmar_exclusao):
                try:
                    ws = obter_worksheet_gspread()
                    coluna_a_raw = ws.col_values(1)
                    coluna_a_limpa = [str(x).replace('.0', '').strip() for x in coluna_a_raw]
                    alvo_os = str(os_para_editar).replace('.0', '').strip()

                    if alvo_os in coluna_a_limpa:
                        linha_planilha = coluna_a_limpa.index(alvo_os) + 1
                    else:
                        idx_relativo = df_os[df_os[col_os].astype(str) == os_para_editar].index[0]
                        linha_planilha = idx_relativo + 5
                    
                    ws.delete_rows(linha_planilha)
                    st.cache_data.clear()
                    st.success(f"🗑️ Ordem de Serviço {os_para_editar} excluída com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir OS no Google Sheets: {e}")
    else:
        st.info("Nenhuma OS disponível para alteração.")
