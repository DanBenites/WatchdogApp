from src.domain.models import AppConfig
from src.services.auth_service import AuthService
from src.infrastructure.persistence import PersistenceRepository

def rodar_testes():
    print("="*50)
    print("INICIANDO TESTES DO AUTH SERVICE")
    print("="*50)

    # 1. Mock (Simulação) da Persistência
    # Vamos intercetar o "salvar" para ele não subscrever a sua licença real durante o teste
    PersistenceRepository.salvar = lambda config: print("[Disco] -> Alterações salvas com sucesso.")

    # 2. Inicializar Configuração Limpa e o Serviço
    config_mock = AppConfig()
    auth = AuthService(config_mock)

    # --- TESTE 1: HWID ---
    print("\n[Teste 1] Leitura de HWID:")
    hwid = auth.obter_hwid_maquina()
    print(f"HWID gerado: {hwid}")

    # --- TESTE 2: Conexão com Servidor ---
    print("\n[Teste 2] Conexão com o n8n:")
    is_online = auth.testar_conexao_servidor()
    print(f"Servidor Online? {'Sim' if is_online else 'Não'}")

    # --- TESTE 3: Formato de Chave Inválido ---
    print("\n[Teste 3] Validação de Chave Falsa:")
    sucesso, msg = auth.validar_chave_inserida("CHAVE-TOTALMENTE-FALSA")
    print(f"Resultado esperado: False. Obtido: {sucesso} | Mensagem: {msg}")

    # --- TESTE 4: Validação de Chave Real ---
    print("\n[Teste 4] Inserção de Chave Real:")
    chave_real = input(">> Cole aqui a chave (WDAM-... ou XXXX-XXXX-XXXX-XXXX) gerada para testar: ").strip()
    
    if chave_real:
        sucesso, msg = auth.validar_chave_inserida(chave_real)
        print(f"Resultado: {sucesso}")
        print(f"Mensagem do Sistema: {msg}")
        
        if sucesso:
            print("\n[Status Interno Pós-Ativação]")
            print(f"- Licença Ativa: {config_mock.licenca.ativa}")
            print(f"- Data Ativação: {config_mock.licenca.data_ativacao}")
            print(f"- Vencimento:    {config_mock.licenca.data_expiracao}")
            
            print("\n[Teste 5] Verificação de Rotina (Ping Background):")
            status_rotina = auth.verificar_status_atual()
            print(f"Status mantido após rotina? {status_rotina}")
    else:
        print("Teste de chave ignorado.")

    print("\n" + "="*50)

if __name__ == "__main__":
    rodar_testes()