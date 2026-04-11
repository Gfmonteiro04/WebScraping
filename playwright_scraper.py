import pandas as pd
from playwright.sync_api import sync_playwright
import time 
from random import uniform
import os
import re

# ==========================================
# CONFIGURAÇÕES
# ==========================================
CSV_PATH = 'C:/Users/gfmon/Documents/scraper/BancoFinal_Tratado_KNN.csv'
OUTPUT_CSV_PATH = 'C:/Users/gfmon/Documents/scraper/BancoFinal_Tratado_KNN.csv'
CSV_PATH = 'C:/Users/ADM/WebScraping/BancoFinal_Seletos.csv'
OUTPUT_CSV_PATH = 'BancoFinal_Completo.csv'

# ==========================================
# 1. NOVO SCRIPT JAVASCRIPT (Com Extração de Imagem)
# ==========================================
SCRIPT_EXTRACAO = '''() => {
    function getChartWinner(titleKeyword, optionsList) {
        const elements = Array.from(document.querySelectorAll('div.cell, div.grid-x, div'));
        
        let targetBlock = null;
        let minLength = 999999;
        const lastOption = optionsList[optionsList.length - 1];

        for (const el of elements) {
            const text = el.innerText;
            if (!text) continue;
            
            if (text.toLowerCase().includes(titleKeyword.toLowerCase()) && 
                text.toLowerCase().includes(lastOption.toLowerCase())) {
                
                if (text.length < minLength && text.length > 50) {
                    minLength = text.length;
                    targetBlock = text;
                }
            }
        }

        if (!targetBlock) return "N/A";

        const lines = targetBlock.split(/\\r?\\n/);
        
        let winner = "N/A";
        let maxVotes = -1;
        let totalVotesGlobal = 0;

        for (const option of optionsList) {
            let optionVotes = 0;
            
            for (const line of lines) {
                const cleanLine = line.trim().toLowerCase();
                const cleanOption = option.toLowerCase();

                if (cleanLine.startsWith(cleanOption)) {
                    const match = cleanLine.match(/(\d+)$/);
                    if (match) {
                        optionVotes = parseInt(match[1]);
                        break; 
                    }
                }
            }

            totalVotesGlobal += optionVotes;

            if (optionVotes > maxVotes) {
                maxVotes = optionVotes;
                winner = option;
            }
        }
        
        if (totalVotesGlobal === 0) return "Sem Votos";
        
        return winner;
    }

    // NOVA FUNÇÃO: Pega a URL da imagem principal do perfume
    function getImageUrl() {
        const imgEl = document.querySelector('img[itemprop="image"]');
        return imgEl ? imgEl.src : "N/A";
    }

    return {
        longevity: getChartWinner("Longevity", ["very weak", "weak", "moderate", "long lasting", "eternal"]),
        sillage: getChartWinner("Sillage", ["intimate", "moderate", "strong", "enormous"]),
        gender: getChartWinner("Gender", ["female", "more female", "unisex", "more male", "male"]),
        price: getChartWinner("Price Value", ["way overpriced", "overpriced", "ok", "good value", "great value"]),
        image_url: getImageUrl() // Adicionado aqui
    };
}'''

# ==========================================
# 2. SCROLL REFINADO
# ==========================================
def human_scroll(page):
    try:
        print("   > Escaneando página para carregar gráficos...")
        viewport_height = page.viewport_size['height']
        for _ in range(8): 
            page.mouse.wheel(0, viewport_height * 0.7)
            time.sleep(uniform(0.5, 0.8))
        
        page.mouse.wheel(0, -2000)
        time.sleep(1.5)
    except: pass

