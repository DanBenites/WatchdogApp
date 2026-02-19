import sys
import os
import threading
from tkinter import messagebox
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
from ..services.auth_service import AuthService

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
        self.tray_handler = TrayHandler(self)
        self.auth_service = AuthService(self.config_data)
        
        # Injeção do Serviço no Monitor E Callback
        self.engine = WatchdogEngine(self.config_data, self.registrar_log, self.auth_service)
        self.engine.callback_licenca_expirada = self._ao_licenca_expirar
        
        self.tray_handler = TrayHandler(self)
        self.overlay_frame = None # Frame do overlay da licença

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
    
    def _ao_licenca_expirar(self):
        """ Chamado pela Thread da Engine no meio do monitoramento se vencer """
        if self.config_data.minimizar_para_tray:
            self.tray_handler.atualizar_icone()
            
        # O TKinter exige que alteração de UI venha da thread principal, por isso o 'after'
        self.after(0, self._processar_bloqueio_ui)

    def _processar_bloqueio_ui(self):
        """ Trava a View de Monitoramento """
        if hasattr(self, 'view_monitor'):
            self.view_monitor.bloquear_por_licenca()
            
        # Se o usuário estiver com a janela aberta na cara dele, já pula o Overlay
        if self.state() == "normal":
            self.exibir_overlay_licenca()

    def exibir_overlay_licenca(self):
        """ Desenha o painel sobreposto (Overlay) no centro da tela bloqueando o acesso """
        if self.overlay_frame is not None:
            self.overlay_frame.destroy()
            
        # Traz a janela para frente caso o sistema chame o overlay da bandeja
        if self.state() != "normal":
            self._mostrar_janela_safe()
            
        self.overlay_frame = ctk.CTkFrame(self, fg_color=AppColors.BRIGHT_SNOW, border_color=AppColors.DUSK_BLUE, border_width=2, corner_radius=10)
        # Place permite sobrepor independente dos grids embaixo
        self.overlay_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.6, relheight=0.6)
        
        lbl_titulo = ctk.CTkLabel(self.overlay_frame, text="Licença Necessária", font=("Arial", 22, "bold"), text_color=AppColors.DUSK_BLUE)
        lbl_titulo.pack(pady=(30, 10))
        
        lbl_desc = ctk.CTkLabel(self.overlay_frame, text="Sua chave de acesso expirou ou não foi configurada.\nPara continuar monitorando, insira uma nova licença vinculada a esta máquina.", font=("Arial", 12))
        lbl_desc.pack(pady=5)
        
        # Campo para o usuário copiar o HWID dele
        frame_hwid = ctk.CTkFrame(self.overlay_frame, fg_color="transparent")
        frame_hwid.pack(pady=10)
        
        ctk.CTkLabel(frame_hwid, text="Seu HWID:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        entry_hwid = ctk.CTkEntry(frame_hwid, width=250, fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT)
        entry_hwid.pack(side="left")
        entry_hwid.insert(0, self.auth_service.obter_hwid_maquina())
        entry_hwid.configure(state="readonly")
        
        # Campo da Chave
        self.entry_chave = ctk.CTkEntry(self.overlay_frame, placeholder_text="Insira sua Chave (WDA-...) aqui...", width=350, height=35)
        self.entry_chave.pack(pady=(20, 5))
        
        self.lbl_erro_chave = ctk.CTkLabel(self.overlay_frame, text="", text_color="red", font=("Arial", 12))
        self.lbl_erro_chave.pack(pady=5)
        
        btn_frame = ctk.CTkFrame(self.overlay_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Validar Chave", command=self._validar_licenca_ui, fg_color=AppColors.GREEN, height=35).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Ignorar e Fechar Aviso", command=self.overlay_frame.destroy, fg_color=AppColors.FLAG_RED, height=35).pack(side="left", padx=10)

    def _validar_licenca_ui(self):
        chave = self.entry_chave.get().strip()
        if not chave:
            self.lbl_erro_chave.configure(text="A chave não pode estar vazia.")
            return
            
        sucesso, msg = self.auth_service.validar_chave_inserida(chave)
        if sucesso:
            PersistenceRepository.salvar(self.config_data)
            self.overlay_frame.destroy()
            self.overlay_frame = None
            
            # Limpa tudo, atualiza o ícone removendo a bolinha e desbloqueia tela
            self.view_monitor.desbloquear_por_licenca()
            self.tray_handler.atualizar_icone()
            self.registrar_log("✅ Nova chave de acesso validada com sucesso.")
            messagebox.showinfo("Sucesso", msg)
        else:
            self.lbl_erro_chave.configure(text=msg)

    def _pos_splash_callback(self):
        """ Chamado quando a splash termina """
        # === BLOQUEIO INICIAL: VERIFICA A LICENÇA NO BOOT ===
        if not self.auth_service.verificar_status_atual():
            self._processar_bloqueio_ui()
            
            # Se for iniciado com o Windows, fica quieto na bandeja. Se não, mostra o overlay
            if self.iniciado_pelo_sistema and self.config_data.minimizar_para_tray:
                self.tray_handler.criar_icone()
                SystemUtils.enviar_notificacao_windows("WatchdogApp", "Iniciado com licença pendente/expirada.")
            else:
                self.deiconify()
                self.exibir_overlay_licenca()
            return # Aborta o resto do callback para NÃO iniciar o monitoramento
        # ====================================================
        
        minimizar = self.config_data.minimizar_para_tray
        
        if minimizar and self.iniciado_pelo_sistema:
            self.tray_handler.criar_icone()
            self.registrar_log("ℹ️ Iniciado na bandeja (Boot do Sistema).")
        elif minimizar and not self.iniciado_pelo_sistema:
            self.deiconify() 
        else:
            self.deiconify()
            
        if self.config_data.persistir_monitoramento and self.config_data.monitoramento_ativo_no_fechamento:
            delay = self.config_data.delay_inicializacao
            self.registrar_log(f"⏳ Aguardando {delay}s para automação...")
            self.after(delay * 1000, self._executar_automacao)