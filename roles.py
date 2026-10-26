import tkinter as tk

from comun import (ANCHO, ALTO, ANCHO_IZQ, FONDO_DERECHO, VERDE_OSCURO, CAFE,
                   TEXTO, FUENTE, crear_panel_izquierdo)

S = 1.5  # escala de los iconos


class pantalla_roles(tk.Frame):
    """Primera pantalla: el usuario elige su rol.

    al_elegir(rol) se llama con "Administrador", "Personal" o "Cliente".
    """

    def __init__(self, master, al_elegir):
        super().__init__(master, width=ANCHO, height=ALTO, bg=FONDO_DERECHO)
        self.al_elegir = al_elegir

        crear_panel_izquierdo(self)

        derecho = tk.Frame(self, bg=FONDO_DERECHO, width=ANCHO - ANCHO_IZQ, height=ALTO)
        derecho.place(x=ANCHO_IZQ, y=0)
        x_centro = (ANCHO - ANCHO_IZQ) / 2

        tk.Label(derecho, text="Inicio de sesion", bg=FONDO_DERECHO, fg=CAFE,
                 font=(FUENTE, 26, "bold")).place(x=x_centro, y=98, anchor="center")

        roles = [
            ("Administrador", x_centro - 232, self._icono_admin),
            ("Personal", x_centro, self._icono_personal),
            ("Cliente", x_centro + 232, self._icono_cliente),
        ]
        for nombre, x, dibujar in roles:
            self._crear_boton_rol(derecho, nombre, x, dibujar)

    # ---------------- Botones de rol ----------------
    def _crear_boton_rol(self, padre, nombre, x, dibujar_icono):
        marco = tk.Frame(padre, bg=FONDO_DERECHO, cursor="hand2")
        marco.place(x=x, y=420, anchor="center")

        canvas = tk.Canvas(marco, width=int(80 * S), height=int(64 * S),
                           bg=FONDO_DERECHO, highlightthickness=0)
        canvas.pack()
        dibujar_icono(canvas)

        etiqueta = tk.Label(marco, text=nombre, bg=FONDO_DERECHO, fg=TEXTO,
                            font=(FUENTE, 13))
        etiqueta.pack(pady=(8, 0))

        for w in (marco, canvas, etiqueta):
            w.bind("<Button-1>", lambda e, n=nombre: self.al_elegir(n))
            w.bind("<Enter>", lambda e, l=etiqueta: l.configure(fg=CAFE))
            w.bind("<Leave>", lambda e, l=etiqueta: l.configure(fg=TEXTO))

    # ---------------- Iconos dibujados ----------------
    def _persona(self, c, cx, y_cabeza, r, ancho, alto):
        cx, y_cabeza, r, ancho, alto = (v * S for v in (cx, y_cabeza, r, ancho, alto))
        c.create_oval(cx - r, y_cabeza - r, cx + r, y_cabeza + r,
                      fill=VERDE_OSCURO, outline="")
        top = y_cabeza + r + 2
        c.create_arc(cx - ancho / 2, top, cx + ancho / 2, top + alto * 2,
                     start=0, extent=180, fill=VERDE_OSCURO, outline="")

    def _icono_admin(self, c):
        self._persona(c, 48, 14, 9, 30, 20)   # persona de atrás
        self._persona(c, 30, 26, 11, 38, 22)  # persona de adelante

    def _icono_personal(self, c):
        self._persona(c, 40, 20, 13, 50, 22)

    def _icono_cliente(self, c):
        for cx in (28, 40, 52):
            self._persona(c, cx, 12 if cx == 40 else 16, 6, 16, 8)
        linea = lambda *p: c.create_line([v * S for v in p],
                                         fill=VERDE_OSCURO, width=3)
        linea(10, 52, 22, 52, 22, 40)
        linea(22, 46, 55, 46, 68, 40)
        linea(22, 56, 55, 56, 70, 44)