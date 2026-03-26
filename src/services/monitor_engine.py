# src/services/monitor_engine.py
import time
import threading
import subprocess
from datetime import datetime
import psutil

from ..infrastructure.system_utils import SystemUtils
from ..infrastructure.process_adapter import ProcessAdapter
from ..domain.process_engine import WatchdogProcessEngine
from .process_use_cases import OSProcessUseCase
from ..infrastructure.service_adapter import ServiceAdapter
from ..domain.service_engine import WatchdogServiceEngine

class WatchdogEngine:
    def __init__(self, config, log_callback, auth_service):
        self.config = config
        self.log_callback = log_callback
        self.auth_service = auth_service
        self.rodando = False
        self._thread_proc = None
        self._thread_serv = None
        self.callback_licenca_expirada = None
        
        self.process_engine = WatchdogProcessEngine()
        self.service_engine = WatchdogServiceEngine()
        
        self.latest_metrics = {}
        self.status_anterior_dict = {}

    def iniciar(self):
        if self.rodando: return
        self.rodando = True
        
        # Dispara as duas threads independentes e simultâneas
        self._thread_proc = threading.Thread(target=self._loop_processos, daemon=True)
        self._thread_serv = threading.Thread(target=self._loop_servicos, daemon=True)
        
        self._thread_proc.start()
        self._thread_serv.start()

    def parar(self):
        self.rodando = False
        now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        self.log_callback(f"\n{'='*15} 🛑 MONITORAMENTO PARADO {'='*15}\n📅 Data: {now}\n{'='*54}", com_hora=False)

    def _gerar_relatorio_inicial(self, cpu, ram, ativos_agora):
        now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        msg = f"\n{'='*15} MONITORAMENTO INICIADO {'='*15}\n📅 Data: {now}\n💻 Sistema: CPU {cpu}% | RAM {ram}%\n{'-'*54}\n📋 STATUS INICIAL DOS PROCESSOS:\n"
        for nome, dados in self.config.processos.items():
            regra = dados.get('regra', 'N/A')
            status_real = "🟢 ATIVO" if nome.lower() in ativos_agora else "🔴 PARADO"
            msg += f"   • {nome:<20} | {regra:<20} | {status_real}\n"
        msg += f"{'='*54}"
        self.log_callback(msg, com_hora=False)

    # ---------------------------------------------
    # THREAD 1: PROCESSOS
    # ---------------------------------------------
    def _loop_processos(self):
        ultimo_heartbeat = time.time()
        try:
            global_cpu, global_ram = SystemUtils.obter_status_recursos()
            metricas_iniciais = OSProcessUseCase.obter_metricas_processos(list(self.config.processos.keys()))
            ativos_agora = {nome.lower() for nome, m in metricas_iniciais.items() if m["status"] == "Em Execução"}
            self._gerar_relatorio_inicial(global_cpu, global_ram, ativos_agora)
        except Exception as e:
            self.log_callback(f"⚠️ Erro ao gerar relatório inicial: {e}")

        while self.rodando:
            try:
                nomes_monitorados = list(self.config.processos.keys())
                if not nomes_monitorados:
                    time.sleep(2)
                    continue

                global_cpu, global_ram = SystemUtils.obter_status_recursos()
                metricas = OSProcessUseCase.obter_metricas_processos(nomes_monitorados)

                segundos_heartbeat = self.config.intervalo_heartbeat * 3600
                agora = time.time()
                fazer_relatorio_rotina = (agora - ultimo_heartbeat) >= segundos_heartbeat
                
                if fazer_relatorio_rotina:
                    self.log_callback(f"\n{'='*15} CHECAGEM DE ROTINA {'='*15}", com_hora=False)
                    ultimo_heartbeat = agora
                    if not self.auth_service.verificar_status_atual():
                        self.log_callback("❌ ATENÇÃO: A licença de uso expirou!", com_hora=True)
                        SystemUtils.enviar_notificacao_windows("WatchdogApp - Licença Expirada", "O monitoramento foi interrompido.")
                        if self.callback_licenca_expirada: self.callback_licenca_expirada()
                        self.parar()
                        break

                for nome, cfg in self.config.processos.items():
                    dados = metricas.get(nome, {"status": "Ausente", "cpu": 0.0, "ram": 0.0})
                    dados["global_cpu"] = global_cpu
                    dados["global_ram"] = global_ram
                    
                    status_real = dados["status"]
                    status_ant = self.status_anterior_dict.get(nome, "Ausente")
                    regra = cfg.get("regra", "Não Reiniciar")

                    if fazer_relatorio_rotina and status_real == "Em Execução":
                         self.log_callback(f"   ✔️  {nome:<20} | Status: OK (Rodando)", com_hora=False)

                    if status_real == "Em Execução" and status_ant != "Em Execução":
                        self.log_callback(f"🟢 DETECTADO: {nome} entrou em execução.")
                    elif status_real != "Em Execução" and status_ant == "Em Execução":
                        state = self.process_engine.get_or_create_state(nome)
                        if not state.get("killed_by_us", False):
                            exit_code = dados.get("exit_code", -1)
                            if exit_code != 0:
                                motivo = "SOBRECARGA DO SO" if (global_cpu > 90 or global_ram > 90) else "CRASH / EXTERNO"
                                self.log_callback(f"🔴 QUEDA: {nome} ({motivo})")
                    
                    self.status_anterior_dict[nome] = status_real

                    dados["pid"] = nome 
                    acao, motivo, alvo = self.process_engine.evaluate_process(nome, dados, cfg)
                    
                    if acao == "Log_Info": self.log_callback(f"ℹ️ [INFO] '{nome}' - {motivo}")
                    elif acao != "Nada": self._executar_acao_recuperacao(nome, acao, motivo, cfg)

                    self.latest_metrics[nome] = {
                        "status": status_real, "cpu": dados["cpu"], "ram": dados["ram"],
                        "regra": regra, "acao_pendente": acao
                    }
                
                if fazer_relatorio_rotina: self.log_callback(f"{'-'*68}\n", com_hora=False)

            except Exception as e:
                print(f"Erro loop central: {e}")
            
            time.sleep(self.config.intervalo)

    def _executar_acao_recuperacao(self, nome, acao, motivo, cfg):
        self.log_callback(f"⚡ [AÇÃO] {nome} | Motivo: {motivo} | Ação: {acao}")
        def task():
            if acao == "Iniciar":
                path = cfg.get("path", "")
                min = cfg.get("execucao", {}).get("minimizado", False)
                oculto = cfg.get("execucao", {}).get("oculto", False)
                ProcessAdapter.iniciar_processo(path, minimizado=min, oculto=oculto)
            elif acao == "Parar_Forcado": ProcessAdapter.encerrar_processo(nome, graceful=False)
            elif acao == "Parar_Elegante": ProcessAdapter.encerrar_processo(nome, graceful=True, timeout=cfg.get("execucao", {}).get("graceful_timeout", 10))
            elif acao == "Alerta_Critico":
                self.log_callback(f"[CRÍTICO] {nome} falhou repetidamente. Ações automáticas suspensas!")
                script_path = cfg.get("emergencia", {}).get("script_path", "")
                if script_path:
                    self.log_callback(f"🔧 A executar script de emergência: {script_path}")
                    try: subprocess.Popen(script_path, shell=True)
                    except Exception as e: self.log_callback(f"Erro ao executar script: {e}")
        threading.Thread(target=task, daemon=True).start()

    # ---------------------------------------------
    # THREAD 2: SERVIÇOS
    # ---------------------------------------------
    def _loop_servicos(self):
        self.log_callback("\n📋 INICIALIZANDO MONITORAMENTO DE SERVIÇOS...", com_hora=False)
        
        while self.rodando:
            try:
                servicos_monitorados = list(self.config.servicos.keys())
                
                # Se não houver serviços, dorme e tenta de novo sem consumir CPU
                if not servicos_monitorados:
                    time.sleep(2)
                    continue

                for nome in servicos_monitorados:
                    cfg = self.config.servicos[nome]
                    info = ServiceAdapter.get_service_info(nome)
                    
                    # Pede ao Cérebro para avaliar a situação
                    acao, motivo, alvo_script = self.service_engine.evaluate_service(
                        nome, info, cfg, ServiceAdapter.get_service_info
                    )
                    
                    # Se o cérebro ditar uma ação, nós a executamos!
                    if acao != "Nada":
                        self._executar_acao_servico(nome, acao, motivo, alvo_script)

            except Exception as e:
                print(f"Erro na thread de serviços: {e}")
            
            time.sleep(self.config.intervalo)

    def _executar_acao_servico(self, nome, acao, motivo, alvo):
        """Dispara os comandos do Windows em background para não travar o loop principal."""
        
        if acao == "Log_Info":
            self.log_callback(f"ℹ️ [INFO] '{nome}' - {motivo}")
            return
            
        self.log_callback(f"⚙️ [SERVIÇO] {nome} | Motivo: {motivo} | Ação: {acao}")
        
        def task():
            if acao == "Iniciar": 
                ServiceAdapter.start_service(nome)
            elif acao == "Parar": 
                ServiceAdapter.stop_service(nome)
            elif acao == "Reiniciar":
                ServiceAdapter.stop_service(nome)
                time.sleep(3) # Aguarda o Windows libertar o serviço
                ServiceAdapter.start_service(nome)
            elif acao == "Continuar": 
                ServiceAdapter.continue_service(nome)
            elif acao == "Iniciar_Outro" and alvo:
                self.log_callback(f"🚀 Iniciando dependência '{alvo}' primeiro...")
                ServiceAdapter.start_service(alvo)
            elif acao == "Forcar_Encerramento":
                # Executa o algoritmo Sniper do ServiceGuard
                sucesso, msg = ServiceAdapter.force_kill_service(nome)
                if sucesso:
                    self.log_callback(f"🔪 Taskkill inteligente executado: {msg}")
                else:
                    self.log_callback(f"⚠️ Falha ao tentar forçar encerramento de {nome}: {msg}")
            elif acao == "Alerta_Critico":
                self.log_callback(f"🚨 [CRÍTICO] {nome} suspenso pelo sistema de Emergência!")
                if alvo: # 'alvo' aqui carrega o caminho do script
                    self.log_callback(f"🔧 A executar script de emergência: {alvo}")
                    try:
                        subprocess.Popen(alvo, shell=True)
                    except Exception as e:
                        self.log_callback(f"Erro ao executar script: {e}")
                
        threading.Thread(target=task, daemon=True).start()