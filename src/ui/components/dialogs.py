import customtkinter as ctk

class DialogoVerificacao(ctk.CTkToplevel):
    def __init__(self, parent, ausentes, icon_manager, config_data):
        super().__init__(parent)
        self.title("Atenção")
        
        # 1. CÁLCULO DE TAMANHO E POSIÇÃO (CENTRALIZADO)
        # Calcula altura baseada na quantidade de itens (30px por item)
        altura_conteudo = len(ausentes) * 35 
        largura = 400
        altura = 160 + altura_conteudo
        
        # Obtém geometria da janela pai (WatchdogApp)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        # Matemática para achar o centro
        pos_x = parent_x + (parent_w // 2) - (largura // 2)
        pos_y = parent_y + (parent_h // 2) - (altura // 2)

        # Aplica geometria fixa e centralizada
        self.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")
        self.resizable(False, False)
        
        # Configurações de Janela Modal
        self.attributes("-topmost", True)
        self.grab_set() # Bloqueia a janela de trás
        self.configure(fg_color="white")
        
        self.resultado = "cancelar"

        # --- CABEÇALHO ---
        ctk.CTkLabel(
            self, 
            text="Processos Ausentes", 
            font=("Arial", 16, "bold"), 
            text_color="black"
        ).pack(pady=(5, 0), padx=20, anchor="w")

        ctk.CTkLabel(
            self, 
            text="Os seguintes programas não estão rodando:", 
            font=("Arial", 12),
            text_color="black"
        ).pack(anchor="w", padx=20)

        # --- LISTA VISUAL (ÍCONE + TEXTO) ---
        # Container para a lista
        frame_lista = ctk.CTkFrame(self, fg_color="white")
        frame_lista.pack(fill="both", expand=True, padx=10, pady=5)

        for nome in ausentes:
            # Cria uma linha para cada item
            row = ctk.CTkFrame(frame_lista, fg_color="transparent", height=30)
            row.pack(fill="x", pady=2)
            
            # Tenta pegar o ícone (precisamos do path que está na config)
            path = config_data.processos.get(nome, {}).get("path")
            icone = icon_manager.carregar(nome, path)

            # 1. Ícone
            lbl_icon = ctk.CTkLabel(row, text="", image=icone, width=30)
            lbl_icon.pack(side="left", padx=(5, 10))

            # 2. Nome em Negrito
            lbl_nome = ctk.CTkLabel(
                row, 
                text=nome, 
                font=("Arial", 13, "bold"), # Negrito aqui
                text_color="black"
            )
            lbl_nome.pack(side="left")

        # --- RODAPÉ COM BOTÕES ---
        frame_btns = ctk.CTkFrame(self, fg_color="transparent")
        frame_btns.pack(side="bottom", fill="x", padx=20, pady=(0,12))

        # Cancelar
        ctk.CTkButton(
            frame_btns, text="Cancelar", font=("Arial", 12),
            fg_color="#ef5350", hover_color="#d32f2f",
            width=80, height=32, command=self.on_sair
        ).pack(side="left")

        frame_acoes = ctk.CTkFrame(frame_btns, fg_color="transparent")
        frame_acoes.pack(side="right")

        # Iniciar mesmo assim
        ctk.CTkButton(
            frame_acoes, text="Iniciar mesmo assim", font=("Arial", 12),
            fg_color="transparent", border_width=1, border_color="gray", text_color="gray",
            hover_color="#f5f5f5", width=130, height=32, command=self.on_ignorar
        ).pack(side="left", padx=(0, 10))

        # Forçar
        ctk.CTkButton(
            frame_acoes, text="Forçar Início", font=("Arial", 12, "bold"),
            fg_color="green", hover_color="darkgreen",
            width=110, height=32, command=self.on_forcar
        ).pack(side="left")
        
    def on_sair(self):
        self.resultado = "cancelar"
        self.destroy()
    
    def on_ignorar(self):
        self.resultado = "ignorar"
        self.destroy()

    def on_forcar(self):
        self.resultado = "forcar"
        self.destroy()