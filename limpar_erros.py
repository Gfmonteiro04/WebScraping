import pandas as pd
import os

# --- CONFIGURAÇÕES ---
# O arquivo que contém os resultados atuais
ARQUIVO_ALVO = 'C:/Users/gfmon/Downloads/BancoFinal_Seletos.csv'

def limpar_erros():
    if not os.path.exists(ARQUIVO_ALVO):
        print(f"Erro: Arquivo {ARQUIVO_ALVO} não encontrado.")
        return

    print("Lendo arquivo para identificar erros...")
    # Lê com ponto e vírgula
    df = pd.read_csv(ARQUIVO_ALVO, sep=';')
    
    # Lista de mensagens de erro que queremos apagar para tentar de novo
    lista_de_erros = [
        'ERRO_DOWNLOAD',
        'ERRO_IMG_NOT_FOUND',
        'ERRO_IO',
        'ERRO_URL_NAO_ENCONTRADA', # O nome que você citou
        'URL_INVALIDA'
    ]

    # Verifica quantas linhas têm esses erros
    # (Filtra onde a coluna 'caminho_imagem_local' está na lista de erros)
    filtro_erros = df['caminho_imagem_local'].isin(lista_de_erros)
    qtd_erros = filtro_erros.sum()

    print(f"Encontrados {qtd_erros} itens com erro.")

    if qtd_erros > 0:
        print("Limpando status para nova tentativa...")
        
        # Substitui os erros por vazio (para o robô achar que falta fazer)
        # Usamos loc para garantir que estamos alterando o DataFrame original
        df.loc[filtro_erros, 'caminho_imagem_local'] = ''
        
        # Salva o arquivo limpo
        df.to_csv(ARQUIVO_ALVO, sep=';', index=False)
        print(f"Pronto! O arquivo {ARQUIVO_ALVO} foi atualizado.")
        print("Agora rode o script principal (scraper) novamente.")
    else:
        print("Nenhum erro encontrado para limpar. Tudo parece correto!")

if __name__ == "__main__":
    limpar_erros()