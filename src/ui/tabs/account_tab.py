import threading

import customtkinter as ctk
from tkinter import messagebox
from ..colors import AppColors
from ...infrastructure.persistence import PersistenceRepository

class AccountTab(ctk.CTkFrame):
    def __init__(self, parent, config_data, auth_service, icon_manager, app_reference):
        super().__init__(parent, fg_color=AppColors.BRIGHT_SNOW)
        self.config = config_data
        self.auth_service = auth_service
        self.icon_manager = icon_manager
        self.app = app_reference
        
        self._setup_ui()
        self._carregar_dados()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.lbl_titulo = ctk.CTkLabel(self,
            text="Credenciais",
            font=("Arial", 16, "bold"),
            text_color=AppColors.CHARCOAL_BLUE,
            anchor="w")
        self.lbl_titulo.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.container = ctk.CTkFrame(self,
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=8)
        self.container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        
        self.container.grid_columnconfigure((0,1), weight=1, uniform="equal_cols")
        self.container.grid_rowconfigure(0, weight=1)

        # --- LADO ESQUERDO: Inputs ---
        self.frame_inputs = ctk.CTkFrame(self.container, fg_color=AppColors.TRANSPARENT, bg_color=AppColors.TRANSPARENT)
        self.frame_inputs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.frame_inputs, text="HWID",
            font=("Arial", 12, "bold"),
            text_color=AppColors.NIGHT).pack(anchor="w", pady=(0, 2))
        
        wrapper_hwid = ctk.CTkFrame(self.frame_inputs,
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=6,
            height=32)
        wrapper_hwid.pack(fill="x", pady=(0, 15))
        
        self.entry_HWID = ctk.CTkEntry(wrapper_hwid,
            font=("Arial", 12),
            fg_color="transparent",
            text_color=AppColors.NIGHT,
            border_width=0,
            corner_radius=0)
        self.entry_HWID.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.entry_HWID.insert(0, self.auth_service.obter_hwid_maquina())
        self.entry_HWID.configure(state="readonly")
        
        ctk.CTkButton(wrapper_hwid,
            text="",
            image=self.icon_manager._icons.get("copy_dark"),
            width=32, height=32,
            fg_color="transparent",
            hover_color=AppColors.PLATINUM,
            border_width=0,
            corner_radius=4,
            command=self._copiar_hwid).pack(side="right", padx=(2,2), pady=2)

        ctk.CTkLabel(self.frame_inputs,
            text="Chave de Licença",
            font=("Arial", 12, "bold"),
            text_color=AppColors.NIGHT
        ).pack(anchor="w", pady=(0, 2))
        
        self.wrapper_chave = ctk.CTkFrame(self.frame_inputs,
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=6,
            height=32)
        self.wrapper_chave.pack(fill="x", pady=(0, 5))
        
        self.entry_access_key = ctk.CTkEntry(self.wrapper_chave,
            font=("Arial", 12),
            placeholder_text="Informe sua chave de licença...",
            fg_color=AppColors.WHITE,
            text_color=AppColors.NIGHT,
            border_width=0,
            corner_radius=0,
        )
        self.entry_access_key.pack(side="left", fill="both", expand=True, padx=5, pady=2)
        # self.entry_access_key.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        icone_colar = self.icon_manager._icons.get("paste")
        self.btn_colar = ctk.CTkButton(self.wrapper_chave,
            text="📋" if not icone_colar else "",
            image=icone_colar,
            width=32,
            height=32,
            fg_color="transparent",
            hover_color=AppColors.PLATINUM,
            text_color=AppColors.NIGHT,
            command=self._colar_chave)
        self.btn_colar.pack(side="right", padx=(2,2), pady=2)

        self.lbl_mensagem = ctk.CTkLabel(self.frame_inputs, text="Informe sua chave de acesso para liberar o app.", font=("Arial", 10, "normal"), text_color=AppColors.NIGHT)
        self.lbl_mensagem.pack(anchor="w", pady=(0,10))

        # Botão de Ação (Confirmar / Renovar)
        self.btn_login = ctk.CTkButton(self.frame_inputs,
            text="Confirmar",
            height=32,
            fg_color=AppColors.DUSK_BLUE,
            font=("Arial", 12),
            text_color=AppColors.WHITE,
            command=self._acao_botao_principal)
        self.btn_login.pack(fill="x", pady=(0, 10))

        # --- LADO DIREITO: Texto (Avisos mantidos) ---
        self.frame_info = ctk.CTkFrame(self.container,fg_color=AppColors.TRANSPARENT)
        self.frame_info.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(self.frame_info, text="Segurança de sua Chave Key", font=("Arial", 12, "bold"), text_color=AppColors.NIGHT).pack(anchor="w")

        texto_aviso = ("Sua Chave API é confidencial e deve ser tratada como uma senha:\n\n"
                       "  • Não compartilhe sua chave com ninguém;\n"
                       "  • Não publique em redes sociais, fóruns ou qualquer site;\n"
                       "  • Não envie por e-mail ou mensagens sem necessidade.\n\n"
                       "Essa chave permite acesso à sua aplicação. Se alguém tiver acesso a ela, poderá realizar ações em seu nome.")

        self.lbl_aviso = ctk.CTkLabel(self.frame_info, text=texto_aviso, font=("Arial", 12), text_color=AppColors.NIGHT, justify="left", anchor="w")
        self.lbl_aviso.pack(fill="x")
        self.lbl_aviso.bind("<Configure>", lambda e: self.lbl_aviso.configure(wraplength=e.width))

        ctk.CTkLabel(self.frame_info, text="Se sua chave for exposta", font=("Arial", 12, "bold"), text_color=AppColors.NIGHT).pack(anchor="w", pady=(10,0))
        ctk.CTkLabel(self.frame_info, text="Caso suspeite que sua chave foi comprometida, gere uma nova imediatamente e desative a chave antiga.", font=("Arial", 12), text_color=AppColors.NIGHT, justify="left", wraplength=320).pack(anchor="w")

        # --- RODAPÉ DO CONTAINER ---
        self.footer = ctk.CTkFrame(self.container, fg_color=AppColors.BRIGHT_SNOW, corner_radius=6, height=40)
        self.footer.grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=2)

        self.footer.grid_columnconfigure(2, weight=1) 

        ctk.CTkLabel(
            self.footer, 
            text="Status do Servidor:", 
            font=("Arial", 11, "bold"), 
            text_color="gray"
        ).grid(row=0, column=0, padx=(10, 2), pady=8, sticky="w")

        self.lbl_status_servidor = ctk.CTkLabel(
            self.footer, 
            text="Procurando...", 
            font=("Arial", 11, "bold"), 
            text_color=AppColors.GREEN
        )
        self.lbl_status_servidor.grid(row=0, column=1, padx=(0, 10), pady=8, sticky="w")

        ctk.CTkFrame(self.footer, fg_color=AppColors.TRANSPARENT, height=1).grid(row=0, column=2, sticky="ew")

        ctk.CTkLabel(
            self.footer, 
            text="Versão: 1.0.0", 
            font=("Arial", 11), 
            text_color="gray"
        ).grid(row=0, column=3, padx=10, pady=8, sticky="e")

        # --- DATAS DE VALIDADE ---
        self.data_account = ctk.CTkFrame(self, fg_color="white", border_color=AppColors.PLATINUM, border_width=2, corner_radius=8)
        self.data_account.grid(row=2, column=0, sticky="new", padx=10, pady=(0, 10))

        self.frame_data_account = ctk.CTkFrame(self.data_account, fg_color=AppColors.TRANSPARENT)
        self.frame_data_account.pack(fill="both", expand=True, padx=15, pady=10)
        
        self.frame_data_account.grid_columnconfigure((2,5), weight=1)

        ctk.CTkLabel(self.frame_data_account, text="Ativada em: ", font=("Arial", 12, "bold"), text_color=AppColors.NIGHT).grid(row=0, column=0, sticky="w")
        self.lbl_ativada = ctk.CTkLabel(self.frame_data_account, text="Não encontrado", font=("Arial", 12, "normal"), text_color=AppColors.NIGHT)
        self.lbl_ativada.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(self.frame_data_account, text="Expira em: ", font=("Arial", 12, "bold"), text_color=AppColors.NIGHT).grid(row=0, column=3, sticky="w")
        self.lbl_expira = ctk.CTkLabel(self.frame_data_account, text="Não encontrado", font=("Arial", 12, "normal"), text_color=AppColors.NIGHT)
        self.lbl_expira.grid(row=0, column=4, sticky="w")

    # --- LÓGICA DE NEGÓCIO DA ABA ---cls

    def _carregar_dados(self):
        """ Preenche os campos baseado no status da licença atual """
        self.lbl_status_servidor.configure(text="Verificando...", text_color=AppColors.YELLOW)
        threading.Thread(target=self._verificar_servidor_async, daemon=True).start()
        
        possui_chave = bool(self.config.licenca.chave)
        licenca_valida = self.config.licenca.ativa and self.auth_service.verificar_status_atual()

        if possui_chave:
            # Máscara de Chave (Mostra os últimos 6)
            chave_real = self.config.licenca.chave
            if len(chave_real) > 6:
                mascara = ("*" * (len(chave_real) - 6)) + chave_real[-6:]
            else:
                mascara = "******"
            
            self._definir_estado_chave(mascara, readonly=True)
            self.btn_login.configure(text="Renovar Chave")
            
            if self.auth_service.is_licenca_ativa() :
                self.lbl_mensagem.configure(text="Sua licença está ativa.", text_color="#2e7d32")
            else:
                self.lbl_mensagem.configure(text="Sua licença expirou! Efetue a renovação.", text_color=AppColors.FLAG_RED)
            
            # Preenche datas
            dt_ativacao = self.config.licenca.data_ativacao
            dt_exp = self.config.licenca.data_expiracao
            
            self.lbl_ativada.configure(text=dt_ativacao.strftime("%d/%m/%Y") if dt_ativacao else "Desconhecida")
            self.lbl_expira.configure(text=dt_exp.strftime("%d/%m/%Y") if dt_exp else "Expirada")
            
        else:
            self._definir_estado_chave("", readonly=False)
            self.btn_login.configure(text="Confirmar")
            self.lbl_mensagem.configure(text="Informe sua chave de acesso para liberar o app.", text_color=AppColors.NIGHT)
            self.lbl_ativada.configure(text="Não Encontrado")
            self.lbl_expira.configure(text="Não Encontrado")

    def _definir_estado_chave(self, texto, readonly=False):
        """ Controla se a caixa da chave pode ser editada e esconde/mostra botão colar """
        self.entry_access_key.configure(state="normal")
        self.entry_access_key.delete(0, "end")
        self.entry_access_key.insert(0, texto)
        
        # Força o cursor para o final para exibir os últimos dígitos
        self.entry_access_key.xview_moveto(1.0)
        self.entry_access_key.icursor("end")
        
        if readonly:
            # Alteramos apenas o state e o text_color (o fg_color já é transparente desde a criação)
            self.entry_access_key.configure(
                state="readonly",
                text_color="gray",
            )
        else:
            self.entry_access_key.configure(
                state="normal",
                text_color=AppColors.NIGHT
            )
            self.btn_colar.pack(side="right", padx=(2,2), pady=2)

    def _acao_botao_principal(self):
        """ Define se o botão atua para Salvar ou para Renovar """
        if self.btn_login.cget("text") == "Renovar Chave":
            # Desbloqueia e mostra a chave real para ele ver e decidir se troca ou mantém
            chave_real = self.config.licenca.chave
            self._definir_estado_chave(chave_real, readonly=False)
            self.btn_login.configure(text="Confirmar")
            self.lbl_mensagem.configure(text="Se você pagou a renovação da mesma chave, apenas clique em Confirmar.\n Senão, cole a nova.", text_color=AppColors.NIGHT)
        else:
            # Tenta validar a chave digitada
            chave = self.entry_access_key.get().strip()
            if not chave:
                from tkinter import messagebox
                messagebox.showerror("Erro", "A chave não pode estar vazia.")
                return
                
            sucesso, msg = self.auth_service.validar_chave_inserida(chave)
            if sucesso:
                self.config.licenca.chave = chave # Garante que a chave nova (ou renovada) fique na memória
                PersistenceRepository.salvar(self.config)
                from tkinter import messagebox
                messagebox.showinfo("Sucesso", msg)
                
                # Atualiza a UI da aba
                self._carregar_dados()
                
                # Desbloqueia a aplicação toda se estava travada
                if hasattr(self.app, 'view_monitor'):
                    self.app.view_monitor.desbloquear_por_licenca()
                if hasattr(self.app, 'tray_handler') and self.app.tray_handler:
                    self.app.tray_handler.atualizar_icone()
            else:
                from tkinter import messagebox
                messagebox.showerror("Erro de Validação", msg)

    def _copiar_hwid(self):
        self.clipboard_clear()
        self.clipboard_append(self.auth_service.obter_hwid_maquina())
        self.update()
        
    def _colar_chave(self):
        try:
            texto_colado = self.clipboard_get()
            self.entry_access_key.delete(0, "end")
            self.entry_access_key.insert(0, texto_colado)
        except Exception:
            pass
    
    def _verificar_servidor_async(self):
        """ Executa em segundo plano para não travar a UI """
        is_online = self.auth_service.testar_conexao_servidor()
        
        # O CustomTkinter exige que as atualizações visuais voltem para a Thread principal
        if is_online:
            self.after(0, lambda: self.lbl_status_servidor.configure(
                text="Online", 
                text_color=AppColors.GREEN
            ))
        else:
            self.after(0, lambda: self.lbl_status_servidor.configure(
                text="Offline", 
                text_color=AppColors.FLAG_RED
            ))