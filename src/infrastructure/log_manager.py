import os
import glob
from datetime import datetime, timedelta

class LogManager:
    def __init__(self):
        app_data= os.getenv('APPDATA')
        self.log_dir = os.path.join(app_data, "WatchdogApp", "logs")
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
            except OSError:
                pass

    def escrever(self, mensagem):
        """ Escreve a mensagem no arquivo do dia atual de forma segura (append) """
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            arquivo = os.path.join(self.log_dir, f"log_{hoje}.txt")
            
            # O modo 'a' (append) grava no final e fecha o arquivo imediatamente.
            # Isso garante que se o PC desligar da tomada 1ms depois, o log está salvo.
            with open(arquivo, "a", encoding="utf-8") as f:
                f.write(mensagem + "\n")
        except Exception as e:
            print(f"Erro ao salvar log: {e}")

    def ler_conteudo_dia(self):
        """ Lê todo o histórico do dia atual para exibir na tela ao abrir """
        try:
            hoje = datetime.now().strftime("%Y-%m-%d")
            arquivo = os.path.join(self.log_dir, f"log_{hoje}.txt")
            
            if os.path.exists(arquivo):
                with open(arquivo, "r", encoding="utf-8") as f:
                    return f.read()
        except Exception:
            pass # Se der erro na leitura, retorna vazio
        return ""

    def limpar_antigos(self, dias_max):
        # (Mantém o código de limpeza igual ao anterior...)
        try:
            if dias_max <= 0: return
            data_limite = datetime.now() - timedelta(days=dias_max)
            padrao = os.path.join(self.log_dir, "log_*.txt")
            
            for arquivo_path in glob.glob(padrao):
                try:
                    nome = os.path.basename(arquivo_path)
                    data_str = nome.replace("log_", "").replace(".txt", "")
                    data_obj = datetime.strptime(data_str, "%Y-%m-%d")
                    
                    if data_obj < data_limite:
                        os.remove(arquivo_path)
                except: continue
        except Exception as e:
            print(f"Erro limpeza: {e}")