import os
import customtkinter as ctk
import threading
from tkinter import messagebox
from PIL import Image
from pystray import MenuItem as item
import pystray
from ...infrastructure.system_utils import SystemUtils

class ConfigTab(ctk.CTkFrame):
    def __init__(self, parent, config_data, persistence_repo, log_callback, log_manager):
        super().__init__(parent, fg_color="transparent")
        self.config_data = config_data
        self.persistence = persistence_repo
        self.log = log_callback
        self.log_manager = log_manager # Para limpeza
        self.opcoes_tempo = {
            "5 segundos": 5, "10 segundos": 10, "30 segundos": 30,
            "1 minuto": 60, "2 minutos": 120, "5 minutos": 300
        }
        self._setup_ui()

    def _setup_ui(self):
        # ===============================================================
        # BLOCO 1: SISTEMA (Inicialização e Tray)
        # ===============================================================
        self.frame_sys = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_sys.pack(fill="x", padx=10, pady=(10, 5))

        # Título da Seção
        ctk.CTkLabel(self.frame_sys, text="SISTEMA", font=("Arial", 14, "bold"), text_color="#1f538d").pack(anchor="w", padx=5)
        
        # Container Grid (2 Colunas)
        grid_sys = ctk.CTkFrame(self.frame_sys, fg_color=["#e8e8e8", "#2b2b2b"]) # Cor de fundo sutil
        grid_sys.pack(fill="x", pady=5)
        grid_sys.grid_columnconfigure((0, 1), weight=1) # Colunas com peso igual

        # --- Coluna 0: Inicializar com Windows ---
        self.mode_button_startup = "disabled"
        self.switch_startup = ctk.CTkSwitch(
            grid_sys, text="Iniciar com o Windows", font=("Arial", 12, "bold"),
            command=self._alterar_startup, onvalue=True, offvalue=False, button_color="#1f538d",
        )
        if self.config_data.iniciar_com_windows: self.switch_startup.select()
        self.switch_startup.grid(row=0, column=0, sticky="w", padx=20, pady=15)
        # Legenda na Linha 1
        ctk.CTkLabel(
            grid_sys, 
            text="Adiciona o programa ao registro do sistema para abrir automaticamente ao ligar o PC.", 
            font=("Arial", 11), 
            text_color="gray",
            wraplength=350,
            justify="left",
            anchor="n"
        ).grid(row=1, column=0, sticky="w", padx=20)

        # --- Coluna 1: Bandeja (Tray) ---
        self.switch_tray = ctk.CTkSwitch(
            grid_sys, text="Minimizar para Bandeja", font=("Arial", 12, "bold"), 
            command=self._alterar_tray_mode, onvalue=True, offvalue=False
        )
        if self.config_data.minimizar_para_tray: self.switch_tray.select()
        self.switch_tray.grid(row=0, column=1, sticky="w", padx=20, pady=15)
        ctk.CTkLabel(
            grid_sys, 
            text="Ao minimizar, o programa ficará oculto perto do relógio do Windows.", 
            font=("Arial", 11), 
            text_color="gray",
            wraplength=350,
            justify="left",
            anchor="n"
        ).grid(row=1, column=1, sticky="w", padx=20)

        # Separador visual
        ctk.CTkFrame(grid_sys, height=2, fg_color="gray").grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        
        # # Frame Container Principal da Automação
        f_auto = ctk.CTkFrame(grid_sys, fg_color="transparent")
        f_auto.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=(10, 15))

        f_linha_controles = ctk.CTkFrame(f_auto, fg_color="transparent")
        f_linha_controles.pack(fill="x", anchor="w")

        # Switch Retomar Monitoramento
        self.switch_persistir = ctk.CTkSwitch(
            f_linha_controles, 
            text="Retomar Monitoramento",
            font=("Arial", 12, "bold"),
            command=self._salvar_automacao, 
            onvalue=True, 
            offvalue=False,
            button_color="#1f538d",
        )
        if self.config_data.persistir_monitoramento: self.switch_persistir.select()
        self.switch_persistir.pack(side="left")

        # Delay 
        self.lbl_delay = ctk.CTkLabel(f_linha_controles, text="Delay:", font=("Arial", 12, "bold"))
        self.lbl_delay.pack(side="left", padx=(20, 5))
        self.combo_delay = ctk.CTkOptionMenu(
            f_linha_controles, 
            width=70, 
            values=["5s", "10s", "30s", "60s"], 
            command=self._salvar_automacao
        )
        self.combo_delay.set(f"{self.config_data.delay_inicializacao}s")
        self.combo_delay.pack(side="left")

        # Linha Inferior: Descrição
        ctk.CTkLabel(
            f_auto,
            text="Ao reiniciar o Windows, retoma o monitoramento após o tempo definido no Delay (aguarda os processos iniciarem).", 
            font=("Arial", 11), 
            text_color="gray",
            wraplength=450, # Quebra o texto se for muito longo
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # Condição para Processos Ausentes
        f_sub_auto = ctk.CTkFrame(grid_sys, fg_color="transparent")
        f_sub_auto.grid(row=3, column=1, sticky="nsew", padx=15)
        
        self.lbl_sub_auto = ctk.CTkLabel(f_sub_auto, text="Se processos ausentes:", font=("Arial", 12, "bold"))
        self.lbl_sub_auto.pack(anchor="w", pady=(5,0))
        self.radio_var = ctk.StringVar(value=self.config_data.acao_ao_iniciar)
        ctk.CTkRadioButton(f_sub_auto, text="Ignorar", variable=self.radio_var, value="ignorar", command=self._salvar_automacao).pack(anchor="w", pady=(0,2))
        ctk.CTkRadioButton(f_sub_auto, text="Forçar Início", variable=self.radio_var, value="forcar", command=self._salvar_automacao).pack(anchor="w")

        if not self.config_data.iniciar_com_windows:
            self.switch_persistir.configure(state="disabled")
            self.combo_delay.configure(state="disabled")
            self.lbl_delay.configure(text_color="#999999")
            self.lbl_sub_auto.configure(text_color="#999999")
            self.radio_var.set(value="ignorar")
            
        # ===============================================================
        # BLOCO 2: MONITOR (Comportamento do Motor e Automação)
        # ===============================================================
        self.frame_mon = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_mon.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(self.frame_mon, text="MONITOR", font=("Arial", 14, "bold"), text_color="#1f538d").pack(anchor="w", padx=5)

        # Container Grid (2 Colunas)
        grid_mon = ctk.CTkFrame(self.frame_mon, fg_color=["#e8e8e8", "#2b2b2b"])
        grid_mon.pack(fill="both", expand=True, pady=5)
        grid_mon.grid_columnconfigure((0, 1), weight=1)

        # --- LINHA 1: Intervalos Básicos ---
        
        # Coluna 0: Ciclo de Verificação
        f_ciclo = ctk.CTkFrame(grid_mon, fg_color="transparent")
        f_ciclo.grid(row=0, column=0, sticky="nsew", padx=15, pady=10)
        ctk.CTkLabel(f_ciclo, text="Ciclo de Verificação:", font=("Arial", 12, "bold")).pack(anchor="w")

        self.combo_intervalo = ctk.CTkOptionMenu(f_ciclo, values=list(self.opcoes_tempo.keys()), command=self._alterar_intervalo)
        self._set_combo_inicial(self.combo_intervalo, self.config_data.intervalo, self.opcoes_tempo)
        self.combo_intervalo.pack(anchor="w", pady=5)
        ctk.CTkLabel(
            f_ciclo, 
            text="Intervalo para realização de verificação dos status dos programas adicionados a lista.", 
            font=("Arial", 11), 
            text_color="gray",
            wraplength=450,
            justify="left",
            anchor="n"
        ).pack(anchor="w")

        # Coluna 1: Heartbeat (Rotina)
        f_heart = ctk.CTkFrame(grid_mon, fg_color="transparent")
        f_heart.grid(row=0, column=1, sticky="nsew", padx=15, pady=10)
        ctk.CTkLabel(f_heart, text="Relatório de Rotina:", font=("Arial", 12, "bold")).pack(anchor="w")
        
        self.combo_heartbeat = ctk.CTkOptionMenu(f_heart, values=[f"{h} horas" for h in [2, 4, 6, 8, 12, 24]], command=self._alterar_heartbeat)
        self.combo_heartbeat.set(f"{self.config_data.intervalo_heartbeat} horas")
        self.combo_heartbeat.pack(anchor="w", pady=5)

        ctk.CTkLabel(
            f_heart, 
            text="Gera um registro no log confirmando que os programas estão rodando, mesmo se não houver falhas.", 
            font=("Arial", 11), 
            text_color="gray",
            wraplength=450,
            justify="left"
        ).pack(anchor="w")

        
        # --- LINHA 2: Logs e Automação ---

        # Coluna 0: Histórico de Logs
        f_logs = ctk.CTkFrame(grid_mon, fg_color="transparent")
        f_logs.grid(row=2, column=0, sticky="nsew", padx=15, pady=10)
        
        self.lbl_dias = ctk.CTkLabel(f_logs, text=f"Histórico de Logs: {self.config_data.dias_log} dias", font=("Arial", 12, "bold"))
        self.lbl_dias.pack(anchor="w")
        
        self.slider_dias = ctk.CTkSlider(f_logs, from_=1, to=30, number_of_steps=29, command=self._alterar_dias_log)
        self.slider_dias.set(self.config_data.dias_log)
        self.slider_dias.pack(fill="x", pady=5)
        ctk.CTkLabel(
            f_logs,
            text="Arquivos de log mais antigos que o limite serão apagados automaticamente.", 
            font=("Arial", 11), 
            text_color="gray",
            wraplength=450,
            justify="left"
        ).pack(anchor="w")

    def _set_combo_inicial(self, combo, valor_atual, opcoes):
        texto = "5 segundos"
        for k, v in opcoes.items():
            if v == valor_atual:
                texto = k
                break
        combo.set(texto)
    
    def _alterar_intervalo(self, escolha):
        novo_tempo = self.opcoes_tempo.get(escolha, 5)
        self.config_data.intervalo = novo_tempo
        self.persistence.salvar(self.config_data)
        self.log(f"ℹ️ Configuração: Ciclo de Verificação alterado para {novo_tempo}s.")

    def _alterar_dias_log(self, valor):
        """ Callback do Slider """
        dias = int(valor)
        self.lbl_dias_valor.configure(text=f"{dias} dias") # Atualiza label visual
        
        # Só salva se mudou (o slider dispara muitos eventos enquanto arrasta)
        if dias != self.config_data.dias_log:
            self.config_data.dias_log = dias
            self.persistence.salvar(self.config_data)
            
            # Opcional: Acionar limpeza imediata ao reduzir os dias
            threading.Thread(target=self.log_manager.limpar_antigos, args=(dias,), daemon=True).start()
            self.log(f"ℹ️ Configuração: Histórico de Logs alterado para {dias} dias.")
    
    def _alterar_heartbeat(self, escolha):
        # Extrai apenas o número da string "4 horas" -> 4
        horas = int(escolha.split()[0])
        self.config_data.intervalo_heartbeat = horas
        self.persistence.salvar(self.config_data)
        self.log(f"ℹ️ Configuração: Relatório de Rotina definido para cada {horas} horas.")

    def _alterar_startup(self):
        """ Callback do Switch """
        ativar = self.switch_startup.get() # 1 (True) ou 0 (False)
        
        # 1. Tenta alterar no Windows
        sucesso = SystemUtils.definir_inicializacao_windows(bool(ativar))
        
        if sucesso:
            # 2. Se deu certo, salva na config interna
            self.config_data.iniciar_com_windows = bool(ativar)
            self.persistence.salvar(self.config_data)
            
            status = "ATIVADA" if ativar else "DESATIVADA"
            self.log(f"ℹ️ Configuração: Inicialização com Windows {status}.")

            if hasattr(self, 'switch_persistir'):
                if ativar:
                    # Se ativou o Windows, libera o botão de retomar
                    self.switch_persistir.configure(state="normal")
                    self.combo_delay.configure(state="normal")
                    self.lbl_delay.configure(text_color="black")
                    self.lbl_sub_auto.configure(text_color="black")
                else:
                    # Se desativou o Windows, bloqueia e desmarca o retomar
                    self.switch_persistir.deselect()
                    self.switch_persistir.configure(state="disabled")
                    self.combo_delay.configure(state="disabled")
                    self.lbl_delay.configure(text_color="#999999")
                    self.lbl_sub_auto.configure(text_color="#999999")
                    self.radio_var.set(value="ignorar")
                    
                    # Atualiza a config interna para refletir que foi desmarcado
                    self.config_data.persistir_monitoramento = False
                    self.persistence.salvar(self.config_data)             

        else:
            # Se falhou (permissão, antivirus, etc), reverte o switch visualmente
            messagebox.showerror("Erro", "Falha ao alterar registro do Windows.\nTente executar como Administrador.")
            if ativar: self.switch_startup.deselect()
            else: self.switch_startup.select()
        
        if status == "ATIVADA":
            self.mode_button_startup = "normal"

    def _alterar_tray_mode(self):
        """ Salva a preferência do usuário """
        valor = self.switch_tray.get() # 1 ou 0
        self.config_data.minimizar_para_tray = bool(valor)
        self.persistence.salvar(self.config_data)
        minimize = "ATIVADO" if bool(valor) else "DESATIVADO"
        self.log(f"ℹ️ Configuração: Minimimizar para Bandeja {minimize}")

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
    
    def _salvar_automacao(self, _=None):
        changed = False

        novo_persistir = bool(self.switch_persistir.get())
        if self.config_data.persistir_monitoramento != novo_persistir:
            self.config_data.persistir_monitoramento = novo_persistir
            condicao = "ATIVADO" if novo_persistir else "DESATIVADO"
            self.log(f"ℹ️ Configuração: Retomar Monitoramento {condicao}")
            changed = True

        try:
            novo_delay = int(self.combo_delay.get().replace("s", ""))
            if self.config_data.delay_inicializacao != novo_delay:
                self.config_data.delay_inicializacao = novo_delay
                self.log(f"ℹ️ Configuração: Delay alterado para {novo_delay}s")
                changed = True
        except ValueError:
            pass

        nova_acao = self.radio_var.get()
        if self.config_data.acao_ao_iniciar != nova_acao:
            self.config_data.acao_ao_iniciar = nova_acao
            traducao = "Forçar Início" if nova_acao == "forcar" else "Ignorar"
            self.log(f"ℹ️ Configuração: Ação para ausentes alterada para '{traducao}'")
            changed = True

        if changed:
            self.persistence.salvar(self.config_data)