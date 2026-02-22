import base64
import json
import subprocess
from datetime import datetime, timedelta

def obter_hwid():
    """ Usa o mesmo método do app para pegar o seu HWID real """
    try:
        output = subprocess.check_output(
            "wmic csproduct get uuid", 
            shell=True, 
            creationflags=subprocess.CREATE_NO_WINDOW
        ).decode('utf-8').split('\n')[1].strip()
        return output if output else "HWID_DESCONHECIDO"
    except Exception:
        return "HWID_DESCONHECIDO"

def gerar_chave(dias_validade=1):
    hwid = obter_hwid()
    data_criacao = datetime.now().strftime("%Y-%m-%d")
    data_exp = (datetime.now() + timedelta(days=dias_validade)).strftime("%Y-%m-%d")
    
    # Monta o payload exatamente como o AuthService espera
    payload = {
        "hwid": hwid,
        "iat": data_criacao,
        "exp": data_exp
    }
    
    # Converte para JSON string e depois para Base64
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    chave_b64 = base64.b64encode(payload_bytes).decode('utf-8')
    
    # Adiciona o nosso prefixo
    chave_final = f"WDA-{chave_b64}"
    
    print("\n" + "="*50)
    print("GERADOR DE LICENÇA DO WATCHDOGAPP")
    print("="*50)
    print(f"HWID Vinculado: {hwid}")
    print(f"Criada em:      {data_criacao}")
    print(f"Válida até:     {data_exp}")
    print("-" * 50)
    print("COPIE A CHAVE ABAIXO:")
    print(f"\n{chave_final}\n")
    print("="*50 + "\n")

if __name__ == "__main__":
    gerar_chave()