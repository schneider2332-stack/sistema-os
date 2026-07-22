import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sistema de Gestão de OS", layout="wide")

st.title("🛠️ Sistema de Gestão de Ordens de Serviço (OS)")

SHEET_ID = "19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA"
GID_ORDENS_SERVICO = "417364075"

# =============================================================================
# CONEXÃO DIRETA COM O GOOGLE SHEETS
# =============================================================================
conn_gsheets = None
modo_escrita_ativo = False
mensagem_erro_escrita = ""

try:
    from streamlit_gsheets import GSheetsConnection
    conn_gsheets = st.connection("gsheets", type=GSheetsConnection)
    modo_escrita_ativo = True
except Exception as e:
    modo_escrita_ativo = False
    mensagem_erro_escrita = str(e)

# FUNÇÃO DE CONVERSÃO INTELIGENTE DE MOEDA (Suporta "1.300,00", "1300,00", "1300.00")
def converter_para_numero(valor):
    if pd.isna(valor) or valor is None:
        return 0.0
    
    val_str = str(valor).replace('R$', '').strip()
    if not val_str:
        return 0.0
        
    if ',' in val_str and '.' in val_str:
        if val_str.rfind(',') > val_str.rfind('.'):
            val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace(',', '')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
        
    try:
        return float(val_str)
    except:
        return 0.0

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

@st.cache_data(ttl=1)
def carregar_dados():
    global modo_escrita_ativo, mensagem_erro_escrita
    
    if modo_escrita_ativo and conn_gsheets is not None:
        try:
            df = conn_gsheets.read(ttl=0)
            df = df.dropna(how='all')
            return df, True, ""
        except Exception as e:
            modo_escrita_ativo = False
            mensagem_erro_escrita = str(e)
            
    try:
        url_csv = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ORDENS_SERVICO}"
        df_raw = pd.read_csv(url_csv, header=None)
        if df_raw.empty:
            return pd.DataFrame(), False, mensagem_erro_escrita
            
        linha_cabecalho = 0
        for idx, row in df_raw.iterrows():
            valores = [str(v).upper().strip() for v in row.values if pd.notna(v)]
            if any("OS" in item or "CLIENTE" in item or "SERVIÇO" in item or "VALOR" in item for item in valores):
                linha_cabecalho = idx
                break
                
        df = df_raw.iloc[linha_cabecalho + 1:].copy()
        df.columns = [str(v).strip() for v in df_raw.iloc[linha_cabecalho].values]
        df = df.dropna(how='all')
        df = df.loc[:, ~df.columns.astype(str).str.contains('^Unnamed|^nan', case=False)]
        df = df.reset_index(drop=True)
        return df, False, mensagem_erro_escrita
    except Exception as e_csv:
        return pd.DataFrame(), False, f"Erro CSV: {e_csv}"

df, modo_escrita_ativo, detalhe_erro = carregar_dados()

# =============================================================================
# MENU LATERAL DE NAVEGAÇÃO
# =============================================================================
menu = st.sidebar.radio(
    "📌 Navegação do Sistema",
    [
        "📈 Dashboard Financeiro & Fluxo de Caixa",
        "📊 OS Cadastradas (Lista)",
        "🔍 Consultar / Detalhar OS",
        "➕ Cadastrar Nova OS",
        "✏️ Alterar OS / Pagamento"
    ]
)

st.sidebar.markdown("---")
if modo_escrita_ativo:
    st.sidebar.success("🟢 Gravação Direta: ATIVA")
else:
    st.sidebar.warning("🟡 Modo de Leitura (Somente Leitura)")

