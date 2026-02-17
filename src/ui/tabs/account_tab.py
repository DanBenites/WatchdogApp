import customtkinter as ctk
from ..colors import AppColors

class AccountTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=AppColors.BRIGHT_SNOW)
        self._setup_ui()

    def _setup_ui(self):
        # Configuração do Grid principal da Tab
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. Título
        self.lbl_titulo = ctk.CTkLabel(
            self, 
            text="Credenciais", 
            font=("Arial", 16, "bold"), 
            text_color=AppColors.CHARCOAL_BLUE,
            anchor="w"
        )
        self.lbl_titulo.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # 2. Container Principal (Card)
        self.container = ctk.CTkFrame(
            self, 
            fg_color=AppColors.WHITE, 
            border_color=AppColors.PLATINUM, 
            border_width=2, 
            corner_radius=8
        )
        self.container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0,10))
        
        # Configuração do Grid do Container
        self.container.grid_columnconfigure((0,1), weight=1, uniform="equal_cols")
        self.container.grid_rowconfigure(0, weight=1)

        # --- LADO ESQUERDO: Inputs ---
        self.frame_inputs = ctk.CTkFrame(self.container, fg_color=AppColors.TRANSPARENT)
        self.frame_inputs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        
        ctk.CTkLabel(self.frame_inputs, text="Chave de Acesso", font=("Arial", 12, "bold"), text_color=AppColors.NIGHT).pack(anchor="w")
        self.entry_access_key = ctk.CTkEntry(self.frame_inputs, height=35, border_color=AppColors.PLATINUM, font=("Arial", 12), placeholder_text="Informe sua chave de acesso...")
        self.entry_access_key.pack(fill="x", pady=(0, 10))

        
        ctk.CTkLabel(self.frame_inputs, text="HWID", font=("Arial", 12, "bold"), text_color=AppColors.NIGHT).pack(anchor="w")
        self.entry_HWID = ctk.CTkEntry(self.frame_inputs, height=35, border_color=AppColors.PLATINUM, show="*", font=("Arial", 12), placeholder_text="Informe sua HWID...")
        self.entry_HWID.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(self.frame_inputs, text="Informe sua chave de acesso para liberar o app.", font=("Arial", 10, "normal"), text_color=AppColors.NIGHT).pack(anchor="w", pady=(0,10))

        self.btn_login = ctk.CTkButton(self.frame_inputs, text="Confirmar", height=35, fg_color=AppColors.DUSK_BLUE, font=("Arial", 12), text_color=AppColors.WHITE)
        self.btn_login.pack(fill="x", pady=(0, 10))

        # --- LADO DIREITO: Texto ---
        self.frame_info = ctk.CTkFrame(self.container, fg_color=AppColors.TRANSPARENT)
        self.frame_info.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(
            self.frame_info, 
            text="Segurança de sua Chave Key", 
            font=("Arial", 12, "bold"), 
            text_color=AppColors.NIGHT
        ).pack(anchor="w")

# Texto formatado com estilo de lista
        texto_aviso = (
            "Sua Chave API é confidencial e deve ser tratada como uma senha:\n\n"
            "  • Não compartilhe sua chave com ninguém;\n"
            "  • Não publique em redes sociais, GitHub ou qualquer site;\n"
            "  • Não envie por e-mail ou mensagens sem necessidade.\n\n"
            "Essa chave permite acesso à sua aplicação. Se alguém tiver acesso a ela, poderá realizar ações em seu nome."
        )

        self.lbl_aviso = ctk.CTkLabel(
            self.frame_info, 
            text=texto_aviso, 
            font=("Arial", 12), 
            text_color=AppColors.NIGHT,
            justify="left",
            anchor="w"
        )
        self.lbl_aviso.pack(fill="x")
        self.lbl_aviso.bind("<Configure>", lambda e: self.lbl_aviso.configure(wraplength=e.width))

        ctk.CTkLabel(
            self.frame_info, 
            text="Se sua chave for exposta", 
            font=("Arial", 12, "bold"), 
            text_color=AppColors.NIGHT
        ).pack(anchor="w")

        ctk.CTkLabel(
            self.frame_info, 
            text="Caso suspeite que sua chave foi comprometida, gere uma nova imediatamente e desative a chave antiga.", 
            font=("Arial", 12), 
            text_color=AppColors.NIGHT,
            justify="left",
            wraplength=320
        ).pack(anchor="w")

        # Rodapé do Container (Sub-container)
        self.footer = ctk.CTkFrame(self.container, fg_color=AppColors.BRIGHT_SNOW, corner_radius=6, height=40)
        self.footer.grid(row=1, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        
        self.footer.grid_columnconfigure(0, weight=1)
        self.footer.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.footer, 
            text="Status do Servidor: Online", 
            font=("Arial", 11, "bold"), 
            text_color="#2e7d32"
        ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(
            self.footer, 
            text="Versão: 1.0.0", 
            font=("Arial", 11), 
            text_color="gray"
        ).grid(row=0, column=1, padx=10, pady=8, sticky="e")


        self.data_account = ctk.CTkFrame(
            self, 
            fg_color="white", 
            border_color=AppColors.PLATINUM, 
            border_width=2, 
            corner_radius=8
        )
        self.data_account.grid(row=2, column=0, sticky="new", padx=10, pady=(0, 10))

        self.frame_data_account = ctk.CTkFrame(self.data_account, fg_color=AppColors.TRANSPARENT)
        self.frame_data_account.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Configuração das Colunas:
        # Col 0 e 1: Esquerda | Col 2: Espaçador (Mola) | Col 3 e 4: Direita
        self.frame_data_account.grid_columnconfigure((2,5), weight=1)

        # Grupo Esquerda (Criado em)
        ctk.CTkLabel(
            self.frame_data_account, 
            text="Criado em: ", 
            font=("Arial", 12, "bold"), 
            text_color=AppColors.NIGHT
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            self.frame_data_account, 
            text="14/02/2026", 
            font=("Arial", 12, "normal"), 
            text_color=AppColors.NIGHT
        ).grid(row=0, column=1, sticky="w")

        # Grupo Direita (Expira em)
        ctk.CTkLabel(
            self.frame_data_account, 
            text="Expira em: ", 
            font=("Arial", 12, "bold"), 
            text_color=AppColors.NIGHT,
        ).grid(row=0, column=3, sticky="w")

        ctk.CTkLabel(
            self.frame_data_account, 
            text="28/02/2026", 
            font=("Arial", 12, "normal"), 
            text_color=AppColors.NIGHT,
        ).grid(row=0, column=4, sticky="w")