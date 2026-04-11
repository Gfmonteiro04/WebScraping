import streamlit as st
import pandas as pd
import os

# Configuração da Página
st.set_page_config(page_title="Catálogo de Perfumes Seletos", layout="wide")

st.title("👃 Catálogo de Perfumes Seletos")

# --- CARREGAMENTO DE DADOS ---
@st.cache_data 
def load_data():
    # Agora lê exatamente o nome do arquivo que você enviou
    arquivo_atual = 'BancoFinal_Tratado.csv'
    
    if os.path.exists(arquivo_atual):
        df = pd.read_csv(arquivo_atual, sep=';')
    else:
        return None
    
    # Limpeza de dados para visualização
    df = df.astype(str)
    df = df.replace('nan', '')
    
    return df

df = load_data()

if df is None:
    st.error("Arquivo 'BancoFinal_Tratado.csv' não encontrado na pasta atual.")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")

coluna_nome = 'Perfume' 
busca_nome = st.sidebar.text_input("Buscar Perfume", "")

# Filtros para os dados de performance
coluna_sillage = 'Sillage'
if coluna_sillage in df.columns:
    filtro_sillage = st.sidebar.multiselect("Projeção (Sillage)", df[coluna_sillage].unique())
else:
    filtro_sillage = []

coluna_longevidade = 'Longevidade'
if coluna_longevidade in df.columns:
    filtro_longevidade = st.sidebar.multiselect("Longevidade", df[coluna_longevidade].unique())
else:
    filtro_longevidade = []


# --- APLICAÇÃO DOS FILTROS ---
df_filtrado = df.copy()

if busca_nome:
    df_filtrado = df_filtrado[df_filtrado[coluna_nome].str.contains(busca_nome, case=False, na=False)]

if filtro_sillage:
    df_filtrado = df_filtrado[df_filtrado[coluna_sillage].isin(filtro_sillage)]

if filtro_longevidade:
    df_filtrado = df_filtrado[df_filtrado[coluna_longevidade].isin(filtro_longevidade)]

# Mostra total
st.markdown(f"**Total na lista:** {len(df_filtrado)}")

# --- GRID DE IMAGENS ---
cols_per_row = 4
rows = [df_filtrado.iloc[i:i + cols_per_row] for i in range(0, len(df_filtrado), cols_per_row)]

for row in rows:
    cols = st.columns(cols_per_row)
    for index, (col, perfume_row) in enumerate(zip(cols, row.iterrows())):
        idx, dados = perfume_row
        
        with col:
            with st.container(border=True):
                # 1. Imagem via arquivo local (Correção aplicada aqui)
                img_path = dados.get('caminho_imagem_local', '')
                
                if img_path and img_path not in ['nan', '', 'N/A', 'IMAGEM_NAO_ENCONTRADA']:
                    # Transforma a barra do Windows (\) em barra universal (/)
                    img_path = img_path.replace('\\', '/')
                    
                    if os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    else:
                        st.markdown(f"📷 *Imagem não encontrada na pasta*")
                else:
                    st.markdown("📷 *Sem Imagem*")
                
                # 2. Nome
                if coluna_nome in dados:
                    st.subheader(dados[coluna_nome].replace('-', ' ').title())
                
                # 3. Informações Extras
                marca = dados.get('Brand', '')
                if marca: st.caption(f"**Marca:** {marca.title()}")

                # Estatísticas
                st.write(f"**⏳ Longevidade:** {dados.get('Longevidade', 'N/A')}")
                st.write(f"**💨 Projeção:** {dados.get('Sillage', 'N/A')}")
                
                genero = dados.get('Genero', dados.get('Genero_Voto', 'N/A'))
                if genero and genero != 'N/A':
                    st.write(f"**👤 Gênero:** {genero}")
                
                # 4. Link
                url = dados.get('url', '')
                if 'http' in str(url):
                    st.link_button("Ver no Fragrantica", url)