import time
import subprocess
import threading
import os
from datetime import datetime
import psutil
from ..infrastructure.system_utils import SystemUtils

class WatchdogEngine:
    def __init__(self, config, log_callback, auth_service):
        self.config = config
        self.log_callback = log_callback
        self.auth_service = auth_service
        self.rodando = False
        self._thread = None
        self.callback_licenca_expirada = None

    def iniciar(self):
        if self.rodando: return
        self.rodando = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def parar(self):
        self.rodando = False
        now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        msg = f"\n{'='*15} 🛑 MONITORAMENTO PARADO {'='*15}\n"
        msg += f"📅 Data: {now}\n"
        msg += f"{'='*54}"
        self.log_callback(msg, com_hora=False)

    def _gerar_relatorio_inicial(self, cpu, ram, ativos_agora):
        now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        msg = f"\n{'='*15} MONITORAMENTO INICIADO {'='*15}\n"
        msg += f"📅 Data: {now}\n"
        msg += f"💻 Sistema: CPU {cpu}% | RAM {ram}%\n"
        msg += f"{'-'*54}\n"
        msg += "📋 STATUS INICIAL DOS PROCESSOS:\n"

        for nome, dados in self.config.processos.items():
            regra = dados.get('regra', 'N/A')
            is_running = nome.lower() in ativos_agora
            status_real = "🟢 ATIVO" if is_running else "🔴 PARADO"
            dados['status'] = "Ativo" if is_running else "Parado"
            
            msg += f"   • {nome:<20} | {regra:<20} | {status_real}\n"
        
        msg += f"{'='*54}"
        self.log_callback(msg, com_hora=False)

    def _loop(self):
        processos_alvo = self.config.processos
        ultimo_heartbeat = time.time()
        
        # Relatório Inicial
        try:
            cpu, ram = SystemUtils.obter_status_recursos()
            ativos_agora = {p.info['name'].lower() for p in psutil.process_iter(['name'])}
            self._gerar_relatorio_inicial(cpu, ram, ativos_agora)
        except Exception as e:
            self.log_callback(f"⚠️ Erro ao gerar relatório inicial: {e}")

        while self.rodando:
            try:
                cpu, ram = SystemUtils.obter_status_recursos()
                ativos_agora = {p.info['name'].lower() for p in psutil.process_iter(['name'])}
                hora_atual_str = datetime.now().strftime('%H:%M:%S')

                # --- HEARTBEAT ---
                segundos_heartbeat = self.config.intervalo_heartbeat * 3600
                agora = time.time()
                fazer_relatorio_rotina = (agora - ultimo_heartbeat) >= segundos_heartbeat
                
                if fazer_relatorio_rotina:
                    self.log_callback(f"\n{'='*15} CHECAGEM DE ROTINA ({hora_atual_str}) {'='*15}", com_hora=False)
                    ultimo_heartbeat = agora

                    if not self.auth_service.verificar_status_atual():
                        self.log_callback("❌ ATENÇÃO: A licença de uso expirou!", com_hora=False)
                        SystemUtils.enviar_notificacao_windows(
                            "WatchdogApp - Licença Expirada", 
                            "O monitoramento foi interrompido. Insira uma nova chave para continuar."
                        )
                        # Avisa a Janela Principal para bloquear tudo
                        if self.callback_licenca_expirada:
                            self.callback_licenca_expirada()
                            
                        self.parar()
                        break

                for nome, dados in processos_alvo.items():
                    esta_rodando = nome.lower() in ativos_agora
                    regra = dados.get('regra', 'Não Reiniciar')
                    status_anterior = dados.get('status', 'Parado')

                    # 1. Registro de Rotina (O que faltava no seu código)
                    if fazer_relatorio_rotina and esta_rodando:
                         self.log_callback(f"   ✔️  {nome:<20} | Status: OK (Rodando)", com_hora=False)

                    # 2. Monitoramento de Mudanças
                    if esta_rodando:
                        if status_anterior != "Ativo":
                            # Removemos o timestamp manual, a UI adiciona
                            self.log_callback(f"🟢 DETECTADO: {nome} entrou em execução.")
                            dados['status'] = "Ativo"
                    else:
                        if status_anterior == "Ativo":
                            motivo = "SOBRECARGA" if (cpu > 90 or ram > 90) else "EXTERNO"
                            self.log_callback(f"🔴 QUEDA: {nome} ({motivo})")
                        
                        dados['status'] = "Parado"
                        
                        deve_reiniciar = (regra == "Sempre Reiniciar") or \
                                         (regra == "Reiniciar se erro Windows" and (cpu > 90 or ram > 90))
                        
                        if deve_reiniciar:
                            self._tenter_reiniciar(nome, dados)
                
                if fazer_relatorio_rotina:
                     self.log_callback(f"{'-'*68}\n", com_hora=False)

            except Exception as e:
                print(f"Erro loop: {e}")
            
            time.sleep(self.config.intervalo)

    def _tenter_reiniciar(self, nome, dados):
        path = dados.get('path')
        if path and os.path.exists(path):
            try:
                subprocess.Popen(path)
                self.log_callback(f"🔄 AUTO-RESTART: Reiniciando {nome}...")
                dados['status'] = "Iniciando" 
            except Exception as e:
                self.log_callback(f"⚠️ ERRO RESTART: Falha ao abrir {nome}. Detalhe: {e}")
        else:
            self.log_callback(f"⚠️ CONFIGURAÇÃO: Caminho inválido para {nome}.")