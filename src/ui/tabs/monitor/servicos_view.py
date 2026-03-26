# src/ui/tabs/monitor/servicos_view.py
import threading
import time
import customtkinter as ctk
from tkinter import messagebox

from ....infrastructure.icon_manager import IconeManager
from ...colors import AppColors
from ...components.service_properties import ServicePropertiesWindow
from ...components.service_modal import AdicionarServicoModal
from ....infrastructure.service_adapter import ServiceAdapter
from ....infrastructure.persistence import PersistenceRepository

class ServicosView(ctk.CTkFrame):
    """Tabela de Serviços Monitorizados do Windows (Padrão ServiceGuard)"""
    def __init__(self, parent, master_tab):
        super().__init__(parent, fg_color=AppColors.BRIGHT_SNOW)
        self.master_tab = master_tab 
        self.linhas_visuais = {} 
        self.running = True
        self.icon_manager = IconeManager()
        
        self._build_header()
        self._build_table()
        
        self.popular_tabela()
        
        self.update_thread = threading.Thread(target=self.loop_atualizacao_tabela, daemon=True)
        self.update_thread.start()

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        self.entry_busca = ctk.CTkEntry(
            header_frame, placeholder_text="Buscar serviços monitorizados...", 
            fg_color=AppColors.WHITE, border_width=2, border_color=AppColors.PLATINUM, 
            height=34, corner_radius=4, text_color=AppColors.CHARCOAL_BLUE, font=("Arial", 12)
        )
        self.entry_busca.pack(side="left", expand=True, fill="x", padx=(0, 15))
        self.entry_busca.bind("<KeyRelease>", self.filtrar_tabela)

        self.btn_add = ctk.CTkButton(
            header_frame, image=self.icon_manager._icons.get("add"), text="Adicionar Serviços", 
            font=("Arial", 13, "bold"), fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE, 
            height=34, command=self.abrir_modal_adicionar
        )
        self.btn_add.pack(side="right")

    def _build_table(self):
        self.table_container = ctk.CTkFrame(self, fg_color=AppColors.WHITE, border_color=AppColors.PLATINUM, border_width=1, corner_radius=8)
        self.table_container.pack(fill="both", expand=True)

        hdr_frame = ctk.CTkFrame(self.table_container, fg_color=AppColors.PLATINUM, corner_radius=4, height=34)
        hdr_frame.pack(fill="x", pady=(2, 2), padx=2)
        hdr_frame.pack_propagate(False) 

        # Colunas Fiéis ao ServiceGuard (Alinhamento Percentual)
        ctk.CTkLabel(hdr_frame, text="  Nome", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.0, relwidth=0.20, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="PID", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.20, relwidth=0.06, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Descrição", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.26, relwidth=0.26, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Grupo", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.52, relwidth=0.08, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Status", anchor="w", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.60, relwidth=0.12, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Controladores", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.72, relwidth=0.18, rely=0, relheight=1)
        ctk.CTkLabel(hdr_frame, text="Ações", anchor="center", font=("Arial", 12, "bold"), text_color=AppColors.CHARCOAL_BLUE).place(relx=0.90, relwidth=0.10, rely=0, relheight=1)

        self.scroll_area = ctk.CTkScrollableFrame(self.table_container, fg_color="transparent")
        self.scroll_area.pack(fill="both", expand=True, padx=2, pady=2)

    def criar_linha(self, nome, config_dados):
        bg_color = AppColors.BRIGHT_SNOW if len(self.linhas_visuais) % 2 == 0 else AppColors.WHITE
        
        row = ctk.CTkFrame(self.scroll_area, fg_color=bg_color, corner_radius=0, height=44)
        row.pack(fill="x", pady=(0, 1))
        row.pack_propagate(False) 

        # 1. Nome
        lbl_nome = ctk.CTkLabel(row, text=f"  {nome}", anchor="w", text_color=AppColors.CHARCOAL_BLUE, font=("Arial", 12, "bold"))
        lbl_nome.place(relx=0.0, relwidth=0.20, rely=0, relheight=1)

        # 2. PID
        lbl_pid = ctk.CTkLabel(row, text="-", anchor="w", text_color=AppColors.NIGHT, font=("Arial", 11))
        lbl_pid.place(relx=0.20, relwidth=0.06, rely=0, relheight=1)

        # 3. Descrição
        lbl_desc = ctk.CTkLabel(row, text="Aguardar dados...", anchor="w", text_color="gray", font=("Arial", 11))
        lbl_desc.place(relx=0.26, relwidth=0.26, rely=0, relheight=1)

        # 4. Grupo (Normalmente N/D nos serviços base, mas mantido por fidelidade)
        lbl_grupo = ctk.CTkLabel(row, text="N/D", anchor="w", text_color="gray", font=("Arial", 11))
        lbl_grupo.place(relx=0.52, relwidth=0.08, rely=0, relheight=1)

        # 5. Status
        lbl_status = ctk.CTkLabel(row, text="...", anchor="w", text_color="gray", font=("Arial", 12, "bold"))
        lbl_status.place(relx=0.60, relwidth=0.12, rely=0, relheight=1)

        # 6. Controladores (Start, Stop, Pause, Restart)
        frm_ctrl = ctk.CTkFrame(row, fg_color="transparent")
        frm_ctrl.place(relx=0.72, relwidth=0.18, rely=0, relheight=1)
        
        ctrl_group = ctk.CTkFrame(frm_ctrl, fg_color="transparent")
        ctrl_group.pack(expand=True)
        
        btn_play = ctk.CTkButton(ctrl_group, text="▶", width=28, height=24, fg_color="#28a745", hover_color="#218838", command=lambda: self._acao_rapida(nome, "start"))
        btn_play.pack(side="left", padx=2)
        btn_stop = ctk.CTkButton(ctrl_group, text="⏹", width=28, height=24, fg_color="#dc3545", hover_color="#c82333", command=lambda: self._acao_rapida(nome, "stop"))
        btn_stop.pack(side="left", padx=2)
        btn_pause = ctk.CTkButton(ctrl_group, text="⏸", width=28, height=24, fg_color="#ffc107", hover_color="#e0a800", text_color="black", command=lambda: self._acao_rapida(nome, "pause"))
        btn_pause.pack(side="left", padx=2)
        btn_restart = ctk.CTkButton(ctrl_group, text="🔄", width=28, height=24, fg_color="#6c757d", hover_color="#5a6268", command=lambda: self._acao_rapida(nome, "restart"))
        btn_restart.pack(side="left", padx=2)

        # 7. Ações (Edit, Delete)
        frm_act = ctk.CTkFrame(row, fg_color="transparent")
        frm_act.place(relx=0.90, relwidth=0.10, rely=0, relheight=1)
        
        act_group = ctk.CTkFrame(frm_act, fg_color="transparent")
        act_group.pack(expand=True)

        btn_edit = ctk.CTkButton(act_group, text="", image=self.icon_manager._icons.get("edit_light"), width=30, height=26, fg_color="#0056b3", hover_color="#004494", command=lambda: self.editar_servico(nome))
        btn_edit.pack(side="left", padx=(0, 5))
        btn_del = ctk.CTkButton(act_group, text="✕", width=26, height=26, fg_color="#dc3545", hover_color="#c82333", command=lambda: self.remover_servico(nome))
        btn_del.pack(side="left", padx=0)

        self.linhas_visuais[nome] = {
            "row": row, "lbl_pid": lbl_pid, "lbl_desc": lbl_desc, "lbl_status": lbl_status, 
            "btn_play": btn_play, "btn_stop": btn_stop, "btn_pause": btn_pause, "btn_restart": btn_restart,
            "btn_edit": btn_edit, "btn_del": btn_del, "bg_padrao": bg_color
        }   

    def popular_tabela(self):
        for w in self.linhas_visuais.values(): w["row"].destroy()
        self.linhas_visuais.clear()
        
        for nome, dados in self.master_tab.config_data.servicos.items():
            self.criar_linha(nome, dados)

    def _acao_rapida(self, nome, acao):
        """Envia comandos ao WindowsAdapter em Background"""
        widgets = self.linhas_visuais.get(nome)
        if widgets:
            if acao == "start": widgets["lbl_status"].configure(text="Iniciando...", text_color="#17a2b8")
            elif acao == "stop": widgets["lbl_status"].configure(text="Parando...", text_color="#17a2b8")
            elif acao == "restart": widgets["lbl_status"].configure(text="Reiniciando...", text_color="#17a2b8")
        
        def task():
            if acao == "start": ServiceAdapter.start_service(nome)
            elif acao == "stop": ServiceAdapter.stop_service(nome)
            elif acao == "pause": ServiceAdapter.pause_service(nome)
            elif acao == "continue": ServiceAdapter.continue_service(nome) # (Pode ser mapeado futuramente)
            elif acao == "restart":
                ServiceAdapter.stop_service(nome)
                time.sleep(2)
                ServiceAdapter.start_service(nome)
            self.master_tab.log(f"Comando '{acao}' enviado para o serviço: {nome}")
            
        threading.Thread(target=task, daemon=True).start()

    def editar_servico(self, nome):
        if self.master_tab.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para editar propriedades.")
            return
        # A janela de propriedades que faremos no Passo 2!
        ServicePropertiesWindow(self.master_tab, self, nome)

    def remover_servico(self, nome):
        if self.master_tab.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para remover itens.")
            return
        if messagebox.askyesno("Remover", f"Deseja remover o serviço '{nome}' do monitoramento?"):
            if nome in self.master_tab.config_data.servicos:
                del self.master_tab.config_data.servicos[nome]
                PersistenceRepository.salvar(self.master_tab.config_data)
                
            self.linhas_visuais[nome]["row"].destroy()
            del self.linhas_visuais[nome]
            self.recalcular_cores_linhas()

    def recalcular_cores_linhas(self):
        index_visivel = 0
        for nome, widget_data in self.linhas_visuais.items():
            if widget_data["row"].winfo_ismapped():
                bg_color = AppColors.BRIGHT_SNOW if index_visivel % 2 == 0 else AppColors.WHITE
                widget_data["row"].configure(fg_color=bg_color)
                widget_data["bg_padrao"] = bg_color
                index_visivel += 1

    def filtrar_tabela(self, event=None):
        query = self.entry_busca.get().lower()
        for widget_data in self.linhas_visuais.values():
            if widget_data["row"].winfo_ismapped(): widget_data["row"].pack_forget()
                
        index_visivel = 0
        for nome, widget_data in self.linhas_visuais.items():
            if query in nome.lower():
                widget_data["row"].pack(fill="x", pady=(0, 1))
                bg_color = AppColors.BRIGHT_SNOW if index_visivel % 2 == 0 else AppColors.WHITE
                widget_data["row"].configure(fg_color=bg_color)
                index_visivel += 1

    def definir_estado_edicao(self, estado):
        self.btn_add.configure(state=estado)
        for widget_data in self.linhas_visuais.values():
            widget_data["btn_del"].configure(state=estado)
            widget_data["btn_edit"].configure(state=estado)

    def abrir_modal_adicionar(self):
        if self.master_tab.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para adicionar itens.")
            return
        AdicionarServicoModal(self.master_tab, self)

    def loop_atualizacao_tabela(self):
        """Atualiza a UI da tabela em tempo real com dados lidos do Windows"""
        status_trad = {"running": "Em Execução", "stopped": "Parado", "start_pending": "Iniciando", 
                       "stop_pending": "Parando", "paused": "Pausado", "pause_pending": "Pausando"}

        while self.running:
            # Só atualiza visualmente se o motor não estiver a rodar (quando o motor roda, ele gere as leituras)
            # Mas para garantir que a UI mostra o estado mesmo com o motor parado, lemos a cada 2 segundos.
            for name in list(self.linhas_visuais.keys()):
                widgets = self.linhas_visuais.get(name)
                if not widgets: continue
                
                info = ServiceAdapter.get_service_info(name)
                status_raw = info["status"]
                
                status_pt = status_trad.get(status_raw, status_raw.upper())
                
                if "pending" in status_raw: color = "#17a2b8"
                elif status_raw == "running": color = "#28a745"
                elif status_raw == "stopped": color = "#dc3545"
                elif status_raw == "paused": color = "#ffc107"
                else: color = "gray"

                try:
                    widgets["lbl_status"].configure(text=status_pt, text_color=color)
                    widgets["lbl_pid"].configure(text=info["pid"])
                    
                    desc = info["desc"]
                    desc_curta = desc if len(desc) < 35 else desc[:32] + "..."
                    widgets["lbl_desc"].configure(text=desc_curta)
                except Exception:
                    pass

            time.sleep(2.5)

    def destroy(self):
        self.running = False
        super().destroy()