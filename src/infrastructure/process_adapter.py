# src/infrastructure/process_adapter.py
import os
import subprocess
import psutil

class ProcessAdapter:
    """Responsável exclusivo por enviar comandos de execução e encerramento para o Windows"""

    @staticmethod
    def iniciar_processo(path, minimizado=False, oculto=False):
        """Inicia um programa com suporte a modos silenciosos"""
        if not path or not os.path.exists(path):
            return False, "Caminho do executável não encontrado."

        try:
            si = subprocess.STARTUPINFO()
            flags = 0x00000008 # DETACHED_PROCESS (Processo independente do Watchdog)

            if minimizado or oculto:
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                if oculto:
                    si.wShowWindow = 0  # SW_HIDE
                elif minimizado:
                    si.wShowWindow = 2  # SW_SHOWMINIMIZED
            
            subprocess.Popen(path, startupinfo=si, creationflags=flags)
            return True, "Processo iniciado com sucesso."
        except Exception as e:
            return False, f"Erro ao iniciar: {str(e)}"

    @staticmethod
    def encerrar_processo(nome_exe, graceful=False, timeout=10):
        """Procura todos os processos com este nome e mata a árvore (processos filhos) de cada um"""
        sucesso = False
        for proc in psutil.process_iter(['name', 'pid']):
            try:
                if proc.info['name'] and proc.info['name'].lower() == nome_exe.lower():
                    parent = psutil.Process(proc.info['pid'])
                    
                    # 1. Tenta o fechamento elegante (Graceful) usando o Windows Nativo
                    if graceful:
                        # O taskkill SEM o /F envia o sinal WM_CLOSE (Elegante)
                        subprocess.run(f'taskkill /PID {parent.pid}', shell=True, capture_output=True)
                        try:
                            parent.wait(timeout) # Aguarda fechar
                            sucesso = True
                            continue # Vai para o próximo processo com este nome
                        except psutil.TimeoutExpired:
                            pass # Tempo esgotou, o usuário não clicou em "Salvar". Desce para a Guilhotina!

                    # 2. A Guilhotina: Force Kill em Árvore
                    children = parent.children(recursive=True)
                    for child in children:
                        try: child.kill()
                        except psutil.NoSuchProcess: pass
                    
                    parent.kill()
                    sucesso = True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass 

        if sucesso: return True, f"'{nome_exe}' encerrado(s) com sucesso."
        return False, f"Nenhum processo ativo encontrado para '{nome_exe}'."