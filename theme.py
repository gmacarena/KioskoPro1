# theme.py
# Este archivo centraliza la configuración de los temas.

THEMES = {
    # --- TU TEMA ORIGINAL ---
    "dark": {
        "bg": "#0E1726",        # fondo app
        "card": "#1C2333",      # paneles / cards
        "border": "#2C3449",    # bordes
        "text": "#EAEAEA",      # texto principal
        "muted": "#CCCCCC",     # texto secundario
        "accent": "#45FF6C",    # <--- TU VERDE NEÓN
        "accent_hover": "#32e95b",
        "danger": "#FF4E4E",
        "tab_bg": "#1C2333",
        "tab_selected": "#0E1726",
    },
    
    # --- TU TEMA LIGHT ORIGINAL ---
    "light": {
        "bg": "#F3F6FA",
        "card": "#FFFFFF",
        "border": "#E1E6EF",
        "text": "#1C2333",
        "muted": "#6B7280",
        "accent": "#10B981",      # verde elegante
        "accent_hover": "#0EA371",
        "danger": "#EF4444",
        "tab_bg": "#FFFFFF",
        "tab_selected": "#E9EEF5",
    },

    # --- NUEVA OPCIÓN 1: PROFESIONAL (AZUL) ---
    "profesional": {
        "bg": "#202A3B",        # Fondo Azul Petróleo
        "card": "#2C3A51",      # Tarjetas un poco más claras
        "border": "#3E506E",    # Bordes
        "text": "#F0F4F8",      # Texto
        "muted": "#A0AEC0",     # Texto grisáceo
        "accent": "#3498DB",    # Acento Azul Brillante
        "accent_hover": "#2E86C1",
        "danger": "#E74C3C",
        "tab_bg": "#2C3A51",
        "tab_selected": "#3498DB", # La pestaña seleccionada resalta
    },

    # --- NUEVA OPCIÓN 2: MINIMALISTA (CARBÓN) ---
    "minimal": {
        "bg": "#1A1A1A",        # Fondo Carbón
        "card": "#222222",      # Tarjetas (casi igual)
        "border": "#333333",    # Bordes sutiles
        "text": "#EAEAEA",      # Texto Blanco
        "muted": "#999999",     # Texto Gris
        "accent": "#EAEAEA",    # Acento es el mismo texto blanco
        "accent_hover": "#FFFFFF",
        "danger": "#FF4E4E",
        "tab_bg": "#222222",
        "tab_selected": "#333333", # Pestaña seleccionada gris
    }
}