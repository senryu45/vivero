"""Pantalla PLANTAS: cuadrícula (diap. 4), ficha de planta (diap. 5) y alta/lista de plantas (diap. 6).

También se usa como ficha dentro de CATALOGO (ver catalogo_secciones.py):
  Catalogo(master, datos, al_volver=..., carrito=..., id_inicial=<id_planta>)
"""
import os
import re
import tkinter as tk
import unicodedata
from decimal import Decimal, InvalidOperation
from tkinter import ttk, messagebox

import psycopg2.errors

import db

# ----------------------------- Colores y constantes -----------------------------
VERDE_OSCURO = "#3F5A1A"
VERDE_CLARO = "#8BCB4E"
VERDE_BUSCADOR = "#587A2D"
FONDO_SECCION = "#C5C7B5"
FONDO_TARJETA = "#E6E8DF"
FONDO_IMAGEN = "#DDE3CC"
CAFE = "#99553A"
CAFE_HOVER = "#7A4029"
BLANCO = "#FFFFFF"
TEXTO = "#4A3B33"
TEXTO_CLARO = "#E3E8D3"
FUENTE = "Open Sans"

# Diapositiva 4: cuadrícula
COLUMNAS = 6
FILAS = 2
POR_PAGINA = COLUMNAS * FILAS
LADO, RADIO = 96, 18                  # miniatura cuadrada y redondeo de esquinas
ANCHO_CELDA, ALTO_CELDA = 150, 138

# Diapositiva 5: ficha
FOTO_ANCHO, FOTO_ALTO, FOTO_RADIO = 100, 150, 16
PESTANAS = ["Descripción", "Cuidados", "Enfermedades frecuentes", "Plagas frecuentes"]

# Diapositiva 6: agregar planta y lista
ESTADOS = {"Saludable": "saludable", "En riesgo": "en_riesgo", "Enferma": "enferma"}
ESTADOS_INV = {v: k for k, v in ESTADOS.items()}
CATEGORIA_VACIA = "Seleccionar categoría"
MINIATURA, MINIATURA_RADIO = 60, 10
ALTO_FILA = 78


# ------------------------------- Utilidades de dibujo -------------------------------
def dinero(valor):
    """Formatea un precio; muestra una raya si no hay valor."""
    return "—" if valor is None else f"${valor:,.2f}"


def rectangulo_redondeado(canvas, x1, y1, x2, y2, radio, color):
    """Rectángulo con esquinas redondeadas. Devuelve el id del polígono."""
    puntos = [x1 + radio, y1, x2 - radio, y1, x2, y1, x2, y1 + radio,
              x2, y2 - radio, x2, y2, x2 - radio, y2, x1 + radio, y2,
              x1, y2, x1, y2 - radio, x1, y1 + radio, x1, y1]
    return canvas.create_polygon(puntos, smooth=True, fill=color, outline=color)


def dibujar_planta(canvas, cx, base_y, escala, color_hoja=VERDE_CLARO):
    """Brote sencillo (tierra, tallo y dos hojas) como imagen provisional."""
    def p(*c):
        return [cx + v * escala if i % 2 == 0 else base_y + v * escala
                for i, v in enumerate(c)]

    canvas.create_oval(p(-52, -16, 52, 14), fill="#6B4A36", outline="")
    canvas.create_oval(p(-30, -22, 30, -2), fill="#7A5640", outline="")
    canvas.create_line(p(0, -12, 0, -60), fill="#4DB04A",
                       width=max(2, int(5 * escala)), capstyle="round")
    canvas.create_polygon(p(0, -55, -20, -80, -52, -78, -48, -58, -25, -45),
                          fill=color_hoja, outline="#5FA83A", smooth=True)
    canvas.create_polygon(p(0, -55, 20, -85, 52, -82, 48, -60, 25, -47),
                          fill=color_hoja, outline="#5FA83A", smooth=True)


def icono_editar(canvas, color=TEXTO_CLARO):
    """Icono de lápiz sobre un cuadro (canvas de 20x20)."""
    canvas.create_rectangle(3, 5, 14, 17, outline=color, width=2)
    canvas.create_line(8, 12, 17, 3, fill=color, width=3)


def icono_papelera(canvas, color=TEXTO_CLARO):
    """Icono de papelera (canvas de 20x20)."""
    canvas.create_line(3, 5, 17, 5, fill=color, width=2)
    canvas.create_line(8, 5, 8, 3, 12, 3, 12, 5, fill=color, width=2)
    canvas.create_polygon(5, 7, 15, 7, 14, 18, 6, 18, outline=color, fill="", width=2)


def enlazar_clic(widget, comando):
    """Hace clicable un widget y todos sus hijos."""
    widget.bind("<Button-1>", lambda e: comando())
    widget.configure(cursor="hand2")
    for hijo in widget.winfo_children():
        enlazar_clic(hijo, comando)


# ------------------------------- Fotos de las plantas -------------------------------
CARPETA_IMAGENES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "imagenes")
EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp")
_cache_fotos = {}     # evita recargar y mantiene viva la referencia de cada PhotoImage


