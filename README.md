# 🐺 WatchdogApp

O **WatchdogApp** é um monitor de processos inteligente desenvolvido em Python. Ele foi projetado para garantir que aplicações críticas permaneçam em execução, detectando encerramentos inesperados e tentando reiniciá-los automaticamente com base em regras personalizáveis.

## 🚀 Funcionalidades

- **Monitoramento em Tempo Real:** Acompanha o status de aplicativos e processos de sistema.
- **Auto-Restart Inteligente:** Reinicia processos automaticamente se forem fechados, com suporte a regras de erro do Windows ou reinicialização constante.
- **Interface Intuitiva:** Desenvolvida com `customtkinter` para uma experiência moderna e amigável.
- **Splash Screen:** Tela de abertura personalizada ao iniciar o programa.
- **Minimizar para Tray:** Opção de ocultar o app na bandeja do sistema (perto do relógio) para economizar espaço na barra de tarefas.
- **Gestão de Logs:** Registros diários detalhados com limpeza automática de arquivos antigos.

## 🛠️ Tecnologias Utilizadas

- **Python 3.12+**
- **CustomTkinter:** Interface gráfica moderna.
- **Pystray:** Integração com a bandeja do sistema (System Tray).
- **Psutil:** Gestão e monitoramento de processos do sistema.
- **PyInstaller:** Compilação para executável (.exe).

## 📦 Como usar o Executável

Se você deseja apenas utilizar o programa sem instalar o Python:
1. Vá até a seção [Releases](https://github.com/DanBenites/WatchdogApp/releases/latest) deste repositório.
2. Baixe o arquivo `WatchdogApp.exe`.
3. Execute o programa (não requer instalação).

## 👨‍💻 Como rodar o código (Desenvolvedores)

1. Clone o repositório:
```bash
git clone [https://github.com/SEU_USUARIO/WatchdogApp.git](https://github.com/SEU_USUARIO/WatchdogApp.git)
```
2. Instale as dependências:
```Bash
pip install -r requirements.txt
```
3. Execute o script principal:
```Bash
python main.py
```
Desenvolvido por DanBenites
