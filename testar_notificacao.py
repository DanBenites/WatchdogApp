from src.infrastructure.system_utils import SystemUtils

print("Enviando notificação...")
SystemUtils.enviar_notificacao_windows(
    "Teste do WatchdogApp", 
    "Olá! Esta é uma notificação de teste do sistema."
)
print("Verifique a central de ações do seu Windows (canto inferior direito)!")