# =============================================================================
# 1. DASHBOARD FINANCEIRO E FLUXO DE CAIXA MENSAL
# =============================================================================
if menu == "📈 Dashboard Financeiro & Fluxo de Caixa":
    st.subheader("📈 Painel de Indicadores & Fluxo de Caixa Mensal")
    
    if not df.empty:
        col_valor = next((c for c in df.columns if any(p in c.upper() for p in ["VALOR", "TOTAL", "PREÇO", "PRECO"])), None)
        col_status = next((c for c in df.columns if any(p in c.upper() for p in ["STATUS", "SITUAÇÃO", "SITUACAO"])), None)
        col_pagto = next((c for c in df.columns if any(p in c.upper() for p in ["PAG", "FORMA"])), None)
        col_data = next((c for c in df.columns if "DATA" in c.upper()), None)
        
        df['VALOR_CALC'] = df[col_valor].apply(converter_para_numero) if col_valor else 0.0
            
        if col_data:
            df['DATA_DT'] = pd.to_datetime(df[col_data], errors='coerce', dayfirst=True)
            df['ANO_MES'] = df['DATA_DT'].dt.strftime('%Y-%m').fillna("Sem Data")
        else:
            df['ANO_MES'] = "Sem Data"

        meses_unicos = sorted([m for m in df['ANO_MES'].dropna().unique() if m != "Sem Data"], reverse=True)
        if meses_unicos:
            st.sidebar.subheader("📅 Filtro de Período")
            meses_selecionados = st.sidebar.multiselect("Filtrar por Mês/Ano:", options=meses_unicos, default=meses_unicos)
            df_filtered = df[df['ANO_MES'].isin(meses_selecionados)] if meses_selecionados else df.copy()
        else:
            df_filtered = df.copy()

        fat_total = df_filtered['VALOR_CALC'].sum()
        
        if col_status:
            status_concluido = df_filtered[col_status].astype(str).str.upper().str.contains("PAGO|CONCLUÍDO|CONCLUIDO|ENTREGUE|FINALIZADO", na=False)
            val_recebido = df_filtered[status_concluido]['VALOR_CALC'].sum()
            val_aberto = df_filtered[~status_concluido]['VALOR_CALC'].sum()
        else:
            val_recebido = fat_total
            val_aberto = 0.0

        m1, m2, m3 = st.columns(3)
        m1.metric("💵 Faturamento Total", formatar_brl(fat_total))
        m2.metric("✅ Valor Recebido", formatar_brl(val_recebido))
        m3.metric("⏳ Valor em Aberto", formatar_brl(val_aberto))
        
        st.markdown("---")
        st.markdown("### 💳 Faturamento Por Forma de Pagamento")
        
        if col_pagto:
            pix_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("PIX", na=False)]['VALOR_CALC'].sum()
            cartao_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("CARTÃO|CARTAO|CRÉDITO|DÉBITO", na=False)]['VALOR_CALC'].sum()
            dinheiro_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("DINHEIRO|ESPÉCIE", na=False)]['VALOR_CALC'].sum()
            boleto_val = df_filtered[df_filtered[col_pagto].astype(str).str.upper().str.contains("BOLETO", na=False)]['VALOR_CALC'].sum()
        else:
            pix_val = cartao_val = dinheiro_val = boleto_val = 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📱 Pix", formatar_brl(pix_val))
        p2.metric("💳 Cartão", formatar_brl(cartao_val))
        p3.metric("💵 Dinheiro", formatar_brl(dinheiro_val))
        p4.metric("📄 Boleto", formatar_brl(boleto_val))
        
        st.markdown("---")
        st.markdown("### 🗓️ Fluxo de Caixa Mensal")
        df_fluxo = df[df['ANO_MES'] != "Sem Data"].groupby('ANO_MES')['VALOR_CALC'].sum().reset_index()
        df_fluxo.columns = ['Mês/Ano', 'Faturamento (R$)']
        
        if not df_fluxo.empty:
            st.bar_chart(df_fluxo.set_index('Mês/Ano'))
            st.dataframe(df_fluxo, use_container_width=True)
    else:
        st.warning("⚠️ Nenhum dado retornado da planilha.")

# =============================================================================
# 2. OS CADASTRADAS
# =============================================================================
elif menu == "📊 OS Cadastradas (Lista)":
    st.subheader("📋 Tabela Geral de Ordens de Serviço")
    if not df.empty:
        st.metric("Total de OSs Registradas", len(df))
        st.markdown("---")
        st.dataframe(df, use_container_width=True)

# =============================================================================
# 3. CONSULTAR OS
# =============================================================================
elif menu == "🔍 Consultar / Detalhar OS":
    st.subheader("🔍 Consultar Ordem de Serviço")
    if not df.empty:
        colunas = list(df.columns)
        coluna_os = next((c for c in colunas if "OS" in c.upper() or "NUMERO" in c.upper() or "Nº" in c.upper()), colunas[0])
        opcoes_os = df[coluna_os].dropna().astype(str).unique()
        os_escolhida = st.selectbox("Selecione a OS que deseja visualizar:", opcoes_os)
        
        if os_escolhida:
            dados = df[df[coluna_os].astype(str) == os_escolhida]
            st.dataframe(dados, use_container_width=True)

