import os
import subprocess
import customtkinter as ctk
import threading
from tkinter import messagebox
from tkinter import filedialog
from datetime import datetime
from PIL import Image
import pystray
from pystray import MenuItem as item

# Importações das outras camadas
from ..domain.models import AppConfig
from ..infrastructure.persistence import PersistenceRepository
from ..infrastructure.system_utils import SystemUtils
from ..infrastructure.icon_manager import IconeManager
from ..services.monitor_engine import WatchdogEngine
from ..infrastructure.log_manager import LogManager

class DialogoVerificacao(ctk.CTkToplevel):
    def __init__(self, parent, ausentes, icon_manager, config_data):
        super().__init__(parent)
        self.title("Atenção")
        
        # 1. CÁLCULO DE TAMANHO E POSIÇÃO (CENTRALIZADO)
        # Calcula altura baseada na quantidade de itens (30px por item)
        altura_conteudo = len(ausentes) * 35 
        largura = 400
        altura = 160 + altura_conteudo
        
        # Obtém geometria da janela pai (WatchdogApp)
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()

        # Matemática para achar o centro
        pos_x = parent_x + (parent_w // 2) - (largura // 2)
        pos_y = parent_y + (parent_h // 2) - (altura // 2)

        # Aplica geometria fixa e centralizada
        self.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")
        self.resizable(False, False)
        
        # Configurações de Janela Modal
        self.attributes("-topmost", True)
        self.grab_set() # Bloqueia a janela de trás
        self.configure(fg_color="white")
        
        self.resultado = "cancelar"

        # --- CABEÇALHO ---
        ctk.CTkLabel(
            self, 
            text="Processos Ausentes", 
            font=("Arial", 16, "bold"), 
            text_color="black"
        ).pack(pady=(5, 0), padx=20, anchor="w")

        ctk.CTkLabel(
            self, 
            text="Os seguintes programas não estão rodando:", 
            font=("Arial", 12),
            text_color="black"
        ).pack(anchor="w", padx=20)

        # --- LISTA VISUAL (ÍCONE + TEXTO) ---
        # Container para a lista
        frame_lista = ctk.CTkFrame(self, fg_color="white")
        frame_lista.pack(fill="both", expand=True, padx=10, pady=5)

        for nome in ausentes:
            # Cria uma linha para cada item
            row = ctk.CTkFrame(frame_lista, fg_color="transparent", height=30)
            row.pack(fill="x", pady=2)
            
            # Tenta pegar o ícone (precisamos do path que está na config)
            path = config_data.processos.get(nome, {}).get("path")
            icone = icon_manager.carregar(nome, path)

            # 1. Ícone
            lbl_icon = ctk.CTkLabel(row, text="", image=icone, width=30)
            lbl_icon.pack(side="left", padx=(5, 10))

            # 2. Nome em Negrito
            lbl_nome = ctk.CTkLabel(
                row, 
                text=nome, 
                font=("Arial", 13, "bold"), # Negrito aqui
                text_color="black"
            )
            lbl_nome.pack(side="left")

        # --- RODAPÉ COM BOTÕES ---
        frame_btns = ctk.CTkFrame(self, fg_color="transparent")
        frame_btns.pack(side="bottom", fill="x", padx=20, pady=(0,12))

        # Cancelar
        ctk.CTkButton(
            frame_btns, text="Cancelar", font=("Arial", 12),
            fg_color="#ef5350", hover_color="#d32f2f",
            width=80, height=32, command=self.on_sair
        ).pack(side="left")

        frame_acoes = ctk.CTkFrame(frame_btns, fg_color="transparent")
        frame_acoes.pack(side="right")

        # Iniciar mesmo assim
        ctk.CTkButton(
            frame_acoes, text="Iniciar mesmo assim", font=("Arial", 12),
            fg_color="transparent", border_width=1, border_color="gray", text_color="gray",
            hover_color="#f5f5f5", width=130, height=32, command=self.on_ignorar
        ).pack(side="left", padx=(0, 10))

        # Forçar
        ctk.CTkButton(
            frame_acoes, text="Forçar Início", font=("Arial", 12, "bold"),
            fg_color="green", hover_color="darkgreen",
            width=110, height=32, command=self.on_forcar
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

class WatchdogApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WatchdogApp - Petrosoft")
        self.geometry("950x650")

        try:
            # Ajuste o caminho conforme onde você salvou o arquivo
            caminho_icone = SystemUtils.resource_path(os.path.join("assets/icons", "app_icon.ico"))
            if os.path.exists(caminho_icone):
                self.iconbitmap(caminho_icone)
        except Exception as e:
            print(f"Erro ao carregar ícone: {e}")
        
        self.bind("<Unmap>", self._ao_minimizar)
        self.tray_icon = None

        self.withdraw() 
        self._exibir_splash()

        # Inicializa Infra e Serviços
        self.icon_manager = IconeManager()
        self.config_data = PersistenceRepository.carregar()
        self.log_manager = LogManager()
        
        # Limpeza automática de logs velhos
        threading.Thread(target=self.log_manager.limpar_antigos, args=(self.config_data.dias_log,), daemon=True).start()
       
        self.engine = WatchdogEngine(self.config_data, self.registrar_log)
        
        # Estado UI
        self.item_selecionado = None
        self.botoes_para_atualizar = []
        self.linhas_visuais = [] 
        self.opcoes_tempo = {
            "5 segundos": 5, "10 segundos": 10, "30 segundos": 30,
            "1 minuto": 60, "2 minutos": 120, "5 minutos": 300
        }
        
        
        self._setup_layout()

        # Se tiver histórico anterior, insere na tela
        historico_hoje = self.log_manager.ler_conteudo_dia()
        self.log_text.configure(state="normal")
        if historico_hoje:
            self.log_text.insert("end", historico_hoje)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
        # Carrega dados na tela
        self._popular_lista_monitoramento()
        self.after(200, self.listar_processos_ativos)

    def _exibir_splash(self):
        splash = ctk.CTkToplevel(self)
        
        # Dimensões exatas
        largura = 400
        altura = 300
        
        # Centralizar na tela
        screen_x = self.winfo_screenwidth()
        screen_y = self.winfo_screenheight()
        pos_x = (screen_x // 2) - (largura // 2)
        pos_y = (screen_y // 2) - (altura // 2)
        
        splash.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")
        splash.overrideredirect(True) # Remove bordas e barra de título
        splash.attributes("-topmost", True) # Mantém no topo
        
        # Carregar Imagem
        try:
            # Substitua 'logo.png' pelo nome exato do seu arquivo
            caminho_img = SystemUtils.resource_path(os.path.join("assets/icons", "logo.png")) 
            
            if os.path.exists(caminho_img):
                pil_img = Image.open(caminho_img)
                
                # Força a imagem a ter exatamente o tamanho da janela (esticar/preencher)
                pil_img = pil_img.resize((largura, altura), Image.Resampling.LANCZOS)
                
                # Cria o objeto CTkImage
                img_splash = ctk.CTkImage(
                    light_image=pil_img, 
                    dark_image=pil_img, 
                    size=(largura, altura)
                )
                
                # Label ocupando tudo (sem padding, sem texto)
                lbl = ctk.CTkLabel(splash, text="", image=img_splash)
                lbl.pack(fill="both", expand=True)
            else:
                # Fallback: Tela preta se não achar a imagem
                lbl = ctk.CTkLabel(splash, text="LOGO NOT FOUND", fg_color="black", text_color="white")
                lbl.pack(fill="both", expand=True)
                
        except Exception as e:
            print(f"Erro Splash: {e}")

        # Função para fechar a splash e abrir o app
        def fechar_splash():
            splash.destroy()
            self.deiconify() # Mostra a janela principal
            
            # Executa a listagem inicial de processos após a splash sumir
            self.after(200, self.listar_processos_ativos)

        # Define quanto tempo a imagem fica na tela (ex: 3000ms = 3 segundos)
        self.after(1500, fechar_splash)

    def _setup_layout(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_monitor = self.tabview.add("Monitoramento")
        self.tab_log = self.tabview.add("Logs")
        self.tab_config = self.tabview.add("Configurações")
        
        self._setup_aba_monitor()
        self._setup_aba_log()
        self._setup_aba_config()

    # --- ABA MONITORAMENTO ---
    def _setup_aba_monitor(self):
        # Lado Esquerdo (Busca)
        frame_left = ctk.CTkFrame(self.tab_monitor)
        frame_left.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(frame_left, text="Processos Ativos", font=("Arial", 16, "bold")).pack(pady=5)
        self.entry_busca = ctk.CTkEntry(frame_left, placeholder_text="Buscar...")
        self.entry_busca.pack(fill="x", padx=10)
        self.entry_busca.bind("<KeyRelease>", lambda e: self.listar_processos_ativos())
        
        self.scroll_ativos = ctk.CTkScrollableFrame(frame_left, bg_color="white", fg_color="white")
        self.scroll_ativos.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Botões de Ação
        frame_btns = ctk.CTkFrame(frame_left, fg_color="transparent")
        frame_btns.pack(fill="x", padx=10)
        
        ctk.CTkButton(frame_btns, image=self.icon_manager._icons.get("refresh"), text="Atualizar", width=100, height=32, command=self.listar_processos_ativos).pack(side="left", padx=2, expand=True, fill="x")
        
        # CORREÇÃO 1: Atribuindo o botão à variável self.btn_add
        self.btn_add = ctk.CTkButton(
            frame_btns, 
            image=self.icon_manager._icons.get("add"), 
            text="Monitorar", 
            width=100,
            height=32,
            fg_color="green", 
            command=self.adicionar_ao_monitor
        )
        self.btn_add.pack(side="left", padx=2, expand=True, fill="x")

        # Lado Direito (Lista de Monitoramento)
        frame_right = ctk.CTkFrame(self.tab_monitor)
        frame_right.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(frame_right, text="Lista de Monitoramento", font=("Arial", 16, "bold")).pack(pady=(5,8))
        
        # Header da tabela
        h_frame = ctk.CTkFrame(frame_right, height=30, fg_color="transparent")
        h_frame.pack(fill="x", padx=10, pady=(2,0))
        ctk.CTkLabel(h_frame, text="Processo", font=("Arial", 12, "bold"), width=170, anchor="w").pack(side="left")
        ctk.CTkLabel(h_frame, text="Regra", font=("Arial", 12, "bold"), width=150, anchor="w").pack(side="left", padx=10)

        # Scroll da lista
        self.scroll_monitor = ctk.CTkScrollableFrame(frame_right, fg_color="#fafafa", bg_color="#fafafa")
        self.scroll_monitor.pack(fill="both", expand=True)
        
        self.btn_start = ctk.CTkButton(frame_right, image=self.icon_manager._icons.get("play"), text="INICIAR MONITORAMENTO", height=32, command=self.toggle_monitor)
        self.btn_start.pack(side="bottom", padx=5, fill="x",pady=(5,0))
        
    # --- LÓGICA DE UI ---
    def listar_processos_ativos(self):
        for w in self.scroll_ativos.winfo_children(): w.destroy()
        self.botoes_para_atualizar = []
        
        grupos = SystemUtils.listar_processos_agrupados(self.entry_busca.get())
        
        self._renderizar_grupo("APLICATIVOS", grupos["apps"], "#1f538d")
        self._renderizar_grupo("SEGUNDO PLANO", grupos["back"], "#2e7d32")
        self._renderizar_grupo("SISTEMA", grupos["system"], "#666666")
        
        threading.Thread(target=self._carregar_icones_bg, daemon=True).start()

    def _renderizar_grupo(self, titulo, dados, cor):
        if not dados: return
        ctk.CTkLabel(self.scroll_ativos, text=titulo, anchor="w", font=("Arial", 12, "bold"), text_color=cor).pack(fill="x", pady=(5,0))
        
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
        # Frame da linha
        row_frame = ctk.CTkFrame(self.scroll_monitor, fg_color="white", corner_radius=6)
        row_frame.pack(fill="x", pady=2, padx=5)
        
        # CORREÇÃO 2: Adiciona este frame à lista de controle visual
        self.linhas_visuais.append(row_frame)
        
        def on_enter(e):
            try: row_frame.configure(fg_color="#f5f5f5")
            except: pass
        
        def on_leave(e):
            try: row_frame.configure(fg_color="white")
            except: pass
        
        icone = self.icon_manager.carregar(nome, path)
        
        lbl_nome = ctk.CTkLabel(row_frame, text=f"   {nome}", image=icone, compound="left", width=150, anchor="w", font=("Arial", 12), text_color="black")
        lbl_nome.pack(side="left", padx=10, pady=5)
        lbl_nome.bind("<Enter>", on_enter)
        lbl_nome.bind("<Leave>", on_leave)
        
        opcoes = ["Não Reiniciar", "Sempre Reiniciar", "Reiniciar se erro Windows"]
        combo_regra = ctk.CTkOptionMenu(
            row_frame, 
            values=opcoes, 
            width=190,
            height=28,
            fg_color="#f0f0f0",
            button_color="#e0e0e0",
            button_hover_color="#d0d0d0",
            text_color="black",
            dropdown_fg_color="white",
            dropdown_text_color="black",
            dropdown_hover_color="#e0e0e0",
            command=lambda r, n=nome: self._atualizar_regra(n, r)
        )
        combo_regra.set(regra)
        combo_regra.pack(side="left", padx=10)

        btn_remover = ctk.CTkButton(
            row_frame, text='✕', width=30, height=28, 
            fg_color="#c62828", hover_color="#b71c1c",
            command=lambda: self._remover_processo(nome, row_frame)
        )
        btn_remover.pack(side="right", padx=10)

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
                self.wait_window(dialogo)

                escolha = dialogo.resultado

                if escolha == "cancelar":
                        return
                elif escolha == "forcar":
                    self.registrar_log("❗ Tentando forçar inicialização dos processos...")
                    self._forcar_inicializacao(ausentes)
                elif escolha == "ignorar":
                        self.registrar_log("❗ Iniciar monitoramento mesmo com processos ausentes") 

            self.engine.iniciar()
            PersistenceRepository.salvar(self.config_data)
            
            self.btn_start.configure(image=self.icon_manager._icons.get("stop"), text="PARAR MONITORAMENTO", height=32, fg_color="orange")
            self._definir_estado_edicao("disabled")
        
        else:
            # PARAR
            self.engine.parar()
            
            self.btn_start.configure(image=self.icon_manager._icons.get("play"), text="INICIAR MONITORAMENTO", height=32, fg_color="#1f538d")
            self._definir_estado_edicao("normal")
    
    def _forcar_inicializacao(self, lista_nomes):
        """ Tenta abrir os executáveis que estão faltando """
        for nome in lista_nomes:
            path = self.config_data.processos[nome].get("path")
            if path and os.path.exists(path):
                try:
                    subprocess.Popen(path)
                    self.registrar_log(f" > Iniciado manualmente: {nome}")
                except Exception as e:
                    self.registrar_log(f" > Erro ao iniciar {nome}: {e}")
            else:
                self.registrar_log(f" > Impossível iniciar {nome}: Caminho não encontrado.")

    def _definir_estado_edicao(self, estado):
        """
        Bloqueia (disabled) ou Desbloqueia (normal) a interface de edição.
        """
        # 1. Bloqueia botão de adicionar (Agora funciona pois atribuímos self.btn_add)
        if hasattr(self, 'btn_add'):
            if(estado=="disabled"):
                self.btn_add.configure(state=estado, fg_color="#004d00")
            else: 
                self.btn_add.configure(state=estado, fg_color="green")
            

        # 2. Bloqueia as linhas usando a lista confiável self.linhas_visuais
        for frame_linha in self.linhas_visuais:
            # Itera sobre os filhos de CADA LINHA (isso o tkinter garante que funciona)
            for widget in frame_linha.winfo_children():
                if isinstance(widget, (ctk.CTkOptionMenu, ctk.CTkButton)):
                    # Não bloqueia Labels, apenas interativos
                    try: widget.configure(state=estado)
                    except: pass

    def registrar_log(self, msg, com_hora=True):
        """
        Registra o log.
        Uso:
            self.registrar_log("Texto com hora por padrão") -> Imprime "[14:30:00] Texto com hora por padrão.
            self.registrar_log("Texto simples", com_hora=False) -> "Texto simples"
        """
        
        texto_final = msg

        # Se solicitado, adiciona o carimbo de tempo automaticamente
        if com_hora:
            hora = datetime.now().strftime('%H:%M:%S')
            texto_final = f"[{hora}] {msg}"

        # 1. Salva no Disco (usando o texto processado)
        self.log_manager.escrever(texto_final)

        # 2. Atualiza a UI
        def _inserir():
            # Verifica se a janela ainda existe antes de tentar escrever
            try:
                if not self.winfo_exists(): return
                
                self.log_text.configure(state="normal")
                self.log_text.insert("end", texto_final + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
            except: pass
        
        self.after(0, _inserir)

    # --- ABA LOGS ---
    def _setup_aba_log(self):
        self.log_text = ctk.CTkTextbox(self.tab_log, font=("Consolas", 12), state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Barra de Ferramentas (Toolbar)
        frame_tools = ctk.CTkFrame(self.tab_log, fg_color="transparent", height=40)
        frame_tools.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkButton(
            frame_tools, 
            text="Salvar em Arquivo", 
            width=140, 
            height=32,
            fg_color="#1f538d",
            command=self._salvar_log
        ).pack(side="right", padx=(0, 5))
       
        ctk.CTkButton(
            frame_tools, 
            text="Copiar Tudo", 
            width=120, 
            height=32,
            fg_color="gray", 
            command=self._copiar_log
        ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            frame_tools, 
            text="Limpar", 
            width=100, 
            height=32,
            fg_color="#c62828", 
            hover_color="#b71c1c",
            command=self._limpar_log
        ).pack(side="left")
        
    # --- AÇÕES DOS BOTÕES DE LOG ---
    def _salvar_log(self):
        """ Exporta o conteúdo atual para um arquivo .txt """
        conteudo = self.log_text.get("1.0", "end").strip()
        if not conteudo:
            messagebox.showinfo("Logs", "O log está vazio.")
            return

        agora = datetime.now().strftime("%d-%m-%Y-%H-%M")
        nome_sugerido= f"Registro de Monitoramento {agora}"

        path = filedialog.asksaveasfilename(
            initialfile=nome_sugerido,
            defaultextension=".txt",
            filetypes=[("Arquivo de Texto", "*.txt"), ("Todos os Arquivos", "*.*")],
            title="Salvar Log de Monitoramento"
        )
        
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(conteudo)
                messagebox.showinfo("Sucesso", "Log salvo com sucesso!")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar: {e}")

    def _copiar_log(self):
        """ Copia todo o log para a área de transferência """
        conteudo = self.log_text.get("1.0", "end")
        if conteudo.strip():
            self.clipboard_clear()
            self.clipboard_append(conteudo)
            self.update() # Necessário para efetivar a cópia no Windows
            
            # Feedback visual rápido no botão (opcional, mas elegante)
            self.registrar_log("ℹ️ Conteúdo copiado para a área de transferência.")
        else:
            messagebox.showinfo("Logs", "Nada para copiar.")

    def _limpar_log(self):
        """ Limpa a tela de logs """
        self.log_text.configure(state="normal") # Destrava para apagar
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled") # Trava de novo

    # --- ABA CONFIG ---
    def _setup_aba_config(self):
        frame_config = ctk.CTkFrame(self.tab_config, fg_color="transparent")
        frame_config.pack(fill="both", expand=True, padx=20, pady=20)

        
        # --- Configuração 1: Inicialização com Windows ---
        ctk.CTkLabel(frame_config, text="Sistema", font=("Arial", 16, "bold")).pack(pady=(0, 5), anchor="w")
        
        self.switch_startup = ctk.CTkSwitch(
            frame_config,
            text="Iniciar junto com o Windows",
            command=self._alterar_startup,
            onvalue=True,
            offvalue=False,
            button_color="#1f538d",
        )
        
        # Carrega o estado atual
        if self.config_data.iniciar_com_windows:
            self.switch_startup.select()
        else:
            self.switch_startup.deselect()
            
        self.switch_startup.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(
            frame_config, 
            text="Adiciona o programa ao registro do sistema para abrir automaticamente ao ligar o PC.", 
            font=("Arial", 11), 
            text_color="gray"
        ).pack(anchor="w")

        self.switch_tray = ctk.CTkSwitch(
            frame_config,
            text="Minimizar para a Bandeja (Tray)",
            command=self._alterar_tray_mode,
            onvalue=True,
            offvalue=False,
            button_color="#1f538d",
        )
        # Carrega estado salvo
        if self.config_data.minimizar_para_tray:
            self.switch_tray.select()
        else:
            self.switch_tray.deselect()
            
        self.switch_tray.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(
            frame_config, 
            text="Ao minimizar, o programa ficará oculto perto do relógio do Windows.", 
            font=("Arial", 11), 
            text_color="gray"
        ).pack(anchor="w")

        ctk.CTkFrame(frame_config, height=2, fg_color="#e0e0e0").pack(fill="x", pady=5)

        ctk.CTkLabel(frame_config, text="Ajustes do Monitor", font=("Arial", 16, "bold")).pack(pady=(0, 5), anchor="w")
        
        # --- Configuração 2: Ciclo de Verificação ---
        ctk.CTkLabel(frame_config, text="Ciclo de Verificação:", font=("Arial", 13)).pack(anchor="w")

        self.combo_intervalo = ctk.CTkOptionMenu(
            frame_config,
            values=list(self.opcoes_tempo.keys()),
            command=self._alterar_intervalo,
            width=200
        )
        
        tempo_atual = self.config_data.intervalo
        texto_inicial = "5 segundos"
        for texto, seg in self.opcoes_tempo.items():
            if seg == tempo_atual:
                texto_inicial = texto
                break
        self.combo_intervalo.set(texto_inicial)
        self.combo_intervalo.pack(anchor="w", pady=10)

        ctk.CTkLabel(
            frame_config, 
            text="Intervalo para realização de verificação dos status dos programas adicionados a lista.", 
            font=("Arial", 11), 
            text_color="gray"
        ).pack(anchor="w")

        # --- Configuração 3: Histórico de Logs ---
        ctk.CTkLabel(frame_config, text="Histórico de Logs (Dias):", font=("Arial", 13)).pack(anchor="w")
        
        # Label que mostra o valor atual dinamicamente
        self.lbl_dias_valor = ctk.CTkLabel(frame_config, text=f"{self.config_data.dias_log} dias", font=("Arial", 12, "bold"), text_color="#1f538d")
        self.lbl_dias_valor.pack(anchor="w", padx=2)

        # Slider (1 a 30 dias)
        self.slider_dias = ctk.CTkSlider(
            frame_config,
            from_=1,
            to=30,
            number_of_steps=29, # Garante que ande de 1 em 1
            width=300,
            command=self._alterar_dias_log
        )
        self.slider_dias.set(self.config_data.dias_log)
        self.slider_dias.pack(anchor="w", pady=5)
        
        ctk.CTkLabel(
            frame_config, 
            text="Arquivos de log mais antigos que o limite serão apagados automaticamente.", 
            font=("Arial", 11), 
            text_color="gray"
        ).pack(anchor="w")
    
        # --- Configuração 4: Checagem de Rotina (Heartbeat) ---
        ctk.CTkLabel(frame_config, text="Relatório de Rotina (Check-up):", font=("Arial", 13)).pack(anchor="w", pady=(15, 0))
        
        self.combo_heartbeat = ctk.CTkOptionMenu(
            frame_config,
            values=[f"{h} horas" for h in [2, 4, 6, 8, 12, 24, 48]],
            command=self._alterar_heartbeat,
            width=200
        )
        
        # Define o valor atual
        atual = self.config_data.intervalo_heartbeat
        self.combo_heartbeat.set(f"{atual} horas")
        self.combo_heartbeat.pack(anchor="w", pady=5)

        ctk.CTkLabel(
            frame_config, 
            text="Gera um registro no log confirmando que os programas estão rodando, mesmo se não houver falhas.", 
            font=("Arial", 11), 
            text_color="gray"
        ).pack(anchor="w")

    def _alterar_intervalo(self, escolha):
        novo_tempo = self.opcoes_tempo.get(escolha, 5)
        self.config_data.intervalo = novo_tempo
        PersistenceRepository.salvar(self.config_data)
        self.registrar_log(f"ℹ️ Configuração: Ciclo de Verificação alterado para {novo_tempo}s.")

    def _alterar_dias_log(self, valor):
        """ Callback do Slider """
        dias = int(valor)
        self.lbl_dias_valor.configure(text=f"{dias} dias") # Atualiza label visual
        
        # Só salva se mudou (o slider dispara muitos eventos enquanto arrasta)
        if dias != self.config_data.dias_log:
            self.config_data.dias_log = dias
            PersistenceRepository.salvar(self.config_data)
            
            # Opcional: Acionar limpeza imediata ao reduzir os dias
            threading.Thread(target=self.log_manager.limpar_antigos, args=(dias,), daemon=True).start()
            self.registrar_log(f"ℹ️ Configuração: Histórico de Logs alterado para {dias} dias.")
    
    def _alterar_heartbeat(self, escolha):
        # Extrai apenas o número da string "4 horas" -> 4
        horas = int(escolha.split()[0])
        self.config_data.intervalo_heartbeat = horas
        PersistenceRepository.salvar(self.config_data)
        self.registrar_log(f"ℹ️ Configuração: Relatório de Rotina definido para cada {horas} horas.")

    def _alterar_startup(self):
        """ Callback do Switch """
        ativar = self.switch_startup.get() # 1 (True) ou 0 (False)
        
        # 1. Tenta alterar no Windows
        sucesso = SystemUtils.definir_inicializacao_windows(bool(ativar))
        
        if sucesso:
            # 2. Se deu certo, salva na config interna
            self.config_data.iniciar_com_windows = bool(ativar)
            PersistenceRepository.salvar(self.config_data)
            
            status = "ATIVADA" if ativar else "DESATIVADA"
            self.registrar_log(f"ℹ️ Configuração: Inicialização com windows {status}.")
        else:
            # Se falhou (permissão, antivirus, etc), reverte o switch visualmente
            messagebox.showerror("Erro", "Falha ao alterar registro do Windows.\nTente executar como Administrador.")
            if ativar: self.switch_startup.deselect()
            else: self.switch_startup.select()

    def _alterar_tray_mode(self):
        """ Salva a preferência do usuário """
        valor = self.switch_tray.get() # 1 ou 0
        self.config_data.minimizar_para_tray = bool(valor)
        PersistenceRepository.salvar(self.config_data)

    # --- LÓGICA DO TRAY ---
    def _ao_minimizar(self, event):
        # Verifica se o widget que disparou o evento é a janela principal
        if str(event.widget) == ".":
            # Verifica se está minimizado ('iconic') e se a config está ativa
            if self.state() == "iconic" and self.config_data.minimizar_para_tray:
                self.withdraw() # Esconde a janela da barra de tarefas
                self._criar_tray_icon()

    def _criar_tray_icon(self):
        if self.tray_icon: return # Já existe

        # Define a imagem do ícone (Tenta pegar o .ico ou .png da pasta assets)
        image = None
        try:
            path_ico = SystemUtils.resource_path(os.path.join("assets/icons", "app_icon.ico"))
            path_png = SystemUtils.resource_path(os.path.join("assets/icons", "logo.png"))
            
            if os.path.exists(path_ico):
                image = Image.open(path_ico)
            elif os.path.exists(path_png):
                image = Image.open(path_png)
        except: pass
        
        # Fallback: Cria uma imagem colorida simples se não achar arquivo
        if not image:
            image = Image.new('RGB', (64, 64), color = (31, 83, 141))

        # Cria o menu do botão direito
        menu = (
            item('Abrir WatchdogApp', self._restaurar_janela, default=True),
            item('Encerrar', self._sair_total)
        )

        self.tray_icon = pystray.Icon("WatchdogApp", image, "WatchdogApp", menu)
        # Roda em thread separada para não travar a UI do Tkinter
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _restaurar_janela(self, icon=None, item=None):
        """ Chamado ao clicar no ícone do Tray """
        if self.tray_icon:
            self.tray_icon.stop() # Remove o ícone da bandeja
            self.tray_icon = None
        
        self.after(0, self._mostrar_janela_safe)

    def _mostrar_janela_safe(self):
        """ Executa na thread principal do Tkinter """
        self.deiconify() # Traz de volta
        self.state("normal") # Garante que não está mais minimizada
        self.lift() # Traz para frente
        self.focus_force()

    def _sair_total(self, icon=None, item=None):
        """ Fecha tudo pelo Tray """
        if self.tray_icon:
            self.tray_icon.stop()
        self.engine.parar() # Para o loop de monitoramento
        self.quit()