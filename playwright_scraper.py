import pandas as pd
import requests
from playwright.sync_api import sync_playwright
import time
from random import uniform, randint
import os

# --- CONFIGURAÇÕES ---
CSV_PATH = 'C:/Users/gfmon/Downloads/BancoFinal.csv'
OUTPUT_CSV_PATH = 'BancoFinal_com_imagens.csv'
OUTPUT_DIR = 'downloaded_images'

# Tempo de castigo quando o bloqueio é detectado (em segundos)
# 600 segundos = 10 minutos. Ajuste conforme necessário.
TEMPO_CASTIGO =  1200

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.fragrantica.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

# Criamos uma exceção personalizada para controlar o fluxo
class JohnWickError(Exception):
    pass

def human_scroll(page):
    try:
        page.mouse.wheel(0, randint(300, 700))
        time.sleep(uniform(0.5, 1.5))
        page.mouse.wheel(0, randint(-100, -300))
        time.sleep(uniform(0.5, 1.0))
    except: pass

def check_for_ban(page):
    """Verifica se fomos bloqueados e lança o erro para fechar o navegador."""
    try:
        content = page.content()
        title = page.title()
        
        is_blocked = (
            "Too Many Requests" in title or 
            "John Wick" in content or 
            "malicious activities" in content or
            page.locator('h1:has-text("429")').is_visible()
        )

        if is_blocked:
            raise JohnWickError("Bloqueio detectado!")
            
    except JohnWickError:
        raise # Re-levanta o erro para ser pego lá embaixo
    except:
        pass # Erros de leitura da página ignoramos

def get_image_url(page, perfume_url):
    print(f"Acessando: {perfume_url}")
    
    # Delay aleatório antes de ir
    time.sleep(uniform(7.0, 12.0))

    try:
        page.goto(perfume_url, wait_until="domcontentloaded", timeout=45000)
    except Exception:
        return None

    # VERIFICAÇÃO CRÍTICA
    check_for_ban(page)

    human_scroll(page)
    
    # Fecha pop-ups
    try:
        if page.locator('text="Continue without supporting us"').is_visible(timeout=1500):
            page.locator('text="Continue without supporting us"').click()
    except: pass

    # Busca URL
    img_url = page.evaluate('''() => {
        const selectors = ['img[itemprop="image"]', '.cell.small-12 img[src*="fimgs"]', 'div.grid-x img[src*=".jpg"]'];
        for (const selector of selectors) {
            const img = document.querySelector(selector);
            if (img) return img.srcset ? img.srcset.split(' ')[0] : img.src;
        }
        return null;
    }''')

    if img_url:
        if img_url.startswith('//'): img_url = 'https:' + img_url
        print(f" > URL: {img_url}")
        return img_url
    
    return None

def download_image(img_url, session, output_path):
    try:
        time.sleep(uniform(0.5, 1.0))
        r = session.get(img_url, stream=True, timeout=15)
        if r.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
        return False
    except: return False

def load_data():
    if not os.path.exists(CSV_PATH): return None, 0
    df = pd.read_csv(CSV_PATH)
    if 'caminho_imagem_local' not in df.columns: df['caminho_imagem_local'] = ''
    
    start_index = 0
    if os.path.exists(OUTPUT_CSV_PATH):
        try:
            df_out = pd.read_csv(OUTPUT_CSV_PATH)
            if len(df_out) == len(df):
                df['caminho_imagem_local'] = df_out['caminho_imagem_local']
                processed = df[df['caminho_imagem_local'].notna() & (df['caminho_imagem_local'] != '')]
                if not processed.empty: start_index = processed.index.max() + 1
        except: pass
    return df, start_index

def run_scraper_session(df, start_index, total, session):
    """
    Roda uma sessão do navegador. 
    Retorna o novo start_index onde parou (seja por sucesso ou erro).
    """
    
    # Inicia o Playwright APENAS para esta sessão
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        context = browser.new_context(user_agent=HEADERS["User-Agent"], viewport={'width': 1280, 'height': 720})
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page = context.new_page()
        
        try:
            # Tenta rodar um lote de até 50 imagens antes de fechar preventivamente (opcional)
            # ou até tomar o erro John Wick
            for i in range(start_index, total):
                
                # Salva a cada 10 para garantir
                if (i - start_index) > 0 and i % 10 == 0:
                    df.to_csv(OUTPUT_CSV_PATH, index=False)
                    print(f"--- Parcial salvo na linha {i} ---")

                # Pula processados
                if str(df.iloc[i, df.columns.get_loc('caminho_imagem_local')]) not in ['nan', '']:
                    continue

                url = df.iloc[i, 1]
                if not isinstance(url, str) or 'http' not in url:
                    df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'URL_INVALIDA'
                    continue

                # --- AQUI PODE ACONTECER O ERRO 429 ---
                img_url = get_image_url(page, url) 
                # --------------------------------------

                if img_url:
                    try:
                        p_id = df.iloc[i, 0]
                        name_raw = str(df.iloc[i, 2])
                        name = "".join([c if c.isalnum() else "_" for c in name_raw])[:40]
                        ext = 'png' if '.png' in img_url else 'jpg'
                        path = os.path.join(OUTPUT_DIR, f"{p_id}_{name}.{ext}")

                        if download_image(img_url, session, path):
                            df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = path
                        else:
                            df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'ERRO_DOWNLOAD'
                    except:
                        df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'ERRO_IO'
                else:
                    df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'ERRO_IMG_NOT_FOUND'

            # Se chegou aqui, acabou tudo
            return total 

        except JohnWickError:
            print("\n" + "!"*40)
            print("!!! BLOQUEIO 429 DETECTADO !!!")
            print("Encerrando esta sessão do navegador imediatamente.")
            print("!"*40 + "\n")
            df.to_csv(OUTPUT_CSV_PATH, index=False) # Salva antes de morrer
            # Ao sair do 'with sync_playwright', o navegador fecha sozinho
            return i # Retorna o índice onde parou para tentar de novo depois
            
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        
        except Exception as e:
            print(f"Erro genérico na sessão: {e}")
            df.to_csv(OUTPUT_CSV_PATH, index=False)
            return i + 1 # Pula para o próximo se deu erro louco

def main():
    df, start_index = load_data()
    if df is None: return

    total = len(df)
    session = requests.Session()
    session.headers.update(HEADERS)

    # LOOP INFINITO DE SESSÕES
    while start_index < total:
        print(f"\n>>> Iniciando nova sessão do navegador na linha {start_index} de {total}...")
        
        try:
            # Chama a função que abre o navegador.
            # Ela vai rodar até acabar OU até tomar um erro 429.
            novo_index = run_scraper_session(df, start_index, total, session)
            
            # Se o índice não mudou (ou seja, travou no mesmo lugar por 429)
            if novo_index == start_index:
                print(f"Entrando em modo de espera (Cool Down) por {TEMPO_CASTIGO} segundos...")
                
                # Contagem regressiva visual
                for k in range(TEMPO_CASTIGO, 0, -10):
                    print(f"Retomando em {k}s...", end='\r')
                    time.sleep(10)
                print("\nAcordando para nova tentativa!\n")
            else:
                # Se avançou, atualizamos o índice mestre
                start_index = novo_index

        except KeyboardInterrupt:
            print("\nScript parado pelo usuário. Salvando...")
            df.to_csv(OUTPUT_CSV_PATH, index=False)
            break
            
    print("Processo finalizado.")

if __name__ == "__main__":
    main()