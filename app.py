import streamlit as st
import pandas as pd
from datetime import datetime
import re
from streamlit_gsheets import GSheetsConnection

# 1. Configuração Inicial da Página
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

# Formatação monetária padrão brasileiro (R$ 1.300,00)
def formatar_moeda_br(valor_float):
    try:
        return f"R$ {float(valor_float):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "R$ 0,00"

# Conversão monetária segura
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

# 2. Carregamento dos dados com tratamento de cabeçalho
@st.cache_data(ttl=0)
def carregar_dados():
    # Tentativa 1: Exportação CSV direta pulando as linhas vazias do topo
    try:
        url_csv = "https://docs.google.com/spreadsheets/d/1IHmxCEP3VdPK7eKR3aoKTsDb-3z6u5auIqlhZoGtRnU/gviz/tq?tqx=out:csv&sheet=Ordens%20de%20Servi%C3%A7o"
        df_csv = pd.read_csv(url_csv, skiprows=3)
        df_csv.columns = [str(c).strip() for c in df_csv.columns]
        df_csv = df_csv.dropna(how='all')
        col_os = next((c for c in df_csv.columns if "OS" in c.upper() or "NUMERO" in c.upper()), df_csv.columns[0])
        df_csv = df_csv.dropna(subset=[col_os])
        if not df_csv.empty:
            return df_csv
    except Exception:
        pass

    # Tentativa 2: Conexão interna GSheets
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Ordens de Serviço", ttl=0)
        if df is not None and not df.empty:
            for idx, row in df.iterrows():
                if row.astype(str).str.contains('Número da OS|Numero da OS', case=False).any():
                    df.columns = [str(c).strip() for c in df.iloc[idx]]
                    df = df.iloc[idx+1:].reset_index(drop=True)
                    break
            df = df.dropna(how='all')
            return df
    except Exception:
        pass

    return pd.DataFrame()

