import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from nueva_venta import NuevaVentaFrame
from repos import ProductoRepo, VentaRepo, CategoriaRepo, PuntoVentaRepo
import datetime
from simulacion_ventas import SimulacionVentasFrame
import pandas as pd
import os
import traceback # Importar para depuración de gráficos

# --- INICIO: AGREGADO DE IMPORTS ---
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- CAMBIO IMPORTANTE: Importamos desde el nuevo archivo theme.py ---
try:
    from theme import THEMES
except ImportError:
    print("Error: No se encontró el archivo 'theme.py'.")
    # Definimos un tema por defecto en caso de que este archivo se ejecute solo
    THEMES = {
        "dark": {
            "bg": "#2c3e50", "fg": "#ecf0f1", "card": "#34495e", "accent": "#45FF6C",
            "border": "#7f8c8d", "text": "#ecf0f1"
        },
        "light": {
            "bg": "#ecf0f1", "fg": "#2c3e50", "card": "#ffffff", "accent": "#1abc9c",
            "border": "#bdc3c7", "text": "#2c3e50"
        }
    }
# --- FIN DEL CAMBIO ---


LOGO_PATH = "logo_pos_kiosko.png"

class ReportesManager:
    """Gestor profesional de reportes del sistema"""
    
    @staticmethod
    def generar_reporte_ventas_completo(parent_frame):
        """Generar reporte completo de ventas en Excel"""
        try:
            # Los reportes SIEMPRE deben consultar datos frescos de la BD
            ventas = VentaRepo.listar_completo()
            if not ventas:
                messagebox.showwarning("Sin datos", "No hay ventas registradas para generar reporte.")
                return

            # Crear DataFrames organizados
            df_ventas = ReportesManager._crear_dataframe_ventas(ventas)
            df_productos_vendidos = ReportesManager._crear_dataframe_productos_vendidos(ventas)
            df_resumen = ReportesManager._crear_dataframe_resumen(ventas)

            # Seleccionar ubicación para guardar
            fecha_actual = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[
                    ("Excel Workbook", "*.xlsx"),
                    ("Excel 97-2003", "*.xls"),
                    ("PDF", "*.pdf"),
                    ("Todos los archivos", "*.*")
                ],
                title="Guardar reporte de ventas como...",
                initialfile=f"Reporte_Ventas_Completo_{fecha_actual}"
            )

            if not ruta:
                return

            # Guardar en Excel con formato profesional
            with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
                # Hoja de resumen ejecutivo
                df_resumen.to_excel(writer, sheet_name="📊 Resumen Ejecutivo", index=False)
                
                # Hoja de ventas detalladas
                df_ventas.to_excel(writer, sheet_name="🧾 Ventas Detalladas", index=False)
                
                # Hoja de productos más vendidos
                df_productos_vendidos.to_excel(writer, sheet_name="📦 Productos Vendidos", index=False)
                
                # Aplicar formatos profesionales
                ReportesManager._aplicar_formato_excel(writer, ruta)

            messagebox.showinfo(
                "✅ Reporte Generado", 
                f"Reporte creado exitosamente:\n\n"
                f"📊 {len(ventas)} ventas procesadas\n"
                f"📦 {len(df_productos_vendidos)} productos analizados\n"
                f"📁 Ubicación: {os.path.basename(ruta)}"
            )

        except Exception as e:
            messagebox.showerror(
                "❌ Error", 
                f"No se pudo generar el reporte:\n\n{str(e)}\n\n"
                f"Verifique que:\n"
                f"• Tenga instalado Microsoft Excel o openpyxl\n"
                f"• Los datos estén correctos en la base de datos"
            )

    @staticmethod
    def _crear_dataframe_ventas(ventas):
        """Crear DataFrame detallado de ventas"""
        datos_ventas = []
        
        for venta in ventas:
            # Información básica de la venta
            datos_ventas.append({
                "ID Venta": venta["id"],
                "Fecha": venta["fecha"].strftime("%d/%m/%Y"),
                "Hora": venta["fecha"].strftime("%H:%M:%S"),
                "Total ($)": float(venta["total"]),
                "Forma de Pago": venta["forma_pago"],
                "Cantidad de Productos": sum(item["cantidad"] for item in venta.get("items", [])),
                "Productos": ", ".join([f"{item['producto']} (x{item['cantidad']})" 
                                      for item in venta.get("items", [])])
            })
        
        return pd.DataFrame(datos_ventas)

    @staticmethod
    def _crear_dataframe_productos_vendidos(ventas):
        """Crear DataFrame de productos más vendidos"""
        productos_vendidos = {}
        
        for venta in ventas:
            for item in venta.get("items", []):
                nombre_producto = item["producto"]
                cantidad = item["cantidad"]
                precio_unitario = item["precio_unitario"]
                total_producto = cantidad * precio_unitario
                
                if nombre_producto in productos_vendidos:
                    productos_vendidos[nombre_producto]["cantidad_total"] += cantidad
                    productos_vendidos[nombre_producto]["ingresos_totales"] += total_producto
                else:
                    productos_vendidos[nombre_producto] = {
                        "cantidad_total": cantidad,
                        "ingresos_totales": total_producto,
                        "precio_promedio": precio_unitario
                    }
        
        # Convertir a DataFrame y ordenar
        df = pd.DataFrame([
            {
                "Producto": producto,
                "Cantidad Total Vendida": datos["cantidad_total"],
                "Ingresos Generados ($)": round(datos["ingresos_totales"], 2),
                "Precio Promedio ($)": round(datos["precio_promedio"], 2)
            }
            for producto, datos in productos_vendidos.items()
        ])
        
        return df.sort_values("Ingresos Generados ($)", ascending=False)

    @staticmethod
    def _crear_dataframe_resumen(ventas):
        """Crear DataFrame de resumen ejecutivo"""
        if not ventas:
            return pd.DataFrame({"Métrica": ["No hay datos"], "Valor": [""]})
        
        # Cálculos de resumen
        total_ventas = len(ventas)
        ingresos_totales = sum(venta["total"] for venta in ventas)
        venta_promedio = ingresos_totales / total_ventas if total_ventas > 0 else 0
        
        # Productos vendidos
        total_productos = sum(
            sum(item["cantidad"] for item in venta.get("items", [])) 
            for venta in ventas
        )
        
        # Formas de pago
        formas_pago = {}
        for venta in ventas:
            fp = venta["forma_pago"]
            formas_pago[fp] = formas_pago.get(fp, 0) + 1
        
        # Crear resumen
        resumen = {
            "Período del Reporte": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
            "Total de Ventas": total_ventas,
            "Ingresos Totales ($)": round(ingresos_totales, 2),
            "Venta Promedio ($)": round(venta_promedio, 2),
            "Total de Productos Vendidos": total_productos,
            "Forma de Pago Más Usada": max(formas_pago.items(), key=lambda x: x[1])[0] if formas_pago else "N/A"
        }
        
        return pd.DataFrame(list(resumen.items()), columns=["Métrica", "Valor"])

    @staticmethod
    def _aplicar_formato_excel(writer, ruta):
        """Aplicar formato profesional al archivo Excel"""
        try:
            workbook = writer.book
            
            # Aplicar formatos a cada hoja
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                
                # Ajustar ancho de columnas automáticamente
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
                
        except Exception as e:
            print(f"⚠️ No se pudieron aplicar formatos Excel: {e}")

    @staticmethod
    def generar_reporte_stock():
        """Generar reporte de inventario y stock"""
        try:
            # Los reportes SIEMPRE deben consultar datos frescos de la BD
            try:
                productos = ProductoRepo.listar_para_reporte()
            except AttributeError:
                # Fallback si 'listar_para_reporte' no existe
                print("Usando fallback para reporte de stock. Optimizar 'ProductoRepo.listar' es recomendado.")
                productos = ProductoRepo.listar()
            
            if not productos:
                messagebox.showwarning("Sin datos", "No hay productos registrados para generar reporte.")
                return

            # Crear DataFrame de stock
            datos_stock = []
            
            for producto in productos:
                
                if 'estado_stock' not in producto:
                    if producto['stock'] == 0:
                        estado_stock = "❌ Agotado"
                    elif producto['stock'] < 5:
                        estado_stock = "⚠️ Bajo"
                    elif producto['stock'] > 100:
                        estado_stock = "📦 Excesivo"
                    else:
                        estado_stock = "✅ Óptimo"
                else:
                    estado_stock = producto['estado_stock'] # Usamos el de la BD
                
                datos_stock.append({
                    "ID": producto["id"],
                    "Código Barras": producto.get("codigo_barras", "N/A"),
                    "Producto": producto["nombre"],
                    "Precio ($)": float(producto["precio"]),
                    "Stock Actual": producto["stock"],
                    "Estado Stock": estado_stock,
                    "Categoría": producto.get("categoria", "Sin categoría"),
                    "Activo": "✅ Sí" if producto.get('activo', True) else "❌ No"
                })

            df_stock = pd.DataFrame(datos_stock)
            
            # Resumen de stock
            stock_agotado = sum(1 for p in productos if p['stock'] == 0)
            stock_bajo = sum(1 for p in productos if 0 < p['stock'] < 5)
            stock_optimo = sum(1 for p in productos if 5 <= p['stock'] <= 100)
            stock_excesivo = sum(1 for p in productos if p['stock'] > 100)
            
            resumen_stock = {
                "Fecha Generación": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Total Productos": len(productos),
                "Stock Agotado": stock_agotado,
                "Stock Bajo": stock_bajo,
                "Stock Óptimo": stock_optimo,
                "Stock Excesivo": stock_excesivo,
                "Valor Total Inventario ($)": round(sum(p['precio'] * p['stock'] for p in productos), 2)
            }
            
            df_resumen_stock = pd.DataFrame(list(resumen_stock.items()), 
                                          columns=["Métrica", "Valor"])

            # Guardar reporte
            fecha_actual = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            ruta = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                title="Guardar reporte de stock como...",
                initialfile=f"Reporte_Stock_{fecha_actual}"
            )

            if not ruta:
                return

            with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
                df_resumen_stock.to_excel(writer, sheet_name="📊 Resumen Stock", index=False)
                df_stock.to_excel(writer, sheet_name="📦 Inventario Detallado", index=False)

            messagebox.showinfo(
                "✅ Reporte de Stock Generado", 
                f"Reporte de inventario creado exitosamente:\n\n"
                f"📦 {len(productos)} productos analizados\n"
                f"⚠️ {stock_bajo} productos con stock bajo\n"
                f"❌ {stock_agotado} productos agotados\n"
                f"📁 Ubicación: {os.path.basename(ruta)}"
            )

        except Exception as e:
            messagebox.showerror("❌ Error", f"No se pudo generar el reporte de stock:\n{str(e)}")


class VentasApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Kiosko - Sistema de Venta")
        self.geometry("1300x800")
        self.configure(bg="#f8f9fa")
        
        try:
            self.iconbitmap("kiosko.ico")  
        except:
            pass

        # --- INICIO CACHÉ CENTRAL ---
        self.cache_productos = []
        self.cache_categorias = []
        self.cache_ventas = []
        self.cache_puntos_venta = []
        # --- FIN CACHÉ CENTRAL ---

        self._setup_modern_styles()
        
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill="both", expand=True)
        
        self._create_header()
        
        self.nb = ttk.Notebook(self.main_frame)
        self.nb.pack(fill="both", expand=True, padx=15, pady=(5, 0))
        
        self._create_status_bar()
        
        # F5 ahora llama a la función de recarga total
        self.bind("<F5>", lambda e: self.refresh_all_caches_and_tabs())
        
        # --- CORRECCIÓN: ORDEN DE INICIO ---
        # 1. Cargar el caché primero
        self.refresh_all_caches_and_tabs(silencioso=True)
        # 2. Crear las pestañas DESPUÉS de que el caché tenga datos
        self._create_tabs()
        # --- FIN CORRECCIÓN ---
        
    def _setup_modern_styles(self):
        """Configurar estilos modernos con colores explícitos"""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        
        # Configurar colores base
        style.configure(".", background="#f8f9fa", foreground="#2c3e50")
        
        # Notebook
        style.configure("TNotebook", background="#f8f9fa", borderwidth=0)
        style.configure("TNotebook.Tab", 
                    padding=(20, 8), 
                    font=("Segoe UI", 10, "bold"),
                    background="#e9ecef",
                    foreground="#495057")
        style.map("TNotebook.Tab", 
                background=[("selected", "#007bff")],
                foreground=[("selected", "white")])
        
        # Treeview
        style.configure("Treeview", 
                    font=("Segoe UI", 10),
                    rowheight=32,
                    borderwidth=0,
                    background="white",
                    fieldbackground="white",
                    foreground="#2c3e50")
        style.configure("Treeview.Heading", 
                    font=("Segoe UI", 10, "bold"),
                    relief="flat",
                    background="#343a40",
                    foreground="white")
        
        # Botones con colores específicos
        style.configure("Accent.TButton",
                    font=("Segoe UI", 10, "bold"),
                    padding=(15, 8),
                    background="#007bff",
                    foreground="white")
        style.configure("Success.TButton",
                    font=("Segoe UI", 10, "bold"), 
                    padding=(15, 8),
                    background="#28a745",
                    foreground="white")
        style.configure("Warning.TButton",
                    font=("Segoe UI", 10, "bold"),
                    padding=(15, 8),
                    background="#ffc107",
                    foreground="#212529")
        style.configure("Danger.TButton", # Añadido para 'toggle_estado'
                    font=("Segoe UI", 10, "bold"),
                    padding=(15, 8),
                    background="#dc3545",
                    foreground="white")
        
        # Frames
        style.configure("Header.TFrame", background="#2c3e50")
        style.configure("Card.TFrame", background="white", relief="raised", borderwidth=1)
        
    def _create_header(self):
        """Crear header moderno con información del sistema"""
        header = ttk.Frame(self.main_frame, style="Header.TFrame", height=80)
        header.pack(fill="x", padx=15, pady=(15, 10))
        header.pack_propagate(False)
        
        title_frame = ttk.Frame(header, style="Header.TFrame")
        title_frame.pack(side="left", padx=20)
        
        # Logo o título alternativo
        try:
            logo_path = "logo_pos_kiosko.png"
            self.logo_image = tk.PhotoImage(file=logo_path)
            
            logo_label = tk.Label(title_frame, 
                                image=self.logo_image,
                                background="#2c3e50")
            logo_label.pack(side="left")
            
        except Exception as e:
            print(f"Error cargando logo: {e}")
            # Título alternativo si el logo falla
            title_label = tk.Label(title_frame, 
                                text="🚀 KIOSKO PRO", 
                                font=("Segoe UI", 20, "bold"),
                                background="#2c3e50",
                                foreground="white")
            title_label.pack(side="left")
            
            subtitle_label = tk.Label(title_frame,
                                    text="Sistema de Ventas Avanzado",
                                    font=("Segoe UI", 11),
                                    background="#2c3e50", 
                                    foreground="#bdc3c7")
            subtitle_label.pack(side="left", padx=(15, 0))
        
        # Stats frame (Placeholder)
        stats_frame = ttk.Frame(header, style="Header.TFrame")
        stats_frame.pack(side="right", padx=20)
        
        self.stats_label = tk.Label(stats_frame,
                            text="Cargando...", # Se llenará después
                            font=("Segoe UI", 10, "bold"),
                            background="#2c3e50",
                            foreground="#ecf0f1")
        self.stats_label.pack(side="right")
        
    def _update_header_stats(self):
        """Actualiza las estadísticas del header usando el caché."""
        try:
            # Lee del caché, no de la BD
            productos_count = len(self.cache_productos) 
            ventas_hoy_count = self._get_ventas_hoy_from_cache() 
            
            stats_text = f"📦 {productos_count} Productos | 🧾 {ventas_hoy_count} Ventas hoy"
            self.stats_label.config(text=stats_text)
        except Exception as e:
            print(f"Error actualizando stats (cache): {e}")
            self.stats_label.config(text="Error cargando stats")
        
    def _create_tabs(self):
        """Crear las pestañas del sistema"""
        self.tab_dashboard = DashboardFrame(self.nb)
        self.tab_nueva_venta = NuevaVentaFrame(self.nb)
        self.tab_productos = ProductosFrame(self.nb)
        self.tab_categorias = CategoriasFrame(self.nb) 
        self.tab_historial = HistorialVentasFrame(self.nb)
        self.tab_puntos = PuntosVentaFrame(self.nb)
        self.tab_simulacion = SimulacionVentasFrame(self.nb)
        
        self.nb.add(self.tab_dashboard, text="📊 Dashboard")
        self.nb.add(self.tab_nueva_venta, text="💰 Nueva Venta")
        self.nb.add(self.tab_productos, text="📦 Productos")
        self.nb.add(self.tab_categorias, text="📂 Categorías")
        self.nb.add(self.tab_historial, text="🧾 Historial Ventas")
        self.nb.add(self.tab_puntos, text="🏪 Puntos de Venta")
        self.nb.add(self.tab_simulacion, text="🎮 Simular Ventas")
        
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)
    
    def _create_status_bar(self):
        """Crear barra de estado moderna"""
        status_frame = ttk.Frame(self.main_frame, relief="sunken")
        status_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        self.status_text = tk.StringVar()
        self.status_text.set("Sistema listo - F5 para actualizar toda la información")
        
        status_label = ttk.Label(status_frame, 
                               textvariable=self.status_text,
                               font=("Segoe UI", 9),
                               foreground="#7f8c8d")
        status_label.pack(side="left", padx=10, pady=5)
        
        self.time_label = ttk.Label(status_frame,
                                  font=("Segoe UI", 9),
                                  foreground="#7f8c8d")
        self.time_label.pack(side="right", padx=10, pady=5)
        self._update_time()
    
    def _update_time(self):
        """Actualizar hora en la barra de estado"""
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.time_label.config(text=f"🕒 {now}")
        self.after(1000, self._update_time)
    
    def _get_ventas_hoy_from_cache(self):
        """Obtener número de ventas de hoy (desde el caché)"""
        try:
            ventas = self.cache_ventas
            hoy = datetime.datetime.now().date()
            ventas_hoy = sum(1 for v in ventas if v['fecha'].date() == hoy)
            return ventas_hoy
        except:
            return 0
    
    def _on_tab_change(self, event):
        """Cuando se cambia de pestaña. Ahora es instantáneo."""
        try:
            tab_name = self.nb.tab(self.nb.select(), "text")
        except tk.TclError:
            tab_name = "N/A" # Ocurre si la app se está cerrando
            
        self.status_text.set(f"Vista activa: {tab_name}")
        
        # Llamar a .load() de la pestaña (ahora usa caché y es rápido)
        selected_tab_widget = self.nametowidget(self.nb.select())
        if hasattr(selected_tab_widget, 'load'):
            try:
                selected_tab_widget.load()
            except Exception as e:
                print(f"Error cargando la pestaña {tab_name}: {e}")
    
    def refresh_all_caches_and_tabs(self, silencioso=False):
        """
        FUNCIÓN CLAVE (F5): 
        1. Llama a la BD para recargar todos los cachés.
        2. Llama a refresh_all_tabs_from_cache() para actualizar las vistas.
        """
        self.status_text.set("Actualizando cachés de la base de datos...")
        try:
            self.cache_productos = ProductoRepo.listar()
            self.cache_categorias = CategoriaRepo.listar()
            self.cache_ventas = VentaRepo.listar(limit=1000) 
            self.cache_puntos_venta = PuntoVentaRepo.listar()
            
            self.status_text.set("Cachés actualizados. Refrescando vistas...")
            
            # Actualizar stats del header con los nuevos datos
            self._update_header_stats()
            
            # Ahora, refrescar todas las vistas (leyendo del caché)
            self.refresh_all_tabs_from_cache()
            
            self.status_text.set("Sistema actualizado.")
            if not silencioso:
                messagebox.showinfo("Actualizado", "Toda la información ha sido actualizada desde la base de datos.")

        except Exception as e:
            self.status_text.set("Error al recargar la información.")
            messagebox.showerror("Error de Carga", f"No se pudo recargar la información: {e}")

    def refresh_all_tabs_from_cache(self):
        """Actualiza todas las pestañas leyendo del caché (NO llama a la BD)."""
        self.status_text.set("Actualizando vistas...")
        
        try:
            for tab_widget in self.nb.tabs():
                widget = self.nametowidget(tab_widget)
                if hasattr(widget, 'load'):
                    try:
                        widget.load() # El 'load' de la pestaña usará el caché
                    except Exception as e:
                        print(f"Error actualizando pestaña desde caché: {e}")
        except tk.TclError:
            pass # Ocurre si las pestañas aún no están listas
        
        self.status_text.set("Vistas actualizadas.")

