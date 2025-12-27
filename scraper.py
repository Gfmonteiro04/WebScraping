import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from random import uniform
import os
from urllib.parse import urlparse

# --- CONFIGURAÇÕES ---
# Nome do novo arquivo de entrada
CSV_PATH = 'C:/Users/gfmon/Downloads/BancoFinal_Seletos.csv' 

# Arquivo onde será salvo o progresso (pode ser o mesmo ou um novo)
OUTPUT_CSV_PATH = 'BancoFinal_Seletos_Atualizado.csv' 

OUTPUT_DIR = 'downloaded_images'
BATCH_SIZE = 50 

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.fragrantica.com/",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive"
}

def get_image_url(perfume_url, session):
    try:
        time.sleep(uniform(1.5, 3.5))
        response = session.get(perfume_url, timeout=20)
        
        if response.status_code == 403:
            print(f"BLOQUEIO (403) em: {perfume_url}")
            return "BLOQUEADO"
            
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        img_tag = soup.find("img", {"itemprop": "image"})
        if not img_tag:
            img_tag = soup.find("img", class_="perfume-main-image")

        if img_tag:
            if img_tag.get("srcset"):
                img_url = img_tag.get("srcset").split(" ")[0]
            else:
                img_url = img_tag.get("src")

            if img_url:
                if img_url.startswith('//'):
                    img_url = 'https:' + img_url
                elif img_url.startswith('/'):
                    parsed_url = urlparse(perfume_url)
                    img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{img_url}"
                return img_url
        return None

    except Exception as e:
        print(f"Erro ao extrair URL: {e}")
        return None

def download_image(img_url, session, output_path):
    try:
        if not img_url or img_url == "BLOQUEADO": return False
        time.sleep(uniform(0.5, 1.0))
        img_response = session.get(img_url, stream=True, timeout=20)
        img_response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in img_response.iter_content(1024):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Erro download: {e}")
        return False

def load_data():
    try:
        # MUDANÇA 1: Adicionado sep=';' para ler o formato novo corretamente
        df = pd.read_csv(CSV_PATH, sep=';')
    except FileNotFoundError:
        print(f"Arquivo {CSV_PATH} não encontrado.")
        return None

    # Verifica se existe um arquivo de progresso para retomar
    if os.path.exists(OUTPUT_CSV_PATH):
        print("Retomando do arquivo de progresso...")
        try:
            # Também lemos o progresso com ;
            df_progress = pd.read_csv(OUTPUT_CSV_PATH, sep=';')
            if len(df_progress) == len(df):
                df = df_progress
        except: pass
    
    # Se a coluna não existir, cria. Se existir, mantém o que tem.
    if 'caminho_imagem_local' not in df.columns:
        df['caminho_imagem_local'] = ''
        
    return df

def main():
    df = load_data()
    if df is None: return

    # A URL continua sendo a segunda coluna (índice 1)
    link_column = df.columns[1] 
    session = requests.Session()
    session.headers.update(HEADERS)

    total_rows = len(df)
    processed_count = 0

    print(f"Iniciando processamento de {total_rows} linhas...")

    for index, row in df.iterrows():
        # Lógica inteligente: Pula se já tem algo escrito na coluna de imagem
        if pd.notna(row['caminho_imagem_local']) and str(row['caminho_imagem_local']).strip() != "":
            continue

        perfume_url = row[link_column]
        
        if not isinstance(perfume_url, str) or 'http' not in perfume_url:
            # Marca como inválido apenas se estiver vazio/errado
            df.at[index, 'caminho_imagem_local'] = 'URL_INVALIDA'
            continue

        print(f"[{index}/{total_rows}] Processando...", end='\r')

        img_url = get_image_url(perfume_url, session)

        if img_url == "BLOQUEADO":
            print(f"\nBloqueio detectado. Salvando progresso e parando.")
            break 

        if img_url:
            try:
                p_id = row[df.columns[0]] # ID
                p_name = str(row[df.columns[2]]).replace(' ', '_').replace('/', '-').replace('\\', '-') # Nome
                ext = 'png' if '.png' in img_url else 'jpg'
                
                filename = f"{p_id}_{p_name}.{ext}"
                output_path = os.path.join(OUTPUT_DIR, filename)

                if download_image(img_url, session, output_path):
                    df.at[index, 'caminho_imagem_local'] = output_path
                    print(f" -> OK: {filename}                    ")
                else:
                    df.at[index, 'caminho_imagem_local'] = 'ERRO_DOWNLOAD'
            except Exception:
                df.at[index, 'caminho_imagem_local'] = 'ERRO_IO'
        else:
            df.at[index, 'caminho_imagem_local'] = 'IMAGEM_NAO_ENCONTRADA'

        processed_count += 1

        if processed_count % BATCH_SIZE == 0:
            # MUDANÇA 2: Salvamos com ; para manter o padrão
            df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
            print(f"\n--- Checkpoint salvo na linha {index} ---")

    # MUDANÇA 2 (Final): Salvamos com ;
    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
    print(f"\nProcessamento finalizado! Arquivo salvo em: {OUTPUT_CSV_PATH}")

if __name__ == "__main__":
    main()