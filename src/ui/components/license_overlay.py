import customtkinter as ctk
from ...infrastructure.persistence import PersistenceRepository
from ..colors import AppColors

class LicenseOverlay(ctk.CTkFrame):
    def __init__(self, parent, auth_service, config_data, icon_manager, on_success_callback, on_close_callback):
        super().__init__(
            parent,
            bg_color=AppColors.TRANSPARENT,
            fg_color=AppColors.DUSK_BLUE,
            corner_radius=10
        )
        self.auth_service = auth_service
        self.config_data = config_data
        self.icon_manager = icon_manager
        self.on_success_callback = on_success_callback
        self.on_close_callback = on_close_callback
        
        self._setup_ui()

    def _setup_ui(self):
        lbl_titulo = ctk.CTkLabel(self, text="Licença Necessária", font=("Arial", 20, "bold"), text_color=AppColors.WHITE)
        lbl_titulo.pack(pady=(20, 5))
        
        lbl_desc = ctk.CTkLabel(self, 
            text="Sua chave de acesso expirou ou não foi configurada.\nPara continuar monitorando, insira uma nova licença vinculada a esta máquina.",
            font=("Arial", 12),
            text_color=AppColors.WHITE,
            )
        lbl_desc.pack(pady=5)
        
        # --- HWID SECTION ---

        frame_hwid = ctk.CTkFrame(self, fg_color="transparent")
        frame_hwid.pack(pady=(10, 0), padx=20)
        
        # Label alinhada à esquerda
        ctk.CTkLabel(
            frame_hwid, 
            text="Seu HWID", 
            font=("Arial", 12, "bold"), 
            text_color=AppColors.WHITE
        ).pack(anchor="w", pady=(0, 2))
        
        input_wrapper = ctk.CTkFrame(
            frame_hwid, 
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2, 
            corner_radius=6,
            width=332,
            height=32
        )
        input_wrapper.pack(anchor="w")
        
        # Caixa de Texto (Fundo transparente e sem borda)
        self.entry_hwid = ctk.CTkEntry(
            input_wrapper,
            width=300,
            height=32,
            text_color=AppColors.NIGHT,
            fg_color="transparent",
            border_width=0,        
            corner_radius=0         
        )
        self.entry_hwid.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.entry_hwid.insert(0, self.auth_service.obter_hwid_maquina())
        self.entry_hwid.configure(state="readonly")

        icone_copiar = self.icon_manager._icons.get("copy_dark")
        ctk.CTkButton(
            input_wrapper,
            text="📄​" if icone_copiar is None else "",
            image=icone_copiar,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color=AppColors.PLATINUM, 
            text_color=AppColors.NIGHT,
            border_width=0,
            corner_radius=4,
            command=self._copiar_hwid
        ).pack(side="right", padx=(2, 2), pady=2)
        
        # --- CHAVE SECTION ---
       
        frame_key = ctk.CTkFrame(self, fg_color="transparent")
        frame_key.pack(pady=(10, 0), padx=20)
        
        # Label alinhada à esquerda
        ctk.CTkLabel(
            frame_key, 
            text="Insira sua Chave de Licença:", 
            font=("Arial", 12, "bold"), 
            text_color=AppColors.WHITE
        ).pack(anchor="w", pady=(0, 2))
        
        input_wrapper = ctk.CTkFrame(
            frame_key, 
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2, 
            corner_radius=6,
            width=332,
            height=32
        )
        input_wrapper.pack(anchor="w")
        
        # Caixa de Texto (Fundo transparente e sem borda)
        self.entry_chave = ctk.CTkEntry(
            input_wrapper,
            placeholder_text="Cole sua Chave de Licença aqui...",
            width=300,
            height=32,
            text_color=AppColors.NIGHT,
            fg_color="transparent",
            border_width=0,        
            corner_radius=0         
        )
        
        self.entry_chave.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        icone_colar = self.icon_manager._icons.get("paste")
        ctk.CTkButton(
            input_wrapper,
            text="📋" if icone_colar is None else "",
            image=icone_colar,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color=AppColors.PLATINUM, 
            text_color=AppColors.NIGHT,
            border_width=0,
            corner_radius=4,
            command=self._colar_chave
        ).pack(side="right", padx=(2, 2), pady=2)
        
        # --- ERRO E BOTÕES FINAIS ---
        self.lbl_erro_chave = ctk.CTkLabel(self, text="", text_color=AppColors.FLAG_RED, font=("Arial", 12))
        self.lbl_erro_chave.pack(pady=(5, 10))
        
        btn_frame = ctk.CTkFrame(self, fg_color=AppColors.TRANSPARENT)
        btn_frame.pack(pady=(0, 20))

        ctk.CTkButton(btn_frame,
            text="Ignorar e Fechar", 
            command=self._fechar,
            text_color=AppColors.CHARCOAL_BLUE,
            fg_color=AppColors.WHITE,
            hover_color=AppColors.PLATINUM,
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=4,
            height=32
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="Validar Chave",
            command=self._validar_licenca,
            text_color=AppColors.WHITE,
            fg_color=AppColors.BRILLIANT_AZURE,
            corner_radius=4,
            height=32
        ).pack(side="left", padx=5)

    def _copiar_hwid(self):
        """ Copia o HWID para a área de transferência """
        self.clipboard_clear()
        self.clipboard_append(self.auth_service.obter_hwid_maquina())
        self.update() # Necessário no Tkinter para garantir a cópia
        self.lbl_erro_chave.configure(text="HWID copiado!", text_color=AppColors.WHITE)
        self.after(2000, lambda: self.lbl_erro_chave.configure(text="")) # Limpa a mensagem após 2s

    def _colar_chave(self):
        """ Cola o texto da área de transferência na entrada de chave """
        try:
            texto_colado = self.clipboard_get()
            self.entry_chave.delete(0, "end")
            self.entry_chave.insert(0, texto_colado)
        except Exception:
            pass # Ignora se não houver texto na área de transferência

    def _validar_licenca(self):
        chave = self.entry_chave.get().strip()
        if not chave:
            self.lbl_erro_chave.configure(text="A chave não pode estar vazia.", text_color=AppColors.YELLOW)
            return
            
        sucesso, msg = self.auth_service.validar_chave_inserida(chave)
        if sucesso:
            PersistenceRepository.salvar(self.config_data)
            self.on_success_callback(msg)
            self.destroy()
        else:
            self.lbl_erro_chave.configure(text=msg, text_color=AppColors.YELLOW)
            
    def _fechar(self):
        self.on_close_callback()
        self.destroy()