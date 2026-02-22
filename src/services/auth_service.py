import base64
import json
from datetime import datetime
from ..domain.models import LicencaInfo
from ..infrastructure.system_utils import SystemUtils

class AuthService:
    def __init__(self, config_data):
        self.config = config_data
        self.hwid_atual = SystemUtils.obter_hwid()
        self._SECRET = "WATCHDOG_LOCAL_SECRET_KEY_2026" # Simula a segurança offline

    def obter_hwid_maquina(self) -> str:
        return self.hwid_atual

    def validar_chave_inserida(self, chave_texto: str) -> tuple[bool, str]:
        """ Valida uma nova chave digitada pelo usuário """
        try:
            # Em um cenário real offline, a chave estaria encriptada (ex: Fernet, AES ou JWT)
            # Para estruturar o esqueleto, vamos usar Base64 de um JSON para simular o Payload
            # Formato esperado: base64({"hwid": "...", "exp": "YYYY-MM-DD"})
            
            # Limpa prefixos hipotéticos caso você crie um gerador (ex: WDA-...)
            chave_limpa = chave_texto.replace("WDA-", "").strip()
            
            payload_bytes = base64.b64decode(chave_limpa)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            hwid_chave = payload.get("hwid")
            data_exp_str = payload.get("exp")
            data_criacao_str = payload.get("iat")
            
            
            if not hwid_chave or not data_exp_str:
                return False, "Formato de chave inválido."
                
            if hwid_chave != self.hwid_atual:
                return False, "Esta chave pertence a outro computador (HWID não confere)."
                
            data_exp = datetime.strptime(data_exp_str, "%Y-%m-%d")
            data_criacao = datetime.strptime(data_criacao_str, "%Y-%m-%d") if data_criacao_str else None

            if datetime.now() > data_exp:
                return False, "Esta chave já está expirada."
                
            # Se passou em tudo, atualiza o modelo
            self.config.licenca.chave = chave_texto
            self.config.licenca.hwid_vinculado = hwid_chave
            self.config.licenca.data_criacao = data_criacao
            self.config.licenca.data_expiracao = data_exp
            self.config.licenca.ativa = True
            
            return True, "Licença ativada com sucesso!"
            
        except Exception as e:
            return False, "Chave inválida ou corrompida."

    def verificar_status_atual(self) -> bool:
        """ Método chamado rotineiramente para checar se a licença salva ainda vale """
        if not self.config.licenca.ativa or not self.config.licenca.chave:
            return False
            
        if self.config.licenca.data_expiracao:
            if datetime.now() > self.config.licenca.data_expiracao:
                self.config.licenca.ativa = False
                return False
                
        # Validação extra de segurança (caso o cara troque a placa mãe)
        if self.config.licenca.hwid_vinculado != self.hwid_atual:
            self.config.licenca.ativa = False
            return False
            
        return True