import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import db

# Configuração da página
st.set_page_config(page_title="Descarte Consciente", layout="wide", initial_sidebar_state="expanded")

# Inicializa o banco de dados
db.init_db()

# Custom CSS para botões maiores em telas menores
st.markdown("""
    <style>
    .stButton>button {
        height: 3em;
        font-size: 18px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Navegação lateral
st.sidebar.title("Descarte Consciente")
menu = st.sidebar.radio("Navegação", [
    "1. Coleta em Campo", 
    "2. Classificação de Medicamentos", 
    "3. Pesagem Mensal", 
    "4. Relatórios e Exportação"
])

def calcular_situacao(mes, ano, data_coleta):
    """
    Medicamento vence no último dia do mês/ano indicado.
    Consideramos vencido se o primeiro dia do próximo mês for <= data da coleta.
    Simplificando:
    Vencido se ano < data_coleta.year ou (ano == data_coleta.year and mes < data_coleta.month)
    """
    if ano < data_coleta.year:
        return "Vencido"
    elif ano == data_coleta.year and mes < data_coleta.month:
        return "Vencido"
    else:
        return "Dentro da validade"

if menu == "1. Coleta em Campo":
    st.header("📋 1. Coleta em Campo")
    st.info("Registre rapidamente os medicamentos encontrados durante a triagem. Adicione múltiplas validades reaproveitando o nome e a forma já preenchidos.")
    
    data_coleta = st.date_input("Data da Coleta", value=datetime.today())

    nomes_db = db.get_all_nomes()
    formas_db = db.get_all_formas()

    col_nome, col_forma = st.columns(2)
    
    with col_nome:
        opcoes_nome = ["+ Adicionar Novo Medicamento..."] + nomes_db
        escolha_nome = st.selectbox("Nome do Medicamento", opcoes_nome, key="sel_nome")
        if escolha_nome == "+ Adicionar Novo Medicamento...":
            nome_final = st.text_input("Digite o nome do novo medicamento", key="txt_nome")
        else:
            nome_final = escolha_nome

    with col_forma:
        opcoes_forma = ["+ Adicionar Nova Forma..."] + formas_db
        escolha_forma = st.selectbox("Forma Farmacêutica", opcoes_forma, key="sel_forma")
        estado_fisico_novo = None
        if escolha_forma == "+ Adicionar Nova Forma...":
            forma_final = st.text_input("Digite a nova forma farmacêutica", key="txt_forma")
            estado_fisico_novo = st.radio("Qual o estado físico?", ["Sólido", "Líquido", "Semissólido"], horizontal=True)
        else:
            forma_final = escolha_forma

    st.markdown("---")
    st.subheader("📆 Adicionar Validade")
    
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        mes_val = st.number_input("Mês da Validade", min_value=1, max_value=12, value=1, step=1)
    with col_v2:
        ano_val = st.number_input("Ano da Validade", min_value=1990, max_value=2100, value=datetime.today().year, step=1)
    
    legivel = st.checkbox("Validade ilegível ou não identificada")

    if legivel:
        sit_calc = "Não foi possível verificar"
        val_str = "Não identificada"
    else:
        sit_calc = calcular_situacao(mes_val, ano_val, data_coleta)
        val_str = f"{mes_val:02d}/{ano_val}"

    st.info(f"Situação calculada automaticamente: **{sit_calc}**")
    
    override = st.checkbox("Corrigir situação manualmente?")
    if override:
        sit_final = st.selectbox("Selecione a situação correta", ["Vencido", "Dentro da validade", "Não foi possível verificar"], index=["Vencido", "Dentro da validade", "Não foi possível verificar"].index(sit_calc))
    else:
        sit_final = sit_calc

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("➕ Adicionar Esta Unidade", type="primary", use_container_width=True):
            if not nome_final or not forma_final:
                st.error("Por favor, preencha o Nome e a Forma Farmacêutica!")
            else:
                # Se for forma nova, adiciona no BD com o estado físico
                if escolha_forma == "+ Adicionar Nova Forma...":
                    db.add_forma(forma_final, estado_fisico_novo)
                
                db.insert_coleta(data_coleta, nome_final, forma_final, val_str, sit_final)
                st.success(f"✅ Registrado: 1 unidade de **{nome_final}** - Vencimento: {val_str} ({sit_final})")

    with col_btn2:
        if st.button("🔄 Concluir este Medicamento e ir p/ o próximo", use_container_width=True):
            # Limpa as seleções limpando o session_state e forçando reload
            chaves = ['sel_nome', 'txt_nome', 'sel_forma', 'txt_forma']
            for k in chaves:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

elif menu == "2. Classificação de Medicamentos":
    st.header("🔬 2. Classificação (Em Casa)")
    st.write("Para cada nome único coletado, preencha as classificações abaixo. Preencher uma vez aplica a todas as unidades já coletadas e futuras.")
    
    nomes_coletados = db.get_all_nomes()
    classificacoes_db = db.get_classificacoes()
    
    faltam = [n for n in nomes_coletados if n not in classificacoes_db]
    if faltam:
        st.warning(f"Existem **{len(faltam)}** medicamentos aguardando classificação!")
    else:
        st.success("Todos os medicamentos coletados até agora estão classificados!")

    nome_classificar = st.selectbox("Selecione o medicamento para classificar/editar", nomes_coletados)

    if nome_classificar:
        existente = classificacoes_db.get(nome_classificar, {"atc": "", "mec_acao": "", "classe_est": "", "mec_antires": "-"})
        
        with st.form("form_class"):
            st.subheader(f"Classificando: {nome_classificar}")
            atc = st.text_input("Classe ATC (ex: J01CA04)", value=existente["atc"])
            mec_acao = st.text_input("Mecanismo de Ação", value=existente["mec_acao"])
            classe_est = st.text_input("Classe Estrutural / Classificação Farmacológica", value=existente["classe_est"])
            mec_antires = st.text_input("Mecanismo Antirresistência", value=existente["mec_antires"])
            
            if st.form_submit_button("💾 Salvar Classificação", type="primary"):
                db.upsert_classificacao(nome_classificar, atc, mec_acao, classe_est, mec_antires)
                st.success("Classificação salva com sucesso! Será aplicada automaticamente nos relatórios.")
                st.rerun()

elif menu == "3. Pesagem Mensal":
    st.header("⚖️ 3. Pesagem Mensal")
    st.write("Registre o peso total medido na balança física para o mês correspondente.")
    
    col1, col2 = st.columns(2)
    with col1:
        mes_pesagem = st.number_input("Mês da Pesagem", min_value=1, max_value=12, value=datetime.today().month, step=1)
    with col2:
        ano_pesagem = st.number_input("Ano da Pesagem", min_value=2000, max_value=2100, value=datetime.today().year, step=1)
    
    mes_ano_str = f"{mes_pesagem:02d}/{ano_pesagem}"
    
    pesagens_db = db.get_pesagens()
    peso_atual = pesagens_db.get(mes_ano_str, {"liquidos": 0.0, "solidos": 0.0})

    peso_liq = st.number_input("Peso total de Líquidos (kg)", min_value=0.0, value=peso_atual["liquidos"], step=0.1, format="%.2f")
    peso_sol = st.number_input("Peso total de Sólidos (kg)", min_value=0.0, value=peso_atual["solidos"], step=0.1, format="%.2f")

    if st.button("💾 Salvar Pesagem do Mês", type="primary"):
        db.upsert_pesagem(mes_ano_str, peso_liq, peso_sol)
        st.success(f"Pesagem de {mes_ano_str} salva com sucesso!")

elif menu == "4. Relatórios e Exportação":
    st.header("📊 4. Relatórios e Exportação")
    
    df_export = db.get_df_exportacao()
    if df_export.empty:
        st.warning("Nenhum dado coletado ainda.")
        st.stop()

    # Botões de exportação
    st.subheader("📥 Exportar Dados Brutos")
    st.write("Os dados abaixo seguem o padrão CICT com as colunas exatas da sua planilha 'Registro_Antimicrobianos'.")
    
    csv = df_export.to_csv(index=False).encode('utf-8')
    
    import io
    excel_buffer = io.BytesIO()
    df_export.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_data = excel_buffer.getvalue()

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Baixar Planilha (CSV)",
            data=csv,
            file_name="Registro_Antimicrobianos.csv",
            mime="text/csv",
        )
    with col2:
        st.download_button(
            label="Baixar Planilha (XLSX - Excel)",
            data=excel_data,
            file_name="Registro_Antimicrobianos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    st.dataframe(df_export, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📈 Gráficos do Relatório Anual")
    st.write("*Dica: Passe o mouse sobre os gráficos e clique no ícone da câmera para exportar como imagem PNG.*")

    # Cores padronizadas para as situações
    color_map = {
        "Vencido": "#EF553B", 
        "Dentro da validade": "#00CC96", 
        "Não foi possível verificar": "#AB63FA"
    }

    # Gráfico 1
    st.markdown("**Gráfico 1 — Frequência das formas farmacêuticas coletadas**")
    fig1 = px.histogram(df_export, y="Forma Farmacêutica", color="Situação Validade", 
                        barmode="stack", color_discrete_map=color_map,
                        orientation='h')
    fig1.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2
    st.markdown("**Gráfico 2 — Frequência das classes estruturais**")
    # Filtra vazios se houver
    df_graf2 = df_export[df_export["Classe Estrutural"] != ""]
    fig2 = px.histogram(df_graf2, y="Classe Estrutural", color="Situação Validade", 
                        barmode="stack", color_discrete_map=color_map,
                        orientation='h')
    fig2.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig2, use_container_width=True)

    # Gráfico 3
    st.markdown("**Gráfico 3 — Distribuição dos mecanismos de ação**")
    df_graf3 = df_export[df_export["Mecanismo de Ação"] != ""]
    fig3 = px.pie(df_graf3, names="Mecanismo de Ação")
    st.plotly_chart(fig3, use_container_width=True)

    # Gráfico 4
    st.markdown("**Gráfico 4 — Princípios ativos mais descartados**")
    # Pega top 20 para não sobrecarregar
    top_meds = df_export["Nome do Medicamento"].value_counts().nlargest(20).index
    df_graf4 = df_export[df_export["Nome do Medicamento"].isin(top_meds)]
    fig4 = px.histogram(df_graf4, y="Nome do Medicamento", color="Situação Validade", 
                        barmode="stack", color_discrete_map=color_map,
                        orientation='h')
    fig4.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig4, use_container_width=True)

    # Gráfico 5
    st.markdown("**Gráfico 5 — Frequência por ano de vencimento**")
    def extrair_ano(val):
        if val == "Não identificada": return val
        try: return val.split("/")[1]
        except: return val
    
    df_export["Ano Extraído"] = df_export["Ano Validade"].apply(extrair_ano)
    anos_ordenados = sorted([y for y in df_export["Ano Extraído"].unique() if y != "Não identificada"])
    if "Não identificada" in df_export["Ano Extraído"].values:
        anos_ordenados.append("Não identificada")

    fig5 = px.histogram(df_export, x="Ano Extraído", color_discrete_sequence=["#1f77b4"],
                        category_orders={"Ano Extraído": anos_ordenados})
    st.plotly_chart(fig5, use_container_width=True)

    st.markdown("---")
    st.subheader("🗓️ Tabela Mensal de Pesagem e Unidades")
    
    df_completo = db.get_df_completo()
    if not df_completo.empty:
        # Extrai mês/ano da data_coleta
        df_completo['mes_ano_coleta'] = pd.to_datetime(df_completo['data_coleta']).dt.strftime('%m/%Y')
        
        # Agrupa unidades líquidas e sólidas
        resumo_unidades = df_completo.groupby(['mes_ano_coleta', 'estado_fisico']).size().unstack(fill_value=0).reset_index()
        # Garante colunas
        for estado in ['Sólido', 'Líquido', 'Semissólido']:
            if estado not in resumo_unidades.columns:
                resumo_unidades[estado] = 0
                
        resumo_unidades['Total Unidades'] = resumo_unidades['Sólido'] + resumo_unidades['Líquido'] + resumo_unidades['Semissólido']
        
        # Calcula %
        resumo_unidades['% Sólidos (unid.)'] = (resumo_unidades['Sólido'] / resumo_unidades['Total Unidades'] * 100).round(1).astype(str) + '%'
        resumo_unidades['% Líquidos (unid.)'] = (resumo_unidades['Líquido'] / resumo_unidades['Total Unidades'] * 100).round(1).astype(str) + '%'

        # Puxa pesagens
        pesagens_db = db.get_pesagens()
        
        # Junta os dados de peso
        pesos_sol = []
        pesos_liq = []
        for index, row in resumo_unidades.iterrows():
            m_a = row['mes_ano_coleta']
            peso = pesagens_db.get(m_a, {"liquidos": 0.0, "solidos": 0.0})
            pesos_sol.append(peso["solidos"])
            pesos_liq.append(peso["liquidos"])
            
        resumo_unidades['Peso Sólidos (kg)'] = pesos_sol
        resumo_unidades['Peso Líquidos (kg)'] = pesos_liq
        
        # Renomear pra exibição final
        tabela_final = resumo_unidades[['mes_ano_coleta', 'Sólido', 'Líquido', '% Sólidos (unid.)', '% Líquidos (unid.)', 'Peso Sólidos (kg)', 'Peso Líquidos (kg)']]
        tabela_final.columns = ['Mês/Ano', 'Qtd Unid. Sólidas', 'Qtd Unid. Líquidas', '% Sólidos', '% Líquidos', 'Peso Sólidos (kg)', 'Peso Líquidos (kg)']
        
        st.dataframe(tabela_final, use_container_width=True)
    else:
        st.write("Sem dados para a tabela mensal.")
