from typing import List, Dict, Optional, Any
from config import get_connection
import time 
import datetime # Importar datetime para la nueva función

def _dict_rows(cur) -> List[Dict[str, Any]]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def _dict_one(cur) -> Optional[Dict[str, Any]]:
    row = cur.fetchone()
    if not row:
        return None
    cols = [c[0] for c in cur.description]
    return dict(zip(cols, row))

class CategoriaRepo:
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nombre, descripcion FROM categorias ORDER BY nombre")
            return _dict_rows(cur)
        finally:
            conn.close()

    @staticmethod
    def agregar(nombre: str, descripcion: str = None):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO categorias (nombre, descripcion) VALUES (?, ?)", (nombre, descripcion))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def actualizar(categoria_id: int, nombre: str, descripcion: str = None):
        """Actualizar una categoría existente"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE categorias 
                SET nombre = ?, descripcion = ? 
                WHERE id = ?
            """, (nombre, descripcion, categoria_id))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def eliminar(categoria_id: int):
        """Eliminar una categoría (solo si no tiene productos)"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM productos WHERE categoria_id = ?", (categoria_id,))
            count = cur.fetchone()[0]
            
            if count > 0:
                raise Exception("No se puede eliminar la categoría porque tiene productos asociados")
            
            cur.execute("DELETE FROM categorias WHERE id = ?", (categoria_id,))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def buscar_por_id(categoria_id: int) -> Optional[Dict[str, Any]]:
        """Buscar categoría por ID específico"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nombre, descripcion FROM categorias WHERE id = ?", (categoria_id,))
            return _dict_one(cur)
        finally:
            conn.close()

