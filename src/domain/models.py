from dataclasses import dataclass, field
from typing import Dict

@dataclass
class ProcessoAlvo:
    nome: str
    path: str
    regra: str  # "Não Reiniciar", "Sempre Reiniciar", etc.
    status: str = "Iniciando"

@dataclass
class AppConfig:
    intervalo: int = 5
    dias_log: int = 7
    intervalo_heartbeat: int = 2
    iniciar_com_windows: bool = False
    minimizar_para_tray: bool = False
    persistir_monitoramento: bool = False 
    monitoramento_ativo_no_fechamento: bool = False 
    delay_inicializacao: int = 20 
    acao_ao_iniciar: str = "ignorar"
    processos: Dict[str, dict] = field(default_factory=dict)