import sys
import os
import threading
import customtkinter as ctk
from datetime import datetime

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

class WatchdogApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WatchdogApp - Petrosoft")
        self.geometry("950x650")
        
        # 1. Configuração Inicial
        self._configurar_icone_janela()
        self.iniciado_pelo_sistema = "--startup" in sys.argv
        
        # 2. Inicialização de Serviços
        self.config_data = PersistenceRepository.carregar()
        self.log_manager = LogManager()
        self.icon_manager = IconeManager()
        self.engine = WatchdogEngine(self.config_data, self.registrar_log)
        self.tray_handler = TrayHandler(self) # Passa 'self' para o handler controlar a janela

        # 3. Limpeza Logs
        threading.Thread(target=self.log_manager.limpar_antigos, args=(self.config_data.dias_log,), daemon=True).start()

        
        # 5. Construir Interface (Abas)
        self._construir_abas()

        # 6. Carregar Logs Anteriores
        historico = self.log_manager.ler_conteudo_dia()
        if historico: self.tab_log.adicionar_linha(historico)

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
            self.deiconify() # Usuário abriu, mostra janela
        else:
            self.deiconify()
            
        # Automação de Retomada
        if self.config_data.persistir_monitoramento and self.config_data.monitoramento_ativo_no_fechamento:
            delay = self.config_data.delay_inicializacao
            self.registrar_log(f"⏳ Aguardando {delay}s para automação...")
            self.after(delay * 1000, self._executar_automacao)

    def _executar_automacao(self):
        # A lógica de automação pode ficar aqui ou ser movida para um 'AutomationService'
        # Para simplificar, delega para a tab de monitoramento que tem acesso aos controles
        self.tab_monitor._automacao_inicio_monitoramento() 
        # Nota: Você precisará mover o método _automacao... para dentro da MonitorTab

    def _construir_abas(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Cria as abas no Tabview
        t_monitor = self.tabview.add("Monitoramento")
        t_log = self.tabview.add("Logs")
        t_config = self.tabview.add("Configurações")
        
        # Instancia os componentes dentro das abas
        self.tab_log = LogTab(t_log, self.log_manager)
        
        self.tab_config = ConfigTab(
            t_config, 
            self.config_data, 
            PersistenceRepository, 
            self.registrar_log,
            self.log_manager
        )
        
        self.tab_monitor = MonitorTab(
            t_monitor,
            self.engine,
            self.config_data,
            self.icon_manager,
            self.registrar_log,
            self
        )
        
        # Layout Pack para preencher as abas
        self.tab_log.pack(fill="both", expand=True)
        self.tab_config.pack(fill="both", expand=True)
        self.tab_monitor.pack(fill="both", expand=True)

    # --- Métodos Públicos para os Componentes ---
    
    def registrar_log(self, msg, com_hora=True):
        if com_hora:
            hora = datetime.now().strftime('%H:%M:%S')
            msg = f"[{hora}] {msg}"
            
        self.log_manager.escrever(msg)
        # Atualiza a UI da aba de log
        if hasattr(self, 'tab_log'):
            self.after(0, lambda: self.tab_log.adicionar_linha(msg))

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
            
    # Ligar evento de minimizar
    def mainloop(self, *args, **kwargs):
        self.bind("<Unmap>", self._ao_minimizar)
        super().mainloop(*args, **kwargs)