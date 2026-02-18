import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import datetime
from ..colors import AppColors
from ...infrastructure.icon_manager import IconeManager

class LogTab(ctk.CTkFrame):
    def __init__(self, parent, log_manager):
        super().__init__(parent, fg_color=AppColors.BRIGHT_SNOW)
        self.log_manager = log_manager
        self.icon_manager = IconeManager()
        self._setup_ui()

    def _setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.container = ctk.CTkFrame(
            self, 
            fg_color=AppColors.WHITE, 
            border_color=AppColors.PLATINUM, 
            border_width=2, 
            corner_radius=8
        )
        self.container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.log_text = ctk.CTkTextbox(self.container,
            font=("Consolas", 12),
            state="disabled",
            fg_color=AppColors.BRIGHT_SNOW,
            border_color=AppColors.PLATINUM, 
            border_width=2,
            corner_radius=6)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

        frame_tools = ctk.CTkFrame(self.container, fg_color="transparent", height=40)
        frame_tools.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(frame_tools, image= self.icon_manager._icons.get("file_save") , text="Salvar em Arquivo", width=140, fg_color=AppColors.DUSK_BLUE, command=self._salvar_log).pack(side="right", padx=5)
        ctk.CTkButton(frame_tools, image= self.icon_manager._icons.get("copy") , text="Copiar Tudo", width=120, fg_color=AppColors.BALTIC_BLUE, command=self._copiar_log).pack(side="right", padx=5)
        ctk.CTkButton(frame_tools, image= self.icon_manager._icons.get("folder"), text="Abrir Pasta", width=120, fg_color=AppColors.STORMY_TEAL, command=self._abrir_pasta_logs).pack(side="right", padx=5)
        ctk.CTkButton(frame_tools, image= self.icon_manager._icons.get("close_console"), text="Limpar", width=100, fg_color=AppColors.FLAG_RED, hover_color="#b71c1c", command=self._limpar_log).pack(side="left")

    def adicionar_linha(self, texto):
        try:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", texto + "\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        except: pass

    def _salvar_log(self):
        conteudo = self.log_text.get("1.0", "end").strip()
        if not conteudo: return messagebox.showinfo("Logs", "Vazio.")
        
        agora = datetime.now().strftime("%d-%m-%Y-%H-%M")
        path = filedialog.asksaveasfilename(initialfile=f"Log {agora}", defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f: f.write(conteudo)
            messagebox.showinfo("Sucesso", "Salvo!")

    def _copiar_log(self):
        conteudo = self.log_text.get("1.0", "end")
        self.master.clipboard_clear()
        self.master.clipboard_append(conteudo)
        self.master.update()

    def _limpar_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
    
    def _abrir_pasta_logs(self):
        try:
            path = self.log_manager.log_dir
            if os.path.exists(path):
                os.startfile(path)
            else:
                messagebox.showerror("Erro", f"Pasta não encontrada:\n{path}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir pasta: {e}")