# Identificação das colunas da planilha
def identificar_colunas(df):
    cols = list(df.columns)
    c_os = next((c for c in cols if ("OS" in str(c).upper() or "NUMERO" in str(c).upper()) and "DATA" not in str(c).upper()), "Número da OS")
    c_data = next((c for c in cols if str(c).strip().upper() == "DATA"), None)
    c_cli = next((c for c in cols if "CLIENTE" in str(c).upper() or "NOME" in str(c).upper()), None)
    c_desc = next((c for c in cols if "DESC" in str(c).upper() or "SERVIÇO" in str(c).upper() or "SERVICO" in str(c).upper()), None)
    c_val = next((c for c in cols if str(c).strip().upper() == "VALOR TOTAL"), None)
    c_pago = next((c for c in cols if str(c).strip().upper() == "VALOR PAGO"), None)
    c_pend = next((c for c in cols if str(c).strip().upper() == "VALOR PENDENTE"), None)
    c_sit = next((c for c in cols if "SITUAÇÃO" in str(c).upper() or "SITUACAO" in str(c).upper() or "STATUS" in str(c).upper()), None)
    c_tel = next((c for c in cols if "TEL" in str(c).upper() or "WHATS" in str(c).upper()), None)
    
    c_pix = next((c for c in cols if str(c).strip().upper() == "PIX"), None)
    c_cartao = next((c for c in cols if "CART" in str(c).upper()), None)
    c_boleto = next((c for c in cols if "BOLETO" in str(c).upper()), None)
    c_dinheiro = next((c for c in cols if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper() or "ESPECIE" in str(c).upper()), None)

    return c_os, c_data, c_cli, c_desc, c_val, c_pago, c_pend, c_sit, c_tel, c_pix, c_cartao, c_boleto, c_dinheiro

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
        c_os, c_data, c_cli, c_desc, c_val, c_pago, c_pend, c_sit, c_tel, c_pix, c_cartao, c_boleto, c_dinheiro = identificar_colunas(df_os)

        df_calc = df_os.copy()
        df_calc['VALOR_NUM'] = df_calc[c_val].apply(converter_para_numero) if c_val else 0.0
        df_calc['PAGO_NUM'] = df_calc[c_pago].apply(converter_para_numero) if c_pago else 0.0
        df_calc['PEND_NUM'] = df_calc[c_pend].apply(converter_para_numero) if c_pend else 0.0

        if c_pix: df_calc['PIX_NUM'] = df_calc[c_pix].apply(converter_para_numero)
        if c_cartao: df_calc['CARTAO_NUM'] = df_calc[c_cartao].apply(converter_para_numero)
        if c_boleto: df_calc['BOLETO_NUM'] = df_calc[c_boleto].apply(converter_para_numero)
        if c_dinheiro: df_calc['DINHEIRO_NUM'] = df_calc[c_dinheiro].apply(converter_para_numero)

        if c_data:
            df_calc['DATA_DT'] = pd.to_datetime(df_calc[c_data], errors='coerce')
            df_calc['MES_ANO'] = df_calc['DATA_DT'].dt.strftime('%m/%Y')
            
            meses_disponiveis = [m for m in df_calc['MES_ANO'].dropna().unique().tolist() if str(m).strip()]
            try:
                meses_disponiveis.sort(key=lambda x: datetime.strptime(x, '%m/%Y'), reverse=True)
            except Exception:
                pass
            
            opcoes_mes = ["📅 Todos os Meses (Geral)"] + meses_disponiveis
        else:
            opcoes_mes = ["📅 Todos os Meses (Geral)"]

        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            mes_selecionado = st.selectbox("📆 **Filtrar Período do Dashboard:**", opcoes_mes, index=0)

        if mes_selecionado != "📅 Todos os Meses (Geral)" and c_data:
            df_filtrado = df_calc[df_calc['MES_ANO'] == mes_selecionado].copy()
            st.caption(f"Exibindo dados consolidados referentes a **{mes_selecionado}**")
        else:
            df_filtrado = df_calc.copy()
            st.caption("Exibindo dados acumulados de **todo o período**")

        st.markdown("<br>", unsafe_allow_html=True)

        total_faturado = df_filtrado['VALOR_NUM'].sum()
        total_qtd_os = len(df_filtrado)
        val_recebido = df_filtrado['PAGO_NUM'].sum() if c_pago else total_faturado
        val_aberto = df_filtrado['PEND_NUM'].sum() if c_pend else (total_faturado - val_recebido)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Total OS Lançadas", total_qtd_os)
        m2.metric("💵 Faturamento Total", formatar_moeda_br(total_faturado))
        m3.metric("✅ Valor Recebido", formatar_moeda_br(val_recebido))
        m4.metric("⏳ Valor em Aberto", formatar_moeda_br(val_aberto))

        st.markdown("---")
        st.markdown(f"##### 💳 Faturamento Efetivado por Forma de Pagamento ({'Geral' if mes_selecionado == '📅 Todos os Meses (Geral)' else mes_selecionado})")

        tot_pix = df_filtrado['PIX_NUM'].sum() if c_pix else 0.0
        tot_cartao = df_filtrado['CARTAO_NUM'].sum() if c_cartao else 0.0
        tot_boleto = df_filtrado['BOLETO_NUM'].sum() if c_boleto else 0.0
        tot_dinheiro = df_filtrado['DINHEIRO_NUM'].sum() if c_dinheiro else 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📱 Pix (Recebido)", formatar_moeda_br(tot_pix))
        p2.metric("💳 Cartão", formatar_moeda_br(tot_cartao))
        p3.metric("💵 Dinheiro", formatar_moeda_br(tot_dinheiro))
        p4.metric("📄 Boleto", formatar_moeda_br(tot_boleto))

        st.markdown("---")
        st.markdown("##### 🗓️ Resumo Comparativo Mês a Mês")

        if c_data:
            df_fluxo_dados = df_calc.dropna(subset=['DATA_DT']).copy()
            if not df_fluxo_dados.empty:
                df_fluxo = df_fluxo_dados.groupby('MES_ANO').agg(
                    Qtd_OS=('VALOR_NUM', 'count'),
                    Faturamento=('VALOR_NUM', 'sum'),
                    Recebido=('PAGO_NUM', 'sum') if c_pago else ('VALOR_NUM', 'sum')
                ).reset_index()

                df_fluxo['Faturamento (R$)'] = df_fluxo['Faturamento'].apply(formatar_moeda_br)
                df_fluxo['Recebido (R$)'] = df_fluxo['Recebido'].apply(formatar_moeda_br)
                df_fluxo = df_fluxo.rename(columns={'MES_ANO': 'Mês / Ano', 'Qtd_OS': 'Qtd. OS Lançadas'})
                
                st.dataframe(df_fluxo[['Mês / Ano', 'Qtd. OS Lançadas', 'Faturamento (R$)', 'Recebido (R$)']], use_container_width=True)
            else:
                st.info("Nenhuma OS com data válida encontrada.")
        else:
            st.info("Coluna de Data não identificada.")
    else:
        st.warning("Nenhum dado encontrado para carregar o Dashboard. Verifique a conexão com a planilha.")

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
        c_os, _, _, _, _, _, _, _, _, _, _, _, _ = identificar_colunas(df_os)
        lista_os = df_os[c_os].dropna().astype(str).unique()
        
        os_sel = st.selectbox("Selecione o Número da OS:", lista_os)
        if os_sel:
            detalhe = df_os[df_os[c_os].astype(str) == os_sel]
            st.dataframe(detalhe, use_container_width=True)

