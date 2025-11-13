import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import os
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import tempfile
from repos import ProductoRepo, VentaRepo, PuntoVentaRepo

logger = logging.getLogger("SimulacionVentasPro")

class SimuladorVentasPro:
    """Simulador PROFESIONAL de ventas usando base de datos real"""
    
    def __init__(self):
        self.ejecutando = False
        self.hilo_simulacion = None
        self.ventas_generadas = 0
        self.ventas_objetivo = 0
        self.productos_disponibles = []
        self.probabilidades_productos = {}
        self.ventas_realizadas = []
        
    def cargar_productos_reales(self):
        """Cargar productos reales de la base de datos - SOLO ACTIVOS Y CON STOCK"""
        try:
            todos_productos = ProductoRepo.listar()
            
            # Filtrar solo productos activos y con stock > 0
            self.productos_disponibles = [
                p for p in todos_productos 
                if p.get('activo', True) and p.get('stock', 0) > 0
            ]
            
            if not self.productos_disponibles:
                logger.warning("No hay productos activos con stock en la base de datos")
                return False
                
            # Convertir precios Decimal a float si es necesario
            for producto in self.productos_disponibles:
                if isinstance(producto['precio'], Decimal):
                    producto['precio'] = float(producto['precio'])
            
            logger.info(f"Cargados {len(self.productos_disponibles)} productos activos con stock")
            return True
            
        except Exception as e:
            logger.error(f"Error cargando productos reales: {e}")
            return False
    
    def _calcular_probabilidades(self):
        """Calcular probabilidades de venta basadas en categorías y stock"""
        categorias_peso = {
            'Bebidas': 0.22,
            'Lácteos': 0.16,
            'Enlatados': 0.07,
            'Limpieza': 0.06,
            'Carnes': 0.05,
            'Frutas': 0.02,
            'Verduras': 0.02
        }
        
        self.probabilidades_productos = {}
        for producto in self.productos_disponibles:
            categoria = producto.get('categoria', 'Otros')
            peso = categorias_peso.get(categoria, 0.04)
            
            precio = producto['precio']
            precio_factor = max(0.1, 1.5 - (precio / 100))
            
            stock = producto.get('stock', 0)
            stock_factor = min(2.0, stock / 10)  # Normalizar stock
            
            probabilidad = peso * precio_factor * stock_factor
            self.probabilidades_productos[producto['id']] = probabilidad
    
    def _obtener_producto_actualizado(self, producto_id):
        """Obtener información actualizada del producto desde la BD"""
        try:
            producto_actual = ProductoRepo.buscar_por_id(producto_id)
            if producto_actual and producto_actual.get('activo', True):
                if isinstance(producto_actual['precio'], Decimal):
                    producto_actual['precio'] = float(producto_actual['precio'])
                return producto_actual
        except Exception as e:
            logger.error(f"Error obteniendo producto actualizado: {e}")
        return None
    
    def _verificar_stock_suficiente(self, producto_id, cantidad):
        """Verificar que el producto tenga stock suficiente"""
        try:
            producto = self._obtener_producto_actualizado(producto_id)
            if producto and producto.get('stock', 0) >= cantidad:
                return True, producto
            return False, producto
        except Exception as e:
            logger.error(f"Error verificando stock: {e}")
            return False, None
    
    def _generar_carrito_inteligente(self):
        """Generar carrito de compra inteligente con productos de la BD"""
        num_items = random.choices([1, 2, 3, 4, 5], 
                                 weights=[0.15, 0.25, 0.30, 0.20, 0.10], 
                                 k=1)[0]
        
        carrito = []
        productos_intentados = set()
        
        for _ in range(num_items):
            productos_posibles = [
                p for p in self.productos_disponibles 
                if p['id'] not in productos_intentados 
                and p.get('stock', 0) > 0
            ]
            
            if not productos_posibles:
                break
            
            pesos = [self.probabilidades_productos.get(p['id'], 0.01) for p in productos_posibles]
            
            producto_seleccionado = random.choices(productos_posibles, weights=pesos, k=1)[0]
            productos_intentados.add(producto_seleccionado['id'])
            
            stock_ok, producto_actual = self._verificar_stock_suficiente(
                producto_seleccionado['id'], 1
            )
            
            if not stock_ok or not producto_actual:
                continue
            
            max_cantidad = min(3, producto_actual.get('stock', 1))
            cantidad = random.choices([1, 2, 3], weights=[0.8, 0.15, 0.05], k=1)[0]
            cantidad = min(cantidad, max_cantidad)
            
            stock_final_ok, producto_final = self._verificar_stock_suficiente(
                producto_seleccionado['id'], cantidad
            )
            
            if stock_final_ok and producto_final:
                carrito.append({
                    'producto_id': producto_final['id'],
                    'nombre': producto_final['nombre'],
                    'precio': producto_final['precio'],
                    'cantidad': cantidad,
                    'categoria': producto_final.get('categoria', 'Otros'),
                    'codigo_barras': producto_final.get('codigo_barras', '')
                })
        
        return carrito
    
    def _generar_forma_pago_realista(self):
        """Generar forma de pago basada en horario"""
        hora_actual = datetime.now().hour
        
        if 6 <= hora_actual < 12:  
            return random.choices(['EFECTIVO', 'TARJETA', 'TRANSFERENCIA'], 
                                weights=[0.75, 0.20, 0.05], k=1)[0]
        elif 12 <= hora_actual < 18:  
            return random.choices(['EFECTIVO', 'TARJETA', 'TRANSFERENCIA'], 
                                weights=[0.60, 0.35, 0.05], k=1)[0]
        else: 
            return random.choices(['EFECTIVO', 'TARJETA', 'TRANSFERENCIA'], 
                                weights=[0.50, 0.45, 0.05], k=1)[0]
    
    def _generar_tiempo_entre_ventas(self):
        """Generar tiempo entre ventas basado en horario real"""
        hora_actual = datetime.now().hour
        dia_semana = datetime.now().weekday()
        

        factor_fin_semana = 0.7 if dia_semana >= 5 else 1.0
        
        if 6 <= hora_actual < 10:    
            return random.uniform(120, 300) * factor_fin_semana
        elif 10 <= hora_actual < 14:
            return random.uniform(30, 90) * factor_fin_semana
        elif 14 <= hora_actual < 17: 
            return random.uniform(60, 150) * factor_fin_semana
        elif 17 <= hora_actual < 20: 
            return random.uniform(25, 75) * factor_fin_semana
        elif 20 <= hora_actual < 22:
            return random.uniform(90, 240) * factor_fin_semana
        else:                  
            return random.uniform(300, 600) * factor_fin_semana
    
    def generar_ticket_pdf(self, venta_info, carrito):
        """Generar ticket en PDF profesional"""
        try:
       
            tickets_dir = "tickets_simulacion"
            os.makedirs(tickets_dir, exist_ok=True)
            
       
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{tickets_dir}/ticket_venta_{venta_info['venta_id']}_{timestamp}.pdf"
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4
            
            c.setFont("Helvetica-Bold", 16)
            
            c.drawString(100, height - 50, "⚡ SUPERMERCADO VIRTUAL")
            c.setFont("Helvetica", 10)
            c.drawString(100, height - 70, "Ticket de Simulación - Ventas Automatizadas")
            
            c.line(50, height - 85, width - 50, height - 85)
            
            y_position = height - 110
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y_position, f"TICKET DE VENTA #{venta_info['venta_id']}")
            
            y_position -= 20
            c.setFont("Helvetica", 10)
            c.drawString(50, y_position, f"Fecha: {venta_info['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}")
            y_position -= 15
            c.drawString(50, y_position, f"Forma de Pago: {venta_info['forma_pago']}")
            y_position -= 15
            c.drawString(50, y_position, f"Items: {venta_info['items']}")
            
            y_position -= 20
            c.line(50, y_position, width - 50, y_position)
            
            y_position -= 20
            c.setFont("Helvetica-Bold", 10)
            c.drawString(50, y_position, "PRODUCTO")
            c.drawString(300, y_position, "CANT.")
            c.drawString(350, y_position, "PRECIO")
            c.drawString(450, y_position, "SUBTOTAL")
            
            y_position -= 15
            c.setFont("Helvetica", 9)
            for item in carrito:
                if y_position < 100:  
                    c.showPage()
                    y_position = height - 50
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(50, y_position, "PRODUCTO (cont.)")
                    c.drawString(300, y_position, "CANT.")
                    c.drawString(350, y_position, "PRECIO")
                    c.drawString(450, y_position, "SUBTOTAL")
                    y_position -= 20
                    c.setFont("Helvetica", 9)
                
                nombre = item['nombre']
                if len(nombre) > 40:
                    nombre = nombre[:37] + "..."
                
                c.drawString(50, y_position, nombre)
                c.drawString(300, y_position, str(item['cantidad']))
                c.drawString(350, y_position, f"${item['precio']:.2f}")
                subtotal = item['precio'] * item['cantidad']
                c.drawString(450, y_position, f"${subtotal:.2f}")
                y_position -= 15
            
            y_position -= 20
            c.line(50, y_position, width - 50, y_position)
            y_position -= 20
            
            c.setFont("Helvetica-Bold", 12)
            c.drawString(350, y_position, "TOTAL:")
            c.drawString(450, y_position, f"${venta_info['total']:.2f}")
            y_position -= 40
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(50, y_position, "Ticket de simulación - Datos reales de base de datos")
            y_position -= 12
            c.drawString(50, y_position, "Sistema de Simulación de Ventas - Stock validado en tiempo real")
            
            c.save()
            
            return filename
            
        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            return None
    
    def simular_venta_unica(self):
        """Simular una única venta con validación de stock en tiempo real"""
        try:
            carrito = self._generar_carrito_inteligente()
            
            if not carrito:
                logger.warning("No se pudo generar carrito de compra válido")
                return None
            
            carrito_valido = []
            for item in carrito:
                stock_ok, producto_actual = self._verificar_stock_suficiente(
                    item['producto_id'], item['cantidad']
                )
                if stock_ok and producto_actual:
                    carrito_valido.append(item)
                else:
                    logger.warning(f"Stock insuficiente para {item['nombre']}")
            
            if not carrito_valido:
                logger.warning("Carrito vacío después de validar stock")
                return None
            
            forma_pago = self._generar_forma_pago_realista()
            total = sum(item['precio'] * item['cantidad'] for item in carrito_valido)
            
            puntos = PuntoVentaRepo.listar()
            punto_venta_id = puntos[0]['id'] if puntos else 1
            
            items_venta = []
            for item in carrito_valido:
                items_venta.append({
                    'producto_id': item['producto_id'],
                    'nombre': item['nombre'],
                    'precio': item['precio'],
                    'cantidad': item['cantidad']
                })
            
            try:
                venta_id = VentaRepo.crear_venta(
                    punto_venta_id=punto_venta_id,
                    items=items_venta,
                    forma_pago=forma_pago
                )
                
                venta_info = {
                    'venta_id': venta_id,
                    'items': len(carrito_valido),
                    'total': round(total, 2),
                    'forma_pago': forma_pago,
                    'timestamp': datetime.now(),
                    'carrito': carrito_valido,
                    'real': True
                }
                
                pdf_path = self.generar_ticket_pdf(venta_info, carrito_valido)
                venta_info['pdf_path'] = pdf_path
                
                self.cargar_productos_reales()
                self._calcular_probabilidades()
                
                return venta_info
                
            except Exception as e:
                logger.error(f"Error creando venta en BD: {e}")
                return self._simular_venta_demo(carrito_valido, forma_pago)
            
        except Exception as e:
            logger.error(f"Error en simulación de venta: {e}")
            return None
    
    def _simular_venta_demo(self, carrito, forma_pago):
        """Simular venta demo sin guardar en BD (solo para fallos)"""
        total = sum(item['precio'] * item['cantidad'] for item in carrito)
        
        venta_info = {
            'venta_id': random.randint(10000, 99999),
            'items': len(carrito),
            'total': round(total, 2),
            'forma_pago': forma_pago,
            'timestamp': datetime.now(),
            'carrito': carrito,
            'real': False,
            'demo': True
        }
        
        pdf_path = self.generar_ticket_pdf(venta_info, carrito)
        venta_info['pdf_path'] = pdf_path
        
        return venta_info
    
    def iniciar_simulacion(self, total_ventas, callback_progreso=None, callback_venta=None, callback_pdf=None):
        """Iniciar simulación de múltiples ventas"""
        if self.ejecutando:
            return False
        
        if not self.cargar_productos_reales():
            messagebox.showerror("Error", "No hay productos activos con stock en la base de datos")
            return False
        
        self._calcular_probabilidades()
        
        self.ejecutando = True
        self.ventas_objetivo = total_ventas
        self.ventas_generadas = 0
        self.ventas_realizadas = []
        
        def hilo_simulacion():
            logger.info(f"Iniciando simulación de {total_ventas} ventas con productos reales")
            
            while self.ejecutando and self.ventas_generadas < self.ventas_objetivo:
                try:
                    venta_info = self.simular_venta_unica()
                    
                    if venta_info:
                        self.ventas_generadas += 1
                        self.ventas_realizadas.append(venta_info)
                        
                        if callback_venta:
                            callback_venta(venta_info)
                        
                        if callback_pdf and venta_info.get('pdf_path'):
                            callback_pdf(venta_info['pdf_path'])
                        
                        if callback_progreso:
                            progreso = (self.ventas_generadas / self.ventas_objetivo) * 100
                            callback_progreso(progreso, self.ventas_generadas, self.ventas_objetivo)
                    
                    if self.ventas_generadas < self.ventas_objetivo:
                        tiempo_espera = self._generar_tiempo_entre_ventas()
                        tiempo_inicio = time.time()
                        
                        while time.time() - tiempo_inicio < tiempo_espera:
                            if not self.ejecutando:
                                break
                            time.sleep(0.1)
                            
                except Exception as e:
                    logger.error(f"Error en hilo de simulación: {e}")
                    time.sleep(2)
            
            self.ejecutando = False
            if callback_progreso:
                callback_progreso(100, self.ventas_generadas, self.ventas_objetivo, completado=True)
        
        self.hilo_simulacion = threading.Thread(target=hilo_simulacion, daemon=True)
        self.hilo_simulacion.start()
        return True
    
    def detener_simulacion(self):
        """Detener la simulación en curso"""
        self.ejecutando = False
        if self.hilo_simulacion and self.hilo_simulacion.is_alive():
            self.hilo_simulacion.join(timeout=3.0)
    
    def obtener_estadisticas(self):
        """Obtener estadísticas completas de la simulación"""
        if not self.ventas_realizadas:
            return {}
        
        total_ventas = len(self.ventas_realizadas)
        ventas_reales = sum(1 for v in self.ventas_realizadas if v.get('real', False))
        ventas_demo = total_ventas - ventas_reales
        total_ingresos = sum(v['total'] for v in self.ventas_realizadas)
        avg_ticket = total_ingresos / total_ventas if total_ventas > 0 else 0
        
        formas_pago = {}
        for venta in self.ventas_realizadas:
            fp = venta['forma_pago']
            formas_pago[fp] = formas_pago.get(fp, 0) + 1
        
        productos_vendidos = {}
        for venta in self.ventas_realizadas:
            for item in venta.get('carrito', []):
                producto_id = item['producto_id']
                if producto_id not in productos_vendidos:
                    productos_vendidos[producto_id] = {
                        'nombre': item['nombre'],
                        'cantidad_total': 0,
                        'ingresos_total': 0
                    }
                productos_vendidos[producto_id]['cantidad_total'] += item['cantidad']
                productos_vendidos[producto_id]['ingresos_total'] += item['precio'] * item['cantidad']
        
        top_productos = sorted(productos_vendidos.items(), 
                             key=lambda x: x[1]['cantidad_total'], 
                             reverse=True)[:10]
        
        return {
            'total_ventas': total_ventas,
            'ventas_reales': ventas_reales,
            'ventas_demo': ventas_demo,
            'total_ingresos': total_ingresos,
            'ticket_promedio': avg_ticket,
            'formas_pago': formas_pago,
            'top_productos': top_productos,
            'productos_disponibles': len(self.productos_disponibles)
        }


