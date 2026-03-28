import pandas as pd
from playwright.sync_api import sync_playwright
import time 
from random import uniform
import os

# ==========================================
# CONFIGURAÇÕES (Caminhos Absolutos)
# ==========================================
CSV_PATH = 'C:/Users/ADM/WebScraping/BancoFinal_Seletos_Atualizado.csv'
OUTPUT_CSV_PATH = 'C:/Users/ADM/WebScraping/BancoFinal_Novo.csv'

def save_csv_safe(df, path):
    while True:
        try:
            df.to_csv(path, sep=';', index=False)
            break
        except PermissionError:
            print(f"\n❌ ERRO DE PERMISSÃO: O arquivo '{path}' está ABERTO NO EXCEL!")
            print("👉 O robô continuará tentando salvar a cada 10 segundos. Feche o Excel.")
            time.sleep(10)

# ==========================================
# 1. JAVASCRIPT OTIMIZADO (Bilíngue + Gênero + Preço)
# ==========================================
SCRIPT_EXTRACAO = r'''() => {
    function getVotesFromText(enHeader, ptHeader, optionsMap) {
        if (!document.body) return "N/A";
        
        const fullText = document.body.innerText.replace(/\s+/g, ' ').toLowerCase();
        
        let headerIndex = fullText.indexOf(enHeader.toLowerCase());
        if (headerIndex === -1) {
            headerIndex = fullText.indexOf(ptHeader.toLowerCase());
        }
        
        if (headerIndex === -1) return "Sem Votos";

        const contextChunk = fullText.substring(headerIndex, headerIndex + 800);
        let winner = "Sem Votos";
        let maxVotes = 0;

        for (const item of optionsMap) {
            const enOpt = item[0];
            const ptOpt = item[1];

            let regex = new RegExp(enOpt.toLowerCase() + "[^0-9]{0,50}(\\d+)", "i");
            let match = contextChunk.match(regex);

            if (!match && ptOpt) {
                regex = new RegExp(ptOpt.toLowerCase() + "[^0-9]{0,50}(\\d+)", "i");
                match = contextChunk.match(regex);
            }

            if (match) {
                const votes = parseInt(match[1]);
                if (votes > maxVotes && votes > 0) {
                    maxVotes = votes;
                    winner = enOpt; 
                }
            }
        }
        return winner;
    }

    // Identifica o gênero com base no texto principal
    function getGender() {
        const titleText = document.body.innerText.substring(0, 1500).toLowerCase();
        if (titleText.includes("for women and men") || titleText.includes("unisex") || titleText.includes("compartilhável")) return "Unissex";
        if (titleText.includes("for women") || titleText.includes("feminino")) return "Feminino";
        if (titleText.includes("for men") || titleText.includes("masculino")) return "Masculino";
        return "N/A";
    }

    return {
        gender: getGender(),
        longevity: getVotesFromText("Longevity", "Longevidade", [
            ["very weak", "muito fraca"], 
            ["weak", "fraca"], 
            ["moderate", "moderada"], 
            ["long lasting", "longa duração"], 
            ["eternal", "eterna"]
        ]),
        sillage: getVotesFromText("Sillage", "Projeção", [
            ["intimate", "íntima"], 
            ["moderate", "moderada"], 
            ["strong", "marcante"], 
            ["enormous", "enorme"]
        ]),
        price: getVotesFromText("Price Value", "Custo-Benefício", [
            ["way overpriced", "muito caro"], 
            ["overpriced", "caro"], 
            ["ok", "ok"], 
            ["good value", "bom valor"], 
            ["great value", "ótimo valor"]
        ])
    };
}'''

# ==========================================
# 2. SCROLL COM "VISÃO"
# ==========================================
def smart_scroll_and_wait(page):
    try:
        print("   > Procurando gráficos na tela...")
        for _ in range(15):
            page.mouse.wheel(0, 500)
            time.sleep(0.8)
            
            js_checker = "() => { const txt = document.body.innerText.toLowerCase(); return txt.includes('longevity') || txt.includes('longevidade'); }"
            if page.evaluate(js_checker):
                print("   > Gráficos encontrados! Lendo votos...")
                time.sleep(2.0)
                return True
                
        page.mouse.wheel(0, -1000)
        time.sleep(1)
        return False
    except: 
        return False

