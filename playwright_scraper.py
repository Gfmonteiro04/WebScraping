import pandas as pd
from playwright.sync_api import sync_playwright
import time 
from random import uniform
import os
import re

# ==========================================
# CONFIGURAÇÕES
# ==========================================
CSV_PATH = 'C:/Users/gfmon/Downloads/BancoFinal_Seletos.csv'
OUTPUT_CSV_PATH = 'BancoFinal_Completo.csv'

# ==========================================
# 1. NOVO SCRIPT JAVASCRIPT (Lógica Linha-por-Linha)
# ==========================================
SCRIPT_EXTRACAO = '''() => {
    function getChartWinner(titleKeyword, optionsList) {
        // 1. Encontra todos os blocos visíveis que podem conter o gráfico
        const elements = Array.from(document.querySelectorAll('div.cell, div.grid-x, div'));
        
        let targetBlock = null;
        let minLength = 999999;
        const lastOption = optionsList[optionsList.length - 1];

        // 2. Busca o MELHOR bloco: deve conter o Título E a Última Opção
        // Isso evita pegar menus laterais ou textos aleatórios
        for (const el of elements) {
            const text = el.innerText;
            if (!text) continue;
            
            // Verifica se tem "Longevity" (ex) e "Eternal" (ex) no mesmo bloco
            if (text.toLowerCase().includes(titleKeyword.toLowerCase()) && 
                text.toLowerCase().includes(lastOption.toLowerCase())) {
                
                // Pega o menor bloco possível que contenha tudo (para evitar pegar a página inteira)
                if (text.length < minLength && text.length > 50) {
                    minLength = text.length;
                    targetBlock = text;
                }
            }
        }

        if (!targetBlock) return "N/A";

        // 3. Processamento Linha-por-Linha (Correção do Erro de Leitura)
        // Quebra o texto em linhas para analisar cada opção separadamente
        const lines = targetBlock.split(/\\r?\\n/);
        
        let winner = "N/A";
        let maxVotes = -1;
        let totalVotesGlobal = 0;

        for (const option of optionsList) {
            let optionVotes = 0;
            
            // Procura este opção em cada linha do bloco
            for (const line of lines) {
                const cleanLine = line.trim().toLowerCase();
                const cleanOption = option.toLowerCase();

                // Verifica se a linha COMEÇA com a opção (evita confundir "Weak" com "Very Weak")
                if (cleanLine.startsWith(cleanOption)) {
                    // Tenta extrair o número no final da linha
                    // Ex: "Moderate 15" ou "Moderate ... 15"
                    const match = cleanLine.match(/(\d+)$/);
                    if (match) {
                        optionVotes = parseInt(match[1]);
                        break; // Achou, para de procurar essa opção
                    }
                }
            }

            totalVotesGlobal += optionVotes;

            // Atualiza o vencedor
            if (optionVotes > maxVotes) {
                maxVotes = optionVotes;
                winner = option;
            }
        }
        
        // Se a soma de todos os votos for 0, retorna Sem Votos
        if (totalVotesGlobal === 0) return "Sem Votos";
        
        return winner;
    }

    return {
        longevity: getChartWinner("Longevity", ["very weak", "weak", "moderate", "long lasting", "eternal"]),
        sillage: getChartWinner("Sillage", ["intimate", "moderate", "strong", "enormous"]),
        gender: getChartWinner("Gender", ["female", "more female", "unisex", "more male", "male"]),
        price: getChartWinner("Price Value", ["way overpriced", "overpriced", "ok", "good value", "great value"])
    };
}'''

# ==========================================
# 2. SCROLL REFINADO (Para ativar Lazy Loading)
# ==========================================
def human_scroll(page):
    try:
        print("   > Escaneando página para carregar gráficos...")
        # Desce a página em "chunks" visuais
        viewport_height = page.viewport_size['height']
        for _ in range(8): 
            page.mouse.wheel(0, viewport_height * 0.7)
            time.sleep(uniform(0.5, 0.8))
        
        # Sobe um pouco para garantir que o meio da página (onde estão os gráficos) foi renderizado
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

                # Verifica se já tem dados (para pular)
                if 'Longevidade' in df.columns:
                    val = str(df.iloc[i, df.columns.get_loc('Longevidade')])
                    if val not in ['nan', '', 'NaN', 'ERRO', 'N/A', 'Sem Votos']:
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

                    df.loc[i, 'Longevidade'] = longevity
                    df.loc[i, 'Sillage'] = sillage
                    df.loc[i, 'Genero_Voto'] = gender
                    df.loc[i, 'Preco_Voto'] = price

                    print(f"   > Resultado: L:{longevity} | S:{sillage} | G:{gender} | $:{price}")
                    
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

    cols = ['Longevidade', 'Sillage', 'Genero_Voto', 'Preco_Voto']
    for col in cols:
        if col not in df.columns: df[col] = ''

    run_data_scraper(df, 0, len(df))
    
    df.to_csv(OUTPUT_CSV_PATH, sep=';', index=False)
    print("Concluído! Salvo em:", OUTPUT_CSV_PATH)

if __name__ == "__main__":
    main()