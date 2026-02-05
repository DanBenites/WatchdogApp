import pystray
from pystray import MenuItem as item
from PIL import Image
import threading
import os
from ...infrastructure.system_utils import SystemUtils

class TrayHandler:
    def __init__(self, app_reference):
        self.app = app_reference # Referência para chamar metodos da main_window
        self.icon = None

    def criar_icone(self):
        if self.icon: return

        image = self._carregar_imagem()
        menu = (
            item('Abrir WatchdogApp', self._restaurar, default=True),
            item('Encerrar', self._encerrar)
        )
        
        self.icon = pystray.Icon("WatchdogApp", image, "WatchdogApp", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def destruir_icone(self):
        if self.icon:
            self.icon.stop()
            self.icon = None

    def _restaurar(self, icon=None, item=None):
        self.destruir_icone()
        self.app.restaurar_janela()

    def _encerrar(self, icon=None, item=None):
        self.destruir_icone()
        self.app.encerrar_aplicacao()

    def _carregar_imagem(self):
        try:
            path_ico = SystemUtils.resource_path(os.path.join("assets/icons", "app_icon.ico"))
            path_png = SystemUtils.resource_path(os.path.join("assets/icons", "logo.png"))
            if os.path.exists(path_ico): return Image.open(path_ico)
            if os.path.exists(path_png): return Image.open(path_png)
        except: pass
        return Image.new('RGB', (64, 64), color=(31, 83, 141))