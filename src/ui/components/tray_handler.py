import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import threading
import os
from ...infrastructure.system_utils import SystemUtils

class TrayHandler:
    def __init__(self, app_reference):
        self.app = app_reference
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

    def atualizar_icone(self):
        """ Força o sistema a recarregar a imagem do ícone (para colocar/tirar a bolinha) """
        if self.icon:
            self.icon.icon = self._carregar_imagem()

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
            
            img = None
            if os.path.exists(path_ico): img = Image.open(path_ico).convert("RGBA")
            elif os.path.exists(path_png): img = Image.open(path_png).convert("RGBA")
            else: img = Image.new('RGBA', (64, 64), color=(31, 83, 141, 255))
            
            # Se a licença estiver inválida, desenha a bolinha vermelha
            if hasattr(self.app, 'auth_service') and not self.app.auth_service.verificar_status_atual():
                draw = ImageDraw.Draw(img)
                w, h = img.size
                r = w // 4
                # Desenha no canto superior direito
                draw.ellipse((w - r - 2, 2, w - 2, r + 2), fill="red", outline="white")
                
            return img
        except Exception as e: 
            return Image.new('RGB', (64, 64), color=(31, 83, 141))