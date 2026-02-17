import os
import subprocess
import customtkinter as ctk
import threading
from tkinter import messagebox

from ..colors import AppColors
from ...infrastructure.system_utils import SystemUtils
from ...infrastructure.persistence import PersistenceRepository
from ..components.dialogs import DialogoVerificacao

class MonitorTab(ctk.CTkFrame):
    def __init__(self, parent, engine, config_data, icon_manager, log_callback, main_app_ref):
        super().__init__(parent, fg_color=AppColors.BRIGHT_SNOW)
        self.engine = engine
        self.config_data = config_data
        self.icon_manager = icon_manager
        self.log = log_callback
        self.app = main_app_ref # Para mudar estado da aba config se precisar
        
        self.item_selecionado = None
        self.botoes_para_atualizar = []
        self.linhas_visuais = []
        
        self._setup_ui()
        self._popular_lista_monitoramento()
        self.after(200, self.listar_processos_ativos)

    def _setup_ui(self):
        self.grid_columnconfigure((0,1), weight=1, uniform="equal_cols")
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = ctk.CTkFrame(self, 
            fg_color=AppColors.WHITE, 
            border_color=AppColors.PLATINUM, 
            border_width=2, 
            corner_radius=8)
        self.frame_left.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10, rowspan=50)
       
        ctk.CTkLabel(self.frame_left, text="Processos Ativos", font=("Arial", 16, "bold"), text_color=AppColors.CHARCOAL_BLUE).pack(pady=5)

        self.entry_busca = ctk.CTkEntry(self.frame_left, 
            placeholder_text="Buscar...",
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=4)
        self.entry_busca.pack(fill="x", padx=10)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.listar_processos_ativos())
        
        self.scroll_ativos = ctk.CTkScrollableFrame(self.frame_left,               
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=4,
            scrollbar_fg_color="transparent",
            )
        self.scroll_ativos.pack(fill="both", expand=True, padx=10, pady=5)
        
        frame_btns = ctk.CTkFrame(self.frame_left, fg_color=AppColors.TRANSPARENT, bg_color=AppColors.TRANSPARENT)
        frame_btns.pack(fill="x", padx=10, pady=(5,10))
        
        ctk.CTkButton(frame_btns,
            image=self.icon_manager._icons.get("refresh"),
            text="Atualizar",
            text_color=AppColors.CHARCOAL_BLUE,
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=4,
            height=28,
            command=self.listar_processos_ativos).pack(side="left", padx=2, expand=True, fill="x")
        
        self.btn_add = ctk.CTkButton(
            frame_btns, 
            image=self.icon_manager._icons.get("add"), 
            text="Monitorar",
            text_color=AppColors.WHITE,
            fg_color=AppColors.DUSK_BLUE,
            corner_radius=4,
            height=28, 
            command=self.adicionar_ao_monitor
        )
        self.btn_add.pack(side="left", padx=2, expand=True, fill="x")

        # Lado Direito (Lista de Monitoramento)
        self.frame_right = ctk.CTkFrame(self, 
            fg_color=AppColors.WHITE, 
            border_color=AppColors.PLATINUM, 
            border_width=2, 
            corner_radius=8)
        self.frame_right.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        
        ctk.CTkLabel(self.frame_right, text="Lista de Monitoramento", font=("Arial", 16, "bold"),text_color=AppColors.CHARCOAL_BLUE).pack(pady=(5,8))
        
        # Header da tabela
        h_frame = ctk.CTkFrame(self.frame_right, height=30,
                       fg_color=AppColors.PLATINUM,
                       corner_radius=4)
        h_frame.pack(fill="x", padx=10)

        h_frame.grid_columnconfigure(0, weight=1, uniform="cols")
        h_frame.grid_columnconfigure(1, weight=1, uniform="cols")

        ctk.CTkLabel(h_frame, text="Processo",
                    font=("Arial", 12, "bold"),
                    anchor="w").grid(row=0, column=0, sticky="ew", padx=10)

        ctk.CTkLabel(h_frame, text="Regra",
                    font=("Arial", 12, "bold"),
                    anchor="w").grid(row=0, column=1, sticky="ew", padx=10)


        # Scroll da lista
        self.scroll_monitor = ctk.CTkScrollableFrame(self.frame_right,
            fg_color=AppColors.WHITE,
            border_color=AppColors.PLATINUM,
            border_width=2,
            corner_radius=4)
        self.scroll_monitor.pack(fill="both", expand=True, padx=10)
        
        self.btn_start = ctk.CTkButton(self.frame_right,
            image=self.icon_manager._icons.get("play"),
            text="INICIAR MONITORAMENTO",
            text_color=AppColors.WHITE,
            fg_color=AppColors.DUSK_BLUE,
            height=28,
            corner_radius=4,
            command=self.toggle_monitor)
        self.btn_start.pack(side="bottom", padx=10, fill="x",pady=(5,10))
        
    # --- LÓGICA DE UI ---
    def listar_processos_ativos(self):
        for w in self.scroll_ativos.winfo_children(): w.destroy()
        self.botoes_para_atualizar = []
        
        grupos = SystemUtils.listar_processos_agrupados(self.entry_busca.get())
        
        self._renderizar_grupo("APLICATIVOS", grupos["apps"], AppColors.DUSK_BLUE)
        self._renderizar_grupo("SEGUNDO PLANO", grupos["back"], AppColors.GREEN)
        self._renderizar_grupo("SISTEMA", grupos["system"], "#666666")
        
        threading.Thread(target=self._carregar_icones_bg, daemon=True).start()

    def _renderizar_grupo(self, titulo, dados, cor):
        if not dados: return
        ctk.CTkLabel(self.scroll_ativos, text=titulo, anchor="w", font=("Arial", 12, "bold"), text_color=cor).pack(fill="x")
        
        for nome in sorted(dados.keys()):
            info = dados[nome]
            txt = f"   {nome} ({info['count']})" if info['count'] > 1 else f"   {nome}"
            
            btn = ctk.CTkButton(self.scroll_ativos, text=txt, anchor="w", fg_color="white", text_color="black", height=28)
            btn.configure(command=lambda b=btn, n=nome, p=info['path']: self._selecionar_item(b, n, p))
            btn.bind("<Double-Button-1>", lambda event: self.adicionar_ao_monitor())
            btn.pack(fill="x", pady=1)
            self.botoes_para_atualizar.append((btn, nome, info['path']))

    def _carregar_icones_bg(self):
        for btn, nome, path in self.botoes_para_atualizar:
            if not btn.winfo_exists(): continue
            icone = self.icon_manager.carregar(nome, path)
            if icone:
                self.after(0, lambda b=btn, i=icone: b.configure(image=i, compound="left") if b.winfo_exists() else None)

    def _selecionar_item(self, widget, nome, path):
        if self.item_selecionado:
            try: self.item_selecionado.configure(fg_color="white", text_color="black")
            except: pass
        self.item_selecionado = widget
        self.escolha_nome = nome
        self.escolha_path = path
        widget.configure(fg_color="#1f538d", text_color="white")

    def adicionar_ao_monitor(self):
        if not hasattr(self, 'escolha_nome') or not self.escolha_nome: return
        if self.escolha_nome in self.config_data.processos: return
        
        # Se estiver rodando, impede adição (Defesa extra além do bloqueio visual)
        if self.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para adicionar itens.")
            return

        self.config_data.processos[self.escolha_nome] = {
            'path': self.escolha_path, 'regra': "Não Reiniciar", 'status': "Iniciando"
        }
        
        self.criar_linha_monitor(self.escolha_nome, "Não Reiniciar", self.escolha_path)
        PersistenceRepository.salvar(self.config_data)

    def criar_linha_monitor(self, nome, regra, path=None):

        # Container e Bottim_border para criar efeito de borda inferior
        container = ctk.CTkFrame(self.scroll_monitor, fg_color=AppColors.PLATINUM)
        container.pack(fill="x")
        row_frame = ctk.CTkFrame(container, fg_color="white", corner_radius=0)
        row_frame.pack(fill="x")
        row_frame.grid_columnconfigure(0, weight=1, uniform="cols")
        row_frame.grid_columnconfigure(1, weight=1, uniform="cols")
        bottom_border = ctk.CTkFrame(container, height=1, fg_color=AppColors.PLATINUM)
        bottom_border.pack(fill="x")

        self.linhas_visuais.append(row_frame)

        # COLUNA 1 - PROCESSO
        icone = self.icon_manager.carregar(nome, path)

        frame_processo = ctk.CTkFrame(row_frame, fg_color="transparent")
        frame_processo.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ctk.CTkLabel(
            frame_processo,
            text=nome,
            image=icone,
            compound="left",
            anchor="w",
            font=("Arial", 12),
            text_color="black"
        ).pack(anchor="w")

        # COLUNA 2 - REGRA
        frame_regra = ctk.CTkFrame(row_frame, fg_color="transparent")
        frame_regra.grid(row=0, column=1, sticky="ew", padx=10)

        frame_regra.grid_columnconfigure(0, weight=1)
        frame_regra.grid_columnconfigure(1, weight=0)

        combo_regra = ctk.CTkOptionMenu(
            frame_regra,
            text_color=AppColors.NIGHT,
            fg_color=AppColors.PLATINUM,
            button_color=AppColors.PLATINUM,
            button_hover_color=AppColors.PLATINUM,
            values=["Não Reiniciar", "Sempre Reiniciar", "Reiniciar se erro Windows"],
            command=lambda r: self._atualizar_regra(nome, r)
        )
        combo_regra.set(regra)
        combo_regra.grid(row=0, column=0, sticky="ew")

        btn_remover = ctk.CTkButton(
            frame_regra,
            text="✕",
            width=16,
            fg_color="transparent",
            text_color=AppColors.NIGHT,
            hover=False,
            command=lambda: self._remover_processo(nome, container)
        )
        btn_remover.grid(row=0, column=1, padx=(4, 0))


    def _atualizar_regra(self, nome, nova_regra):
        if self.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para editar.")
            return
            
        if nome in self.config_data.processos:
            self.config_data.processos[nome]['regra'] = nova_regra
        PersistenceRepository.salvar(self.config_data)

    def _remover_processo(self, nome, widget):
        if self.engine.rodando:
            messagebox.showwarning("Bloqueado", "Pare o monitoramento para remover itens.")
            return

        if nome in self.config_data.processos:
            del self.config_data.processos[nome]
            
            # Remove da lista visual de controle
            if widget in self.linhas_visuais:
                self.linhas_visuais.remove(widget)
                
            widget.destroy()
            PersistenceRepository.salvar(self.config_data)

    def _popular_lista_monitoramento(self):
        # Limpa tudo antes de recriar (evita duplicatas e limpa a lista de controle)
        for w in self.scroll_monitor.winfo_children(): w.destroy()
        self.linhas_visuais = []
        
        for nome, dados in self.config_data.processos.items():
            self.criar_linha_monitor(nome, dados['regra'], dados.get("path"))
    
    def toggle_monitor(self):
        if not self.engine.rodando:
            # INICIAR
            if not self.config_data.processos:
                messagebox.showwarning("Vazio", "Adicione processos primeiro.")
                return
            
            lista_alvo = list(self.config_data.processos)
            ausentes = SystemUtils.verificar_processos_ausentes(lista_alvo)

            if(ausentes):
                dialogo = DialogoVerificacao(self, ausentes, self.icon_manager, self.config_data)
                self.master.wait_window(dialogo)
                # dialogo.grab_set(dialogo)

                escolha = dialogo.resultado

                if escolha == "cancelar":
                        return
                elif escolha == "forcar":
                    self.log("❗ Tentando forçar inicialização dos processos...")
                    self._forcar_inicializacao(ausentes)
                elif escolha == "ignorar":
                        self.log("❗ Iniciar monitoramento mesmo com processos ausentes") 

            self.engine.iniciar()
            self.config_data.monitoramento_ativo_no_fechamento = True
            PersistenceRepository.salvar(self.config_data)
            
            self.btn_start.configure(image=self.icon_manager._icons.get("stop"),
                text="PARAR MONITORAMENTO",
                text_color=AppColors.WHITE,
                height=28,
                fg_color="orange",
                corner_radius=4)
            self._definir_estado_edicao("disabled")
        
        else:
            # PARAR
            self.engine.parar()
            self.config_data.monitoramento_ativo_no_fechamento = False
            PersistenceRepository.salvar(self.config_data)
            self.btn_start.configure(
                image=self.icon_manager._icons.get("play"),
                text="INICIAR MONITORAMENTO",
                text_color=AppColors.WHITE,
                fg_color=AppColors.DUSK_BLUE,
                height=28,
                corner_radius=4)
            self._definir_estado_edicao("normal")
    
    def _forcar_inicializacao(self, lista_nomes):
        """ Tenta abrir os executáveis que estão faltando """
        for nome in lista_nomes:
            path = self.config_data.processos[nome].get("path")
            if path and os.path.exists(path):
                try:
                    subprocess.Popen(path)
                    self.log(f" > Iniciado manualmente: {nome}")
                except Exception as e:
                    self.log(f" > Erro ao iniciar {nome}: {e}")
            else:
                self.log(f" > Impossível iniciar {nome}: Caminho não encontrado.")

    def _definir_estado_edicao(self, estado):
        """
        Bloqueia (disabled) ou Desbloqueia (normal) a interface de edição.
        """
        # 1. Bloqueia botão de adicionar (Agora funciona pois atribuímos self.btn_add)
        if hasattr(self, 'btn_add'):
            if(estado=="disabled"):
                self.btn_add.configure(state=estado, fg_color=AppColors.DUSK_BLUE)
            else: 
                self.btn_add.configure(state=estado, fg_color=AppColors.DUSK_BLUE)
            

        # 2. Bloqueia as linhas usando a lista confiável self.linhas_visuais
        for frame_linha in self.linhas_visuais:
            # Itera sobre os filhos de CADA LINHA (isso o tkinter garante que funciona)
            for widget in frame_linha.winfo_children():
                if isinstance(widget, (ctk.CTkOptionMenu, ctk.CTkButton)):
                    # Não bloqueia Labels, apenas interativos
                    try: widget.configure(state=estado)
                    except: pass

    def _automacao_inicio_monitoramento(self):
        """ Executado automaticamente após o delay inicial """
        if self.engine.rodando: return

        self.log("🤖 Iniciando automação de retomada...")
        
        # 1. Verifica ausentes
        lista_alvo = list(self.config_data.processos)
        ausentes = SystemUtils.verificar_processos_ausentes(lista_alvo)
        
        if ausentes:
            acao = self.config_data.acao_ao_iniciar
            self.log(f"⚠️ Processos ausentes detectados: {len(ausentes)}. Ação: {acao.upper()}")

            if acao == "forcar":
                 self._forcar_inicializacao(ausentes)
                 # Pequeno delay extra para dar tempo dos processos abrirem antes de monitorar
                 self.after(2000, lambda: self._iniciar_engine_silencioso())
                 return
            
            elif acao == "ignorar":
                 # Segue o baile, monitora o que tem (ou avisa que está parado)
                 pass
        
        self._iniciar_engine_silencioso()

    def _iniciar_engine_silencioso(self):
        """ Inicia o motor sem passar pelos diálogos de UI """
        self.engine.iniciar()
        
        # Atualiza UI
        self.btn_start.configure(image=self.icon_manager._icons.get("stop"), text="PARAR MONITORAMENTO", height=32, fg_color="orange")
        self._definir_estado_edicao("disabled")
        self.log("✅ Monitoramento retomado automaticamente.")