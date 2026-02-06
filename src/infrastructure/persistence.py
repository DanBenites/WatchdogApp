import json
import os
from ..domain.models import AppConfig

app_data = os.getenv('APPDATA')
pasta_config = os.path.join(app_data, "WatchdogApp")

# Garante que a pasta existe antes de definir o arquivo
if not os.path.exists(pasta_config):
    try:
        os.makedirs(pasta_config)
    except: pass

CONFIG_FILE = os.path.join(pasta_config, "config_watchdog.json")

class PersistenceRepository:
    @staticmethod
    def salvar(config: AppConfig):
        dados = {
            "configuracoes": {"intervalo": config.intervalo, 
                              "dias_log": config.dias_log, 
                              "intervalo_heartbeat": config.intervalo_heartbeat,
                              "iniciar_com_windows": config.iniciar_com_windows,
                              "minimizar_para_tray": config.minimizar_para_tray,
                              "persistir_monitoramento": config.persistir_monitoramento,
                              "monitoramento_ativo_no_fechamento": config.monitoramento_ativo_no_fechamento,
                              "delay_inicializacao": config.delay_inicializacao,
                              "acao_ao_iniciar": config.acao_ao_iniciar
                              },
            "processos_monitorados": config.processos
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4)

    @staticmethod
    def carregar() -> AppConfig:
        if not os.path.exists(CONFIG_FILE):
            return AppConfig()
        
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return AppConfig(
                    intervalo=dados["configuracoes"].get("intervalo", 5),
                    dias_log=dados["configuracoes"].get("dias_log", 7),
                    intervalo_heartbeat=dados["configuracoes"].get("intervalo_heartbeat", 2),
                    iniciar_com_windows=dados["configuracoes"].get("iniciar_com_windows", False),
                    minimizar_para_tray=dados["configuracoes"].get("minimizar_para_tray", False),
                    persistir_monitoramento=dados["configuracoes"].get("persistir_monitoramento", False),
                    monitoramento_ativo_no_fechamento=dados["configuracoes"].get("monitoramento_ativo_no_fechamento", False),
                    delay_inicializacao=dados["configuracoes"].get("delay_inicializacao", 20),
                    acao_ao_iniciar=dados["configuracoes"].get("acao_ao_iniciar", "ignorar"),
                    processos=dados.get("processos_monitorados", {})
                )
        except Exception as e:
            print(f"Erro ao ler config: {e}")
            return AppConfig()