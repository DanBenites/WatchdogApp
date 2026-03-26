# src/ui/tabs/monitor/monitor_tab.py
import os
import subprocess
import customtkinter as ctk
from tkinter import messagebox

from ...colors import AppColors
from ....infrastructure.system_utils import SystemUtils
from ....infrastructure.persistence import PersistenceRepository
from ...components.dialogs import DialogoVerificacao
from ....services.process_use_cases import ProcessManagementUseCase
from .processos_view import ProcessosView
from .servicos_view import ServicosView

class MonitorTab(ctk.CTkFrame):
    """Casca principal de Navegação (Abas Superiores) e Controlador de Ciclo de Vida"""
    def __init__(self, parent, engine, config_data, icon_manager, log_callback, main_app_ref):
        super().__init__(parent, fg_color=AppColors.BRIGHT_SNOW, corner_radius=0)
        self.engine = engine
        self.config_data = config_data
        self.icon_manager = icon_manager
        self.log = log_callback
        self.app = main_app_ref
        
        self.process_use_case = ProcessManagementUseCase(self.config_data)

        self.grid_rowconfigure(0, weight=0) # Abas
        self.grid_rowconfigure(1, weight=1) # Tabelas
        self.grid_rowconfigure(2, weight=0) # NOVO: Rodapé Global (Botão)
        self.grid_columnconfigure(0, weight=1)

        self._build_top_tabs()
        self._build_content_area()
        self._build_footer() # NOVO: Instancia o botão único

    def _build_top_tabs(self):
        self.tabs_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.tabs_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))

        self.btn_processos = self._create_tab_button("Processos", self.show_processos)
        self.btn_servicos = self._create_tab_button("Serviços", self.show_servicos)

        self.btn_processos.pack(side="left")
        self.btn_servicos.pack(side="left")

        separator = ctk.CTkFrame(self, fg_color=AppColors.PLATINUM, height=2)
        separator.grid(row=0, column=0, sticky="sew", padx=10)

    def _create_tab_button(self, text, command):
        return ctk.CTkButton(
            self.tabs_frame, text=text, fg_color="transparent", 
            text_color=AppColors.CHARCOAL_BLUE, hover_color=AppColors.PLATINUM, 
            font=("Arial", 14, "bold"), height=34, width=120, corner_radius=0, command=command
        )

    def _build_content_area(self):
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.view_processos = ProcessosView(self.content_container, self)
        self.view_servicos = ServicosView(self.content_container, self)
        
        self.show_processos()

    def _build_footer(self):
        """O Botão Global de Iniciar Monitoramento"""
        self.btn_start = ctk.CTkButton(
            self, text="INICIAR MONITORAMENTO", image=self.icon_manager._icons.get("play"), text_color=AppColors.WHITE,
            fg_color=AppColors.DUSK_BLUE, height=34, font=("Arial", 14, "bold"),
            command=self.toggle_monitor
        )
        self.btn_start.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))

    def show_processos(self):
        self._reset_tab_buttons()
        self.btn_processos.configure(fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE)
        if hasattr(self, 'view_servicos'): self.view_servicos.grid_forget()
        self.view_processos.grid(row=0, column=0, sticky="nsew")

    def show_servicos(self):
        self._reset_tab_buttons()
        self.btn_servicos.configure(fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE)
        self.view_processos.grid_forget()
        self.view_servicos.grid(row=0, column=0, sticky="nsew")

    def _reset_tab_buttons(self):
        self.btn_processos.configure(fg_color="transparent", text_color=AppColors.CHARCOAL_BLUE)
        self.btn_servicos.configure(fg_color="transparent", text_color=AppColors.CHARCOAL_BLUE)

    def toggle_monitor(self):
        if not self.app.auth_service.verificar_status_atual():
            self.app.exibir_overlay_licenca()
            return

        if not self.engine.rodando:
            if not self.config_data.processos and not self.config_data.servicos:
                messagebox.showwarning("Vazio", "Adicione processos ou serviços primeiro.")
                return
            
            lista_alvo = [nome for nome, dados in self.config_data.processos.items() if dados.get("regra") != "Sempre Encerrar (Blacklist)"]
            ausentes = SystemUtils.verificar_processos_ausentes(lista_alvo)

            if ausentes:
                dialogo = DialogoVerificacao(self, ausentes, self.icon_manager, self.config_data)
                self.master.wait_window(dialogo)
                escolha = dialogo.resultado
                if escolha == "cancelar": return
                elif escolha == "forcar": self._forcar_inicializacao(ausentes)
                
            self.engine.iniciar()
            self.config_data.monitoramento_ativo_no_fechamento = True
            PersistenceRepository.salvar(self.config_data)
            
            # Atualiza o Botão Global e bloqueia edição nas duas Views
            self.btn_start.configure(text="PARAR MONITORAMENTO", image=self.icon_manager._icons.get("stop"), fg_color="orange")
            self.view_processos.definir_estado_edicao("disabled")
            self.view_servicos.definir_estado_edicao("disabled")
        
        else:
            self.engine.parar()
            self.config_data.monitoramento_ativo_no_fechamento = False
            PersistenceRepository.salvar(self.config_data)
            
            self.btn_start.configure(text="INICIAR MONITORAMENTO", image=self.icon_manager._icons.get("play"), fg_color=AppColors.DUSK_BLUE)
            self.view_processos.definir_estado_edicao("normal")
            self.view_servicos.definir_estado_edicao("normal")

    def _forcar_inicializacao(self, lista_nomes):
        for nome in lista_nomes:
            path = self.config_data.processos[nome].get("path")
            if path and os.path.exists(path):
                try: subprocess.Popen(path)
                except: pass

    def _automacao_inicio_monitoramento(self):
        if self.engine.rodando: return
        self._iniciar_engine_silencioso()

    def _iniciar_engine_silencioso(self):
        self.engine.iniciar()
        self.btn_start.configure(text="PARAR MONITORAMENTO", image=self.icon_manager._icons.get("stop"), fg_color="orange")
        self.view_processos.definir_estado_edicao("disabled")
        self.view_servicos.definir_estado_edicao("disabled")
    
    def bloquear_por_licenca(self):
        self.btn_start.configure(text="LICENÇA EXPIRADA - ATIVAR", text_color=AppColors.WHITE, fg_color="gray", hover_color="darkgray", command=self.app.exibir_overlay_licenca)
        self.view_processos.definir_estado_edicao("disabled")
        self.view_servicos.definir_estado_edicao("disabled")

    def desbloquear_por_licenca(self):
        self.btn_start.configure(text="INICIAR MONITORAMENTO", image=self.icon_manager._icons.get("play"), fg_color=AppColors.DUSK_BLUE, hover_color="#14375d", command=self.toggle_monitor)
        self.view_processos.definir_estado_edicao("normal")
        self.view_servicos.definir_estado_edicao("normal")