class ModernBaseFrame(ttk.Frame):
    """Frame base modernizado con herramientas avanzadas"""
    
    def __init__(self, parent):
        super().__init__(parent)
        # Referencia a la ventana principal para acceder al caché
        self.app_root = self.winfo_toplevel()
        self.pack(fill="both", expand=True, padx=10, pady=10)
        
    def make_modern_toolbar(self, buttons, title=None):
        """Crear toolbar moderno con título"""
        toolbar_container = ttk.Frame(self, style="Card.TFrame")
        toolbar_container.pack(fill="x", pady=(0, 10))
        
        if title:
            title_frame = ttk.Frame(toolbar_container, style="Card.TFrame")
            title_frame.pack(fill="x", padx=15, pady=(10, 5))
            
            title_label = ttk.Label(title_frame, 
                                 text=title,
                                 font=("Segoe UI", 14, "bold"))
            title_label.pack(side="left")
        
        toolbar = ttk.Frame(toolbar_container, style="Card.TFrame")
        toolbar.pack(fill="x", padx=15, pady=(5, 15))
        
        for text, cmd, style in buttons:
            if style == "accent":
                btn = ttk.Button(toolbar, text=text, command=cmd, style="Accent.TButton")
            elif style == "success":
                btn = ttk.Button(toolbar, text=text, command=cmd, style="Success.TButton")
            elif style == "warning":
                btn = ttk.Button(toolbar, text=text, command=cmd, style="Warning.TButton")
            elif style == "danger": # Añadido
                btn = ttk.Button(toolbar, text=text, command=cmd, style="Danger.TButton")
            else:
                btn = ttk.Button(toolbar, text=text, command=cmd)
            
            btn.pack(side="left", padx=3)
        
        if hasattr(self, 'app_root') and hasattr(self.app_root, 'refresh_all_caches_and_tabs'):
            ttk.Button(toolbar, text="🔄 Actualizar (F5)", 
                    command=self.app_root.refresh_all_caches_and_tabs).pack(side="right", padx=3)
    
    def create_search_bar(self, placeholder="Buscar...", on_search=None):
        """Crear barra de búsqueda moderna"""
        search_frame = ttk.Frame(self)
        search_frame.pack(fill="x", pady=(0, 10))
        
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, font=("Segoe UI", 10))
        search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        search_entry.insert(0, placeholder)
        
        # --- Placeholder Logic ---
        def on_focus_in(event):
            if search_entry.get() == placeholder:
                search_entry.delete(0, tk.END)
                search_entry.config(foreground="black") 
        
        def on_focus_out(event):
            if not search_entry.get():
                search_entry.insert(0, placeholder)
                search_entry.config(foreground="gray")
        
        search_entry.bind("<FocusIn>", on_focus_in)
        search_entry.bind("<FocusOut>", on_focus_out)
        search_entry.config(foreground="gray")
        # --- Fin Placeholder Logic ---
        
        search_cmd = (lambda: on_search(search_var.get())) if callable(on_search) else None
        
        def clear_and_search():
            search_var.set("")
            on_focus_out(None) 
            if callable(on_search):
                on_search("")
        
        ttk.Button(search_frame, text="🔍 Buscar", 
                  command=search_cmd).pack(side="left", padx=(0, 5))
        
        ttk.Button(search_frame, text="🗑️ Limpiar", 
                  command=clear_and_search).pack(side="left")
        
        search_entry.bind("<Return>", lambda e: search_cmd())
        
        return search_var
    
    def create_modern_treeview(self, columns_config, height=15):
        """Crear treeview moderno con scrollbars"""
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        
        columns = [col[0] for col in columns_config]
        tree = ttk.Treeview(container, columns=columns, show="headings", height=height)
        
        for col_id, heading, width, anchor in columns_config:
            tree.heading(col_id, text=heading)
            tree.column(col_id, width=width, anchor=anchor)
        
        v_scroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        h_scroll = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # --- CORRECCIÓN ERROR 3 (Colores) ---
        # Quitamos los 'background' fijos para que hereden del tema
        tree.tag_configure("even") 
        tree.tag_configure("odd")
        # --- FIN CORRECCIÓN ---
        
        tree.tag_configure("warning", background="#fff3cd", foreground="#856404")
        tree.tag_configure("danger", background="#f8d7da", foreground="#721c24")
        tree.tag_configure("inactive", background="#e9ecef", foreground="#6c757d")
        
        return tree

