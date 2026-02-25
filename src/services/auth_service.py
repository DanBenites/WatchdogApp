import base64
import json
import platform
import subprocess
import hashlib
import hmac
import requests
import re
from datetime import datetime, timedelta

from ..domain.models import LicencaInfo
from ..infrastructure.persistence import PersistenceRepository

class AuthService:
    def __init__(self, config_data):
        self.config = config_data
        self.SECRET_KEY_APP = "*9|#I1u93q3vq=s=!WU~Fr9I-g-4oTG("
        self.WEBHOOK_URL = "https://n8n.vttk.cloud/webhook/validar-licenca"
        self.hwid_atual = self.get_hwid() # Renomeado para seguir o padrão do gerador

    def get_hwid(self) -> str:
        """ Coleta de IDs (Placa-mãe + CPU no Windows / machine-id no Linux) """
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

    def validar_formato_chave(self, chave: str) -> bool:
        """ Valida a estrutura da chave inserida usando Regex """
        regex_chave = r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        if isinstance(chave, str) and re.match(regex_chave, chave.upper()):
            return True
        return False

    def gerar_assinatura(self, chave: str, hwid: str, secret_key: str) -> str:
        """ Gera a assinatura HMAC-SHA256 combinando a chave e o hwid. """
        mensagem = f"{chave}{hwid}"
        return hmac.new(
            secret_key.encode('utf-8'), 
            mensagem.encode('utf-8'), 
            hashlib.sha256
        ).hexdigest()

    def verificar_acesso(self, chave_usuario: str, rotina: bool = False) -> dict:
        """ Comunica com backend para validar a licença. """
        # Ignora a validação de formato se for um ping de rotina
        if not rotina and not self.validar_formato_chave(chave_usuario):
            return {"status": "erro", "motivo": "formato_invalido"}

        url = self.WEBHOOK_URL
        assinatura = self.gerar_assinatura(chave_usuario, self.hwid_atual, self.SECRET_KEY_APP)

        payload = {
            "chave": chave_usuario,
            "hwid": self.hwid_atual,
            "signature": assinatura
        }
        
        if rotina:
            payload["rotina"] = True

        try:
            # Timeout de 10 segundos para não travar o app se o servidor cair
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return response.json() # Sucesso (Ativa)
            elif response.status_code == 403:
                return {"status": "erro", "motivo": "bloqueado_ou_expirado"}
            else:
                return {"status": "erro", "motivo": "servidor_instavel"}
                
        except requests.exceptions.RequestException:
            return {"status": "erro", "motivo": "sem_conexao"}

    def validar_chave_inserida(self, chave_texto: str) -> tuple[bool, str]:
        """ Roteador: Decide se é uma chave Master ou Cliente Online """
        chave_texto = chave_texto.strip()

        # 1. Rota Obscura (Chave Fantasma Master)
        if chave_texto.startswith("WDAM-"):
            return self._validar_chave_master(chave_texto)
        
        # 2. Rota Padrão (Webhook n8n)
        resposta = self.verificar_acesso(chave_texto)
        
        if "status" in resposta and resposta["status"] == "erro":
            motivo = resposta.get("motivo")
            
            # SE NÃO TIVER INTERNET NA HORA DE INSERIR: Libera provisoriamente por 48h
            if motivo in ["sem_conexao", "servidor_instavel"]:
                self.config.licenca.chave = chave_texto
                self.config.licenca.hwid_vinculado = self.hwid_atual
                self.config.licenca.data_expiracao = None # Só saberemos quando conectar
                self.config.licenca.data_ativacao = datetime.now() # Hora que a pessoa inseriu a chave
                
                # Se você adicionou o campo de ultimo_checkin conforme conversamos antes, limpe-o:
                if hasattr(self.config.licenca, 'data_ultimo_checkin'):
                    self.config.licenca.data_ultimo_checkin = None
                    
                self.config.licenca.ativa = True
                PersistenceRepository.salvar(self.config)
                return True, "Sem internet. Acesso provisório de 48h liberado."

            # Erros reais (bloqueado, formato)
            mensagens_erro = {
                "formato_invalido": "Formato de chave inválido. Use XXXX-XXXX-XXXX-XXXX.",
                "bloqueado_ou_expirado": "Acesso bloqueado ou chave revogada."
            }
            return False, mensagens_erro.get(motivo, "Erro desconhecido na validação.")
        
        # SUCESSO ONLINE
        data_exp_str = resposta.get("expira_em") 
        if data_exp_str:
            data_limpa = data_exp_str.split('T')[0]
            data_exp = datetime.strptime(data_limpa, "%Y-%m-%d")
            
            # NOVA TRAVA: Verifica se a máquina do usuário está no futuro burlando a expiração
            if datetime.now().date() > data_exp.date():
                return False, "Sua licença já expirou!"

            self._salvar_licenca_ativa(chave_texto, self.hwid_atual, data_exp)
            return True, "Licença ativada com sucesso!"
        else:
            return False, "Erro no servidor: Data de expiração não informada."

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
            
            if datetime.now().date() > data_exp.date():
                return False, "Esta chave master já está expirada."

            # Validação criptográfica da chave master usando a função centralizada
            texto_base = f"{hwid_chave}{data_exp_str}"
            assinatura_esperada = self.gerar_assinatura(texto_base, hwid_chave, self.SECRET_KEY_APP)
            
            # hmac.compare_digest previne ataques de tempo
            if not hmac.compare_digest(sig_chave, assinatura_esperada):
                return False, "Assinatura da chave master é inválida."
            
            self._salvar_licenca_ativa(chave_texto, hwid_chave, data_exp)
            return True, "Licença Master ativada com sucesso!"

        except Exception as e:
            return False, "Chave Master corrompida."

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
        if not self.config.licenca.chave:
            return False
            
        if self.config.licenca.hwid_vinculado != self.hwid_atual:
            self._bloquear_licenca()
            return False

        # 1. Rota Master (Offline)
        if self.config.licenca.chave.startswith("WDAM-"):
            if self.config.licenca.data_expiracao and datetime.now().date() > self.config.licenca.data_expiracao.date():
                self._bloquear_licenca()
                return False
            return True

        # 2. Rota Online
        resultado = self.verificar_acesso(self.config.licenca.chave, rotina=True)

        if "status" not in resultado or resultado.get("status") != "erro":
            # Sucesso
            nova_exp_str = resultado.get("expira_em")
            if nova_exp_str:
                nova_data_limpa = nova_exp_str.split('T')[0]
                nova_exp = datetime.strptime(nova_data_limpa, "%Y-%m-%d")
                
                # NOVA TRAVA ROTINEIRA: Checa bypass de data local
                if datetime.now().date() > nova_exp.date():
                    self._bloquear_licenca()
                    return False
                    
                self.config.licenca.data_expiracao = nova_exp
            
            # Registra o sucesso na conexão
            if hasattr(self.config.licenca, 'data_ultimo_checkin'):
                self.config.licenca.data_ultimo_checkin = datetime.now()
            
            # Garante que temos a data de ativação salva (se foi gerado no passado)
            if not self.config.licenca.data_ativacao:
                 self.config.licenca.data_ativacao = datetime.now()

            self.config.licenca.ativa = True
            PersistenceRepository.salvar(self.config)
            return True
            
        elif resultado.get("motivo") == "bloqueado_ou_expirado":
            self._bloquear_licenca()
            return False
            
        elif resultado.get("motivo") in ["sem_conexao", "servidor_instavel"]:
            pass # Sem internet, deixa o código continuar para a verificação offline abaixo
        else:
            self._bloquear_licenca()
            return False
            
        # 3. Avaliação Offline (Sem internet ou n8n fora do ar)
        if self.config.licenca.data_expiracao and datetime.now().date() > self.config.licenca.data_expiracao.date():
            self._bloquear_licenca()
            return False
            
        # Pega a última vez que validou online OU a data em que inseriu offline
        ultimo_checkin = getattr(self.config.licenca, 'data_ultimo_checkin', None)
        if not ultimo_checkin:
            ultimo_checkin = self.config.licenca.data_ativacao
            
        if not ultimo_checkin:
            ultimo_checkin = datetime.now() # Fallback de segurança
            
        limite_carencia = ultimo_checkin + timedelta(hours=48)
        
        if datetime.now() <= limite_carencia:
            return True 
        else:
            self._bloquear_licenca() 
            return False

        if "status" not in resultado or resultado.get("status") != "erro":
            # Sucesso
            nova_exp_str = resultado.get("expira_em")
            if nova_exp_str:
                # Corta a string no "T" e pega apenas a data
                nova_data_limpa = nova_exp_str.split('T')[0]
                nova_exp = datetime.strptime(nova_data_limpa, "%Y-%m-%d")
                self.config.licenca.data_expiracao = nova_exp
            
            # self.config.licenca.data_ativacao = datetime.now()
            self.config.licenca.ativa = True
            PersistenceRepository.salvar(self.config)
            return True
            
        elif resultado.get("motivo") == "bloqueado_ou_expirado":
            self._bloquear_licenca()
            return False
            
        elif resultado.get("motivo") in ["sem_conexao", "servidor_instavel"]:
            # Deixa passar para a avaliação offline de carência
            pass
        else:
            # Erro de formato salvo (improvável, mas protegido)
            self._bloquear_licenca()
            return False
            
        # 3. Avaliação Offline (Sem internet ou n8n fora do ar)
        if self.config.licenca.data_expiracao and datetime.now().date() > self.config.licenca.data_expiracao.date():
            self._bloquear_licenca()
            return False
            
        ultimo_checkin = self.config.licenca.data_ativacao or datetime.now()
        limite_carencia = ultimo_checkin + timedelta(hours=48)
        
        if datetime.now() <= limite_carencia:
            return True 
        else:
            self._bloquear_licenca() 
            return False

    def _bloquear_licenca(self):
        """ Helper para revogar e salvar no disco (apenas se houver mudança) """
        if self.config.licenca.ativa:
            self.config.licenca.ativa = False
            PersistenceRepository.salvar(self.config)
    
    def testar_conexao_servidor(self) -> bool:
        """ Faz um ping rápido apenas para verificar se o servidor n8n está de pé """
        try:
            requests.options(self.WEBHOOK_URL, timeout=3)
            return True
        except requests.exceptions.RequestException:
            return False
    
    def is_licenca_ativa(self) -> bool:
        if not self.config.licenca.ativa or not self.config.licenca.chave:
            return False
            
        if self.config.licenca.hwid_vinculado != self.hwid_atual:
            return False

        if self.config.licenca.data_expiracao and datetime.now().date() > self.config.licenca.data_expiracao.date():
            return False
            
        return True