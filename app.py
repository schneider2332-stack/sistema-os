import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import gspread
from google.oauth2.service_account import Credentials

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL E ESTRUTURA FIXA DAS COLUNAS
# =============================================================================
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

NOME_ABA = "Ordens de Serviço"

# Estrutura padrão e imutável das colunas da planilha (Linha 4, Colunas A até P)
COLUNAS_OFICIAIS = [
    "Número da OS", "Data", "Cliente", "Telefone", "Cidade", 
    "Descrição", "Valor Total", "Valor Pago", "Valor Pendente", 
    "Pix", "Cartão de Crédito", "Cartão de Débito", "Boleto", "Dinheiro", 
    "Situação", "Data do Pagamento", "Observações"
]

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
            # Garante que não carregue linhas totalmente em branco
            if "Número da OS" in df.columns:
                df = df[df["Número da OS"].notna() & (df["Número da OS"].astype(str).str.strip() != "")]
            return df
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)
    except Exception:
        return pd.DataFrame(columns=COLUNAS_OFICIAIS)

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
        
        # Conversão numérica de valores
        col_total = next((c for c in df_calc.columns if "TOTAL" in str(c).upper() or "VALOR" in str(c).upper()), None)
        col_pago = next((c for c in df_calc.columns if "VALOR PAG" in str(c).upper() or "PAGO" in str(c).upper()), None)
        col_pend = next((c for c in df_calc.columns if "PEND" in str(c).upper() or "ABERTO" in str(c).upper()), None)
        col_data = next((c for c in df_calc.columns if str(c).strip().upper() == "DATA"), "Data")

        df_calc['VALOR_TOTAL_NUM'] = df_calc[col_total].apply(converter_para_numero) if col_total else 0.0
        df_calc['VALOR_PAGO_NUM'] = df_calc[col_pago].apply(converter_para_numero) if col_pago else 0.0
        df_calc['VALOR_PEND_NUM'] = df_calc[col_pend].apply(converter_para_numero) if col_pend else (df_calc['VALOR_TOTAL_NUM'] - df_calc['VALOR_PAGO_NUM'])

        # Parsing de datas com detecção inteligente
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

        # Puxa os totais das colunas específicas ou de agrupamento
        col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
        col_cred = next((c for c in df_os.columns if "CRÉD" in str(c).upper() or "CRED" in str(c).upper()), None)
        col_deb = next((c for c in df_os.columns if "DÉB" in str(c).upper() or "DEB" in str(c).upper()), None)
        col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
        col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

        pix = df_filtrado[col_pix].apply(converter_para_numero).sum() if col_pix else 0.0
        credito = df_filtrado[col_cred].apply(converter_para_numero).sum() if col_cred else 0.0
        debito = df_filtrado[col_deb].apply(converter_para_numero).sum() if col_deb else 0.0
        dinheiro = df_filtrado[col_dinheiro].apply(converter_para_numero).sum() if col_dinheiro else 0.0
        boleto = df_filtrado[col_boleto].apply(converter_para_numero).sum() if col_boleto else 0.0

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
        st.info("Nenhuma OS encontrada. Cadastre uma nova OS para iniciar o Dashboard.")

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
# 4. CADASTRAR NOVA OS (GRAVAÇÃO EXATA NA PRIMEIRA LINHA LIVRE)
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
        valor_input = st.text_input("Valor Total (R$)", value="0,00")
        forma_pagto = st.selectbox(
            "Forma de Pagamento", 
            ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto"]
        )
        status = st.selectbox("Situação Inicial", ["Paga", "Em Aberto", "Parcial"])
        data_entrada = st.date_input("Data de Entrada", datetime.now())

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Salvar Ordem de Serviço", type="primary", use_container_width=True):
        if not cliente.strip():
            st.warning("⚠️ Por favor, informe o Nome do Cliente antes de salvar.")
        else:
            val_formatado = converter_para_numero(valor_input)
            
            # Montar a linha com base nas colunas oficiais
            nova_linha = {c: "" for c in COLUNAS_OFICIAIS}
            nova_linha["Número da OS"] = str(num_os).strip()
            nova_linha["Data"] = data_entrada.strftime('%Y-%m-%d')
            nova_linha["Cliente"] = cliente
            nova_linha["Telefone"] = telefone
            nova_linha["Cidade"] = cidade
            nova_linha["Descrição"] = servico
            nova_linha["Valor Total"] = val_formatado
            
            if status == "Paga":
                nova_linha["Valor Pago"] = val_formatado
                nova_linha["Valor Pendente"] = 0.0
                nova_linha["Data do Pagamento"] = data_entrada.strftime('%Y-%m-%d')
            else:
                nova_linha["Valor Pago"] = 0.0
                nova_linha["Valor Pendente"] = val_formatado

            nova_linha["Situação"] = str(status).strip()

            # Atribuição por forma de pagamento
            if forma_pagto == "Pix":
                nova_linha["Pix"] = val_formatado
            elif forma_pagto == "Cartão de Crédito":
                nova_linha["Cartão de Crédito"] = val_formatado
            elif forma_pagto == "Cartão de Débito":
                nova_linha["Cartão de Débito"] = val_formatado
            elif forma_pagto == "Boleto":
                nova_linha["Boleto"] = val_formatado
            elif forma_pagto == "Dinheiro":
                nova_linha["Dinheiro"] = val_formatado

            try:
                ws = obter_worksheet_gspread()
                
                # Encontrar a primeira linha verdadeiramente vazia na coluna A
                coluna_a = ws.col_values(1)  # Pega os valores da coluna A
                
                # Se só tem até a linha 4 (ou menos), a próxima linha é a 5
                primeira_linha_livre = max(5, len(coluna_a) + 1)
                
                # Monta a lista de valores na ordem exata de A até P
                lista_valores = [nova_linha.get(col, "") for col in COLUNAS_OFICIAIS]
                
                # Grava exatamente na linha livre encontrada (ex: A5:Q5)
                alcance = f"A{primeira_linha_livre}:Q{primeira_linha_livre}"
                ws.update(range_name=alcance, values=[lista_valores])

                st.cache_data.clear()
                st.success(f"✅ Ordem de Serviço {num_os} gravada com sucesso na linha {primeira_linha_livre}!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar no Google Sheets: {e}")

