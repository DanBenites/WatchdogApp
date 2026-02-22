import sys
import os
import threading
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime

# Componentes
from .components.license_overlay import LicenseOverlay
from .components.splash_screen import SplashScreen
from .components.sidebar import Sidebar  # <--- Novo componente

# Tabs
from .tabs.monitor_tab import MonitorTab
from .tabs.config_tab import ConfigTab
from .tabs.log_tab import LogTab
from .tabs.account_tab import AccountTab
from .colors import AppColors

from ..infrastructure.system_utils import SystemUtils

class WatchdogApp(ctk.CTk):
    def __init__(self, config_data, log_manager, icon_manager, auth_service):
        super().__init__()
        self.title("WatchdogApp")
        self.geometry("950x650")
        
        # Injeção de Dependências
        self.config_data = config_data
        self.log_manager = log_manager
        self.icon_manager = icon_manager
        self.auth_service = auth_service
        
        self.engine = None
        self.tray_handler = None
        self.overlay_frame = None 
        
        self._configurar_icone_janela()
        self.iniciado_pelo_sistema = "--startup" in sys.argv

        threading.Thread(target=self.log_manager.limpar_antigos, args=(self.config_data.dias_log,), daemon=True).start()

        # Layout Principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. Sidebar (Barra Lateral Refatorada)
        self.sidebar = Sidebar(self, on_navigate_callback=self._navegar)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        # 2. Área de Conteúdo
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=AppColors.BRIGHT_SNOW)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

    def set_engine(self, engine):
        self.engine = engine
        self.engine.callback_licenca_expirada = self._ao_licenca_expirar
        self._inicializar_views()

    def set_tray_handler(self, tray_handler):
        self.tray_handler = tray_handler

    def _inicializar_views(self):
        self.view_monitor = MonitorTab(self.content_frame, self.engine, self.config_data, self.icon_manager, self.registrar_log, self)
        self.view_config = ConfigTab(self.content_frame, self.engine, self.config_data, None, self.registrar_log, self.log_manager)
        self.view_logs = LogTab(self.content_frame, self.log_manager)
        self.view_account = AccountTab(self.content_frame, self.config_data, self.auth_service, self.icon_manager, self)

        # Estado Inicial
        self.sidebar.definir_selecao("Monitor")
        self._navegar("Monitor")

        historico = self.log_manager.ler_todo_historico()
        if historico: 
            self.view_logs.adicionar_linha(historico)

    def _navegar(self, nome_tela):
        """ Roteador central de navegação """
        # Esconde todas
        self.view_monitor.grid_forget()
        self.view_logs.grid_forget()
        self.view_config.grid_forget()
        self.view_account.grid_forget()

        # Mostra a escolhida
        if nome_tela == "Monitor":
            self.view_monitor.grid(row=0, column=0, sticky="nsew")
        elif nome_tela == "Logs":
            self.view_logs.grid(row=0, column=0, sticky="nsew")
            if hasattr(self.view_logs, 'start_log_stream'): 
                self.view_logs.start_log_stream()
        elif nome_tela == "Configurações":
            self.view_config.grid(row=0, column=0, sticky="nsew")
        elif nome_tela == "Conta":
            self.view_account.grid(row=0, column=0, sticky="nsew")

    def run(self):
        self.withdraw()
        if self.iniciado_pelo_sistema:
            self._pos_splash_callback() 
        else:
            self.splash = SplashScreen(self, self.config_data, self._pos_splash_callback)
            self.splash.exibir()
        self.mainloop()

    # --- LÓGICA DE LICENÇA E UI ---
    def exibir_overlay_licenca(self):
        if self.overlay_frame and self.overlay_frame.winfo_exists(): return
        if self.state() != "normal": self._mostrar_janela_safe()
            
        self.overlay_frame = LicenseOverlay(
            self, 
            self.auth_service, 
            self.config_data,
            self.icon_manager, # <--- Passando o gerenciador de ícones
            on_success_callback=self._ao_licenca_ativada_sucesso,
            on_close_callback=lambda: None
        )
        # Reduzi o tamanho relativo de 0.6 para 0.5 (ou você pode trocar para width=450, height=350 fixos)
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.5, relheight=0.55)

    def _ao_licenca_ativada_sucesso(self, msg):
        self.view_monitor.desbloquear_por_licenca()
        if hasattr(self, 'view_account'):
            self.view_account._carregar_dados()
        if self.tray_handler: self.tray_handler.atualizar_icone()
        self.registrar_log("✅ Nova chave de acesso validada com sucesso.")
        messagebox.showinfo("Sucesso", msg)

    def _ao_licenca_expirar(self):
        if self.config_data.minimizar_para_tray and self.tray_handler:
            self.tray_handler.atualizar_icone()
        self.after(0, self._processar_bloqueio_ui)

    def _processar_bloqueio_ui(self):
        if hasattr(self, 'view_monitor'): self.view_monitor.bloquear_por_licenca()
        if self.state() == "normal": self.exibir_overlay_licenca()

    # --- HELPERS ---
    def _configurar_icone_janela(self):
        try:
            caminho = SystemUtils.resource_path(os.path.join("assets/icons", "app_icon.ico"))
            if os.path.exists(caminho): self.iconbitmap(caminho)
        except: pass

    def _pos_splash_callback(self):
        if not self.auth_service.verificar_status_atual():
            self._processar_bloqueio_ui()
            if self.iniciado_pelo_sistema and self.config_data.minimizar_para_tray and self.tray_handler:
                self.tray_handler.criar_icone()
                SystemUtils.enviar_notificacao_windows("WatchdogApp", "Licença expirada.")
            else:
                self.deiconify()
                self.exibir_overlay_licenca()
            return

        if self.config_data.minimizar_para_tray and self.iniciado_pelo_sistema:
            if self.tray_handler: self.tray_handler.criar_icone()
        else:
            self.deiconify()
            
        if self.config_data.persistir_monitoramento and self.config_data.monitoramento_ativo_no_fechamento:
            self.after(self.config_data.delay_inicializacao * 1000, self._executar_automacao)

    def _executar_automacao(self):
        self.view_monitor._automacao_inicio_monitoramento() 

    def registrar_log(self, msg, com_hora=True):
        if com_hora: msg = f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {msg}"
        self.log_manager.escrever(msg)
        if hasattr(self, 'view_logs'): self.after(0, lambda: self.view_logs.adicionar_linha(msg))

    def restaurar_janela(self): self.after(0, self._mostrar_janela_safe)
    def _mostrar_janela_safe(self):
        self.deiconify(); self.state("normal"); self.lift(); self.focus_force()

    def encerrar_aplicacao(self):
        if self.engine: self.engine.parar()
        self.quit()

    def _ao_minimizar(self, event):
        if str(event.widget) == "." and self.state() == "iconic":
            if self.config_data.minimizar_para_tray and self.tray_handler:
                self.withdraw(); self.tray_handler.criar_icone()
            
    def mainloop(self, *args, **kwargs):
        self.bind("<Unmap>", self._ao_minimizar)
        super().mainloop(*args, **kwargs)