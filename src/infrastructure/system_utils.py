import psutil
import os
import sys
import winreg
import sys
import os

try:
    import win32gui, win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class SystemUtils:
    @staticmethod
    def verificar_processos_ausentes(lista_nomes_alvo):
        """ 
        Recebe uma lista de nomes (ex: ['chrome.exe', 'notepad.exe'])
        Retorna uma lista contendo apenas os que NÃO estão rodando no momento.
        """
        # Cria um conjunto com tudo que está rodando agora (para busca rápida)
        ativos_agora = {p.info['name'].lower() for p in psutil.process_iter(['name'])}
        
        ausentes = []
        for nome in lista_nomes_alvo:
            if nome.lower() not in ativos_agora:
                ausentes.append(nome)
        
        return ausentes

    @staticmethod
    def get_processos_com_janela_visivel():
        pids = set()
        if not HAS_WIN32: return pids
        
        def callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                pids.add(pid)
        
        win32gui.EnumWindows(callback, None)
        return pids

    _usuario_cache = None

    @staticmethod
    def get_usuario_atual():
        if SystemUtils._usuario_cache is None:
            try:
                SystemUtils._usuario_cache = os.getlogin().lower()
            except:
                SystemUtils._usuario_cache = ""
        return SystemUtils._usuario_cache

    @staticmethod
    def listar_processos_agrupados(termo_busca=""):
        usuario_atual = SystemUtils.get_usuario_atual()
        pids_visiveis = SystemUtils.get_processos_com_janela_visivel()
        
        grupos = {
            "apps": {},     # Primeiro Plano
            "back": {},     # Segundo Plano
            "system": {}    # Sistema
        }

        for proc in psutil.process_iter(['pid', 'name', 'exe', 'username']):
            try:
                info = proc.info
                nome = info['name']
                if not nome: continue
                if termo_busca and termo_busca not in nome.lower(): continue

                # Classificação
                if usuario_atual not in (info['username'] or "").lower():
                    target = grupos["system"]
                elif info['pid'] in pids_visiveis:
                    target = grupos["apps"]
                else:
                    target = grupos["back"]

                # Agrupamento
                if nome in target:
                    target[nome]['count'] += 1
                else:
                    target[nome] = {'count': 1, 'path': info['exe'] or "", 'full_name': nome}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return grupos

    @staticmethod
    def obter_status_recursos():
        return psutil.cpu_percent(), psutil.virtual_memory().percent
    
    @staticmethod
    def definir_inicializacao_windows(ativar: bool):
        """ Adiciona ou remove o programa da inicialização do Windows (Registro) """
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "WatchdogApp"
        
        # Lógica para pegar o caminho correto (seja .py ou .exe compilado)
        if getattr(sys, 'frozen', False):
            # Se for executável (PyInstaller)
            app_path = f'"{sys.executable}" --startup'
        else:
            # Se for script Python rodando
            script_path = os.path.abspath(sys.argv[0])
            # Executa: "python.exe" "caminho/do/main.py"
            app_path = f'"{sys.executable}" "{script_path}" --startup'

        try:
            # Abre a chave do registro
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            
            if ativar:
                # Cria o valor
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            else:
                # Tenta deletar
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass # Já não existia, tudo bem
            
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Erro ao alterar registro do Windows: {e}")
            return False
    
    @staticmethod
    def resource_path(relative_path):
        """ Retorna o caminho absoluto para recursos, funcionando no PyInstaller e Script """
        try:
            base_path = sys._MEIPASS
        except Exception:
            # Se for Script Python (Dev) ou Executável sem MEIPASS - Como no ato de Reinicialização do Windows
            # Pega o diretório onde está o arquivo main.py (ou o .exe), e NÃO o diretório atual do cmd
            base_path = os.path.dirname(os.path.abspath(sys.argv[0]))

        return os.path.join(base_path, relative_path)
    
    @staticmethod
    def obter_hwid():
        """ Obtém o UUID da placa-mãe via WMIC para identificação única """
        try:
            import subprocess
            output = subprocess.check_output(
                "wmic csproduct get uuid", 
                shell=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            ).decode('utf-8').split('\n')[1].strip()
            return output if output else "HWID_DESCONHECIDO"
        except Exception as e:
            print(f"Erro ao obter HWID: {e}")
            return "HWID_DESCONHECIDO"

    @staticmethod
    def enviar_notificacao_windows(titulo: str, mensagem: str):
        """ Envia notificação nativa para a Central de Ações do Windows 10/11 """
        try:
            import subprocess
            ps_script = f"""
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $toastXml = [xml] $template.GetXml()
            $toastXml.GetElementsByTagName("text")[0].AppendChild($toastXml.CreateTextNode("{titulo}")) > $null
            $toastXml.GetElementsByTagName("text")[1].AppendChild($toastXml.CreateTextNode("{mensagem}")) > $null
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($toastXml.OuterXml)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("WatchdogApp").Show($toast)
            """
            subprocess.run(["powershell", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            print(f"Erro ao enviar notificação: {e}")