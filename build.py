import PyInstaller.__main__
import customtkinter
import os

# Pega o caminho onde o CustomTkinter está instalado no seu PC
ctk_path = os.path.dirname(customtkinter.__file__)

# Define os argumentos para gerar o EXE
args = [
    'main.py',                       # Seu arquivo principal
    '--name=WatchdogApp',            # Nome do arquivo final
    '--onefile',                     # Cria um único arquivo .exe (portátil)
    '--noconsole',                   # Não mostra aquela tela preta de cmd
    '--icon=assets/icons/app_icon.ico',    # Ícone do arquivo .exe (na área de trabalho)
    '--clean',                       # Limpa cache de builds anteriores
    
    # Adiciona a pasta de assets dentro do executável
    # O formato é "origem;destino" (no Windows usa ponto e vírgula)
    '--add-data=assets;assets',      
    
    # Adiciona os temas do CustomTkinter (obrigatório senão dá erro)
    f'--add-data={ctk_path};customtkinter',
    
    # Garante que bibliotecas críticas sejam incluídas
    '--hidden-import=PIL._tkinter_finder',
    '--hidden-import=pystray',
    '--hidden-import=win32timezone',
]

print("🔨 Iniciando a criação do executável...")
PyInstaller.__main__.run(args)
print("✅ Sucesso! Seu executável está na pasta 'dist'.")