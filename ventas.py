"""ventas.py - Seccion VENTAS (diapositiva 9).

Izquierda: formulario "Agregar venta" (solo administrador y personal).
Derecha  : tabla de ventas (no. venta, cliente, fecha, total, estado).
El cliente solo ve la tabla, con sus propias compras.

Uso desde secciones.py:
    from ventas import crear_ventas
    "VENTAS": (crear_ventas, ("admin", "vendedor", "cliente")),

Prueba suelta:  python ventas.py
Reglas de calculo y validacion: ventas_logica.py (se prueba sin base de datos).

Tablas y columnas que asume este modulo (ajusta el bloque SQL_* si difieren):
    clientes(id_cliente, id_usuario)         usuarios(id_usuario, nombre)
    plantas(id_planta, nombre_comun, tamano_cm, precio, cantidad)
    ventas(id_venta, id_cliente, cliente_nombre, id_empleado, fecha,
           monto_total, estado, metodo_pago)      <- ver 04_ventas_capacitaciones.sql
    detalle_venta(id_venta, id_planta, cantidad, precio_unitario)
"""
import tkinter as tk
from datetime import date
from tkinter import messagebox

import db
from sanidad import (CLARO, FONDO, FUENTE, TERRACOTA, TEXTO, VERDE, BotonPildora,
                     FrameDesplazable, _consulta, _rect)
from ventas_logica import (ESTADO_VISIBLE, METODOS_PAGO, calcular_total, fecha_corta,
                           fecha_larga, formato_dinero, parsear_cantidad,
                           parsear_fecha)

# --------------------------------------------------------------------------
# Colores de la diapositiva 9
# --------------------------------------------------------------------------
CAFE = "#4E3B31"
CELDA = "#D2A090"
OLIVA = "#9AAE2B"

# --------------------------------------------------------------------------
# SQL (unico lugar que menciona columnas)
# --------------------------------------------------------------------------
SQL_CLIENTES = """
    SELECT c.id_cliente, u.nombre
    FROM clientes c JOIN usuarios u ON u.id_usuario = c.id_usuario
"""
SQL_PLANTAS = """
    SELECT id_planta, nombre_comun, tamano_cm, precio, cantidad
    FROM plantas WHERE cantidad > 0
    ORDER BY nombre_comun, tamano_cm
"""
SQL_VENTAS = """
    SELECT v.id_venta, COALESCE(u.nombre, v.cliente_nombre, '') AS cliente,
           v.fecha, v.monto_total, v.estado
    FROM ventas v
    LEFT JOIN clientes c ON c.id_cliente = v.id_cliente
    LEFT JOIN usuarios u ON u.id_usuario = c.id_usuario
    {filtro}
    ORDER BY v.fecha DESC, v.id_venta DESC
    LIMIT 200
"""


class SinExistencias(Exception):
    """La planta ya no tiene suficientes existencias."""


def _dato(fila, nombre, pos=0):
    """Lee una columna de una fila que puede ser dict o tupla."""
    return fila[nombre] if isinstance(fila, dict) else fila[pos]


def _usuario(usuario, clave):
    if isinstance(usuario, dict):
        return usuario.get(clave)
    return getattr(usuario, clave, None)


# --------------------------------------------------------------------------
# Operaciones con la base (cada una en su propia transaccion)
# --------------------------------------------------------------------------
def registrar_venta(id_cliente, nombre_libre, id_empleado, fecha, metodo, id_planta, cantidad):
    """Descuenta existencias y crea venta + detalle en una sola transaccion.

    Devuelve (id_venta, total). El precio se toma de la base, no del formulario.
    """
    conn = db.conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE plantas SET cantidad = cantidad - %s "
                "WHERE id_planta = %s AND cantidad >= %s RETURNING precio AS precio",
                (cantidad, id_planta, cantidad))
            fila = cur.fetchone()
            if not fila:
                raise SinExistencias()
            precio = _dato(fila, "precio")
            total = calcular_total(cantidad, precio)
            cur.execute(
                "INSERT INTO ventas (id_cliente, cliente_nombre, id_empleado, fecha, "
                "monto_total, estado, metodo_pago) VALUES (%s, %s, %s, %s, %s, 'pagada', %s) "
                "RETURNING id_venta AS id_venta",
                (id_cliente, None if id_cliente else nombre_libre, id_empleado, fecha,
                 total, metodo))
            id_venta = _dato(cur.fetchone(), "id_venta")
            cur.execute(
                "INSERT INTO detalle_venta (id_venta, id_planta, cantidad, precio_unitario) "
                "VALUES (%s, %s, %s, %s)", (id_venta, id_planta, cantidad, precio))
        conn.commit()
        return id_venta, total
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cobrar_venta(id_venta):
    """pendiente -> pagada. Devuelve True si cambio algo."""
    filas = _consulta("UPDATE ventas SET estado = 'pagada' "
                      "WHERE id_venta = %s AND estado = 'pendiente' "
                      "RETURNING id_venta AS id_venta", (id_venta,))
    return bool(filas)


