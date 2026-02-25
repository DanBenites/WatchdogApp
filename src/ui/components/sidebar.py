import os
import customtkinter as ctk
from PIL import Image
from ..colors import AppColors
from ...infrastructure.system_utils import SystemUtils

class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_navigate_callback):
        super().__init__(parent, width=200, corner_radius=0, fg_color=AppColors.BRIGHT_SNOW)
        self.on_navigate_callback = on_navigate_callback
        
        self.grid_rowconfigure(4, weight=1) # Empurrar item 'Conta' para baixo
        self.menu_buttons = []
        self.icons = {}
        
        self._load_icons()
        self._setup_ui()

    def _setup_ui(self):
        # Logo
        self.logo_label = ctk.CTkLabel(
            self, 
            text="WatchdogApp", 
            font=ctk.CTkFont(family="Lexend Deca", size=20, weight="bold"),
            text_color=AppColors.DUSK_BLUE,
            image=self.icons.get("logo"),
            compound="left",
            padx=6 
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Botões de Navegação
        self._create_button("Monitor", "radar", 1)
        self._create_button("Logs", "log", 2)
        self._create_button("Configurações", "settings", 3)
        
        # Botão Conta (separado)
        self.btn_account = self._create_button("Conta", "person", 5)
        self.btn_account.grid(pady=(0, 20))

    def _create_button(self, text, icon_key, row):
        initial_icon = self.icons.get(f"{icon_key}_dark")
        
        btn = ctk.CTkButton(
            self,
            text=text,
            image=initial_icon,
            compound="left",
            font=ctk.CTkFont(family="Arial", size=12, weight="normal"),
            corner_radius=6,
            height=32,
            anchor="w",
            fg_color="transparent",
            text_color=AppColors.CHARCOAL_BLUE,
            hover_color=AppColors.PLATINUM,
            command=lambda: self._on_button_click(text, icon_key)
        )
        btn.grid(row=row, column=0, sticky="ew", padx=10, pady=5)
        
        # Armazena metadados no próprio botão para facilitar a troca de ícone
        btn.icon_key = icon_key 
        self.menu_buttons.append(btn)
        return btn

    def _on_button_click(self, text, icon_key):
        self._update_selection_visuals(text)
        if self.on_navigate_callback:
            self.on_navigate_callback(text)

    def _update_selection_visuals(self, selected_text):
        for btn in self.menu_buttons:
            key = getattr(btn, "icon_key", None)
            
            if btn.cget("text") == selected_text:
                # Selecionado
                btn.configure(
                    fg_color=AppColors.DUSK_BLUE, 
                    text_color="white",
                    hover_color=AppColors.DUSK_BLUE, 
                    image=self.icons.get(f"{key}_light")
                )
            else:
                # Normal
                btn.configure(
                    fg_color="transparent", 
                    text_color=AppColors.CHARCOAL_BLUE,
                    hover_color=AppColors.PLATINUM,
                    image=self.icons.get(f"{key}_dark")
                )

    def definir_selecao(self, texto_botao):
        """ Permite selecionar visualmente um botão via código (ex: ao iniciar) """
        self._update_selection_visuals(texto_botao)

    def _load_icons(self):
        # Usa o SystemUtils para garantir que funcione compilado ou em script
        base_path = SystemUtils.resource_path("assets/icons")
        keys = ["radar", "log", "settings", "person"]

        for key in keys:
            # Dark (Padrão)
            path_dark = os.path.join(base_path, f"{key}_dark.png")
            path_def = os.path.join(base_path, f"{key}.png")
            
            img_dark = None
            if os.path.exists(path_dark): img_dark = Image.open(path_dark)
            elif os.path.exists(path_def): img_dark = Image.open(path_def)
            
            self.icons[f"{key}_dark"] = ctk.CTkImage(img_dark, img_dark, size=(20, 20)) if img_dark else None

            # Light (Selecionado)
            path_light = os.path.join(base_path, f"{key}_light.png")
            img_light = Image.open(path_light) if os.path.exists(path_light) else None
            
            # Fallback para dark se não tiver light
            self.icons[f"{key}_light"] = ctk.CTkImage(img_light, img_light, size=(20, 20)) if img_light else self.icons[f"{key}_dark"]

        # Logo
        path_logo = os.path.join(base_path, "app_icon_off_background.png")
        if os.path.exists(path_logo):
            img = Image.open(path_logo)
            self.icons["logo"] = ctk.CTkImage(img, img, size=(28, 28))
        else:
            self.icons["logo"] = None