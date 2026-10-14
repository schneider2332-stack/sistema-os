import streamlit as st
import pandas as pd
from datetime import datetime
import re
from streamlit_gsheets import GSheetsConnection

# =============================================================================
# 1. CONFIGURAÇÃO INICIAL E CONEXÃO
# =============================================================================
st.set_page_config(page_title="Sistema de OS & Gestão Financeira", layout="wide")

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
    except Exception:
        # Fallback de leitura CSV público caso ocorra oscilação nas credenciais
        try:
            url_csv = "https://docs.google.com/spreadsheets/d/19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA/export?format=csv&gid=417364075"
            df_csv = pd.read_csv(url_csv)
            df_csv = df_csv.dropna(how='all')
            return df_csv
        except Exception:
            return pd.DataFrame()

# Formatação monetária padrão brasileiro (R$ 1.300,00)
def formatar_moeda_br(valor_float):
    return f"R$ {valor_float:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

# Conversão monetária segura (Ex: R$ 1.300,00 -> 1300.0)
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

# Decomposição exata de pagamentos puros e mistos (aplicada apenas para valores recebidos)
def extrair_totais_pagamento(df_escopo, col_pagto, col_val_num):
    totais = {
        'pix': 0.0,
        'credito': 0.0,
        'debito': 0.0,
        'dinheiro': 0.0,
        'boleto': 0.0,
        'cartao_generico': 0.0
    }
    
    if not col_pagto or df_escopo.empty:
        return totais

    for _, row in df_escopo.iterrows():
        forma = str(row.get(col_pagto, '')).strip()
        val_total = float(row.get(col_val_num, 0.0))
        
        if "MISTO" in forma.upper():
            partes = forma.split('|')
            for parte in partes:
                p_upper = parte.upper()
                match = re.search(r'R\$\s*([\d\.,]+)', parte, re.IGNORECASE) or re.search(r'([\d\.,]+)', parte)
                val_parcial = converter_para_numero(match.group(1)) if match else 0.0
                
                if "PIX" in p_upper:
                    totais['pix'] += val_parcial
                elif "CRÉDITO" in p_upper or "CREDITO" in p_upper:
                    totais['credito'] += val_parcial
                elif "DÉBITO" in p_upper or "DEBITO" in p_upper:
                    totais['debito'] += val_parcial
                elif "DINHEIRO" in p_upper or "ESPÉCIE" in p_upper or "ESPECIE" in p_upper:
                    totais['dinheiro'] += val_parcial
                elif "BOLETO" in p_upper:
                    totais['boleto'] += val_parcial
                elif "CARTÃO" in p_upper or "CARTAO" in p_upper:
                    totais['cartao_generico'] += val_parcial
        else:
            f_upper = forma.upper()
            if "PIX" in f_upper:
                totais['pix'] += val_total
            elif "CRÉDITO" in f_upper or "CREDITO" in f_upper:
                totais['credito'] += val_total
            elif "DÉBITO" in f_upper or "DEBITO" in f_upper:
                totais['debito'] += val_total
            elif "DINHEIRO" in f_upper or "ESPÉCIE" in f_upper or "ESPECIE" in f_upper:
                totais['dinheiro'] += val_total
            elif "BOLETO" in f_upper:
                totais['boleto'] += val_total
            elif "CARTÃO" in f_upper or "CARTAO" in f_upper:
                totais['cartao_generico'] += val_total

    return totais

df_os = carregar_dados()

