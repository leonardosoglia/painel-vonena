import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 1. Configuração básica da página (DEVE SER O PRIMEIRO COMANDO)
st.set_page_config(page_title="Gestão da Produção Vó Nena", layout="wide")

# ==========================================
# ÁREA DAS FUNÇÕES (FERRAMENTAS DO SITE)
# ==========================================

# 2. FUNÇÃO PARA CRIAR AS MATRIZES 
def transformar_em_quadro(df, nome_coluna_produto, nome_coluna_quantidade, tipo_quadro="Corte"):
    """Transforma a lista, agrupa os formatos e fixa a ordem oficial dos sabores"""
    try:
        df_visual = df.copy()
        
        # 1. Quebra o código (Ex: COC-TRAD-30G)
        df_visual[['Categoria', 'Sabor_Sigla', 'Tamanho_Bruto']] = df_visual[nome_coluna_produto].str.split('-', n=2, expand=True)
        
        # 2. Dicionário para traduzir a sigla da base de dados para a linguagem da fábrica
        dicionario_sabores = {
            'TRAD': 'TRADICIONAL',
            'LEIT': 'LEITE CONDENSADO',
            'BRIG': 'BRIGADEIRO',
            'CAFE': 'CAFÉ',
            'PMOC': 'PÉ DE MOÇA',
            'ZERO': 'ZERO'
        }
        df_visual['Sabor'] = df_visual['Sabor_Sigla'].map(dicionario_sabores).fillna(df_visual['Sabor_Sigla'])
        
        # 3. Traduzir os tamanhos
        def traduzir_formato(tamanho):
            if '45' in tamanho: return '45g'
            elif '30' in tamanho or '27' in tamanho: return 'Mini'
            elif '160' in tamanho or '100' in tamanho or 'PET' in tamanho: return 'Pet'
            return tamanho
            
        df_visual['Formato_Fabrica'] = df_visual['Tamanho_Bruto'].apply(traduzir_formato)
        
        # 4. Constrói a Matriz
        matriz = pd.pivot_table(
            df_visual,
            values=nome_coluna_quantidade,
            index='Sabor',
            columns='Formato_Fabrica',
            aggfunc='sum',
            fill_value=0
        )
        
        # 5. Define a ordem exata das COLUNAS
        if tipo_quadro == "Corte":
            ordem_colunas = ['45g', 'Mini', 'Pet']
        else:
            ordem_colunas = ['45g', 'Mini']
            
        colunas_finais = [col for col in ordem_colunas if col in matriz.columns]
        matriz = matriz[colunas_finais]
        
        # 6. A MÁGICA DA ORDEM DAS LINHAS: Define a ordem exata e inalterável
        ordem_sabores = ['TRADICIONAL', 'LEITE CONDENSADO', 'BRIGADEIRO', 'CAFÉ', 'PÉ DE MOÇA', 'ZERO']
        matriz = matriz.reindex(ordem_sabores).fillna(0).astype(int)
        
        return matriz
        
    except Exception as e:
        st.warning(f"Aviso na formatação do quadro: {e}")
        return df

# 3. FUNÇÃO ESPECÍFICA PARA O QUADRO DE PRODUÇÃO DO SR. JOEL
def transformar_quadro_joel(df, nome_coluna_produto):
    """Transforma a lista do Sr. Joel num quadro com as colunas de Produção, Potes, etc."""
    try:
        df_visual = df.copy()
        
        # 1. Extrair o Sabor do código do produto
        df_visual[['Categoria', 'Sabor_Sigla', 'Resto']] = df_visual[nome_coluna_produto].str.split('-', n=2, expand=True)
        
        # 2. Traduzir as siglas para os nomes oficiais
        dicionario_sabores = {
            'TRAD': 'TRADICIONAL',
            'LEIT': 'LEITE CONDENSADO',
            'BRIG': 'BRIGADEIRO',
            'CAFE': 'CAFÉ',
            'PMOC': 'PÉ DE MOÇA',
            'ZERO': 'ZERO'
        }
        df_visual['Sabor'] = df_visual['Sabor_Sigla'].map(dicionario_sabores).fillna(df_visual['Sabor_Sigla'])
        
        # 3. Limpar colunas técnicas de rascunho
        df_visual = df_visual.drop(columns=[nome_coluna_produto, 'Categoria', 'Sabor_Sigla', 'Resto'], errors='ignore')
        
        # 4. Colocar o "Sabor" como sendo as linhas do nosso quadro
        df_visual = df_visual.groupby('Sabor').sum()
        
        # 5. Fixar a ordem inalterável das linhas
        ordem_sabores = ['TRADICIONAL', 'LEITE CONDENSADO', 'BRIGADEIRO', 'CAFÉ', 'PÉ DE MOÇA', 'ZERO']
        df_visual = df_visual.reindex(ordem_sabores).fillna(0).astype(int, errors='ignore')
        
        return df_visual
        
    except Exception as e:
        st.warning(f"Aviso na formatação do quadro do Sr. Joel: {e}")
        return df

