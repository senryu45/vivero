"""Punto de entrada de la app Vivero.

Flujo:  selección de rol  ->  login  ->  (registro de clientes)  ->  pantalla principal
"""
import tkinter as tk
from tkinter import messagebox

import comun
import db
import menu_principal
from roles import pantalla_roles
from login import pantalla_login
from registro import pantalla_registro


class App(tk.Tk):
    """Una sola ventana que va cambiando de pantalla."""

    def __init__(self):
        super().__init__()
        self.resizable(False, False)
        self.pantalla = None
        self.usuario = None          # dict del usuario autenticado
        if not self._probar_bd():
            self.after(0, self.destroy)
            return
        self.mostrar_roles()

    def _probar_bd(self):
        """Verifica la conexión a viveros_db antes de abrir la app."""
        try:
            db.conectar().close()
            return True
        except Exception as e:
            messagebox.showerror(
                "Error de base de datos",
                f"No se pudo conectar a viveros_db:\n{e}\n\n"
                "Revisa host, usuario y contraseña en el archivo .env.")
            return False

    def _mostrar(self, titulo, ancho, alto, crear):
        """Destruye la pantalla actual, ajusta la ventana y crea la nueva."""
        if self.pantalla is not None:
            self.pantalla.destroy()
        self.title(titulo)
        self.geometry(f"{ancho}x{alto}")
        self.pantalla = crear()
        self.pantalla.place(x=0, y=0, width=ancho, height=alto)

    # ---- Pantallas ----
    def mostrar_roles(self):
        self.usuario = None
        self._mostrar("Vivero - Inicio de sesion", comun.ANCHO, comun.ALTO,
                      lambda: pantalla_roles(self, al_elegir=self.mostrar_login))

    def mostrar_login(self, rol):
        self._mostrar(f"Vivero - {rol}", comun.ANCHO, comun.ALTO,
                      lambda: pantalla_login(self, rol,
                                             al_entrar=self.mostrar_principal,
                                             al_volver=self.mostrar_roles,
                                             al_registrar=self.mostrar_registro))

    def mostrar_registro(self):
        self._mostrar("Vivero - Crear cuenta", comun.ANCHO, comun.ALTO,
                      lambda: pantalla_registro(
                          self,
                          al_registrado=lambda: self.mostrar_login("Cliente"),
                          al_volver=lambda: self.mostrar_login("Cliente")))

    def mostrar_principal(self, correo, rol):
        # Datos del usuario autenticado (incluye id_cliente / id_empleado si aplica)
        self.usuario = db.consultar(
            """SELECT u.id_usuario, u.nombre_completo, u.rol,
                      c.id_cliente, e.id_empleado
               FROM usuarios u
               LEFT JOIN clientes  c ON c.id_usuario = u.id_usuario
               LEFT JOIN empleados e ON e.id_usuario = u.id_usuario
               WHERE lower(u.correo) = lower(%s)""",
            (correo,), uno=True)

        if self.usuario is None:
            messagebox.showerror(
                "Error",
                "No se encontraron los datos del usuario autenticado.")
            self.mostrar_roles()
            return

        self._mostrar(
            f"Vivero - {correo} ({rol})",
            menu_principal.ANCHO, menu_principal.ALTO,
            lambda: menu_principal.pantalla_principal(
                self,
                usuario=correo,
                datos=self.usuario,
                al_cerrar=self.mostrar_roles))


if __name__ == "__main__":
    App().mainloop()