# Identificação das colunas da planilha
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

        # Tratamento seguro de datas
        if col_data:
            df_calc['DATA_DT'] = pd.to_datetime(df_calc[col_data], errors='coerce', dayfirst=True)
            df_calc['MES_ANO'] = df_calc['DATA_DT'].dt.strftime('%m/%Y')
            
            meses_disponiveis = df_calc['MES_ANO'].dropna().unique().tolist()
            try:
                meses_disponiveis.sort(key=lambda x: datetime.strptime(x, '%m/%Y'), reverse=True)
            except Exception:
                pass
            
            opcoes_mes = ["📅 Todos os Meses (Geral)"] + meses_disponiveis
        else:
            opcoes_mes = ["📅 Todos os Meses (Geral)"]

        # Filtro de período
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

        # ---------------------------------------------------------------------
        # CÁLCULOS DAS MÉTRICAS GERAIS E STATUS
        # ---------------------------------------------------------------------
        total_faturado = df_filtrado['VALOR_NUM'].sum()
        total_qtd_os = len(df_filtrado)

        if col_status:
            # Identifica OS quitadas/concluídas/entregues
            mask_pago = df_filtrado[col_status].astype(str).str.upper().str.contains("CONCLUÍDO|CONCLUIDO|PAGO|ENTREGUE", na=False)
            df_recebidos = df_filtrado[mask_pago].copy()
            
            val_recebido = df_recebidos['VALOR_NUM'].sum()
            val_aberto = df_filtrado[~mask_pago]['VALOR_NUM'].sum()
        else:
            df_recebidos = df_filtrado.copy()
            val_recebido = total_faturado
            val_aberto = 0.0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Total OS Lançadas", total_qtd_os)
        m2.metric("💵 Faturamento Total", formatar_moeda_br(total_faturado))
        m3.metric("✅ Valor Recebido", formatar_moeda_br(val_recebido))
        m4.metric("⏳ Valor em Aberto", formatar_moeda_br(val_aberto))

        st.markdown("---")
        st.markdown(f"##### 💳 Faturamento Efetivado por Forma de Pagamento ({'Geral' if mes_selecionado == '📅 Todos os Meses (Geral)' else mes_selecionado})")
        st.caption("ℹ️ *Apenas OS com status **Concluído**, **Entregue** ou **Pago** entram na soma abaixo.*")

        # CÁLCULO EXCLUSIVO COM BASE NAS OS CONCLUÍDAS/ENTREGUES
        totais_pag = extrair_totais_pagamento(df_recebidos, col_pagto, 'VALOR_NUM')

        p1, p2, p3, p4, p5 = st.columns(5)
        p1.metric("📱 Pix (Recebido)", formatar_moeda_br(totais_pag['pix']))
        p2.metric("💳 Cartão Crédito", formatar_moeda_br(totais_pag['credito']))
        p3.metric("💳 Cartão Débito", formatar_moeda_br(totais_pag['debito']))
        p4.metric("💵 Dinheiro", formatar_moeda_br(totais_pag['dinheiro']))
        p5.metric("📄 Boleto", formatar_moeda_br(totais_pag['boleto']))

        if totais_pag['cartao_generico'] > 0:
            st.caption(f"ℹ️ Registros classificados como 'Cartão' genérico recebidos: **{formatar_moeda_br(totais_pag['cartao_generico'])}**")

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
            st.info("Coluna de Data não identificada.")
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
            if c_data: nova_linha[c_data] = data_entrada.strftime('%d/%m/%Y')
            if c_cli: nova_linha[c_cli] = cliente
            if c_desc: nova_linha[c_desc] = servico
            if c_val: nova_linha[c_val] = formatar_moeda_br(val_formatado)
            if c_sit: nova_linha[c_sit] = str(status).strip()
            if c_pag: nova_linha[c_pag] = detalhe_pagto
            if c_tel: nova_linha[c_tel] = telefone

            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                df_atualizado = pd.concat([df_os, pd.DataFrame([nova_linha])], ignore_index=True)
                conn.update(data=df_atualizado)
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
        os_para_editar = st.selectbox("Selecione a OS para alterar ou excluir:", ["-- Selecione a OS --"] + list(lista_os))
        
        if os_para_editar != "-- Selecione a OS --":
            dados_os = df_os[df_os[col_os].astype(str) == os_para_editar].iloc[0]
            
            status_atual = str(dados_os.get(col_sit, "Aberto")).strip()
            opcoes_status = ["Aberto", "Em Andamento", "Concluído", "Entregue", "Cancelado"]
            idx_status = opcoes_status.index(status_atual) if status_atual in opcoes_status else 0

            forma_atual = str(dados_os.get(col_pag, "Pix")).strip()
            opcoes_forma = ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"]
            idx_forma = opcoes_forma.index(forma_atual) if forma_atual in opcoes_forma else (5 if "MISTO" in forma_atual.upper() else 0)

            with st.form("form_editar_os"):
                st.markdown(f"**Editando Ordem de Serviço:** `{os_para_editar}`")
                
                col1, col2 = st.columns(2)
                with col1:
                    novo_status = st.selectbox("Novo Status", opcoes_status, index=idx_status)
                    nova_forma = st.selectbox("Forma de Pagamento", opcoes_forma, index=idx_forma)
                
                with col2:
                    val_atual = str(dados_os[col_val]) if col_val and col_val in dados_os else "0,00"
                    novo_valor = st.text_input("Valor Total (R$)", value=val_atual)

                detalhe_pagto_edit = nova_forma
                if nova_forma == "Pagamento Misto":
                    st.info("ℹ️ Para registrar divisão de valores no pagamento misto, preencha o detalhamento abaixo (ex: `Pix: R$ 500,00 | Boleto: R$ 500,00`):")
                    valor_misto_texto = st.text_input("Detalhamento Misto", value=forma_atual if "MISTO" in forma_atual.upper() else "Misto (Pix: R$ 0,00 | Boleto: R$ 0,00)")
                    detalhe_pagto_edit = valor_misto_texto
                
                btn_salvar_alt = st.form_submit_button("💾 Salvar Alterações na OS")
                
                if btn_salvar_alt:
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        idx = df_os[df_os[col_os].astype(str) == os_para_editar].index[0]
                        
                        if col_sit: df_os.at[idx, col_sit] = str(novo_status).strip()
                        if col_pag: df_os.at[idx, col_pag] = detalhe_pagto_edit
                        if col_val: 
                            val_num = converter_para_numero(novo_valor)
                            df_os.at[idx, col_val] = formatar_moeda_br(val_num)
                        
                        conn.update(data=df_os)
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
                    df_filtrado = df_os[df_os[col_os].astype(str) != os_para_editar]
                    
                    conn.update(data=df_filtrado)
                    st.cache_data.clear()
                    st.success(f"🗑️ Ordem de Serviço **{os_para_editar}** excluída com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao excluir OS no Google Sheets: {e}")
