import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Sistema de Gestão de OS", layout="wide")

st.title("🛠️ Sistema de Gestão de Ordens de Serviço (OS)")

SHEET_ID = "19Y3_TJGk0svt-0LAJdQ11MGBsLbAzqbE19kRDChP9tA"
GID_ORDENS_SERVICO = "417364075"
NOME_ABA_PLANILHA = "OS"  # Nome da guia na planilha

# =============================================================================
# CONEXÃO DIRETA COM O GOOGLE SHEETS
# =============================================================================
conn_gsheets = None
modo_escrita_ativo = False

try:
    from streamlit_gsheets import GSheetsConnection
    conn_gsheets = st.connection("gsheets", type=GSheetsConnection)
    modo_escrita_ativo = True
except Exception as e:
    modo_escrita_ativo = False

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
    # 1. Tenta carregar via GSheets Connection (Escrita Habilitada)
    if modo_escrita_ativo and conn_gsheets is not None:
        try:
            df = conn_gsheets.read(ttl=0)
            df = df.dropna(how='all')
            return df, True
        except Exception:
            pass

    # 2. Fallback: Leitura via CSV Público
    try:
        url_csv = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID_ORDENS_SERVICO}"
        df_raw = pd.read_csv(url_csv, header=None)
        if df_raw.empty:
            return pd.DataFrame(), False
            
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
        return df, False
    except Exception:
        return pd.DataFrame(), False

df, modo_escrita_ativo = carregar_dados()

# Dicionário para formatar nomes dos meses em Português
MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# =============================================================================
# MENU LATERAL
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
    st.sidebar.success("🟢 Gravação Direta no Sheets: ATIVA")