# =============================================================================
# 5. ALTERAR OU EXCLUIR OS / PAGAMENTO
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

            with st.form("form_editar_os"):
                st.markdown(f"**Editando Ordem de Serviço:** `{os_para_editar}`")
                c1, c2 = st.columns(2)
                with c1:
                    novo_status = st.selectbox("Novo Status", opcoes_status, index=idx_status)
                    nova_forma = st.selectbox(
                        "Nova Forma de Pagamento", 
                        ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto"]
                    )
                with c2:
                    val_atual = str(dados_os.get("Valor Total", "0,00"))
                    novo_valor = st.text_input("Atualizar Valor Total (R$)", value=val_atual)

                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações na OS")
                if btn_salvar_alt:
                    try:
                        ws = obter_worksheet_gspread()
                        idx_relativo = df_os[df_os[col_os].astype(str) == os_para_editar].index[0]
                        linha_planilha = idx_relativo + 5  # Linha 4 cabeçalho, dados começam na 5

                        val_num = converter_para_numero(novo_valor)

                        # Encontra os índices das colunas
                        headers = ws.row_values(4)
                        
                        def atualizar_se_existir(nome_col, valor):
                            if nome_col in headers:
                                col_idx = headers.index(nome_col) + 1
                                ws.update_cell(linha_planilha, col_idx, valor)

                        atualizar_se_existir("Situação", str(novo_status).strip())
                        atualizar_se_existir("Valor Total", val_num)

                        if novo_status == "Paga":
                            atualizar_se_existir("Valor Pago", val_num)
                            atualizar_se_existir("Valor Pendente", 0.0)
                        else:
                            atualizar_se_existir("Valor Pago", 0.0)
                            atualizar_se_existir("Valor Pendente", val_num)

                        # Limpa formas de pagamento antigas e grava na nova
                        for f in ["Pix", "Cartão de Crédito", "Cartão de Débito", "Boleto", "Dinheiro"]:
                            atualizar_se_existir(f, val_num if f == nova_forma else 0.0)

                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao alterar OS no Google Sheets: {e}")
    else:
        st.info("Nenhuma OS disponível para alteração.")
