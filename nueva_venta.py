import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List, Dict, Any, Optional
import datetime
import os
import logging
import subprocess
import sys
import threading  # Importar threading

PDF_ENGINE = None
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    PDF_ENGINE = "reportlab"
except Exception:
    try:
        from fpdf import FPDF
        PDF_ENGINE = "fpdf"
    except Exception:
        PDF_ENGINE = None

# --- CORRECCIÓN ---
# Asegurarnos de importar CategoriaRepo para el bloque de prueba
from repos import ProductoRepo, VentaRepo, PuntoVentaRepo, CategoriaRepo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NuevaVentaPro")

CURRENCY_QUANTIZE = Decimal('0.01')

def money(v) -> str:
    try:
        d = Decimal(v).quantize(CURRENCY_QUANTIZE, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError):
        d = Decimal('0.00')
    return f"${d:,.2f}"

@dataclass
class VentaItem:
    producto_id: int
    codigo_barras: str
    nombre: str
    precio: Decimal
    cantidad: int = 1
    stock: int = 0

    def __post_init__(self):
        if self.cantidad < 0:
            self.cantidad = 0

    @property
    def subtotal(self) -> Decimal:
        return (self.precio * Decimal(self.cantidad)).quantize(CURRENCY_QUANTIZE, rounding=ROUND_HALF_UP)
    
    @property
    def tiene_stock(self) -> bool:
        return self.stock >= self.cantidad
    
    @property
    def stock_disponible(self) -> int:
        return max(0, self.stock)
    
    def puede_vender(self, cantidad=None) -> bool:
        if cantidad is None:
            cantidad = self.cantidad
        return self.stock >= cantidad and cantidad > 0

class PagoDialog(tk.Toplevel):
    """Diálogo para procesar el pago de la venta, con botones Aceptar/Cancelar"""
    
    def __init__(self, parent, total: Decimal):
        super().__init__(parent)
        self.parent = parent
        self.total = total
        self.resultado = None
        
        self.title("💳 PROCESAR PAGO")
        self.geometry("420x340")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._construir_ui()
        
    def _construir_ui(self):
        main_frame = ttk.Frame(self, padding="18")
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text="TOTAL A PAGAR:", 
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 6))
        ttk.Label(main_frame, text=money(self.total), 
                 font=("Segoe UI", 22, "bold"), foreground="#27ae60").pack(pady=(0, 14))
        
        pago_frame = ttk.LabelFrame(main_frame, text="FORMA DE PAGO", padding="10")
        pago_frame.pack(fill="x", pady=6)
        
        self.forma_pago = tk.StringVar(value="EFECTIVO")
        
        rb_frame = ttk.Frame(pago_frame)
        rb_frame.pack(fill="x")
        ttk.Radiobutton(rb_frame, text="💰 Efectivo", variable=self.forma_pago, value="EFECTIVO").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        ttk.Radiobutton(rb_frame, text="💳 Tarjeta Débito", variable=self.forma_pago, value="TARJETA_DEBITO").grid(row=0, column=1, sticky="w", padx=6, pady=2)
        ttk.Radiobutton(rb_frame, text="💳 Tarjeta Crédito", variable=self.forma_pago, value="TARJETA_CREDITO").grid(row=1, column=0, sticky="w", padx=6, pady=2)
        ttk.Radiobutton(rb_frame, text="📱 Transferencia", variable=self.forma_pago, value="TRANSFERENCIA").grid(row=1, column=1, sticky="w", padx=6, pady=2)
        
        # Monto recibido (solo para efectivo)
        self.monto_frame = ttk.Frame(main_frame)
        self.monto_frame.pack(fill="x", pady=10)
        ttk.Label(self.monto_frame, text="Monto Recibido:").pack(side="left")
        self.entry_monto = ttk.Entry(self.monto_frame, width=18, font=("Segoe UI", 12))
        self.entry_monto.pack(side="left", padx=6)
        self.entry_monto.bind("<KeyRelease>", self._calcular_vuelto)
        
        self.lbl_vuelto = ttk.Label(main_frame, text="Vuelto: $0.00", font=("Segoe UI", 12, "bold"))
        self.lbl_vuelto.pack(pady=6)
        
        # Botones Aceptar/Cancelar
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=12)
        
        aceptar_btn = ttk.Button(btn_frame, text="✅ ACEPTAR PAGO", command=self._confirmar_pago, width=16)
        aceptar_btn.pack(side="left", padx=6)
        cancel_btn = ttk.Button(btn_frame, text="❌ CANCELAR", command=self._cancelar, width=12)
        cancel_btn.pack(side="right", padx=6)
        
        # Atajos
        self.bind("<Return>", lambda e: self._confirmar_pago())
        self.bind("<Escape>", lambda e: self._cancelar())
        self.forma_pago.trace('w', self._on_forma_pago_change)
        self._on_forma_pago_change()
        self.entry_monto.focus()

    def _on_forma_pago_change(self, *args):
        if self.forma_pago.get() == "EFECTIVO":
            self.monto_frame.pack(fill="x", pady=10)
            self.lbl_vuelto.pack(pady=6)
            self.entry_monto.focus()
        else:
            self.monto_frame.pack_forget()
            self.lbl_vuelto.pack_forget()

    def _calcular_vuelto(self, event=None):
        try:
            monto_recibido = Decimal(self.entry_monto.get() or "0")
            vuelto = monto_recibido - self.total
            if vuelto >= 0:
                self.lbl_vuelto.config(text=f"Vuelto: {money(vuelto)}", foreground="#27ae60")
            else:
                self.lbl_vuelto.config(text=f"Faltante: {money(-vuelto)}", foreground="#e74c3c")
        except InvalidOperation:
            self.lbl_vuelto.config(text="Vuelto: $0.00", foreground="#e74c3c")

    def _confirmar_pago(self):
        forma_pago = self.forma_pago.get()
        if forma_pago == "EFECTIVO":
            try:
                monto_recibido_str = self.entry_monto.get() or "0"
                monto_recibido = Decimal(monto_recibido_str)
                if monto_recibido < self.total:
                    messagebox.showwarning("Pago Insuficiente", "El monto recibido es menor al total.")
                    return
                self.resultado = {
                    "forma_pago": forma_pago,
                    "monto_recibido": float(monto_recibido),
                    "vuelto": float(monto_recibido - self.total)
                }
                self.destroy()
            except InvalidOperation:
                messagebox.showerror("Error", "Monto recibido no válido")
                return
        else:
            self.resultado = {
                "forma_pago": forma_pago,
                "monto_recibido": float(self.total),
                "vuelto": 0.0
            }
            self.destroy()

    def _cancelar(self):
        self.resultado = None
        self.destroy()

