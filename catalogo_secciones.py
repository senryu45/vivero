"""Diap. 7: CATALOGO por secciones  ·  Diap. 8: gestión (alta/edición/baja) de secciones."""
import math
import os
import tkinter as tk
from tkinter import messagebox

import psycopg2.errors

import catalogo
import db
from catalogo import (VERDE_OSCURO, VERDE_BUSCADOR, FONDO_SECCION, FONDO_IMAGEN, CAFE,
                      CAFE_HOVER, BLANCO, TEXTO, TEXTO_CLARO, FUENTE, CARPETA_IMAGENES,
                      EXTENSIONES, _slug, dinero, rectangulo_redondeado, dibujar_planta,
                      icono_editar, icono_papelera, foto_redondeada, enlazar_clic)

ROJO = "#C8553D"

ANCHO_CELDA, ALTO_CELDA = 150, 138
LADO, RADIO = 96, 18
POR_PAGINA = 6               # una fila de 6 tarjetas por página
ALTO_FILA = 78
ICONO_W, ICONO_H = 100, 90   # tamaño "virtual" en el que se dibujan los íconos


# ==================================================================================
#                         Íconos de las secciones (vectoriales)
# ==================================================================================
def _icono_medicinales(c):
    """Sansevieria en maceta."""
    cx = 50
    for dx, punta, y in ((-15, -20, 16), (-5, -6, 6), (6, 8, 10), (16, 22, 24)):
        x = cx + dx
        c.create_polygon(x - 6, 58, x - 8, 40, cx + punta, y, x + 8, 40, x + 6, 58,
                         fill="#4E8A3E", outline="#C9D77A", width=2)
    c.create_polygon(cx - 20, 56, cx + 20, 56, cx + 16, 86, cx - 16, 86,
                     fill="#9A5A3C", outline="#6B3E28")
    c.create_rectangle(cx - 23, 52, cx + 23, 60, fill="#B9714A", outline="#6B3E28")
    for y in (67, 76):
        c.create_line(cx - 17, y, cx + 17, y, fill="#6B3E28", width=2)


def _icono_frutales(c):
    """Canasta con frutas y una piña."""
    cx = 50
    c.create_oval(cx - 7, 22, cx + 11, 52, fill="#F2B632", outline="#C98F12")
    c.create_polygon(cx + 2, 24, cx - 6, 8, cx + 1, 15, cx + 3, 3, cx + 8, 15, cx + 16, 8,
                     fill="#4E9A3A", outline="")
    c.create_rectangle(cx - 32, 56, cx + 32, 86, fill="#E8B37A", outline="#B07A45")
    for fila in range(3):
        for col in range(8):
            if (fila + col) % 2 == 0:
                x1 = cx - 32 + col * 8
                c.create_rectangle(x1, 56 + fila * 10, x1 + 8, 66 + fila * 10,
                                   fill="#C98A52", outline="")
    for x, y, r, color in ((cx - 24, 52, 9, "#F28C28"), (cx - 9, 55, 9, "#D9363E"),
                           (cx + 9, 56, 8, "#5B2A86"), (cx + 25, 52, 9, "#F6A03B")):
        c.create_oval(x - r, y - r, x + r, y + r, fill=color, outline="")


def _icono_arboreas(c):
    """Árbol de copa redondeada."""
    cx = 50
    c.create_polygon(cx - 5, 86, cx - 4, 56, cx - 14, 42, cx - 8, 42, cx, 54, cx + 8, 40,
                     cx + 14, 42, cx + 4, 56, cx + 5, 86, fill="#8A5A3C", outline="")
    for x, y, r in ((cx, 26, 19), (cx - 19, 40, 15), (cx + 19, 40, 15),
                    (cx - 6, 46, 13), (cx + 8, 48, 12)):
        c.create_oval(x - r, y - r, x + r, y + r, fill="#6FA84E", outline="")
    for x in (cx - 18, cx + 18):
        c.create_line(x, 86, x, 80, fill="#5B9040", width=2)
        c.create_line(x, 86, x + 5, 81, fill="#5B9040", width=2)


