import customtkinter as ctk
from PIL import Image
import os
from ...infrastructure.system_utils import SystemUtils

class SplashScreen:
    def __init__(self, parent, config, on_finish_callback):
        self.parent = parent
        self.config = config
        self.on_finish = on_finish_callback
        self.window = None

    def exibir(self):
        self.window = ctk.CTkToplevel(self.parent)
        
        largura, altura = 400, 300
        screen_x = self.parent.winfo_screenwidth()
        screen_y = self.parent.winfo_screenheight()
        pos_x = (screen_x // 2) - (largura // 2)
        pos_y = (screen_y // 2) - (altura // 2)
        
        self.window.geometry(f"{largura}x{altura}+{pos_x}+{pos_y}")
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        
        try:
            caminho_img = SystemUtils.resource_path(os.path.join("assets/icons", "logo.png")) 
            if os.path.exists(caminho_img):
                pil_img = Image.open(caminho_img)
                pil_img = pil_img.resize((largura, altura), Image.Resampling.LANCZOS)
                img_splash = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(largura, altura))
                lbl = ctk.CTkLabel(self.window, text="", image=img_splash)
                lbl.pack(fill="both", expand=True)
            else:
                ctk.CTkLabel(self.window, text="Watchdog App", fg_color="black", text_color="white").pack(fill="both", expand=True)
        except: pass

        self.parent.after(1500, self._fechar)

    def _fechar(self):
        if self.window:
            self.window.destroy()
        self.on_finish()