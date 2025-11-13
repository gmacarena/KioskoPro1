import tkinter as tk
from tkinter import ttk, messagebox
import sys, traceback

# ─────────────────────────────────────────────────────────────────────
# Importar tu app real del POS
# ─────────────────────────────────────────────────────────────────────
try:
    from ventas_app import VentasApp
except Exception as e:
    print("Error importando ventas_app.VentasApp. Asegúrate de que 'ventas_app.py' está junto a este archivo.")
    traceback.print_exc()
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────
# LOGO (cargado desde un archivo PNG local)
LOGO_PATH= "logo_pos_kiosko.png"

# ─────────────────────────────────────────────────────────────────────
# Usuarios y Roles
# ─────────────────────────────────────────────────────────────────────
USUARIOS = {
    "admin":    {"password": "admin",    "rol": "admin"},
    "cajero1":  {"password": "cajero",   "rol": "cajero"},
    "cajero2":  {"password": "cajero",   "rol": "cajero"},
    "deposito": {"password": "deposito", "rol": "deposito"},
}

# Pestañas permitidas por rol (deben coincidir con los títulos del Notebook en ventas_app)
TABS_POR_ROL = {
    "admin": {
        "📊 Dashboard",
        "💰 Nueva Venta",
        "📦 Productos",
        "📂 Categorías",
        "🧾 Historial Ventas",
        "🏪 Puntos de Venta",
        "🎮 Simular Ventas",
    },
    "cajero": {
        "💰 Nueva Venta",
        "📦 Productos",
        "📂 Categorías",
    },
    "deposito": {
        "📦 Productos",
    },
}
TAB_INICIAL_POR_ROL = {
    "admin": "📊 Dashboard",
    "cajero": "💰 Nueva Venta",
    "deposito": "📦 Productos",
}

# ─────────────────────────────────────────────────────────────────────
# THEME: Claro / Oscuro (paleta Kiosko PRO)
# theme.py
# Este archivo centraliza la configuración de los temas.