def _icono_florales(c):
    """Flor rosa de cinco pétalos."""
    cx, cy = 50, 46
    for i in range(5):
        a = math.radians(-90 + 72 * i)
        x, y = cx + 17 * math.cos(a), cy + 17 * math.sin(a)
        c.create_oval(x - 14, y - 14, x + 14, y + 14, fill="#FF4FA3", outline="#E03385")
    c.create_oval(cx - 9, cy - 9, cx + 9, cy + 9, fill="#FFC531", outline="")


def _icono_generico(c):
    dibujar_planta(c, 50, 80, 0.9)


ICONOS = (("medicin", _icono_medicinales), ("frut", _icono_frutales),
          ("arbor", _icono_arboreas), ("flor", _icono_florales))
_cache_iconos = {}


def _imagen_seccion(nombre, ancho, alto):
    """Busca imagenes/secciones/<nombre>.png|jpg... Devuelve PhotoImage o None."""
    base = _slug(nombre)
    for ext in EXTENSIONES:
        ruta = os.path.join(CARPETA_IMAGENES, "secciones", base + ext)
        if os.path.exists(ruta):
            break
    else:
        return None
    clave = (ruta, ancho, alto)
    if clave not in _cache_iconos:
        try:
            from PIL import Image, ImageTk
            imagen = Image.open(ruta).convert("RGBA")
            imagen.thumbnail((ancho, alto), Image.LANCZOS)
            _cache_iconos[clave] = ImageTk.PhotoImage(imagen)
        except Exception:
            return None                      # sin Pillow o imagen inválida
    return _cache_iconos[clave]


def dibujar_icono_seccion(canvas, nombre, ancho, alto):
    """Imagen propia de la sección si existe; si no, ilustración vectorial por nombre."""
    canvas.delete("all")
    foto = _imagen_seccion(nombre, ancho, alto)
    if foto is not None:
        canvas.create_image(ancho / 2, alto / 2, image=foto)
        return
    clave = _slug(nombre)
    dibujar = next((f for prefijo, f in ICONOS if clave.startswith(prefijo)), _icono_generico)
    dibujar(canvas)
    k = min(ancho / ICONO_W, alto / ICONO_H)
    canvas.scale("all", 0, 0, k, k)
    canvas.move("all", (ancho - ICONO_W * k) / 2, (alto - ICONO_H * k) / 2)


