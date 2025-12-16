import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
from random import uniform
import os
from urllib.parse import urlparse

# 1. Configuração baseada no contexto fornecido
CSV_PATH = '/home/ubuntu/upload/BancoFinal.csv'
OUTPUT_DIR = 'downloaded_images'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cabeçalhos completos para evitar o erro 403 (Acesso Negado)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.google.com/",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Connection": "keep-alive"
}

def get_image_url(perfume_url, session):
    """Busca a página e extrai a URL da imagem."""
    try:
        print(f"Acessando: {perfume_url}")
        # Pausa aleatória para evitar bloqueio por requisições rápidas
        time.sleep(uniform(1.5, 3.5))

        response = session.get(perfume_url, timeout=15)
        response.raise_for_status() # Levanta exceção para códigos de status ruins (4xx ou 5xx)

        soup = BeautifulSoup(response.content, 'html.parser')

        # Solução sugerida: buscar pela tag <picture> com itemprop="image"
        picture_tag = soup.find("picture", {"itemprop": "image"})
        
        if not picture_tag:
            print("AVISO: Tag <picture> não encontrada. Tentando seletor alternativo.")
            # Tentativa alternativa: imagem principal dentro da div de conteúdo
            img_tag = soup.find("img", class_="perfume-main-image")
            if not img_tag:
                print("ERRO: Nenhuma tag de imagem principal encontrada.")
                return None
        else:
            # A tag <picture> contém a tag <img>
            img_tag = picture_tag.find("img")
            if not img_tag:
                print("ERRO: Tag <img> não encontrada dentro de <picture>.")
                return None

        # Solução sugerida: extrair preferencialmente o srcset
        img_url = img_tag.get("srcset", "").split(" ")[0]
        
        # Se srcset estiver vazio, usa o src
        if not img_url:
            img_url = img_tag.get("src")

        # O Fragrantica usa URLs relativas para as imagens. Precisamos torná-las absolutas.
        if img_url and img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif img_url and img_url.startswith('/'):
            # Isso pode ser um problema se o domínio não for o mesmo, mas para o Fragrantica deve funcionar
            parsed_url = urlparse(perfume_url)
            img_url = f"{parsed_url.scheme}://{parsed_url.netloc}{img_url}"
        
        if img_url:
            print(f"URL da imagem encontrada: {img_url}")
            return img_url
        
        return None

    except requests.exceptions.RequestException as e:
        print(f"ERRO de requisição para {perfume_url}: {e}")
        return None
    except Exception as e:
        print(f"ERRO inesperado ao processar {perfume_url}: {e}")
        return None

def download_image(img_url, session, output_path):
    """Baixa a imagem e salva no disco."""
    try:
        print(f"Baixando imagem de: {img_url}")
        # Pausa aleatória antes de baixar a imagem
        time.sleep(uniform(0.5, 1.5))
        
        # O download da imagem também precisa da sessão e dos headers
        img_response = session.get(img_url, stream=True, timeout=15)
        img_response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in img_response.iter_content(1024):
                f.write(chunk)
        
        print(f"Imagem salva em: {output_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"ERRO ao baixar a imagem {img_url}: {e}")
        return False
    except Exception as e:
        print(f"ERRO inesperado ao salvar a imagem: {e}")
        return False

def main():
    """Função principal para processar o CSV."""
    try:
        # Tenta ler o CSV
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print(f"ERRO: Arquivo CSV não encontrado em {CSV_PATH}")
        return
    except Exception as e:
        print(f"ERRO ao ler o arquivo CSV: {e}")
        return

    # Adiciona a nova coluna para o caminho da imagem
    # O nome da coluna de links é a segunda coluna (índice 1)
    link_column = df.columns[1]
    df['caminho_imagem_local'] = ''
    
    # Cria uma sessão persistente com os headers
    session = requests.Session()
    session.headers.update(HEADERS)

    # Itera sobre as linhas do DataFrame
    for index, row in df.iterrows():
        perfume_url = row[link_column]
        
        if not isinstance(perfume_url, str) or not perfume_url.startswith('http'):
            print(f"AVISO: Linha {index} tem URL inválida: {perfume_url}. Pulando.")
            continue

        # 1. Extrair a URL da imagem
        img_url = get_image_url(perfume_url, session)

        if img_url:
            # 2. Definir o nome do arquivo local
            # Usa o ID da linha (primeira coluna) e o nome do perfume (terceira coluna) para o nome do arquivo
            # O ID está na coluna 0, o nome do perfume na coluna 2
            try:
                perfume_id = row[df.columns[0]]
                perfume_name = row[df.columns[2]].replace('-', '_').replace(' ', '_')
                
                # Tenta obter a extensão da URL da imagem
                path_parts = urlparse(img_url).path.split('.')
                extension = path_parts[-1] if len(path_parts) > 1 else 'jpg' # Default para jpg
                
                filename = f"{perfume_id}_{perfume_name}.{extension}"
                output_path = os.path.join(OUTPUT_DIR, filename)

                # 3. Baixar a imagem
                if download_image(img_url, session, output_path):
                    # 4. Salvar o caminho local no DataFrame
                    df.loc[index, 'caminho_imagem_local'] = output_path
                else:
                    df.loc[index, 'caminho_imagem_local'] = 'ERRO_DOWNLOAD'
            except Exception as e:
                print(f"ERRO ao processar a linha {index}: {e}")
                df.loc[index, 'caminho_imagem_local'] = 'ERRO_PROCESSAMENTO'
        else:
            df.loc[index, 'caminho_imagem_local'] = 'ERRO_URL_NAO_ENCONTRADA'

    # 5. Salvar o DataFrame atualizado
    output_csv_path = 'BancoFinal_com_imagens.csv'
    df.to_csv(output_csv_path, index=False)
    print(f"\nProcessamento concluído. Arquivo atualizado salvo em: {output_csv_path}")

if __name__ == "__main__":
    main()