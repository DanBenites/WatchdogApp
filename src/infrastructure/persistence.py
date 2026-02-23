import json
import os
import base64
from datetime import datetime
from ..domain.models import AppConfig

app_data = os.getenv('APPDATA')
pasta_config = os.path.join(app_data, "WatchdogApp")

if not os.path.exists(pasta_config):
    try:
        os.makedirs(pasta_config)
    except: pass

CONFIG_FILE = os.path.join(pasta_config, "init.dat")
CONFIG_LEGADA = os.path.join(pasta_config, "config_watchdog.json")

class PersistenceRepository:
    @staticmethod
    def salvar(config: AppConfig):
        dt_ativacao = config.licenca.data_ativacao.isoformat() if config.licenca.data_ativacao else None
        dt_expiracao = config.licenca.data_expiracao.isoformat() if config.licenca.data_expiracao else None

        dados = {
            "configuracoes": {
                "intervalo": config.intervalo, 
                "dias_log": config.dias_log, 
                "intervalo_heartbeat": config.intervalo_heartbeat,
                "iniciar_com_windows": config.iniciar_com_windows,
                "minimizar_para_tray": config.minimizar_para_tray,
                "persistir_monitoramento": config.persistir_monitoramento,
                "monitoramento_ativo_no_fechamento": config.monitoramento_ativo_no_fechamento,
                "delay_inicializacao": config.delay_inicializacao,
                "acao_ao_iniciar": config.acao_ao_iniciar
            },
            "processos_monitorados": config.processos,
            "licenca": {
                "chave": config.licenca.chave,
                "hwid_vinculado": config.licenca.hwid_vinculado,
                "data_ativacao": dt_ativacao,
                "data_expiracao": dt_expiracao,
                "ativa": config.licenca.ativa
            }
        }
        
        json_str = json.dumps(dados)
        dados_ofuscados = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(dados_ofuscados)
            
        if os.path.exists(CONFIG_LEGADA):
            try: os.remove(CONFIG_LEGADA)
            except: pass

    @staticmethod
    def carregar() -> AppConfig:
        caminho_leitura = CONFIG_FILE
        usando_legado = False
        
        if not os.path.exists(caminho_leitura):
            if os.path.exists(CONFIG_LEGADA):
                caminho_leitura = CONFIG_LEGADA
                usando_legado = True
            else:
                return AppConfig()
        
        try:
            with open(caminho_leitura, "r", encoding="utf-8") as f:
                conteudo = f.read()
                
            if usando_legado:
                dados = json.loads(conteudo)
            else:
                json_str = base64.b64decode(conteudo).decode('utf-8')
                dados = json.loads(json_str)
                
            config = AppConfig(
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
            
            if "licenca" in dados:
                l_dados = dados["licenca"]
                config.licenca.chave = l_dados.get("chave")
                config.licenca.hwid_vinculado = l_dados.get("hwid_vinculado")
                config.licenca.ativa = l_dados.get("ativa", False)
                
                l_ativacao = l_dados.get("data_ativacao") or l_dados.get("data_criacao")
                if l_ativacao:
                    config.licenca.data_ativacao = datetime.fromisoformat(l_ativacao)

                if l_dados.get("data_expiracao"):
                    config.licenca.data_expiracao = datetime.fromisoformat(l_dados.get("data_expiracao"))
                    
            return config
                
        except Exception as e:
            print(f"Erro ao ler config: {e}")
            return AppConfig()