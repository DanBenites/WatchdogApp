# src/ui/components/process_properties.py
import os
import time
from datetime import datetime
import customtkinter as ctk
from tkinter import filedialog, messagebox

from ...infrastructure.icon_manager import IconeManager
from ..colors import AppColors
from ...infrastructure.persistence import PersistenceRepository

class ProcessPropertiesWindow(ctk.CTkToplevel):
    def __init__(self, master_tab, processos_view, process_name):
        super().__init__(master_tab)
        
        # Garante que o fundo da janela tem a mesma cor limpa da aplicação
        self.configure(fg_color=AppColors.BRIGHT_SNOW)
        self.icon_manager = IconeManager()
        self.master_tab = master_tab
        self.processos_view = processos_view
        self.process_name = process_name
        
        self.title(f"Propriedades Avançadas: {process_name}")
        self.geometry("580x680")
        self.grab_set() 
        self.transient(master_tab) 

        # --- Ícone da Janela ---
        try:
            icon_path = os.path.abspath("assets/icons/app_icon.ico")
            self.after(200, lambda: self.iconbitmap(icon_path))
        except Exception:
            pass

        self.cfg = self.master_tab.config_data.processos.get(self.process_name, {})
        self._inicializar_chaves_vazias()
        self.engine_state = self.master_tab.engine.process_engine.get_or_create_state(self.process_name)
        
        self._build_top_tabs()
        self._build_content_area()
        self._build_footer()

    def _inicializar_chaves_vazias(self):
        """Garante que o dicionário do processo tem todas as chaves necessárias"""
        if "execucao" not in self.cfg:
            self.cfg["execucao"] = {"minimizado": False, "oculto": False, "cooldown_enabled": False, "cooldown": 0, "graceful_close": False, "graceful_timeout": 10, "check_exit_code": False}
        elif "cooldown_enabled" not in self.cfg["execucao"]:
            self.cfg["execucao"]["cooldown_enabled"] = False

        if "desempenho" not in self.cfg:
            self.cfg["desempenho"] = {
                "cpu_max": 0.0, "ram_max": 0.0, "tolerance": 30, "max_restarts": 3, "reset_dias": 0,
                "heartbeat_enabled": False, "heartbeat_timeout": 5, "hb_max_restarts": 3, "hb_reset_dias": 0
            }
            
        if "emergencia" not in self.cfg:
            self.cfg["emergencia"] = {"enabled": False, "max_falhas": 3, "reset_dias": 0, "script_path": ""}
        elif "enabled" not in self.cfg["emergencia"]:
            self.cfg["emergencia"]["enabled"] = False

    def _create_section_header(self, parent, text, help_text=""):
        frm = ctk.CTkFrame(parent, fg_color="transparent")
        frm.pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(frm, text=text, font=("Arial", 13, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(side="left")
        if help_text:
            btn_help = ctk.CTkButton(
                frm, text="?", width=20, height=20, corner_radius=10, fg_color=AppColors.DUSK_BLUE, 
                command=lambda: self._show_help_dialog(text, help_text) 
            )
            btn_help.pack(side="left", padx=10)
        return frm

    # ==========================================
    # MODAL DE AJUDA
    # ==========================================
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


    # ==========================================
    # SISTEMA DE NAVEGAÇÃO CUSTOMIZADO (ABAS)
    # ==========================================
    def _build_top_tabs(self):
        self.tabs_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        self.tabs_frame.pack(fill="x", padx=15, pady=(10, 0))

        self.btn_geral = ctk.CTkButton(
            self.tabs_frame, text="Geral", fg_color="transparent", 
            text_color=AppColors.CHARCOAL_BLUE, hover_color=AppColors.PLATINUM, 
            font=("Arial", 12, "bold"), height=30, width=100, corner_radius=0, 
            command=self.show_geral
        )
        self.btn_recuperacao = ctk.CTkButton(
            self.tabs_frame, text="Recuperação", fg_color="transparent", 
            text_color=AppColors.CHARCOAL_BLUE, hover_color=AppColors.PLATINUM, 
            font=("Arial", 12, "bold"), height=30, width=100, corner_radius=0, 
            command=self.show_recuperacao
        )

        self.btn_geral.pack(side="left")
        self.btn_recuperacao.pack(side="left")

        separator = ctk.CTkFrame(self, fg_color=AppColors.PLATINUM, height=2)
        separator.pack(fill="x", padx=15)

    def _build_content_area(self):
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=15, pady=(10, 0))
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.frame_geral = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
        self.frame_recuperacao = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")

        self._build_geral_tab()
        self._build_recuperacao_tab()

        self.show_geral()

    def show_geral(self):
        self._reset_tab_buttons()
        self.btn_geral.configure(fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE)
        self.frame_recuperacao.grid_forget()
        self.frame_geral.grid(row=0, column=0, sticky="nsew")

    def show_recuperacao(self):
        self._reset_tab_buttons()
        self.btn_recuperacao.configure(fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE)
        self.frame_geral.grid_forget()
        self.frame_recuperacao.grid(row=0, column=0, sticky="nsew")

    def _reset_tab_buttons(self):
        self.btn_geral.configure(fg_color="transparent", text_color=AppColors.CHARCOAL_BLUE)
        self.btn_recuperacao.configure(fg_color="transparent", text_color=AppColors.CHARCOAL_BLUE)

    # ==========================================
    # CONTEÚDO DA ABA 1: GERAL E EXECUÇÃO
    # ==========================================
    def _build_geral_tab(self):
        scroll = self.frame_geral # Aponta para o novo container de aba
        exec_cfg = self.cfg["execucao"]

        # --- 1. IDENTIFICAÇÃO ---
        ctk.CTkLabel(scroll, text="Caminho do Executável:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(5, 0))
        path_box = ctk.CTkTextbox(scroll, height=50, fg_color=AppColors.WHITE, border_color=AppColors.PLATINUM, border_width=1)
        path_box.pack(fill="x", pady=5)
        path_box.insert("0.0", self.cfg.get("path", "Caminho não encontrado"))
        path_box.configure(state="disabled")

        # --- 2. REGRA PRINCIPAL ---
        self._create_section_header(scroll, "Regra Principal de Monitoramento", "Define o comportamento base do Watchdog para este processo.")
        self.cb_regra = ctk.CTkOptionMenu(
            scroll, width=300, 
            values=["Não Reiniciar", "Sempre Reiniciar", "Reiniciar se erro Windows", "Reinício Condicional", "Sempre Encerrar (Blacklist)"],
            fg_color=AppColors.PLATINUM, text_color=AppColors.NIGHT, button_color=AppColors.PLATINUM,
            command=self._toggle_reinicio_condicional
        )
        self.cb_regra.set(self.cfg.get("regra", "Não Reiniciar"))
        self.cb_regra.pack(anchor="w", pady=5)

        # --- 3. PARÂMETROS DE INICIALIZAÇÃO ---
        self._create_section_header(scroll, "Parâmetros de Inicialização", "Força o programa a abrir de forma silenciosa.")
        frm_init = ctk.CTkFrame(scroll, fg_color=AppColors.WHITE, corner_radius=5, border_width=1, border_color=AppColors.PLATINUM)
        frm_init.pack(fill="x", pady=5)
        
        self.chk_min = ctk.BooleanVar(value=exec_cfg.get("minimizado", False))
        ctk.CTkCheckBox(frm_init, text="Iniciar Minimizado", variable=self.chk_min, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.chk_hide = ctk.BooleanVar(value=exec_cfg.get("oculto", False))
        ctk.CTkCheckBox(frm_init, text="Iniciar Oculto (Em Segundo Plano)", variable=self.chk_hide, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE).pack(anchor="w", padx=10, pady=(5, 10))

        # --- 4. REINÍCIO CONDICIONAL ---
        self._create_section_header(scroll, "Opções de Reinício Condicional", "Estas opções só estão ativas se a regra acima for 'Reinício Condicional'.")
        self.frm_cond = ctk.CTkFrame(scroll, fg_color=AppColors.WHITE, corner_radius=5, border_width=1, border_color=AppColors.PLATINUM)
        self.frm_cond.pack(fill="x", pady=5)

        self.chk_exit_code = ctk.BooleanVar(value=exec_cfg.get("check_exit_code", False))
        self.chk_exit_code_widget = ctk.CTkCheckBox(self.frm_cond, text="Reiniciar apenas se o Exit Code indicar falha", variable=self.chk_exit_code, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE)
        self.chk_exit_code_widget.pack(anchor="w", padx=10, pady=(15, 5))

        self.chk_graceful = ctk.BooleanVar(value=exec_cfg.get("graceful_close", False))
        self.chk_graceful_widget = ctk.CTkCheckBox(self.frm_cond, text="Tentar Fechamento Elegante antes do Force Kill", variable=self.chk_graceful, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE)
        self.chk_graceful_widget.pack(anchor="w", padx=10, pady=5)

        sub_frm1 = ctk.CTkFrame(self.frm_cond, fg_color="transparent")
        sub_frm1.pack(fill="x", padx=35, pady=5)
        self.lbl_grace_time = ctk.CTkLabel(sub_frm1, text="Timeout do Fechamento Elegante (segundos):")
        self.lbl_grace_time.pack(side="left")
        self.ent_grace_time = ctk.CTkEntry(sub_frm1, width=60)
        self.ent_grace_time.insert(0, str(exec_cfg.get("graceful_timeout", 10)))
        self.ent_grace_time.pack(side="left", padx=10)

        sub_frm2 = ctk.CTkFrame(self.frm_cond, fg_color="transparent")
        sub_frm2.pack(fill="x", padx=10, pady=(10, 15))
        
        self.chk_cooldown = ctk.BooleanVar(value=exec_cfg.get("cooldown_enabled", False))
        self.chk_cooldown_widget = ctk.CTkCheckBox(sub_frm2, text="Cooldown: Aguardar X segundos antes de reabrir:", variable=self.chk_cooldown, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE)
        self.chk_cooldown_widget.pack(side="left")

        self.ent_cooldown = ctk.CTkEntry(sub_frm2, width=60)
        self.ent_cooldown.insert(0, str(exec_cfg.get("cooldown", 0)))
        self.ent_cooldown.pack(side="left", padx=10)

        # --- 5. BOTÕES DE RESET ---
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(30, 10))
        ctk.CTkButton(btn_frame, text="Zerar Contadores", image=self.icon_manager._icons.get("refresh"), text_color=AppColors.CHARCOAL_BLUE, fg_color=AppColors.WHITE, hover_color=AppColors.PLATINUM, border_width=2, border_color=AppColors.CHARCOAL_BLUE, command=self._reset_counters).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Resetar Configurações para Padrão", image=self.icon_manager._icons.get("reset_settings"), text_color=AppColors.WHITE, fg_color=AppColors.FLAG_RED, hover_color="#c82333", command=self._reset_configs).pack(side="left", padx=5)

        self._toggle_reinicio_condicional(self.cb_regra.get())

    def _toggle_reinicio_condicional(self, escolha):
        estado = "normal" if escolha == "Reinício Condicional" else "disabled"
        cor_texto = AppColors.CHARCOAL_BLUE if estado == "normal" else "gray"

        self.chk_exit_code_widget.configure(state=estado, text_color=cor_texto)
        self.chk_graceful_widget.configure(state=estado, text_color=cor_texto)
        self.lbl_grace_time.configure(text_color=cor_texto)
        self.ent_grace_time.configure(state=estado)
        
        self.chk_cooldown_widget.configure(state=estado, text_color=cor_texto)
        self.ent_cooldown.configure(state=estado)

    def _reset_counters(self):
        self.engine_state["crash_count"] = 0
        self.engine_state["perf_retry_count"] = 0
        self.engine_state["hb_retry_count"] = 0
        self.engine_state["script_executed"] = False
        self._show_help_dialog("Contadores", "Os contadores de falhas na memória foram zerados com sucesso!")
        self.destroy()

    def _reset_configs(self):
        if messagebox.askyesno("Atenção", f"Tem certeza que deseja apagar TODAS as configurações avançadas do processo '{self.process_name}'?", parent=self):
            path_salvo = self.cfg.get("path", "")
            self.master_tab.config_data.processos[self.process_name] = {'path': path_salvo, 'regra': "Não Reiniciar"}
            PersistenceRepository.salvar(self.master_tab.config_data)
            self.destroy()

    # ==========================================
    # CONTEÚDO DA ABA 2: RECUPERAÇÃO
    # ==========================================
    def _build_recuperacao_tab(self):
        scroll = self.frame_recuperacao # Aponta para o novo container de aba
        perf_cfg = self.cfg["desempenho"]
        em_cfg = self.cfg["emergencia"]

        # 1. LIMITES DE DESEMPENHO
        self._create_section_header(scroll, "Limites de Desempenho (0 = Desativado)", "Monitoriza vazamentos de memória ou picos de CPU.")
        frm_perf = ctk.CTkFrame(scroll, fg_color=AppColors.WHITE, corner_radius=5, border_width=1, border_color=AppColors.PLATINUM)
        frm_perf.pack(fill="x", pady=5)

        ctk.CTkLabel(frm_perf, text="Reiniciar se CPU exceder (%):").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.ent_cpu = ctk.CTkEntry(frm_perf, width=60); self.ent_cpu.insert(0, str(perf_cfg.get("cpu_max", 0.0)))
        self.ent_cpu.grid(row=0, column=1, padx=10, pady=5)

        ctk.CTkLabel(frm_perf, text="Reiniciar se RAM exceder (MB):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.ent_ram = ctk.CTkEntry(frm_perf, width=60); self.ent_ram.insert(0, str(perf_cfg.get("ram_max", 0.0)))
        self.ent_ram.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(frm_perf, text="Tempo de Tolerância (Segundos):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.ent_tol = ctk.CTkEntry(frm_perf, width=60); self.ent_tol.insert(0, str(perf_cfg.get("tolerance", 30)))
        self.ent_tol.grid(row=2, column=1, padx=10, pady=5)

        ctk.CTkFrame(frm_perf, height=1, fg_color=AppColors.PLATINUM).grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(frm_perf, text="Parar de tentar após X reinícios:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.ent_perf_max = ctk.CTkEntry(frm_perf, width=60); self.ent_perf_max.insert(0, str(perf_cfg.get("max_restarts", 3)))
        self.ent_perf_max.grid(row=4, column=1, padx=10, pady=5)

        fails_perf = self.engine_state.get("perf_retry_count", 0)
        ctk.CTkLabel(frm_perf, text=f"(Falhas atuais: {fails_perf})", text_color="#dc3545" if fails_perf > 0 else "gray", font=("Arial", 11, "italic")).grid(row=4, column=2, padx=5)
        
        ctk.CTkLabel(frm_perf, text="Resetar contador após X dias:").grid(row=5, column=0, padx=10, pady=(5, 10), sticky="w")
        self.ent_perf_reset = ctk.CTkEntry(frm_perf, width=60); self.ent_perf_reset.insert(0, str(perf_cfg.get("reset_dias", 0)))
        self.ent_perf_reset.grid(row=5, column=1, padx=10, pady=(5, 10))

        # 2. HEARTBEAT
        self._create_section_header(scroll, "Verificação de Inatividade (Heartbeat)", "Detecta processos travados internamente (CPU 0%).")
        frm_hb = ctk.CTkFrame(scroll, fg_color=AppColors.WHITE, corner_radius=5, border_width=1, border_color=AppColors.PLATINUM)
        frm_hb.pack(fill="x", pady=5)

        self.chk_hb_var = ctk.BooleanVar(value=perf_cfg.get("heartbeat_enabled", False))
        ctk.CTkCheckBox(frm_hb, text="Ativar reinício por inatividade", variable=self.chk_hb_var, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="w")
        
        ctk.CTkLabel(frm_hb, text="Tempo limite de Inatividade (Minutos):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.ent_hb_time = ctk.CTkEntry(frm_hb, width=60); self.ent_hb_time.insert(0, str(perf_cfg.get("heartbeat_timeout", 5)))
        self.ent_hb_time.grid(row=1, column=1, padx=10, pady=5)

        ctk.CTkLabel(frm_hb, text="Parar de tentar após X reinícios:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.ent_hb_max = ctk.CTkEntry(frm_hb, width=60); self.ent_hb_max.insert(0, str(perf_cfg.get("hb_max_restarts", 3)))
        self.ent_hb_max.grid(row=2, column=1, padx=10, pady=5)

        fails_hb = self.engine_state.get("hb_retry_count", 0)
        ctk.CTkLabel(frm_hb, text=f"(Falhas atuais: {fails_hb})", text_color="#dc3545" if fails_hb > 0 else "gray", font=("Arial", 11, "italic")).grid(row=2, column=2, padx=5)
        
        ctk.CTkLabel(frm_hb, text="Resetar contador após X dias:").grid(row=3, column=0, padx=10, pady=(5, 10), sticky="w")
        self.ent_hb_reset = ctk.CTkEntry(frm_hb, width=60); self.ent_hb_reset.insert(0, str(perf_cfg.get("hb_reset_dias", 0)))
        self.ent_hb_reset.grid(row=3, column=1, padx=10, pady=(5, 10))

        # 3. EMERGÊNCIA (CRASH LOOPS GERAIS)
        self._create_section_header(scroll, "Ações de Emergência (Crash Loops)", "Ações caso o programa caia repetidas vezes por erros próprios.")
        
        frm_em = ctk.CTkFrame(scroll, fg_color=AppColors.WHITE, corner_radius=5, border_width=1, border_color=AppColors.PLATINUM)
        frm_em.pack(fill="x", pady=5)
        
        frm_em.columnconfigure(0, weight=0)
        frm_em.columnconfigure(1, weight=0)
        frm_em.columnconfigure(2, weight=1) 

        self.chk_em_enabled = ctk.BooleanVar(value=em_cfg.get("enabled", False))
        ctk.CTkCheckBox(frm_em, text="Habilitar Proteção contra Crash Loops", variable=self.chk_em_enabled, fg_color=AppColors.DUSK_BLUE, border_color=AppColors.CHARCOAL_BLUE).grid(row=0, column=0, columnspan=3, padx=10, pady=(10, 5), sticky="w")

        ctk.CTkLabel(frm_em, text="Parar de tentar após X falhas seguidas:").grid(row=1, column=0, padx=(15, 10), pady=10, sticky="w")
        self.ent_retries = ctk.CTkEntry(frm_em, width=60)
        self.ent_retries.insert(0, str(em_cfg.get("max_falhas", 3)))
        self.ent_retries.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        fails_em = self.engine_state.get("crash_count", 0)
        ctk.CTkLabel(frm_em, text=f"(Falhas atuais: {fails_em})", text_color="#dc3545" if fails_em > 0 else "gray", font=("Arial", 11, "italic")).grid(row=1, column=2, padx=5)
        
        ctk.CTkLabel(frm_em, text="Resetar contagem de falhas após X dias:").grid(row=2, column=0, padx=(15, 10), pady=5, sticky="w")
        self.ent_reset = ctk.CTkEntry(frm_em, width=60)
        self.ent_reset.insert(0, str(em_cfg.get("reset_dias", 0)))
        self.ent_reset.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkLabel(frm_em, text="Executar Script em caso de Falha Crítica:").grid(row=3, column=0, columnspan=3, padx=(15, 10), pady=(15, 5), sticky="w")

        frm_script = ctk.CTkFrame(frm_em, fg_color="transparent")
        frm_script.grid(row=4, column=0, columnspan=3, padx=(15, 15), pady=(0, 15), sticky="ew")
        
        self.ent_script = ctk.CTkEntry(frm_script, placeholder_text="Ex: C:\\Scripts\\alerta_crash.bat")
        self.ent_script.insert(0, em_cfg.get("script_path", ""))
        self.ent_script.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkButton(frm_script, text="Procurar...", width=100,
                      image=self.icon_manager._icons.get("folder"),
                      fg_color=AppColors.DUSK_BLUE, text_color=AppColors.WHITE, 
                      command=self._browse_file).pack(side="right")
                      
    def _browse_file(self):
        filename = filedialog.askopenfilename(title="Selecione o Script", filetypes=(("Scripts", "*.bat *.cmd *.ps1 *.py"), ("Todos", "*.*")))
        if filename:
            self.ent_script.delete(0, "end")
            self.ent_script.insert(0, filename)

    # ==========================================
    # RODAPÉ E SALVAMENTO
    # ==========================================
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", side="bottom", pady=15, padx=15)
        

        ctk.CTkButton(
            footer,  
            text="Salvar Alterações",
            text_color=AppColors.WHITE,
            fg_color=AppColors.DUSK_BLUE,
            corner_radius=4,
            height=28,
            width=140,
            command=self._salvar_alteracoes
        ).pack(side="right", padx=5)

        ctk.CTkButton(footer,
            text="Cancelar",
            text_color=AppColors.CHARCOAL_BLUE,
            fg_color=AppColors.TRANSPARENT,
            border_color=AppColors.CHARCOAL_BLUE,
            hover_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=4,
            height=28,
            width=100,
            command=self.destroy).pack(side="right", padx=5)

    def _salvar_alteracoes(self):
        try:
            self.cfg["regra"] = self.cb_regra.get()
            
            self.cfg["execucao"]["minimizado"] = self.chk_min.get()
            self.cfg["execucao"]["oculto"] = self.chk_hide.get()
            self.cfg["execucao"]["check_exit_code"] = self.chk_exit_code.get()
            self.cfg["execucao"]["graceful_close"] = self.chk_graceful.get()
            self.cfg["execucao"]["graceful_timeout"] = int(self.ent_grace_time.get())
            
            self.cfg["execucao"]["cooldown_enabled"] = self.chk_cooldown.get()
            self.cfg["execucao"]["cooldown"] = int(self.ent_cooldown.get())

            self.cfg["desempenho"]["cpu_max"] = float(self.ent_cpu.get())
            self.cfg["desempenho"]["ram_max"] = float(self.ent_ram.get())
            self.cfg["desempenho"]["tolerance"] = int(self.ent_tol.get())
            self.cfg["desempenho"]["max_restarts"] = int(self.ent_perf_max.get())
            self.cfg["desempenho"]["reset_dias"] = int(self.ent_perf_reset.get())
            
            self.cfg["desempenho"]["heartbeat_enabled"] = self.chk_hb_var.get()
            self.cfg["desempenho"]["heartbeat_timeout"] = int(self.ent_hb_time.get())
            self.cfg["desempenho"]["hb_max_restarts"] = int(self.ent_hb_max.get())
            self.cfg["desempenho"]["hb_reset_dias"] = int(self.ent_hb_reset.get())

            self.cfg["emergencia"]["enabled"] = self.chk_em_enabled.get()
            self.cfg["emergencia"]["max_falhas"] = int(self.ent_retries.get())
            self.cfg["emergencia"]["reset_dias"] = int(self.ent_reset.get())
            self.cfg["emergencia"]["script_path"] = self.ent_script.get().strip()

            PersistenceRepository.salvar(self.master_tab.config_data)
            
            if self.process_name in self.processos_view.linhas_visuais:
                self.processos_view.linhas_visuais[self.process_name]["combo"].set(self.cfg["regra"])
                
            self.destroy()
            
        except ValueError:
            messagebox.showerror("Erro de Formatação", "Por favor, certifique-se de que os campos numéricos (Timeout, Cooldown, CPU, etc.) contêm apenas números válidos.", parent=self)