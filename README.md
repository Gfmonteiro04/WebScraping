# 📊 Fragrantica Data Scraper & Analytics
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://essentiacatalogo.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-KNN-orange.svg)

Este projeto é um pipeline de dados ponta a ponta desenvolvido em Python. Ele realiza a extração automatizada de dados de perfumes do site Fragrantica, faz o tratamento inteligente de dados faltantes usando Machine Learning e exibe os resultados em uma interface web interativa.

👉 **[Acesse o Web App: Catálogo de Perfumes Seletos](https://essentiacatalogo.streamlit.app/)**

---

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
Uma interface web em Streamlit para explorar a base de dados tratada, visualizando as estatísticas de cada perfume juntamente com sua respectiva foto.

---

## 🛠️ Tecnologias Utilizadas
* **Playwright:** Automação de navegador e extração de dados brutos.
* **Pandas:** Manipulação, limpeza e estruturação de DataFrames.
* **Scikit-Learn:** Algoritmo KNN para imputação de dados.
* **Streamlit:** Construção do dashboard e interface interativa.
* **Google Colab:** Ambiente de treinamento e execução do modelo de ML.

---

## 🚀 Como Executar Localmente

**1. Clone o repositório:**
```bash
git clone [https://github.com/Gfmonteiro04/WebScraping.git](https://github.com/Gfmonteiro04/WebScraping.git)
cd WebScraping
````
**2. Instala as dependencias:**
```bash
pip install -r requirements.txt
playwright install chromium
```
**3. Extrai as informações e votos dos perfumes:**
```bash
python scraper_dados.py
```
**4.  Extrai os links e salva as imagens:**
```bash
python playwright_scraper.py
```
**5.  Inicie o Catálogo Web:**
```bash
streamlit run app.py
```
