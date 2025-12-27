import pandas as pd
import requests
from playwright.sync_api import sync_playwright
import time
from random import uniform, randint
import os

# ==========================================
# CONFIGURAÇÕES DE ARQUIVOS
# ==========================================
CSV_PATH = 'C:/Users/gfmon/Downloads/BancoFinal_Seletos.csv'
OUTPUT_CSV_PATH = 'BancoFinal_Seletos_Atualizado.csv'
OUTPUT_DIR = 'downloaded_images'

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==========================================
# ESTRATÉGIA DE SOBREVIVÊNCIA (ANTI-SOFTBLOCK)
# ==========================================
TEMPO_CASTIGO_NORMAL = 1200  # 20 minutos
TEMPO_CASTIGO_SEVERO = 13000 # ~3.6 horas
LIMITE_TENTATIVAS_CURTAS = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.fragrantica.com/",
    "Accept-Language": "en-US,en;q=0.9",
}

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
    try:
        content = page.content()
        title = page.title()
        
        if "Just a moment" in title:
            print("Verificação Cloudflare. Aguardando 10s...")
            time.sleep(10)

        is_blocked = (
            "Too Many Requests" in title or 
            "John Wick" in content or 
            "malicious activities" in content or
            page.locator('h1:has-text("429")').is_visible()
        )
        if is_blocked:
            raise JohnWickError("Bloqueio detectado!")
    except JohnWickError:
        raise 
    except: pass 

def get_image_url(page, perfume_url):
    print(f"Acessando: {perfume_url}")
    
    # Pausa Noturna (15s a 25s)
    time.sleep(uniform(15.0, 25.0)) 

    try:
        page.goto(perfume_url, wait_until="domcontentloaded", timeout=60000)
    except Exception:
        return None

    check_for_ban(page)
    human_scroll(page)
    
    try:
        if page.locator('text="Continue without supporting us"').is_visible(timeout=1500):
            page.locator('text="Continue without supporting us"').click()
    except: pass

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
        r = session.get(img_url, stream=True, timeout=20)
        if r.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
        return False
    except: return False

def load_data():
    if not os.path.exists(CSV_PATH): 
        print(f"ERRO: Arquivo {CSV_PATH} não encontrado.")
        return None, 0
    
    try:
        df = pd.read_csv(CSV_PATH, sep=';')
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return None, 0

    if 'caminho_imagem_local' not in df.columns: df['caminho_imagem_local'] = ''
    
    # Carrega progresso anterior para mesclar
    if os.path.exists(OUTPUT_CSV_PATH):
        try:
            print("Carregando progresso anterior...")
            df_out = pd.read_csv(OUTPUT_CSV_PATH, sep=';')
            if len(df_out) == len(df):
                df['caminho_imagem_local'] = df_out['caminho_imagem_local']
        except: pass

    # IMPORTANTE: Começa sempre do ZERO para revisar erros antigos.
    # O script vai pular rapidinho o que já está pronto.
    start_index = 0
    return df, start_index

def run_scraper_session(df, start_index, total, session):
    with sync_playwright() as p:
        args = ["--start-maximized", "--disable-blink-features=AutomationControlled"]
        browser = p.chromium.launch(headless=False, args=args)
        
        context = browser.new_context(user_agent=HEADERS["User-Agent"], viewport={'width': 1366, 'height': 768})
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        context.add_init_script("window.navigator.chrome = { runtime: {} };")
        
        page = context.new_page()
        
        try:
            for i in range(start_index, total):
                
                if (i - start_index) > 0 and i % 10 == 0:
                    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
                    print(f"--- Parcial salvo na linha {i} ---")

                # --- LÓGICA DE REPESCAGEM ---
                valor_celula = str(df.iloc[i, df.columns.get_loc('caminho_imagem_local')])

                # 1. PULA se já tem sucesso (pasta downloaded_images E sem palavra ERRO)
                if 'downloaded_images' in valor_celula and 'ERRO' not in valor_celula:
                    continue
                
                # 2. Se caiu aqui, vai tentar baixar (Vazio ou Erro anterior)
                url = df.iloc[i, 1]
                if not isinstance(url, str) or 'http' not in url:
                    df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'URL_INVALIDA'
                    continue

                img_url = get_image_url(page, url) 

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
                            # NOME EXATO DO ERRO PEDIDO
                            df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'ERRO_DOWNLOAD'
                    except:
                        df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'ERRO_IO'
                else:
                    # NOME EXATO DO ERRO PEDIDO
                    df.iloc[i, df.columns.get_loc('caminho_imagem_local')] = 'ERRO_URL_NAO_ENCONTRADA'

            return total 

        except JohnWickError:
            print("\n!!! BLOQUEIO 429 !!! Salvando...")
            df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
            return i 
            
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        
        except Exception as e:
            print(f"Erro genérico: {e}")
            df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
            return i + 1

def main():
    df, start_index = load_data()
    if df is None: return

    total = len(df)
    session = requests.Session()
    session.headers.update(HEADERS)

    consecutive_blocks = 0

    while start_index < total:
        print(f"\n>>> Verificando lista a partir da linha {start_index} de {total}...")
        
        try:
            novo_index = run_scraper_session(df, start_index, total, session)
            
            if novo_index == start_index:
                consecutive_blocks += 1
                
                if consecutive_blocks > LIMITE_TENTATIVAS_CURTAS:
                    tempo_espera = TEMPO_CASTIGO_SEVERO
                    print(f"\n[ALERTA] {consecutive_blocks} bloqueios seguidos.")
                    print(f"Modo HIBERNAÇÃO por {tempo_espera/3600:.1f} horas...")
                else:
                    tempo_espera = TEMPO_CASTIGO_NORMAL
                    print(f"\n[AVISO] Bloqueio. Esperando {tempo_espera/60:.0f} minutos...")

                for k in range(tempo_espera, 0, -10):
                    print(f"Retomando em {k}s...", end='\r')
                    time.sleep(10)
                print("\nReiniciando...\n")
            
            else:
                start_index = novo_index
                consecutive_blocks = 0
                print("Lote finalizado com sucesso.")

        except KeyboardInterrupt:
            print("\nParado pelo usuário. Salvando...")
            df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
            break
            
    print("Processo finalizado.")

if __name__ == "__main__":
    main()