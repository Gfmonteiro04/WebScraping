# 📊 Fragrantica Data Scraper & Analytics

Este projeto é um pipeline de dados ponta a ponta desenvolvido em Python. Ele realiza a extração automatizada de dados de perfumes do site Fragrantica, faz o tratamento inteligente de dados faltantes usando Machine Learning e exibe os resultados em uma interface interativa.

## ⚙️ Arquitetura do Projeto

O projeto é dividido em três etapas principais:

### 1. Web Scraping Avançado (Playwright + JavaScript)
Um robô construído para navegar no Fragrantica e contornar proteções antibot (Cloudflare) e pop-ups. 
* Utiliza injeção de JavaScript no DOM para ler gráficos dinâmicos de **Longevidade, Projeção (Sillage), Custo-Benefício e Gênero**.
* Lida com **Lazy Loading** (carregamento preguiçoso) simulando rolagens humanas.
* Extrai as URLs das imagens em alta qualidade de cada perfume.

### 2. Tratamento de Dados com Machine Learning (Scikit-Learn)
Para lidar com perfumes recém-lançados ou impopulares ("Sem Votos"), foi implementado um modelo **K-Nearest Neighbors (KNN)**.
* O algoritmo analisa as "features" do perfume (Marca, Gênero e Acordes Principais).
* Encontra os 5 perfumes matematicamente mais parecidos na base de dados.
* Imputa os votos faltantes com base nos vizinhos mais próximos, garantindo que 100% da base tenha dados precisos e coerentes sem necessidade de excluir linhas.

### 3. Visualização de Dados (`app.py`)
Uma interface web para explorar a base de dados tratada, visualizando as estatísticas de cada perfume juntamente com sua respectiva foto.

## 🛠️ Tecnologias Utilizadas
* **Python 3**
* **Playwright:** Automação de navegador e extração de dados.
* **Pandas:** Manipulação e estruturação de DataFrames.
* **Scikit-Learn:** Algoritmo KNN para imputação de dados.
* **Google Colab:** Ambiente de treinamento do modelo de Machine Learning.

## 🚀 Como Executar Localmente

1. Clone o repositório:
```bash
 git clone https://github.com/Gfmonteiro04/WebScraping.git

pip install -r requirements.txt
playwright install chromium

python scraper_dados.py

python app.py
