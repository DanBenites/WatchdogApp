import sys
import os
import threading
import customtkinter as ctk
from datetime import datetime
from PIL import Image

# Camadas
from ..domain.models import AppConfig
from ..infrastructure.persistence import PersistenceRepository
from ..infrastructure.system_utils import SystemUtils
from ..infrastructure.icon_manager import IconeManager
from ..infrastructure.log_manager import LogManager
from ..services.monitor_engine import WatchdogEngine

# Componentes UI Refatorados
from .components.splash_screen import SplashScreen
from .components.tray_handler import TrayHandler
from .tabs.monitor_tab import MonitorTab
from .tabs.config_tab import ConfigTab
from .tabs.log_tab import LogTab
from .tabs.account_tab import AccountTab
from .colors import AppColors

class WatchdogApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WatchdogApp")
        self.geometry("950x650")
        
        # 1. Configuração Inicial
        self._configurar_icone_janela()
        self.iniciado_pelo_sistema = "--startup" in sys.argv
        
        # 2. Inicialização de Serviços
        self.config_data = PersistenceRepository.carregar()
        self.log_manager = LogManager()
        self.icon_manager = IconeManager()
        self.engine = WatchdogEngine(self.config_data, self.registrar_log)
        self.tray_handler = TrayHandler(self)

        threading.Thread(target=self.log_manager.limpar_antigos, args=(self.config_data.dias_log,), daemon=True).start()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._load_icons()

        # --- 1. Drawer (Barra Lateral) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=AppColors.BRIGHT_SNOW)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        
        # Grid do Drawer para empurrar o botão "Conta" para o final
        self.sidebar_frame.grid_rowconfigure(4, weight=1) 

        # Logo / Título no Drawer
        # Fonte: Lexend Deca, Size 20, Weight: Bold (Simulando Medium), Padx=6
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="WatchdogApp", 
            font=ctk.CTkFont(family="Lexend Deca", size=20, weight="bold"),
            text_color=AppColors.DUSK_BLUE,
            image=self.icons.get("logo"),
            compound="left",
            padx=6 
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Lista para armazenar referências dos botões
        self.menu_buttons = []

        # Botões de Navegação
        # Passamos a chave do ícone (ex: "monitor") para ele buscar as versões _dark e _light depois
        self.btn_monitor = self._create_sidebar_button("Monitor", "radar", 1, self._show_monitor)
        self.btn_logs = self._create_sidebar_button("Logs", "log", 2, self._show_logs)
        self.btn_config = self._create_sidebar_button("Configurações", "settings", 3, self._show_config)

        # Botão Conta (Isolado na parte inferior)
        self.btn_account = self._create_sidebar_button("Conta", "person", 5, self._show_account)
        self.btn_account.grid(pady=(0, 20))

        # --- 2. Área de Conteúdo ---
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=AppColors.BRIGHT_SNOW)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # --- INICIALIZANDO AS VIEWS ---
        self.view_monitor = MonitorTab(
            self.content_frame, 
            self.engine, 
            self.config_data, 
            self.icon_manager, 
            self.registrar_log, 
            self
        )
        
        self.view_config = ConfigTab(
            self.content_frame, 
            self.engine,
            self.config_data,    
            PersistenceRepository, 
            self.registrar_log, 
            self.log_manager
        )
        
        self.view_logs = LogTab(self.content_frame, self.log_manager)
        self.view_account = AccountTab(self.content_frame)

        # Iniciar na tela de Monitor
        self._select_menu_button("Monitor")
        self._show_monitor()

        historico = self.log_manager.ler_todo_historico()
        if historico: 
            self.view_logs.adicionar_linha(historico)

        # 4. Iniciar Splash (Esconde janela)
        self.withdraw()
        if self.iniciado_pelo_sistema:
            self._pos_splash_callback() 
        else:
            self.splash = SplashScreen(self, self.config_data, self._pos_splash_callback)
            self.splash.exibir()

    def _configurar_icone_janela(self):
        try:
            caminho = SystemUtils.resource_path(os.path.join("assets/icons", "app_icon.ico"))
            if os.path.exists(caminho): self.iconbitmap(caminho)
        except: pass

    def _pos_splash_callback(self):
        """ Chamado quando a splash termina """
        minimizar = self.config_data.minimizar_para_tray
        
        if minimizar and self.iniciado_pelo_sistema:
            self.tray_handler.criar_icone()
            self.registrar_log("ℹ️ Iniciado na bandeja (Boot do Sistema).")
        elif minimizar and not self.iniciado_pelo_sistema:
            self.deiconify() 
        else:
            self.deiconify()
            
        # Automação de Retomada
        if self.config_data.persistir_monitoramento and self.config_data.monitoramento_ativo_no_fechamento:
            delay = self.config_data.delay_inicializacao
            self.registrar_log(f"⏳ Aguardando {delay}s para automação...")
            self.after(delay * 1000, self._executar_automacao)

    def _executar_automacao(self):
        self.view_monitor._automacao_inicio_monitoramento() 

    def registrar_log(self, msg, com_hora=True):
        if com_hora:
            hora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
            msg = f"[{hora}] {msg}"
            
        self.log_manager.escrever(msg)
        
        if hasattr(self, 'view_logs'):
            self.after(0, lambda: self.view_logs.adicionar_linha(msg))

    def restaurar_janela(self):
        """ Chamado pelo TrayHandler """
        self.after(0, self._mostrar_janela_safe)

    def _mostrar_janela_safe(self):
        self.deiconify()
        self.state("normal")
        self.lift()
        self.focus_force()

    def encerrar_aplicacao(self):
        """ Chamado pelo TrayHandler """
        self.engine.parar()
        self.quit()

    def _ao_minimizar(self, event):
        """ Evento de minimizar a janela """
        if str(event.widget) == "." and self.state() == "iconic":
            if self.config_data.minimizar_para_tray:
                self.withdraw()
                self.tray_handler.criar_icone()
            
    def mainloop(self, *args, **kwargs):
        self.bind("<Unmap>", self._ao_minimizar)
        super().mainloop(*args, **kwargs)
    
    def _load_icons(self):
        self.icons = {}
        icon_path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
        
        # Lista de chaves base
        keys = ["radar", "log", "settings", "person"]

        for key in keys:
            # Tenta carregar Dark
            path_dark = os.path.join(icon_path, f"{key}_dark.png")
            path_default = os.path.join(icon_path, f"{key}.png") # Fallback
            
            img_dark = None
            if os.path.exists(path_dark):
                img_dark = Image.open(path_dark)
            elif os.path.exists(path_default):
                img_dark = Image.open(path_default)
            
            if img_dark:
                self.icons[f"{key}_dark"] = ctk.CTkImage(img_dark, img_dark, size=(20, 20))
            else:
                self.icons[f"{key}_dark"] = None

            # Tenta carregar Light
            path_light = os.path.join(icon_path, f"{key}_light.png")
            img_light = None
            if os.path.exists(path_light):
                 img_light = Image.open(path_light)
            
            # Se tiver o light, usa. Se não, usa o dark como fallback
            if img_light:
                self.icons[f"{key}_light"] = ctk.CTkImage(img_light, img_light, size=(20, 20))
            else:
                self.icons[f"{key}_light"] = self.icons[f"{key}_dark"]

        path_logo = os.path.join(icon_path, "app_icon_off_background.png")
        if os.path.exists(path_logo):
            img = Image.open(path_logo)
            self.icons["logo"] = ctk.CTkImage(img, img, size=(28, 28))
        else:
            self.icons["logo"] = None

    def _create_sidebar_button(self, text, icon_key, row, command):
        initial_icon = self.icons.get(f"{icon_key}_dark")
        
        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=text,
            image=initial_icon,
            compound="left",
            font=ctk.CTkFont(family="Arial", size=12, weight="normal"),
            corner_radius=6,
            height=32,
            anchor="w",
            fg_color=AppColors.TRANSPARENT,
            text_color=AppColors.CHARCOAL_BLUE,
            hover_color=AppColors.PLATINUM,
            command=lambda: [self._select_menu_button(text), command()]
        )
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        
        # Guardando a chave do ícone no próprio botão para usar depois na seleção
        btn.icon_key = icon_key 
        self.menu_buttons.append(btn)
        return btn

    def _select_menu_button(self, selected_text):
        for btn in self.menu_buttons:
            icon_key = getattr(btn, "icon_key", None)
            
            if btn.cget("text") == selected_text:
                # --- ESTADO: SELECIONADO ---
                btn.configure(
                    fg_color=AppColors.DUSK_BLUE, 
                    text_color=AppColors.WHITE,
                    hover_color=AppColors.DUSK_BLUE, 
                    image=self.icons.get(f"{icon_key}_light")
                )
            else:
                # --- ESTADO: PADRÃO ---
                btn.configure(
                    fg_color=AppColors.TRANSPARENT, 
                    text_color=AppColors.CHARCOAL_BLUE,
                    hover_color=AppColors.PLATINUM,
                    image=self.icons.get(f"{icon_key}_dark")
                )

    def _show_frame(self, frame):
        """Remove o frame atual e mostra o novo."""
        self.view_monitor.grid_forget()
        self.view_logs.grid_forget()
        self.view_config.grid_forget()
        self.view_account.grid_forget()

        frame.grid(row=0, column=0, sticky="nsew")

    def _show_monitor(self):
        self._show_frame(self.view_monitor)

    def _show_logs(self):
        self._show_frame(self.view_logs)
        if hasattr(self.view_logs, 'start_log_stream'):
            self.view_logs.start_log_stream() 

    def _show_config(self):
        self._show_frame(self.view_config)
    
    def _show_account(self):
        self._show_frame(self.view_account)

    def run(self):
        self.mainloop()