class ProductoRepo:
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.codigo_barras, p.nombre, p.precio, p.stock, 
                       ISNULL(c.nombre,'') AS categoria, p.activo, p.categoria_id
                FROM productos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                ORDER BY p.nombre
            """)
            return _dict_rows(cur)
        finally:
            conn.close()

    @staticmethod
    def listar_para_reporte() -> List[Dict[str, Any]]:
        """
        Lista productos con una columna 'estado_stock' calculada en la BD.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    p.id, p.codigo_barras, p.nombre, p.precio, p.stock, 
                    ISNULL(c.nombre,'') AS categoria, p.activo,
                    -- Lógica de estado movida a SQL con CASE --
                    CASE
                        WHEN p.stock = 0 THEN '❌ Agotado'
                        WHEN p.stock < 5 THEN '⚠️ Bajo'
                        WHEN p.stock > 100 THEN '📦 Excesivo'
                        ELSE '✅ Óptimo'
                    END AS estado_stock
                FROM productos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                ORDER BY p.nombre
            """)
            return _dict_rows(cur)
        finally:
            conn.close()

    @staticmethod
    def buscar(codigo_o_nombre: str) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, codigo_barras, nombre, precio, stock, activo
                FROM productos
                WHERE codigo_barras = ? OR nombre LIKE ?
            """, (codigo_o_nombre, f"%{codigo_o_nombre}%"))
            return _dict_one(cur)
        finally:
            conn.close()

    @staticmethod
    def buscar_por_id(producto_id: int) -> Optional[Dict[str, Any]]:
        """Buscar producto por ID específico"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT p.id, p.codigo_barras, p.nombre, p.precio, p.stock, 
                       p.stock_minimo, p.proveedor, p.activo, p.categoria_id,
                       ISNULL(c.nombre, '') AS categoria
                FROM productos p
                LEFT JOIN categorias c ON p.categoria_id = c.id
                WHERE p.id = ?
            """, (producto_id,))
            return _dict_one(cur)
        except Exception as e:
            print(f"Error buscando producto por ID: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def agregar(nombre, precio, stock, categoria_id=None, codigo=None):
        if not codigo: 
            codigo = f"AUTO-{int(time.time())}"

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO productos (codigo_barras, nombre, precio, stock, categoria_id)
                VALUES (?, ?, ?, ?, ?)
            """, (codigo, nombre, precio, stock, categoria_id))
            conn.commit()

    @staticmethod
    def actualizar_precio(producto_id: int, nuevo_precio: float):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("UPDATE productos SET precio = ?, fecha_modificacion = GETDATE() WHERE id = ?", (nuevo_precio, producto_id))
            conn.commit()
        finally:
            conn.close()
            
    @staticmethod
    def actualizar_completo(producto_id: int, nombre: str, precio: float, codigo_barras: str = None,
                          categoria_id: int = None, stock: int = None, stock_minimo: int = None,
                          proveedor: str = None, activo: bool = True):
        """Actualizar todos los campos de un producto"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            campos = []
            valores = []
            
            if nombre is not None:
                campos.append("nombre = ?")
                valores.append(nombre)
            if precio is not None:
                campos.append("precio = ?")
                valores.append(precio)
            if codigo_barras is not None:
                campos.append("codigo_barras = ?")
                valores.append(codigo_barras)
            if categoria_id is not None:
                campos.append("categoria_id = ?")
                valores.append(categoria_id)
            if stock is not None:
                campos.append("stock = ?")
                valores.append(stock)
            if stock_minimo is not None:
                campos.append("stock_minimo = ?")
                valores.append(stock_minimo)
            if proveedor is not None:
                campos.append("proveedor = ?")
                valores.append(proveedor)
            if activo is not None:
                campos.append("activo = ?")
                valores.append(activo)
            
            campos.append("fecha_modificacion = GETDATE()")
            
            valores.append(producto_id)
            
            if campos:
                query = f"UPDATE productos SET {', '.join(campos)} WHERE id = ?"
                cur.execute(query, valores)
                conn.commit()
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def actualizar_stock(producto_id: int, nuevo_stock: int):
        """Actualizar solo el stock de un producto"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE productos 
                SET stock = ?, fecha_modificacion = GETDATE() 
                WHERE id = ?
            """, (nuevo_stock, producto_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# ----------------- Puntos de Venta -----------------
class PuntoVentaRepo:
    @staticmethod
    def listar() -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, nombre, direccion, telefono FROM puntos_venta ORDER BY nombre")
            return _dict_rows(cur)
        finally:
            conn.close()

    @staticmethod
    def agregar(nombre: str, direccion: str, telefono: str):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("INSERT INTO puntos_venta (nombre, direccion, telefono) VALUES (?, ?, ?)", (nombre, direccion, telefono))
            conn.commit()
        finally:
            conn.close()

# ----------------- Ventas -----------------
class VentaRepo:
    @staticmethod
    def crear_venta(punto_venta_id: int, items: List[Dict[str, Any]], forma_pago="EFECTIVO", descuento=0.0, **kwargs) -> int:
        """
        Crea una venta con sus detalles, descuenta stock e inserta movimientos_stock.
        """
        conn = get_connection()
        try:
            conn.autocommit = False
            cur = conn.cursor()

            subtotal = sum(it['cantidad'] * it['precio'] for it in items)
            total = round(subtotal * (1 - descuento/100.0), 2)

            # --- CORRECCIÓN ERROR 42S22 ---
            # Asumimos que tu tabla SI tiene 'descuento' pero NO tiene 'punto_venta_id'
            # Si 'descuento' tampoco existe, quítalo de aquí.
            cur.execute("""
                INSERT INTO ventas (fecha, total, descuento, forma_pago)
                OUTPUT INSERTED.id
                VALUES (GETDATE(), ?, ?, ?)
            """, (total, descuento, forma_pago))
            venta_id = cur.fetchone()[0]

            for it in items:
                
                # Volvemos a la versión simple del INSERT para detalle_venta
                # Asumimos que tu tabla 'detalle_venta' solo tiene estas 4 columnas:
                cur.execute("""
                    INSERT INTO detalle_venta (venta_id, producto_id, cantidad, precio_unitario)
                    VALUES (?, ?, ?, ?)
                """, (venta_id, it['producto_id'], it['cantidad'], it['precio']))

           
                cur.execute("UPDATE productos SET stock = stock - ? WHERE id = ?", (it['cantidad'], it['producto_id']))

             
                cur.execute("""
                    INSERT INTO movimientos_stock (producto_id, tipo, cantidad, stock_anterior, stock_nuevo)
                    VALUES (?, 'VENTA', ?, 
                        (SELECT stock + ? FROM productos WHERE id=?),
                        (SELECT stock FROM productos WHERE id=?))
                """, (it['producto_id'], it['cantidad'], it['cantidad'], it['producto_id'], it['producto_id']))

            conn.commit()
            return venta_id
        except Exception as e:
            conn.rollback()
            print(f"ERROR DETALLADO EN crear_venta: {e}") 
            raise
        finally:
            conn.close()

    @staticmethod
    def listar(limit=50) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT TOP (?) id, fecha, total, forma_pago FROM ventas ORDER BY fecha DESC", (limit,))
            return _dict_rows(cur)
        finally:
            conn.close()

    @staticmethod
    def listar_completo(limit=100) -> List[Dict[str, Any]]:
        """
        Devuelve todas las ventas con su detalle de productos (items).
        """
        conn = get_connection()
        try:
            cur = conn.cursor()

            cur.execute("""
                SELECT TOP (?) id, fecha, total, forma_pago
                FROM ventas
                ORDER BY fecha DESC
            """, (limit,))
            ventas = _dict_rows(cur)

            if not ventas:
                return []

            venta_ids = tuple(v["id"] for v in ventas)

            if len(venta_ids) == 1:
                params = (venta_ids[0],)
                where_in = "(?)"
            else:
                params = venta_ids
                where_in = "(" + ",".join("?" * len(venta_ids)) + ")"

            cur.execute(f"""
                SELECT 
                    dv.venta_id,
                    p.nombre AS producto,
                    dv.cantidad,
                    dv.precio_unitario
                FROM detalle_venta dv
                INNER JOIN productos p ON p.id = dv.producto_id
                WHERE dv.venta_id IN {where_in}
                ORDER BY dv.venta_id DESC
            """, params)

            detalles = _dict_rows(cur)

            for venta in ventas:
                venta["items"] = [
                    {
                        "producto": d["producto"],
                        "cantidad": d["cantidad"],
                        "precio_unitario": float(d["precio_unitario"])
                    }
                    for d in detalles if d["venta_id"] == venta["id"]
                ]

            return ventas

        finally:
            conn.close()

    @staticmethod
    def buscar_por_id(venta_id: int) -> Optional[Dict[str, Any]]:
        """Buscar venta por ID con todos sus detalles"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            
            # --- CORRECCIÓN ERROR 42S22 ---
            # Quitamos 'punto_venta_id' del SELECT
            cur.execute("""
                SELECT id, fecha, total, forma_pago, descuento
                FROM ventas 
                WHERE id = ?
            """, (venta_id,))
            
            venta = _dict_one(cur)
            if not venta:
                return None
            
            cur.execute("""
                SELECT 
                    p.nombre AS producto,
                    dv.cantidad,
                    dv.precio_unitario,
                    (dv.cantidad * dv.precio_unitario) AS subtotal
                FROM detalle_venta dv
                INNER JOIN productos p ON p.id = dv.producto_id
                WHERE dv.venta_id = ?
            """, (venta_id,))
            
            items = _dict_rows(cur)
            venta["items"] = items
            
            return venta
            
        finally:
            conn.close()

    @staticmethod
    def obtener_items_venta(venta_id: int) -> List[Dict[str, Any]]:
        """Obtener solo los items de una venta específica"""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    p.nombre AS producto,
                    dv.cantidad,
                    dv.precio_unitario,
                    (dv.cantidad * dv.precio_unitario) AS subtotal
                FROM detalle_venta dv
                INNER JOIN productos p ON p.id = dv.producto_id
                WHERE dv.venta_id = ?
            """, (venta_id,))
            
            return _dict_rows(cur)
            
        finally:
            conn.close()

    @staticmethod
    def obtener_ventas_por_fecha(fecha_inicio: str, fecha_fin: str) -> List[Dict[str, Any]]:
        """
        Obtener ventas entre dos fechas
        Formato fecha: 'YYYY-MM-DD'
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, fecha, total, forma_pago
                FROM ventas
                WHERE CAST(fecha AS DATE) BETWEEN ? AND ?
                ORDER BY fecha DESC
            """, (fecha_inicio, fecha_fin))
            
            return _dict_rows(cur)
            
        finally:
            conn.close()

    @staticmethod
    def obtener_total_ventas_por_dia(fecha: str) -> float:
        """
        Obtener el total de ventas para un día específico
        Formato fecha: 'YYYY-MM-DD'
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT ISNULL(SUM(total), 0) as total_dia
                FROM ventas
                WHERE CAST(fecha AS DATE) = ?
            """, (fecha,))
            
            result = cur.fetchone()
            return float(result[0]) if result else 0.0
            
        finally:
            conn.close()

    @staticmethod
    def obtener_resumen_ventas_diarias(dias: int = 7) -> List[Dict[str, Any]]:
        """
        Obtiene la suma total de ventas por día para los últimos 'dias' días.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    CAST(fecha AS DATE) as dia_venta,
                    SUM(total) as total_dia
                FROM ventas
                WHERE fecha >= DATEADD(day, -?, GETDATE())
                GROUP BY CAST(fecha AS DATE)
                ORDER BY dia_venta ASC
            """, (dias,))
            
            datos_raw = _dict_rows(cur)
            
            datos_formateados = []
            for fila in datos_raw:
                datos_formateados.append({
                    "fecha": fila["dia_venta"].strftime("%Y-%m-%d"),
                    "total": float(fila["total_dia"])
                })
            
            return datos_formateados
            
        except Exception as e:
            print(f"Error obteniendo resumen de ventas: {e}")
            return []
        finally:
            conn.close()