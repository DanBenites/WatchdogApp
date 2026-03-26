# src/ui/components/service_modal.py
import threading
import customtkinter as ctk
from tkinter import messagebox
import tkinter as tk

from ...infrastructure.icon_manager import IconeManager
from ..colors import AppColors
from ...infrastructure.service_adapter import ServiceAdapter
from ...infrastructure.persistence import PersistenceRepository

class AdicionarServicoModal(ctk.CTkToplevel):
    def __init__(self, master_tab, servicos_view):
        super().__init__(master_tab, fg_color=AppColors.BRIGHT_SNOW)
        self.master_tab = master_tab
        self.servicos_view = servicos_view
        self.icon_manager = IconeManager()
        
        self.title("Adicionar Serviços ao Monitor")
        self.geometry("750x650")
        self.grab_set()
        self.transient(master_tab)
        
        self.servicos_selecionados = set()
        self.widgets_catalogo = []

        self.protocol("WM_DELETE_WINDOW", self.fechar_modal)

        self._build_header()
        self._build_search_and_actions()
        self._build_table()

        # Carrega a lista pesada numa thread separada
        threading.Thread(target=self._carregar_servicos_windows, daemon=True).start()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkButton(hdr, image=self.icon_manager._icons.get("chevron_left_dark"), text="", fg_color=AppColors.TRANSPARENT, hover_color=AppColors.PLATINUM, width=30, height=30, command=self.fechar_modal).pack(side="left", padx=5)
        ctk.CTkLabel(hdr, text="Catálogo de Serviços no Windows", font=("Arial", 16, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(side="left", padx=5)

    def _build_search_and_actions(self):
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=15, pady=5)
        
        # Barra de Pesquisa otimizada com KeyRelease
        self.entry_busca = ctk.CTkEntry(
            action_frame, 
            placeholder_text="Procurar por Nome ou Descrição...",
            fg_color=AppColors.WHITE, border_color=AppColors.PLATINUM,
            height=30, border_width=2, corner_radius=4, text_color=AppColors.CHARCOAL_BLUE
        )
        self.entry_busca.pack(side="left", expand=True, fill="x", padx=(0, 15))
        self.entry_busca.bind("<KeyRelease>", self._filtrar_lista)
        
        # Botão de Confirmação
        self.btn_confirm = ctk.CTkButton(
            action_frame, text="Adicionar (0)", fg_color=AppColors.GREEN, hover_color="#006400",
            text_color=AppColors.WHITE, height=30, font=("Arial", 13, "bold"), command=self._confirmar_selecao
        )
        self.btn_confirm.pack(side="right")

    def _build_table(self):
        table_container = ctk.CTkFrame(self, fg_color=AppColors.WHITE, corner_radius=8, border_width=1, border_color=AppColors.PLATINUM)
        table_container.pack(fill="both", expand=True, padx=15, pady=(10, 15))
        
        # Cabeçalho da Tabela - Usando place percentual para alinhamento perfeito
        hdr_frame = ctk.CTkFrame(table_container, fg_color=AppColors.PLATINUM, corner_radius=4, height=30)
        hdr_frame.pack(fill="x", pady=(0, 2))
        hdr_frame.pack_propagate(False)

        ctk.CTkLabel(hdr_frame, text="Sel.", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.0, relwidth=0.08, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Nome do Serviço", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.08, relwidth=0.30, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Descrição", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.38, relwidth=0.60, rely=0, relheight=1)

        self.scroll_area = ctk.CTkScrollableFrame(table_container, fg_color="transparent")
        self.scroll_area.pack(fill="both", expand=True)

        self.lbl_loading = ctk.CTkLabel(self.scroll_area, text="A varrer serviços do sistema...", text_color="gray", font=("Arial", 14))
        self.lbl_loading.pack(pady=40)

    def _carregar_servicos_windows(self):
        servicos = ServiceAdapter.get_all_services()
        self.after(0, self._renderizar_lista, servicos)

    def _renderizar_lista(self, servicos):
        self.lbl_loading.destroy()
        servicos_atuais = self.master_tab.config_data.servicos

        for index, svc in enumerate(servicos):
            name = svc["name"]
            desc = svc["desc"]
            is_monitored = name in servicos_atuais

            # Lógica de Cores
            if is_monitored:
                bg_color = AppColors.DUSK_BLUE
                text_color = AppColors.WHITE  
            else:
                bg_color = AppColors.BRIGHT_SNOW if index % 2 == 0 else AppColors.WHITE
                text_color = AppColors.CHARCOAL_BLUE
            
            # 1. HÍBRIDO: Frame nativo para máxima performance (bd=0 remove bordas feias)
            row = tk.Frame(self.scroll_area, bg=bg_color, bd=0, highlightthickness=0, height=36)
            row.pack_propagate(False) # Força a altura exata de 36px para não achatar
            
            # 2. HÍBRIDO: Componente Moderno CTkCheckBox centralizado com rely=0.5
            chk_var = ctk.BooleanVar(value=is_monitored)
            chk = ctk.CTkCheckBox(row, text="", variable=chk_var, width=24, checkbox_width=20, checkbox_height=20, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE)
            chk.place(relx=0.02, rely=0.5, anchor="w") 
            
            # 3. HÍBRIDO: Labels nativos (tk.Label) com fontes e cores customizadas
            lbl_name = tk.Label(row, text=name, bg=bg_color, fg=text_color, font=("Arial", 10, "bold"), anchor="w", bd=0)
            lbl_name.place(relx=0.08, relwidth=0.30, rely=0, relheight=1)
            
            desc_display = desc if len(desc) < 70 else desc[:67] + "..."
            lbl_desc = tk.Label(row, text=desc_display, bg=bg_color, fg=text_color, font=("Arial", 10), anchor="w", bd=0)
            lbl_desc.place(relx=0.38, relwidth=0.60, rely=0, relheight=1)

            if is_monitored:
                chk.configure(state="disabled")
                lbl_desc.config(text=f"[Já Monitorado] {desc_display}")
            else:
                # Comandos de clique amarrados aos widgets nativos
                def ao_clicar(event=None, n=name): self._alternar_selecao(n)
                
                # Clique na Checkbox
                chk.configure(command=lambda n=name: self._alternar_selecao(n))
                
                # Clique na Linha ou Textos
                for widget in (lbl_name, lbl_desc, row):
                    widget.bind("<Button-1>", ao_clicar)
                    widget.config(cursor="hand2")

            self.widgets_catalogo.append({
                "row": row, "name": name, "desc": desc, "monitored": is_monitored,
                "chk_var": chk_var, "lbl_name": lbl_name, "lbl_desc": lbl_desc, "bg_padrao": bg_color
            })
            
            row.pack(fill="x", pady=1)

    def _alternar_selecao(self, name):
        # Encontra o item de forma rápida e direta no catálogo
        item = next((x for x in self.widgets_catalogo if x["name"] == name), None)
        if not item or item["monitored"]: return

        if name in self.servicos_selecionados:
            # Desmarcar: Retorna às cores nativas
            self.servicos_selecionados.remove(name)
            bg_novo = item["bg_padrao"]
            fg_novo = AppColors.CHARCOAL_BLUE
            item["chk_var"].set(False)
        else:
            # Marcar: Aplica o Verde Claro de seleção igual aos Processos
            self.servicos_selecionados.add(name)
            bg_novo = "#D1E7DD" 
            fg_novo = AppColors.GREEN
            item["chk_var"].set(True)

        # Atualiza o Tkinter nativo (usamos .config em vez de .configure)
        item["row"].config(bg=bg_novo)
        item["lbl_name"].config(bg=bg_novo, fg=fg_novo)
        item["lbl_desc"].config(bg=bg_novo, fg=fg_novo)
            
        self.btn_confirm.configure(text=f"Adicionar ({len(self.servicos_selecionados)})")

    def _filtrar_lista(self, event=None):
        query = self.entry_busca.get().lower()
        index_visivel = 0
        
        # Como usamos tk.Frame, o pack_forget() em massa é praticamente instantâneo
        for item in self.widgets_catalogo:
            if item["row"].winfo_ismapped():
                item["row"].pack_forget()
                
        for item in self.widgets_catalogo:
            if query in item["name"].lower() or query in item["desc"].lower():
                item["row"].pack(fill="x", pady=1)
                
                # Recalcula dinamicamente o zebrado (mantendo o verde se estiver selecionado)
                novo_bg = AppColors.BRIGHT_SNOW if index_visivel % 2 == 0 else AppColors.WHITE
                item["bg_padrao"] = novo_bg
                
                if item["name"] not in self.servicos_selecionados:
                    item["row"].config(bg=novo_bg)
                    item["lbl_name"].config(bg=novo_bg)
                    item["lbl_desc"].config(bg=novo_bg)
                
                index_visivel += 1

    def _confirmar_selecao(self):
        count = 0
        for name in self.servicos_selecionados:
            if name not in self.master_tab.config_data.servicos:
                self.master_tab.config_data.servicos[name] = {
                    "state_actions": {"running": "Não Fazer Nada", "stopped": "Reiniciar", "paused": "Não Fazer Nada"},
                    "perf_limits": {"cpu": 0.0, "ram": 0.0, "tolerance": 30, "max_restarts": 3, "reset_days": 0},
                    "snooze": {"active": False, "until": 0}
                }
                count += 1
                
        if count > 0:
            PersistenceRepository.salvar(self.master_tab.config_data)
            self.servicos_view.popular_tabela() 
            self.master_tab.log(f"➕ {count} novo(s) serviço(s) adicionado(s) ao monitor.")
            
        self.fechar_modal()
    
    def fechar_modal(self):
        self.grab_release()  
        self.destroy()