class SimulacionVentasFrame(ttk.Frame):
    """Interfaz moderna para controlar la simulación de ventas"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.simulador = SimuladorVentasPro()  
        self._construir_ui()
    
    def _construir_ui(self):
        """Construir interfaz de usuario moderna"""

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        

        control_frame = ttk.LabelFrame(main_frame, text="🎮 CONTROL DE SIMULACIÓN", padding=15)
        control_frame.pack(fill="x", pady=(0, 10))
        
        input_frame = ttk.Frame(control_frame)
        input_frame.pack(fill="x", pady=5)
        
        ttk.Label(input_frame, text="Ventas a simular:", 
                 font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
        
        self.ventas_var = tk.StringVar(value="25")
        ventas_entry = ttk.Entry(input_frame, textvariable=self.ventas_var, 
                                width=8, font=("Segoe UI", 10), justify="center")
        ventas_entry.pack(side="left", padx=(0, 20))
        
        self.btn_iniciar = ttk.Button(input_frame, text="🚀 INICIAR SIMULACIÓN", 
                                     command=self._iniciar_simulacion, style="Success.TButton")
        self.btn_iniciar.pack(side="left", padx=(0, 10))
        
        self.btn_detener = ttk.Button(input_frame, text="⏹️ DETENER", 
                                     command=self._detener_simulacion, state="disabled")
        self.btn_detener.pack(side="left", padx=(0, 10))
        
        self.btn_abrir_carpeta = ttk.Button(input_frame, text="📁 ABRIR CARPETA TICKETS",
                                           command=self._abrir_carpeta_tickets)
        self.btn_abrir_carpeta.pack(side="left")
        
        self.progress_frame = ttk.Frame(control_frame)
        self.progress_frame.pack(fill="x", pady=10)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", 
                                           mode="determinate", length=500)
        self.progress_bar.pack(fill="x", pady=(5, 0))
        
        self.progress_label = ttk.Label(self.progress_frame, text="Listo para simular", 
                                       font=("Segoe UI", 9))
        self.progress_label.pack(anchor="w")
        
        stats_frame = ttk.LabelFrame(main_frame, text="📊 ESTADÍSTICAS EN TIEMPO REAL", padding=10)
        stats_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.stats_text = tk.Text(stats_frame, height=12, font=("Consolas", 9), 
                                 state="disabled", wrap="word")
        scrollbar = ttk.Scrollbar(stats_frame, orient="vertical", command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=scrollbar.set)
        
        self.stats_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        tickets_frame = ttk.LabelFrame(main_frame, text="🧾 ÚLTIMOS TICKETS GENERADOS", padding=10)
        tickets_frame.pack(fill="x")
        
        self.tickets_text = tk.Text(tickets_frame, height=6, font=("Consolas", 8), 
                                   state="disabled", wrap="word")
        tickets_scrollbar = ttk.Scrollbar(tickets_frame, orient="vertical", command=self.tickets_text.yview)
        self.tickets_text.configure(yscrollcommand=tickets_scrollbar.set)
        
        self.tickets_text.pack(side="left", fill="both", expand=True)
        tickets_scrollbar.pack(side="right", fill="y")
        
        self.ultimas_ventas = []
        self.tickets_generados = []
        self._actualizar_estadisticas()
    
    def _iniciar_simulacion(self):
        """Iniciar la simulación"""
        try:
            total_ventas = int(self.ventas_var.get())
            if total_ventas <= 0:
                messagebox.showwarning("Error", "Ingrese un número positivo de ventas")
                return
            
            self.btn_iniciar.config(state="disabled")
            self.btn_detener.config(state="normal")
            self.progress_bar['value'] = 0
            
            self.ultimas_ventas = []
            self.tickets_generados = []
            
            exito = self.simulador.iniciar_simulacion(
                total_ventas=total_ventas,
                callback_progreso=self._actualizar_progreso,
                callback_venta=self._registrar_venta,
                callback_pdf=self._registrar_ticket
            )
            
            if not exito:
                messagebox.showerror("Error", "No se pudo iniciar la simulación")
                
        except ValueError:
            messagebox.showerror("Error", "Ingrese un número válido de ventas")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo iniciar la simulación: {e}")
    
    def _detener_simulacion(self):
        """Detener la simulación"""
        self.simulador.detener_simulacion()
        self.btn_iniciar.config(state="normal")
        self.btn_detener.config(state="disabled")
        self.progress_label.config(text="Simulación detenida por el usuario")
    
    def _abrir_carpeta_tickets(self):
        """Abrir carpeta de tickets generados"""
        tickets_dir = "tickets_simulacion"
        if os.path.exists(tickets_dir):
            os.startfile(tickets_dir)
        else:
            messagebox.showinfo("Información", "Aún no se han generado tickets")
    
    def _actualizar_progreso(self, porcentaje, ventas_generadas, ventas_objetivo, completado=False):
        """Actualizar barra de progreso"""
        def actualizar():
            self.progress_bar['value'] = porcentaje
            if completado:
                self.progress_label.config(text=f"✅ SIMULACIÓN COMPLETADA: {ventas_generadas} ventas")
                self.btn_iniciar.config(state="normal")
                self.btn_detener.config(state="disabled")
                

                self._mostrar_resumen_final()
            else:
                self.progress_label.config(text=f"Simulando: {ventas_generadas}/{ventas_objetivo} ({porcentaje:.1f}%)")
        
        self.after(0, actualizar)
    
    def _registrar_venta(self, venta_info):
        """Registrar una venta generada"""
        def actualizar():
            self.ultimas_ventas.insert(0, venta_info)
            if len(self.ultimas_ventas) > 50:
                self.ultimas_ventas = self.ultimas_ventas[:50]
            
            self._actualizar_estadisticas()
        
        self.after(0, actualizar)
    
    def _registrar_ticket(self, pdf_path):
        """Registrar ticket PDF generado"""
        def actualizar():
            self.tickets_generados.insert(0, pdf_path)
            if len(self.tickets_generados) > 10:
                self.tickets_generados = self.tickets_generados[:10]
            
            self._actualizar_tickets()
        
        self.after(0, actualizar)
    
    def _actualizar_estadisticas(self):
        """Actualizar panel de estadísticas"""
        stats = self.simulador.obtener_estadisticas()
        
        if not stats:
            stats_text = "Esperando datos de simulación..."
        else:
            formas_pago_text = ""
            for fp, count in stats['formas_pago'].items():
                porcentaje = (count / stats['total_ventas']) * 100
                formas_pago_text += f"  {fp}: {count} ({porcentaje:.1f}%)\n"
            
            top_productos_text = ""
            for i, (prod_id, datos) in enumerate(stats['top_productos'][:5], 1):
                nombre = datos['nombre'][:30] + "..." if len(datos['nombre']) > 30 else datos['nombre']
                top_productos_text += f"  {i}. {nombre}\n     Vendidos: {datos['cantidad_total']} - Total: ${datos['ingresos_total']:.2f}\n"
            
            stats_text = f"""
