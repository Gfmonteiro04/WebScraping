import streamlit as st
import pandas as pd
import os

# Configuração da Página
st.set_page_config(page_title="Catálogo de Perfumes Seletos", layout="wide")

st.title("👃 Catálogo de Perfumes Seletos")

# --- CARREGAMENTO DE DADOS (ATUALIZADO PARA NOVA BASE) ---
@st.cache_data 
def load_data():
    # Caminho do arquivo que o robô está gerando
    arquivo_atual = 'BancoFinal_Seletos_Atualizado.csv'
    
    if os.path.exists(arquivo_atual):
        # IMPORTANTE: Adicionado sep=';'
        df = pd.read_csv(arquivo_atual, sep=';')
        
    elif os.path.exists('BancoFinal_Seletos.csv'):
        st.warning("Carregando base original (sem imagens novas).")
        df = pd.read_csv('BancoFinal_Seletos.csv', sep=';')
        
    else:
        return None
    
    # Limpeza de dados
    df = df.astype(str)
    df = df.replace('nan', '')
    
    return df

df = load_data()

if df is None:
    st.error("Nenhum arquivo CSV encontrado (BancoFinal_Seletos.csv ou Atualizado).")
    st.stop()

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("Filtros")

# Filtro de Texto
# Na nova base, a coluna do nome é a terceira (índice 2), chamada 'Perfume'
coluna_nome = df.columns[2] 
busca_nome = st.sidebar.text_input("Buscar Perfume", "")

# Filtro de Imagem
mostrar_apenas_com_foto = st.sidebar.checkbox("Apenas com foto baixada", value=False)

# --- APLICAÇÃO DOS FILTROS ---
df_filtrado = df.copy()

if busca_nome:
    df_filtrado = df_filtrado[df_filtrado[coluna_nome].str.contains(busca_nome, case=False, na=False)]

if mostrar_apenas_com_foto and 'caminho_imagem_local' in df_filtrado.columns:
    df_filtrado = df_filtrado[
        (df_filtrado['caminho_imagem_local'] != 'nan') & 
        (df_filtrado['caminho_imagem_local'] != '') & 
        (df_filtrado['caminho_imagem_local'] != 'IMAGEM_NAO_ENCONTRADA') &
        (df_filtrado['caminho_imagem_local'].str.contains('downloaded_images'))
    ]

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
                # 1. Imagem
                img_path = dados.get('caminho_imagem_local', '')
                
                # Se o caminho tiver barra invertida do Windows (\), o Python às vezes reclama no Linux/Web
                # Vamos normalizar só por garantia
                if img_path:
                    img_path = img_path.replace('\\', '/')

                if img_path and os.path.exists(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    st.markdown("📷 *Sem Imagem*")
                
                # 2. Nome
                st.subheader(dados[coluna_nome])
                
                # 3. Informações Extras (Brand, Country)
                # Na sua base nova, Brand é coluna 3 e Country é 4
                marca = dados.get('Brand', '')
                pais = dados.get('Country', '')
                if marca: st.caption(f"Marca: {marca} ({pais})")
                
                # 4. Link
                url = dados.get('url', '')
                if 'http' in str(url):
                    st.link_button("Ver no Site", url)