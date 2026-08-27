THEMES = {
    "dark": {
        "bg": "#1e1e1e",
        "bg_secondary": "#2d2d2d",
        "surface": "#2d2d2d",
        "bg_tertiary": "#383838",
        "fg": "#ffffff",
        "fg_secondary": "#aaaaaa",
        "accent": "#0078d4",
        "accent_hover": "#1a8fe3",
        "success": "#44bb44",
        "warning": "#ffaa00",
        "danger": "#ff4444",
        "border": "#444444",
        "entry_bg": "#3c3c3c",
        "button_bg": "#0078d4",
        "button_fg": "#ffffff",
        "scrollbar_bg": "#2d2d2d",
        "scrollbar_fg": "#555555",
        "card_bg": "#2d2d2d",
        "hover_bg": "#3c3c3c",
        "tab_bg": "#252525",
        "tab_active": "#1e1e1e",
        "graph_line": "#0078d4",
        "graph_fill": "#003d6b",
        "graph_grid": "#333333",
        "graph_text": "#888888",
    },
    "light": {
        "bg": "#f0f0f0",
        "bg_secondary": "#ffffff",
        "surface": "#ffffff",
        "bg_tertiary": "#e5e5e5",
        "fg": "#1a1a1a",
        "fg_secondary": "#666666",
        "accent": "#0063b1",
        "accent_hover": "#0078d4",
        "success": "#2e7d32",
        "warning": "#f57c00",
        "danger": "#c62828",
        "border": "#d0d0d0",
        "entry_bg": "#ffffff",
        "button_bg": "#0063b1",
        "button_fg": "#ffffff",
        "scrollbar_bg": "#e0e0e0",
        "scrollbar_fg": "#aaaaaa",
        "card_bg": "#ffffff",
        "hover_bg": "#e8e8e8",
        "tab_bg": "#e0e0e0",
        "tab_active": "#ffffff",
        "graph_line": "#0063b1",
        "graph_fill": "#cce0f5",
        "graph_grid": "#d0d0d0",
        "graph_text": "#666666",
    }
}


class ThemeManager:
    def __init__(self, config):
        self.config = config
        self.current_theme_name = config.get("theme", "dark")
        self.theme = THEMES.get(self.current_theme_name, THEMES["dark"])

    def set_theme(self, theme_name):
        if theme_name in THEMES:
            self.current_theme_name = theme_name
            self.theme = THEMES[theme_name]
            self.config["theme"] = theme_name
            return True
        return False

    def toggle_theme(self):
        new = "light" if self.current_theme_name == "dark" else "dark"
        return self.set_theme(new)

    def get(self, key, default=None):
        return self.theme.get(key, default)