# ==========================================
# 3. ROBÔ PRINCIPAL
# ==========================================
def run_data_scraper(df, start_index, total):
    with sync_playwright() as p:
        args = ["--disable-blink-features=AutomationControlled", "--start-maximized"]
        browser = p.chromium.launch(headless=False, args=args)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()

        try:
            for i in range(start_index, total):
                
                if (i - start_index) > 0 and i % 5 == 0:
                    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
                    print(f"--- Backup na linha {i} ---")

                # Modificado para verificar também se a Imagem_URL está vazia
                if 'Longevidade' in df.columns and 'Imagem_URL' in df.columns:
                    val_long = str(df.iloc[i, df.columns.get_loc('Longevidade')])
                    val_img = str(df.iloc[i, df.columns.get_loc('Imagem_URL')])
                    if val_long not in ['nan', '', 'NaN', 'ERRO', 'N/A', 'Sem Votos'] and val_img not in ['nan', '', 'NaN', 'N/A']:
                        continue

                url = df.iloc[i, 1] 
                if not isinstance(url, str) or 'http' not in url:
                    continue

                print(f"[{i}/{total}] Acessando: {url}")
                
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # --- ANTI-BLOQUEIO (CLOUDFLARE) ---
                    while True:
                        try:
                            title = page.title()
                            if "Just a moment" in title or "Security" in title or "Cloudflare" in title:
                                print(f"🛑 [LINHA {i}] BLOQUEIO DETECTADO! Resolva o Captcha...")
                                page.bring_to_front()
                                time.sleep(5)
                            else:
                                break
                        except: break
                    # ----------------------------------

                    human_scroll(page)
                    
                    # Extração
                    dados = page.evaluate(SCRIPT_EXTRACAO) or {}

                    longevity = str(dados.get('longevity', 'N/A')).title()
                    sillage = str(dados.get('sillage', 'N/A')).title()
                    gender = str(dados.get('gender', 'N/A')).title()
                    price = str(dados.get('price', 'N/A')).title()
                    image_url = str(dados.get('image_url', 'N/A')) # Extrai o link da imagem

                    # Segunda tentativa se falhar
                    if longevity == "N/A" and gender == "N/A":
                        print("   > Tentativa 2 (Rolagem extra)...")
                        page.keyboard.press("End")
                        time.sleep(1)
                        page.mouse.wheel(0, -1000)
                        time.sleep(1)
                        dados = page.evaluate(SCRIPT_EXTRACAO) or {}
                        
                        longevity = str(dados.get('longevity', 'N/A')).title()
                        sillage = str(dados.get('sillage', 'N/A')).title()
                        gender = str(dados.get('gender', 'N/A')).title()
                        price = str(dados.get('price', 'N/A')).title()
                        image_url = str(dados.get('image_url', 'N/A'))

                    df.loc[i, 'Longevidade'] = longevity
                    df.loc[i, 'Sillage'] = sillage
                    df.loc[i, 'Genero_Voto'] = gender
                    df.loc[i, 'Preco_Voto'] = price
                    df.loc[i, 'Imagem_URL'] = image_url # Salva no DataFrame

                    print(f"   > Resultado: L:{longevity} | S:{sillage} | Img: {image_url[:30]}...")
                    
                    time.sleep(uniform(4.0, 7.0))

                except Exception as e:
                    print(f"   > Erro na url (Pulando): {e}")
                    df.loc[i, 'Longevidade'] = 'ERRO'

            return df

        except Exception as e:
            print(f"Erro crítico: {e}")
            df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
            return df
        finally:
            try: browser.close()
            except: pass

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Arquivo {CSV_PATH} não encontrado!")
        return

    print("Iniciando extração...")
    try: df = pd.read_csv(CSV_PATH, sep=';')
    except: df = pd.read_csv(CSV_PATH, sep=',')

    # Adicionada a coluna Imagem_URL para ser criada caso não exista
    cols = ['Longevidade', 'Sillage', 'Genero_Voto', 'Preco_Voto', 'Imagem_URL']
    for col in cols:
        if col not in df.columns: df[col] = ''

    run_data_scraper(df, 0, len(df))
    
    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
    print("Concluído! Salvo em:", OUTPUT_CSV_PATH)

if __name__ == "__main__":
    main()