# =============================================================================
# 4. CADASTRAR NOVA OS
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Cadastrar Nova OS")
    st.caption("Preencha os dados abaixo e clique em 'Salvar Ordem de Serviço'.")

    col1, col2 = st.columns(2)
    with col1:
        num_os = st.text_input("Número da OS", value=f"{len(df_os)+99000}")
        cliente = st.text_input("Nome do Cliente")
        telefone = st.text_input("Telefone / WhatsApp")
        servico = st.text_area("Descrição do Serviço")

    with col2:
        valor_input = st.text_input("Valor Total (R$)", value="0,00", help="Exemplo: 1300,00 ou 500,00")
        forma_pagto = st.selectbox("Forma de Pagamento Principal", ["Pix", "Cartão", "Dinheiro", "Boleto"])
        status = st.selectbox("Situação da OS", ["Concluída", "Em Aberto", "Parcial", "Paga"])
        data_entrada = st.date_input("Data de Entrada", datetime.now())

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 Salvar Ordem de Serviço", type="primary", use_container_width=True):
        if not cliente.strip():
            st.warning("⚠️ Por favor, informe o Nome do Cliente antes de salvar.")
        else:
            val_formatado = converter_para_numero(valor_input)
            c_os, c_data, c_cli, c_desc, c_val, c_pago, c_pend, c_sit, c_tel, c_pix, c_cartao, c_boleto, c_dinheiro = identificar_colunas(df_os)
            
            nova_linha = {col: "" for col in df_os.columns}
            if c_os: nova_linha[c_os] = str(num_os).strip()
            if c_data: nova_linha[c_data] = data_entrada.strftime('%Y-%m-%d')
            if c_cli: nova_linha[c_cli] = cliente
            if c_desc: nova_linha[c_desc] = servico
            if c_val: nova_linha[c_val] = val_formatado
            if c_pago: nova_linha[c_pago] = val_formatado if status in ["Concluída", "Paga"] else 0
            if c_pend: nova_linha[c_pend] = 0 if status in ["Concluída", "Paga"] else val_formatado
            if c_sit: nova_linha[c_sit] = str(status).strip()
            if c_tel: nova_linha[c_tel] = telefone

            if c_pix: nova_linha[c_pix] = val_formatado if forma_pagto == "Pix" else 0
            if c_cartao: nova_linha[c_cartao] = val_formatado if forma_pagto == "Cartão" else 0
            if c_boleto: nova_linha[c_boleto] = val_formatado if forma_pagto == "Boleto" else 0
            if c_dinheiro: nova_linha[c_dinheiro] = val_formatado if forma_pagto == "Dinheiro" else 0

            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_atualizado = pd.concat([df_os, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(worksheet="Ordens de Serviço", data=df_atualizado)
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
        c_os, c_data, c_cli, c_desc, c_val, c_pago, c_pend, c_sit, c_tel, _, _, _, _ = identificar_colunas(df_os)
        
        lista_os = df_os[c_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS para alterar ou excluir:", ["-- Selecione a OS --"] + list(lista_os))
        
        if os_para_editar != "-- Selecione a OS --":
            dados_os = df_os[df_os[c_os].astype(str) == os_para_editar].iloc[0]
            
            status_atual = str(dados_os.get(c_sit, "Em Aberto")).strip()
            opcoes_status = ["Concluída", "Em Aberto", "Parcial", "Paga", "Cancelado"]
            idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0

            with st.form("form_editar_os"):
                st.markdown(f"**Editando Ordem de Serviço:** `{os_para_editar}`")
                
                col1, col2 = st.columns(2)
                with col1:
                    novo_status = st.selectbox("Novo Status", opcoes_status, index=idx_status)
                
                with col2:
                    val_atual = str(dados_os[c_val]) if c_val and c_val in dados_os else "0,00"
                    novo_valor = st.text_input("Valor Total (R$)", value=val_atual)
                
                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações na OS")
                
                if btn_salvar_alt:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        idx = df_os[df_os[c_os].astype(str) == os_para_editar].index[0]
                        
                        if c_sit: df_os.at[idx, c_sit] = str(novo_status).strip()
                        if c_val: 
                            val_num = converter_para_numero(novo_valor)
                            df_os.at[idx, c_val] = val_num
                        
                        conn.update(worksheet="Ordens de Serviço", data=df_os.reset_index(drop=True))
                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada com sucesso!")
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
                    df_filtrado = df_os[df_os[c_os].astype(str) != os_para_editar].reset_index(drop=True)
                    
                    conn.update(worksheet="Ordens de Serviço", data=df_filtrado)
                    st.cache_data.clear()
                    st.success(f"🗑️ Ordem de Serviço **{os_para_editar}** excluída com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir OS no Google Sheets: {e}")
