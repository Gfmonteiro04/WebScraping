import pandas as pd
from playwright.sync_api import sync_playwright
import time 
from random import uniform
import os

# ==========================================
# CONFIGURAÇÕES
# ==========================================
CSV_PATH = 'C:/Users/gfmon/Downloads/BancoFinal_Seletos.csv'
OUTPUT_CSV_PATH = 'BancoFinal_Completo.csv'

# ==========================================
# 1. JAVASCRIPT OTIMIZADO (Baseado em DOM)
# ==========================================
SCRIPT_EXTRACAO = r'''() => {
    function getChartVotes(headerName, options) {
        // 1. Procura EXATAMENTE o elemento que contém o título (ex: "Longevity")
        const allEls = Array.from(document.querySelectorAll('h1, h2, h3, h4, div, span, b, strong'));
        let targetEl = allEls.find(el => el.children.length === 0 && el.textContent.trim().toLowerCase() === headerName.toLowerCase());
        
        if (!targetEl) return "N/A";

        // 2. Sobe na árvore do HTML até achar a "caixa" que engloba o gráfico inteiro
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

        // 3. Limpa o texto dessa caixa específica
        const blockText = container.innerText.replace(/\s+/g, ' ').toLowerCase();

        let bestWinner = "Sem Votos";
        let maxVotes = 0;

        // 4. Analisa cada opção
        for (const option of options) {
            // Regex: Opção + até 30 caracteres ignorados + Número
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
# 2. SCROLL COM "VISÃO" (Espera o Gráfico Aparecer)
# ==========================================
def smart_scroll_and_wait(page):
    try:
        print("   > Procurando gráficos na tela...")
        # Dá pequenos passos para baixo
        for _ in range(8):
            page.mouse.wheel(0, 500)
            time.sleep(0.5)
            
            # O "Olho": Verifica se a palavra 'Longevity' já carregou na tela
            if page.locator("text='Longevity'").is_visible():
                print("   > Gráficos encontrados! Aguardando preenchimento dos votos...")
                # Espera 2 segundos extras para a barrinha do gráfico carregar os números
                time.sleep(2.0)
                return True
                
        # Se tentou rolar 8 vezes e não achou, volta um pouco
        page.mouse.wheel(0, -1000)
        time.sleep(1)
        return False
    except: 
        return False

# ==========================================
# 3. ROBÔ PRINCIPAL
# ==========================================
def run_data_scraper(df, start_index, total):
    i = start_index
    
    # Loop externo: controla a reabertura do navegador
    while i < total:
        # Define um lote de no máximo 40 perfumes por sessão
        limite_batch = min(i + 40, total)
        print(f"\n🚀 Iniciando nova sessão limpa do navegador (Lote: {i} até {limite_batch})...")
        
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
                # Loop interno: processa os perfumes do lote
                while i < limite_batch:
                    
                    if (i - start_index) > 0 and i % 5 == 0:
                        df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
                        print(f"--- Backup salvo na linha {i} ---")

                    # Pula se já processado
                    if 'Longevidade' in df.columns:
                        val = str(df.iloc[i, df.columns.get_loc('Longevidade')])
                        if val not in ['nan', '', 'NaN', 'ERRO', 'N/A']:
                            i += 1
                            continue

                    url = df.iloc[i, 1] 
                    if not isinstance(url, str) or 'http' not in url:
                        i += 1
                        continue

                    print(f"[{i}/{total}] Acessando: {url}")
                    
                    max_retries = 3
                    sucesso_neste_perfume = False
                    
                    for attempt in range(max_retries):
                        try:
                            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                            
                            status_code = response.status if response else 0
                            if status_code in [429, 403]:
                                print(f"🛑 [LINHA {i}] BLOQUEIO (429/403) - Tentativa {attempt+1}/{max_retries}")
                                if attempt == 0:
                                    time.sleep(120)
                                else:
                                    print(f"   > 🧊 Salvando e Hibernando por 15 min...")
                                    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
                                    time.sleep(900)
                                continue

                            titulo = page.title().lower()
                            html_conteudo = page.content().lower()
                            
                            if "just a moment" in titulo or "security" in titulo or "cloudflare" in titulo or "verifying" in html_conteudo:
                                print(f"⚠️ [LINHA {i}] Captcha detectado. Resolva manualmente...")
                                page.bring_to_front()
                                for _ in range(120):
                                    if "just a moment" not in page.title().lower() and "verifying" not in page.content().lower(): 
                                        break
                                    time.sleep(1)
                                time.sleep(3)

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
                            
                            sucesso_neste_perfume = True
                            break # Sai do loop de tentativas

                        except Exception as e:
                            print(f"   > Erro na tentativa {attempt+1}: {e}")
                            time.sleep(5)
                            if attempt == max_retries - 1:
                                df.loc[i, 'Longevidade'] = 'ERRO'

                    # Avança para o próximo perfume independentemente de sucesso ou erro final
                    i += 1

            except Exception as e:
                print(f"Erro crítico no lote: {e}")
                df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
                # O loop 'while i < total' fará o navegador reiniciar e tentar do mesmo 'i'
            finally:
                try: browser.close()
                except: pass
                
            print("♻️ Fechando navegador para limpar histórico e evitar banimento...")
            time.sleep(3)
            
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