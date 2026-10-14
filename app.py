# =============================================================================
# 1. DASHBOARD FINANCEIRO & FLUXO DE CAIXA MENSAL
# =============================================================================
if menu == "📈 Dashboard Financeiro":
    st.subheader("📈 Dashboard Executivo & Fluxo de Caixa")
    
    if not df_os.empty:
        col_os, col_data, col_cliente, col_desc, col_valor, col_status, col_pagto, col_tel = identificar_colunas(df_os)

        df_calc = df_os.copy()
        df_calc['VALOR_NUM'] = df_calc[col_valor].apply(converter_para_numero) if col_valor else 0.0

        # Tratar a coluna de data para criar os filtros mensais
        if col_data:
            df_calc['DATA_DT'] = pd.to_datetime(df_calc[col_data], errors='coerce', dayfirst=True)
            df_calc['MES_ANO'] = df_calc['DATA_DT'].dt.strftime('%m/%Y')
            
            # Lista de meses únicos ordenada
            meses_disponiveis = df_calc['MES_ANO'].dropna().unique().tolist()
            # Ordena do mais recente para o mais antigo se houver datas válidas
            try:
                meses_disponiveis.sort(key=lambda x: datetime.strptime(x, '%m/%Y'), reverse=True)
            except:
                pass
            
            opcoes_mes = ["📅 Todos os Meses (Geral)"] + meses_disponiveis
        else:
            opcoes_mes = ["📅 Todos os Meses (Geral)"]

        # ---------------------------------------------------------------------
        # SELETOR DE MÊS / PERÍODO
        # ---------------------------------------------------------------------
        col_filtro, _ = st.columns([2, 2])
        with col_filtro:
            mes_selecionado = st.selectbox("📆 **Filtrar Período do Dashboard:**", opcoes_mes)

        # Filtrar o dataframe se um mês específico for selecionado
        if mes_selecionado != "📅 Todos os Meses (Geral)" and col_data:
            df_filtrado = df_calc[df_calc['MES_ANO'] == mes_selecionado].copy()
            st.caption(f"Exibindo dados consolidados referentes a **{mes_selecionado}**")
        else:
            df_filtrado = df_calc.copy()
            st.caption("Exibindo dados acumulados de **todo o período**")

        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # CÁLCULOS DAS MÉTRICAS (BASEADO NO FILTRO)
        # ---------------------------------------------------------------------
        total_faturado = df_filtrado['VALOR_NUM'].sum()
        total_qtd_os = len(df_filtrado)

        if col_status:
            mask_pago = df_filtrado[col_status].astype(str).str.upper().str.contains("CONCLUÍDO|CONCLUIDO|PAGO|ENTREGUE", na=False)
            val_recebido = df_filtrado[mask_pago]['VALOR_NUM'].sum()
            val_aberto = df_filtrado[~mask_pago]['VALOR_NUM'].sum()
        else:
            val_recebido = total_faturado
            val_aberto = 0.0

        # CARDS SUPERIORES
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📋 Total OS Lançadas", total_qtd_os)
        m2.metric("💵 Faturamento Total", formatar_moeda_br(total_faturado))
        m3.metric("✅ Valor Recebido", formatar_moeda_br(val_recebido))
        m4.metric("⏳ Valor em Aberto", formatar_moeda_br(val_aberto))

        st.markdown("---")
        st.markdown(f"##### 💳 Faturamento Por Forma de Pagamento ({'Geral' if mes_selecionado == '📅 Todos os Meses (Geral)' else mes_selecionado})")

        # CÁLCULO POR FORMA DE PAGAMENTO (BASEADO NO FILTRO)
        if col_pagto:
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
            st.caption(f"ℹ️ Registros classificados como 'Cartão' sem especificação de Débito/Crédito neste período: **{formatar_moeda_br(cartao_generico)}**")

        st.markdown("---")
        st.markdown("##### 🗓️ Resumo Comparativo Mês a Mês")

        # TABELA DE RESUMO MÊS A MÊS (Visão Macro)
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