# =============================================================================
# 4. CADASTRAR NOVA OS
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Nova OS")
    
    col1, col2 = st.columns(2)
    
    with col1:
        num_os = st.text_input("Número da OS", value=f"OS-{len(df)+1:04d}")
        cliente = st.text_input("Nome do Cliente")
        telefone = st.text_input("Telefone / WhatsApp")
        servico = st.text_area("Descrição do Serviço / Defeito")
    
    with col2:
        forma_pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
        
        # CAMPO DE VALOR FLEXÍVEL (Aceita "1.300,00", "1300,00", "1300.00")
        valor_input = st.text_input("Valor Total (R$)", value="0,00", help="Pode digitar com ponto ou vírgula, ex: 1.300,00 ou 1300,00")
        valor_total_num = converter_para_numero(valor_input)
        
        # SEÇÃO DEDICADA PARA PAGAMENTO MISTO
        detalhe_pagto_str = forma_pagamento
        if forma_pagamento == "Pagamento Misto":
            st.markdown("##### 💵 Detalhamento do Pagamento Misto")
            v_pix = st.text_input("Valor no Pix (R$)", value="0,00")
            v_cartao = st.text_input("Valor no Cartão (R$)", value="0,00")
            v_dinheiro = st.text_input("Valor em Dinheiro (R$)", value="0,00")
            v_boleto = st.text_input("Valor em Boleto (R$)", value="0,00")
            
            n_pix = converter_para_numero(v_pix)
            n_cartao = converter_para_numero(v_cartao)
            n_dinheiro = converter_para_numero(v_dinheiro)
            n_boleto = converter_para_numero(v_boleto)
            
            soma_misto = n_pix + n_cartao + n_dinheiro + n_boleto
            if soma_misto > 0 and valor_total_num == 0.0:
                valor_total_num = soma_misto
                
            partes = []
            if n_pix > 0: partes.append(f"Pix: {formatar_brl(n_pix)}")
            if n_cartao > 0: partes.append(f"Cartão: {formatar_brl(n_cartao)}")
            if n_dinheiro > 0: partes.append(f"Dinheiro: {formatar_brl(n_dinheiro)}")
            if n_boleto > 0: partes.append(f"Boleto: {formatar_brl(n_boleto)}")
            
            if partes:
                detalhe_pagto_str = "Misto (" + " | ".join(partes) + ")"
        
        status = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue"])
        data_entrada = st.date_input("Data de Entrada", datetime.now()).strftime("%d/%m/%Y")

    btn_salvar = st.button("💾 Salvar OS no Google Sheets")
    
    if btn_salvar:
        valor_str_salvar = formatar_brl(valor_total_num)
        
        nova_os = pd.DataFrame([{
            "OS": num_os, "Cliente": cliente, "Telefone": telefone,
            "Serviço": servico, "Valor Total": valor_str_salvar,
            "Forma Pagamento": detalhe_pagto_str, "Status": status, "Data": data_entrada
        }])
        
        if modo_escrita_ativo and conn_gsheets is not None:
            try:
                df_atualizado = pd.concat([df, nova_os], ignore_index=True)
                conn_gsheets.update(data=df_atualizado)
                st.success(f"✅ OS {num_os} salva no Google Sheets com valor de {valor_str_salvar}!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar no Google Sheets: {e}")
        else:
            st.warning("⚠️ O sistema está em modo de leitura.")

# =============================================================================
# 5. ALTERAR OS / PAGAMENTO
# =============================================================================
elif menu == "✏️ Alterar OS / Pagamento":
    st.subheader("✏️ Alterar Status e Forma de Pagamento")
    
    if not df.empty:
        colunas = list(df.columns)
        coluna_os = next((c for c in colunas if "OS" in c.upper() or "NUMERO" in c.upper() or "Nº" in c.upper()), colunas[0])
        col_valor = next((c for c in df.columns if any(p in c.upper() for p in ["VALOR", "TOTAL", "PREÇO", "PRECO"])), None)
        
        opcoes_os = df[coluna_os].dropna().astype(str).unique()
        os_para_editar = st.selectbox("Selecione a OS para alterar:", opcoes_os)
        
        if os_para_editar:
            idx = df[df[coluna_os].astype(str) == os_para_editar].index[0]
            val_atual = converter_para_numero(df.loc[idx, col_valor]) if col_valor else 0.0
            
            col1, col2 = st.columns(2)
            with col1:
                novo_status = st.selectbox("Alterar Status", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue", "Cancelado"])
                nova_forma_pagto = st.selectbox("Alterar Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
            
            with col2:
                novo_valor_input = st.text_input("Atualizar Valor Total (R$)", value=f"{val_atual:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','))
                novo_valor_num = converter_para_numero(novo_valor_input)
                
                detalhe_pagto_edit = nova_forma_pagto
                if nova_forma_pagto == "Pagamento Misto":
                    st.markdown("##### 💵 Detalhar Pagamento Misto")
                    ev_pix = st.text_input("Parte no Pix (R$)", value="0,00")
                    ev_cartao = st.text_input("Parte no Cartão (R$)", value="0,00")
                    ev_dinheiro = st.text_input("Parte em Dinheiro (R$)", value="0,00")
                    
                    en_pix = converter_para_numero(ev_pix)
                    en_cartao = converter_para_numero(ev_cartao)
                    en_dinheiro = converter_para_numero(ev_dinheiro)
                    
                    partes_e = []
                    if en_pix > 0: partes_e.append(f"Pix: {formatar_brl(en_pix)}")
                    if en_cartao > 0: partes_e.append(f"Cartão: {formatar_brl(en_cartao)}")
                    if en_dinheiro > 0: partes_e.append(f"Dinheiro: {formatar_brl(en_dinheiro)}")
                    
                    if partes_e:
                        detalhe_pagto_edit = "Misto (" + " | ".join(partes_e) + ")"

            btn_atualizar = st.button("🔄 Atualizar no Google Sheets")
            
            if btn_atualizar:
                if modo_escrita_ativo and conn_gsheets is not None:
                    try:
                        valor_str_alt = formatar_brl(novo_valor_num)
                        df.loc[idx, "Status"] = novo_status
                        df.loc[idx, "Forma Pagamento"] = detalhe_pagto_edit
                        if col_valor:
                            df.loc[idx, col_valor] = valor_str_alt
                            
                        conn_gsheets.update(data=df)
                        st.success(f"✅ OS {os_para_editar} atualizada no Google Sheets!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar no Google Sheets: {e}")
                else:
                    st.warning("⚠️ O sistema está em modo de leitura.")