else:
    st.sidebar.warning("🟡 Modo de Leitura (Verifique os Secrets)")

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

        # MÉTRICAS PRINCIPAIS
        total_os_qtd = len(df)
        fat_total = df['VALOR_CALC'].sum()
        
        if col_status:
            status_concluido = df[col_status].astype(str).str.upper().str.contains("PAGO|CONCLUÍDO|CONCLUIDO|ENTREGUE|FINALIZADO", na=False)
            val_recebido = df[status_concluido]['VALOR_CALC'].sum()
            val_aberto = df[~status_concluido]['VALOR_CALC'].sum()
        else:
            val_recebido = fat_total
            val_aberto = 0.0

        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("📋 Total de OS Lançadas", f"{total_os_qtd}")
        col_m2.metric("💵 Faturamento Total", formatar_brl(fat_total))
        col_m3.metric("✅ Valor Recebido", formatar_brl(val_recebido))
        col_m4.metric("⏳ Valor em Aberto", formatar_brl(val_aberto))
        
        st.markdown("---")
        st.markdown("### 💳 Faturamento Por Forma de Pagamento")
        
        if col_pagto:
            pix_val = df[df[col_pagto].astype(str).str.upper().str.contains("PIX", na=False)]['VALOR_CALC'].sum()
            cartao_val = df[df[col_pagto].astype(str).str.upper().str.contains("CARTÃO|CARTAO|CRÉDITO|DÉBITO", na=False)]['VALOR_CALC'].sum()
            dinheiro_val = df[df[col_pagto].astype(str).str.upper().str.contains("DINHEIRO|ESPÉCIE", na=False)]['VALOR_CALC'].sum()
            boleto_val = df[df[col_pagto].astype(str).str.upper().str.contains("BOLETO", na=False)]['VALOR_CALC'].sum()
        else:
            pix_val = cartao_val = dinheiro_val = boleto_val = 0.0

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("📱 Pix", formatar_brl(pix_val))
        p2.metric("💳 Cartão", formatar_brl(cartao_val))
        p3.metric("💵 Dinheiro", formatar_brl(dinheiro_val))
        p4.metric("📄 Boleto", formatar_brl(boleto_val))
        
        st.markdown("---")
        # FLUXO MÊS A MÊS EM TABELA (Ex: Julho/2026, Agosto/2026)
        st.markdown("### 🗓️ Fluxo de Caixa Mês a Mês")
        
        if col_data and not df.empty:
            df_valido = df.dropna(subset=['DATA_DT']).copy()
            if not df_valido.empty:
                df_valido['Ano'] = df_valido['DATA_DT'].dt.year.astype(int)
                df_valido['Mes_Num'] = df_valido['DATA_DT'].dt.month.astype(int)
                
                fluxo = df_valido.groupby(['Ano', 'Mes_Num']).agg(
                    Qtd_OS=('VALOR_CALC', 'count'),
                    Total_Faturado=('VALOR_CALC', 'sum')
                ).reset_index().sort_values(by=['Ano', 'Mes_Num'], ascending=True)
                
                fluxo['Mês / Ano'] = fluxo.apply(lambda r: f"{MESES_PT.get(r['Mes_Num'], r['Mes_Num'])}/{r['Ano']}", axis=1)
                fluxo['Faturamento Total'] = fluxo['Total_Faturado'].apply(formatar_brl)
                
                tabela_exibicao = fluxo[['Mês / Ano', 'Qtd_OS', 'Faturamento Total']].rename(
                    columns={'Qtd_OS': 'Qtd. de OS Lançadas'}
                )
                
                st.dataframe(tabela_exibicao, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma data válida para agrupar o fluxo mensal.")
    else:
        st.warning("⚠️ Nenhum dado retornado da planilha.")

# =============================================================================
# 2. OS CADASTRADAS (LISTA COMPLETA)
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
# 4. CADASTRAR NOVA OS (COM LIMPEZA AUTOMÁTICA)
# =============================================================================
elif menu == "➕ Cadastrar Nova OS":
    st.subheader("➕ Formulário para Nova OS")
    
    # clear_on_submit=True garante que os campos esvaziem após o envio!
    with st.form("form_nova_os", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            num_os = st.text_input("Número da OS", value=f"OS-{len(df)+1:04d}")
            cliente = st.text_input("Nome do Cliente")
            telefone = st.text_input("Telefone / WhatsApp")
            servico = st.text_area("Descrição do Serviço / Defeito")
        
        with col2:
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
            valor_input = st.text_input("Valor Total (R$)", value="0,00", help="Exemplo: 1.300,00 ou 1300,00")
            
            st.markdown("##### 💵 Preencha se for Pagamento Misto:")
            v_pix = st.text_input("Valor no Pix (R$)", value="0,00")
            v_cartao = st.text_input("Valor no Cartão (R$)", value="0,00")
            v_dinheiro = st.text_input("Valor em Dinheiro (R$)", value="0,00")
            v_boleto = st.text_input("Valor em Boleto (R$)", value="0,00")
            
            status = st.selectbox("Status Inicial", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue"])
            data_entrada = st.date_input("Data de Entrada", datetime.now()).strftime("%d/%m/%Y")
            
        btn_salvar = st.form_submit_button("💾 Salvar OS no Google Sheets")
        
        if btn_salvar:
            valor_num = converter_para_numero(valor_input)
            
            # Trata Pagamento Misto
            detalhe_pagto_str = forma_pagamento
            if forma_pagamento == "Pagamento Misto":
                npix = converter_para_numero(v_pix)
                ncartao = converter_para_numero(v_cartao)
                ndinheiro = converter_para_numero(v_dinheiro)
                nboleto = converter_para_numero(v_boleto)
                
                soma_misto = npix + ncartao + ndinheiro + nboleto
                if soma_misto > 0 and valor_num == 0.0:
                    valor_num = soma_misto
                    
                partes = []
                if npix > 0: partes.append(f"Pix: {formatar_brl(npix)}")
                if ncartao > 0: partes.append(f"Cartão: {formatar_brl(ncartao)}")
                if ndinheiro > 0: partes.append(f"Dinheiro: {formatar_brl(ndinheiro)}")
                if nboleto > 0: partes.append(f"Boleto: {formatar_brl(nboleto)}")
                
                if partes:
                    detalhe_pagto_str = "Misto (" + " | ".join(partes) + ")"

            valor_str_salvar = formatar_brl(valor_num)
            
            nova_os = pd.DataFrame([{
                "OS": num_os, "Cliente": cliente, "Telefone": telefone,
                "Serviço": servico, "Valor Total": valor_str_salvar,
                "Forma Pagamento": detalhe_pagto_str, "Status": status, "Data": data_entrada
            }])
            
            if modo_escrita_ativo and conn_gsheets is not None:
                try:
                    df_atualizado = pd.concat([df, nova_os], ignore_index=True)
                    conn_gsheets.update(data=df_atualizado)
                    st.success(f"✅ OS {num_os} salva no Google Sheets com sucesso!")
                    st.cache_data.clear()
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
            
            with st.form("form_editar_os"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_status = st.selectbox("Alterar Status", ["Aberto", "Em Andamento", "Aguardando Peça", "Concluído", "Entregue", "Cancelado"])
                    nova_forma_pagto = st.selectbox("Alterar Forma de Pagamento", ["Pix", "Cartão de Crédito", "Cartão de Débito", "Dinheiro", "Boleto", "Pagamento Misto"])
                
                with col2:
                    novo_valor_input = st.text_input("Atualizar Valor Total (R$)", value=f"{val_atual:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ','))
                    
                    st.markdown("##### 💵 Preencha se for Pagamento Misto:")
                    ev_pix = st.text_input("Parte no Pix (R$)", value="0,00")
                    ev_cartao = st.text_input("Parte no Cartão (R$)", value="0,00")
                    ev_dinheiro = st.text_input("Parte em Dinheiro (R$)", value="0,00")

                btn_atualizar = st.form_submit_button("🔄 Atualizar no Google Sheets")
                
                if btn_atualizar:
                    novo_valor_num = converter_para_numero(novo_valor_input)
                    detalhe_pagto_edit = nova_forma_pagto
                    
                    if nova_forma_pagto == "Pagamento Misto":
                        en_pix = converter_para_numero(ev_pix)
                        en_cartao = converter_para_numero(ev_cartao)
                        en_dinheiro = converter_para_numero(ev_dinheiro)
                        
                        partes_e = []
                        if en_pix > 0: partes_e.append(f"Pix: {formatar_brl(en_pix)}")
                        if en_cartao > 0: partes_e.append(f"Cartão: {formatar_brl(en_cartao)}")
                        if en_dinheiro > 0: partes_e.append(f"Dinheiro: {formatar_brl(en_dinheiro)}")
                        
                        if partes_e:
                            detalhe_pagto_edit = "Misto (" + " | ".join(partes_e) + ")"

                    if modo_escrita_ativo and conn_gsheets is not None:
                        try:
                            valor_str_alt = formatar_brl(novo_valor_num)
                            df.loc[idx, "Status"] = novo_status
                            df.loc[idx, "Forma Pagamento"] = detalhe_pagto_edit
                            if col_valor:
                                df.loc[idx, col_valor] = valor_str_alt
                                
                            conn_gsheets.update(data=df)
                            st.success(f"✅ OS {os_para_editar} atualizada no Google Sheets com sucesso!")
                            st.cache_data.clear()
                        except Exception as e:
                            st.error(f"Erro ao atualizar no Google Sheets: {e}")
                    else:
                        st.warning("⚠️ O sistema está em modo de leitura.")