# 4. CONEXÃO COM GOOGLE SHEETS VIA GSPREAD (substitui o pd.read_csv)
@st.cache_resource
def conectar_gspread():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(creds)

def ler_aba(gc, spreadsheet_id, nome_aba):
    """Lê uma aba pelo nome e retorna um DataFrame pandas."""
    planilha = gc.open_by_key(spreadsheet_id)
    aba = planilha.worksheet(nome_aba)
    dados = aba.get_all_records()
    return pd.DataFrame(dados)

# 5. FUNÇÃO PARA CARREGAR TODAS AS ABAS DO GOOGLE SHEETS
@st.cache_data(ttl=60)
def carregar_todos_os_dados():
    SPREADSHEET_ID = "1YPYm7yrKjzR95DdKfRcKALXS_QSUjt4MwtpRgQs5gfM"

    try:
        gc = conectar_gspread()

        df_estoque  = ler_aba(gc, SPREADSHEET_ID, "PAINEL_GESTAO")
        df_eraldo   = ler_aba(gc, SPREADSHEET_ID, "QUADRO_ERALDO")
        df_gil      = ler_aba(gc, SPREADSHEET_ID, "CORTE_GIL")
        df_leonice  = ler_aba(gc, SPREADSHEET_ID, "EMBALAGEM_LEONICE")
        df_joel     = ler_aba(gc, SPREADSHEET_ID, "PRODUCAO_JOEL")

        # Limpar nomes de colunas
        for df in [df_estoque, df_eraldo, df_gil, df_leonice, df_joel]:
            df.columns = df.columns.str.replace(':', '').str.strip()

        # Remover linhas sem produto
        df_estoque = df_estoque.dropna(subset=['ID_Produto'])
        df_eraldo  = df_eraldo.dropna(subset=['Produto'])
        df_gil     = df_gil.dropna(subset=['Produto'])
        df_leonice = df_leonice.dropna(subset=['Produto'])
        df_joel    = df_joel.dropna(subset=['Produto'])

        return df_estoque, df_eraldo, df_gil, df_leonice, df_joel

    except Exception as e:
        st.error(f"❌ Erro ao carregar dados do Google Sheets.\n\nDetalhe técnico: `{e}`")
        dfs_vazios = [pd.DataFrame()] * 5
        return dfs_vazios

# 6. FUNÇÃO DE GESTÃO VISUAL (PINTAR TABELAS)
def aplicar_cores(valor, cor_destaque):
    """Pinta a célula se for maior que zero, e esconde se for zero"""
    if isinstance(valor, (int, float)) and valor > 0:
        return f'background-color: {cor_destaque}; color: white; font-weight: bold;'
    elif isinstance(valor, (int, float)) and valor == 0:
        return 'color: rgba(255, 255, 255, 0.2);'
    return ''


# ==========================================
# CONSTRUÇÃO DO VISUAL DO SITE COMEÇA AQUI
# ==========================================

# 1. CABEÇALHO PRINCIPAL
col1, col2 = st.columns([8, 2])
with col1:
    st.title("🏭 Painel de Controle de Produção")
    st.markdown("Visão gerencial em tempo real do chão de fábrica.")
with col2:
    st.write("")
    if st.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# 2. CARREGA OS DADOS
df_estoque, df_eraldo, df_gil, df_leonice, df_joel = carregar_todos_os_dados()

# --- FUNÇÃO DA JANELA CENTRAL (POP-UP) ---
@st.dialog("🚨 Lista Completa de Faltas")
def abrir_janela_faltas(df_tabela):
    st.markdown("Estes produtos estão abaixo do estoque de segurança:")
    st.dataframe(df_tabela, use_container_width=True, hide_index=True)

# --- MENU LATERAL: ALERTAS DE ESTOQUE ---
with st.sidebar:
    st.header("🚨 Estoque Crítico")
    df_alertas = df_estoque[df_estoque['Alerta_Producao'].astype(str).str.contains('GERAR', na=False)]

    if df_alertas.empty:
        st.success("✅ Tudo controlado!")
    else:
        st.warning(f"Atenção: {len(df_alertas)} produtos precisam de produção!")
        
        if st.button("⚠️ Abrir Janela de Faltas", use_container_width=True):
            df_resumo_alertas = df_alertas[['ID_Produto', 'Stock_Real', 'Stock_Seguranca']].copy()
            df_resumo_alertas.columns = ['Produto', 'Em Estoque', 'Meta']
            abrir_janela_faltas(df_resumo_alertas)

# --- ACOMPANHAMENTO DO CHÃO DE FÁBRICA ---
st.header("⚙️ Produção em Tempo Real")

