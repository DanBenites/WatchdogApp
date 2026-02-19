import sys
import os
import threading
from tkinter import messagebox
import customtkinter as ctk

from ...infrastructure.persistence import PersistenceRepository
from ...infrastructure.system_utils import SystemUtils
from ...ui.colors import AppColors

class License_Overlay:
    def __init__(self, app_reference):
        self.app = app_reference
        self.icon = None

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
            import customtkinter as ctk
from tkinter import messagebox
from ...infrastructure.persistence import PersistenceRepository
from ..colors import AppColors

class LicenseOverlay(ctk.CTkFrame):
    def __init__(self, parent, auth_service, config_data, on_success_callback, on_close_callback):
        super().__init__(
            parent, 
            fg_color=AppColors.BRIGHT_SNOW, 
            border_color=AppColors.DUSK_BLUE, 
            border_width=2, 
            corner_radius=10
        )
        self.auth_service = auth_service
        self.config_data = config_data
        self.on_success_callback = on_success_callback
        self.on_close_callback = on_close_callback
        
        self._setup_ui()

    def _setup_ui(self):
        lbl_titulo = ctk.CTkLabel(self, text="Licença Necessária", font=("Arial", 22, "bold"), text_color=AppColors.DUSK_BLUE)
        lbl_titulo.pack(pady=(30, 10))
        
        lbl_desc = ctk.CTkLabel(self, text="Sua chave de acesso expirou ou não foi configurada.\nPara continuar monitorando, insira uma nova licença vinculada a esta máquina.", font=("Arial", 12))
        lbl_desc.pack(pady=5)
        
        # Campo para o usuário copiar o HWID dele
        frame_hwid = ctk.CTkFrame(self, fg_color="transparent")
        frame_hwid.pack(pady=10)
        
        ctk.CTkLabel(frame_hwid, text="Seu HWID:", font=("Arial", 12, "bold")).pack(side="left", padx=5)
        entry_hwid = ctk.CTkEntry(frame_hwid, width=250, fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT)
        entry_hwid.pack(side="left")
        entry_hwid.insert(0, self.auth_service.obter_hwid_maquina())
        entry_hwid.configure(state="readonly")
        
        # Campo da Chave
        self.entry_chave = ctk.CTkEntry(self, placeholder_text="Insira sua Chave (WDA-...) aqui...", width=350, height=35)
        self.entry_chave.pack(pady=(20, 5))
        
        self.lbl_erro_chave = ctk.CTkLabel(self, text="", text_color="red", font=("Arial", 12))
        self.lbl_erro_chave.pack(pady=5)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        ctk.CTkButton(btn_frame, text="Validar Chave", command=self._validar_licenca, fg_color=AppColors.GREEN, height=35).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="Ignorar e Fechar", command=self._fechar, fg_color=AppColors.FLAG_RED, height=35).pack(side="left", padx=10)

    def _validar_licenca(self):
        chave = self.entry_chave.get().strip()
        if not chave:
            self.lbl_erro_chave.configure(text="A chave não pode estar vazia.")
            return
            
        sucesso, msg = self.auth_service.validar_chave_inserida(chave)
        if sucesso:
            PersistenceRepository.salvar(self.config_data)
            self.on_success_callback(msg)
            self.destroy()
        else:
            self.lbl_erro_chave.configure(text=msg)
            
    def _fechar(self):
        self.on_close_callback()
        self.destroy()
        if self.config_data.persistir_monitoramento and self.config_data.monitoramento_ativo_no_fechamento:
            delay = self.config_data.delay_inicializacao
            self.registrar_log(f"⏳ Aguardando {delay}s para automação...")
            self.after(delay * 1000, self._executar_automacao)