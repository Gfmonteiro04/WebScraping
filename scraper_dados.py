import pandas as pd
from playwright.sync_api import sync_playwright
import time 
from random import uniform
import os

# ==========================================
# CONFIGURAÇÕES
# ==========================================
CSV_PATH = 'C:/Users/gfmon/Documents/scraper/BancoFinal_Tratado_KNN.csv'
OUTPUT_CSV_PATH = 'C:/Users/gfmon/Documents/scraper/BancoFinal_Tratado_KNN.csv'

# ==========================================
# 1. JAVASCRIPT OTIMIZADO (Baseado em DOM)
# ==========================================
SCRIPT_EXTRACAO = r'''() => {
    function getChartVotes(headerName, options) {
        const allEls = Array.from(document.querySelectorAll('h1, h2, h3, h4, div, span, b, strong'));
        let targetEl = allEls.find(el => el.children.length === 0 && el.textContent.trim().toLowerCase() === headerName.toLowerCase());
        
        if (!targetEl) return "N/A";

        let container = targetEl.parentElement;
        let maxDepth = 10;
        while (container && maxDepth > 0) {
            if (container.innerText.toLowerCase().includes(options[0].toLowerCase())) {
                break;
            }
            container = container.parentElement;
            maxDepth--;
        }

        if (!container || maxDepth === 0) return "N/A";

        const blockText = container.innerText.replace(/\s+/g, ' ').toLowerCase();

        let bestWinner = "Sem Votos";
        let maxVotes = 0;

        for (const option of options) {
            const optClean = option.toLowerCase();
            const regex = new RegExp(optClean + "[^0-9]{0,30}(\\d+)");
            const match = blockText.match(regex);

            if (match) {
                const votes = parseInt(match[1], 10);
                if (votes > maxVotes && votes > 0) {
                    maxVotes = votes;
                    bestWinner = option;
                }
            }
        }

        return bestWinner;
    }

    return {
        longevity: getChartVotes("Longevity", ["very weak", "weak", "moderate", "long lasting", "eternal"]),
        sillage: getChartVotes("Sillage", ["intimate", "moderate", "strong", "enormous"])
    };
}'''

# ==========================================
# 2. SCROLL COM "VISÃO"
# ==========================================
def smart_scroll_and_wait(page):
    try:
        print("   > Procurando gráficos na tela...")
        for _ in range(8):
            page.mouse.wheel(0, 500)
            time.sleep(0.5)
            
            if page.locator("text='Longevity'").is_visible():
                print("   > Gráficos encontrados! Aguardando preenchimento dos votos...")
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
            viewport={'width': 1920, 'height': 1080}
        )
        context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = context.new_page()

        try:
            for i in range(start_index, total):
                
                if (i - start_index) > 0 and i % 5 == 0:
                    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
                    print(f"--- Backup salvo na linha {i} ---")

                if 'Longevidade' in df.columns:
                    val = str(df.iloc[i, df.columns.get_loc('Longevidade')])
                    if val not in ['nan', '', 'NaN', 'ERRO', 'N/A']:
                        continue

                url = df.iloc[i, 1] 
                if not isinstance(url, str) or 'http' not in url:
                    continue

                print(f"[{i}/{total}] Acessando: {url}")
                
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        
                        # === PAUSA MANUAL DE IP (Erro 429/403) ===
                        status_code = response.status if response else 0
                        if status_code in [429, 403]:
                            print(f"\n🛑 [LINHA {i}] BLOQUEIO SEVERO DE IP (429/403)!")
                            print("🚨 O Fragrantica bloqueou a sua conexão de internet. 🚨")
                            print("👉 O QUE FAZER AGORA:")
                            print("   1. Salvei seus dados até aqui.")
                            print("   2. Conecte no 4G do celular OU reinicie seu modem de internet.")
                            df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
                            
                            input("\n⏳ Após trocar a internet, clique aqui no terminal e pressione [ENTER] para continuar...")
                            
                            print("🔄 Retomando a extração com a nova conexão...")
                            continue

                        # === CAPTCHA E CLOUDFLARE ===
                        titulo = page.title().lower()
                        html_conteudo = page.content().lower()
                        
                        palavras_bloqueio = [
                            "just a moment", "security", "cloudflare", 
                            "verifying", "verificação de segurança", "contra bots maliciosos"
                        ]
                        
                        if any(palavra in titulo for palavra in palavras_bloqueio) or any(palavra in html_conteudo for palavra in palavras_bloqueio):
                            print(f"\n⚠️ [LINHA {i}] CLOUDFLARE DETECTADO!")
                            print("👉 O site bloqueou a tela com uma verificação.")
                            page.bring_to_front()
                            
                            input("⏳ Resolva o Captcha lá no navegador, espere o perfume carregar, e DEPOIS aperte [ENTER] aqui no terminal...")
                            
                            print("🔄 Retomando a extração...")
                            time.sleep(2)

                        smart_scroll_and_wait(page)
                        
                        dados = page.evaluate(SCRIPT_EXTRACAO) or {}
                        longevity = str(dados.get('longevity', 'N/A')).title()
                        sillage = str(dados.get('sillage', 'N/A')).title()

                        if longevity == "N/A" and attempt < max_retries - 1:
                            print(f"   > Falha visual. Atualizando (F5)...")
                            page.reload()
                            time.sleep(4)
                            continue

                        df.loc[i, 'Longevidade'] = longevity
                        df.loc[i, 'Sillage'] = sillage

                        print(f"   > Resultado: L:{longevity} | S:{sillage}")
                        time.sleep(uniform(4.0, 7.0))
                        break 

                    except Exception as e:
                        print(f"   > Erro na tentativa {attempt+1}: {e}")
                        time.sleep(5)
                        if attempt == max_retries - 1:
                            df.loc[i, 'Longevidade'] = 'ERRO'

        except Exception as e:
            print(f"Erro crítico: {e}")
            df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
        finally:
            try: browser.close()
            except: pass
            
    return df

def main():
    if os.path.exists(OUTPUT_CSV_PATH):
        print(f"🔄 Encontrei um backup em: {OUTPUT_CSV_PATH}")
        print("   > Carregando dados já processados para retomar...")
        try: df = pd.read_csv(OUTPUT_CSV_PATH, sep=';')
        except: df = pd.read_csv(OUTPUT_CSV_PATH, sep=',')
    elif os.path.exists(CSV_PATH):
        print(f"🆕 Iniciando do zero com o arquivo: {CSV_PATH}")
        try: df = pd.read_csv(CSV_PATH, sep=';')
        except: df = pd.read_csv(CSV_PATH, sep=',')
    else:
        print("❌ Nenhum arquivo encontrado.")
        return

    cols = ['Longevidade', 'Sillage']
    for col in cols:
        if col not in df.columns: df[col] = ''

    feitos = df[~df['Longevidade'].isin(['', 'nan', 'NaN', 'ERRO', 'N/A']) & df['Longevidade'].notna()].shape[0]
    print(f"📊 Progresso atual: {feitos} de {len(df)} perfumes concluídos.")

    run_data_scraper(df, 0, len(df))
    
    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
    print("✅ Concluído! Salvo em:", OUTPUT_CSV_PATH)

if __name__ == "__main__":
    main()