# ---------------------------------------------------------------------
# --- DASHBOARD FRAME (Modificado para usar Caché) ---
# ---------------------------------------------------------------------
class DashboardFrame(ModernBaseFrame):
    """Dashboard moderno con métricas y gráficos (lee de caché)"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas_grafico = None 
    
    def load(self):
        """Cargar datos del dashboard (métricas Y gráfico) desde el caché"""
        
        for widget in self.winfo_children():
            widget.destroy()
        
        self.make_modern_toolbar([
            ("📈 Reporte Completo", self.generar_reporte, "success")
        ], "📊 Dashboard de Ventas")
        
        content_frame = ttk.Frame(self)
        content_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self._create_metrics_cards(content_frame) 
        
        self._crear_grafico_ventas(content_frame) 
    
    def _create_metrics_cards(self, parent_frame):
        """Crear tarjetas de métricas (leyendo de caché)"""
        metrics_frame = ttk.Frame(parent_frame)
        metrics_frame.pack(fill="x", pady=(0, 20))
        
        try:
            productos = self.app_root.cache_productos
            ventas = self.app_root.cache_ventas
            ventas_hoy = self.app_root._get_ventas_hoy_from_cache()
            
            total_ventas = sum(v['total'] for v in ventas)
            productos_bajo_stock = sum(1 for p in productos if p['stock'] < 10 and p.get('activo', True))
            
            metrics = [
                ("📦 Total Productos", len(productos), "#3498db", "productos"),
                ("🧾 Ventas Hoy", ventas_hoy, "#27ae60", "ventas"), 
                ("💰 Ingresos (Recientes)", f"${total_ventas:,.2f}", "#9b59b6", "ingresos"),
                ("⚠️ Stock Bajo (Activos)", productos_bajo_stock, "#e74c3c", "stock")
            ]
            
            for i, (title, value, color, key) in enumerate(metrics):
                card = self._create_metric_card(metrics_frame, title, value, color)
                card.pack(side="left", fill="x", expand=True, padx=5)
                
        except Exception as e:
            print(f"Error cargando métricas: {e}")
    
    def _create_metric_card(self, parent, title, value, color):
        """Crear tarjeta de métrica individual"""
        card = tk.Frame(parent, bg="white", relief="raised", borderwidth=1, width=200, height=100)
        
        title_label = tk.Label(card, text=title, bg="white", 
                              font=("Segoe UI", 10, "bold"),
                              foreground="#7f8c8d")
        title_label.pack(pady=(15, 5))
        
        value_label = tk.Label(card, text=value, bg="white",
                              font=("Segoe UI", 18, "bold"), 
                              foreground=color)
        value_label.pack(pady=(0, 15))
        
        color_bar = tk.Frame(card, bg=color, height=4)
        color_bar.pack(fill="x", side="bottom")
        
        return card
    
    def _crear_grafico_ventas(self, parent_frame):
        """Crea e incrusta el gráfico de ventas (leyendo de caché)"""
        
        bg_color = "#FFFFFF"
        text_color = "#000000"
        accent_color = "#45FF6C"
        grid_color = "#CCCCCC"

        try:
            if hasattr(self.app_root, '_theme_name'):
                theme_name = self.app_root._theme_name
                p = THEMES.get(theme_name, {}) 
                bg_color = p.get("card", bg_color)
                text_color = p.get("text", text_color)
                accent_color = p.get("accent", accent_color)
                grid_color = p.get("border", grid_color)
        except Exception as e:
            print(f"No se pudo aplicar el tema al gráfico: {e}") 
    
        try:
            ventas_cacheadas = self.app_root.cache_ventas
            
            datos = {}
            hoy = datetime.datetime.now().date()
            for i in range(6, -1, -1): 
                fecha = hoy - datetime.timedelta(days=i)
                datos[fecha.strftime("%Y-%m-%d")] = {"fecha": fecha.strftime("%Y-%m-%d"), "total": 0.0}
            
            for v in ventas_cacheadas:
                fecha_venta_str = v['fecha'].date().strftime("%Y-%m-%d")
                if fecha_venta_str in datos:
                    datos[fecha_venta_str]["total"] += float(v['total'])
            
            datos_lista = list(datos.values())
            
            if not datos_lista:
                ttk.Label(parent_frame, text="No hay datos de ventas para el gráfico.").pack()
                return

            df = pd.DataFrame(datos_lista)
            df['fecha_corta'] = df['fecha'].apply(lambda x: x[5:]) 

            fig = Figure(figsize=(10, 4.5), dpi=100, facecolor=bg_color)
            
            ax = fig.add_subplot(111)
            ax.set_facecolor(bg_color) 
            
            ax.bar(df['fecha_corta'], df['total'], color=accent_color)
            
            ax.set_title("Ventas de los Últimos 7 Días", color=text_color, fontsize=14, weight='bold')
            ax.set_ylabel("Total ($)", color=text_color, fontsize=10)
            ax.tick_params(axis='x', colors=text_color, rotation=15)
            ax.tick_params(axis='y', colors=text_color)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(grid_color)
            ax.spines['bottom'].set_color(grid_color)
            ax.yaxis.grid(True, color=grid_color, linestyle='--', linewidth=0.5, alpha=0.5)
            fig.tight_layout() 

            grafico_frame = ttk.LabelFrame(parent_frame, text="📈 Evolución de Ventas", padding=10)
            grafico_frame.pack(fill="both", expand=True, padx=5)

            if self.canvas_grafico:
                self.canvas_grafico.get_tk_widget().destroy()

            self.canvas_grafico = FigureCanvasTkAgg(fig, master=grafico_frame)
            self.canvas_grafico.draw()
            self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)
            
        except Exception as e:
            ttk.Label(parent_frame, text=f"Error al generar gráfico: {e}").pack()
            print(f"Error al generar gráfico: {e}")
            traceback.print_exc() 
        
    def generar_reporte(self):
        """Generar reporte completo profesional (usa datos frescos)"""
        ReportesManager.generar_reporte_ventas_completo(self)
          
class ProductosFrame(ModernBaseFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.toolbar_buttons = [
            ("➕ Agregar Producto", self.add, "success"),
            ("✏️ Editar Seleccionado", self.edit, "accent"),
            ("📊 Actualizar Precio", self.actualizar_precio, "warning"),
            ("📋 Reporte Stock", self.generar_reporte_stock, "accent"),
            ("🔄 Activar/Desactivar", self.toggle_estado, "danger")
        ]
        
        self.make_modern_toolbar(self.toolbar_buttons, "📦 Gestión de Productos")
        
        self._create_status_filter()
        
        self.search_var = self.create_search_bar("Buscar productos...", self.buscar_productos)
        
        columns = [
            ("id", "ID", 70, "center"),
            ("codigo", "Código", 130, "center"),
            ("nombre", "Nombre", 250, "w"),
            ("precio", "Precio", 100, "center"),
            ("stock", "Stock", 80, "center"),
            ("categoria", "Categoría", 120, "center"),
            ("estado", "Estado", 100, "center")
        ]
        
        self.tree = self.create_modern_treeview(columns)
        
        self.tree.bind("<Double-1>", lambda e: self.edit())
        self.tree.bind("<Delete>", lambda e: self.toggle_estado())
    
    def _create_status_filter(self):
        """Crear filtro por estado"""
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(filter_frame, text="Filtrar por estado:", font=("Segoe UI", 9)).pack(side="left", padx=(0, 10))
        
        self.filter_var = tk.StringVar(value="TODOS")
        
        ttk.Radiobutton(filter_frame, text="Todos", variable=self.filter_var, 
                       value="TODOS", command=self.load).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(filter_frame, text="Activos", variable=self.filter_var, 
                       value="ACTIVOS", command=self.load).pack(side="left", padx=(0, 10))
        ttk.Radiobutton(filter_frame, text="Inactivos", variable=self.filter_var, 
                       value="INACTIVOS", command=self.load).pack(side="left")

    def load(self):
        """Cargar productos desde el CACHÉ"""
        self.buscar_productos(self.search_var.get())

    def buscar_productos(self, query):
        """Buscar productos desde el CACHÉ con filtro de estado"""
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            productos = self.app_root.cache_productos
            filtro = self.filter_var.get()
            
            if not query or query == "Buscar productos...":
                query = "" 
            
            query = query.lower()
            
            for idx, p in enumerate(productos):
                if query:
                    if not (query in p['nombre'].lower() or 
                           query in p.get('codigo_barras', '').lower() or
                           query in p.get('categoria', '').lower()):
                        continue
                
                estado = "ACTIVO" if p.get('activo', True) else "INACTIVO"
                if filtro == "ACTIVOS" and estado != "ACTIVO":
                    continue
                if filtro == "INACTIVOS" and estado != "INACTIVO":
                    continue
                
                tags = ['even' if idx % 2 == 0 else 'odd']
                if p['stock'] < 5:
                    tags.append("warning")
                if p['stock'] == 0:
                    tags.append("danger")
                if estado == "INACTIVO":
                    tags.append("inactive")
                
                self.tree.insert("", tk.END, values=(
                    p["id"],
                    p["codigo_barras"],
                    p["nombre"],
                    f"${p['precio']:.2f}",
                    p["stock"],
                    p["categoria"],
                    estado
                ), tags=tuple(tags))
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los productos desde el caché:\n{str(e)}")

    def toggle_estado(self):
        """Activar/Desactivar producto seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Seleccione un producto para cambiar su estado")
            return
            
        try:
            producto_id = self.tree.item(seleccion[0])["values"][0]
            producto_nombre = self.tree.item(seleccion[0])["values"][2]
            estado_actual = self.tree.item(seleccion[0])["values"][6]
            
            nuevo_estado = not (estado_actual == "ACTIVO")
            accion = "activar" if nuevo_estado else "desactivar"
            
            if messagebox.askyesno("Confirmar", 
                                 f"¿Está seguro de {accion} el producto '{producto_nombre}'?"):
                
                producto = next((p for p in self.app_root.cache_productos if p['id'] == producto_id), None)
                
                if producto:
                    ProductoRepo.actualizar_completo(
                        producto_id=producto_id,
                        nombre=producto['nombre'],
                        precio=producto['precio'],
                        codigo_barras=producto.get('codigo_barras'),
                        categoria_id=producto.get('categoria_id'),
                        stock=producto.get('stock'),
                        activo=nuevo_estado 
                    )
                    self.app_root.refresh_all_caches_and_tabs()
                    
                    estado_text = "activado" if nuevo_estado else "desactivado"
                    messagebox.showinfo("Éxito", f"Producto {estado_text} correctamente")
                else:
                    messagebox.showerror("Error", "No se pudo encontrar el producto en el caché")
                        
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cambiar el estado del producto:\n{str(e)}")

    def add(self):
        """Agregar nuevo producto"""
        # --- CORRECCIÓN ERROR 4/5 ---
        dialog = ProductoDialog(self, "Nuevo Producto", 
                                cache_productos=self.app_root.cache_productos,
                                cache_categorias=self.app_root.cache_categorias)
        # --- FIN CORRECCIÓN ---
        self.wait_window(dialog)
        if dialog.resultado:
            self.app_root.refresh_all_caches_and_tabs()

    def edit(self):
        """Editar producto seleccionado"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Seleccione un producto para editar")
            return
            
        try:
            producto_id = self.tree.item(seleccion[0])["values"][0]
            # --- CORRECCIÓN ERROR 4/5 ---
            dialog = ProductoDialog(self, "Editar Producto", producto_id,
                                    cache_productos=self.app_root.cache_productos,
                                    cache_categorias=self.app_root.cache_categorias)
            # --- FIN CORRECCIÓN ---
            self.wait_window(dialog)
            if dialog.resultado:
                self.app_root.refresh_all_caches_and_tabs()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el editor:\n{e}")

    def actualizar_precio(self):
        """Actualizar precio rápido"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Seleccione un producto")
            return
            
        try:
            producto_id = self.tree.item(seleccion[0])["values"][0]
            producto_nombre = self.tree.item(seleccion[0])["values"][2]
            estado_actual = self.tree.item(seleccion[0])["values"][6]
            
            if estado_actual == "INACTIVO":
                messagebox.showwarning("Producto Inactivo", "No se puede actualizar el precio de un producto inactivo")
                return
            
            nuevo_precio = simpledialog.askfloat(
                "Actualizar Precio",
                f"Nuevo precio para {producto_nombre}:",
                initialvalue=float(self.tree.item(seleccion[0])["values"][3].replace('$', '')),
                minvalue=0.0
            )
            
            if nuevo_precio is not None: 
                ProductoRepo.actualizar_precio(producto_id, nuevo_precio)
                self.app_root.refresh_all_caches_and_tabs()
                messagebox.showinfo("Éxito", "Precio actualizado correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo actualizar el precio:\n{str(e)}")
            
    def generar_reporte_stock(self):
        """Generar reporte profesional de stock (usa datos frescos)"""
        ReportesManager.generar_reporte_stock()      
              