class AutoCompleteEntry(ttk.Entry):
    def __init__(self, parent, suggestions_callback, on_select_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.suggestions_callback = suggestions_callback
        self.on_select_callback = on_select_callback
        self.parent = parent
        self.listbox = None
        self.bind('<KeyRelease>', self._on_keyrelease)
        self.bind('<FocusOut>', self._on_focus_out)
        self.bind('<Down>', self._on_down)
        self.bind('<Up>', self._on_up)
        self.bind('<Return>', self._on_return)
        self.bind('<Escape>', self._on_escape)

    def _on_keyrelease(self, event):
        if event.keysym in ['Down', 'Up', 'Return', 'Escape']:
            return
        self._show_suggestions()

    def _show_suggestions(self):
        query = self.get().strip()
        if not query or len(query) < 1:  # Reducido a 1 carácter para mejor UX
            self._hide_listbox()
            return
        suggestions = self.suggestions_callback(query)
        if not suggestions:
            self._hide_listbox()
            return
        self._create_listbox()
        self.listbox.delete(0, tk.END)
        for prod in suggestions[:8]:
            display_text = f"{prod.get('codigo_barras', '')} - {prod['nombre']} - ${float(prod['precio']):.2f}"
            self.listbox.insert(tk.END, display_text)
            self.listbox.data.append(prod)

    def _create_listbox(self):
        if self.listbox:
            self.listbox.destroy()
        x = self.winfo_x()
        y = self.winfo_y() + self.winfo_height()
        width = self.winfo_width()
        self.listbox = tk.Listbox(self.master, width=width, height=6, font=("Segoe UI", 9), bg="white", relief="solid", border=1)
        self.listbox.place(x=x, y=y)
        self.listbox.data = []
        self.listbox.bind('<Double-Button-1>', self._on_listbox_select)
        self.listbox.bind('<Return>', self._on_listbox_select)

    def _hide_listbox(self):
        if self.listbox:
            self.listbox.destroy()
            self.listbox = None

    def _on_focus_out(self, event):
        self.after(150, self._hide_listbox)

    def _on_down(self, event):
        if self.listbox and self.listbox.winfo_ismapped():
            self.listbox.focus_set()
            if self.listbox.size() > 0:
                self.listbox.selection_set(0)
            return "break"

    def _on_up(self, event):
        if self.listbox and self.listbox.winfo_ismapped():
            self.listbox.focus_set()
            if self.listbox.size() > 0:
                self.listbox.selection_set(tk.END)
            return "break"

    def _on_return(self, event):
        if self.listbox and self.listbox.winfo_ismapped() and self.listbox.curselection():
            self._on_listbox_select(event)
            return "break"
        else:
            # Llamar al método del padre para agregar desde la entrada
            if hasattr(self.parent, '_add_from_entry'):
                self.parent._add_from_entry()
            elif hasattr(self.master, '_add_from_entry'):
                self.master._add_from_entry()
            return "break"

    def _on_escape(self, event):
        self._hide_listbox()

    def _on_listbox_select(self, event):
        if not self.listbox or not self.listbox.curselection():
            return
        index = self.listbox.curselection()[0]
        if index < len(self.listbox.data):
            product_data = self.listbox.data[index]
            self.on_select_callback(product_data)
            self.delete(0, tk.END)
            self._hide_listbox()

class NuevaVentaFrame(ttk.Frame):
    FONT_BOLD = ("Segoe UI", 10, "bold")
    FONT_NORMAL = ("Segoe UI", 10)
    FONT_LARGE = ("Segoe UI", 12, "bold")
    COLOR_PRIMARY = "#2c3e50"
    COLOR_SECONDARY = "#3498db"
    COLOR_SUCCESS = "#27ae60"
    COLOR_WARNING = "#e74c3c"
    
    def __init__(self, master: Optional[tk.Misc] = None) -> None:
        super().__init__(master)
        self.items: List[VentaItem] = []
        
        # Referencia a la App principal para acceder al caché
        self.app_root = self.winfo_toplevel()
        
        self.punto_venta_id = self._obtener_punto_venta()
        self._setup_advanced_style()
        self._build_professional_ui()
        self._bind_advanced_shortcuts()
        self.lector_activo = True
        self.buffer_lector = ""
        self.bind('<Key>', self._capturar_lector_barras)
        
        # Cargar los productos desde el caché principal la primera vez
        self._actualizar_cache_productos()

    def _actualizar_cache_productos(self):
        """
        Actualiza la lista de productos leyéndola del CACHÉ CENTRAL de la app.
        """
        try:
            if hasattr(self.app_root, 'cache_productos'):
                self._productos_cache = self.app_root.cache_productos
                logger.info(f"Caché de productos de NuevaVenta actualizado desde app_root: {len(self._productos_cache)} productos")
            else:
                # Fallback por si acaso (consulta directa a la BD)
                self._productos_cache = ProductoRepo.listar()
                logger.warning("NuevaVenta usó fallback de BD. 'app_root.cache_productos' no encontrado.")
        except Exception as e:
            logger.error(f"Error actualizando cache de productos desde app_root: {e}")
            self._productos_cache = []

    def _get_productos_fresh(self):
        """Obtiene productos frescos (Ahora lee de la variable local sincronizada con el caché)"""
        # Si el caché local está vacío (ej. al inicio), intenta cargarlo
        if not hasattr(self, '_productos_cache') or not self._productos_cache:
            self._actualizar_cache_productos()
        return self._productos_cache

    def _capturar_lector_barras(self, event):
        if not self.lector_activo:
            return
        if event.char and event.char.isprintable():
            self.buffer_lector += event.char
        if event.keysym == 'Return' and self.buffer_lector:
            codigo = self.buffer_lector.strip()
            self.buffer_lector = ""
            if len(codigo) >= 3:
                self._procesar_codigo_barras(codigo)

    def _obtener_punto_venta(self) -> int:
        try:
            puntos = []
            if hasattr(self.app_root, 'cache_puntos_venta'):
                puntos = self.app_root.cache_puntos_venta
            
            if not puntos:
                # Si el caché está vacío, consulta la BD como fallback
                puntos = PuntoVentaRepo.listar()
                if not puntos:
                    messagebox.showerror("Error", "No hay puntos de venta configurados. Contacte al administrador.")
                    return 1
            
            for punto in puntos:
                if 'cliente' in punto['nombre'].lower() or 'pc' in punto['nombre'].lower():
                    return punto['id']
            return puntos[0]['id']
        except Exception as e:
            logger.error(f"Error obteniendo punto de venta: {e}")
            messagebox.showerror("Error", f"No se pudo obtener el punto de venta: {e}")
            return 1

    def _setup_advanced_style(self) -> None:
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("Professional.TFrame", background="#ecf0f1")
        s.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.COLOR_PRIMARY)
        s.configure("Total.TLabel", font=("Segoe UI", 12, "bold"), foreground=self.COLOR_SUCCESS)
        s.configure("Accent.TButton", background=self.COLOR_SECONDARY, foreground="white")
        s.configure("Treeview", font=self.FONT_NORMAL, rowheight=28, borderwidth=0)
        s.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background=self.COLOR_PRIMARY, foreground="white", relief="flat")
        s.map("Treeview", background=[("selected", self.COLOR_SECONDARY)], foreground=[("selected", "white")])

    def _build_professional_ui(self) -> None:
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=0, pady=0)
        
        main_container = ttk.Frame(container, style="Professional.TFrame")
        main_container.pack(fill="both", expand=True, padx=8, pady=8)

        # 1. PANEL SUPERIOR (FIJO ARRIBA)
        top_section = ttk.LabelFrame(main_container, text="⚡ ENTRADA RÁPIDA - LECTOR CÓDIGOS DE BARRAS", padding=(15, 10))
        top_section.pack(side="top", fill="x", pady=(0, 8))

        input_row = ttk.Frame(top_section)
        input_row.pack(fill="x", pady=5)
        ttk.Label(input_row, text="Código/Nombre:", font=self.FONT_BOLD).pack(side="left", padx=(0, 8))

        self.entry_codigo = AutoCompleteEntry(
            input_row, 
            suggestions_callback=self._get_suggestions,
            on_select_callback=self._on_suggestion_selected,
            width=45,
            font=self.FONT_NORMAL
        )
        self.entry_codigo.pack(side="left", padx=8, fill="x", expand=True)
        
        ttk.Button(input_row, text="➕ Agregar", command=self._add_from_entry, width=10).pack(side="left", padx=4)

        btn_frame = ttk.Frame(input_row)
        btn_frame.pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🔍 Buscar Productos (F2)", command=self._show_busqueda_avanzada).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="📋 Lista Productos (F3)", command=self._show_lista_productos).pack(side="left", padx=2)

        lector_frame = ttk.Frame(top_section)
        lector_frame.pack(fill="x", pady=5)
        self.lector_status = ttk.Label(lector_frame, text="✅ LECTOR ACTIVO - Escanee códigos de barras", foreground=self.COLOR_SUCCESS, font=("Segoe UI", 9, "bold"))
        self.lector_status.pack(side="left")
        ttk.Button(lector_frame, text="⏸️ Pausar Lector", command=self._toggle_lector, width=12).pack(side="right", padx=5)
        
        ttk.Button(lector_frame, text="🔄 Actualizar Lista", command=self._actualizar_cache_productos, width=14).pack(side="right", padx=5)

        # --- INICIO: CORRECCIÓN DE LAYOUT ---

        # 2. BARRA DE ESTADO (FIJA ABAJO)
        self.status_bar = ttk.Label(main_container, text="Listo - Escanee productos o use F2 para búsqueda manual", 
                                   relief="sunken", anchor="w", font=("Segoe UI", 9))
        self.status_bar.pack(side="bottom", fill="x", pady=(8, 0))

        # 3. BARRA DE BOTONES/TOTALES (FIJA ABAJO, ENCIMA DE LA BARRA DE ESTADO)
        bottom_section = ttk.Frame(main_container)
        bottom_section.pack(side="bottom", fill="x", pady=(8, 0)) 

        # Configurar el grid del 'bottom_section'
        bottom_section.columnconfigure(0, weight=1) # Col 0 (Totales) se expande
        bottom_section.columnconfigure(1, weight=0) # Col 1 (Botones) NO se expande

        # Panel de Totales (va en grid col 0)
        totals_panel = ttk.LabelFrame(bottom_section, text="💰 TOTALES", padding=(15, 10))
        totals_panel.grid(row=0, column=0, sticky="ew", padx=(0, 5)) 

        # Panel de Acciones (va en grid col 1)
        actions_panel = ttk.Frame(bottom_section)
        actions_panel.grid(row=0, column=1, sticky="ns", padx=(5, 0)) 
        
        totals_grid = ttk.Frame(totals_panel)
        totals_grid.pack(fill="x") 

        self.lbl_items = ttk.Label(totals_grid, text="Items: 0", font=self.FONT_BOLD)
        self.lbl_items.grid(row=0, column=0, padx=20, pady=2, sticky="w")
        self.lbl_subtotal = ttk.Label(totals_grid, text="Subtotal: $0.00", font=self.FONT_BOLD)
        self.lbl_subtotal.grid(row=0, column=1, padx=20, pady=2, sticky="w")
        self.lbl_total = ttk.Label(totals_grid, text="TOTAL: $0.00", font=self.FONT_LARGE, foreground=self.COLOR_SUCCESS)
        self.lbl_total.grid(row=0, column=2, padx=20, pady=2, sticky="w")
        
        # Hacemos que la grilla de totales se expanda
        totals_grid.columnconfigure(0, weight=1)
        totals_grid.columnconfigure(1, weight=1)
        totals_grid.columnconfigure(2, weight=1)

        action_buttons = [
            ("🧾 Finalizar (F12)", self._finalizar_venta, self.COLOR_SUCCESS),
            ("🔄 Limpiar (F11)", self._limpiar_venta, "#95a5a6"),
            ("🗑 Eliminar (Del)", self._eliminar_seleccionado, self.COLOR_WARNING),
            ("➕ Agregar (Insert)", self._show_busqueda_avanzada, self.COLOR_SECONDARY),
        ]
        
        # Usamos .grid() dentro de 'actions_panel' para apilarlos verticalmente
        for idx, (text, command, color) in enumerate(action_buttons):
            btn = ttk.Button(actions_panel, text=text, command=command, width=16)
            btn.grid(row=idx, column=0, padx=3, pady=2, sticky="ew") 

        # 4. PANEL MEDIO (LISTA DE PRODUCTOS) (SE EXPANDE PARA LLENAR EL RESTO)
        middle_section = ttk.LabelFrame(main_container, text="🛒 PRODUCTOS EN VENTA", padding=(10, 5))
        middle_section.pack(side="top", fill="both", expand=True, pady=8)

        # --- FIN: CORRECCIÓN DE LAYOUT ---

        tree_frame = ttk.Frame(middle_section)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("codigo", "producto", "cantidad", "precio", "subtotal", "stock")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=14)
        
        column_config = [
            ("codigo", "Código", 120),
            ("producto", "Producto", 280),
            ("cantidad", "Cant.", 80),
            ("precio", "Precio Unit.", 100),
            ("subtotal", "Subtotal", 120),
            ("stock", "Stock", 80)
        ]
        
        for col, text, width in column_config:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
            
        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # --- CORRECCIÓN ERROR 3 (Colores) ---
        # Quitamos los 'background' fijos para que hereden del tema
        self.tree.tag_configure("even")
        self.tree.tag_configure("odd")
        # --- FIN CORRECCIÓN ---
        
        self.tree.tag_configure("sin_stock", background="#ffe6e6", foreground="#cc0000")
        self.tree.tag_configure("bajo_stock", background="#fff3cd", foreground="#856404")

        self._setup_context_menu()
        self._actualizar_totales()
        self.entry_codigo.focus()

    def _setup_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0, font=("Segoe UI", 9))
        self.context_menu.add_command(label="✏️ Editar cantidad", command=self._menu_editar_cantidad)
        self.context_menu.add_command(label="➖ Disminuir 1", command=self._menu_disminuir_1)
        self.context_menu.add_command(label="➕ Aumentar 1", command=self._menu_aumentar_1)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Eliminar ítem", command=self._menu_eliminar_item)
        self.context_menu.add_command(label="📊 Ver información", command=self._menu_ver_info)
        
        self.tree.bind("<Double-1>", self._on_doble_clic)
        self.tree.bind("<Button-3>", self._on_clic_derecho)
        self.tree.bind("<Delete>", lambda e: self._eliminar_seleccionado())

    def _bind_advanced_shortcuts(self):
        shortcuts = [
            ('<F2>', lambda e: self._show_busqueda_avanzada()),
            ('<F3>', lambda e: self._show_lista_productos()),
            ('<F5>', lambda e: self._actualizar_cache_productos()),
            ('<F11>', lambda e: self._limpiar_venta()),
            ('<F12>', lambda e: self._finalizar_venta()),
            ('<Insert>', lambda e: self._show_busqueda_avanzada()),
            ('<Delete>', lambda e: self._eliminar_seleccionado()),
            ('<Control-plus>', lambda e: self._menu_aumentar_1()),
            ('<Control-minus>', lambda e: self._menu_disminuir_1()),
            ('<Control-e>', lambda e: self._menu_editar_cantidad()),
        ]
        for key, func in shortcuts:
            self.bind_all(key, func)

    def _get_suggestions(self, query: str) -> List[Dict]:
        """Obtener sugerencias de productos (leyendo de caché)"""
        try:
            if not query or len(query) < 1:
                return []
                
            productos = self._get_productos_fresh()
            query_lower = query.lower().strip()
            resultados = []
            
            for prod in productos:
                if not prod.get('activo', True):
                    continue
                    
                nombre_match = query_lower in prod['nombre'].lower()
                codigo_match = query_lower in prod.get('codigo_barras', '').lower()
                
                if nombre_match or codigo_match:
                    resultados.append(prod)
            
            resultados.sort(key=lambda p: (
                query_lower == p.get('codigo_barras', '').lower(),
                query_lower in p['nombre'].lower(),
                p['nombre'].lower().startswith(query_lower)
            ), reverse=True)
            
            return resultados[:10]
            
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return []

    def _procesar_entrada_producto(self, entrada: str):
        """Procesar entrada de producto (leyendo de caché)"""
        try:
            entrada = entrada.strip()
            if not entrada:
                self._actualizar_status("Entrada vacía")
                return
                
            self._actualizar_status(f"Buscando: {entrada}")
            
            producto_encontrado = None
            productos = self._get_productos_fresh()
            
            for prod in productos:
                if not prod.get('activo', True):
                    continue
                    
                codigo_barras = prod.get('codigo_barras', '').strip()
                if codigo_barras and codigo_barras == entrada:
                    producto_encontrado = prod
                    break
                    
                if prod['nombre'].strip().lower() == entrada.lower():
                    producto_encontrado = prod
                    break
            
            if not producto_encontrado:
                for prod in productos:
                    if not prod.get('activo', True):
                        continue
                        
                    if entrada.lower() in prod['nombre'].lower():
                        producto_encontrado = prod
                        break
            
            if not producto_encontrado:
                self._actualizar_status(f"Producto no encontrado: {entrada}")
                messagebox.showwarning("No encontrado", 
                    f"No se encontró el producto: {entrada}\n\n"
                    f"Verifique que:\n"
                    f"• El producto esté activo\n"
                    f"• El código/nombre sea correcto\n"
                    f"• El producto exista en el sistema")
                return

            if not producto_encontrado.get('activo', True):
                self._actualizar_status(f"Producto inactivo: {producto_encontrado['nombre']}")
                messagebox.showwarning("Producto Inactivo", 
                    f"El producto '{producto_encontrado['nombre']}' está inactivo\n"
                    f"Actívelo desde la pestaña de Productos")
                return
                
            item = VentaItem(
                producto_id=producto_encontrado['id'],
                codigo_barras=producto_encontrado.get('codigo_barras', ''),
                nombre=producto_encontrado['nombre'],
                precio=Decimal(str(producto_encontrado['precio'])),
                cantidad=1,
                stock=producto_encontrado.get('stock', 0)
            )
            
            self._agregar_item(item)
            self._actualizar_status(f"Agregado: {producto_encontrado['nombre']}")
            
        except Exception as e:
            logger.error(f"Error procesando entrada '{entrada}': {e}")
            messagebox.showerror("Error", 
                f"Error al procesar producto '{entrada}':\n{str(e)}")

    def _procesar_codigo_barras(self, codigo: str):
        """Procesar código de barras escaneado (leyendo de caché)"""
        if not self.lector_activo:
            return
        try:
            producto_encontrado = None
            productos = self._get_productos_fresh()
            
            for prod in productos:
                if (prod.get('codigo_barras') == codigo and 
                    prod.get('activo', True)):
                    producto_encontrado = prod
                    break
            
            if producto_encontrado:
                self._agregar_producto_desde_datos(producto_encontrado, 1)
                self._actualizar_status(f"Escaneado: {producto_encontrado['nombre']}")
            else:
                self._actualizar_status(f"Código no encontrado: {codigo}")
                messagebox.showwarning("Código inválido", 
                    f"No se encontró producto para código: {codigo}\n\n"
                    f"Verifique que:\n"
                    f"• El producto esté activo\n"
                    f"• El código esté correctamente asignado")
                    
        except Exception as e:
            logger.error(f"Error procesando código de barras: {e}")
            messagebox.showerror("Error", f"Error al procesar código: {e}")

    def _on_suggestion_selected(self, product_data: Dict):
        """Callback cuando se selecciona una sugerencia del autocomplete"""
        try:
            self._agregar_producto_desde_datos(product_data)
            self._actualizar_status(f"Producto agregado: {product_data['nombre']}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo agregar el producto: {e}")

    def _agregar_producto_desde_datos(self, product_data: Dict, cantidad: int = 1):
        """Agregar producto a la venta desde datos del producto"""
        try:
            item = VentaItem(
                producto_id=product_data['id'],
                codigo_barras=product_data.get('codigo_barras', ''),
                nombre=product_data['nombre'],
                precio=Decimal(str(product_data['precio'])),
                cantidad=cantidad,
                stock=product_data.get('stock', 0)
            )
            self._agregar_item(item)
        except Exception as e:
            logger.error(f"Error agregando producto: {e}")
            raise

    def _agregar_item(self, item: VentaItem):
        """Agregar item a la venta, actualizando cantidad si ya existe"""
        for existing_item in self.items:
            if existing_item.producto_id == item.producto_id:
                existing_item.cantidad += item.cantidad
                self._actualizar_treeview()
                self._actualizar_totales()
                self._actualizar_status(f"Cantidad actualizada: {existing_item.nombre}")
                return
                
        self.items.append(item)
        self._actualizar_treeview()
        self._actualizar_totales()
        self._actualizar_status(f"Agregado: {item.nombre}")

    def _actualizar_treeview(self):
        """Actualizar la tabla de productos en venta"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for idx, item in enumerate(self.items):
            # Usamos los tags 'even' y 'odd' que ahora heredan del tema
            tags = ['even' if idx % 2 == 0 else 'odd']
            
            if not item.tiene_stock:
                tags.append('sin_stock')
            elif item.stock < 5:  # Stock bajo
                tags.append('bajo_stock')
                
            values = (
                item.codigo_barras,
                item.nombre,
                item.cantidad,
                money(item.precio),
                money(item.subtotal),
                item.stock
            )
            self.tree.insert('', tk.END, values=values, tags=tags)

    def _actualizar_totales(self):
        """Actualizar los totales de la venta"""
        total_items = sum(item.cantidad for item in self.items)
        subtotal = sum(float(item.subtotal) for item in self.items)
        total = subtotal
        
        self.lbl_items.config(text=f"Items: {total_items}")
        self.lbl_subtotal.config(text=f"Subtotal: ${subtotal:,.2f}")
        self.lbl_total.config(text=f"TOTAL: ${total:,.2f}")

    def _actualizar_status(self, mensaje: str):
        """Actualizar la barra de estado"""
        self.status_bar.config(text=mensaje)
        self.after(3500, lambda: self.status_bar.config(
            text="Listo - Escanee productos o use F2 para búsqueda manual"
        ))

    def _add_from_entry(self):
        """Método para agregar producto desde la entrada de texto"""
        codigo = self.entry_codigo.get().strip()
        if not codigo:
            return
        self._procesar_entrada_producto(codigo)
        self.entry_codigo.delete(0, tk.END)

    def _toggle_lector(self):
        """Activar/desactivar el lector de códigos de barras"""
        self.lector_activo = not self.lector_activo
        if self.lector_activo:
            self.lector_status.config(text="✅ LECTOR ACTIVO - Escanee códigos de barras", foreground=self.COLOR_SUCCESS)
            self.entry_codigo.focus()
            self._actualizar_status("Lector activado - Listo para escanear")
        else:
            self.lector_status.config(text="⏸️ LECTOR PAUSADO - Presione para activar", foreground=self.COLOR_WARNING)
            self._actualizar_status("Lector pausado")

    def _show_busqueda_avanzada(self):
        """Mostrar diálogo de búsqueda avanzada (usa caché de app_root)"""
        dialogo = BusquedaAvanzadaDialog(self)
        self.wait_window(dialogo)
        if hasattr(dialogo, 'producto_seleccionado') and dialogo.producto_seleccionado:
            self._agregar_producto_desde_datos(dialogo.producto_seleccionado)

    def _show_lista_productos(self):
        """Mostrar diálogo de lista completa de productos (usa caché de app_root)"""
        dialogo = ListaProductosDialog(self)
        self.wait_window(dialogo)
        if hasattr(dialogo, 'producto_seleccionado') and dialogo.producto_seleccionado:
            self._agregar_producto_desde_datos(dialogo.producto_seleccionado)

    def _on_doble_clic(self, event):
        """Manejar doble clic en la tabla"""
        self._menu_editar_cantidad()

    def _on_clic_derecho(self, event):
        """Manejar clic derecho en la tabla"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.tk_popup(event.x_root, event.y_root)

    def _menu_editar_cantidad(self):
        """Editar cantidad del item seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            self._actualizar_status("Seleccione un producto para editar")
            return
            
        idx = self.tree.index(seleccion[0])
        if 0 <= idx < len(self.items):
            item = self.items[idx]
            nueva_cantidad = tk.simpledialog.askinteger(
                "Editar cantidad", 
                f"Nueva cantidad para {item.nombre}:", 
                parent=self, 
                initialvalue=item.cantidad, 
                minvalue=1
            )
            if nueva_cantidad:
                item.cantidad = nueva_cantidad
                self._actualizar_treeview()
                self._actualizar_totales()
                self._actualizar_status(f"Cantidad actualizada: {item.nombre}")

    def _menu_aumentar_1(self):
        """Aumentar cantidad en 1 del item seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            return
        idx = self.tree.index(seleccion[0])
        if 0 <= idx < len(self.items):
            self.items[idx].cantidad += 1
            self._actualizar_treeview()
            self._actualizar_totales()

    def _menu_disminuir_1(self):
        """Disminuir cantidad en 1 del item seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            return
        idx = self.tree.index(seleccion[0])
        if 0 <= idx < len(self.items):
            if self.items[idx].cantidad > 1:
                self.items[idx].cantidad -= 1
                self._actualizar_treeview()
                self._actualizar_totales()

    def _menu_eliminar_item(self):
        """Eliminar item seleccionado"""
        self._eliminar_seleccionado()

    def _menu_ver_info(self):
        """Mostrar información del producto seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            return
        idx = self.tree.index(seleccion[0])
        if 0 <= idx < len(self.items):
            item = self.items[idx]
            info = f"""
            Información del Producto:
            
            Nombre: {item.nombre}
            Código: {item.codigo_barras}
            Precio: {money(item.precio)}
            Cantidad: {item.cantidad}
            Stock disponible: {item.stock}
            Subtotal: {money(item.subtotal)}
            
            Estado: {'✅ Stock suficiente' if item.tiene_stock else '⚠️ Stock insuficiente'}
            """
            messagebox.showinfo("Información del Producto", info.strip())

    def _eliminar_seleccionado(self):
        """Eliminar el item seleccionado de la venta"""
        seleccion = self.tree.selection()
        if not seleccion:
            self._actualizar_status("Seleccione un item para eliminar")
            return
            
        idx = self.tree.index(seleccion[0])
        if 0 <= idx < len(self.items):
            item = self.items[idx]
            self.items.pop(idx)
            self._actualizar_treeview()
            self._actualizar_totales()
            self._actualizar_status(f"Eliminado: {item.nombre}")

    def _limpiar_venta(self):
        """Limpiar toda la venta"""
        if not self.items:
            return
            
        # Si hay items, preguntar
        if self.items and not messagebox.askyesno("Limpiar venta", "¿Está seguro de que desea limpiar toda la venta?"):
            return

        self.items.clear()
        self._actualizar_treeview()
        self._actualizar_totales()
        self._actualizar_status("Venta limpiada")
        self.entry_codigo.focus()

    def _finalizar_venta(self):
        """Finalizar la venta, procesar pago, y generar PDF en hilo."""
        if not self.items:
            messagebox.showwarning("Venta vacía", "No hay productos en la venta")
            return
            
        # Verificar stock
        sin_stock = []
        for item in self.items:
            if item.stock < item.cantidad:
                sin_stock.append({
                    'item': item,
                    'stock_actual': item.stock,
                    'cantidad_solicitada': item.cantidad
                })
                
        if sin_stock:
            productos_sin_stock = "\n".join([
                f"- {item['item'].nombre}: Stock {item['stock_actual']}, Solicitado {item['cantidad_solicitada']}" 
                for item in sin_stock
            ])
            if not messagebox.askyesno(
                "Stock insuficiente", 
                f"Los siguientes productos no tienen stock suficiente:\n\n{productos_sin_stock}\n\n¿Desea continuar igualmente?"
            ):
                return
                
        # Calcular total y mostrar diálogo de pago
        total = sum(float(item.subtotal) for item in self.items)
        dialogo_pago = PagoDialog(self, Decimal(total))
        self.wait_window(dialogo_pago)
        
        if not dialogo_pago.resultado:
            return
            
        try:
            # Preparar datos para la venta
            items_payload = [
                {
                    "producto_id": item.producto_id,
                    "cantidad": item.cantidad,
                    "precio": float(item.precio),
                    "nombre": item.nombre
                }
                for item in self.items
            ]
            
            # --- CREAR VENTA (Esto es bloqueante y DEBE SERLO) ---
            # Aquí se descuenta el stock de la BD
            venta_id = VentaRepo.crear_venta(
                punto_venta_id=self.punto_venta_id,
                items=items_payload,
                forma_pago=dialogo_pago.resultado["forma_pago"],
                monto_recibido=dialogo_pago.resultado["monto_recibido"],
                vuelto=dialogo_pago.resultado["vuelto"]
            )
            
            # Guardar copia para el ticket
            items_para_ticket = [
                VentaItem(**{
                    "producto_id": it["producto_id"],
                    "codigo_barras": "",
                    "nombre": it["nombre"],
                    "precio": Decimal(str(it["precio"])),
                    "cantidad": it["cantidad"],
                    "stock": 0
                }) for it in items_payload
            ]
            
            datos_pago = dialogo_pago.resultado
            
            # --- INICIO CAMBIO THREADING ---
            # 1. Mostrar feedback inmediato al usuario
            messagebox.showinfo("Venta Exitosa", 
                f"Venta #{venta_id} procesada exitosamente!\n\n"
                f"El ticket PDF se está generando en segundo plano...")

            # 2. Generar PDF en un hilo separado para no congelar la app
            try:
                pdf_args = (venta_id, items_para_ticket, datos_pago)
                pdf_thread = threading.Thread(target=self._generar_y_mostrar_pdf_en_hilo, args=pdf_args)
                pdf_thread.start()
                
            except Exception as e:
                logger.error(f"Error iniciando hilo de PDF: {e}")
                messagebox.showwarning("Aviso", 
                    f"Venta procesada pero no se pudo generar PDF automáticamente:\n{e}")
            # --- FIN CAMBIO THREADING ---
                    
            # 3. Limpiar venta (se ejecuta inmediatamente)
            self._limpiar_venta()
            
            # --- 4. ACTUALIZAR CACHÉ CENTRAL ---
            # Le decimos a la app principal que recargue todos los datos
            # porque el stock y el historial de ventas han cambiado.
            if hasattr(self.app_root, 'refresh_all_caches_and_tabs'):
                self.app_root.refresh_all_caches_and_tabs()
            
        except ValueError as e:
            logger.error(f"Error de stock en venta: {e}")
            messagebox.showerror("Error de Stock", f"No se puede procesar la venta:\n{e}")
        except Exception as e:
            logger.error(f"Error finalizando venta: {e}")
            messagebox.showerror("Error", f"No se pudo procesar la venta: {e}")

    def _generar_y_mostrar_pdf_en_hilo(self, venta_id: int, items: List[VentaItem], datos_pago: Dict):
        """
        Esta función se ejecuta en un hilo separado para no congelar la UI.
        Genera el PDF e intenta abrirlo.
        """
        try:
            pdf_path = self._exportar_pdf_a4(venta_id, items, datos_pago)
            logger.info(f"PDF generado exitosamente en {pdf_path}")
            
        except Exception as e:
            logger.error(f"Error generando PDF en el hilo: {e}")
            # Usamos self.after(0, ...) para mostrar el error de forma segura
            # desde el hilo principal de Tkinter.
            self.after(0, lambda: messagebox.showerror("Error de PDF", 
                f"La venta #{venta_id} se guardó, pero hubo un error al generar el PDF:\n{e}"))

    def _exportar_pdf_a4(self, venta_id: int, items: List[VentaItem], datos_pago: Dict) -> str:
        """
        Genera un PDF A4 profesional con los datos de la venta.
        (Sin cambios en esta función)
        """
        os.makedirs("tickets_pdf", exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tickets_pdf/venta_{venta_id}_{timestamp}.pdf"
        abs_path = os.path.abspath(filename)

        total = sum(float(it.subtotal) for it in items)
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formas_pago_display = {
            "EFECTIVO": "EFECTIVO",
            "TARJETA_DEBITO": "TARJETA DÉBITO",
            "TARJETA_CREDITO": "TARJETA CRÉDITO",
            "TRANSFERENCIA": "TRANSFERENCIA"
        }

        if PDF_ENGINE == "reportlab":
            c = rl_canvas.Canvas(abs_path, pagesize=A4)
            width, height = A4
            margin = 20 * mm
            x = margin
            y = height - margin

            c.setFont("Helvetica-Bold", 16)
            c.drawString(x, y, "KIOSKO PRO")
            c.setFont("Helvetica", 10)
            c.drawString(x, y - 18, f"Ticket: #{venta_id}")
            c.drawString(x + 300, y - 18, f"Fecha: {fecha}")
            y -= 36
            c.line(x, y, width - margin, y)
            y -= 12

            c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y, "Cant.")
            c.drawString(x + 50, y, "Producto")
            c.drawString(x + 380, y, "Precio")
            c.drawString(x + 460, y, "Subtotal")
            y -= 14
            c.setFont("Helvetica", 9)
            
            for it in items:
                if y < margin + 80:
                    c.showPage()
                    y = height - margin
                    
                c.drawString(x, y, f"{it.cantidad}")
                nombre = it.nombre if len(it.nombre) <= 40 else it.nombre[:37] + "..."
                c.drawString(x + 50, y, nombre)
                c.drawRightString(x + 450 + 10, y, money(it.precio))
                c.drawRightString(x + 530, y, money(it.subtotal))
                y -= 14

            if y < margin + 120:
                c.showPage()
                y = height - margin
                
            y -= 10
            c.line(x, y, width - margin, y)
            y -= 18
            c.setFont("Helvetica-Bold", 11)
            c.drawRightString(width - margin, y, f"TOTAL: {money(total)}")
            y -= 22
            c.setFont("Helvetica", 10)
            c.drawString(x, y, f"Forma de pago: {formas_pago_display.get(datos_pago['forma_pago'], datos_pago['forma_pago'])}")
            y -= 14
            
            if datos_pago['forma_pago'] == "EFECTIVO":
                c.drawString(x, y, f"Monto recibido: {money(datos_pago['monto_recibido'])}")
                c.drawString(x + 200, y, f"Vuelto: {money(datos_pago['vuelto'])}")
                
            y -= 28
            c.setFont("Helvetica-Oblique", 9)
            c.drawCentredString(width / 2, y, "*** GRACIAS POR SU COMPRA ***")
            c.save()

        elif PDF_ENGINE == "fpdf":
            pdf = FPDF(unit="mm", format="A4")
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 8, "KIOSKO PRO", ln=1)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"Ticket: #{venta_id}    Fecha: {fecha}", ln=1)
            pdf.ln(4)
            
            pdf.set_font("Arial", "B", 10)
            pdf.cell(20, 8, "Cant.", border=0)
            pdf.cell(110, 8, "Producto", border=0)
            pdf.cell(30, 8, "Precio", border=0, align="R")
            pdf.cell(30, 8, "Subtotal", border=0, align="R")
            pdf.ln(8)
            
            pdf.set_font("Arial", "", 10)
            for it in items:
                nombre = it.nombre if len(it.nombre) <= 50 else it.nombre[:47] + "..."
                pdf.cell(20, 7, str(it.cantidad), border=0)
                pdf.cell(110, 7, nombre, border=0)
                pdf.cell(30, 7, money(it.precio), border=0, align="R")
                pdf.cell(30, 7, money(it.subtotal), border=0, align="R")
                pdf.ln(7)
                
            pdf.ln(6)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, f"TOTAL: {money(total)}", ln=1, align="R")
            pdf.ln(4)
            pdf.set_font("Arial", "", 10)
            pdf.cell(0, 6, f"Forma de pago: {formas_pago_display.get(datos_pago['forma_pago'], datos_pago['forma_pago'])}", ln=1)
            
            if datos_pago['forma_pago'] == "EFECTIVO":
                pdf.cell(0, 6, f"Monto recibido: {money(datos_pago['monto_recibido'])}    Vuelto: {money(datos_pago['vuelto'])}", ln=1)
                
            pdf.ln(8)
            pdf.set_font("Arial", "I", 9)
            pdf.cell(0, 6, "*** GRACIAS POR SU COMPRA ***", ln=1, align="C")
            pdf.output(abs_path)

        else:
            raise RuntimeError("No se encontró motor PDF. Instale 'reportlab' o 'fpdf' (pip install reportlab OR pip install fpdf2).")

        try:
            if sys.platform.startswith("win"):
                os.startfile(abs_path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", abs_path])
            else:
                subprocess.Popen(["xdg-open", abs_path])
        except Exception:
            logger.info(f"PDF guardado en {abs_path} (no se pudo abrir automáticamente)")

        return abs_path

class BusquedaAvanzadaDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        # Referencia a la app principal para el caché
        self.app_root = self.winfo_toplevel()
        self.producto_seleccionado = None
        self.title("🔍 Búsqueda Avanzada de Productos")
        self.geometry("620x420")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()
        self._construir_ui()
        self._cargar_productos()

    def _construir_ui(self):
        search_frame = ttk.Frame(self, padding="10")
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Buscar:").pack(side="left")
        self.entry_busqueda = ttk.Entry(search_frame, width=40)
        self.entry_busqueda.pack(side="left", padx=5, fill="x", expand=True)
        self.entry_busqueda.bind("<KeyRelease>", self._filtrar_productos)
        ttk.Button(search_frame, text="Buscar", command=self._filtrar_productos).pack(side="left", padx=5)
        # El botón actualizar ahora recarga desde el caché global
        ttk.Button(search_frame, text="Actualizar", command=self._cargar_productos).pack(side="left", padx=5)
        
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("codigo", "nombre", "precio", "stock", "estado")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        for col, text, width in [
            ("codigo", "Código", 120), 
            ("nombre", "Nombre", 250), 
            ("precio", "Precio", 100), 
            ("stock", "Stock", 80),
            ("estado", "Estado", 80)
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
            
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<Double-1>", self._seleccionar_producto)
        self.tree.bind("<Return>", self._seleccionar_producto)
        
        btn_frame = ttk.Frame(self, padding="10")
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Seleccionar", command=self._seleccionar_producto).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.destroy).pack(side="right", padx=5)
        
        self.entry_busqueda.focus()

    def _cargar_productos(self):
        """Cargar productos desde el caché central"""
        try:
            if hasattr(self.app_root, 'cache_productos'):
                self.productos = self.app_root.cache_productos
            else:
                # Fallback
                self.productos = ProductoRepo.listar()
            self._mostrar_productos(self.productos)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los productos: {e}")

    def _mostrar_productos(self, productos):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for prod in productos:
            estado = "✅ Activo" if prod.get('activo', True) else "❌ Inactivo"
            self.tree.insert("", tk.END, values=(
                prod.get('codigo_barras', ''), 
                prod['nombre'], 
                f"${float(prod['precio']):.2f}", 
                prod.get('stock', 0),
                estado
            ))

    def _filtrar_productos(self, event=None):
        query = self.entry_busqueda.get().lower().strip()
        if not query:
            self._mostrar_productos(self.productos)
            return
            
        resultados = []
        for prod in self.productos:
            if (query in prod['nombre'].lower() or 
                query in prod.get('codigo_barras', '').lower()):
                resultados.append(prod)
                
        self._mostrar_productos(resultados)

    def _seleccionar_producto(self, event=None):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Seleccione un producto")
            return
            
        item = self.tree.item(seleccion[0])
        valores = item['values']
        
        nombre_producto = valores[1]
        
        for prod in self.productos:
            if prod.get('nombre') == nombre_producto: 
                if not prod.get('activo', True):
                    messagebox.showwarning("Producto Inactivo", "Este producto está inactivo")
                    return
                self.producto_seleccionado = prod
                self.destroy()
                return
                
        messagebox.showerror("Error", "No se pudo encontrar el producto seleccionado")

class ListaProductosDialog(BusquedaAvanzadaDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("📋 Lista Completa de Productos")

    def _construir_ui(self):
        info_frame = ttk.Frame(self, padding="10")
        info_frame.pack(fill="x")
        ttk.Label(info_frame, text="Lista completa de productos - Doble clic para seleccionar", 
                 font=("Segoe UI", 9)).pack()
                 
        search_frame = ttk.Frame(self, padding="10")
        search_frame.pack(fill="x")
        ttk.Label(search_frame, text="Filtrar:").pack(side="left")
        self.entry_busqueda = ttk.Entry(search_frame, width=40)
        self.entry_busqueda.pack(side="left", padx=5, fill="x", expand=True)
        self.entry_busqueda.bind("<KeyRelease>", self._filtrar_productos)
        ttk.Button(search_frame, text="Buscar", command=self._filtrar_productos).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Actualizar", command=self._cargar_productos).pack(side="left", padx=5)
        
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("codigo", "nombre", "precio", "stock", "categoria", "estado")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=18)
        
        for col, text, width in [
            ("codigo", "Código", 120), 
            ("nombre", "Nombre", 220), 
            ("precio", "Precio", 100), 
            ("stock", "Stock", 80), 
            ("categoria", "Categoría", 120),
            ("estado", "Estado", 80)
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width, anchor="center")
            
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<Double-1>", self._seleccionar_producto)
        self.tree.bind("<Return>", self._seleccionar_producto)
        
        btn_frame = ttk.Frame(self, padding="10")
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Seleccionar Producto", command=self._seleccionar_producto).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=self.destroy).pack(side="right", padx=5)
        
        self.entry_busqueda.focus()
    
    # Sobrescribimos _mostrar_productos para incluir la categoría
    def _mostrar_productos(self, productos):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for prod in productos:
            estado = "✅ Activo" if prod.get('activo', True) else "❌ Inactivo"
            self.tree.insert("", tk.END, values=(
                prod.get('codigo_barras', ''), 
                prod['nombre'], 
                f"${float(prod['precio']):.2f}", 
                prod.get('stock', 0),
                prod.get('categoria', 'Sin categoría'), # Añadido
                estado
            ))

# Ejecución de prueba
if __name__ == "__main__":
    if PDF_ENGINE is None:
        root = tk.Tk()
        root.withdraw()
        message = ("No se detectó ninguna librería para generar PDF.\n\n"
                   "Instalá una de las siguientes antes de usar el guardado automático de tickets:\n"
                   "  pip install reportlab\n  -o- \n  pip install fpdf2\n\n"
                   "El programa seguirá funcionando para agregar productos, pero al finalizar la venta\n"
                   "no se podrá generar el PDF hasta instalar alguna de las librerías anteriores.")
        if messagebox.askyesno("Librería PDF no encontrada", message + "\n\n¿Desea continuar de todos modos?"):
            root.destroy()
        else:
            root.destroy()
            sys.exit(0)

    # --- SIMULACIÓN DE LA APP PRINCIPAL (VentasApp) ---
    # Para que el caché funcione en modo prueba, simulamos la app principal
    class MockApp(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Sistema de Ventas PRO - Modo Prueba")
            self.geometry("1200x800")
            
            # Crear el caché
            self.cache_productos = []
            self.cache_categorias = []
            self.cache_ventas = []
            self.cache_puntos_venta = []
            
            # Cargar el caché
            self.refresh_all_caches_and_tabs()
            
            # Crear el frame de NuevaVenta
            frame = NuevaVentaFrame(self)
            frame.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh_all_caches_and_tabs(self):
            print("Refrescando caché simulado...")
            try:
                self.cache_productos = ProductoRepo.listar()
                self.cache_categorias = CategoriaRepo.listar()
                self.cache_ventas = VentaRepo.listar(limit=100)
                self.cache_puntos_venta = PuntoVentaRepo.listar()
                print("Caché simulado cargado.")
            except Exception as e:
                messagebox.showerror("Error de BD en Prueba", f"No se pudo conectar a la BD para el modo prueba: {e}")
                self.destroy()

    root = MockApp()
    root.mainloop()