ESTADÍSTICAS DE SIMULACIÓN:
────────────────────────────────────────
Ventas realizadas: {stats['total_ventas']}
  • Reales en BD: {stats['ventas_reales']}
  • Demo: {stats['ventas_demo']}
Ingresos totales: ${stats['total_ingresos']:,.2f}
Ticket promedio: ${stats['ticket_promedio']:.2f}
Productos disponibles: {stats['productos_disponibles']}

FORMAS DE PAGO:
{formas_pago_text}
TOP 5 PRODUCTOS MÁS VENDIDOS:
{top_productos_text}
"""
        
        self.stats_text.config(state="normal")
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text.strip())
        self.stats_text.config(state="disabled")
    
    def _actualizar_tickets(self):
        """Actualizar lista de tickets generados"""
        tickets_text = "TICKETS PDF GENERADOS:\n\n"
        
        for i, ticket_path in enumerate(self.tickets_generados[:8], 1):
            nombre_archivo = os.path.basename(ticket_path)
            tickets_text += f"{i}. {nombre_archivo}\n"
        
        if not self.tickets_generados:
            tickets_text += "No se han generado tickets aún"
        
        self.tickets_text.config(state="normal")
        self.tickets_text.delete(1.0, tk.END)
        self.tickets_text.insert(1.0, tickets_text.strip())
        self.tickets_text.config(state="disabled")
    
    def _mostrar_resumen_final(self):
        """Mostrar resumen al finalizar la simulación"""
        stats = self.simulador.obtener_estadisticas()
        
        if stats:
            messagebox.showinfo(
                "🏁 SIMULACIÓN COMPLETADA", 
                f"✅ Simulación finalizada exitosamente\n\n"
                f"📊 RESUMEN FINAL:\n"
                f"• Ventas realizadas: {stats['total_ventas']}\n"
                f"• Ventas reales en BD: {stats['ventas_reales']}\n"
                f"• Ingresos totales: ${stats['total_ingresos']:,.2f}\n"
                f"• Ticket promedio: ${stats['ticket_promedio']:.2f}\n"
                f"• Productos disponibles: {stats['productos_disponibles']}\n\n"
                f"🧾 Se generaron {len(self.tickets_generados)} tickets PDF\n"
                f"📁 Guardados en: tickets_simulacion/"
            )