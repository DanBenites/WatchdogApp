from src.infrastructure.persistence import PersistenceRepository
from src.infrastructure.log_manager import LogManager
from src.infrastructure.icon_manager import IconeManager
from src.services.auth_service import AuthService
from src.services.monitor_engine import WatchdogEngine
from src.ui.main_window import WatchdogApp
from src.ui.components.tray_handler import TrayHandler

if __name__ == "__main__":
    # 1. Carregar Dados Essenciais
    config_data = PersistenceRepository.carregar()
    
    # 2. Inicializar Infraestrutura e Serviços
    log_manager = LogManager()
    icon_manager = IconeManager()
    auth_service = AuthService(config_data)

    # 3. Inicializar Interface Gráfica (Injetando dependências limpas)
    app = WatchdogApp(
        config_data=config_data,
        log_manager=log_manager,
        icon_manager=icon_manager,
        auth_service=auth_service
    )
    
    # 4. Inicializar o Motor (Precisamos passar a função de log do app)
    engine = WatchdogEngine(config_data, app.registrar_log, auth_service)
    
    # 5. Inicializar o Tray (Ícone da Bandeja)
    tray_handler = TrayHandler(app)

    # 6. Vincular as dependências cruzadas finais à UI
    app.set_engine(engine)
    app.set_tray_handler(tray_handler)

    # 7. Rodar a aplicação
    app.run()