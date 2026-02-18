import os
import subprocess
from pathlib import Path
from PIL import Image
import customtkinter as ctk
from ..infrastructure.system_utils import SystemUtils

try:
    import win32gui, win32ui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    print("Aviso: 'pywin32' não instalado. Ícones reais não serão mostrados. (pip install pywin32)")

class IconeManager:
    """ Gerencia a extração, cache em disco e carregamento de ícones """
    
    # Mapeamento necessário: Nome do Processo -> Nome do Pacote na Loja
    # Sem isso, não conseguimos achar a pasta da Calculadora, Fotos, etc.
    UWP_MAP = {
        # --- Utilitários Padrão do Windows ---
        "calculatorapp.exe": "Microsoft.WindowsCalculator",
        "wincalculator.exe": "Microsoft.WindowsCalculator",      # Win10 Antigo
        "windowscamera.exe": "Microsoft.WindowsCamera",          # Câmera
        "windowsmaps.exe": "Microsoft.WindowsMaps",              # Mapas
        "windowsalarms.exe": "Microsoft.WindowsAlarms",          # Relógio e Alarmes
        "time.exe": "Microsoft.WindowsAlarms",                   # Variação do Relógio
        "soundrecorder.exe": "Microsoft.WindowsSoundRecorder",   # Gravador de Som (Novo)
        "winstore.app.exe": "Microsoft.WindowsStore",            # Microsoft Store
        "bingweather.exe": "Microsoft.BingWeather",              # Clima / Tempo
        "microsoft.msn.weather.exe": "Microsoft.BingWeather",    # Clima (Processo real)
        "feedbackhub.exe": "Microsoft.WindowsFeedbackHub",       # Hub de Comentários
        "gethelp.exe": "Microsoft.GetHelp",                      # Obter Ajuda

        # --- Ferramentas de Sistema & Produtividade ---
        "notepad.exe": "Microsoft.WindowsNotepad",               # Bloco de Notas (Win11)
        "mspaint.exe": "Microsoft.Paint",                        # Paint (Win11)
        "snippingtool.exe": "Microsoft.ScreenSketch",            # Ferramenta de Captura (Win11)
        "screensketch.exe": "Microsoft.ScreenSketch",            # Ferramenta de Captura (Win10)
        "windowsterminal.exe": "Microsoft.WindowsTerminal",      # Windows Terminal
        "microsoft.notes.exe": "Microsoft.MicrosoftStickyNotes", # Notas Autoadesivas (Sticky Notes)
        "hxoutlook.exe": "microsoft.windowscommunicationsapps",  # Email e Calendário
        "onenoteim.exe": "Microsoft.Office.OneNote",             # OneNote for Windows
        "todo.exe": "Microsoft.Todos",                           # Microsoft To Do
        "todos.exe": "Microsoft.Todos",                          # Variação
        "peopleapp.exe": "Microsoft.People",                     # Aplicativo Pessoas

        # --- Multimídia (Fotos, Música, Vídeo) ---
        "photos.exe": "Microsoft.Windows.Photos",                # Fotos
        "microsoft.photos.exe": "Microsoft.Windows.Photos",
        "video.ui.exe": "Microsoft.ZuneVideo",                   # Filmes e TV
        "music.ui.exe": "Microsoft.ZuneMusic",                   # Groove Música (Legado)
        "microsoft.media.player.exe": "Microsoft.Media.Player",  # Novo Media Player (Win11)
        
        # --- Comunicação & Social ---
        "whatsapp.exe": "WhatsApp",                              # WhatsApp
        "skypeapp.exe": "Microsoft.SkypeApp",                    # Skype
        "yourphone.exe": "Microsoft.YourPhone",                  # Vincular ao Celular
        "phoneexperiencehost.exe": "Microsoft.YourPhone",        # Variação do Vincular ao Celular

        # --- Jogos e Xbox ---
        "gamebar.exe": "Microsoft.XboxGamingOverlay",            # Xbox Game Bar
        "xboxpcapp.exe": "Microsoft.GamingApp",                  # Aplicativo Xbox
        "solitaire.exe": "Microsoft.MicrosoftSolitaireCollection" # Microsoft Solitaire
    }

    def __init__(self):
        app_data = os.getenv('APPDATA')
        self.cache_dir = os.path.join(app_data, "WatchdogApp", "cache_icons")
        self.memoria_cache = {}
        
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir)
            except Exception as e:
                print(f"Erro ao criar pasta de cache: {e}")
                
        self._icons = {} # Inicializa o dicionário de ícones do sistema
        
        # Mapeamento dos ícones internos do app
        icon_files = {
            "play": SystemUtils.resource_path(os.path.join("assets", "icons", "play.png")),
            "stop": SystemUtils.resource_path(os.path.join("assets", "icons", "stop.png")),
            "add": SystemUtils.resource_path(os.path.join("assets", "icons", "add.png")),
            "refresh": SystemUtils.resource_path(os.path.join("assets", "icons", "refresh.png")),
            "close_console": SystemUtils.resource_path(os.path.join("assets", "icons", "close_console.png")),
            "copy": SystemUtils.resource_path(os.path.join("assets", "icons", "copy.png")),
            "folder": SystemUtils.resource_path(os.path.join("assets", "icons", "folder.png")),
            "file_save": SystemUtils.resource_path(os.path.join("assets", "icons", "file_save.png")),
        }

        # Carrega cada ícone se o arquivo existir
        for name, path in icon_files.items():
            if os.path.exists(path):
                img = Image.open(path)
                # Criando o objeto CTkImage para ser usado nos botões
                self._icons[name] = ctk.CTkImage(light_image=img, dark_image=img, size=(16, 16))
            else:
                print(f"Aviso: Ícone não encontrado em {path}")
                self._icons[name] = None
                
    # def load(self, name, path):
    #     img = Image.open(path)
    #     self._icons[name] = ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))

    def __getitem__(self, name):
        return self._icons.get(name)

    def get_icon_path(self, nome_processo):
        safe_name = "".join([c for c in nome_processo if c.isalnum() or c in (' ', '.', '_')]).strip()
        return os.path.join(self.cache_dir, f"{safe_name}.png")
    
    def extrair_e_salvar(self, nome_processo, path):
        img = None

        # --- PASSO 1: Tenta extrair como aplicativo comum (.EXE) ---
        if path and os.path.exists(path):
            img = self._tenta_extrair_win32(path)
        
        # --- PASSO 2: Se falhou, verifica se é um App UWP (Loja) ---
        if not img:
            img = self._tenta_extrair_uwp(nome_processo)

        # --- PASSO 3: Se ainda falhou, usa o ícone Genérico do Sistema ---
        if not img:
            try:
                # Pega o ícone padrão de "Janela" do Windows
                system_icon_path = os.path.join(os.environ['SystemRoot'], 'System32', 'imageres.dll')
                img = self._tenta_extrair_win32(system_icon_path, index=11) 
            except: pass

        # --- FINALIZAÇÃO: Redimensiona e Salva ---
        if img:
            try:
                # OBRIGATÓRIO: Força o tamanho 32x32 para padronizar
                img = img.resize((32, 32), Image.Resampling.LANCZOS)

                save_path = self.get_icon_path(nome_processo)
                img.save(save_path, "PNG")
                return img
            except: pass
            
        return None

    def _tenta_extrair_win32(self, path, index=0):
        """ Extrai ícone embutido em DLL ou EXE """
        if not HAS_WIN32: return None
        try:
            large, small = win32gui.ExtractIconEx(path, index)
            hIcon = large[0] if large else None
            if not hIcon: return None

            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, 32, 32)
            hdc = hdc.CreateCompatibleDC()
            hdc.SelectObject(hbmp)
            
            # Desenha com fundo transparente
            win32gui.DrawIconEx(hdc.GetHandleOutput(), 0, 0, hIcon, 32, 32, 0, None, 3)
            
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            
            # Tenta ler com canal Alpha (Transparência)
            img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRA', 0, 1)
            
            # Correção para ícones "Fantasmas" (sem canal alpha definido)
            if img.getextrema()[3][1] == 0:
                 img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

            win32gui.DestroyIcon(hIcon)
            if small: win32gui.DestroyIcon(small[0])
            return img
        except: return None

    def _tenta_extrair_uwp(self, nome_processo):
        """ Usa PowerShell para achar o ícone real do pacote UWP """
        nome_limpo = nome_processo.lower()
        if nome_limpo not in self.UWP_MAP: return None
            
        package_name = self.UWP_MAP[nome_limpo]
        
        try:
            def run_ps(cmd):
                command = f'powershell -ExecutionPolicy Bypass -Command "{cmd}"'
                res = subprocess.run(command, capture_output=True, text=True, shell=True, encoding='utf-8')
                return res.stdout.strip()

            install_loc = run_ps(f"(Get-AppxPackage -Name {package_name}).InstallLocation")
            if not install_loc: return None
            
            install_path = Path(install_loc)
            logo_rel = run_ps(f"(Get-AppxPackage -Name {package_name} | Get-AppxPackageManifest).package.properties.logo")
            if not logo_rel: return None

            logo_stem = Path(logo_rel).stem
            # Busca recursiva pelo arquivo de imagem
            matches = list(install_path.glob(f"**/{logo_stem}*.png"))
            
            if matches:
                # Pega o maior arquivo (melhor qualidade) para depois reduzirmos
                matches.sort(key=lambda p: p.stat().st_size, reverse=True)
                return Image.open(matches[0])
        except: pass
        return None
    
    def carregar(self, nome_processo, path):
        # 1. RAM Cache
        if nome_processo in self.memoria_cache: return self.memoria_cache[nome_processo]
        
        # 2. Disk Cache
        save_path = self.get_icon_path(nome_processo)
        if os.path.exists(save_path):
            try:
                img = Image.open(save_path)
                # Garante que carregamos no tamanho certo na UI
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))
                self.memoria_cache[nome_processo] = ctk_img
                return ctk_img
            except: pass 

        # 3. Extração Nova (Processo pesado)
        img = self.extrair_e_salvar(nome_processo, path)
        if img:
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))
            self.memoria_cache[nome_processo] = ctk_img
            return ctk_img
        
        return None
    