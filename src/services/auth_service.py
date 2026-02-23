import base64
import json
import platform
import subprocess
import hashlib
import hmac
import requests
from datetime import datetime, timedelta

from ..domain.models import LicencaInfo
from ..infrastructure.persistence import PersistenceRepository

class AuthService:
    def __init__(self, config_data):
        self.config = config_data
        self.SECRET_KEY_APP = "*9|#I1u93q3vq=s=!WU~Fr9I-g-4oTG("
        self.WEBHOOK_URL = "https://n8n.vttk.cloud/webhook/validar-licenca"
        self.hwid_atual = self._gerar_novo_hwid()

    def _gerar_novo_hwid(self) -> str:
        """ Novo método de HWID baseado em SHA256 (Placa Mãe + CPU) """
        try:
            if platform.system() == "Windows":
                m_board = subprocess.check_output('wmic baseboard get serialnumber', shell=True).decode().split('\n')[1].strip()
                cpu = subprocess.check_output('wmic cpu get processorid', shell=True).decode().split('\n')[1].strip()
                raw_id = f"{m_board}-{cpu}"
            else:
                with open("/etc/machine-id", "r") as f:
                    raw_id = f.read().strip()
            return hashlib.sha256(raw_id.encode()).hexdigest()
        except Exception as e:
            print(f"Erro ao gerar HWID: {e}")
            return "HWID_DESCONHECIDO_NOVO"

    def obter_hwid_maquina(self) -> str:
        return self.hwid_atual

    def _gerar_assinatura(self, texto_base: str, hwid: str) -> str:
        """ Gera assinatura HMAC-SHA256 padrão para online e offline """
        mensagem = f"{texto_base}{hwid}"
        return hmac.new(
            self.SECRET_KEY_APP.encode('utf-8'), 
            mensagem.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def validar_chave_inserida(self, chave_texto: str) -> tuple[bool, str]:
        """ Roteador: Decide se é uma chave Master ou Cliente Online """
        chave_texto = chave_texto.strip()

        # 1. Rota Obscura (Chave Fantasma Master)
        if chave_texto.startswith("WDAM-"):
            return self._validar_chave_master(chave_texto)
        
        # 2. Rota Padrão (Webhook n8n)
        return self._validar_chave_online(chave_texto)

    def _validar_chave_master(self, chave_texto: str) -> tuple[bool, str]:
        """ Validação 100% offline e com assinatura local """
        try:
            chave_limpa = chave_texto.replace("WDAM-", "").strip()
            payload_bytes = base64.b64decode(chave_limpa)
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            hwid_chave = payload.get("hwid")
            data_exp_str = payload.get("exp")
            sig_chave = payload.get("sig")
            
            if not hwid_chave or not data_exp_str or not sig_chave:
                return False, "Formato de chave master inválido."
            
            if hwid_chave != self.hwid_atual:
                return False, "Esta chave pertence a outro computador."
                
            data_exp = datetime.strptime(data_exp_str, "%Y-%m-%d")
            if datetime.now() > data_exp:
                return False, "Esta chave master já está expirada."

            # Validação criptográfica da chave master
            texto_base = f"{hwid_chave}{data_exp_str}"
            assinatura_esperada = self._gerar_assinatura(texto_base, hwid_chave)
            
            # hmac.compare_digest previne ataques de tempo (timing attacks)
            if not hmac.compare_digest(sig_chave, assinatura_esperada):
                return False, "Assinatura da chave master é inválida."
            
            self._salvar_licenca_ativa(chave_texto, hwid_chave, data_exp)
            return True, "Licença Master ativada com sucesso!"

        except Exception as e:
            return False, "Chave Master corrompida."

    def _validar_chave_online(self, chave_texto: str) -> tuple[bool, str]:
        """ Requisição para o Webhook com tratamento de timeout """
        assinatura = self._gerar_assinatura(chave_texto, self.hwid_atual)
        payload = {
            "chave": chave_texto,
            "hwid": self.hwid_atual,
            "signature": assinatura
        }

        try:
            response = requests.post(self.WEBHOOK_URL, json=payload, timeout=10)
            
            if response.status_code == 200:
                dados = response.json()
                
                # Se o seu n8n retornar a data limite, pegamos ela. Se não, damos 30 dias de backup
                data_exp_str = dados.get("expiracao") 
                if data_exp_str:
                    data_exp = datetime.strptime(data_exp_str, "%Y-%m-%d")
                else:
                    data_exp = datetime.now() + timedelta(days=30) 

                self._salvar_licenca_ativa(chave_texto, self.hwid_atual, data_exp)
                return True, "Licença ativada com sucesso!"
                
            elif response.status_code == 403:
                return False, "Acesso bloqueado ou chave revogada."
            else:
                return False, f"Falha no servidor ({response.status_code}). Contate o suporte."

        except requests.exceptions.RequestException:
            return False, "Sem conexão com o servidor. Verifique sua internet para ativar."

    def _salvar_licenca_ativa(self, chave: str, hwid: str, data_exp: datetime):
        """ Salva na memória e no disco (.dat) """
        self.config.licenca.chave = chave
        self.config.licenca.hwid_vinculado = hwid
        self.config.licenca.data_expiracao = data_exp
        self.config.licenca.ativa = True
        
        self.config.licenca.data_ativacao = datetime.now()
        PersistenceRepository.salvar(self.config)

    def verificar_status_atual(self) -> bool:
        """ Rodado em background pelo programa constantemente """
        if not self.config.licenca.ativa or not self.config.licenca.chave:
            return False
            
        if self.config.licenca.hwid_vinculado != self.hwid_atual:
            self._bloquear_licenca()
            return False

        if self.config.licenca.data_expiracao and datetime.now() > self.config.licenca.data_expiracao:
            self._bloquear_licenca()
            return False
        
        # Se for a chave Master (rota obscura), não checa webhook e assume como válida
        if self.config.licenca.chave.startswith("WDAM-"):
            return True

        # Rotina de verificação no Webhook (Ping em background)
        assinatura = self._gerar_assinatura(self.config.licenca.chave, self.hwid_atual)
        payload = {
            "chave": self.config.licenca.chave,
            "hwid": self.hwid_atual,
            "signature": assinatura,
            "rotina": True # Identificador para seu n8n saber que é só um ping de checagem
        }

        try:
            # Timeout curto de 5s para não travar a UI do usuário
            response = requests.post(self.WEBHOOK_URL, json=payload, timeout=5)
            
            if response.status_code == 200:
                # Sucesso: Renova a data do último check-in
                self.config.licenca.data_criacao = datetime.now()
                PersistenceRepository.salvar(self.config)
                return True
                
            elif response.status_code == 403: 
                # Chave revogada por você lá no n8n -> Bloqueia o App na hora
                self._bloquear_licenca()
                return False
                
        except requests.exceptions.RequestException:
            # Caiu aqui: Sem internet ou n8n fora do ar
            # Aplica a regra de carência de 48 horas
            ultimo_checkin = self.config.licenca.data_ativacao or datetime.now()
            limite_carencia = ultimo_checkin + timedelta(hours=48)
            
            if datetime.now() <= limite_carencia:
                return True # Internet caiu, mas está dentro das 48h (Permite uso)
            else:
                self._bloquear_licenca() # Estourou as 48h sem falar com o servidor
                return False
                
        return True

    def _bloquear_licenca(self):
        """ Helper para revogar e salvar no disco """
        self.config.licenca.ativa = False
        PersistenceRepository.salvar(self.config)
    
    def testar_conexao_servidor(self) -> bool:
        """ Faz um ping rápido apenas para verificar se o servidor n8n está de pé """
        try:
            # Usamos um timeout bem curto (3s). Apenas para ver se o servidor web responde.
            # Mesmo que o webhook exija POST, um GET ou OPTIONS retornará um status HTTP (ex: 404, 405),
            # o que prova que a rede/servidor estão Online.
            requests.options(self.WEBHOOK_URL, timeout=3)
            return True
        except requests.exceptions.RequestException:
            # Se der timeout ou erro de DNS, o servidor está realmente inacessível/offline
            return False