# ==================================================================================
#                               DIAPOSITIVA 7
# ==================================================================================
class CatalogoSecciones(tk.Frame):
    """Pestañas por sección (categoría) con su ícono y, debajo, las plantas de esa sección.

    - Personal: ve todas las plantas y el enlace '+ Agregar sección'.
    - Cliente: solo ve plantas con existencias.
    - Clic en una planta: abre su ficha (con 'Añadir al carrito' para clientes).
    """

    def __init__(self, master, datos=None):
        super().__init__(master, bg=FONDO_SECCION)
        self.datos = datos
        self.es_staff = (datos is None) or datos["rol"] in ("admin", "vendedor")

        self.carrito = {}            # se comparte con las fichas para no perderlo al volver
        self.categorias = []
        self.id_seccion = None       # categoría activa
        self.plantas = []
        self.pagina = 0
        self.formulario = None       # capa de la diap. 8
        self.ficha = None            # capa de la ficha de planta

        self._crear_cabecera()
        self.marco_tabs = tk.Frame(self, bg=FONDO_SECCION)
        self.marco_tabs.pack(fill="x", padx=28, pady=(8, 4))
        self._crear_paginador()      # va abajo: se empaqueta antes que la zona
        self.zona = tk.Frame(self, bg=FONDO_SECCION)
        self.zona.pack(fill="both", expand=True, padx=12)

        self.cargar_datos()

    # ---------------- Construcción de la interfaz ----------------
    def _crear_cabecera(self):
        fila = tk.Frame(self, bg=FONDO_SECCION)
        fila.pack(fill="x", padx=28, pady=(8, 0))
        tk.Label(fila, text="CATÁLOGO", bg=FONDO_SECCION, fg=CAFE,
                 font=(FUENTE, 24, "bold")).pack(side="left")
        if self.es_staff:
            agregar = tk.Label(fila, text="+ Agregar sección", bg=FONDO_SECCION, fg=CAFE,
                               font=(FUENTE, 15), cursor="hand2")
            agregar.pack(side="right", padx=(0, 20))
            agregar.bind("<Button-1>", lambda e: self._abrir_formulario())
            agregar.bind("<Enter>", lambda e: agregar.config(fg=CAFE_HOVER))
            agregar.bind("<Leave>", lambda e: agregar.config(fg=CAFE))

    def _crear_paginador(self):
        pie = tk.Frame(self, bg=FONDO_SECCION)
        pie.pack(side="bottom", fill="x", padx=28, pady=4)
        self.btn_ant = tk.Button(pie, text="◀ Anterior", command=lambda: self._cambiar_pagina(-1),
                                 bg=VERDE_OSCURO, fg=BLANCO, relief="flat", padx=10,
                                 font=(FUENTE, 9))
        self.btn_ant.pack(side="left")
        self.lbl_pagina = tk.Label(pie, bg=FONDO_SECCION, fg=VERDE_OSCURO, font=(FUENTE, 10))
        self.lbl_pagina.pack(side="left", padx=14)
        self.btn_sig = tk.Button(pie, text="Siguiente ▶", command=lambda: self._cambiar_pagina(1),
                                 bg=VERDE_OSCURO, fg=BLANCO, relief="flat", padx=10,
                                 font=(FUENTE, 9))
        self.btn_sig.pack(side="left")

    # ---------------- Datos ----------------
    def cargar_datos(self):
        """Lee las secciones, conserva la activa si sigue existiendo y redibuja todo."""
        try:
            self.categorias = db.consultar(
                "SELECT id_categoria, nombre, descripcion FROM categorias ORDER BY id_categoria")
        except Exception as e:
            messagebox.showerror("Error de base de datos",
                                 f"No se pudieron cargar las secciones:\n{e}")
            self.categorias = []

        ids = [c["id_categoria"] for c in self.categorias]
        if self.id_seccion not in ids:
            self.id_seccion = ids[0] if ids else None
            self.pagina = 0
        self._dibujar_tabs()
        self._cargar_plantas()
        self._dibujar_pagina()

    def _cargar_plantas(self):
        """Plantas de la sección activa. El cliente solo ve las que tienen existencias."""
        self.plantas = []
        if self.id_seccion is None:
            return
        sql = """SELECT id_planta, nombre_comun, precio, cantidad, disponible
                 FROM plantas WHERE id_categoria = %s"""
        if not self.es_staff:
            sql += " AND disponible"
        sql += " ORDER BY nombre_comun"
        try:
            self.plantas = db.consultar(sql, (self.id_seccion,))
        except Exception as e:
            messagebox.showerror("Error de base de datos", f"Error al cargar las plantas:\n{e}")

    # ---------------- Pestañas ----------------
    def _dibujar_tabs(self):
        for h in self.marco_tabs.winfo_children():
            h.destroy()
        if not self.categorias:
            texto = "No hay secciones registradas."
            if self.es_staff:
                texto += " Usa «+ Agregar sección» para crear la primera."
            tk.Label(self.marco_tabs, text=texto, bg=FONDO_SECCION, fg=TEXTO,
                     font=(FUENTE, 12, "italic")).pack(pady=20)
            return

        interior = tk.Frame(self.marco_tabs, bg=FONDO_SECCION)
        interior.pack()                                     # centrado
        tam = 18 if len(self.categorias) <= 5 else 13
        for cat in self.categorias:
            activa = cat["id_categoria"] == self.id_seccion
            tab = tk.Frame(interior, bg=FONDO_SECCION)
            tab.pack(side="left", padx=18)
            tk.Label(tab, text=cat["nombre"], bg=FONDO_SECCION, fg=CAFE,
                     font=(FUENTE, tam, "bold underline" if activa else "bold")).pack()
            lienzo = tk.Canvas(tab, width=100, height=80, bg=FONDO_SECCION,
                               highlightthickness=0)
            lienzo.pack(pady=(4, 0))
            dibujar_icono_seccion(lienzo, cat["nombre"], 100, 80)
            enlazar_clic(tab, lambda i=cat["id_categoria"]: self._elegir(i))

    def _elegir(self, id_categoria):
        self.id_seccion = id_categoria
        self.pagina = 0
        self._dibujar_tabs()
        self._cargar_plantas()
        self._dibujar_pagina()

    # ---------------- Cuadrícula de plantas ----------------
    def _cambiar_pagina(self, delta):
        self.pagina += delta
        self._dibujar_pagina()

    def _dibujar_pagina(self):
        for h in self.zona.winfo_children():
            h.destroy()

        total = len(self.plantas)
        paginas = max(1, -(-total // POR_PAGINA))
        self.pagina = max(0, min(self.pagina, paginas - 1))
        visibles = self.plantas[self.pagina * POR_PAGINA:(self.pagina + 1) * POR_PAGINA]

        if self.categorias and not visibles:
            tk.Label(self.zona, text="No hay plantas registradas en esta sección.",
                     bg=FONDO_SECCION, fg=VERDE_OSCURO,
                     font=(FUENTE, 12, "italic")).pack(pady=30)
        elif visibles:
            fila = tk.Frame(self.zona, bg=FONDO_SECCION)
            fila.pack(pady=6)
            for p in visibles:
                self._crear_celda(fila, p).pack(side="left", padx=3)

        self.lbl_pagina.config(
            text=f"Página {self.pagina + 1} de {paginas} · {total} planta(s)" if total else "")
        self.btn_ant.config(state="normal" if self.pagina > 0 else "disabled")
        self.btn_sig.config(state="normal" if self.pagina < paginas - 1 else "disabled")

    def _crear_celda(self, padre, p):
        celda = tk.Frame(padre, bg=FONDO_SECCION, width=ANCHO_CELDA, height=ALTO_CELDA)
        celda.pack_propagate(False)

        lienzo = tk.Canvas(celda, width=LADO, height=LADO, bg=FONDO_SECCION,
                           highlightthickness=0)
        lienzo.pack(pady=(2, 4))
        foto = foto_redondeada(p, LADO, RADIO)
        if foto is not None:
            lienzo.create_image(0, 0, anchor="nw", image=foto)
        else:
            rectangulo_redondeado(lienzo, 0, 0, LADO, LADO, RADIO, FONDO_IMAGEN)
            dibujar_planta(lienzo, LADO / 2, LADO - 10, 0.8)

        disponible = p["cantidad"] > 0
        tk.Label(celda, text=p["nombre_comun"], bg=FONDO_SECCION, fg=TEXTO,
                 font=(FUENTE, 10), wraplength=ANCHO_CELDA - 8).pack()
        tk.Label(celda, text=dinero(p["precio"]), bg=FONDO_SECCION, fg=TEXTO,
                 font=(FUENTE, 9)).pack()
        tk.Label(celda, text="Disponible" if disponible else "Agotado", bg=FONDO_SECCION,
                 fg=TEXTO if disponible else ROJO, font=(FUENTE, 9, "bold")).pack()

        enlazar_clic(celda, lambda i=p["id_planta"]: self._abrir_ficha(i))
        return celda

    # ---------------- Capas: ficha de planta y diap. 8 ----------------
    def _abrir_ficha(self, id_planta):
        if self.ficha is not None:
            return
        self.ficha = catalogo.Catalogo(self, self.datos, al_volver=self._cerrar_ficha,
                                       carrito=self.carrito, id_inicial=id_planta)
        self.ficha.place(x=0, y=0, relwidth=1, relheight=1)

    def _cerrar_ficha(self):
        if self.ficha is not None:
            self.ficha.destroy()
            self.ficha = None

    def _abrir_formulario(self):
        if self.formulario is not None:
            return
        self.formulario = AgregarSeccion(self, self.datos, al_volver=self._cerrar_formulario)
        self.formulario.place(x=0, y=0, relwidth=1, relheight=1)

    def _cerrar_formulario(self):
        if self.formulario is not None:
            self.formulario.destroy()
            self.formulario = None
        self.cargar_datos()          # refleja las secciones agregadas, editadas o eliminadas


# ==================================================================================
#                               DIAPOSITIVA 8
# ==================================================================================
class AgregarSeccion(tk.Frame):
    """Formulario de alta/edición de secciones + lista con editar y eliminar.

    al_volver() cierra esta capa y regresa al catálogo.
    Requiere la columna categorias.tipo_plantas (ver ALTER TABLE).
    """

    def __init__(self, master, datos=None, al_volver=None):
        super().__init__(master, bg=FONDO_SECCION)
        self.datos = datos
        self.al_volver = al_volver
        self.editando_id = None
        self.marcadas = set()
        self.lista_secciones = []

        izq = tk.Frame(self, bg=FONDO_SECCION)
        izq.place(x=0, y=0, width=420, height=490)

        lbl_volver = tk.Label(izq, text="← Volver al catálogo", bg=FONDO_SECCION,
                              fg=VERDE_OSCURO, font=(FUENTE, 10, "underline"), cursor="hand2")
        lbl_volver.place(x=24, y=10)
        lbl_volver.bind("<Button-1>", lambda e: self._regresar())

        self.lbl_titulo_form = tk.Label(izq, text="Agregar seccion", bg=FONDO_SECCION,
                                        fg=CAFE, font=(FUENTE, 20, "bold"))
        self.lbl_titulo_form.place(x=24, y=36)

        self.e_nombre = self._crear_campo_pildora(izq, 24, 95, 360, "Nombre de la sección:")
        self.e_categoria = self._crear_campo_pildora(izq, 24, 155, 360, "Categoría:")
        self.e_tipo = self._crear_campo_pildora(izq, 24, 215, 360, "tipo de plantas:")

        tk.Label(izq, text="Descripción:", bg=FONDO_SECCION, fg=TEXTO,
                 font=(FUENTE, 10)).place(x=24, y=275)
        canvas_desc = tk.Canvas(izq, width=360, height=75, bg=FONDO_SECCION,
                                highlightthickness=0)
        canvas_desc.place(x=24, y=295)
        rectangulo_redondeado(canvas_desc, 0, 0, 360, 75, 20, CAFE)
        self.e_desc = tk.Text(canvas_desc, bd=0, bg=CAFE, fg=BLANCO, insertbackground=BLANCO,
                              font=(FUENTE, 10), wrap="word", relief="flat",
                              highlightthickness=0)
        canvas_desc.create_window(180, 37, window=self.e_desc, width=320, height=55)

        self.btn_guardar = tk.Canvas(izq, width=240, height=36, bg=FONDO_SECCION,
                                     highlightthickness=0, cursor="hand2")
        self.btn_guardar.place(x=84, y=395)
        self.r_btn = rectangulo_redondeado(self.btn_guardar, 0, 0, 240, 36, 18, CAFE)
        self.txt_btn = self.btn_guardar.create_text(120, 18, text="AGREGAR SECCION",
                                                    fill=BLANCO, font=(FUENTE, 11, "bold"))
        self.btn_guardar.bind("<Button-1>", lambda e: self._procesar_guardado())
        self.btn_guardar.bind("<Enter>", lambda e: self.btn_guardar.itemconfig(
            self.r_btn, fill=CAFE_HOVER, outline=CAFE_HOVER))
        self.btn_guardar.bind("<Leave>", lambda e: self.btn_guardar.itemconfig(
            self.r_btn, fill=CAFE, outline=CAFE))

        self._construir_panel_lista()
        self.recargar_lista()

    def _crear_campo_pildora(self, master, x, y, ancho, titulo):
        tk.Label(master, text=titulo, bg=FONDO_SECCION, fg=TEXTO,
                 font=(FUENTE, 10)).place(x=x, y=y)
        canvas_fnd = tk.Canvas(master, width=ancho, height=28, bg=FONDO_SECCION,
                               highlightthickness=0)
        canvas_fnd.place(x=x, y=y + 20)
        rectangulo_redondeado(canvas_fnd, 0, 0, ancho, 28, 14, CAFE)
        entrada = tk.Entry(canvas_fnd, bd=0, bg=CAFE, fg=BLANCO, insertbackground=BLANCO,
                           font=(FUENTE, 10), relief="flat", highlightthickness=0)
        canvas_fnd.create_window(ancho / 2, 14, window=entrada, width=ancho - 24)
        return entrada

    def _construir_panel_lista(self):
        der = tk.Canvas(self, width=540, height=430, bg=FONDO_SECCION, highlightthickness=0)
        der.place(x=435, y=15)
        rectangulo_redondeado(der, 0, 0, 540, 430, 28, VERDE_OSCURO)

        canvas_search = tk.Canvas(der, width=500, height=28, bg=VERDE_OSCURO,
                                  highlightthickness=0)
        der.create_window(20, 15, window=canvas_search, anchor="nw")
        rectangulo_redondeado(canvas_search, 0, 0, 500, 28, 14, VERDE_BUSCADOR)
        canvas_search.create_oval(15, 6, 25, 16, outline=TEXTO_CLARO, width=2)
        canvas_search.create_line(24, 15, 30, 21, fill=TEXTO_CLARO, width=2)
        self.e_buscar = tk.Entry(canvas_search, bd=0, bg=VERDE_BUSCADOR, fg=TEXTO_CLARO,
                                 insertbackground=TEXTO_CLARO, font=(FUENTE, 9), relief="flat",
                                 highlightthickness=0)
        canvas_search.create_window(260, 14, window=self.e_buscar, width=420)
        self.e_buscar.bind("<KeyRelease>", lambda e: self.recargar_lista())

        der.create_text(24, 60, text="Lista de secciones", anchor="w", fill=TEXTO_CLARO,
                        font=(FUENTE, 11, "bold"))
        lbl_del = der.create_text(516, 60, text="eliminar seleccionado", anchor="e",
                                  fill=TEXTO_CLARO, font=(FUENTE, 10, "underline"))
        der.tag_bind(lbl_del, "<Button-1>", lambda e: self._eliminar_marcados())
        der.tag_bind(lbl_del, "<Enter>", lambda e: der.config(cursor="hand2"))
        der.tag_bind(lbl_del, "<Leave>", lambda e: der.config(cursor=""))

        der.create_text(105, 85, text="informacion", anchor="w", fill=TEXTO_CLARO,
                        font=(FUENTE, 9, "bold"))
        der.create_text(472, 85, text="Acciones", fill=TEXTO_CLARO, font=(FUENTE, 9, "bold"))

        self.frame_scroll = tk.Frame(der, bg=VERDE_OSCURO)
        der.create_window(10, 100, window=self.frame_scroll, anchor="nw", width=520, height=315)
        self.canvas_rows = tk.Canvas(self.frame_scroll, bg=VERDE_OSCURO, highlightthickness=0)
        scr = tk.Scrollbar(self.frame_scroll, orient="vertical", command=self.canvas_rows.yview)
        self.canvas_rows.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y")
        self.canvas_rows.pack(side="left", fill="both", expand=True)
        self.interior_lista = tk.Frame(self.canvas_rows, bg=VERDE_OSCURO)
        self.canvas_rows.create_window(0, 0, window=self.interior_lista, anchor="nw", width=495)
        self.interior_lista.bind("<Configure>", lambda e: self.canvas_rows.configure(
            scrollregion=self.canvas_rows.bbox("all")))

    # ---------------- Lista ----------------
    def recargar_lista(self):
        for h in self.interior_lista.winfo_children():
            h.destroy()
        sql = "SELECT id_categoria, nombre, tipo_plantas FROM categorias"
        txt = self.e_buscar.get().strip()
        params = []
        if txt:
            sql += " WHERE nombre ILIKE %s OR tipo_plantas ILIKE %s"
            params = [f"%{txt}%", f"%{txt}%"]
        sql += " ORDER BY id_categoria"
        try:
            self.lista_secciones = db.consultar(sql, params)
        except Exception as e:
            messagebox.showerror("Error de base de datos",
                                 f"No se pudo cargar la lista:\n{e}\n\n"
                                 "¿Ejecutaste el ALTER TABLE de tipo_plantas?")
            return

        if not self.lista_secciones:
            tk.Label(self.interior_lista, text="No hay secciones registradas.",
                     bg=VERDE_OSCURO, fg=TEXTO_CLARO, font=(FUENTE, 11)).pack(pady=40)

        for s in self.lista_secciones:
            row = tk.Frame(self.interior_lista, bg=VERDE_OSCURO, height=ALTO_FILA)
            row.pack(fill="x")
            row.pack_propagate(False)

            cid = s["id_categoria"]
            lbl_chk = tk.Label(row, text="☑" if cid in self.marcadas else "☐",
                               bg=VERDE_OSCURO, fg=TEXTO_CLARO, font=(FUENTE, 16),
                               cursor="hand2")
            lbl_chk.place(x=8, y=ALTO_FILA / 2, anchor="w")
            lbl_chk.bind("<Button-1>", lambda e, i=cid, l=lbl_chk: self._alternar_marca(i, l))

            ico = tk.Canvas(row, width=45, height=45, bg=VERDE_OSCURO, highlightthickness=0)
            ico.place(x=40, y=(ALTO_FILA - 45) / 2)
            dibujar_icono_seccion(ico, s["nombre"], 45, 45)

            tk.Label(row, text=s["nombre"], bg=VERDE_OSCURO, fg=BLANCO,
                     font=(FUENTE, 10, "bold"), anchor="w").place(x=105, y=15)
            tk.Label(row, text=s["tipo_plantas"] or "General", bg=VERDE_OSCURO,
                     fg=TEXTO_CLARO, font=(FUENTE, 9), anchor="w").place(x=105, y=38)

            editar = tk.Canvas(row, width=20, height=20, bg=VERDE_OSCURO,
                               highlightthickness=0, cursor="hand2")
            editar.place(x=435, y=ALTO_FILA / 2, anchor="center")
            icono_editar(editar)
            editar.bind("<Button-1>", lambda e, item=s: self._cargar_edicion(item))

            borrar = tk.Canvas(row, width=20, height=20, bg=VERDE_OSCURO,
                               highlightthickness=0, cursor="hand2")
            borrar.place(x=472, y=ALTO_FILA / 2, anchor="center")
            icono_papelera(borrar)
            borrar.bind("<Button-1>", lambda e, i=cid: self._eliminar_secciones_db([i]))

            tk.Frame(self.interior_lista, bg=VERDE_BUSCADOR, height=1).pack(fill="x", padx=10)

    def _alternar_marca(self, cid, label):
        if cid in self.marcadas:
            self.marcadas.remove(cid)
            label.config(text="☐")
        else:
            self.marcadas.add(cid)
            label.config(text="☑")

    # ---------------- Alta y edición ----------------
    @staticmethod
    def _poner(entrada, texto):
        entrada.delete(0, tk.END)
        entrada.insert(0, texto)

    def _cargar_edicion(self, s):
        try:
            completo = db.consultar("SELECT * FROM categorias WHERE id_categoria = %s",
                                    (s["id_categoria"],), uno=True)
        except Exception as e:
            messagebox.showerror("Error de base de datos", str(e))
            return
        if completo is None:
            self.recargar_lista()
            return
        self.editando_id = completo["id_categoria"]
        self._poner(self.e_nombre, completo["nombre"])
        self._poner(self.e_categoria, completo["nombre"])
        self._poner(self.e_tipo, completo["tipo_plantas"] or "")
        self.e_desc.delete("1.0", tk.END)
        self.e_desc.insert("1.0", completo["descripcion"] or "")
        self.lbl_titulo_form.config(text="Editar seccion")
        self.btn_guardar.itemconfig(self.txt_btn, text="GUARDAR CAMBIOS")

    def _procesar_guardado(self):
        nom = self.e_nombre.get().strip()
        tipo = self.e_tipo.get().strip()
        desc = self.e_desc.get("1.0", tk.END).strip()
        if not nom:
            messagebox.showwarning("Campos incompletos",
                                   "Por favor introduce el nombre de la sección.")
            return
        if len(nom) > 50:
            messagebox.showwarning("Nombre muy largo",
                                   "El nombre de la sección no puede pasar de 50 caracteres.")
            return
        if len(tipo) > 100:
            messagebox.showwarning("Texto muy largo",
                                   "El tipo de plantas no puede pasar de 100 caracteres.")
            return
        try:
            if self.editando_id is None:
                db.ejecutar("""INSERT INTO categorias (nombre, tipo_plantas, descripcion)
                               VALUES (%s, %s, %s)""", (nom, tipo or None, desc or None))
                msg = "Sección agregada con éxito."
            else:
                db.ejecutar("""UPDATE categorias
                               SET nombre = %s, tipo_plantas = %s, descripcion = %s
                               WHERE id_categoria = %s""",
                            (nom, tipo or None, desc or None, self.editando_id))
                msg = "Sección actualizada con éxito."
        except psycopg2.errors.UniqueViolation:
            messagebox.showwarning("Sección repetida", "Ya existe una sección con ese nombre.")
            return
        except Exception as e:
            messagebox.showerror("Error de base de datos",
                                 f"No se pudo guardar la información:\n{e}")
            return
        messagebox.showinfo("Éxito", msg)
        self._limpiar_campos()
        self.recargar_lista()

    def _limpiar_campos(self):
        self.editando_id = None
        for entrada in (self.e_nombre, self.e_categoria, self.e_tipo):
            entrada.delete(0, tk.END)
        self.e_desc.delete("1.0", tk.END)
        self.lbl_titulo_form.config(text="Agregar seccion")
        self.btn_guardar.itemconfig(self.txt_btn, text="AGREGAR SECCION")

    # ---------------- Eliminación ----------------
    def _eliminar_marcados(self):
        if not self.marcadas:
            messagebox.showinfo("Eliminar",
                                "Selecciona las casillas de las secciones que deseas eliminar.")
            return
        self._eliminar_secciones_db(list(self.marcadas))

    def _eliminar_secciones_db(self, ids):
        if not messagebox.askyesno(
                "Confirmar",
                f"¿Eliminar {len(ids)} sección(es)?\nEsta acción no se puede deshacer."):
            return
        nombres = {s["id_categoria"]: s["nombre"] for s in self.lista_secciones}
        con_plantas = []
        for cid in ids:
            try:
                db.ejecutar("DELETE FROM categorias WHERE id_categoria = %s", (cid,))
            except (psycopg2.errors.ForeignKeyViolation, psycopg2.errors.RestrictViolation):
                con_plantas.append(nombres.get(cid, str(cid)))
                continue
            except Exception as e:
                messagebox.showerror("Error de base de datos", str(e))
                break
            self.marcadas.discard(cid)
            if self.editando_id == cid:
                self._limpiar_campos()
        self.recargar_lista()
        if con_plantas:
            messagebox.showwarning(
                "No se pudo eliminar",
                "Estas secciones todavía tienen plantas:\n\n"
                + "\n".join(f"• {n}" for n in con_plantas)
                + "\n\nReubica o elimina sus plantas primero.")

    def _regresar(self):
        if self.al_volver is not None:
            self.al_volver()