# ==========================================
# 3. ROBÔ PRINCIPAL
# ==========================================
def run_data_scraper(df, start_index, total):
    with sync_playwright() as p:
        args = ["--disable-blink-features=AutomationControlled", "--start-maximized"]
        browser = p.chromium.launch(headless=False, args=args)
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York'
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()

        try:
            for i in range(start_index, total):
                
                val = str(df.iloc[i, df.columns.get_loc('Longevidade')])
                if val not in ['nan', '', 'NaN', 'ERRO', 'N/A', 'BLOQUEADO'] and val != 'None':
                    continue

                if (i - start_index) > 0 and i % 5 == 0:
                    save_csv_safe(df, OUTPUT_CSV_PATH)
                    print(f"--- Backup salvo na linha {i} ---")

                url = df.iloc[i, 1] 
                if not isinstance(url, str) or 'http' not in url:
                    continue

                print(f"[{i}/{total}] Acessando: {url}")
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        
                        status_code = response.status if response else 0
                        if status_code in [429, 403]:
                            print(f"\n🛑 [LINHA {i}] BLOQUEIO DE IP (429/403) - Tentativa {attempt+1}")
                            save_csv_safe(df, OUTPUT_CSV_PATH)
                            
                            if attempt == 0:
                                print("   > Aguardando 3 minutos...")
                                time.sleep(180)
                            else:
                                print("   > 🧊 Hibernando por 15 minutos para tentar limpar o IP automaticamente...")
                                time.sleep(900)
                            continue

                        titulo = page.title().lower()
                        html_conteudo = page.content().lower()
                        
                        palavras_bloqueio = [
                            "just a moment", "security", "cloudflare", 
                            "verifying", "verificação de segurança", "contra bots maliciosos"
                        ]
                        
                        if any(palavra in titulo for palavra in palavras_bloqueio) or any(palavra in html_conteudo for palavra in palavras_bloqueio):
                            print(f"\n⚠️ [LINHA {i}] CLOUDFLARE DETECTADO! Tentando bypass automático...")
                            page.bring_to_front()
                            
                            try:
                                page.mouse.click(1920 / 2, 1080 / 2)
                            except: pass

                            resolvido = False
                            for _ in range(22): 
                                time.sleep(2)
                                if not any(palavra in page.title().lower() for palavra in palavras_bloqueio):
                                    resolvido = True
                                    break
                            
                            if not resolvido:
                                print("   > ❌ O Cloudflare não liberou. Pulando este perfume por enquanto...")
                                df.loc[i, 'Longevidade'] = 'BLOQUEADO'
                                break 
                            else:
                                print("   > ✅ Cloudflare resolvido! Aguardando a página do perfume carregar...")
                                try:
                                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                                except: pass
                                time.sleep(4)

                        # ANTI-POPUP
                        try:
                            page.keyboard.press("Escape")
                            time.sleep(0.5)
                            texto_popup = page.evaluate("() => document.body.innerText.toLowerCase().includes('join our fragrance community')")
                            if texto_popup:
                                print("   > 🎯 Pop-up chato detectado. Fechando...")
                                page.mouse.click(5, 5) 
                                time.sleep(1)
                        except: pass

                        smart_scroll_and_wait(page)
                        
                        dados = page.evaluate(SCRIPT_EXTRACAO) or {}
                        longevity = str(dados.get('longevity', 'N/A')).title()
                        sillage = str(dados.get('sillage', 'N/A')).title()
                        price = str(dados.get('price', 'N/A')).title()
                        gender = str(dados.get('gender', 'N/A')).title()

                        if longevity == "N/A" and attempt < max_retries - 1:
                            print(f"   > Falha visual. Atualizando (F5)...")
                            page.reload()
                            time.sleep(4)
                            continue

                        df.loc[i, 'Longevidade'] = longevity
                        df.loc[i, 'Sillage'] = sillage
                        df.loc[i, 'Preco'] = price
                        df.loc[i, 'Genero'] = gender

                        print(f"   > Resultado: L:{longevity} | S:{sillage} | $: {price} | Sexo: {gender}")
                        time.sleep(uniform(4.0, 7.0))
                        break 

                    except Exception as e:
                        print(f"   > Erro na tentativa {attempt+1}: {e}")
                        time.sleep(5)
                        if attempt == max_retries - 1:
                            df.loc[i, 'Longevidade'] = 'ERRO'

        except Exception as e:
            print(f"Erro crítico: {e}")
            save_csv_safe(df, OUTPUT_CSV_PATH)
        finally:
            try: browser.close()
            except: pass
            
    return df

def main():
    if os.path.exists(OUTPUT_CSV_PATH):
        print(f"🔄 Encontrei um backup em: {OUTPUT_CSV_PATH}")
        print("   > Carregando dados já processados para retomar...")
        df = pd.read_csv(OUTPUT_CSV_PATH, sep=';')
    elif os.path.exists(CSV_PATH):
        print(f"🆕 Iniciando do zero com o arquivo: {CSV_PATH}")
        df = pd.read_csv(CSV_PATH, sep=';')
    else:
        print("❌ Nenhum arquivo encontrado.")
        return

 # === Adicionadas as novas colunas aqui ===
    cols = ['Longevidade', 'Sillage', 'Preco', 'Genero']
    for col in cols:
        if col not in df.columns: df[col] = ''

    for col in cols:
        df[col] = df[col].fillna('')

    feitos = df[~df['Longevidade'].isin(['', 'ERRO', 'N/A', 'BLOQUEADO'])].shape[0]
    print(f"📊 Progresso atual: {feitos} de {len(df)} perfumes concluídos.")

    start_index = 0
    for i in range(len(df)):
        if df.loc[i, 'Longevidade'] in ['', 'ERRO', 'N/A', 'BLOQUEADO']:
            start_index = i
            break

    print(f"▶️ Retomando a partir da linha: {start_index}")

    run_data_scraper(df, start_index, len(df))
    
    save_csv_safe(df, OUTPUT_CSV_PATH)
    print("✅ Concluído! Salvo em:", OUTPUT_CSV_PATH)

if __name__ == "__main__":
    main()