# Criando as Abas
aba_eraldo, aba_gil, aba_leonice = st.tabs([
    "📋 Planeamento (Eraldo)", 
    "🔪 Corte (Gil)", 
    "📦 Embalagem (Leonice)"
])

with aba_eraldo:

    # --- A "COLA" COMPLETA DO ERALDO ---
    with st.expander("📚 Parâmetros e Conversões (Metas Ideais da Fábrica)"):
        aba_45g, aba_outros, aba_conversoes = st.tabs(["📅 Metas 45g (Semanal)", "🎯 Mini, Pet, Potes e Produção (Fixo)", "🔄 Taxas de Conversão"])
        
        with aba_45g:
            df_param_45 = pd.DataFrame({
                'Sabor': ['TRADICIONAL', 'LEITE COND.', 'BRIGADEIRO', 'CAFÉ', 'PÉ DE MOÇA'],
                'Segunda': [5200, 2600, 1300, 1300, 1300],
                'Terça': [4400, 2200, 1100, 1100, 1100],
                'Quarta': [5200, 2600, 1300, 1300, 1300],
                'Quinta': [6800, 3400, 1700, 1700, 1700],
                'Sexta': [5600, 2800, 1400, 1400, 1400]
            })
            st.dataframe(df_param_45, hide_index=True, use_container_width=True)
        
        with aba_outros:
            col_mp, col_potes = st.columns(2)
            with col_mp:
                st.write("**Mini e Pet (Todo dia)**")
                df_param_mini = pd.DataFrame({
                    'Sabor': ['TRADICIONAL', 'LEITE COND.', 'BRIGADEIRO', 'CAFÉ', 'PÉ DE MOÇA', 'ZERO'],
                    'Mini': ['500', '500', '300', '300', '300', 'L 45g'],
                    'Pet': ['220', '180', '90', '90', '90', '300']
                })
                st.dataframe(df_param_mini, hide_index=True, use_container_width=True)
            with col_potes:
                st.write("**Potes e Ref. Produção (Todo dia)**")
                df_param_potes = pd.DataFrame({
                    'Sabor': ['TRADICIONAL', 'LEITE COND.', 'BRIGADEIRO', 'CAFÉ', 'PÉ DE MOÇA', 'ZERO'],
                    'Potes 260g': [50, 5, 20, 15, 15, 50],
                    'Potes 605g': [20, 20, 10, 10, 10, 20],
                    'Ref. Bandejas (Produção)': [70, 35, 22, 22, 22, 18]
                })
                st.dataframe(df_param_potes, hide_index=True, use_container_width=True)
                
        with aba_conversoes:
            st.info("💡 **Regras de Rendimento da Fábrica**")
            st.markdown("""
            * **Tacho:** 1 Tacho = 8 Bandejas
            * **Bandeja 45g:** 1 Bandeja = 100 unidades
            * **Bandeja Mini:** 1 Bandeja = 150 unidades
            * **Bandeja Pet:** 1 Bandeja = 30 unidades
            * **Bandeja Pet ZERO:** 1 Bandeja = 60 unidades
            """)

    st.subheader("⚖️ Saldos e Projeções de Bandejas")
    st.dataframe(df_eraldo, use_container_width=True, hide_index=True)
    
    st.divider() 
    
    st.subheader("🏭 Quadro de Produção (Sr. Joel)")
    col_tabela, col_lembretes = st.columns([3, 1])
    
    with col_tabela:
        matriz_joel = transformar_quadro_joel(df_joel, 'Produto')
        st.dataframe(matriz_joel.style.map(lambda x: aplicar_cores(x, 'rgba(0, 128, 0, 0.4)')), use_container_width=True)
        
    with col_lembretes:
        st.info("📌 Lembretes / Amanhã")
        notas_amanha = st.text_area("O que fica para amanhã?", height=150, placeholder="Ex: Produzir mais Pão de Mel...")

with aba_gil:
    st.subheader("🔪 Quadro de Corte")
    matriz_gil = transformar_em_quadro(df_gil, 'Produto', 'Falta_Cortar', "Corte")
    st.dataframe(matriz_gil.style.map(lambda x: aplicar_cores(x, 'rgba(178, 34, 34, 0.5)')), use_container_width=True)

with aba_leonice:
    st.subheader("📦 Quadro de Embalagem")
    matriz_leonice = transformar_em_quadro(df_leonice, 'Produto', 'Falta_Embalar', "Embalagem")
    st.dataframe(matriz_leonice.style.map(lambda x: aplicar_cores(x, 'rgba(30, 144, 255, 0.4)')), use_container_width=True)

st.divider()

# --- TABELA DE ESTOQUE COMPLETA ---
with st.expander("📊 Clique para ver o Estoque Geral Detalhado"):
    st.dataframe(df_estoque, use_container_width=True, hide_index=True)
