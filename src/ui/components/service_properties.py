# src/ui/components/service_properties.py
import os
import time
import psutil
import subprocess
import threading
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ...infrastructure.icon_manager import IconeManager
from ..colors import AppColors
from ...infrastructure.persistence import PersistenceRepository
from ...infrastructure.service_adapter import ServiceAdapter

class ServicePropertiesWindow(ctk.CTkToplevel):
    def __init__(self, master_tab, servicos_view, service_name, live_states=None):
        super().__init__(master_tab)
        
        self.configure(fg_color=AppColors.BRIGHT_SNOW)
        self.icon_manager = IconeManager()
        self.master_tab = master_tab
        self.servicos_view = servicos_view
        self.service_name = service_name
        self.live_states = live_states if live_states else {}
        
        self.title(f"Propriedades Avançadas: {service_name}")
        self.geometry("580x680")
        self.grab_set() 
        self.transient(master_tab) 

        # Dados Atuais do SO
        self.info_so = self._fetch_deep_service_data()
        
        # Configurações do WatchdogApp
        if self.service_name not in self.master_tab.config_data.servicos:
            self.master_tab.config_data.servicos[self.service_name] = {}
        self.cfg = self.master_tab.config_data.servicos[self.service_name]
        self._inicializar_chaves_padrao()
        
        self._build_top_tabs()
        self._build_content_area()
        self._build_footer()

    def _fetch_deep_service_data(self):
        """Busca dados profundos usando ServiceAdapter e PsUtil"""
        data = {"name": self.service_name, "display_name": "N/D", "desc": "N/D", "binpath": "N/D", "start_type": "manual", "status": "stopped"}
        
        try:
            adapter_info = ServiceAdapter.get_service_info(self.service_name)
            data.update(adapter_info)
        except Exception: pass

        try:
            svc = psutil.win_service_get(self.service_name)
            data["status"] = svc.status()
            try: data["display_name"] = svc.display_name()
            except: pass
            try: data["desc"] = svc.description() or "Nenhuma descrição disponível."
            except: pass
            try: data["binpath"] = svc.binpath()
            except: pass
            try: data["start_type"] = svc.start_type()
            except: pass
        except Exception: pass
        
        return data

    def _inicializar_chaves_padrao(self):
        """Garante que todas as chaves do WatchdogApp existam no dicionário"""
        defaults = {
            "state_actions": {"running": "Não Fazer Nada", "stopped": "Reiniciar", "paused": "Não Fazer Nada"},
            "pending_timeouts": {"enabled": False, "start": 60, "stop_others": 30},
            "emergency": {"enabled": False, "max_retries": 3, "reset_days": 0, "run_script": ""},
            "perf_limits": {"cpu": 0.0, "ram": 0.0, "disk": 0.0, "tolerance": 30, "max_restarts": 3, "reset_days": 0},
            "heartbeat": {"enabled": False, "timeout": 5, "max_restarts": 3, "reset_days": 0},
            "custom_deps": {"services": "", "behavior": "Não Fazer Nada"},
            "schedule": {"enabled": False, "days": "Todos os Dias", "time": "03:00"},
        }
        for k, v in defaults.items():
            if k not in self.cfg: self.cfg[k] = v

    def _show_help_dialog(self, title, message):
        """Um overlay de ajuda customizado, silencioso, arredondado e com o design da aplicação"""
        dlg = ctk.CTkToplevel(self, fg_color=AppColors.BRIGHT_SNOW)
        dlg.withdraw() 
        dlg.transient(self) 
        dlg.grab_set() 

        dlg.overrideredirect(True) 
        
        main_frm = ctk.CTkFrame(dlg, fg_color=AppColors.WHITE, corner_radius=15, border_width=1, border_color=AppColors.PLATINUM)
        main_frm.pack(fill="both", expand=True)

        self.update_idletasks() 
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()

        width = 420
        height = 200
        center_x = parent_x + (parent_width // 2) - (width // 2)
        center_y = parent_y + (parent_height // 2) - (height // 2)

        dlg.geometry(f"{width}x{height}+{center_x}+{center_y}")
        dlg.deiconify() 

        # Cabeçalho
        header_frm = ctk.CTkFrame(main_frm, fg_color="transparent")
        header_frm.pack(fill="x", padx=15, pady=(15, 10))
        
        title_lbl = ctk.CTkLabel(header_frm, text=f"{title}", font=("Arial", 14, "bold"), text_color=AppColors.CHARCOAL_BLUE)
        title_lbl.pack(side="left")
        
        close_btn = ctk.CTkButton(
            header_frm, text="✕", width=28, height=28, corner_radius=4, 
            fg_color="transparent", hover_color="#e0e0e0", text_color="gray", 
            font=("Arial", 12, "bold"), command=dlg.destroy
        )
        close_btn.pack(side="right")

        ctk.CTkFrame(main_frm, height=1, fg_color=AppColors.PLATINUM).pack(fill="x", padx=15, pady=0)

        # Corpo
        body_lbl = ctk.CTkLabel(
            main_frm, text=message, font=("Arial", 12), text_color=AppColors.NIGHT, 
            wraplength=380, justify="left", anchor="nw"
        )
        body_lbl.pack(fill="both", expand=True, padx=20, pady=(15, 10))

        # Rodapé
        footer_frm = ctk.CTkFrame(main_frm, fg_color="transparent")
        footer_frm.pack(fill="x", padx=15, pady=(0, 15), side="bottom")

        ctk.CTkButton(
            footer_frm,  
            text="Entendi",
            text_color=AppColors.WHITE,
            fg_color=AppColors.DUSK_BLUE,
            corner_radius=4,
            height=28,
            width=110,
            command=dlg.destroy
        ).pack(side="right")

    def _create_section(self, parent, title, help_msg=None):
        hdr_frm = ctk.CTkFrame(parent, fg_color="transparent")
        hdr_frm.pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(hdr_frm, text=title, font=("Arial", 13, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(side="left")
        if help_msg:
            btn_help = ctk.CTkButton(hdr_frm, text="?", width=20, height=20, corner_radius=10, fg_color=AppColors.DUSK_BLUE, hover_color=AppColors.CHARCOAL_BLUE, command=lambda: self._show_help_dialog(title, help_msg))
            btn_help.pack(side="left", padx=10)

        frm = ctk.CTkFrame(parent, fg_color=AppColors.WHITE, corner_radius=5, border_width=1, border_color=AppColors.PLATINUM)
        frm.pack(fill="x", pady=2)
        return frm

    # ==========================================
    # SISTEMA DE NAVEGAÇÃO DE ABAS
    # ==========================================
    def _build_top_tabs(self):
        self.tabs_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.tabs_frame.pack(fill="x", padx=15, pady=(10, 0))

        abas = [
            ("Geral", self.show_geral), ("Recuperação", self.show_recuperacao),
            ("Dependências", self.show_deps), ("Agendamento", self.show_agendamento),
            ("Logs", self.show_logs)
        ]
        
        self.btn_abas = {}
        for txt, cmd in abas:
            btn = ctk.CTkButton(self.tabs_frame, text=txt, fg_color="transparent", text_color=AppColors.CHARCOAL_BLUE, hover_color=AppColors.PLATINUM, font=("Arial", 12, "bold"), height=30, width=100, corner_radius=0, command=cmd)
            btn.pack(side="left", fill="x", expand=True)
            self.btn_abas[txt] = btn

        ctk.CTkFrame(self, fg_color=AppColors.PLATINUM, height=2).pack(fill="x", padx=15)

    def _build_content_area(self):
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=15, pady=(10, 0))
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.frames = {
            "Geral": ctk.CTkScrollableFrame(self.content_container, fg_color="transparent"),
            "Recuperação": ctk.CTkScrollableFrame(self.content_container, fg_color="transparent"),
            "Dependências": ctk.CTkScrollableFrame(self.content_container, fg_color="transparent"),
            "Agendamento": ctk.CTkScrollableFrame(self.content_container, fg_color="transparent"),
            "Logs": ctk.CTkFrame(self.content_container, fg_color="transparent")
        }

        self._build_geral_tab()
        self._build_recuperacao_tab()
        self._build_deps_tab()
        self._build_agendamento_tab()
        self._build_logs_tab()

        self.show_geral()

    def _switch_tab(self, tab_name):
        for nome, btn in self.btn_abas.items():
            btn.configure(fg_color="transparent", text_color=AppColors.CHARCOAL_BLUE)
        self.btn_abas[tab_name].configure(fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE)
        
        for frame in self.frames.values(): frame.grid_forget()
        self.frames[tab_name].grid(row=0, column=0, sticky="nsew")

    def show_geral(self): self._switch_tab("Geral")
    def show_recuperacao(self): self._switch_tab("Recuperação")
    def show_deps(self): self._switch_tab("Dependências")
    def show_agendamento(self): self._switch_tab("Agendamento")
    def show_logs(self): self._switch_tab("Logs")

    # ==========================================
    # 1. ABA GERAL
    # ==========================================
    def _build_geral_tab(self):
        frm = self.frames["Geral"]
        
        sec_info = self._create_section(frm, "Informações do Serviço")
        
        grid_frm = ctk.CTkFrame(sec_info, fg_color="transparent")
        grid_frm.pack(fill="x", padx=10, pady=5)
        grid_frm.grid_columnconfigure(0, weight=0, minsize=200)
        grid_frm.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(grid_frm, text="Nome do Serviço:", font=("Arial", 12, "bold"), anchor="w").grid(row=0, column=0, sticky="w", pady=5)
        ctk.CTkLabel(grid_frm, text=self.info_so["name"], font=("Arial", 12)).grid(row=0, column=1, sticky="w", pady=5)

        # Nome de Exibição como Container
        ctk.CTkLabel(grid_frm, text="Nome de Exibição:", font=("Arial", 12, "bold"), anchor="w").grid(row=1, column=0, sticky="w", pady=5)
        disp_box = ctk.CTkEntry(grid_frm, fg_color="transparent", text_color="gray", width=250)
        disp_box.grid(row=1, column=1, sticky="ew", pady=5)
        disp_box.insert(0, self.info_so["display_name"])
        disp_box.configure(state="readonly")

        # Descrição como Container
        ctk.CTkLabel(grid_frm, text="Descrição:", font=("Arial", 12, "bold"), anchor="nw").grid(row=2, column=0, sticky="nw", pady=5)
        desc_box = ctk.CTkTextbox(grid_frm, height=60, fg_color=AppColors.WHITE, border_width=1, border_color=AppColors.PLATINUM, text_color=AppColors.NIGHT)
        desc_box.grid(row=2, column=1, sticky="ew", pady=5)
        desc_box.insert("0.0", self.info_so["desc"])
        desc_box.configure(state="disabled")

        ctk.CTkLabel(grid_frm, text="Caminho do Executável:", font=("Arial", 12, "bold")).grid(row=3, column=0, sticky="nw", pady=5)
        path_box = ctk.CTkTextbox(grid_frm, height=50, fg_color="transparent", text_color=AppColors.NIGHT)
        path_box.grid(row=3, column=1, sticky="ew", pady=5)
        path_box.insert("0.0", self.info_so["binpath"])
        path_box.configure(state="disabled")

        ctk.CTkLabel(grid_frm, text="Inicialização (Windows):", font=("Arial", 12, "bold"), anchor="w").grid(row=4, column=0, sticky="w", pady=5)
        st_raw = self.info_so["start_type"].lower()
        st_val = "Automático" if st_raw == "automatic" else "Desativado" if st_raw == "disabled" else "Manual"
        self.startup_var = ctk.StringVar(value=st_val)
        ctk.CTkOptionMenu(grid_frm, values=["Automático", "Automático (Atraso na inicialização)", "Manual", "Desativado"], variable=self.startup_var, width=250, fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT, button_color=AppColors.PLATINUM,).grid(row=4, column=1, sticky="w", pady=5)

        status_pt = {"running": "Em Execução", "stopped": "Parado"}.get(self.info_so["status"], self.info_so["status"])
        ctk.CTkLabel(grid_frm, text="Status do Serviço:", font=("Arial", 12, "bold"), anchor="w").grid(row=5, column=0, sticky="w", pady=5)
        self.lbl_status_geral = ctk.CTkLabel(grid_frm, text=status_pt.upper(), font=("Arial", 12, "bold"), text_color=AppColors.DUSK_BLUE)
        self.lbl_status_geral.grid(row=5, column=1, sticky="w", pady=5)

        # Controladores Manuais
        sec_ctrl = self._create_section(frm, "Controladores Manuais")
        ctrl_frame = ctk.CTkFrame(sec_ctrl, fg_color="transparent")
        ctrl_frame.pack(pady=15)
        
        is_run = self.info_so["status"] == "running"
        self.btn_start = ctk.CTkButton(ctrl_frame, text="Iniciar", image=self.icon_manager._icons.get("play"), text_color=AppColors.WHITE, fg_color="#28a745", hover_color="#218838", width=100, state="disabled" if is_run else "normal", command=lambda: self._cmd("start"))
        self.btn_start.pack(side="left", padx=5)
        self.btn_stop = ctk.CTkButton(ctrl_frame, text="Parar", image=self.icon_manager._icons.get("stop"), text_color=AppColors.WHITE, fg_color="#dc3545", hover_color="#c82333", width=100, state="normal" if is_run else "disabled", command=lambda: self._cmd("stop"))
        self.btn_stop.pack(side="left", padx=5)
        self.btn_pause = ctk.CTkButton(ctrl_frame, text="Pausar", image=self.icon_manager._icons.get("pause"), text_color=AppColors.WHITE, fg_color="#ffc107", hover_color="#e0a800", width=100, state="normal" if is_run else "disabled", command=lambda: self._cmd("pause"))
        self.btn_pause.pack(side="left", padx=5)
        self.btn_resume = ctk.CTkButton(ctrl_frame, text="Continuar", image=self.icon_manager._icons.get("continue"), text_color=AppColors.WHITE, fg_color="#17a2b8", hover_color="#138496", width=100, state="disabled", command=lambda: self._cmd("continue"))
        self.btn_resume.pack(side="left", padx=5)

        # Ações do WatchdogApp (Reset)
        sec_act = self._create_section(frm, "Gestão de Configurações")
        act_frame = ctk.CTkFrame(sec_act, fg_color="transparent")
        act_frame.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkButton(act_frame, text="Zerar Contadores", image=self.icon_manager._icons.get("refresh"), text_color=AppColors.CHARCOAL_BLUE, fg_color=AppColors.WHITE, hover_color=AppColors.PLATINUM, border_width=2, border_color=AppColors.CHARCOAL_BLUE, command=self._reset_counters).pack(side="left", padx=(0, 10))
        ctk.CTkButton(act_frame, text="Resetar Configurações para Padrão", image=self.icon_manager._icons.get("reset_settings"), text_color=AppColors.WHITE, fg_color=AppColors.FLAG_RED, hover_color="#c82333", command=self._reset_configs).pack(side="left")

    def _cmd(self, action):
        def task():
            if action == "start": ServiceAdapter.start_service(self.service_name)
            elif action == "stop": ServiceAdapter.stop_service(self.service_name)
            elif action == "pause": subprocess.run(f"sc pause {self.service_name}", shell=True, capture_output=True)
            elif action == "continue": subprocess.run(f"sc continue {self.service_name}", shell=True, capture_output=True)
            time.sleep(1.5)
            
            try:
                new_status = psutil.win_service_get(self.service_name).status()
                is_run = new_status == "running"
                self.lbl_status_geral.configure(text={"running": "EM EXECUÇÃO", "stopped": "PARADO"}.get(new_status, new_status.upper()))
                self.btn_start.configure(state="disabled" if is_run else "normal")
                self.btn_stop.configure(state="normal" if is_run else "disabled")
                self.btn_pause.configure(state="normal" if is_run else "disabled")
                self.btn_resume.configure(state="disabled") 
            except Exception: pass
        threading.Thread(target=task, daemon=True).start()


    def _reset_counters(self):
        if self.service_name in self.live_states:
            st = self.live_states[self.service_name]
            st["retry_count"] = 0
            st["perf_retry_count"] = 0
            st["hb_retry_count"] = 0
            st["script_executed"] = False
        messagebox.showinfo("Contadores Zerados", "Os contadores de falhas foram resetados para zero com sucesso!", parent=self)
        self.destroy()

    def _reset_configs(self):
        resposta = messagebox.askyesno("Atenção", f"Tem certeza que deseja apagar TODAS as configurações e automações de '{self.service_name}'?", parent=self)
        if resposta:
            if self.service_name in self.master_tab.config_data.servicos:
                del self.master_tab.config_data.servicos[self.service_name]
                PersistenceRepository.salvar(self.master_tab.config_data)
            messagebox.showinfo("Sucesso", "Configurações restauradas para o padrão.", parent=self)
            self.destroy()

    # ==========================================
    # 2. ABA RECUPERAÇÃO
    # ==========================================
    def _build_recuperacao_tab(self):
        frm = self.frames["Recuperação"]
        
        my_live_state = self.live_states.get(self.service_name, {})
        curr_state_fails = my_live_state.get("retry_count", 0)
        curr_perf_fails = my_live_state.get("perf_retry_count", 0)
        curr_hb_fails = my_live_state.get("hb_retry_count", 0)

        # 1. Matriz de Estados
        acts = self.cfg.get("state_actions", {})
        msg_matriz = "Define a ação automática perante o status do serviço.\nPara bloquear um serviço (Blacklist), defina 'Em Execução' como 'Parar' e 'Parado' como 'Não Fazer Nada'."
        sec_matriz = self._create_section(frm, "Matriz de Estados (Ação por Status)", msg_matriz)
        
        # Cabeçalho da Matriz
        hdr_row = ctk.CTkFrame(sec_matriz, fg_color="transparent")
        hdr_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(hdr_row, text="Status do Serviço", font=("Arial", 11, "bold"), text_color=AppColors.NIGHT, width=180, anchor="w").pack(side="left")
        ctk.CTkLabel(hdr_row, text="Ação a ser Tomada", font=("Arial", 11, "bold"), text_color=AppColors.NIGHT).pack(side="left")

        status_possiveis = [("stopped", "Parado"), ("paused", "Pausado"), ("running", "Em Execução")]
        opcoes_seguras = {
            "stopped": ["Não Fazer Nada", "Iniciar", "Reiniciar", "Somente Alertar/Notificar"],
            "paused": ["Não Fazer Nada", "Continuar", "Parar", "Reiniciar", "Somente Alertar/Notificar"],
            "running": ["Não Fazer Nada", "Parar", "Somente Alertar/Notificar"]
        }

        self.cb_states = {}
        for s_eng, s_pt in status_possiveis:
            row = ctk.CTkFrame(sec_matriz, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=5)
            ctk.CTkLabel(row, text=f"Se estiver {s_pt}:", width=180, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
            
            cb = ctk.CTkOptionMenu(row, values=opcoes_seguras[s_eng], fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT, button_color=AppColors.PLATINUM)
            valor_salvo = acts.get(s_eng)
            if valor_salvo in opcoes_seguras[s_eng]: cb.set(valor_salvo)
            elif s_eng == "stopped": cb.set("Reiniciar")
            else: cb.set("Não Fazer Nada")
            
            cb.pack(side="left", fill="x", expand=True)
            self.cb_states[s_eng] = cb

        # 2. Timeouts de Transição
        msg_trans = "Se o tempo definido aqui esgotar (status Iniciando/Parando travado), o WatchdogApp fará um Kill Forçado no processo."
        sec_pend = self._create_section(frm, "Tratamento de Transições (Deadlocks)", msg_trans)
        pend = self.cfg.get("pending_timeouts", {})
        
        row_pend_en = ctk.CTkFrame(sec_pend, fg_color="transparent")
        row_pend_en.pack(fill="x", padx=15, pady=(10, 5))
        self.chk_pend_var = ctk.BooleanVar(value=pend.get("enabled", False))
        ctk.CTkCheckBox(row_pend_en, text="Habilitar Verificação de Tempo de Transição", variable=self.chk_pend_var, text_color=AppColors.NIGHT, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE).pack(side="left")

        self.ent_pend_start = self._criar_campo_texto(sec_pend, "Tempo limite aguardando 'Iniciando' (Segundos):", pend.get("start", 60))
        self.ent_pend_stop = self._criar_campo_texto(sec_pend, "Tempo limite aguardando 'Parando/Outros' (Segundos):", pend.get("stop_others", 30))

        # 3. Emergência
        msg_emerg = "Se as ações falharem repetidamente, declara 'Falha Crítica' e impede loops."
        sec_emg = self._create_section(frm, "Ações de Emergência", msg_emerg)
        emg = self.cfg.get("emergency", {})

        row_em_en = ctk.CTkFrame(sec_emg, fg_color="transparent")
        row_em_en.pack(fill="x", padx=15, pady=(10, 5))
        self.chk_em_var = ctk.BooleanVar(value=emg.get("enabled", False))
        ctk.CTkCheckBox(row_em_en, text="Habilitar Ações de Emergência", variable=self.chk_em_var, text_color=AppColors.NIGHT, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE).pack(side="left")
        
        row_retry = ctk.CTkFrame(sec_emg, fg_color="transparent")
        row_retry.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_retry, text="Parar de tentar após X falhas da Matriz:", width=220, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        self.ent_retries = ctk.CTkEntry(row_retry, width=80, fg_color=AppColors.WHITE, text_color=AppColors.NIGHT)
        self.ent_retries.insert(0, str(emg.get("max_retries", 3)))
        self.ent_retries.pack(side="left")
        ctk.CTkLabel(row_retry, text=f"(Falhas atuais: {curr_state_fails})", text_color=AppColors.FLAG_RED if curr_state_fails > 0 else "gray", font=("Arial", 11, "italic")).pack(side="left", padx=5)
        
        self.ent_em_reset = self._criar_campo_texto(sec_emg, "Resetar falhas após X dias (0 = Nunca):", emg.get("reset_days", 0))
        
        row_emg = ctk.CTkFrame(sec_emg, fg_color="transparent")
        row_emg.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(row_emg, text="Executar Programa em caso de Falha Crítica:", width=260, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        self.ent_script = ctk.CTkEntry(row_emg, placeholder_text="Ex: C:\\Scripts\\alerta.bat", fg_color=AppColors.WHITE, text_color=AppColors.NIGHT)
        self.ent_script.insert(0, emg.get("run_script", ""))
        self.ent_script.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(row_emg, text="Procurar...", width=100, image=self.icon_manager._icons.get("folder"),
                      fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE, command=self._procurar_script).pack(side="right")

        # 4. Limites de Desempenho
        msg_perf = "Monitoriza vazamentos de memória ou picos de CPU. Defina 0 para desativar."
        sec_perf = self._create_section(frm, "Limites de Desempenho (0 = Desativado)", msg_perf)
        perf = self.cfg.get("perf_limits", {})
        
        self.ent_cpu = self._criar_campo_texto(sec_perf, "Reiniciar se CPU exceder (%):", perf.get("cpu", 0))
        self.ent_ram = self._criar_campo_texto(sec_perf, "Reiniciar se RAM exceder (MB):", perf.get("ram", 0))
        self.ent_disk = self._criar_campo_texto(sec_perf, "Reiniciar se Disco exceder (MB/s):", perf.get("disk", 0))
        self.ent_tol = self._criar_campo_texto(sec_perf, "Tolerância (Segundos):", perf.get("tolerance", 30))
        
        row_perf_max = ctk.CTkFrame(sec_perf, fg_color="transparent")
        row_perf_max.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_perf_max, text="Parar de tentar após X reinícios:", width=220, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        self.ent_perf_max = ctk.CTkEntry(row_perf_max, width=80, fg_color=AppColors.WHITE, text_color=AppColors.NIGHT)
        self.ent_perf_max.insert(0, str(perf.get("max_restarts", 3)))
        self.ent_perf_max.pack(side="left")
        ctk.CTkLabel(row_perf_max, text=f"(Reinícios atuais: {curr_perf_fails})", text_color=AppColors.FLAG_RED if curr_perf_fails > 0 else "gray", font=("Arial", 11, "italic")).pack(side="left", padx=5)

        self.ent_perf_reset = self._criar_campo_texto(sec_perf, "Resetar após X dias (0 = Nunca):", perf.get("reset_days", 0))

        # 5. Heartbeat / Inatividade
        msg_hb = "Detecta Deadlocks onde o status é 'Em Execução' mas a CPU fica a 0%."
        sec_hb = self._create_section(frm, "Verificação de Inatividade (Heartbeat)", msg_hb)
        hb = self.cfg.get("heartbeat", {})
        
        row_hb_en = ctk.CTkFrame(sec_hb, fg_color="transparent")
        row_hb_en.pack(fill="x", padx=15, pady=(10, 5))
        self.chk_hb_var = ctk.BooleanVar(value=hb.get("enabled", False))
        ctk.CTkCheckBox(row_hb_en, text="Ativar reinicialização por inatividade (CPU 0%)", variable=self.chk_hb_var, text_color=AppColors.NIGHT, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE).pack(side="left")
        
        self.ent_hb_time = self._criar_campo_texto(sec_hb, "Timeout de Inatividade (Minutos):", hb.get("timeout", 5))
        
        row_hb_max = ctk.CTkFrame(sec_hb, fg_color="transparent")
        row_hb_max.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_hb_max, text="Parar de tentar após X reinícios:", width=220, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        self.ent_hb_max = ctk.CTkEntry(row_hb_max, width=80, fg_color=AppColors.WHITE, text_color=AppColors.NIGHT)
        self.ent_hb_max.insert(0, str(hb.get("max_restarts", 3)))
        self.ent_hb_max.pack(side="left")
        ctk.CTkLabel(row_hb_max, text=f"(Reinícios atuais: {curr_hb_fails})", text_color=AppColors.FLAG_RED if curr_hb_fails > 0 else "gray", font=("Arial", 11, "italic")).pack(side="left", padx=5)

        self.ent_hb_reset = self._criar_campo_texto(sec_hb, "Resetar após X dias (0 = Nunca):", hb.get("reset_days", 0))

    def _criar_campo_texto(self, parent, label, valor):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row, text=label, width=220, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        ent = ctk.CTkEntry(row, width=80, fg_color=AppColors.WHITE, text_color=AppColors.NIGHT)
        ent.insert(0, str(valor))
        ent.pack(side="left")
        return ent

    def _procurar_script(self):
        path = filedialog.askopenfilename(title="Selecione o Script", filetypes=[("Scripts", "*.bat *.ps1 *.cmd *.py *.exe")])
        if path:
            self.ent_script.delete(0, 'end')
            self.ent_script.insert(0, path)

    # ==========================================
    # 3. ABA DEPENDÊNCIAS
    # ==========================================
    def _build_deps_tab(self):
        frm = self.frames["Dependências"]
        
        # Nativas do Sistema
        sec_nat = self._create_section(frm, "Dependências do Sistema (Nativas)")
        deps_frame = ctk.CTkFrame(sec_nat, fg_color="transparent")
        deps_frame.pack(fill="x", padx=15, pady=10)
        
        dependencies = self._get_fast_dependencies()
        if not dependencies: ctk.CTkLabel(deps_frame, text="< Nenhuma dependência nativa encontrada >", text_color="gray").pack(anchor="w")
        else:
            for dep in dependencies: ctk.CTkLabel(deps_frame, text=f"⚙️ {dep}", text_color=AppColors.NIGHT).pack(anchor="w", pady=2)

        # Customizadas (Órfãos)
        msg_orf = "Crie grupos de dependência. Se este serviço precisa que outro esteja rodando, defina o comportamento aqui."
        sec_cust = self._create_section(frm, "Dependências Customizadas (Serviços Órfãos)", msg_orf)
        deps = self.cfg.get("custom_deps", {})
        
        row_nome = ctk.CTkFrame(sec_cust, fg_color="transparent")
        row_nome.pack(fill="x", padx=15, pady=(15, 5))
        ctk.CTkLabel(row_nome, text="Serviço que DEVE estar rodando (Nome Exato):", width=260, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        self.ent_deps = ctk.CTkEntry(row_nome, placeholder_text="Ex: MySQL", fg_color=AppColors.WHITE, text_color=AppColors.NIGHT)
        self.ent_deps.insert(0, deps.get("services", ""))
        self.ent_deps.pack(side="left", fill="x", expand=True)

        row_beh = ctk.CTkFrame(sec_cust, fg_color="transparent")
        row_beh.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_beh, text="Comportamento do WatchdogApp:", width=260, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        
        opcoes_comp = ["Não Fazer Nada", "Ordem de Inicialização", "Efeito Dominó (Queda)"]
        self.cb_dep_behavior = ctk.CTkOptionMenu(row_beh, values=opcoes_comp, command=self._update_dep_desc, fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT, button_color=AppColors.PLATINUM)
        self.cb_dep_behavior.set(deps.get("behavior", "Não Fazer Nada"))
        self.cb_dep_behavior.pack(side="left", fill="x", expand=True)

        self.lbl_dep_desc = ctk.CTkLabel(sec_cust, text="", text_color=AppColors.DUSK_BLUE, justify="left", wraplength=450)
        self.lbl_dep_desc.pack(padx=15, pady=(5, 15), anchor="w")
        self._update_dep_desc(self.cb_dep_behavior.get())

    def _get_fast_dependencies(self):
        deps = []
        try:
            result = subprocess.run(f'sc qc "{self.service_name}"', shell=True, capture_output=True, text=True, creationflags=0x08000000)
            if result.returncode == 0:
                is_parsing = False
                for line in result.stdout.split('\n'):
                    if "DEPEND" in line.upper():
                        is_parsing = True
                        parts = line.split(":", 1)
                        if len(parts) > 1 and parts[1].strip(): deps.append(parts[1].strip())
                    elif is_parsing:
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            if not parts[0].strip() and parts[1].strip(): deps.append(parts[1].strip())
                            else: is_parsing = False
        except Exception: pass
        return deps

    def _update_dep_desc(self, choice):
        if choice == "Não Fazer Nada": txt = "O sistema apenas registra a dependência, mas não toma nenhuma ação."
        elif choice == "Ordem de Inicialização": txt = "Antes de iniciar este serviço, o WatchdogApp ligará o serviço acima caso ele esteja parado."
        else: txt = "Efeito Dominó: Se o serviço acima cair, este serviço será PARADO IMEDIATAMENTE para evitar erros, e religado quando o outro voltar."
        self.lbl_dep_desc.configure(text=txt)

    # ==========================================
    # 4. ABA AGENDAMENTO
    # ==========================================
    def _build_agendamento_tab(self):
        frm = self.frames["Agendamento"]
        sched = self.cfg.get("schedule", {})

        msg_sched = "Evita vazamentos de memória agendando um reinício preventivo em horários de baixo impacto."
        sec_sched = self._create_section(frm, "Smart Schedule (Reinicialização Preventiva)", msg_sched)
        
        row_en = ctk.CTkFrame(sec_sched, fg_color="transparent")
        row_en.pack(fill="x", padx=15, pady=(15, 5))
        self.chk_sched_var = ctk.BooleanVar(value=sched.get("enabled", False))
        ctk.CTkCheckBox(row_en, text="Ativar Reinício Preventivo", variable=self.chk_sched_var, fg_color=AppColors.DUSK_BLUE, text_color=AppColors.NIGHT, border_color=AppColors.CHARCOAL_BLUE).pack(side="left")

        row_days = ctk.CTkFrame(sec_sched, fg_color="transparent")
        row_days.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row_days, text="Dia da Semana:", width=150, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        dias = ["Todos os Dias", "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        self.cb_days = ctk.CTkOptionMenu(row_days, values=dias, fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT, button_color=AppColors.PLATINUM)
        self.cb_days.set(sched.get("days", "Todos os Dias"))
        self.cb_days.pack(side="left", fill="x", expand=True)

        row_time = ctk.CTkFrame(sec_sched, fg_color="transparent")
        row_time.pack(fill="x", padx=15, pady=(5, 15))
        ctk.CTkLabel(row_time, text="Horário (HH:MM):", width=150, anchor="w", text_color=AppColors.NIGHT).pack(side="left")
        self.ent_time = ctk.CTkEntry(row_time, width=100, placeholder_text="03:00", fg_color=AppColors.WHITE, text_color=AppColors.NIGHT)
        self.ent_time.insert(0, sched.get("time", "03:00"))
        self.ent_time.pack(side="left")

    # ==========================================
    # 5. ABA LOGS
    # ==========================================
    def _build_logs_tab(self):
        frm = self.frames["Logs"]
        
        hdr = ctk.CTkFrame(frm, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(hdr, text="Extrair erros do Visualizador de Eventos", font=("Arial", 13, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(side="left")
        ctk.CTkButton(hdr, text="🔎 Extrair Últimas 24h", fg_color=AppColors.DUSK_BLUE, command=self._extract_logs).pack(side="right")

        self.txt_logs = ctk.CTkTextbox(frm, fg_color=AppColors.WHITE, border_width=1, border_color=AppColors.PLATINUM, text_color=AppColors.NIGHT, font=("Consolas", 11))
        self.txt_logs.pack(fill="both", expand=True)
        self.txt_logs.insert("end", "O Snapshot de logs busca falhas silenciosas do Windows...\nClique no botão acima para iniciar a busca.")
        self.txt_logs.configure(state="disabled")

    def _extract_logs(self):
        self.txt_logs.configure(state="normal")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.insert("end", "A executar PowerShell para extrair eventos. Aguarde...\n\n")
        self.txt_logs.configure(state="disabled")
        
        def run_ps():
            ps_cmd = f"Get-WinEvent -FilterHashtable @{{LogName='System'; ProviderName='Service Control Manager'; StartTime=(Get-Date).AddDays(-1)}} -ErrorAction SilentlyContinue | Where-Object {{$_.Message -match '{self.service_name}'}} | Select-Object TimeCreated, Message -First 15 | Format-List"
            try:
                result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True, creationflags=0x08000000)
                output = result.stdout.strip()
                self.txt_logs.configure(state="normal")
                if output: self.txt_logs.insert("end", output)
                else: self.txt_logs.insert("end", "Nenhum erro crítico encontrado para este serviço nas últimas 24 horas.")
                self.txt_logs.configure(state="disabled")
            except Exception as e:
                self.txt_logs.configure(state="normal")
                self.txt_logs.insert("end", f"Falha ao executar consulta: {e}")
                self.txt_logs.configure(state="disabled")
                
        threading.Thread(target=run_ps, daemon=True).start()

    # ==========================================
    # RODAPÉ E SALVAMENTO
    # ==========================================
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=15, padx=15)
        
        ctk.CTkButton(footer,
            text="Salvar Alterações",
            text_color=AppColors.WHITE,
            fg_color=AppColors.DUSK_BLUE,
            corner_radius=4,
            height=28,
            width=140,
            command=self._salvar_alteracoes).pack(side="right", padx=5)
        ctk.CTkButton(footer, text="Cancelar",
            text_color=AppColors.CHARCOAL_BLUE,
            fg_color=AppColors.TRANSPARENT,
            border_color=AppColors.CHARCOAL_BLUE,
            hover_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=4,
            height=28,
            width=100, command=self.destroy).pack(side="right", padx=5)

    def _salvar_alteracoes(self):
        # 1. VALIDAÇÃO ANTI-LOOP (Ping-Pong e Kamikaze)
        act_running = self.cb_states["running"].get()
        act_stopped = self.cb_states["stopped"].get()

        if act_running == "Parar" and act_stopped in ["Iniciar", "Reiniciar"]:
            msg = ("⚠️ EFEITO LOOP DETECTADO!\n\nVocê configurou para 'Parar' o serviço se ele estiver em execução, "
                   f"mas configurou para '{act_stopped}' se ele estiver parado.\nIsso criará uma guerra infinita.\n\n"
                   "💡 SOLUÇÃO: Mude a ação do status 'Parado' para 'Não Fazer Nada'.")
            messagebox.showerror("Bloqueio de Segurança", msg, parent=self)
            return

        if act_running == "Reiniciar":
            msg = ("⚠️ EFEITO LOOP DETECTADO!\n\nVocê configurou a ação 'Reiniciar' para o status 'Em Execução'. "
                   "Isso fará o WatchdogApp reiniciar o serviço infinitamente.\n\n"
                   "💡 SOLUÇÃO: Use a aba 'Limites de Desempenho' e mude a ação 'Em Execução' para 'Não Fazer Nada'.")
            messagebox.showerror("Bloqueio de Segurança", msg, parent=self)
            return

        if self.chk_pend_var.get() and (int(self.ent_pend_start.get()) < 10 or int(self.ent_pend_stop.get()) < 10):
            messagebox.showerror("Aviso de Segurança", "O timeout de transição não pode ser inferior a 10 segundos.", parent=self)
            return

        # 2. AUTO-FORMATAÇÃO DA HORA (SMART SCHEDULE)
        raw_time = self.ent_time.get().strip()
        formatted_time = "03:00" 
        if raw_time:
            if ":" not in raw_time and raw_time.isdigit():
                if len(raw_time) == 3: raw_time = f"0{raw_time[0]}:{raw_time[1:]}" 
                elif len(raw_time) == 4: raw_time = f"{raw_time[:2]}:{raw_time[2:]}" 
            try:
                formatted_time = datetime.strptime(raw_time, "%H:%M").strftime("%H:%M")
            except ValueError:
                messagebox.showerror("Hora Inválida", "Formato de hora inválido no Agendamento Preventivo (ex: 08:30).", parent=self)
                return 

        # 3. SET STARTUP TYPE NO WINDOWS
        startup_map = {"Automático": "auto", "Automático (Atraso na inicialização)": "delayed-auto", "Manual": "demand", "Desativado": "disabled"}
        try:
            os_startup_cmd = startup_map.get(self.startup_var.get(), "demand")
            subprocess.run(f'sc config "{self.service_name}" start= {os_startup_cmd}', shell=True, capture_output=True, creationflags=0x08000000)
        except Exception: pass

        # 4. SALVAMENTO NO CONFIG_DATA E REPOSITÓRIO
        try:
            self.cfg["state_actions"] = {s_eng: cb.get() for s_eng, cb in self.cb_states.items()}
            self.cfg["pending_timeouts"] = {
                "enabled": self.chk_pend_var.get(),
                "start": int(self.ent_pend_start.get()),
                "stop_others": int(self.ent_pend_stop.get())
            }
            
            self.cfg["emergency"] = {
                "enabled": self.chk_em_var.get(),
                "max_retries": int(self.ent_retries.get()), 
                "reset_days": int(self.ent_em_reset.get()), 
                "run_script": self.ent_script.get().strip()
            }
            
            self.cfg["perf_limits"] = {
                "cpu": float(self.ent_cpu.get()),
                "ram": float(self.ent_ram.get()),
                "disk": float(self.ent_disk.get()),
                "tolerance": int(self.ent_tol.get()),
                "max_restarts": int(self.ent_perf_max.get()),
                "reset_days": int(self.ent_perf_reset.get())
            }
            
            self.cfg["heartbeat"] = {
                "enabled": self.chk_hb_var.get(),
                "timeout": int(self.ent_hb_time.get()),
                "max_restarts": int(self.ent_hb_max.get()),
                "reset_days": int(self.ent_hb_reset.get())
            }
            
            self.cfg["custom_deps"] = {
                "services": self.ent_deps.get().strip(),
                "behavior": self.cb_dep_behavior.get()
            }
            self.cfg["schedule"] = {
                "enabled": self.chk_sched_var.get(),
                "days": self.cb_days.get(),
                "time": formatted_time
            }

            PersistenceRepository.salvar(self.master_tab.config_data)
            
            if hasattr(self.master_tab, "log"):
                self.master_tab.log(f"💾 Configurações salvas para o serviço: {self.service_name}")
                
            self.destroy()
        except ValueError:
            messagebox.showerror("Erro de Validação", "Certifique-se que os limites e tempos contêm apenas números válidos.", parent=self)