class ProductoDialog(tk.Toplevel):
    """Diálogo moderno para agregar/editar productos - CORREGIDO"""
    
    # --- CORRECCIÓN ERROR 4/5 ---
    def __init__(self, parent, titulo, producto_id=None, cache_productos=None, cache_categorias=None):
        super().__init__(parent)
        self.parent = parent
        self.producto_id = producto_id
        self.resultado = False
        
        # Guardamos los cachés pasados como argumentos
        self.cache_productos = cache_productos if cache_productos is not None else []
        self.cache_categorias = cache_categorias if cache_categorias is not None else []
        # --- FIN CORRECCIÓN ---
        
        self.title(titulo)
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._construir_ui()
        self._cargar_datos()
        
    def _construir_ui(self):
        """Construir interfaz del diálogo"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text=self.title(), 
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill="x", pady=10)
        
        ttk.Label(form_frame, text="Nombre del Producto:*").grid(row=0, column=0, sticky="w", pady=8)
        self.nombre_var = tk.StringVar()
        self.nombre_entry = ttk.Entry(form_frame, textvariable=self.nombre_var, width=40, font=("Segoe UI", 10))
        self.nombre_entry.grid(row=0, column=1, sticky="ew", pady=8, padx=(10, 0))
        
        ttk.Label(form_frame, text="Código de Barras:").grid(row=1, column=0, sticky="w", pady=8)
        self.codigo_var = tk.StringVar()
        self.codigo_entry = ttk.Entry(form_frame, textvariable=self.codigo_var, width=40, font=("Segoe UI", 10))
        self.codigo_entry.grid(row=1, column=1, sticky="ew", pady=8, padx=(10, 0))
        
        ttk.Label(form_frame, text="Precio:*").grid(row=2, column=0, sticky="w", pady=8)
        self.precio_var = tk.StringVar()
        self.precio_entry = ttk.Entry(form_frame, textvariable=self.precio_var, width=20, font=("Segoe UI", 10))
        self.precio_entry.grid(row=2, column=1, sticky="w", pady=8, padx=(10, 0))
        
        ttk.Label(form_frame, text="Stock:*").grid(row=3, column=0, sticky="w", pady=8)
        self.stock_var = tk.StringVar()
        self.stock_entry = ttk.Entry(form_frame, textvariable=self.stock_var, width=20, font=("Segoe UI", 10))
        self.stock_entry.grid(row=3, column=1, sticky="w", pady=8, padx=(10, 0))
        
        ttk.Label(form_frame, text="Categoría:").grid(row=4, column=0, sticky="w", pady=8)
        
        cat_frame = ttk.Frame(form_frame)
        cat_frame.grid(row=4, column=1, sticky="ew", pady=8, padx=(10, 0))
        
        self.categoria_id_var = tk.StringVar()
        self.categoria_combo = ttk.Combobox(cat_frame, textvariable=self.categoria_id_var, state="readonly", width=37)
        self.categoria_combo.pack(side="left", fill="x", expand=True)
        
        self._cargar_categorias()
        
        form_frame.grid_columnconfigure(1, weight=1)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(btn_frame, text="💾 Guardar", style="Success.TButton",
                  command=self._guardar).pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame, text="❌ Cancelar",
                  command=self.destroy).pack(side="left")
        
        self.nombre_entry.focus()
        
    def _cargar_categorias(self):
        """Cargar categorías en el combobox (lee del caché)"""
        try:
            # --- CORRECCIÓN ERROR 4/5 ---
            # Usamos el caché que nos pasaron, no 'winfo_toplevel'
            categorias = self.cache_categorias
            # --- FIN CORRECCIÓN ---
            
            self.categorias_map = {}
            nombres_categorias = []
            
            for cat in categorias:
                self.categorias_map[cat['nombre']] = cat['id']
                nombres_categorias.append(cat['nombre'])
            
            self.categoria_combo['values'] = nombres_categorias
            if nombres_categorias:
                self.categoria_combo.current(0)
                
        except Exception as e:
            print(f"Error cargando categorías desde caché: {e}")
            self.categoria_combo['values'] = []
    
    def _cargar_datos(self):
        """Cargar datos si es edición (lee del caché)"""
        if self.producto_id:
            try:
                # --- CORRECCIÓN ERROR 4/5 ---
                # Usamos el caché que nos pasaron
                producto = next((p for p in self.cache_productos if p['id'] == self.producto_id), None)
                # --- FIN CORRECCIÓN ---
                
                if producto:
                    self.nombre_var.set(producto['nombre'])
                    self.codigo_var.set(producto.get('codigo_barras', ''))
                    self.precio_var.set(str(producto['precio']))
                    self.stock_var.set(str(producto['stock']))
                    
                    categoria_encontrada_nombre = None
                    if producto.get('categoria_id'):
                        for nombre, cat_id in self.categorias_map.items():
                            if cat_id == producto.get('categoria_id'):
                                categoria_encontrada_nombre = nombre
                                break
                    
                    if categoria_encontrada_nombre:
                         self.categoria_id_var.set(categoria_encontrada_nombre)
                    
            except Exception as e:
                messagebox.showerror("Error", f"No se pudieron cargar los datos:\n{str(e)}")
    
    def _validar_formulario(self):
        """Validar formulario"""
        if not self.nombre_var.get().strip():
            messagebox.showwarning("Validación", "El nombre del producto es obligatorio")
            return False
        
        try:
            precio = float(self.precio_var.get())
            if precio < 0:
                messagebox.showwarning("Validación", "El precio no puede ser negativo")
                return False
        except ValueError:
            messagebox.showwarning("Validación", "El precio debe ser un número válido")
            return False
        
        try:
            stock = int(self.stock_var.get())
            if stock < 0:
                messagebox.showwarning("Validación", "El stock no puede ser negativo")
                return False
        except ValueError:
            messagebox.showwarning("Validación", "El stock debe ser un número entero válido")
            return False
        
        return True
    
    def _guardar(self):
        """Guardar producto"""
        if not self._validar_formulario():
            return
            
        try:
            nombre = self.nombre_var.get().strip()
            codigo = self.codigo_var.get().strip()
            precio = float(self.precio_var.get())
            stock = int(self.stock_var.get())
            
            categoria_id = None
            categoria_nombre = self.categoria_id_var.get()
            if categoria_nombre and hasattr(self, 'categorias_map'):
                categoria_id = self.categorias_map.get(categoria_nombre)
            
            if self.producto_id:
                ProductoRepo.actualizar_completo(
                    producto_id=self.producto_id,
                    nombre=nombre,
                    precio=precio,
                    codigo_barras=codigo if codigo else None,
                    categoria_id=categoria_id,
                    stock=stock,
                    activo=True # Asumimos que al editar se mantiene activo
                )
                messagebox.showinfo("Éxito", "✅ Producto actualizado correctamente")
            else:
                ProductoRepo.agregar(
                    nombre=nombre,
                    precio=precio,
                    stock=stock,
                    categoria_id=categoria_id,
                    codigo=codigo if codigo else None
                )
                messagebox.showinfo("Éxito", "✅ Producto agregado correctamente")
            
            self.resultado = True
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"❌ No se pudo guardar el producto:\n{str(e)}")

class CategoriaDialog(tk.Toplevel):
    """Diálogo moderno para agregar/editar categorías - CORREGIDO"""
    
    # --- CORRECCIÓN ERROR 4/5 ---
    def __init__(self, parent, titulo, categoria_id=None, cache_productos=None, cache_categorias=None):
        super().__init__(parent)
        self.parent = parent
        self.categoria_id = categoria_id
        self.resultado = False
        
        # Guardamos los cachés pasados como argumentos
        self.cache_productos = cache_productos if cache_productos is not None else []
        self.cache_categorias = cache_categorias if cache_categorias is not None else []
        # --- FIN CORRECCIÓN ---
        
        self.title(titulo)
        self.geometry("500x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._construir_ui()
        self._cargar_datos()
        
    def _construir_ui(self):
        """Construir interfaz del diálogo"""
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        ttk.Label(main_frame, text=self.title(), 
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 20))
        
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill="x", pady=10)
        
        ttk.Label(form_frame, text="Nombre de la Categoría:*", 
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=12)
        self.nombre_var = tk.StringVar()
        self.nombre_entry = ttk.Entry(form_frame, textvariable=self.nombre_var, 
                                     width=40, font=("Segoe UI", 10))
        self.nombre_entry.grid(row=0, column=1, sticky="ew", pady=12, padx=(15, 0))
        
        ttk.Label(form_frame, text="Descripción:", 
                 font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="nw", pady=12)
        self.descripcion_text = tk.Text(form_frame, width=40, height=6, 
                                       font=("Segoe UI", 10), wrap="word")
        self.descripcion_text.grid(row=1, column=1, sticky="ew", pady=12, padx=(15, 0))
        
        scrollbar = ttk.Scrollbar(form_frame, orient="vertical", command=self.descripcion_text.yview)
        self.descripcion_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=2, sticky="ns", pady=12)
        
        self.info_frame = ttk.Frame(form_frame)
        self.info_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(15, 5))
        
        form_frame.grid_columnconfigure(1, weight=1)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(btn_frame, text="💾 Guardar", style="Success.TButton",
                  command=self._guardar).pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame, text="❌ Cancelar",
                  command=self.destroy).pack(side="left")
        
        self.nombre_entry.focus()
        
    def _cargar_datos(self):
        """Cargar datos si es edición (lee del caché)"""
        if self.categoria_id:
            try:
                # --- CORRECCIÓN ERROR 4/5 ---
                categoria = next((c for c in self.cache_categorias if c['id'] == self.categoria_id), None)
                
                if categoria:
                    self.nombre_var.set(categoria['nombre'])
                    if categoria.get('descripcion'):
                        self.descripcion_text.insert("1.0", categoria['descripcion'])
                    
                    productos = self.cache_productos
                    # --- FIN CORRECCIÓN ---
                    
                    productos_categoria = [p for p in productos if p.get('categoria_id') == self.categoria_id]
                    
                    if productos_categoria:
                        info_text = f"📦 Esta categoría tiene {len(productos_categoria)} productos asociados"
                        info_label = ttk.Label(self.info_frame, text=info_text, 
                                             font=("Segoe UI", 9, "italic"),
                                             foreground="#6c757d")
                        info_label.pack(anchor="w")
                        
            except Exception as e:
                messagebox.showerror("Error", f"No se pudieron cargar los datos:\n{str(e)}")
    
    def _validar_formulario(self):
        """Validar formulario (usa caché para verificar duplicados)"""
        nombre = self.nombre_var.get().strip()
        
        if not nombre:
            messagebox.showwarning("Validación", "El nombre de la categoría es obligatorio")
            return False
        
        if len(nombre) < 2:
            messagebox.showwarning("Validación", "El nombre debe tener al menos 2 caracteres")
            return False
        
        try:
            # --- CORRECCIÓN ERROR 4/5 ---
            categorias = self.cache_categorias
            # --- FIN CORRECCIÓN ---
            for cat in categorias:
                if cat['nombre'].lower() == nombre.lower():
                    if self.categoria_id and cat['id'] == self.categoria_id:
                        continue
                    messagebox.showwarning("Validación", f"Ya existe una categoría con el nombre '{nombre}'")
                    return False
        except:
            pass  
        
        return True
    
    def _guardar(self):
        """Guardar categoría"""
        if not self._validar_formulario():
            return
            
        try:
            nombre = self.nombre_var.get().strip()
            descripcion = self.descripcion_text.get("1.0", "end-1c").strip()
            
            if self.categoria_id:
                CategoriaRepo.actualizar(self.categoria_id, nombre, descripcion if descripcion else None)
                messagebox.showinfo("Éxito", "✅ Categoría actualizada correctamente")
            else:
                CategoriaRepo.agregar(nombre, descripcion if descripcion else None)
                messagebox.showinfo("Éxito", "✅ Categoría agregada correctamente")
            
            self.resultado = True
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"❌ No se pudo guardar la categoría:\n{str(e)}")


class CategoriasFrame(ModernBaseFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.make_modern_toolbar([
            ("➕ Agregar Categoría", self.agregar_categoria, "success"),
            ("✏️ Editar Seleccionada", self.editar_categoria, "accent"),
            ("🗑️ Eliminar Seleccionada", self.eliminar_categoria, "danger")
        ], "📂 Gestión de Categorías")
        
        self.search_var = self.create_search_bar("Buscar categorías...", self.buscar_categorias)
        
        columns = [
            ("id", "ID", 80, "center"),
            ("nombre", "Nombre", 250, "w"),
            ("descripcion", "Descripción", 400, "w"),
            ("num_productos", "N° Productos", 100, "center") # Columna añadida
        ]
        
        self.tree = self.create_modern_treeview(columns)
        
        self.tree.bind("<Double-1>", lambda e: self.editar_categoria())
        self.tree.bind("<Delete>", lambda e: self.eliminar_categoria())
        
    def load(self):
        """Cargar categorías con conteo de productos (desde caché)"""
        self.buscar_categorias(self.search_var.get())

    def buscar_categorias(self, query):
        """Buscar categorías por nombre o descripción (desde caché)"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            categorias = self.app_root.cache_categorias
            productos = self.app_root.cache_productos
            
            productos_por_categoria = {}
            for producto in productos:
                cat_id = producto.get('categoria_id')
                if cat_id:
                    productos_por_categoria[cat_id] = productos_por_categoria.get(cat_id, 0) + 1
            
            if not query or query == "Buscar categorías...":
                query = ""
            
            query = query.lower()
            
            for idx, categoria in enumerate(categorias):
                if query:
                    if not (query in categoria['nombre'].lower() or 
                           query in (categoria.get('descripcion') or '').lower()):
                        continue
                    
                tags = ['even' if idx % 2 == 0 else 'odd']
                num_productos = productos_por_categoria.get(categoria['id'], 0)
                
                if num_productos == 0:
                    tags.append("inactive") # Marcar categorías vacías
                
                self.tree.insert("", tk.END, values=(
                    categoria["id"],
                    categoria["nombre"],
                    categoria["descripcion"] or "Sin descripción",
                    f"{num_productos} productos"
                ), tags=tuple(tags))
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las categorías desde el caché:\n{str(e)}")

    def agregar_categoria(self):
        """Agregar nueva categoría"""
        # --- CORRECCIÓN ERROR 4/5 ---
        dialog = CategoriaDialog(self, "Nueva Categoría",
                                 cache_productos=self.app_root.cache_productos,
                                 cache_categorias=self.app_root.cache_categorias)
        # --- FIN CORRECCIÓN ---
        self.wait_window(dialog)
        if dialog.resultado:
            self.app_root.refresh_all_caches_and_tabs()

    def editar_categoria(self):
        """Editar categoría seleccionada"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Seleccione una categoría para editar")
            return
        
        try:
            categoria_id = self.tree.item(seleccion[0])["values"][0]
            # --- CORRECCIÓN ERROR 4/5 ---
            dialog = CategoriaDialog(self, "Editar Categoría", categoria_id,
                                     cache_productos=self.app_root.cache_productos,
                                     cache_categorias=self.app_root.cache_categorias)
            # --- FIN CORRECCIÓN ---
            self.wait_window(dialog)
            if dialog.resultado:
                self.app_root.refresh_all_caches_and_tabs()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el editor:\n{e}")


    def eliminar_categoria(self):
        """Eliminar categoría seleccionada (si no tiene productos)"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Seleccione una categoría para eliminar")
            return
            
        try:
            categoria_id = self.tree.item(seleccion[0])["values"][0]
            categoria_nombre = self.tree.item(seleccion[0])["values"][1]
            num_productos_str = self.tree.item(seleccion[0])["values"][3]
            num_productos = int(num_productos_str.split()[0])
            
            if num_productos > 0:
                messagebox.showerror(
                    "Error", 
                    f"No se puede eliminar la categoría '{categoria_nombre}'\n\n"
                    f"Tiene {num_productos} productos asociados.\n"
                    f"Reasigne los productos a otra categoría antes de eliminar."
                )
                return
            
            if messagebox.askyesno(
                "Confirmar Eliminación", 
                f"¿Está seguro de que desea eliminar la categoría '{categoria_nombre}'?\n\n"
                "Esta acción no se puede deshacer."
            ):
                CategoriaRepo.eliminar(categoria_id)
                messagebox.showinfo("Éxito", "✅ Categoría eliminada correctamente")
                self.app_root.refresh_all_caches_and_tabs()
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo eliminar la categoría:\n{str(e)}")

