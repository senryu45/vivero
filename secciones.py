"""Secciones del menú conectadas a viveros_db."""
import tkinter as tk
from tkinter import ttk, messagebox

import db
from alta_personal import AltaPersonal
from catalogo import Catalogo as Plantas              # PLANTAS: diap. 4, 5 y 6
from catalogo_secciones import CatalogoSecciones      # CATALOGO: diap. 7 y 8

VERDE_OSCURO = "#3F5A1A"
FONDO_SECCION = "#C5C7B5"
CAFE = "#99553A"
FUENTE = "Open Sans"

STAFF = ("admin", "vendedor")
TODOS = ("admin", "vendedor", "cliente")


class Tabla(tk.Frame):
    """Título + tabla (Treeview) llena con el resultado de una consulta."""

    def __init__(self, master, titulo, columnas, sql, params=None):
        # columnas: [(encabezado, clave_en_la_consulta, ancho_px), ...]
        super().__init__(master, bg=FONDO_SECCION)
        self.columnas, self.sql, self.params = columnas, sql, params

        tk.Label(self, text=titulo, bg=FONDO_SECCION, fg=CAFE,
                 font=(FUENTE, 20, "bold")).pack(anchor="w", padx=24, pady=(16, 8))

        marco = tk.Frame(self, bg=FONDO_SECCION)
        marco.pack(fill="both", expand=True, padx=24)
        self.tree = ttk.Treeview(marco, show="headings",
                                 columns=[c[1] for c in columnas])
        for encabezado, clave, ancho in columnas:
            self.tree.heading(clave, text=encabezado)
            self.tree.column(clave, width=ancho, anchor="w")
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        tk.Button(self, text="Actualizar", command=self.cargar, bg=VERDE_OSCURO,
                  fg="white", relief="flat", padx=14, pady=4,
                  font=(FUENTE, 10)).pack(anchor="e", padx=24, pady=10)
        self.cargar()

    def cargar(self):
        try:
            filas = db.consultar(self.sql, self.params)
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))
            return
        self.tree.delete(*self.tree.get_children())
        for f in filas:
            self.tree.insert("", "end", values=[
                "" if f[clave] is None else f[clave] for _, clave, _ in self.columnas])


# ------------------------------ Definición de secciones ------------------------------
def _plantas(master, datos):
    return Plantas(master, datos)


def _catalogo(master, datos):
    return CatalogoSecciones(master, datos)


def _ventas(master, datos):
    columnas = [("Folio", "id_venta", 60), ("Fecha", "fecha", 150),
                ("Cliente", "cliente", 200), ("Vendedor", "vendedor", 200),
                ("Total", "monto_total", 100), ("Estado", "estado", 90)]
    sql = """SELECT v.id_venta, to_char(v.fecha_venta, 'YYYY-MM-DD HH24:MI') AS fecha,
                    uc.nombre_completo AS cliente, ue.nombre_completo AS vendedor,
                    v.monto_total, v.estado
             FROM ventas v
             JOIN clientes  c  ON c.id_cliente  = v.id_cliente
             JOIN usuarios  uc ON uc.id_usuario = c.id_usuario
             JOIN empleados e  ON e.id_empleado = v.id_empleado
             JOIN usuarios  ue ON ue.id_usuario = e.id_usuario"""
    if datos and datos["rol"] == "cliente":       # el cliente solo ve sus compras
        return Tabla(master, "Mis compras", columnas,
                     sql + " WHERE v.id_cliente = %s ORDER BY v.fecha_venta DESC",
                     (datos["id_cliente"],))
    return Tabla(master, "Ventas", columnas, sql + " ORDER BY v.fecha_venta DESC")


def _capacitaciones(master, datos):
    return Tabla(master, "Capacitaciones", [
        ("ID", "id_capacitacion", 50), ("Tema", "tema", 300),
        ("Subtemas", "subtemas", 90), ("Empleados", "empleados", 90)],
        """SELECT c.id_capacitacion, c.tema,
                  (SELECT count(*) FROM subtemas_capacitacion s
                    WHERE s.id_capacitacion = c.id_capacitacion) AS subtemas,
                  (SELECT count(*) FROM capacitacion_empleado ce
                    WHERE ce.id_capacitacion = c.id_capacitacion) AS empleados
           FROM capacitaciones c ORDER BY c.tema""")


def _plagas(master, datos):
    return Tabla(master, "Plagas", [
        ("ID", "id_plaga", 50), ("Nombre", "nombre", 200),
        ("Riesgo", "nivel_riesgo", 80), ("Tratamiento", "tratamiento", 480)],
        "SELECT id_plaga, nombre, nivel_riesgo, tratamiento FROM plagas ORDER BY nombre")


def _enfermedades(master, datos):
    return Tabla(master, "Enfermedades", [
        ("ID", "id_enfermedad", 50), ("Nombre", "nombre", 200),
        ("Agente causal", "agente_causal", 200), ("Tratamiento", "tratamiento", 360)],
        """SELECT id_enfermedad, nombre, agente_causal, tratamiento
           FROM enfermedades ORDER BY nombre""")


def _personal(master, datos):
    return AltaPersonal(master, datos)


# nombre en el menú -> (función que crea la sección, roles con acceso)
SECCIONES = {
    "PLANTAS":        (_plantas,        STAFF),
    "CATALOGO":       (_catalogo,       TODOS),
    "VENTAS":         (_ventas,         TODOS),
    "CAPACITACIONES": (_capacitaciones, STAFF),
    "PLAGAS":         (_plagas,         STAFF),
    "ENFERMEDADES":   (_enfermedades,   STAFF),
    "PERSONAL":       (_personal,       ("admin",)),
}


def crear(master, nombre, datos):
    """Devuelve el Frame de la sección, o None si el rol no tiene acceso."""
    funcion, permitidos = SECCIONES[nombre]
    rol = datos["rol"] if datos else "admin"      # sin datos (prueba suelta) = admin
    if rol not in permitidos:
        return None
    return funcion(master, datos)