def _slug(texto):
    """'Hierba Buena' -> 'hierba_buena' (sin acentos ni símbolos)."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def buscar_imagen(planta):
    """Busca imagenes/<nombre>.jpg o imagenes/<id_planta>.jpg. Devuelve la ruta o None."""
    for base in (_slug(planta["nombre_comun"]), str(planta["id_planta"])):
        for ext in EXTENSIONES:
            ruta = os.path.join(CARPETA_IMAGENES, base + ext)
            if os.path.exists(ruta):
                return ruta
    return None


def foto_redondeada(planta, ancho, radio, alto=None):
    """Foto con esquinas redondeadas (cuadrada si no se da 'alto'), o None si no hay foto."""
    alto = alto or ancho
    ruta = buscar_imagen(planta)
    if ruta is None:
        return None
    clave = (ruta, ancho, alto, radio)
    if clave in _cache_fotos:
        return _cache_fotos[clave]
    try:
        from PIL import Image, ImageOps, ImageDraw, ImageTk
        imagen = ImageOps.fit(Image.open(ruta).convert("RGBA"), (ancho, alto),
                              method=Image.LANCZOS)
        mascara = Image.new("L", (ancho, alto), 0)
        ImageDraw.Draw(mascara).rounded_rectangle((0, 0, ancho - 1, alto - 1),
                                                  radius=radio, fill=255)
        imagen.putalpha(mascara)
        foto = ImageTk.PhotoImage(imagen)
    except Exception:
        return None            # sin Pillow (pip install pillow) o imagen inválida
    _cache_fotos[clave] = foto
    return foto


# ==================================================================================
#                                   CLASE CATALOGO
# ==================================================================================
class Catalogo(tk.Frame):
    """Cabecera (solo clientes) + una vista a la vez.

    Vistas:
      - mostrar_cuadricula()   diapositiva 4: miniaturas con filtros y paginación
      - mostrar_detalle(id)    diapositiva 5: ficha de la planta con pestañas
      - mostrar_agregar()      diapositiva 6: formulario de alta + lista con editar/eliminar

    Parámetros opcionales (para usarla como ficha dentro de CATALOGO):
      al_volver   función que se llama con '← Volver' en lugar de mostrar la cuadrícula
      carrito     diccionario compartido para no perder el carrito al volver
      id_inicial  abre directamente la ficha de esa planta
    """

    ALTO_CABECERA = 50

    def __init__(self, master, datos=None, al_volver=None, carrito=None, id_inicial=None):
        super().__init__(master, bg=FONDO_SECCION)
        self.datos = datos
        self.es_staff = (datos is None) or datos["rol"] in ("admin", "vendedor")

        self.al_volver = al_volver
        self.carrito = carrito if carrito is not None else {}   # id_planta -> {"nombre", "precio", "cantidad"}
        self.ALTO_CABECERA = 0 if self.es_staff else 50          # el personal no necesita la franja del carrito
        self.lbl_carrito = None
        self.vista = None

        # Estado de la cuadrícula (diap. 4)
        self.plantas = []
        self.pagina = 0
        self.var_cat = tk.StringVar(self, value="Todas")
        self.var_txt = tk.StringVar(self)

        # Estado de la ficha (diap. 5)
        self.planta = None
        self.cache_pestanas = {}
        self.pestanas = {}

        # Estado de agregar planta (diap. 6)
        self.lista = []
        self.marcadas = set()        # ids de plantas con la casilla marcada
        self.editando = None         # id de la planta que se está editando (o None)
        self.interior = None
        self.contenedor_lista = None
        self.lienzo_lista = None
        self.trabajo_busqueda = None
        self.marcador_activo = True
        self.rueda_activa = False

        try:
            self.categorias = db.consultar(
                "SELECT id_categoria, nombre FROM categorias ORDER BY nombre")
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))
            self.categorias = []

        if not self.es_staff:
            self._crear_cabecera()
        if id_inicial is not None:
            self.mostrar_detalle(id_inicial)
        else:
            self.mostrar_cuadricula()

    # ------------------------------------------------------------------
    # Estructura común: cabecera, carrito y cambio de vista
    # ------------------------------------------------------------------
    def _volver(self):
        """Regresa al catálogo si la ficha se abrió desde allí; si no, a la cuadrícula."""
        (self.al_volver or self.mostrar_cuadricula)()

    def _crear_cabecera(self):
        cab = tk.Frame(self, bg=FONDO_SECCION)
        cab.place(x=0, y=0, relwidth=1, height=self.ALTO_CABECERA)

        tk.Label(cab, text="Catálogo", bg=FONDO_SECCION, fg=CAFE,
                 font=(FUENTE, 20, "bold")).pack(side="left", padx=(24, 20), pady=8)
        texto = "← Catálogo" if self.al_volver else "Plantas"
        tk.Button(cab, text=texto, command=self._volver, bg=VERDE_OSCURO,
                  fg=BLANCO, relief="flat", padx=12, pady=3, cursor="hand2",
                  font=(FUENTE, 10)).pack(side="left", padx=4)

        self.lbl_carrito = tk.Label(cab, bg=FONDO_SECCION, fg=VERDE_OSCURO,
                                    font=(FUENTE, 11, "bold"))
        self.lbl_carrito.pack(side="right", padx=24)
        self._actualizar_carrito()

    def _actualizar_carrito(self):
        if self.lbl_carrito is None:
            return
        articulos = sum(i["cantidad"] for i in self.carrito.values())
        total = sum(i["cantidad"] * i["precio"] for i in self.carrito.values())
        self.lbl_carrito.config(text=f"Carrito: {articulos} artículo(s) · {dinero(total)}")

    def _nueva_vista(self):
        """Limpia lo pendiente de la vista actual y devuelve un Frame vacío para la nueva."""
        if self.trabajo_busqueda is not None:
            self.after_cancel(self.trabajo_busqueda)
            self.trabajo_busqueda = None
        if self.rueda_activa:
            for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.unbind_all(secuencia)
            self.rueda_activa = False
        self.interior = None

        if self.vista is not None:
            self.vista.destroy()
        self.vista = tk.Frame(self, bg=FONDO_SECCION)
        self.vista.place(x=0, y=self.ALTO_CABECERA, relwidth=1,
                         relheight=1, height=-self.ALTO_CABECERA)
        return self.vista

    def destroy(self):
        """Libera los atajos de la rueda del mouse antes de destruir la pantalla."""
        if self.rueda_activa:
            for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                try:
                    self.unbind_all(secuencia)
                except tk.TclError:
                    pass
            self.rueda_activa = False
        super().destroy()

    def _encabezado_plantas(self, vista):
        """Fila con el título PLANTAS y, para el personal, el enlace '+ Agregar planta'."""
        fila = tk.Frame(vista, bg=FONDO_SECCION)
        fila.pack(fill="x", padx=28, pady=(2, 0))
        tk.Label(fila, text="PLANTAS", bg=FONDO_SECCION, fg=CAFE,
                 font=(FUENTE, 24)).pack(side="left")
        if self.es_staff:
            agregar = tk.Label(fila, text="+ Agregar planta", bg=FONDO_SECCION, fg=CAFE,
                               font=(FUENTE, 15), cursor="hand2")
            agregar.pack(side="right", padx=(0, 20))
            agregar.bind("<Button-1>", lambda e: self.mostrar_agregar())
            agregar.bind("<Enter>", lambda e: agregar.config(fg=CAFE_HOVER))
            agregar.bind("<Leave>", lambda e: agregar.config(fg=CAFE))

    def anadir_al_carrito(self, planta, cantidad_txt):
        """Valida la cantidad contra las existencias y la suma al carrito."""
        try:
            cantidad = int(cantidad_txt)
        except ValueError:
            messagebox.showwarning("Carrito", "Escribe una cantidad válida.")
            return
        en_carrito = self.carrito.get(planta["id_planta"], {}).get("cantidad", 0)
        if cantidad < 1 or en_carrito + cantidad > planta["cantidad"]:
            messagebox.showwarning(
                "Carrito",
                f"Solo hay {planta['cantidad']} disponible(s) y ya tienes "
                f"{en_carrito} en el carrito.")
            return
        self.carrito[planta["id_planta"]] = {
            "nombre": planta["nombre_comun"], "precio": planta["precio"],
            "cantidad": en_carrito + cantidad}
        self._actualizar_carrito()
        messagebox.showinfo("Carrito", f"{cantidad} × {planta['nombre_comun']} añadido(s).")

    # ==================================================================
    # DIAPOSITIVA 4: cuadrícula de plantas
    # ==================================================================
    def mostrar_cuadricula(self):
        vista = self._nueva_vista()

        self._encabezado_plantas(vista)
        self._crear_filtros(vista)
        self._crear_paginador(vista)           # va abajo: se empaqueta antes que la zona

        self.zona = tk.Frame(vista, bg=FONDO_SECCION)
        self.zona.pack(fill="both", expand=True, padx=12, pady=(4, 0))
        self.zona.columnconfigure(tuple(range(COLUMNAS)), weight=1)

        self._cargar_plantas()
        self._dibujar_pagina()

    def _crear_filtros(self, vista):
        barra = tk.Frame(vista, bg=FONDO_SECCION)
        barra.pack(fill="x", padx=28, pady=(0, 2))

        tk.Label(barra, text="Categoría", bg=FONDO_SECCION, fg=VERDE_OSCURO,
                 font=(FUENTE, 9)).pack(side="left")
        combo = ttk.Combobox(
            barra, textvariable=self.var_cat, state="readonly", width=16,
            values=["Todas"] + [c["nombre"] for c in self.categorias])
        combo.pack(side="left", padx=(6, 14))
        combo.bind("<<ComboboxSelected>>", lambda e: self._filtrar())

        tk.Label(barra, text="Buscar", bg=FONDO_SECCION, fg=VERDE_OSCURO,
                 font=(FUENTE, 9)).pack(side="left")
        entrada = tk.Entry(barra, textvariable=self.var_txt, font=(FUENTE, 9),
                           width=22, relief="flat")
        entrada.pack(side="left", padx=6, ipady=2)
        entrada.bind("<Return>", lambda e: self._filtrar())

        tk.Button(barra, text="Buscar", command=self._filtrar, bg=CAFE, fg=BLANCO,
                  relief="flat", padx=8, font=(FUENTE, 8)).pack(side="left", padx=3)
        tk.Button(barra, text="Limpiar", command=self._limpiar_filtros, bg=CAFE,
                  fg=BLANCO, relief="flat", padx=8, font=(FUENTE, 8)).pack(side="left")

    def _crear_paginador(self, vista):
        pie = tk.Frame(vista, bg=FONDO_SECCION)
        pie.pack(side="bottom", fill="x", padx=28, pady=4)
        self.btn_ant = tk.Button(pie, text="◀ Anterior",
                                 command=lambda: self._cambiar_pagina(-1),
                                 bg=VERDE_OSCURO, fg=BLANCO, relief="flat", padx=10,
                                 font=(FUENTE, 9))
        self.btn_ant.pack(side="left")
        self.lbl_pagina = tk.Label(pie, bg=FONDO_SECCION, fg=VERDE_OSCURO,
                                   font=(FUENTE, 10))
        self.lbl_pagina.pack(side="left", padx=14)
        self.btn_sig = tk.Button(pie, text="Siguiente ▶",
                                 command=lambda: self._cambiar_pagina(1),
                                 bg=VERDE_OSCURO, fg=BLANCO, relief="flat", padx=10,
                                 font=(FUENTE, 9))
        self.btn_sig.pack(side="left")

    def _limpiar_filtros(self):
        self.var_cat.set("Todas")
        self.var_txt.set("")
        self._filtrar()

    def _filtrar(self):
        self.pagina = 0
        self._cargar_plantas()
        self._dibujar_pagina()

    def _cambiar_pagina(self, delta):
        self.pagina += delta
        self._dibujar_pagina()

    def _cargar_plantas(self):
        """El personal ve todo el inventario; el cliente solo plantas disponibles."""
        sql = """SELECT p.id_planta, p.nombre_comun, p.cantidad
                 FROM plantas p JOIN categorias c USING (id_categoria)
                 WHERE TRUE"""
        params = []
        if not self.es_staff:
            sql += " AND p.disponible"
        if self.var_cat.get() != "Todas":
            sql += " AND c.nombre = %s"
            params.append(self.var_cat.get())
        texto = self.var_txt.get().strip()
        if texto:
            sql += " AND (p.nombre_comun ILIKE %s OR p.nombre_cientifico ILIKE %s)"
            params += [f"%{texto}%", f"%{texto}%"]
        sql += " ORDER BY p.nombre_comun"
        try:
            self.plantas = db.consultar(sql, params)
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))
            self.plantas = []

    def _dibujar_pagina(self):
        for hijo in self.zona.winfo_children():
            hijo.destroy()

        total = len(self.plantas)
        paginas = max(1, -(-total // POR_PAGINA))
        self.pagina = max(0, min(self.pagina, paginas - 1))
        visibles = self.plantas[self.pagina * POR_PAGINA:(self.pagina + 1) * POR_PAGINA]

        if not visibles:
            tk.Label(self.zona, text="No hay plantas con ese filtro.",
                     bg=FONDO_SECCION, fg=VERDE_OSCURO,
                     font=(FUENTE, 13)).place(relx=0.5, rely=0.35, anchor="center")
        for i, planta in enumerate(visibles):
            celda = self._crear_celda(self.zona, planta)
            celda.grid(row=i // COLUMNAS, column=i % COLUMNAS, padx=4, pady=4)

        self.lbl_pagina.config(text=f"Página {self.pagina + 1} de {paginas} · {total} planta(s)")
        self.btn_ant.config(state="normal" if self.pagina > 0 else "disabled")
        self.btn_sig.config(state="normal" if self.pagina < paginas - 1 else "disabled")

    def _crear_celda(self, padre, p):
        """Miniatura redondeada con el nombre debajo."""
        celda = tk.Frame(padre, bg=FONDO_SECCION, width=ANCHO_CELDA, height=ALTO_CELDA)
        celda.pack_propagate(False)

        lienzo = tk.Canvas(celda, width=LADO, height=LADO, bg=FONDO_SECCION,
                           highlightthickness=0)
        lienzo.pack(pady=(4, 6))

        foto = foto_redondeada(p, LADO, RADIO)
        if foto is not None:
            lienzo.create_image(0, 0, anchor="nw", image=foto)
        else:                                    # sin foto: cuadro redondeado + brote
            rectangulo_redondeado(lienzo, 0, 0, LADO, LADO, RADIO, FONDO_IMAGEN)
            dibujar_planta(lienzo, LADO / 2, LADO - 10, 0.8)

        tk.Label(celda, text=p["nombre_comun"], bg=FONDO_SECCION, fg=CAFE,
                 font=(FUENTE, 11, "bold"), wraplength=ANCHO_CELDA - 10,
                 justify="center").pack()

        enlazar_clic(celda, lambda i=p["id_planta"]: self.mostrar_detalle(i))
        return celda

    # ==================================================================
    # DIAPOSITIVA 5: ficha de la planta
    # ==================================================================
    def mostrar_detalle(self, id_planta):
        try:
            planta = db.consultar(
                """SELECT p.*, c.nombre AS categoria
                   FROM plantas p JOIN categorias c USING (id_categoria)
                   WHERE p.id_planta = %s""", (id_planta,), uno=True)
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))
            return
        if planta is None:
            messagebox.showwarning("Catálogo", "La planta ya no existe.")
            self._volver()
            return

        self.planta = planta
        self.cache_pestanas = {}
        self.pestanas = {}

        vista = self._nueva_vista()
        self._encabezado_plantas(vista)
        self._crear_volver(vista)
        self._crear_resumen(vista)
        self._crear_pestanas(vista)
        if not self.es_staff:
            self._crear_accion_carrito(vista)
        self._mostrar_pestana("Descripción")

    def _crear_volver(self, vista):
        volver = tk.Label(vista, text="← Volver", bg=FONDO_SECCION, fg=VERDE_OSCURO,
                          font=(FUENTE, 10), cursor="hand2")
        volver.pack(anchor="w", padx=28, pady=(0, 2))
        volver.bind("<Button-1>", lambda e: self._volver())
        volver.bind("<Enter>", lambda e: volver.config(fg=CAFE))
        volver.bind("<Leave>", lambda e: volver.config(fg=VERDE_OSCURO))

    def _crear_resumen(self, vista):
        """Foto vertical a la izquierda y lista con viñetas a la derecha."""
        p = self.planta
        fila = tk.Frame(vista, bg=FONDO_SECCION)
        fila.pack(fill="x", padx=36, pady=(2, 8))

        lienzo = tk.Canvas(fila, width=FOTO_ANCHO, height=FOTO_ALTO, bg=FONDO_SECCION,
                           highlightthickness=0)
        lienzo.pack(side="left")
        foto = foto_redondeada(p, FOTO_ANCHO, FOTO_RADIO, alto=FOTO_ALTO)
        if foto is not None:
            lienzo.create_image(0, 0, anchor="nw", image=foto)
        else:
            rectangulo_redondeado(lienzo, 0, 0, FOTO_ANCHO, FOTO_ALTO, FOTO_RADIO, FONDO_IMAGEN)
            dibujar_planta(lienzo, FOTO_ANCHO / 2, FOTO_ALTO - 14, 0.9)

        datos = tk.Frame(fila, bg=FONDO_SECCION)
        datos.pack(side="left", padx=(110, 0), anchor="n", pady=2)

        estado = p["estado_salud"].replace("_", " ").capitalize()
        items = [p["categoria"],
                 "Disponible" if p["disponible"] else "Agotada",
                 f"Precio: {dinero(p['precio'])}",
                 f"Cantidad: {p['cantidad']}",
                 f"Tamaño: {p['tamano'] or '—'}",
                 f"Estado de salud: {estado}"]
        for i, texto in enumerate(items):
            linea = tk.Frame(datos, bg=FONDO_SECCION)
            linea.pack(anchor="w")
            ultimo = i == len(items) - 1          # la última viñeta va en café
            tk.Label(linea, text="•", bg=FONDO_SECCION, fg=CAFE if ultimo else TEXTO,
                     font=(FUENTE, 12)).pack(side="left", padx=(0, 8))
            tk.Label(linea, text=texto, bg=FONDO_SECCION, fg=TEXTO,
                     font=(FUENTE, 12)).pack(side="left")

    def _crear_pestanas(self, vista):
        barra = tk.Frame(vista, bg=FONDO_SECCION)
        barra.pack(fill="x", padx=36, pady=(6, 6))
        for nombre in PESTANAS:
            etiqueta = tk.Label(barra, text=nombre, bg=FONDO_SECCION, fg=CAFE,
                                font=(FUENTE, 11), cursor="hand2")
            etiqueta.pack(side="left", expand=True)
            etiqueta.bind("<Button-1>", lambda e, n=nombre: self._mostrar_pestana(n))
            self.pestanas[nombre] = etiqueta

        self.texto_pestana = tk.Label(vista, bg=FONDO_SECCION, fg=TEXTO, font=(FUENTE, 10),
                                      wraplength=640, anchor="n")
        self.texto_pestana.pack(fill="x", padx=60, pady=(2, 0))

    def _crear_accion_carrito(self, vista):
        """Solo clientes: cantidad y 'Añadir al carrito'."""
        p = self.planta
        accion = tk.Frame(vista, bg=FONDO_SECCION)
        accion.pack(side="bottom", pady=8)
        tk.Label(accion, text="Cantidad", bg=FONDO_SECCION, fg=VERDE_OSCURO,
                 font=(FUENTE, 10)).pack(side="left")
        spin = tk.Spinbox(accion, from_=1, to=max(1, p["cantidad"]), width=5,
                          font=(FUENTE, 11), justify="center")
        spin.pack(side="left", padx=8)
        boton = tk.Button(accion, text="Añadir al carrito", bg=VERDE_OSCURO, fg=BLANCO,
                          relief="flat", cursor="hand2", padx=16, pady=4,
                          font=(FUENTE, 10, "bold"),
                          command=lambda: self.anadir_al_carrito(p, spin.get()))
        boton.pack(side="left", padx=10)
        if p["cantidad"] < 1:
            boton.config(state="disabled")

    def _contenido_pestana(self, nombre):
        """Devuelve (texto, centrado) de una pestaña; consulta la BD solo la primera vez."""
        if nombre in self.cache_pestanas:
            return self.cache_pestanas[nombre]
        p = self.planta
        try:
            if nombre == "Descripción":
                res = (p["descripcion"] or "Sin descripción registrada.", True)
            elif nombre == "Cuidados":
                res = (p["cuidados"] or "Sin cuidados registrados.", True)
            elif nombre == "Enfermedades frecuentes":
                filas = db.consultar(
                    """SELECT e.nombre, e.sintomas
                       FROM planta_enfermedad pe JOIN enfermedades e USING (id_enfermedad)
                       WHERE pe.id_planta = %s ORDER BY e.nombre""", (p["id_planta"],))
                lineas = [f"• {f['nombre']}" + (f": {f['sintomas']}" if f["sintomas"] else "")
                          for f in filas]
                res = ("\n".join(lineas) or "No hay enfermedades registradas para esta planta.",
                       not lineas)
            else:                                           # Plagas frecuentes
                filas = db.consultar(
                    """SELECT pl.nombre, pl.nivel_riesgo, pl.tratamiento
                       FROM planta_plaga pp JOIN plagas pl USING (id_plaga)
                       WHERE pp.id_planta = %s ORDER BY pl.nombre""", (p["id_planta"],))
                lineas = [f"• {f['nombre']} (riesgo {f['nivel_riesgo']})"
                          + (f": {f['tratamiento']}" if f["tratamiento"] else "")
                          for f in filas]
                res = ("\n".join(lineas) or "No hay plagas registradas para esta planta.",
                       not lineas)
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))
            return "No se pudo cargar la información.", True
        self.cache_pestanas[nombre] = res
        return res

    def _mostrar_pestana(self, nombre):
        for n, etiqueta in self.pestanas.items():
            etiqueta.config(font=(FUENTE, 11, "bold" if n == nombre else "normal"))
        texto, centrado = self._contenido_pestana(nombre)
        self.texto_pestana.config(text=texto, justify="center" if centrado else "left",
                                  anchor="n" if centrado else "nw")

    # ==================================================================
    # DIAPOSITIVA 6: agregar planta + lista de plantas
    # ==================================================================
    def mostrar_agregar(self):
        if not self.es_staff:
            messagebox.showwarning("Agregar planta", "Solo el personal puede agregar plantas.")
            return

        self.editando = None
        self.marcadas = set()
        self.marcador_activo = True
        vista = self._nueva_vista()

        self.var_categoria = tk.StringVar(self, value=CATEGORIA_VACIA)
        self.var_estado = tk.StringVar(self, value="Saludable")

        self._crear_formulario(vista)
        self._crear_panel_lista(vista)
        self._cargar_lista()

        for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(secuencia, self._rueda)
        self.rueda_activa = True

    # ---------------- Formulario (izquierda) ----------------
    def _pildora(self, vista, x, y, ancho, alto=24):
        """Fondo café con forma de píldora donde se coloca un campo."""
        lienzo = tk.Canvas(vista, width=ancho, height=alto, bg=FONDO_SECCION,
                           highlightthickness=0)
        lienzo.place(x=x, y=y)
        rectangulo_redondeado(lienzo, 0, 0, ancho, alto, alto // 2, CAFE)
        return lienzo

    def _etiqueta_campo(self, vista, x, y, texto):
        tk.Label(vista, text=texto, bg=FONDO_SECCION, fg=TEXTO,
                 font=(FUENTE, 9)).place(x=x, y=y)

    def _campo_texto(self, vista, x, y, ancho, texto):
        self._etiqueta_campo(vista, x, y, texto)
        lienzo = self._pildora(vista, x, y + 18, ancho)
        entrada = tk.Entry(lienzo, bd=0, bg=CAFE, fg=BLANCO, insertbackground=BLANCO,
                           relief="flat", highlightthickness=0, font=(FUENTE, 10))
        lienzo.create_window(ancho / 2, 12, window=entrada, width=ancho - 24)
        return entrada

    def _campo_selector(self, vista, x, y, ancho, texto, variable, opciones):
        """Lista desplegable con el mismo aspecto de píldora."""
        self._etiqueta_campo(vista, x, y, texto)
        lienzo = self._pildora(vista, x, y + 18, ancho)
        boton = tk.Menubutton(lienzo, textvariable=variable, bg=CAFE, fg=BLANCO,
                              activebackground=CAFE, activeforeground=BLANCO,
                              relief="flat", bd=0, highlightthickness=0, anchor="w",
                              cursor="hand2", font=(FUENTE, 10))
        menu = tk.Menu(boton, tearoff=0, font=(FUENTE, 10),
                       activebackground=CAFE, activeforeground=BLANCO)
        for opcion in opciones:
            menu.add_radiobutton(label=opcion, variable=variable, value=opcion)
        boton.config(menu=menu)
        lienzo.create_window(ancho / 2 - 8, 12, window=boton, width=ancho - 40, height=20)
        lienzo.create_text(ancho - 14, 12, text="▾", fill=BLANCO, font=(FUENTE, 10))

    def _crear_formulario(self, vista):
        self.lbl_titulo_form = tk.Label(vista, text="Agregar planta", bg=FONDO_SECCION,
                                        fg=CAFE, font=(FUENTE, 20, "bold"))
        self.lbl_titulo_form.place(x=24, y=2)

        self.lbl_cancelar = tk.Label(vista, text="Cancelar edición", bg=FONDO_SECCION,
                                     fg=VERDE_OSCURO, font=(FUENTE, 9, "underline"),
                                     cursor="hand2")
        self.lbl_cancelar.bind("<Button-1>", lambda e: self._limpiar_formulario())

        self.e_nombre = self._campo_texto(vista, 24, 40, 380, "Nombre común")
        self.e_cientifico = self._campo_texto(vista, 24, 88, 380, "Nombre científico")
        self._campo_selector(vista, 24, 136, 380, "Categoría", self.var_categoria,
                             [c["nombre"] for c in self.categorias])
        self.e_precio = self._campo_texto(vista, 24, 184, 176, "Precio")
        self.e_cantidad = self._campo_texto(vista, 228, 184, 176, "Cantidad disponible")
        self.e_tamano = self._campo_texto(vista, 24, 232, 176, "Tamaño (cm)")
        self._campo_selector(vista, 228, 232, 176, "Estado de salud", self.var_estado,
                             list(ESTADOS))

        self._etiqueta_campo(vista, 24, 280, "Descripción")
        lienzo = tk.Canvas(vista, width=380, height=74, bg=FONDO_SECCION, highlightthickness=0)
        lienzo.place(x=24, y=298)
        rectangulo_redondeado(lienzo, 0, 0, 380, 74, 24, CAFE)
        self.e_desc = tk.Text(lienzo, bd=0, bg=CAFE, fg=BLANCO, insertbackground=BLANCO,
                              relief="flat", highlightthickness=0, wrap="word",
                              font=(FUENTE, 10))
        lienzo.create_window(190, 37, window=self.e_desc, width=330, height=52)

        # Botón AGREGAR PLANTA / GUARDAR CAMBIOS
        self.lienzo_boton = tk.Canvas(vista, width=260, height=34, bg=FONDO_SECCION,
                                      highlightthickness=0, cursor="hand2")
        self.lienzo_boton.place(x=84, y=388)
        fondo = rectangulo_redondeado(self.lienzo_boton, 0, 0, 260, 34, 17, CAFE)
        self.texto_boton = self.lienzo_boton.create_text(
            130, 17, text="AGREGAR PLANTA", fill=BLANCO, font=(FUENTE, 11))
        self.lienzo_boton.bind("<Button-1>", lambda e: self._guardar())
        self.lienzo_boton.bind("<Enter>", lambda e: self.lienzo_boton.itemconfig(
            fondo, fill=CAFE_HOVER, outline=CAFE_HOVER))
        self.lienzo_boton.bind("<Leave>", lambda e: self.lienzo_boton.itemconfig(
            fondo, fill=CAFE, outline=CAFE))

    def _limpiar_formulario(self):
        self.editando = None
        for entrada in (self.e_nombre, self.e_cientifico, self.e_precio,
                        self.e_cantidad, self.e_tamano):
            entrada.delete(0, tk.END)
        self.e_desc.delete("1.0", tk.END)
        self.var_categoria.set(CATEGORIA_VACIA)
        self.var_estado.set("Saludable")
        self.lbl_titulo_form.config(text="Agregar planta")
        self.lienzo_boton.itemconfig(self.texto_boton, text="AGREGAR PLANTA")
        self.lbl_cancelar.place_forget()
        self.e_nombre.focus_set()

    @staticmethod
    def _poner(entrada, texto):
        entrada.delete(0, tk.END)
        entrada.insert(0, texto)

    # ---------------- Validación y guardado ----------------
    def _validar_planta(self):
        """Devuelve (datos, None) con la tupla lista para SQL, o (None, mensaje)."""
        nombre = self.e_nombre.get().strip()
        cientifico = self.e_cientifico.get().strip()
        categoria = self.var_categoria.get()
        precio_txt = self.e_precio.get().strip().replace(",", "")
        cantidad_txt = self.e_cantidad.get().strip()
        tamano_txt = self.e_tamano.get().strip().replace(",", ".")
        estado = ESTADOS.get(self.var_estado.get())
        descripcion = self.e_desc.get("1.0", "end").strip()

        categorias = {c["nombre"]: c["id_categoria"] for c in self.categorias}

        if not nombre:
            return None, "Escribe el nombre común de la planta."
        if len(nombre) > 100:
            return None, "El nombre común no puede pasar de 100 caracteres."
        if len(cientifico) > 150:
            return None, "El nombre científico no puede pasar de 150 caracteres."
        if categoria not in categorias:
            return None, "Selecciona una categoría."

        try:
            precio = Decimal(precio_txt)
        except InvalidOperation:
            return None, "El precio debe ser un número."
        if not precio.is_finite() or precio < 0 or precio > Decimal("99999999.99"):
            return None, "El precio debe estar entre 0 y 99,999,999.99."
        precio = precio.quantize(Decimal("0.01"))

        if not cantidad_txt.isdigit() or int(cantidad_txt) > 2147483647:
            return None, "La cantidad debe ser un número entero (0 o más)."
        cantidad = int(cantidad_txt)

        tamano = None
        if tamano_txt:
            try:
                valor = Decimal(tamano_txt)
            except InvalidOperation:
                return None, "El tamaño debe ser un número (en centímetros)."
            if not valor.is_finite() or valor <= 0 or valor > Decimal("100000"):
                return None, "El tamaño debe ser mayor que 0."
            tamano = f"{format(valor.normalize(), 'f')} cm"

        return (nombre, cientifico or None, categorias[categoria], precio, cantidad,
                tamano, estado, descripcion or None), None

    def _guardar(self):
        datos, error = self._validar_planta()
        if error:
            messagebox.showwarning("Planta", error)
            return
        try:
            if self.editando is None:
                db.ejecutar(
                    """INSERT INTO plantas (nombre_comun, nombre_cientifico, id_categoria,
                                            precio, cantidad, tamano, estado_salud, descripcion)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", datos)
                mensaje = "La planta se agregó correctamente."
            else:
                db.ejecutar(
                    """UPDATE plantas
                       SET nombre_comun = %s, nombre_cientifico = %s, id_categoria = %s,
                           precio = %s, cantidad = %s, tamano = %s, estado_salud = %s,
                           descripcion = %s, fecha_actualizacion = CURRENT_TIMESTAMP
                       WHERE id_planta = %s""", datos + (self.editando,))
                mensaje = "Los cambios se guardaron."
        except psycopg2.errors.UniqueViolation:
            messagebox.showwarning("Planta repetida",
                                   "Ya existe una planta con ese nombre y tamaño.")
            return
        except psycopg2.errors.ForeignKeyViolation:
            messagebox.showwarning(
                "Categoría no válida",
                "No se puede cambiar la categoría: la planta tiene plagas asociadas "
                "que no afectan a la nueva categoría.")
            return
        except Exception as e:
            messagebox.showerror("Error de base de datos", f"No se pudo guardar:\n{e}")
            return

        messagebox.showinfo("Planta", mensaje)
        self._limpiar_formulario()
        self._cargar_lista()

    # ---------------- Panel con la lista (derecha) ----------------
    def _crear_panel_lista(self, vista):
        ancho, alto = 545, 424
        fondo = tk.Canvas(vista, width=ancho, height=alto, bg=FONDO_SECCION,
                          highlightthickness=0)
        fondo.place(x=440, y=8)
        rectangulo_redondeado(fondo, 0, 0, ancho, alto, 28, VERDE_OSCURO)

        # Buscador con lupa
        buscador = tk.Canvas(fondo, width=513, height=26, bg=VERDE_OSCURO, highlightthickness=0)
        fondo.create_window(16, 12, window=buscador, anchor="nw")
        rectangulo_redondeado(buscador, 0, 0, 513, 26, 13, VERDE_BUSCADOR)
        buscador.create_oval(18, 6, 29, 17, outline=TEXTO_CLARO, width=2)
        buscador.create_line(28, 16, 34, 22, fill=TEXTO_CLARO, width=2)
        self.busqueda = tk.Entry(buscador, bd=0, bg=VERDE_BUSCADOR, fg=TEXTO_CLARO,
                                 insertbackground=TEXTO_CLARO, justify="center",
                                 relief="flat", highlightthickness=0, font=(FUENTE, 9))
        buscador.create_window(256, 13, window=self.busqueda, width=380)
        self._poner_marcador()
        self.busqueda.bind("<FocusIn>", self._al_enfocar_busqueda)
        self.busqueda.bind("<FocusOut>", self._al_desenfocar_busqueda)
        self.busqueda.bind("<KeyRelease>", lambda e: self._programar_busqueda())

        # Título de la lista y "eliminar seleccionado"
        fondo.create_text(20, 58, text="Lista de plantas", anchor="w", fill=TEXTO_CLARO,
                          font=(FUENTE, 10, "bold"))
        eliminar = fondo.create_text(ancho - 20, 58, text="eliminar seleccionado",
                                     anchor="e", fill=TEXTO_CLARO, font=(FUENTE, 10, "bold"))
        fondo.tag_bind(eliminar, "<Button-1>", lambda e: self._eliminar_seleccionadas())
        fondo.tag_bind(eliminar, "<Enter>", lambda e: fondo.config(cursor="hand2"))
        fondo.tag_bind(eliminar, "<Leave>", lambda e: fondo.config(cursor=""))

        # Encabezados de columnas
        fondo.create_text(116, 84, text="informacion", anchor="w", fill=TEXTO_CLARO,
                          font=(FUENTE, 9, "bold"))
        fondo.create_text(370, 84, text="Cantidad", fill=TEXTO_CLARO, font=(FUENTE, 9, "bold"))
        fondo.create_text(471, 84, text="Acciones", fill=TEXTO_CLARO, font=(FUENTE, 9, "bold"))

        # Zona con desplazamiento
        self.contenedor_lista = tk.Frame(fondo, bg=VERDE_OSCURO)
        fondo.create_window(8, 98, window=self.contenedor_lista, anchor="nw",
                            width=529, height=316)
        self.lienzo_lista = tk.Canvas(self.contenedor_lista, bg=VERDE_OSCURO,
                                      highlightthickness=0)
        barra = tk.Scrollbar(self.contenedor_lista, orient="vertical",
                             command=self.lienzo_lista.yview, bg=VERDE_BUSCADOR,
                             troughcolor=VERDE_OSCURO, activebackground=VERDE_BUSCADOR,
                             bd=0, width=10, relief="flat")
        self.lienzo_lista.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y")
        self.lienzo_lista.pack(side="left", fill="both", expand=True)

        self.interior = tk.Frame(self.lienzo_lista, bg=VERDE_OSCURO)
        self.lienzo_lista.create_window(0, 0, window=self.interior, anchor="nw", width=505)
        self.interior.bind("<Configure>", lambda e: self.lienzo_lista.configure(
            scrollregion=self.lienzo_lista.bbox("all")))

    def _rueda(self, evento):
        """Desplaza la lista con la rueda del mouse solo si el puntero está sobre ella."""
        try:
            destino = self.winfo_containing(evento.x_root, evento.y_root)
            if destino is None or not str(destino).startswith(str(self.contenedor_lista)):
                return
            if evento.num == 4:
                paso = -1
            elif evento.num == 5:
                paso = 1
            else:
                paso = -1 if evento.delta > 0 else 1
            self.lienzo_lista.yview_scroll(paso, "units")
        except (tk.TclError, KeyError):
            pass

    # ---------------- Buscador ----------------
    def _poner_marcador(self):
        self.marcador_activo = True
        self.busqueda.delete(0, tk.END)
        self.busqueda.insert(0, "Buscar Planta")

    def _al_enfocar_busqueda(self, _):
        if self.marcador_activo:
            self.busqueda.delete(0, tk.END)
            self.marcador_activo = False

    def _al_desenfocar_busqueda(self, _):
        if not self.busqueda.get():
            self._poner_marcador()

    def _texto_busqueda(self):
        return "" if self.marcador_activo else self.busqueda.get().strip()

    def _programar_busqueda(self):
        """Espera un instante tras la última tecla para no consultar en cada letra."""
        if self.trabajo_busqueda is not None:
            self.after_cancel(self.trabajo_busqueda)
        self.trabajo_busqueda = self.after(250, self._ejecutar_busqueda)

    def _ejecutar_busqueda(self):
        self.trabajo_busqueda = None
        if self.interior is None or not self.interior.winfo_exists():
            return
        self._cargar_lista()

    # ---------------- Datos y filas ----------------
    def _cargar_lista(self):
        sql = """SELECT p.id_planta, p.nombre_comun, p.nombre_cientifico, p.id_categoria,
                        c.nombre AS categoria, p.precio, p.cantidad, p.tamano,
                        p.estado_salud, p.descripcion
                 FROM plantas p JOIN categorias c ON c.id_categoria = p.id_categoria"""
        params = []
        texto = self._texto_busqueda()
        if texto:
            sql += (" WHERE p.nombre_comun ILIKE %s OR p.nombre_cientifico ILIKE %s"
                    " OR c.nombre ILIKE %s")
            params = [f"%{texto}%"] * 3
        sql += " ORDER BY p.nombre_comun"
        try:
            self.lista = db.consultar(sql, params)
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))
            self.lista = []
        self._dibujar_lista()

    def _dibujar_lista(self):
        for hijo in self.interior.winfo_children():
            hijo.destroy()
        if not self.lista:
            tk.Label(self.interior, text="No hay plantas registradas.", bg=VERDE_OSCURO,
                     fg=TEXTO_CLARO, font=(FUENTE, 11)).pack(pady=40)
        for p in self.lista:
            self._crear_fila(self.interior, p)
        self.lienzo_lista.yview_moveto(0)

    def _crear_fila(self, padre, p):
        fila = tk.Frame(padre, bg=VERDE_OSCURO, height=ALTO_FILA)
        fila.pack(fill="x")
        fila.pack_propagate(False)
        medio = ALTO_FILA / 2

        # Casilla de selección
        marca = tk.Label(fila, text="☑" if p["id_planta"] in self.marcadas else "☐",
                         bg=VERDE_OSCURO, fg=TEXTO_CLARO, font=(FUENTE, 16), cursor="hand2")
        marca.place(x=4, y=medio, anchor="w")
        marca.bind("<Button-1>", lambda e, i=p["id_planta"], m=marca: self._alternar_marca(i, m))

        # Miniatura
        lienzo = tk.Canvas(fila, width=MINIATURA, height=MINIATURA, bg=VERDE_OSCURO,
                           highlightthickness=0)
        lienzo.place(x=34, y=(ALTO_FILA - MINIATURA) / 2)
        foto = foto_redondeada(p, MINIATURA, MINIATURA_RADIO)
        if foto is not None:
            lienzo.create_image(0, 0, anchor="nw", image=foto)
        else:
            rectangulo_redondeado(lienzo, 0, 0, MINIATURA, MINIATURA, MINIATURA_RADIO,
                                  FONDO_IMAGEN)
            dibujar_planta(lienzo, MINIATURA / 2, MINIATURA - 6, 0.45)

        # Información
        estado = ESTADOS_INV.get(p["estado_salud"], p["estado_salud"]).lower()
        tk.Label(fila, text=p["nombre_comun"], bg=VERDE_OSCURO, fg=BLANCO,
                 font=(FUENTE, 10, "bold"), anchor="w").place(x=104, y=6)
        tk.Label(fila, text=f"{p['categoria']}\n{dinero(p['precio'])}\nestado: {estado}",
                 bg=VERDE_OSCURO, fg=TEXTO_CLARO, font=(FUENTE, 9), justify="left",
                 anchor="w").place(x=104, y=24)

        # Cantidad
        tk.Label(fila, text=str(p["cantidad"]), bg=VERDE_OSCURO, fg=TEXTO_CLARO,
                 font=(FUENTE, 10)).place(x=362, y=medio, anchor="center")

        # Acciones
        editar = tk.Canvas(fila, width=20, height=20, bg=VERDE_OSCURO,
                           highlightthickness=0, cursor="hand2")
        editar.place(x=442, y=medio, anchor="center")
        icono_editar(editar)
        editar.bind("<Button-1>", lambda e, pl=p: self._editar(pl))

        borrar = tk.Canvas(fila, width=20, height=20, bg=VERDE_OSCURO,
                           highlightthickness=0, cursor="hand2")
        borrar.place(x=484, y=medio, anchor="center")
        icono_papelera(borrar)
        borrar.bind("<Button-1>", lambda e, pl=p: self._eliminar([(pl["id_planta"], pl["nombre_comun"])]))

        # Línea separadora
        tk.Frame(padre, bg=VERDE_BUSCADOR, height=1).pack(fill="x", padx=8)

    def _alternar_marca(self, id_planta, etiqueta):
        if id_planta in self.marcadas:
            self.marcadas.discard(id_planta)
            etiqueta.config(text="☐")
        else:
            self.marcadas.add(id_planta)
            etiqueta.config(text="☑")

    # ---------------- Acciones: editar y eliminar ----------------
    def _editar(self, p):
        """Carga la planta en el formulario; el botón pasa a 'GUARDAR CAMBIOS'."""
        self.editando = p["id_planta"]
        self._poner(self.e_nombre, p["nombre_comun"])
        self._poner(self.e_cientifico, p["nombre_cientifico"] or "")
        self.var_categoria.set(p["categoria"])
        self._poner(self.e_precio, f"{p['precio']:.2f}")
        self._poner(self.e_cantidad, str(p["cantidad"]))
        self._poner(self.e_tamano, (p["tamano"] or "").lower().replace("cm", "").strip())
        self.var_estado.set(ESTADOS_INV.get(p["estado_salud"], "Saludable"))
        self.e_desc.delete("1.0", tk.END)
        self.e_desc.insert("1.0", p["descripcion"] or "")

        self.lbl_titulo_form.config(text="Editar planta")
        self.lienzo_boton.itemconfig(self.texto_boton, text="GUARDAR CAMBIOS")
        self.lbl_cancelar.place(x=290, y=12)
        self.e_nombre.focus_set()

    def _eliminar_seleccionadas(self):
        objetivos = [(p["id_planta"], p["nombre_comun"]) for p in self.lista
                     if p["id_planta"] in self.marcadas]
        if not objetivos:
            messagebox.showinfo("Eliminar", "Marca con la casilla las plantas que quieras eliminar.")
            return
        self._eliminar(objetivos)

    def _eliminar(self, objetivos):
        """objetivos: lista de (id_planta, nombre). Pide confirmación antes de borrar."""
        nombres = "\n".join(f"• {n}" for _, n in objetivos[:10])
        if len(objetivos) > 10:
            nombres += "\n…"
        if not messagebox.askyesno(
                "Eliminar",
                f"¿Eliminar {len(objetivos)} planta(s)?\n\n{nombres}\n\n"
                "Esta acción no se puede deshacer."):
            return

        con_ventas = []
        for id_planta, nombre in objetivos:
            try:
                db.ejecutar("DELETE FROM plantas WHERE id_planta = %s", (id_planta,))
            except psycopg2.errors.ForeignKeyViolation:
                con_ventas.append(nombre)
                continue
            except Exception as e:
                messagebox.showerror("Error de base de datos", f"No se pudo eliminar:\n{e}")
                break
            self.marcadas.discard(id_planta)
            if self.editando == id_planta:
                self._limpiar_formulario()

        self._cargar_lista()
        if con_ventas:
            messagebox.showwarning(
                "No se pudo eliminar",
                "Estas plantas tienen ventas registradas y no se pueden borrar:\n\n"
                + "\n".join(f"• {n}" for n in con_ventas)
                + "\n\nPon su cantidad en 0 para que dejen de aparecer en el catálogo.")