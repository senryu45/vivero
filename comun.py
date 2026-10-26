"""Elementos compartidos por las pantallas de selección de rol y de login."""
import os
import tkinter as tk

# ----------------------------- Colores del diseño -----------------------------
VERDE_OSCURO = "#3F5A1A"
FONDO_DERECHO = "#C5C7B5"
CAFE = "#99553A"
CAFE_OSCURO = "#4F3F36"
CAFE_OSCURO_HOVER = "#66544A"
BLANCO = "#FFFFFF"
TEXTO = "#3A3A3A"

FUENTE = "Open Sans"  # si no está instalada, Tkinter usa una fuente por defecto

# ------------------------------- Tamaños --------------------------------------
ANCHO, ALTO = 1000, 567
ANCHO_IZQ = 295
ALTO_LOGO = 262
ALTO_FOTO = ALTO - ALTO_LOGO

# Imagen opcional para la parte inferior izquierda (manos con la planta).
# Guárdala junto a estos archivos con el nombre "planta.jpg" (o .png).
RUTA_FOTO = ["planta.jpg", "planta.png"]


def rectangulo_redondeado(canvas, x1, y1, x2, y2, color, tag=None):
    """Dibuja una 'píldora' (extremos totalmente redondeados) en el canvas."""
    r = (y2 - y1) / 2
    canvas.create_oval(x1, y1, x1 + 2 * r, y2, fill=color, outline=color, tags=tag)
    canvas.create_oval(x2 - 2 * r, y1, x2, y2, fill=color, outline=color, tags=tag)
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=color, outline=color, tags=tag)


def dibujar_brote(canvas, cx, base_y):
    """Dibuja un brote sencillo (tierra, tallo y dos hojas)."""
    canvas.create_oval(cx - 52, base_y - 16, cx + 52, base_y + 14,
                       fill="#6B4A36", outline="")
    canvas.create_oval(cx - 30, base_y - 22, cx + 30, base_y - 2,
                       fill="#7A5640", outline="")
    canvas.create_line(cx, base_y - 12, cx, base_y - 60, fill="#4DB04A",
                       width=5, capstyle="round")
    canvas.create_polygon(cx, base_y - 55, cx - 20, base_y - 80, cx - 52, base_y - 78,
                          cx - 48, base_y - 58, cx - 25, base_y - 45,
                          fill="#8BCB4E", outline="#5FA83A", smooth=True)
    canvas.create_polygon(cx, base_y - 55, cx + 20, base_y - 85, cx + 52, base_y - 82,
                          cx + 48, base_y - 60, cx + 25, base_y - 47,
                          fill="#8BCB4E", outline="#5FA83A", smooth=True)


def _cargar_foto():
    """Carga y recorta la foto para que llene el espacio. Devuelve None si no existe."""
    carpeta = os.path.dirname(os.path.abspath(__file__))
    try:
        from PIL import Image, ImageOps, ImageTk
        hay_pillow = True
    except ImportError:
        hay_pillow = False

    for nombre in RUTA_FOTO:
        ruta = os.path.join(carpeta, nombre)
        if not os.path.exists(ruta):
            continue
        try:
            if hay_pillow:
                img = Image.open(ruta)
                img = ImageOps.fit(img, (ANCHO_IZQ, ALTO_FOTO), method=Image.LANCZOS)
                return ImageTk.PhotoImage(img)
            # Sin Pillow solo funcionan PNG/GIF, y sin redimensionar
            return tk.PhotoImage(file=ruta)
        except Exception:
            continue  # prueba con el siguiente archivo
    return None


def crear_panel_izquierdo(padre):
    """Panel verde con el logo y la foto. Se usa igual en rol y login."""
    panel = tk.Frame(padre, width=ANCHO_IZQ, height=ALTO, bg=VERDE_OSCURO)
    panel.place(x=0, y=0)

    logo = tk.Canvas(panel, width=ANCHO_IZQ, height=ALTO_LOGO,
                     bg=VERDE_OSCURO, highlightthickness=0)
    logo.place(x=0, y=0)
    logo.create_text(ANCHO_IZQ / 2, 62, text="VIVERO", fill=CAFE,
                     font=(FUENTE, 30, "bold"))
    dibujar_brote(logo, ANCHO_IZQ / 2, 205)

    foto = tk.Label(panel, bg="#2B1D14")
    foto.place(x=0, y=ALTO_LOGO, width=ANCHO_IZQ, height=ALTO_FOTO)
    foto.imagen = _cargar_foto()  # referencia para que no la borre el recolector
    if foto.imagen:
        foto.config(image=foto.imagen)
    else:
        foto.config(text="Coloca aquí tu foto\n(planta.jpg)", fg="#B8A898",
                    font=(FUENTE, 11))
    return panel