import os
import customtkinter as ctk

from ..colors import AppColors
from ...infrastructure.system_utils import SystemUtils

class DialogoVerificacao(ctk.CTkToplevel):
    def __init__(self, parent, ausentes, icon_manager, config_data):
        super().__init__(parent, fg_color=AppColors.WHITE)
        self.title("Atenção")
        
        # --- 1. ADICIONANDO O ÍCONE DO APP ---
        # Busca o ícone usando o utilitário do sistema
        icon_path = SystemUtils.resource_path(os.path.join("assets", "icons", "app_icon.ico"))
        if os.path.exists(icon_path):
            # Usamos .after(200) para evitar um bug comum do CustomTkinter 
            # onde o ícone falha em carregar imediatamente no CTkToplevel
            self.after(200, lambda: self.iconbitmap(icon_path))
        
        # --- 2. CÁLCULO DE TAMANHO E POSIÇÃO (CENTRALIZADO NA TELA) ---
        altura_conteudo = len(ausentes) * 35 
        largura = 400
        altura = 160 + altura_conteudo
        
        # Obtém geometria da tela inteira
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        # Matemática para achar o centro da tela
        pos_x = (screen_w // 2) - (largura // 2)
        pos_y = (screen_h // 2) - (altura // 2)

        # Aplica geometria fixa e centralizada
        self.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")
        self.resizable(False, False)
        
        # Configurações de Janela Modal
        self.attributes("-topmost", True)
        self.grab_set() # Bloqueia a janela de trás
        
        # Removido self.configure(fg_color="white") para respeitar o tema global (Dark/Light)
        
        self.resultado = "cancelar"

        # --- CABEÇALHO ---
        # Removido text_color="black" para respeitar o tema
        ctk.CTkLabel(
            self, 
            text="Processos Ausentes", 
            font=("Arial", 16, "bold"),
            text_color=AppColors.NIGHT,
        ).pack(pady=(10, 5), padx=10, anchor="w")

        ctk.CTkLabel(
            self, 
            text="Os seguintes programas não estão rodando:", 
            font=("Arial", 12),
            text_color=AppColors.NIGHT
        ).pack(anchor="w", padx=10, pady=(0, 10))

        # --- LISTA VISUAL (ÍCONE + TEXTO) ---
        # Container para a lista usando fundo transparente para mesclar com a janela
        frame_lista = ctk.CTkFrame(self, fg_color="transparent")
        frame_lista.pack(fill="both", expand=True, padx=10, pady=5)

        for nome in ausentes:
            row = ctk.CTkFrame(frame_lista, fg_color="transparent", height=30)
            row.pack(fill="x", pady=2)
            
            path = config_data.processos.get(nome, {}).get("path")
            icone = icon_manager.carregar(nome, path)

            # Ícone
            lbl_icon = ctk.CTkLabel(row, text="", image=icone, width=30)
            lbl_icon.pack(side="left", padx=(5, 10))

            # Nome do Processo
            lbl_nome = ctk.CTkLabel(
                row, 
                text=nome, 
                font=("Arial", 12, "bold"),
                text_color=AppColors.NIGHT
            )
            lbl_nome.pack(side="left")

        # --- RODAPÉ COM BOTÕES ---
        frame_btns = ctk.CTkFrame(self, fg_color="transparent")
        frame_btns.pack(side="bottom", fill="x", padx=10, pady=(10, 20))

        # Cancelar
        ctk.CTkButton(
            frame_btns, text="Cancelar",
            font=("Arial", 12),
            text_color=AppColors.WHITE,
            fg_color =AppColors.FLAG_RED,
            hover_color="#d32f2f",
            width=80,
            height=32,
            command=self.on_sair
        ).pack(side="left")

        frame_acoes = ctk.CTkFrame(frame_btns, fg_color="transparent")
        frame_acoes.pack(side="right")

        # Iniciar mesmo assim
        # Adaptado para trocar a cor do texto dependendo se está no modo claro ou escuro
        ctk.CTkButton(
            frame_acoes,
            text="Iniciar mesmo assim",
            text_color=AppColors.WHITE,
            font=("Arial", 12),
            fg_color=AppColors.BALTIC_BLUE,
            width=130,
            height=32,
            command=self.on_ignorar
        ).pack(side="left", padx=(0, 10))

        # Forçar
        ctk.CTkButton(
            frame_acoes,
            text="Forçar Início",
            text_color=AppColors.WHITE,
            font=("Arial", 12, "bold"),
            fg_color=AppColors.DUSK_BLUE,
            width=110,
            height=32,
            command=self.on_forcar
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