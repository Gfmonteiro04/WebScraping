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

## 🧠 Tratamento de Dados no Google Colab

Devido à presença de valores faltantes (como "Sem Votos" ou falhas de leitura) nas colunas de performance dos perfumes, a base bruta precisou passar por uma etapa de limpeza e preenchimento inteligente utilizando o Google Colab. 

O processo foi dividido nos seguintes blocos de execução:

**Passo 1: Importações e Carregamento da Base**
Importamos as bibliotecas de Machine Learning e carregamos o arquivo gerado pelo robô.
```python
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

df = pd.read_csv('BancoFinal_Novo.csv', sep=';')
print(f"📊 Linhas carregadas inicialmente: {len(df)}")
```
**Passo 2: Limpeza Inicial e Definição de Variáveis (Features)**
A coluna de preço foi descartada. O algoritmo foi configurado para usar a Marca, Gênero e os três Acordes Principais para definir a "semelhança" entre os perfumes.
```python
if 'Preco' in df.columns:
    df = df.drop(columns=['Preco'])

features = ['Brand', 'Gender', 'MainAccord1', 'MainAccord2', 'MainAccord3']
for col in features:
    df[col] = df[col].fillna('Desconhecido')
```
**Passo 3: Construção do Pipeline (Transformação + KNN)**
Textos não podem ser lidos diretamente por algoritmos matemáticos. Usamos o OneHotEncoder para transformar as características textuais em matrizes numéricas, e configuramos o KNN para buscar os 5 "vizinhos" mais próximos (n_neighbors=5).
```python
preprocessor = ColumnTransformer(
    transformers=[('cat', OneHotEncoder(handle_unknown='ignore'), features)]
)
knn_model = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', KNeighborsClassifier(n_neighbors=5))
])

invalidos = ['Sem Votos', 'N/A', 'BLOQUEADO', 'ERRO', 'nan', 'NaN', '']
```
**Passo 4: Função de Preenchimento Seguro**
Criamos uma função que separa os perfumes com votos válidos (para treinar a IA) dos perfumes com falhas (para receberem a previsão). Isso garante que o número total de linhas do arquivo nunca seja alterado.
```python
def aplicar_knn(df, coluna_alvo):
    df[coluna_alvo] = df[coluna_alvo].astype(str).str.strip()
    
    df_treino = df[~df[coluna_alvo].isin(invalidos)].copy()
    mask_vazio = df[coluna_alvo].isin(invalidos)
    df_vazio = df[mask_vazio].copy()
    
    if df_vazio.empty:
        return df

    knn_model.fit(df_treino[features], df_treino[coluna_alvo])
    previsoes = knn_model.predict(df_vazio[features])
    
    df.loc[mask_vazio, coluna_alvo] = previsoes
    return df
```
**Passo 5: Aplicação e Exportação**
O modelo foi aplicado individualmente para as colunas de "Longevidade" e "Sillage". Por fim, a base totalmente preenchida foi exportada.
```python
print("🤖 Treinando modelo e preenchendo Longevidade...")
df = aplicar_knn(df, 'Longevidade')

print("🤖 Treinando modelo e preenchendo Sillage...")
df = aplicar_knn(df, 'Sillage')

nome_saida = 'BancoFinal_Tratado_KNN.csv'
df.to_csv(nome_saida, sep=';', index=False)
print(f"✅ Finalizado! O arquivo '{nome_saida}' está pronto para download.")
```
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

git clone [https://github.com/Gfmonteiro04/WebScraping.git]

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

**4. Extrai os links e salva as imagens:**

```bash

python playwright_scraper.py

```

**5. Inicie o Catálogo Web:**

```bash

streamlit run app.py

```