THEMES = {
    
    
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


    "dark": {
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

}

# ─────────────────────────────────────────────────────────────────────
# Subclase del POS con permisos + logout + logo en header
class VentasAppConPermisos(VentasApp):
    def __init__(self, usuario: str, rol: str, theme: str = "dark", *args, **kwargs):
        self.usuario = usuario
        self.rol = rol
        self._theme_name = theme
        super().__init__(*args, **kwargs)

        try:
            self.title(f"Kiosko - Sistema de Venta | Usuario: {usuario} | Rol: {rol}")
        except Exception:
            pass

        # Menú y barra logout + menú de tema
        self._inject_menubar()
        self._insert_toolbar()

        # Atajos
        self.bind_all("<Control-l>", lambda e: self._logout())
        self.bind_all("<Control-L>", lambda e: self._logout())

        # Permisos y selección inicial
        self._apply_permissions()
        self.go_to(TAB_INICIAL_POR_ROL.get(rol, "📊 Dashboard"))

        # Tema
        self.apply_theme(self._theme_name)

    # ----------------- Tema -----------------
    # ----------------- Tema -----------------
    def apply_theme(self, name: str):
        self._theme_name = name
        p = THEMES[name]
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Fondo de ventana
        self.configure(bg=p["bg"])
        # Si VentasApp define frames principales, forzamos su bg si existen
        for attr in ("main_frame",):
            if hasattr(self, attr):
                try:
                    getattr(self, attr).configure(style="TFrame") # Usar TFrame base
                except Exception:
                    pass

        # Estilos globales
        style.configure("TFrame", background=p["bg"])
        style.configure("Card.TFrame", background=p["card"])
        style.configure("Header.TFrame", background=p["card"])

        # Labels
        style.configure("TLabel", background=p["card"], foreground=p["text"])
        style.configure("Muted.TLabel", background=p["card"], foreground=p["muted"])
        
        # --- CORRECCIÓN: ESTILO DE LABELFRAME (Títulos de secciones) ---
        style.configure("TLabelFrame", background=p["bg"], foreground=p["muted"], bordercolor=p["border"])
        style.configure("TLabelFrame.Label", background=p["bg"], foreground=p["muted"])
        # --- FIN DE CORRECCIÓN ---


        # Botones
        style.configure("Accent.TButton",
                        font=("Segoe UI", 10, "bold"), padding=(14, 8),
                        background=p["accent"], foreground="#0B1320")
        style.map("Accent.TButton",
                  background=[("active", p["accent_hover"])])
        style.configure("Success.TButton",
                        font=("Segoe UI", 10, "bold"), padding=(14, 8),
                        background=p["accent"], foreground="#0B1320")
        style.configure("Warning.TButton",
                        font=("Segoe UI", 10, "bold"), padding=(14, 8),
                        background="#F59E0B", foreground="#111827")

        # Notebook (tabs)
        style.configure("TNotebook", background=p["bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        padding=(18, 8),
                        font=("Segoe UI", 10, "bold"),
                        background=p["tab_bg"],
                        foreground=p["muted"])
        style.map("TNotebook.Tab",
          background=[("selected", p["text"])], 
          foreground=[("selected", p["bg"])])

        # Treeview
        style.configure("Treeview",
                        background=p["card"], fieldbackground=p["card"],
                        foreground=p["text"], borderwidth=0, rowheight=28)
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 10, "bold"),
                        background=p["tab_selected"], foreground=p["text"],
                        relief="flat")
        style.map("Treeview",
                  background=[("selected", p["accent"])],
                  foreground=[("selected", "#0B1320")])
        
        # --- NUEVA CORRECCIÓN: ESTILO DE SCROLLBARS (Barras de desplazamiento) ---
        style.configure("TScrollbar",
                        gripcount=0,
                        relief="flat",
                        background=p["border"],      # Color del "thumb" (la barra que se arrastra)
                        troughcolor=p["card"],     # Color del "canal" (el fondo)
                        bordercolor=p["card"],
                        arrowcolor=p["text"])
        
        style.configure("Vertical.TScrollbar", 
                        background=p["border"],
                        troughcolor=p["card"])
                        
        style.configure("Horizontal.TScrollbar", 
                        background=p["border"],
                        troughcolor=p["card"])
        
        # Mapeo para que el "thumb" cambie de color al pasar el mouse
        style.map("TScrollbar",
            background=[('active', p["muted"]), ('!active', p["border"])]
        )
        # --- FIN DE CORRECCIÓN ---

        # status bar (si existe)
        try:
            if hasattr(self, "status_text"):
                # suele ser un StringVar; el widget usa estilos por defecto
                pass
        except Exception:
            pass

        # Barra superior creada por nosotros
        if hasattr(self, "_toolbar"):
            self._toolbar.configure(style="Card.TFrame")
            for c in self._toolbar.winfo_children():
                if isinstance(c, ttk.Label):
                    c.configure(style="Muted.TLabel")

                    
    def toggle_theme(self):
        new_theme = "light" if self._theme_name == "dark" else "dark"
        self.apply_theme(new_theme)

    # ----------------- Menú / Toolbar / Logout -----------------
    def _inject_menubar(self):
        try:
            menubar = self.nametowidget(self["menu"]) if self["menu"] else None
        except Exception:
            menubar = None
        if menubar is None:
            menubar = tk.Menu(self)
            self.config(menu=menubar)

        # Cuenta
        cuenta_menu = tk.Menu(menubar, tearoff=0)
        cuenta_menu.add_command(label="Cerrar sesión\tCtrl+L", command=self._logout)
        menubar.add_cascade(label="Cuenta", menu=cuenta_menu)

        # Ver
        ver_menu = tk.Menu(menubar, tearoff=0)
        ver_menu.add_command(label="Tema: Claro / Oscuro", command=self.toggle_theme)
        menubar.add_cascade(label="Ver", menu=ver_menu)

    def _insert_toolbar(self):
        self._toolbar = ttk.Frame(self, padding=(8, 4), style="Card.TFrame")
        self._toolbar.pack(side="top", fill="x")
        ttk.Label(self._toolbar, text=f"Usuario: {self.usuario}  |  Rol: {self.rol}",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(self._toolbar, text="Cerrar sesión", command=self._logout).pack(side="right")

    def _logout(self):
        if not messagebox.askyesno("Cerrar sesión", "¿Seguro que deseas cerrar sesión?"):
            return
        try:
            self.destroy()
        finally:
            abrir_login(theme=self._theme_name)

    # ----------------- Permisos -----------------
    def _apply_permissions(self):
        permitidas = TABS_POR_ROL.get(self.rol, set())
        try:
            for tab_id in list(self.nb.tabs()):
                titulo = self.nb.tab(tab_id, "text")
                if titulo not in permitidas:
                    self.nb.hide(tab_id)
        except Exception as e:
            messagebox.showerror("Permisos", f"No se pudieron aplicar permisos.\n\n{e}")

    def go_to(self, titulo_tab: str):
        try:
            for tab_id in self.nb.tabs():
                if self.nb.tab(tab_id, "text") == titulo_tab:
                    self.nb.select(tab_id)
                    return
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────
# Login Moderno (con logo fijo arriba) + tema claro/oscuro
class LoginApp(tk.Tk):
    def __init__(self, theme: str = "dark"):
        super().__init__()
        self._theme_name = theme
        self.title("Iniciar sesión | Kiosko Pro")
        self.geometry("560x480")
        self.minsize(520, 400)

        self._setup_style()
        self._build_ui()
        self.apply_theme(self._theme_name)

    def _setup_style(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

    def apply_theme(self, name: str):
        self._theme_name = name
        p = THEMES[name]
        self.configure(bg=p["bg"])

        # Estilos del login
        self.style.configure("Card.TFrame", background=p["card"])
        self.style.configure("Header.TLabel",
                             font=("Segoe UI", 16, "bold"),
                             foreground=p["text"], background=p["card"])
        self.style.configure("Sub.TLabel",
                             font=("Segoe UI", 10),
                             foreground=p["muted"], background=p["card"])
        self.style.configure("Muted.TLabel",
                             font=("Segoe UI", 9),
                             foreground=p["muted"], background=p["card"])
        self.style.configure("TCheckbutton", background=p["card"])

        # Botón primario (usamos tk.Button para asegurar color en Windows)
        self._btn_login.configure(
            bg=p["accent"], fg="#0B1320",
            activebackground=p["accent_hover"], activeforeground="#0B1320"
        )

        # Tarjeta / header background
        self._card.configure(style="Card.TFrame")
        self._form.configure(style="Card.TFrame")
        self._logo_frame.configure(bg=p["bg"])  # logo sobre fondo app para quedar "fijo arriba"

        # Entrys y error
        self._error_label.configure(background=p["card"], foreground=THEMES[name]["danger"])

    def _build_ui(self):
        # Header superior fijo con logo
        self._logo_frame = tk.Frame(self, bd=0)
        # --- CAMBIO: Añadimos padding (espacio) arriba del logo ---
        self._logo_frame.pack(side="top", fill="x", pady=(20, 0))
        
        # Cargar el logo desde el archivo PNG local
        try:
            self._logo_img = tk.PhotoImage(file=LOGO_PATH)
            logo = tk.Label(self._logo_frame, image=self._logo_img, bd=0)
            logo.pack()
        except Exception as e:
            print(f"Error cargando logo: {e}")
            tk.Label(self._logo_frame, text="Kiosko PRO", font=("Segoe UI", 18, "bold")).pack()

        # --- CAMBIO: Eliminamos self._shadow y .place() ---

        # Card central (ahora se "empaqueta" debajo del logo)
        self._card = ttk.Frame(self, style="Card.TFrame")
        # Usamos .pack() en lugar de .place() para que se apile
        self._card.pack(side="top", pady=15, padx=30, fill="x") 
        # --- FIN CAMBIO ---

        header = ttk.Label(self._card, text="Iniciá sesión", style="Header.TLabel")
        header.pack(pady=(18, 0))
        sub = ttk.Label(self._card, text="Ingresá tus credenciales para continuar", style="Sub.TLabel")
        sub.pack(pady=(4, 14))

        self._form = ttk.Frame(self._card, style="Card.TFrame")
        self._form.pack(padx=24, fill="x")

        ttk.Label(self._form, text="Usuario", style="Muted.TLabel").pack(anchor="w")
        self.var_user = tk.StringVar()
        ent_user = ttk.Entry(self._form, textvariable=self.var_user, font=("Segoe UI", 10))
        ent_user.pack(fill="x", pady=(2, 10))
        ent_user.focus()

        ttk.Label(self._form, text="Contraseña", style="Muted.TLabel").pack(anchor="w")
        self.var_pass = tk.StringVar()
        self.ent_pass = ttk.Entry(self._form, textvariable=self.var_pass, show="*", font=("Segoe UI", 10))
        self.ent_pass.pack(fill="x", pady=(2, 8))

        self.var_show = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(self._form, text="Mostrar contraseña", variable=self.var_show,
                              command=lambda: self.ent_pass.config(show="" if self.var_show.get() else "*"))
        chk.pack(anchor="w", pady=(0, 6))

        self._error_label = ttk.Label(self._form, text="", style="Sub.TLabel")
        self._error_label.pack(anchor="w")
        self._set_error("")

        # BOTÓN: usamos tk.Button para asegurar colores en Windows
        self._btn_login = tk.Button(self._card, text="Ingresar",
                                    font=("Segoe UI", 10, "bold"),
                                    relief="flat", command=self._on_login)
        # --- CAMBIO: Añadimos padding inferior al botón ---
        self._btn_login.pack(padx=24, fill="x", pady=(14, 20), ipady=6)

        # Toggle de tema también desde el login (Ctrl+T)
        self.bind("<Control-t>", lambda e: self._toggle_theme())
        self.bind("<Return>", lambda e: self._on_login())

    def _toggle_theme(self):
        self.apply_theme("light" if self._theme_name == "dark" else "dark")

    def _set_error(self, msg: str):
        self._error_label.configure(text=msg)

    def _on_login(self):
        usuario = (self.var_user.get() or "").strip()
        password = self.var_pass.get() or ""
        data = USUARIOS.get(usuario)
        if not data or data["password"] != password:
            self._set_error("Usuario o contraseña incorrectos.")
            self._shake()
            return

        rol = data["rol"]
        theme_for_pos = self._theme_name  # respetamos el tema elegido en el login
        self.destroy()
        abrir_pos(usuario, rol, theme_for_pos)

    # Animación "shake"
    def _shake(self):
        x, y = self.winfo_x(), self.winfo_y()
        for dx in (8, -16, 12, -8, 4, -2, 0):
            self.geometry(f"+{x+dx}+{y}")
            self.update_idletasks()
            self.after(18)

# ─────────────────────────────────────────────────────────────────────
# Lanzadores
# ─────────────────────────────────────────────────────────────────────
def abrir_pos(usuario: str, rol: str, theme: str = "dark"):
    app = VentasAppConPermisos(usuario, rol, theme=theme)
    app.mainloop()

def abrir_login(theme: str = "dark"):
    LoginApp(theme=theme).mainloop()

# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    LoginApp(theme="dark").mainloop()