class HistorialVentasFrame(ModernBaseFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.make_modern_toolbar([
            ("📊 Generar Reporte", self.generar_reporte, "accent"),
            ("📋 Ver Detalles", self.ver_detalles, "success")
        ], "🧾 Historial de Ventas")
        
        columns = [
            ("id", "ID", 80, "center"),
            ("fecha", "Fecha y Hora", 180, "center"),
            ("total", "Total", 120, "center"),
            ("forma_pago", "Forma de Pago", 150, "center")
        ]
        
        self.tree = self.create_modern_treeview(columns)
    
    def load(self):
        """Carga el historial desde el caché"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            for idx, v in enumerate(self.app_root.cache_ventas):
                tags = ['even' if idx % 2 == 0 else 'odd']
                self.tree.insert("", tk.END, values=(
                    v["id"],
                    v["fecha"].strftime("%d/%m/%Y %H:%M"),
                    f"${v['total']:.2f}",
                    v["forma_pago"]
                ), tags=tuple(tags))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el historial desde el caché:\n{e}")
    
    def generar_reporte(self):
        """Generar reporte (usa datos frescos)"""
        ReportesManager.generar_reporte_ventas_completo(self)

    def ver_detalles(self):
        """Ver detalles de una venta (usa datos frescos)"""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Seleccione una venta para ver sus detalles.")
            return
        
        try:
            venta_id = self.tree.item(seleccion[0])["values"][0]
            venta = VentaRepo.buscar_por_id(venta_id)
            
            if not venta:
                messagebox.showerror("Error", f"No se pudo encontrar la venta ID: {venta_id}")
                return
            
            detalles_texto = f"--- DETALLES DE VENTA #{venta_id} ---\n\n"
            detalles_texto += f"Fecha: {venta['fecha'].strftime('%d/%m/%Y %H:%M')}\n"
            detalles_texto += f"Total: ${float(venta['total']):,.2f}\n"
            detalles_texto += f"Forma de Pago: {venta['forma_pago']}\n"
            if 'descuento' in venta: # Comprobar si la columna existe
                detalles_texto += f"Descuento: {venta.get('descuento', 0)}%\n\n"
            detalles_texto += "--- PRODUCTOS ---\n"
            
            if "items" in venta and venta["items"]:
                for item in venta["items"]:
                    subtotal = float(item.get('subtotal', item['cantidad'] * item['precio_unitario']))
                    detalles_texto += (
                        f"- {item['producto']} (x{item['cantidad']}) "
                        f"@ ${float(item['precio_unitario']):,.2f} c/u = "
                        f"${subtotal:,.2f}\n"
                    )
            else:
                detalles_texto += "No se encontraron productos detallados para esta venta."

            messagebox.showinfo(f"Detalles Venta #{venta_id}", detalles_texto)

        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los detalles:\n{e}")

class PuntosVentaFrame(ModernBaseFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.make_modern_toolbar([
            ("➕ Agregar Punto", self.add, "success"),
            ("✏️ Editar Seleccionado", self.edit, "accent")
        ], "🏪 Puntos de Venta")
        
        columns = [
            ("id", "ID", 80, "center"),
            ("nombre", "Nombre", 200, "w"),
            ("direccion", "Dirección", 300, "w"),
            ("telefono", "Teléfono", 150, "center")
        ]
        
        self.tree = self.create_modern_treeview(columns)
    
    def load(self):
        """Cargar Puntos de Venta (desde caché)"""
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        try:
            for idx, p in enumerate(self.app_root.cache_puntos_venta):
                tags = ['even' if idx % 2 == 0 else 'odd']
                self.tree.insert("", tk.END, values=(
                    p["id"], p["nombre"], p["direccion"], p["telefono"]
                ), tags=tuple(tags))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar los Puntos de Venta:\n{e}")
    
    def add(self):
        nombre = simpledialog.askstring("Nuevo Punto", "Nombre del punto de venta:")
        if nombre:
            direccion = simpledialog.askstring("Nuevo Punto", "Dirección:")
            telefono = simpledialog.askstring("Nuevo Punto", "Teléfono:")
            if direccion is None or telefono is None:
                messagebox.showinfo("Cancelado", "Operación cancelada.")
                return
            try:
                PuntoVentaRepo.agregar(nombre, direccion, telefono)
                self.app_root.refresh_all_caches_and_tabs()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo agregar el punto de venta:\n{e}")
    
    def edit(self):
        seleccion = self.tree.selection() 
        if seleccion:
            messagebox.showinfo("En desarrollo", "Edición de puntos de venta en desarrollo")
        else:
            messagebox.showwarning("Selección", "Seleccione un punto de venta para editar.")


if __name__ == "__main__":
    app = VentasApp()
    app.mainloop()