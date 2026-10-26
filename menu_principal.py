import os
import tkinter as tk

import secciones   # secciones conectadas a viveros_db (usa db.py internamente)
from indicador_sesion import IndicadorSesion

# ----------------------------- Colores del diseño -----------------------------
VERDE_OSCURO = "#3F5A1A"
VERDE_CLARO = "#8BCB4E"
FONDO = "#E6E8DF"
FONDO_SECCION = "#C5C7B5"
CAFE = "#99553A"
TEXTO_MENU = "#E3E8D3"
BLANCO = "#FFFFFF"

FUENTE = "Open Sans"  # si no está instalada, Tkinter usa una fuente por defecto

# ------------------------------- Tamaños --------------------------------------
ANCHO = 1000
ALTO_ESTADO = 30                      # franja superior con el indicador de sesión
ALTO_BARRA = 70
ALTO_FOTO = 490
Y_CONTENIDO = ALTO_ESTADO + ALTO_BARRA
ALTO = Y_CONTENIDO + ALTO_FOTO

ARCHIVO_FOTO = "vivero.jpg"

# Opciones del menú y posición horizontal (centro) de cada una en la barra
MENU = [
    ("INICIO", 130),
    ("PLANTAS", 225),
    ("CATALOGO", 335),
    ("VENTAS", 435),
    ("CAPACITACIONES", 545),
    ("PLAGAS", 665),
    ("ENFERMEDADES", 780),
    ("PERSONAL", 905),
]


# ------------------------------- Dibujo ---------------------------------------
def rectangulo_redondeado(canvas, x1, y1, x2, y2, radio, color):
    """Rectángulo con esquinas redondeadas."""
    puntos = [x1 + radio, y1, x2 - radio, y1, x2, y1, x2, y1 + radio,
              x2, y2 - radio, x2, y2, x2 - radio, y2, x1 + radio, y2,
              x1, y2, x1, y2 - radio, x1, y1 + radio, x1, y1]
    canvas.create_polygon(puntos, smooth=True, fill=color, outline=color)


def dibujar_brote(canvas, cx, base_y, e=1.0):
    """Brote sencillo (tierra, tallo y dos hojas). 'e' es la escala."""
    def p(*coords):
        return [cx + c * e if i % 2 == 0 else base_y + c * e
                for i, c in enumerate(coords)]

    canvas.create_oval(p(-52, -16, 52, 14), fill="#6B4A36", outline="")
    canvas.create_oval(p(-30, -22, 30, -2), fill="#7A5640", outline="")
    canvas.create_line(p(0, -12, 0, -60), fill="#4DB04A",
                       width=max(2, int(5 * e)), capstyle="round")
    canvas.create_polygon(p(0, -55, -20, -80, -52, -78, -48, -58, -25, -45),
                          fill=VERDE_CLARO, outline="#5FA83A", smooth=True)
    canvas.create_polygon(p(0, -55, 20, -85, 52, -82, 48, -60, 25, -47),
                          fill=VERDE_CLARO, outline="#5FA83A", smooth=True)


