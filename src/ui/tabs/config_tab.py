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
        frame_config = ctk.CTkFrame(self, fg_color="transparent")
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

        # --- SEÇÃO DE AUTOMAÇÃO ---
        ctk.CTkLabel(frame_config, text="Automação de Reinício", font=("Arial", 16, "bold")).pack(pady=(0, 5), anchor="w")

        # 1. Switch Principal
        self.switch_persistir = ctk.CTkSwitch(
            frame_config, text="Retomar monitoramento ao iniciar app", 
            command=self._salvar_automacao, onvalue=True, offvalue=False, button_color="#1f538d"
        )
        if self.config_data.persistir_monitoramento: self.switch_persistir.select()
        else: self.switch_persistir.deselect()
        self.switch_persistir.pack(anchor="w", pady=5)

        # 2. Delay (Slider ou OptionMenu)
        frame_delay = ctk.CTkFrame(frame_config, fg_color="transparent")
        frame_delay.pack(fill="x", anchor="w")
        
        ctk.CTkLabel(frame_delay, text="Aguardar (Delay):").pack(side="left", padx=(0,10))
        self.combo_delay = ctk.CTkOptionMenu(
            frame_delay, width=100,
            values=["5s", "10s", "30s", "60s", "120s"],
            command=self._salvar_automacao
        )
        self.combo_delay.set(f"{self.config_data.delay_inicializacao}s")
        self.combo_delay.pack(side="left")
        
        ctk.CTkLabel(frame_delay, text="antes de retomar.", text_color="gray", font=("Arial", 11)).pack(side="left", padx=10)

        # 3. Ação para Processos Ausentes
        ctk.CTkLabel(frame_config, text="Se houver processos fechados ao retomar:", font=("Arial", 12)).pack(anchor="w", pady=(10,0))
        
        self.radio_var = ctk.StringVar(value=self.config_data.acao_ao_iniciar)
        
        r1 = ctk.CTkRadioButton(frame_config, text="Ignorar (Monitorar apenas os ativos)", variable=self.radio_var, value="ignorar", command=self._salvar_automacao)
        r1.pack(anchor="w", pady=2)
        
        r2 = ctk.CTkRadioButton(frame_config, text="Tentar Iniciar (Forçar abertura)", variable=self.radio_var, value="forcar", command=self._salvar_automacao)
        r2.pack(anchor="w", pady=2)

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
            self.log(f"ℹ️ Configuração: Inicialização com windows {status}.")
        else:
            # Se falhou (permissão, antivirus, etc), reverte o switch visualmente
            messagebox.showerror("Erro", "Falha ao alterar registro do Windows.\nTente executar como Administrador.")
            if ativar: self.switch_startup.deselect()
            else: self.switch_startup.select()

    def _alterar_tray_mode(self):
        """ Salva a preferência do usuário """
        valor = self.switch_tray.get() # 1 ou 0
        self.config_data.minimizar_para_tray = bool(valor)
        self.persistence.salvar(self.config_data)

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
        self.config_data.persistir_monitoramento = self.switch_persistir.get()
        
        # Tratamento do texto "10s" -> 10
        val_delay = self.combo_delay.get().replace("s", "")
        self.config_data.delay_inicializacao = int(val_delay)
        
        self.config_data.acao_ao_iniciar = self.radio_var.get()
        
        self.persistence.salvar(self.config_data)