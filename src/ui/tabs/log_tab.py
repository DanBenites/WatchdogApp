import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import datetime

class LogTab(ctk.CTkFrame):
    def __init__(self, parent, log_manager):
        super().__init__(parent)
        self.log_manager = log_manager
        self._setup_ui()

    def _setup_ui(self):
        self.log_text = ctk.CTkTextbox(self, font=("Consolas", 12), state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        frame_tools = ctk.CTkFrame(self, fg_color="transparent", height=40)
        frame_tools.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(frame_tools, text="Salvar em Arquivo", width=140, fg_color="#1f538d", command=self._salvar_log).pack(side="right", padx=(0, 5))
        ctk.CTkButton(frame_tools, text="Copiar Tudo", width=120, fg_color="gray", command=self._copiar_log).pack(side="right", padx=5)
        ctk.CTkButton(frame_tools, text="Abrir Pasta", width=120, fg_color="green", command=self._abrir_pasta_logs).pack(side="right", padx=5)
        ctk.CTkButton(frame_tools, text="Limpar", width=100, fg_color="#c62828", hover_color="#b71c1c", command=self._limpar_log).pack(side="left")

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