# ------------------------------ Pantalla --------------------------------------
class pantalla_principal(tk.Frame):
    def __init__(self, master, usuario=None, datos=None, al_cerrar=None):
        """
        usuario:   correo del usuario (solo para mostrar).
        datos:     dict de la BD con id_usuario, nombre_completo, rol,
                   id_cliente e id_empleado (los arma main.py tras el login).
        al_cerrar: función que se llama al cerrar sesión (vuelve a la pantalla de roles).
        """
        super().__init__(master, width=ANCHO, height=ALTO, bg=FONDO)
        self.usuario = usuario
        self.datos = datos
        self.al_cerrar = al_cerrar
        self.contenido = None      # sección abierta actualmente
        self.activa = None
        self.foto_tk = None

        self._crear_estado()
        self._crear_contenido()
        self._crear_barra()
        self.mostrar_seccion("INICIO")

    # ---- Franja superior: usuario activo ----
    def _crear_estado(self):
        franja = tk.Frame(self, bg=FONDO)
        franja.place(x=0, y=0, width=ANCHO, height=ALTO_ESTADO)
        if self.datos is None:                 # prueba suelta sin inicio de sesión
            return
        self.indicador = IndicadorSesion(
            franja, self.datos["rol"],
            al_cerrar=self.al_cerrar or (lambda: None), fondo=FONDO)
        self.indicador.pack(side="right", padx=(0, 22), pady=4)

    # ---- Área de contenido (debajo de la barra) ----
    def _crear_contenido(self):
        self.foto = tk.Label(self, bg="#2B3A1A")
        self.foto.place(x=0, y=Y_CONTENIDO, width=ANCHO, height=ALTO_FOTO)
        self.foto_tk = self._cargar_foto()
        if self.foto_tk:
            self.foto.config(image=self.foto_tk)
        else:
            self.foto.config(text=f"Coloca aquí la foto del vivero\n({ARCHIVO_FOTO})",
                             fg="#B8C9A0", font=(FUENTE, 12))

        self.panel = tk.Frame(self, bg=FONDO_SECCION)
        self.titulo = tk.Label(self.panel, bg=FONDO_SECCION, fg=CAFE,
                               font=(FUENTE, 26, "bold"))
        self.titulo.place(relx=0.5, rely=0.42, anchor="center")
        self.subtitulo = tk.Label(self.panel, text="", bg=FONDO_SECCION,
                                  fg=VERDE_OSCURO, font=(FUENTE, 13))
        self.subtitulo.place(relx=0.5, rely=0.52, anchor="center")

    def _cargar_foto(self):
        """Carga la foto y la ajusta al área. Devuelve None si no se puede."""
        ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), ARCHIVO_FOTO)
        if not os.path.exists(ruta):
            return None
        try:
            from PIL import Image, ImageOps, ImageTk
            imagen = ImageOps.fit(Image.open(ruta), (ANCHO, ALTO_FOTO),
                                  method=Image.LANCZOS)
            return ImageTk.PhotoImage(imagen)
        except Exception:
            return None  # sin Pillow (pip install pillow) o imagen inválida

    # ---- Barra de navegación ----
    def _crear_barra(self):
        self.barra = tk.Canvas(self, width=ANCHO, height=ALTO_BARRA, bg=FONDO,
                               highlightthickness=0)
        self.barra.place(x=0, y=ALTO_ESTADO)
        rectangulo_redondeado(self.barra, 6, 6, ANCHO - 6, ALTO_BARRA - 8, 10,
                              VERDE_OSCURO)

        dibujar_brote(self.barra, 42, 54, e=0.4)

        self.items = {}
        for nombre, x in MENU:
            # "PERSONAL" solo lo ve el administrador
            if nombre == "PERSONAL" and self.datos and self.datos["rol"] != "admin":
                continue
            item = self.barra.create_text(x, (ALTO_BARRA - 2) / 2, text=nombre,
                                          fill=TEXTO_MENU, font=(FUENTE, 10))
            self.items[nombre] = item
            self.barra.tag_bind(item, "<Enter>", lambda e, n=nombre: self._hover(n, True))
            self.barra.tag_bind(item, "<Leave>", lambda e, n=nombre: self._hover(n, False))
            self.barra.tag_bind(item, "<Button-1>", lambda e, n=nombre: self.mostrar_seccion(n))

    def _hover(self, nombre, dentro):
        self.barra.config(cursor="hand2" if dentro else "")
        color = BLANCO if (dentro or nombre == self.activa) else TEXTO_MENU
        self.barra.itemconfig(self.items[nombre], fill=color)

    # ---- Navegación entre secciones ----
    def mostrar_seccion(self, nombre):
        self.activa = nombre

        self.barra.delete("subrayado")
        for n, item in self.items.items():
            self.barra.itemconfig(item, fill=BLANCO if n == nombre else TEXTO_MENU)
        x1, _, x2, y2 = self.barra.bbox(self.items[nombre])
        self.barra.create_line(x1, y2 + 3, x2, y2 + 3, fill=VERDE_CLARO, width=2,
                               tags="subrayado")

        # Quitar la sección anterior (así los datos se recargan al volver)
        if self.contenido is not None:
            self.contenido.destroy()
            self.contenido = None

        if nombre == "INICIO":
            self.panel.place_forget()
            return

        self.titulo.config(text=nombre.capitalize())
        self.panel.place(x=0, y=Y_CONTENIDO, width=ANCHO, height=ALTO_FOTO)

        self.contenido = secciones.crear(self.panel, nombre, self.datos)
        if self.contenido is None:
            self.subtitulo.config(text="No tienes acceso a esta sección")
        else:
            self.subtitulo.config(text="")
            self.contenido.place(x=0, y=0, width=ANCHO, height=ALTO_FOTO)


def abrir(usuario=None, datos=None):
    """Abre la pantalla principal por separado (útil para probarla sola)."""
    ventana = tk.Tk()
    ventana.title("Vivero" if not usuario else f"Vivero - {usuario}")
    ventana.geometry(f"{ANCHO}x{ALTO}")
    ventana.resizable(False, False)
    ventana.configure(bg=FONDO)
    pantalla_principal(ventana, usuario, datos,
                       al_cerrar=ventana.destroy).pack()
    ventana.mainloop()


if __name__ == "__main__":
    abrir()