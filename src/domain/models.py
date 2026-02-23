from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

@dataclass
class ProcessoAlvo:
    nome: str
    path: str
    regra: str  # "Não Reiniciar", "Sempre Reiniciar", etc.
    status: str = "Iniciando"
@dataclass
class LicencaInfo:
    chave: str = ""
    hwid_vinculado: str = ""
    data_ativacao: Optional[datetime] = None
    data_expiracao: Optional[datetime] = None
    ativa: bool = False

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
    licenca: LicencaInfo = field(default_factory=LicencaInfo)