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
        # header=3 faz a leitura considerar a 4ª linha da folha como cabeçalho
        df = conn.read(worksheet=NOME_ABA, header=3, ttl=0)
        if df is not None and not df.empty:
            df = df.dropna(how='all')
            df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
            return df
        return pd.DataFrame()
    except Exception:
        try:
            url_csv = "https://docs.google.com/spreadsheets/d/1IHmxCEP3VdPK7eKR3aoKTsDb-3z6u5auIqlhZoGtRnU/export?format=csv&gid=318068232"
            df_csv = pd.read_csv(url_csv, skiprows=3)
            df_csv = df_csv.dropna(how='all')
            return df_csv
        except Exception:
            return pd.DataFrame()

# Função para formatação monetária padrão brasileiro (R$ 1.300,00)
def formatar_moeda_br(valor_float):
    return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Função segura para conversão monetária (Ex: R$ 1.300,00 -> 1300.0)
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

# Mapeamento dinâmico e inteligente das colunas da folha de cálculo
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
            # Converte tanto datas ISO (2026-07-04) como brasileiras (04/07/2026)
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

        # Seletor de Período
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
            mask_pago = df_filtrado[col_status].astype(str).str.upper().str.contains("CONCLUÍDO|CONCLUIDO|PAGO|ENTREGUE", na=False)
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

        # Verifica se as formas de pagamento estão divididas em colunas próprias
        col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
        col_cartao = next((c for c in df_os.columns if "CART" in str(c).upper()), None)
        col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
        col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

        if col_pix or col_cartao or col_boleto or col_dinheiro:
            pix = df_filtrado[col_pix].apply(converter_para_numero).sum() if col_pix else 0.0
            credito = df_filtrado[col_cartao].apply(converter_para_numero).sum() if col_cartao else 0.0
            debito = 0.0
            cartao_generico = 0.0
            dinheiro = df_filtrado[col_dinheiro].apply(converter_para_numero).sum() if col_dinheiro else 0.0
            boleto = df_filtrado[col_boleto].apply(converter_para_numero).sum() if col_boleto else 0.0
        elif col_pagto:
            pix = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("PIX", na=False)]['VALOR_NUM'].sum()
            credito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("CRÉDITO|CREDITO", na=False)]['VALOR_NUM'].sum()
            debito = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("DÉBITO|DEBITO", na=False)]['VALOR_NUM'].sum()
            
            cartao_generico = df_filtrado[
                df_filtrado[col_pagto].astype(str).str.upper().str.contains("CARTÃO|CARTAO", na=False) & 
                ~df_filtrado[col_pagto].astype(str).str.upper().str.contains("CRÉDITO|CREDITO|DÉBITO|DEBITO", na=False)
            ]['VALOR_NUM'].sum()

            dinheiro = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("DINHEIRO|ESPÉCIE", na=False)]['VALOR_NUM'].sum()
            boleto = df_filtrado[df_filtrado[col_pagto].astype(str).str.upper().str.contains("BOLETO", na=False)]['VALOR_NUM'].sum()
        else:
            pix = credito = debito = cartao_generico = dinheiro = boleto = 0.0

        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("📱 Pix", formatar_moeda_br(pix))
        p2.metric("💳 Cartão Crédito", formatar_moeda_br(credito))
        p3.metric("💳 Cartão Débito", formatar_moeda_br(debito))
        p4.metric("💵 Dinheiro", formatar_moeda_br(dinheiro))
        p5.metric("📄 Boleto", formatar_moeda_br(boleto))

        if cartao_generico > 0:
            st.caption(f"ℹ️ Registos classificados como 'Cartão' sem especificação de Débito/Crédito: **{formatar_moeda_br(cartao_generico)}**")

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
                st.info("Nenhuma OS com data válida encontrada para o resumo mensal.")
        else:
            st.info("Coluna de Data não identificada para o resumo mensal.")
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
# 4. CADASTRAR NOVA OS
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
        
        forma_pagto = st.selectbox(
            "Forma de Pagamento", 
            ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
        )
        
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
            # Formato de data idêntico ao da folha (YYYY-MM-DD)
            if c_data: nova_linha[c_data] = data_entrada.strftime('%Y-%m-%d')
            if c_cli: nova_linha[c_cli] = cliente
            if c_desc: nova_linha[c_desc] = servico
            if c_val: nova_linha[c_val] = formatar_moeda_br(val_formatado)
            if c_sit: nova_linha[c_sit] = str(status).strip()
            if c_pag: nova_linha[c_pag] = detalhe_pagto
            if c_tel: nova_linha[c_tel] = telefone

            # Distribuição nas colunas financeiras individuais se existirem na folha
            col_pix = next((c for c in df_os.columns if "PIX" in str(c).upper()), None)
            col_cartao = next((c for c in df_os.columns if "CART" in str(c).upper()), None)
            col_boleto = next((c for c in df_os.columns if "BOLETO" in str(c).upper()), None)
            col_dinheiro = next((c for c in df_os.columns if "DINHEIRO" in str(c).upper() or "ESPÉCIE" in str(c).upper()), None)

            if "PIX" in forma_pagto.upper() and col_pix:
                nova_linha[col_pix] = formatar_moeda_br(val_formatado)
            elif "CART" in forma_pagto.upper() and col_cartao:
                nova_linha[col_cartao] = formatar_moeda_br(val_formatado)
            elif "BOLETO" in forma_pagto.upper() and col_boleto:
                nova_linha[col_boleto] = formatar_moeda_br(val_formatado)
            elif "DINHEIRO" in forma_pagto.upper() and col_dinheiro:
                nova_linha[col_dinheiro] = formatar_moeda_br(val_formatado)

            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_atualizado = pd.concat([df_os, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(worksheet=NOME_ABA, data=df_atualizado)
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
                st.markdown(f"**A editar Ordem de Serviço:** `{os_para_editar}`")
                
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
                        
                        if col_val: 
                            val_num = converter_para_numero(novo_valor)
                            df_os.at[idx, col_val] = formatar_moeda_br(val_num)
                        
                        conn.update(worksheet=NOME_ABA, data=df_os)
                        st.cache_data.clear()
                        st.success(f"✅ OS {os_para_editar} atualizada para **{novo_status}** com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao alterar OS no Google Sheets: {e}")

            # -----------------------------------------------------------------
            # ZONA DE PERIGO: EXCLUSÃO DE OS
            # -----------------------------------------------------------------
            st.markdown("---")
            st.warning("⚠️ **Zona de Perigo: Exclusão de Registo**")
            
            confirmar_exclusao = st.checkbox(f"Confirmo que pretendo apagar permanentemente a **{os_para_editar}**")
            
            if st.button("🗑️ Excluir esta OS", type="primary", disabled=not confirmar_exclusao):
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_filtrado = df_os[df_os[col_os].astype(str) != os_para_editar]
                    
                    conn.update(worksheet=NOME_ABA, data=df_filtrado)
                    st.cache_data.clear()
                    st.success(f"🗑️ Ordem de Serviço **{os_para_editar}** excluída com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir OS no Google Sheets: {e}")