def cancelar_venta(id_venta):
    """Marca la venta como cancelada y devuelve las existencias (una sola transaccion)."""
    conn = db.conectar()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE ventas SET estado = 'cancelada' "
                        "WHERE id_venta = %s AND estado <> 'cancelada' "
                        "RETURNING id_venta AS id_venta", (id_venta,))
            if not cur.fetchone():
                conn.rollback()
                return False
            cur.execute("UPDATE plantas p SET cantidad = p.cantidad + d.cantidad "
                        "FROM detalle_venta d "
                        "WHERE d.id_venta = %s AND p.id_planta = d.id_planta", (id_venta,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------
class Celda(tk.Canvas):
    """Celda redondeada de la tabla; si recibe comando, es clicable."""

    def __init__(self, master, ancho, alto, texto, color, fg="black", negrita=False,
                 comando=None):
        super().__init__(master, width=ancho, height=alto, bg=FONDO, highlightthickness=0,
                         cursor="hand2" if comando else "")
        _rect(self, 0, 0, ancho, alto, 10, color)
        self.create_text(ancho // 2, alto // 2, text=texto, fill=fg, width=ancho - 8,
                         font=(FUENTE, 9, "bold" if negrita else "normal"), justify="center")
        if comando:
            self.bind("<Button-1>", comando)


class CampoPildora(tk.Canvas):
    """Pildora terracota con un Entry (texto libre) o un valor de solo lectura."""

    def __init__(self, master, ancho, solo_lectura=False):
        super().__init__(master, width=ancho, height=32, bg=FONDO, highlightthickness=0)
        _rect(self, 0, 0, ancho, 32, 16, TERRACOTA)
        self.var = tk.StringVar()
        self.entrada = tk.Entry(self, textvariable=self.var, bd=0, relief="flat",
                                bg=TERRACOTA, fg="white", insertbackground="white",
                                disabledbackground=TERRACOTA, disabledforeground="white",
                                readonlybackground=TERRACOTA, font=(FUENTE, 10),
                                highlightthickness=0,
                                state="readonly" if solo_lectura else "normal")
        self.create_window(ancho // 2, 16, window=self.entrada, width=ancho - 28, height=22)

    def get(self):
        return self.var.get()

    def set(self, valor):
        self.var.set("" if valor is None else str(valor))


class SelectorPildora(tk.Canvas):
    """Pildora que abre una lista con buscador (para elegir una planta o un metodo)."""

    def __init__(self, master, ancho, texto_vacio, abrir):
        super().__init__(master, width=ancho, height=32, bg=FONDO, highlightthickness=0,
                         cursor="hand2")
        self.texto_vacio = texto_vacio
        _rect(self, 0, 0, ancho, 32, 16, TERRACOTA)
        self._texto = self.create_text(14, 16, text=texto_vacio, fill=CLARO, anchor="w",
                                       font=(FUENTE, 10), width=ancho - 40)
        self.create_text(ancho - 14, 16, text="▾", fill="white", font=(FUENTE, 10))
        self.bind("<Button-1>", lambda e: abrir())

    def mostrar(self, texto):
        self.itemconfigure(self._texto, text=texto or self.texto_vacio,
                           fill="white" if texto else CLARO)


class DialogoLista(tk.Toplevel):
    """Ventana modal con buscador y lista. Deja el elegido en .resultado (indice)."""

    def __init__(self, master, titulo, opciones, con_buscador=True):
        super().__init__(master)
        self.title(titulo)
        self.configure(bg=FONDO)
        self.resizable(False, False)
        self.transient(master.winfo_toplevel())
        self.opciones = list(opciones)
        self.visibles = list(range(len(self.opciones)))
        self.resultado = None

        if con_buscador:
            self.busca = tk.StringVar()
            self.busca.trace_add("write", lambda *a: self._filtrar())
            e = tk.Entry(self, textvariable=self.busca, font=(FUENTE, 10), relief="flat",
                         highlightthickness=1, highlightbackground=TERRACOTA)
            e.pack(fill="x", padx=12, pady=(12, 6))
            e.focus_set()
        self.lista = tk.Listbox(self, width=48, height=min(12, max(4, len(self.opciones))),
                                font=(FUENTE, 10), activestyle="none", bd=0,
                                highlightthickness=1, highlightbackground=TERRACOTA,
                                selectbackground=VERDE, selectforeground="white")
        self.lista.pack(padx=12, pady=(0, 6))
        self.lista.bind("<Double-Button-1>", lambda e: self._elegir())
        self.lista.bind("<Return>", lambda e: self._elegir())
        self.bind("<Escape>", lambda e: self.destroy())
        BotonPildora(self, 120, 32, "Elegir", self._elegir, color=TERRACOTA).pack(pady=(0, 12))
        self._filtrar()
        self.update_idletasks()
        x = master.winfo_rootx() + 60
        y = master.winfo_rooty() + 60
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.wait_window()

    def _filtrar(self):
        txt = self.busca.get().strip().lower() if hasattr(self, "busca") else ""
        self.visibles = [i for i, o in enumerate(self.opciones) if txt in o.lower()]
        self.lista.delete(0, "end")
        for i in self.visibles:
            self.lista.insert("end", self.opciones[i])
        if self.visibles:
            self.lista.selection_set(0)

    def _elegir(self):
        sel = self.lista.curselection()
        if not sel:
            return
        self.resultado = self.visibles[sel[0]]
        self.destroy()


# --------------------------------------------------------------------------
# Pantalla
# --------------------------------------------------------------------------
class PantallaVentas(tk.Frame):
    ANCHOS = (62, 98, 82, 64, 96)          # no. venta, cliente, fecha, total, estado
    TITULOS = ("no. venta", "cliente", "fecha", "total", "estado")

    def __init__(self, master, usuario=None):
        super().__init__(master, bg=FONDO)
        self.usuario = usuario
        self.rol = _usuario(usuario, "rol")
        self.planta = None                 # dict de la planta elegida
        self.metodo = None
        if self.rol not in ("admin", "vendedor", "cliente"):
            tk.Label(self, text="No tienes acceso a esta sección.", bg=FONDO, fg=TEXTO,
                     font=(FUENTE, 14)).pack(expand=True)
            return
        self.es_personal = self.rol in ("admin", "vendedor")
        self._construir()
        self.pintar_tabla()

    # ---- construccion ---------------------------------------------------
    def _construir(self):
        if self.es_personal:
            self.columnconfigure(0, weight=5, uniform="c")
            self.columnconfigure(1, weight=6, uniform="c")
            self._formulario().grid(row=0, column=0, sticky="n", padx=(24, 8), pady=14)
            col_tabla = 1
        else:
            self.columnconfigure(0, weight=1)
            col_tabla = 0
        self.rowconfigure(0, weight=1)

        derecha = tk.Frame(self, bg=FONDO)
        derecha.grid(row=0, column=col_tabla, sticky="nsew", padx=(8, 24), pady=14)
        titulo = "VENTAS" if self.es_personal else "MIS COMPRAS"
        if not self.es_personal:
            tk.Label(derecha, text=titulo, bg=FONDO, fg=TERRACOTA,
                     font=(FUENTE, 22, "bold")).pack(anchor="w", pady=(0, 8))
        cab = tk.Frame(derecha, bg=FONDO)
        cab.pack(anchor="w", pady=(32 if self.es_personal else 0, 4))
        for ancho, texto in zip(self.ANCHOS, self.TITULOS):
            Celda(cab, ancho, 40, texto, TERRACOTA, fg="black", negrita=True).pack(
                side="left", padx=3)
        self.tabla = FrameDesplazable(derecha, FONDO)
        self.tabla.pack(fill="both", expand=True)
        self.pie = tk.Label(derecha, text="", bg=FONDO, fg=TEXTO, font=(FUENTE, 9))
        self.pie.pack(anchor="w", pady=(4, 0))

    def _formulario(self):
        f = tk.Frame(self, bg=FONDO)
        tk.Label(f, text="VENTAS", bg=FONDO, fg=TERRACOTA,
                 font=(FUENTE, 22, "bold")).pack(pady=(0, 10))

        def etiqueta(parent, texto):
            return tk.Label(parent, text=texto, bg=FONDO, fg=TERRACOTA, font=(FUENTE, 11))

        etiqueta(f, "NOMBRE CLIENTE").pack()
        self.cliente = CampoPildora(f, 250)
        self.cliente.pack(pady=(2, 8))

        etiqueta(f, "Nombre de la planta").pack()
        self.sel_planta = SelectorPildora(f, 250, "Elegir planta…", self._elegir_planta)
        self.sel_planta.pack(pady=(2, 8))

        fila1 = tk.Frame(f, bg=FONDO)
        fila1.pack(pady=(0, 8))
        a = tk.Frame(fila1, bg=FONDO)
        a.pack(side="left", padx=8)
        etiqueta(a, "Cantidad").pack()
        self.cantidad = CampoPildora(a, 112)
        self.cantidad.pack(pady=2)
        self.cantidad.entrada.bind("<KeyRelease>", lambda e: self._actualizar_total())
        b = tk.Frame(fila1, bg=FONDO)
        b.pack(side="left", padx=8)
        etiqueta(b, "Precio unitario").pack()
        self.precio = CampoPildora(b, 112, solo_lectura=True)
        self.precio.pack(pady=2)

        fila2 = tk.Frame(f, bg=FONDO)
        fila2.pack(pady=(0, 6))
        c = tk.Frame(fila2, bg=FONDO)
        c.pack(side="left", padx=8)
        etiqueta(c, "fecha").pack()
        self.fecha = CampoPildora(c, 112)
        self.fecha.pack(pady=2)
        self.fecha.set(fecha_larga(date.today()))
        d = tk.Frame(fila2, bg=FONDO)
        d.pack(side="left", padx=8)
        etiqueta(d, "metodo de pago").pack()
        self.sel_metodo = SelectorPildora(d, 112, "Elegir…", self._elegir_metodo)
        self.sel_metodo.pack(pady=2)

        self.total = tk.Label(f, text="Total: —", bg=FONDO, fg=TEXTO, font=(FUENTE, 11, "bold"))
        self.total.pack(pady=(4, 6))
        BotonPildora(f, 200, 36, "Agregar venta", self._guardar, color=OLIVA, fg=TERRACOTA,
                     fuente=(FUENTE, 10, "bold")).pack(pady=(0, 4))
        return f

    # ---- selectores -------------------------------------------------------
    def _elegir_planta(self):
        try:
            filas = _consulta(SQL_PLANTAS) or []
        except Exception as e:
            self._error_bd(e)
            return
        if not filas:
            messagebox.showinfo("Sin existencias", "No hay plantas con existencias para vender.",
                                parent=self)
            return
        textos = [f"{f['nombre_comun']} ({f['tamano_cm']} cm) · {formato_dinero(f['precio'])} "
                  f"· {f['cantidad']} disp." for f in filas]
        dlg = DialogoLista(self, "Elegir planta", textos)
        if dlg.resultado is None:
            return
        f = filas[dlg.resultado]
        self.planta = {"id": f["id_planta"], "nombre": f["nombre_comun"],
                       "tamano": f["tamano_cm"], "precio": f["precio"],
                       "disponible": int(f["cantidad"])}
        self.sel_planta.mostrar(f"{f['nombre_comun']} ({f['tamano_cm']} cm)")
        self.precio.set(formato_dinero(f["precio"]))
        self._actualizar_total()

    def _elegir_metodo(self):
        dlg = DialogoLista(self, "Método de pago", METODOS_PAGO, con_buscador=False)
        if dlg.resultado is None:
            return
        self.metodo = METODOS_PAGO[dlg.resultado]
        self.sel_metodo.mostrar(self.metodo)

    def _actualizar_total(self):
        n, _ = parsear_cantidad(self.cantidad.get())
        if self.planta and n:
            self.total.config(text=f"Total: {formato_dinero(calcular_total(n, self.planta['precio']))}")
        else:
            self.total.config(text="Total: —")

    # ---- guardar ------------------------------------------------------------
    def _error_bd(self, error):
        messagebox.showerror("Error de base de datos",
                             f"No se pudo completar la operación.\n\n{error}", parent=self)

    def _guardar(self):
        nombre = " ".join(self.cliente.get().split())
        if not nombre:
            return self._aviso("Escribe el nombre del cliente.")
        if len(nombre) < 2 or len(nombre) > 100:
            return self._aviso("El nombre del cliente debe tener entre 2 y 100 caracteres.")
        if not self.planta:
            return self._aviso("Elige la planta que se vendió.")
        cantidad, error = parsear_cantidad(self.cantidad.get(), self.planta["disponible"])
        if error:
            return self._aviso(error)
        fecha, error = parsear_fecha(self.fecha.get())
        if error:
            return self._aviso(error)
        if not self.metodo:
            return self._aviso("Elige el método de pago.")
        id_empleado = _usuario(self.usuario, "id_empleado")
        if not id_empleado:
            return self._aviso("Tu usuario no está registrado como empleado, así que no puede "
                               "registrar ventas. Pide al administrador que lo dé de alta en PERSONAL.")
        try:
            clientes = _consulta(SQL_CLIENTES + " WHERE lower(u.nombre) = lower(%s)", (nombre,)) or []
            id_cliente = clientes[0]["id_cliente"] if len(clientes) == 1 else None
            id_venta, total = registrar_venta(id_cliente, nombre, id_empleado, fecha,
                                              self.metodo, self.planta["id"], cantidad)
        except SinExistencias:
            messagebox.showwarning("Sin existencias",
                                   "Esa planta ya no tiene suficientes existencias. "
                                   "Elígela de nuevo para ver las actuales.", parent=self)
            self.planta = None
            self.sel_planta.mostrar("")
            self.precio.set("")
            return
        except Exception as e:
            self._error_bd(e)
            return
        messagebox.showinfo("Venta registrada",
                            f"Venta {id_venta:03d} registrada por {formato_dinero(total)}.",
                            parent=self)
        self.cliente.set("")
        self.cantidad.set("")
        self.precio.set("")
        self.planta = None
        self.sel_planta.mostrar("")
        self.fecha.set(fecha_larga(date.today()))
        self.metodo = None
        self.sel_metodo.mostrar("")
        self.total.config(text="Total: —")
        self.pintar_tabla()

    def _aviso(self, texto):
        messagebox.showwarning("Revisa el formulario", texto, parent=self)

    # ---- tabla ------------------------------------------------------------------
    def pintar_tabla(self):
        for w in self.tabla.interior.winfo_children():
            w.destroy()
        filtro, params = "", ()
        if not self.es_personal:
            filtro, params = "WHERE v.id_cliente = %s", (_usuario(self.usuario, "id_cliente"),)
            if params[0] is None:
                self._vacia("Tu cuenta no tiene un perfil de cliente.")
                return
        try:
            filas = _consulta(SQL_VENTAS.format(filtro=filtro), params) or []
        except Exception as e:
            self._error_bd(e)
            return
        if not filas:
            self._vacia("Aún no hay ventas registradas.")
            return
        for fila in filas:
            linea = tk.Frame(self.tabla.interior, bg=FONDO)
            linea.pack(anchor="w", pady=3)
            estado = fila["estado"]
            textos = (f"{fila['id_venta']:03d}", fila["cliente"], fecha_corta(fila["fecha"]),
                      formato_dinero(fila["monto_total"]),
                      ESTADO_VISIBLE.get(estado, str(estado)))
            for i, (ancho, texto) in enumerate(zip(self.ANCHOS, textos)):
                cmd = None
                if i == 4 and self.es_personal and estado != "cancelada":
                    cmd = lambda e, v=fila["id_venta"], s=estado: self._menu_estado(e, v, s)
                Celda(linea, ancho, 44, texto, CAFE if i == 0 else CELDA,
                      fg="white" if i == 0 else "black", comando=cmd).pack(side="left", padx=3)
        self.tabla.vincular_hijos()
        extra = "  ·  Haz clic en el estado para cobrar o cancelar." if self.es_personal else ""
        self.pie.config(text=f"{len(filas)} venta(s) mostradas (las 200 más recientes){extra}")

    def _vacia(self, texto):
        tk.Label(self.tabla.interior, text=texto, bg=FONDO, fg=TEXTO,
                 font=(FUENTE, 11)).pack(pady=30)
        self.pie.config(text="")

    def _menu_estado(self, evento, id_venta, estado):
        menu = tk.Menu(self, tearoff=0)
        if estado == "pendiente":
            menu.add_command(label="Marcar como completada (cobrar)",
                             command=lambda: self._cobrar(id_venta))
        menu.add_command(label="Cancelar venta", command=lambda: self._cancelar(id_venta))
        menu.tk_popup(evento.x_root, evento.y_root)

    def _cobrar(self, id_venta):
        try:
            cobrar_venta(id_venta)
        except Exception as e:
            self._error_bd(e)
            return
        self.pintar_tabla()

    def _cancelar(self, id_venta):
        if not messagebox.askyesno(
                "Cancelar venta",
                f"¿Cancelar la venta {id_venta:03d}?\nLas plantas vuelven al inventario.",
                parent=self):
            return
        try:
            cancelar_venta(id_venta)
        except Exception as e:
            self._error_bd(e)
            return
        self.pintar_tabla()


def crear_ventas(parent, usuario=None):
    pantalla = PantallaVentas(parent, usuario)
    pantalla.pack(fill="both", expand=True)
    return pantalla


if __name__ == "__main__":
    raiz = tk.Tk()
    raiz.title("Vivero - Ventas")
    raiz.geometry("1000x620")
    # Para probar: administrador con id_empleado = 1 (cambia el numero si hace falta)
    crear_ventas(raiz, {"rol": "admin", "id_empleado": 1})
    raiz.mainloop()