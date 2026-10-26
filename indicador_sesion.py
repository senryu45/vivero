"""Indicador de sesión activa: luz parpadeante + tiempo de actividad al cerrar sesión."""
import time
import tkinter as tk
from tkinter import messagebox

FONDO = "#E6E8DF"
TEXTO = "#4A3B33"
CAFE = "#99553A"
CAFE_HOVER = "#7A4029"
VERDE_LUZ = "#2ECC40"
VERDE_APAGADO = "#B5E3B9"
ROJO_LUZ = "#D93025"
FUENTE = "Open Sans"

INTERVALO_MS = 600            # velocidad del parpadeo

# Valor de usuarios.rol -> texto que se muestra
ETIQUETAS = {"admin": "Admin", "vendedor": "Empleado", "cliente": "Cliente"}


def formatear_duracion(segundos):
    """Segundos -> 'HH:MM:SS'."""
    segundos = int(segundos)
    horas, resto = divmod(segundos, 3600)
    minutos, segundos = divmod(resto, 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


class IndicadorSesion(tk.Frame):
    """Luz verde parpadeante + 'Rol activo' + enlace 'Cerrar sesión'.

    rol:        valor del ENUM (admin, vendedor o cliente).
    al_cerrar:  se llama después de mostrar el tiempo activo (vuelve a la pantalla de roles).
    """

    def __init__(self, master, rol, al_cerrar, fondo=FONDO):
        super().__init__(master, bg=fondo)
        self.nombre = ETIQUETAS.get(rol, str(rol).capitalize())
        self.al_cerrar = al_cerrar
        self.inicio = time.monotonic()      # momento en que inició la sesión
        self.activa = True
        self.encendida = True
        self.trabajo = None                 # id del after() del parpadeo

        self.luz = tk.Canvas(self, width=16, height=16, bg=fondo, highlightthickness=0)
        self.luz.pack(side="left", padx=(0, 7))
        self.punto = self.luz.create_oval(2, 2, 14, 14, fill=VERDE_LUZ, outline="")

        self.texto = tk.Label(self, text=f"{self.nombre} activo", bg=fondo, fg=TEXTO,
                              font=(FUENTE, 10, "bold"))
        self.texto.pack(side="left")

        self.boton = tk.Label(self, text="Cerrar sesión", bg=fondo, fg=CAFE,
                              font=(FUENTE, 9, "underline"), cursor="hand2")
        self.boton.pack(side="left", padx=(16, 0))
        self.boton.bind("<Button-1>", lambda e: self.cerrar_sesion())
        self.boton.bind("<Enter>", lambda e: self.boton.config(fg=CAFE_HOVER))
        self.boton.bind("<Leave>", lambda e: self.boton.config(fg=CAFE))

        self.trabajo = self.after(INTERVALO_MS, self._parpadear)

    # ---------------- Parpadeo ----------------
    def _parpadear(self):
        if not self.activa:
            return
        self.encendida = not self.encendida
        self.luz.itemconfig(self.punto, fill=VERDE_LUZ if self.encendida else VERDE_APAGADO)
        self.trabajo = self.after(INTERVALO_MS, self._parpadear)

    def _detener(self):
        if self.trabajo is not None:
            self.after_cancel(self.trabajo)
            self.trabajo = None

    def destroy(self):
        """Cancela el parpadeo antes de destruir el widget (evita errores de Tk)."""
        self.activa = False
        self._detener()
        super().destroy()

    # ---------------- Cierre de sesión ----------------
    def tiempo_activo(self):
        return formatear_duracion(time.monotonic() - self.inicio)

    def cerrar_sesion(self):
        if not self.activa:
            return
        self.activa = False
        self._detener()

        duracion = self.tiempo_activo()
        self.luz.itemconfig(self.punto, fill=ROJO_LUZ)           # rojo estático
        self.texto.config(text=f"{self.nombre} inactivo · activo {duracion}")
        self.boton.pack_forget()
        self.update_idletasks()                                  # pinta el rojo antes del aviso

        messagebox.showinfo(
            "Sesión cerrada",
            f"Sesión de {self.nombre.lower()} cerrada.\nTiempo activo: {duracion}",
            parent=self.winfo_toplevel())
        self.al_cerrar()