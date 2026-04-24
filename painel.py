import streamlit as st
import pandas as pd

# 1. Configuração básica da página
st.set_page_config(page_title="Gestão da Produção", layout="wide")

# 2. PRIMEIRO ENSINAMOS O PYTHON A LER OS DADOS (A Ferramenta)
@st.cache_data 
def carregar_dados():
    # O seu link correto da aba Painel_Gestão
    url_planilha = "https://docs.google.com/spreadsheets/d/1YPYm7yrKjzR95DdKfRcKALXS_QSUjt4MwtpRgQs5gfM/export?format=csv&gid=177579187"
    dados = pd.read_csv(url_planilha)
    
    # TRATAMENTO DE DADOS: 
    dados.columns = dados.columns.str.replace(':', '').str.strip()
    dados = dados.dropna(subset=['ID_Produto']) # Aqui ele apaga os "None" vazios!
    
    return dados

# 3. AGORA SIM, CRIAMOS O CABEÇALHO E O BOTÃO
col1, col2 = st.columns([8, 2]) 

with col1:
    st.title("🏭 Painel de Controle de Produção")
    st.markdown("Visão gerencial em tempo real do chão de fábrica.")

with col2:
    st.write("") # Espaço para alinhar o botão
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        carregar_dados.clear() # Agora ele já sabe quem é o "carregar_dados"!
        st.rerun()

# 4. CARREGA OS DADOS PARA A TELA
df_estoque = carregar_dados()

# --- SEÇÃO 1: OS CARDS DE ALERTA ---
st.subheader("🚨 Alertas de Ação Imediata")

df_alertas = df_estoque[df_estoque['Alerta_Producao'].str.contains('GERAR', na=False)]

if df_alertas.empty:
    st.success("✅ Estoque controlado! Nenhuma ordem de produção pendente no momento.")
else:
    colunas = st.columns(3)
    for index, row in df_alertas.reset_index(drop=True).iterrows():
        with colunas[index % 3]:
            st.metric(
                label=f"⚠️ {row['ID_Produto']}", 
                value=f"{row['Stock_Real']} un", 
                delta=f"Meta era {row['Stock_Seguranca']} un",
                delta_color="inverse"
            )

st.divider()

# --- SEÇÃO 2: A TABELA GERAL ---
st.subheader("📦 Visão Geral do Estoque")
# A tabela também já vai aparecer sem aqueles "None" feios!
st.dataframe(df_estoque, use_container_width=True)