import pandas as pd
import os
import numpy as np

# --- CONFIGURAÇÃO ---
ARQUIVO_PRINCIPAL = 'BancoFinal_com_imagens.csv' # O arquivo que vai receber os dados
ARQUIVO_DOADOR = 'BancoFinal_pc1.csv'            # O arquivo que tem as fotos (PC1)
ARQUIVO_SAIDA = 'BancoFinal_UNIFICADO.csv'

def forcar_unificacao():
    if not os.path.exists(ARQUIVO_PRINCIPAL) or not os.path.exists(ARQUIVO_DOADOR):
        print("Erro: Arquivos não encontrados.")
        return

    print("Carregando arquivos...")
    df_main = pd.read_csv(ARQUIVO_PRINCIPAL, dtype=str) # Lê tudo como texto para evitar erro
    df_pc1 = pd.read_csv(ARQUIVO_DOADOR, dtype=str)

    # Garante que a coluna existe
    col_img = 'caminho_imagem_local'
    if col_img not in df_main.columns: df_main[col_img] = np.nan
    if col_img not in df_pc1.columns: df_pc1[col_img] = np.nan

    # Limpeza: Transforma textos vazios ou 'nan' em Nulo real
    # Isso é crucial para o Python entender o que é dado e o que é lixo
    replacements = {'': np.nan, 'nan': np.nan, 'None': np.nan}
    df_main[col_img] = df_main[col_img].replace(replacements)
    df_pc1[col_img] = df_pc1[col_img].replace(replacements)

    # Configura o ID (primeira coluna) como índice para alinhar as linhas
    col_id = df_main.columns[0]
    df_main.set_index(col_id, inplace=True)
    df_pc1.set_index(col_id, inplace=True)

    print("Identificando imagens novas no PC1...")
    
    # Filtra apenas as linhas do PC1 que REALMENTE têm imagem
    # O comando notna() pega tudo que não é nulo
    pc1_com_imagem = df_pc1[df_pc1[col_img].notna()]
    
    qtd_novas = len(pc1_com_imagem)
    print(f"O arquivo do PC1 tem {qtd_novas} imagens válidas para transferir.")

    # --- A TRANSFERÊNCIA ---
    # O comando update usa o índice (ID) para atualizar.
    # Ele pega os valores do pc1_com_imagem e SOBRESCREVE no df_main
    df_main.update(pc1_com_imagem)

    # Restaura o formato original
    df_main.reset_index(inplace=True)

    # Salva
    df_main.to_csv(ARQUIVO_SAIDA, index=False)
    print("="*40)
    print(f"CONCLUÍDO! Arquivo salvo em: {ARQUIVO_SAIDA}")
    print("Abra o app.py apontando para este arquivo e verifique os primeiros itens.")
    print("="*40)

if __name__ == "__main__":
    forcar_unificacao()