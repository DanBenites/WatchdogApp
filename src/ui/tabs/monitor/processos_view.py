import subprocess
import threading
import time
import customtkinter as ctk
from tkinter import messagebox

from ....infrastructure.icon_manager import IconeManager
from ...colors import AppColors
from ...components.process_modal import AdicionarProcessoModal
from ....services.process_use_cases import OSProcessUseCase
from ...components.process_properties import ProcessPropertiesWindow
from ....infrastructure.process_adapter import ProcessAdapter
from ....domain.process_engine import WatchdogProcessEngine
from ....infrastructure.system_utils import SystemUtils

class ProcessosView(ctk.CTkFrame):
    """Tabela de Processos Monitorados"""
    def __init__(self, parent, master_tab):
        super().__init__(parent, fg_color=AppColors.BRIGHT_SNOW)
        self.master_tab = master_tab 
        self.linhas_visuais = {} 
        self.running = True
        self.icon_manager = IconeManager()
        self.process_engine = WatchdogProcessEngine()
        
        self._build_header()
        self._build_table()
        self._build_footer()
        
        self.popular_tabela()
        
        self.update_thread = threading.Thread(target=self.loop_atualizacao_tabela, daemon=True)
        self.update_thread.start()

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        # Barra de busca corrigida (sem o Frame extra que corta as bordas)
        self.entry_busca = ctk.CTkEntry(
            header_frame, 
            placeholder_text="Buscar processos monitorados...", 
            fg_color=AppColors.WHITE, 
            border_width=2, 
            border_color=AppColors.PLATINUM, 
            height=30, 
            corner_radius=4,
            text_color=AppColors.CHARCOAL_BLUE
        )
        self.entry_busca.pack(side="left", expand=True, fill="x", padx=(0, 15))
        self.entry_busca.bind("<KeyRelease>", self.filtrar_tabela)

        
        self.btn_add = ctk.CTkButton(
            header_frame, image=self.icon_manager._icons.get("add"), text="Adicionar Processos", font=("Arial", 13, "bold"),
            fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE, height=30,
            command=self.abrir_modal_adicionar
        )
        self.btn_add.pack(side="right")

    def _build_table(self):
        self.table_container = ctk.CTkScrollableFrame(self, fg_color=AppColors.WHITE, border_color=AppColors.PLATINUM, border_width=1, corner_radius=8)
        self.table_container.pack(fill="both", expand=True)

        hdr_frame = ctk.CTkFrame(self.table_container, fg_color=AppColors.PLATINUM, corner_radius=4, height=30)
        hdr_frame.pack(fill="x", pady=(0, 5))
        hdr_frame.pack_propagate(False) 

        # Layout Percentual Fixo (relx = Posição de início, relwidth = Largura da coluna)
        ctk.CTkLabel(hdr_frame, text="  Processo", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.0, relwidth=0.28, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Regra", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.28, relwidth=0.25, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Status", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.53, relwidth=0.16, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="CPU (%)", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.69, relwidth=0.09, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="RAM (MB)", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.78, relwidth=0.09, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Ações", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.87, relwidth=0.13, rely=0, relheight=1)
    
    def _build_footer(self):
        self.btn_start = ctk.CTkButton(
            self, text="INICIAR MONITORAMENTO", image=self.icon_manager._icons.get("play"), text_color=AppColors.WHITE,
            fg_color=AppColors.DUSK_BLUE, height=34, font=("Arial", 14, "bold"),
            command=self.master_tab.toggle_monitor
        )
        self.btn_start.pack(fill="x", pady=(10, 0))

    def criar_linha(self, nome, regra, path=None):

        if regra == "Sempre Encerrar (Blacklist)":
            bg_color = "#d6d6d6" # Cinza de Blacklist
        else:
            bg_color = AppColors.BRIGHT_SNOW if len(self.linhas_visuais) % 2 == 0 else AppColors.WHITE
        
        # A linha agora precisa de uma altura fixa (height=42) para os itens se alinharem dentro
        row = ctk.CTkFrame(self.table_container, fg_color=bg_color, corner_radius=0, height=42)
        row.pack(fill="x", pady=(0, 2))
        row.pack_propagate(False) 

        icone = self.master_tab.icon_manager.carregar(nome, path)
        
        # As mesmas percentagens do cabeçalho são aplicadas a cada linha!
        lbl_nome = ctk.CTkLabel(row, text=f"  {nome}", image=icone, compound="left", anchor="w", text_color=AppColors.CHARCOAL_BLUE)
        lbl_nome.place(relx=0.01, relwidth=0.27, rely=0, relheight=1)

        combo_regra = ctk.CTkOptionMenu(
            row, values=["Não Reiniciar", "Sempre Reiniciar", "Reiniciar se erro Windows", "Reinício Condicional", "Sempre Encerrar (Blacklist)"],
            fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT, button_color=AppColors.PLATINUM,
            command=lambda r, n=nome: self.atualizar_regra(n, r)
        )
        combo_regra.set(regra)
        # O rely e relheight dão um espaçamento em cima e em baixo para a caixa não colar nas bordas
        combo_regra.place(relx=0.28, relwidth=0.24, rely=0.15, relheight=0.7) 

        lbl_status = ctk.CTkLabel(row, text="Aguardando", anchor="center", text_color="gray", font=("Arial", 12, "bold"))
        lbl_status.place(relx=0.53, relwidth=0.16, rely=0, relheight=1)
        
        lbl_cpu = ctk.CTkLabel(row, text="0.0", anchor="center", text_color=AppColors.CHARCOAL_BLUE)
        lbl_cpu.place(relx=0.69, relwidth=0.09, rely=0, relheight=1)
        
        lbl_ram = ctk.CTkLabel(row, text="0", anchor="center", text_color=AppColors.CHARCOAL_BLUE)
        lbl_ram.place(relx=0.78, relwidth=0.09, rely=0, relheight=1)

        frm_act = ctk.CTkFrame(row, fg_color="transparent")
        frm_act.place(relx=0.87, relwidth=0.13, rely=0, relheight=1)
        
        btn_group_frame = ctk.CTkFrame(frm_act, fg_color="transparent")
        btn_group_frame.pack(expand=True)

        
        btn_edit = ctk.CTkButton(btn_group_frame, text="", image=self.icon_manager._icons.get("edit_light"), width=30, height=26, fg_color="#0056b3", hover_color="#004494", command=lambda: self.editar_processo(nome))
        btn_edit.pack(side="left", padx=(0, 5))

        btn_del = ctk.CTkButton(btn_group_frame, text="✕", width=24, height=24, fg_color="#dc3545", hover_color="#c82333", command=lambda: self.remover_processo(nome))
        btn_del.pack(side="left", padx=0)

        self.linhas_visuais[nome] = {"row": row, "combo": combo_regra, "btn_edit": btn_edit, "btn_del": btn_del, "status": lbl_status, "cpu": lbl_cpu, "ram": lbl_ram}   
    
    def popular_tabela(self):
        for w in self.linhas_visuais.values(): w["row"].destroy()
        self.linhas_visuais.clear()
        
        for nome, dados in self.master_tab.config_data.processos.items():
            self.criar_linha(nome, dados['regra'], dados.get("path"))

    def atualizar_regra(self, nome, nova_regra):
        if self.master_tab.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para editar regras.")
            self.linhas_visuais[nome]["combo"].set(self.master_tab.config_data.processos[nome]['regra'])
            return
        self.master_tab.process_use_case.atualizar_regra(nome, nova_regra)
        # Recalcula as cores na hora em que o usuário muda a combobox!
        self.recalcular_cores_linhas()
    
    def editar_processo(self, nome):
        """Abre opções avançadas do processo"""
        if self.master_tab.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para editar propriedades.")
            return
            
        # Abre a nova janela modal passando o nome do processo a ser editado
        ProcessPropertiesWindow(self.master_tab, self, nome)

    def remover_processo(self, nome):
        if self.master_tab.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para remover itens.")
            return

        if self.master_tab.process_use_case.remover_processo(nome):
            self.linhas_visuais[nome]["row"].destroy()
            del self.linhas_visuais[nome]
            self.recalcular_cores_linhas()

    def recalcular_cores_linhas(self):
        index_visivel = 0
        for nome, widget_data in self.linhas_visuais.items():
            if widget_data["row"].winfo_ismapped():
                regra = widget_data["combo"].get()
                
                # Se for Blacklist, pinta de cinza. Senão, faz o efeito zebrado.
                if regra == "Sempre Encerrar (Blacklist)":
                    bg_color = "#d6d6d6" 
                else:
                    bg_color = AppColors.BRIGHT_SNOW if index_visivel % 2 == 0 else AppColors.WHITE
                    
                widget_data["row"].configure(fg_color=bg_color)
                index_visivel += 1

    def filtrar_tabela(self, event=None):
        query = self.entry_busca.get().lower()
        
        # 1. Esconde TODAS as linhas visíveis para "limpar" a tabela
        for widget_data in self.linhas_visuais.values():
            if widget_data["row"].winfo_ismapped():
                widget_data["row"].pack_forget()
                
        # 2. Re-adiciona apenas as que dão match, garantindo a ordem original
        index_visivel = 0
        for nome, widget_data in self.linhas_visuais.items():
            if query in nome.lower():
                # Empacota novamente na ordem correta
                widget_data["row"].pack(fill="x", pady=(0, 2))
                
                # Reajusta o efeito zebrado (cores alternadas) apenas para os itens que ficaram na tela
                bg_color = AppColors.BRIGHT_SNOW if index_visivel % 2 == 0 else AppColors.WHITE
                widget_data["row"].configure(fg_color=bg_color)
                
                index_visivel += 1

    def definir_estado_edicao(self, estado):
        self.btn_add.configure(state=estado)
        for widget_data in self.linhas_visuais.values():
            widget_data["combo"].configure(state=estado)
            widget_data["btn_del"].configure(state=estado)
            widget_data["btn_edit"].configure(state=estado)

    def abrir_modal_adicionar(self):
        if not self.master_tab.app.auth_service.verificar_status_atual():
            self.master_tab.app.exibir_overlay_licenca()
            return
        if self.master_tab.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para adicionar itens.")
            return
        
        AdicionarProcessoModal(self.master_tab, self)

    def loop_atualizacao_tabela(self):
        """Thread ultra-leve: apenas lê os dados já processados pelo Motor."""
        while self.running:
            if not self.master_tab.engine.rodando:
                # Se o motor está desligado, limpa visualmente a tela
                for nome, widgets in self.linhas_visuais.items():
                    widgets["cpu"].configure(text="0.0 %")
                    widgets["ram"].configure(text="0 MB")
                    widgets["status"].configure(text="Aguard. Monitor", text_color="gray")
                time.sleep(1)
                continue
                
            # Lê a memória partilhada do Motor
            metrics = getattr(self.master_tab.engine, "latest_metrics", {})
            
            for nome, widgets in self.linhas_visuais.items():
                try:
                    # Se não houver dados, exibe Ausente
                    dados = metrics.get(nome, {"status": "Ausente", "cpu": 0.0, "ram": 0.0, "regra": "Não Reiniciar", "acao_pendente": "Nada"})
                    
                    status_real = dados["status"]
                    regra = dados["regra"]
                    acao = dados["acao_pendente"]

                    # --- ATUALIZAÇÃO VISUAL ---
                    if status_real == "Em Execução":
                        if regra == "Sempre Encerrar (Blacklist)":
                            widgets["status"].configure(text="Bloqueando...", text_color="#dc3545")
                        else:
                            if "Parar" in acao:
                                widgets["status"].configure(text="Encerrando...", text_color="#dc3545")
                            else:
                                widgets["status"].configure(text="Em Execução", text_color=AppColors.GREEN)
                            
                        widgets["cpu"].configure(text=f"{dados['cpu']:.1f} %")
                        widgets["ram"].configure(text=f"{dados['ram']:.0f} MB")
                    else:
                        widgets["cpu"].configure(text="0.0 %")
                        widgets["ram"].configure(text="0 MB")
                        
                        if acao == "Iniciar":
                            widgets["status"].configure(text="Iniciando...", text_color="#17a2b8")
                        elif regra in ["Sempre Reiniciar", "Reiniciar se erro Windows", "Reinício Condicional"]:
                            widgets["status"].configure(text="Reiniciando...", text_color="#ffc107")
                        elif regra == "Sempre Encerrar (Blacklist)":
                            widgets["status"].configure(text="Bloqueado", text_color="gray")
                        else:
                            widgets["status"].configure(text="Ausente", text_color="gray")
                            
                except Exception:
                    pass
                    
            # Loop da interface muito mais rápido e suave
            time.sleep(1)

    def destroy(self):
        self.running = False
        super().destroy()