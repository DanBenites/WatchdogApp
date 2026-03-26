import threading
import customtkinter as ctk

from ...infrastructure.icon_manager import IconeManager
from ..colors import AppColors
from ...services.process_use_cases import OSProcessUseCase

class AdicionarProcessoModal(ctk.CTkToplevel):
    """Janela Flutuante para selecionar e adicionar processos."""
    def __init__(self, master_tab, processos_view):
        super().__init__(master_tab, fg_color=AppColors.BRIGHT_SNOW)
        self.master_tab = master_tab
        self.processos_view = processos_view
        self.icon_manager = IconeManager()
        
        self.title("Adicionar Processos ao Monitor")
        self.geometry("750x650")
        self.grab_set() 
        self.transient(master_tab) 

        # Garante que clicar no "X" da janela execute o fechamento limpo
        self.protocol("WM_DELETE_WINDOW", self.fechar_modal)
        
        self.selected_processes = {}
        self.all_catalog_widgets = []

        self._build_ui()
        threading.Thread(target=self._load_processes_to_ui, daemon=True).start()

    def _build_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkButton(header_frame, image=self.icon_manager._icons.get("chevron_left_dark"), text="", fg_color=AppColors.TRANSPARENT, hover_color=AppColors.PLATINUM, width=30, height=30, command=self.fechar_modal).pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Catálogo de Processos Ativos", font=("Arial", 16, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(side="left")

        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=5)
        
        self.entry_busca = ctk.CTkEntry(
            action_frame, 
            placeholder_text="Buscar por Nome...", 
            fg_color=AppColors.WHITE, 
            border_width=2, 
            border_color=AppColors.PLATINUM, 
            height=30, 
            corner_radius=4,
            text_color=AppColors.CHARCOAL_BLUE
        )
        self.entry_busca.pack(side="left", expand=True, fill="x", padx=(0, 15))
        
        # Usamos o evento de soltar a tecla em vez de StringVar
        self.entry_busca.bind("<KeyRelease>", self.filter_list)
        self.btn_confirm_add = ctk.CTkButton(action_frame, text="Adicionar (0)", fg_color=AppColors.GREEN, hover_color="#006400", height=30, font=("Arial", 13, "bold"), command=self.confirm_selection)
        self.btn_confirm_add.pack(side="right")

        table_container = ctk.CTkFrame(self, corner_radius=8, fg_color=AppColors.WHITE, border_width=1, border_color=AppColors.PLATINUM)
        table_container.pack(fill="both", expand=True, padx=15, pady=(10, 15))
        
        hdr_frame = ctk.CTkFrame(table_container, fg_color=AppColors.PLATINUM, corner_radius=0, height=30)
        hdr_frame.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(hdr_frame, text="Sel.", width=40, anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(side="left", padx=5)
        ctk.CTkLabel(hdr_frame, text="Nome do Processo", width=250, anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(side="left", padx=5)

        self.catalog_scroll = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.catalog_scroll.pack(fill="both", expand=True)
        
        self.lbl_loading = ctk.CTkLabel(self.catalog_scroll, text="A varrer processos do sistema...", font=("Arial", 14), text_color="gray")
        self.lbl_loading.pack(pady=40)

    def _load_processes_to_ui(self):
        grupos = OSProcessUseCase.obter_processos_agrupados()
        self.after(0, self._render_catalog, grupos)

    def _render_catalog(self, grupos):
        self.lbl_loading.destroy()
        
        self._render_group("APLICATIVOS", grupos["apps"], AppColors.DUSK_BLUE)
        self._render_group("SEGUNDO PLANO", grupos["back"], AppColors.GREEN)
        self._render_group("SISTEMA", grupos["system"], "gray")

    def _render_group(self, titulo, dados, cor):
        if not dados: return
        
        lbl_titulo = ctk.CTkLabel(self.catalog_scroll, text=titulo, anchor="w", font=("Arial", 12, "bold"), text_color=cor)
        lbl_titulo.pack(fill="x", pady=(10, 2), padx=5)
        self.all_catalog_widgets.append({"row": lbl_titulo, "nome": titulo, "is_title": True})

        for nome in sorted(dados.keys()):
            info = dados[nome]
            path = info['path']
            is_monitored = nome in self.master_tab.config_data.processos
            
            if is_monitored:
                bg_color = AppColors.DUSK_BLUE
                text_color = AppColors.WHITE  
            else:
                bg_color = AppColors.BRIGHT_SNOW
                text_color = AppColors.CHARCOAL_BLUE
            
            row = ctk.CTkFrame(self.catalog_scroll, fg_color=bg_color, corner_radius=0)
            
            # --- CHECKBOX NATIVO ---
            chk_var = ctk.BooleanVar(value=is_monitored)
            chk = ctk.CTkCheckBox(row, text="", variable=chk_var, width=20, checkbox_width=20, checkbox_height=20, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE)
            chk.pack(side="left", padx=(10, 5), pady=2)
            
            # Nome e Ícone do App
            icone = self.master_tab.icon_manager.carregar(nome, path)
            lbl_nome = ctk.CTkLabel(row, text=f"  {nome} ({info['count']})" if info['count'] > 1 else f"  {nome}", image=icone, compound="left", text_color=text_color, font=("Arial", 12), anchor="w")
            lbl_nome.pack(side="left", padx=5)
            
            if is_monitored:
                chk.configure(state="disabled") # Bloqueia o checkbox se já for monitorado
                ctk.CTkLabel(row, text="[Já Monitorado]", text_color=AppColors.PLATINUM, font=("Arial", 11)).pack(side="right", padx=15)
            else:
                # 1. Se o utilizador clicar diretamente na checkbox nativa:
                chk.configure(command=lambda n=nome, p=path, r=row, cv=chk_var, ln=lbl_nome: self.toggle_selection(n, p, r, cv, ln))
                
                # 2. Se o utilizador clicar na linha ou no nome do aplicativo:
                def on_row_click(event=None, n=nome, p=path, r=row, cv=chk_var, ln=lbl_nome): 
                    cv.set(not cv.get()) # Inverte a checkbox visualmente por código
                    self.toggle_selection(n, p, r, cv, ln) # Roda a lógica de marcação

                lbl_nome.bind("<Button-1>", on_row_click)
                row.bind("<Button-1>", on_row_click)
                
                lbl_nome.configure(cursor="hand2")
                row.configure(cursor="hand2")

            self.all_catalog_widgets.append({"row": row, "nome": nome, "is_title": False, "monitored": is_monitored})
            row.pack(fill="x", pady=1)

    def toggle_selection(self, nome, path, row, chk_var, lbl_nome):
        # A lógica agora lê diretamente o estado da CheckBox nativa (chk_var)
        if chk_var.get():
            # Marcar
            self.selected_processes[nome] = {"nome": nome, "path": path}
            row.configure(fg_color="#D1E7DD") # Fundo verde claro
            lbl_nome.configure(text_color=AppColors.GREEN)
        else:
            # Desmarcar
            if nome in self.selected_processes:
                del self.selected_processes[nome]
            row.configure(fg_color=AppColors.BRIGHT_SNOW)
            lbl_nome.configure(text_color=AppColors.CHARCOAL_BLUE)
            
        self.btn_confirm_add.configure(text=f"Adicionar ({len(self.selected_processes)})")

    def filter_list(self, event=None):
        query = self.entry_busca.get().lower()
        
        for item in self.all_catalog_widgets:
            if item["row"].winfo_ismapped():
                item["row"].pack_forget()
                
        for item in self.all_catalog_widgets:
            if item["is_title"]:
                # Se não há busca, mostra os títulos de categoria
                if not query:
                    item["row"].pack(fill="x", pady=(10, 2), padx=5)
            else:
                # Se o texto da busca estiver no nome do processo, mostra a linha
                if query in item["nome"].lower():
                    item["row"].pack(fill="x", pady=1)

    def confirm_selection(self):
        if not self.selected_processes: return
        
        lista_adicionar = list(self.selected_processes.values())
        self.master_tab.process_use_case.adicionar_processos(lista_adicionar)
        
        self.processos_view.popular_tabela()
        self.destroy()
    
    def fechar_modal(self):
        """Método seguro para fechar a janela, liberando o foco primeiro."""
        self.grab_release()  
        self.destroy()