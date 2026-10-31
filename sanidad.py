"""sanidad.py - Pantallas de PLAGAS y ENFERMEDADES (diapositivas 12 a 16).

Las dos secciones tienen el mismo diseno, asi que comparten esta clase:

    * Cuadricula  : miniaturas redondeadas con el nombre en una pildora verde
    * Formulario  : "Agregar plaga / enfermedad" + lista con buscador,
                    casillas, editar, eliminar y "eliminar seleccionado"
    * Ficha       : foto grande y datos de la plaga o enfermedad

Todo el acceso a la base pasa por `_consulta()`. Si tus columnas se llaman
distinto, cambialas en CAMPOS_PLAGA / CAMPOS_ENFERMEDAD y en las constantes
de cada `Tipo` (tabla y clave primaria).

Fotos: se buscan en  imagenes/plagas/<nombre>.jpg  e
imagenes/enfermedades/<nombre>.jpg  (sin tildes, en minusculas, espacios
como guion bajo; por ejemplo  mancha_foliar.jpg  o el id:  3.jpg).
"""
import os
import re
import unicodedata
import tkinter as tk
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageOps, ImageTk

import db

RAIZ = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------
# Estilo (tomado de las diapositivas)
# --------------------------------------------------------------------------
VERDE = "#3E5A1C"
VERDE_BUSQUEDA = "#55762F"
FONDO = "#C7C9B6"
TERRACOTA = "#A5532F"
TEXTO = "#4B3D33"
CLARO = "#E6EAD3"

FUENTE = "Segoe UI"
OPCIONES_RIESGO = ("Bajo", "Medio", "Alto")
RESAMPLE = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS


# --------------------------------------------------------------------------
# Definicion de cada tipo
# --------------------------------------------------------------------------
class Tipo:
    """Describe una seccion: tabla, columnas y textos."""

    def __init__(self, tabla, pk, carpeta, singular, plural, titulo_ficha,
                 campos, ficha, salto_tras_nombre=False):
        self.tabla = tabla
        self.pk = pk
        self.carpeta = carpeta
        self.singular = singular
        self.plural = plural
        self.titulo_ficha = titulo_ficha
        self.campos = campos            # (columna, etiqueta, modo, obligatorio, maximo)
        self.ficha = ficha              # (columna, etiqueta) en el orden de la ficha
        self.salto_tras_nombre = salto_tras_nombre


CAMPOS_PLAGA = [
    ("nombre_comun", "Nombre común", "linea", True, 100),
    ("afecta", "Afecta", "linea", False, 100),
    ("sintomas", "Síntomas", "texto", True, 500),
    ("plantas_afectadas", "Plantas afectadas", "texto", False, 300),
    ("prevencion", "Prevención", "texto", False, 500),
    ("control", "Control", "texto", False, 500),
]

CAMPOS_ENFERMEDAD = [
    ("nombre_comun", "Nombre común", "linea", True, 100),
    ("afecta", "Afecta", "linea", False, 100),
    ("sintomas", "Síntomas", "texto", True, 500),
    ("plantas_afectadas", "Plantas afectadas", "texto", False, 300),
    ("causas", "Causas", "texto", False, 300),
    ("prevencion", "Prevención", "texto", False, 500),
    ("tratamiento", "Control (tratamiento)", "texto", False, 500),
    ("nivel_riesgo", "Nivel de riesgo", "riesgo", False, 10),
]

PLAGAS = Tipo(
    tabla="plagas", pk="id_plaga", carpeta="plagas",
    singular="plaga", plural="plagas", titulo_ficha="PLAGAS",
    campos=CAMPOS_PLAGA,
    ficha=[("afecta", "Afecta"), ("sintomas", "Síntomas"),
           ("plantas_afectadas", "Plantas afectadas"),
           ("prevencion", "Prevención"), ("control", "Control")],
)

ENFERMEDADES = Tipo(
    tabla="enfermedades", pk="id_enfermedad", carpeta="enfermedades",
    singular="enfermedad", plural="enfermedades", titulo_ficha="Enfermedades",
    campos=CAMPOS_ENFERMEDAD,
    ficha=[("sintomas", "Síntomas"), ("afecta", "Afecta"),
           ("plantas_afectadas", "Plantas afectadas"), ("causas", "Causas"),
           ("prevencion", "Prevención"), ("tratamiento", "Tratamiento"),
           ("nivel_riesgo", "Nivel de riesgo")],
    salto_tras_nombre=True,
)


# --------------------------------------------------------------------------
# Acceso a datos (unico punto que toca la base)
# --------------------------------------------------------------------------
def _consulta(sql, params=()):
    """Ejecuta sql y devuelve una lista de dicts (o None si no hay filas)."""
    conn = db.conectar()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            filas = None
            if cur.description:
                cols = [d[0] for d in cur.description]
                filas = [dict(f) if isinstance(f, dict) else dict(zip(cols, f))
                         for f in cur.fetchall()]
        conn.commit()
        return filas
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# --------------------------------------------------------------------------
# Utilidades de imagen y dibujo
# --------------------------------------------------------------------------
def _slug(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_")


def _buscar_foto(carpeta, nombre, ident):
    base = os.path.join(RAIZ, "imagenes", carpeta)
    for raiz in (_slug(nombre), str(ident)):
        if not raiz:
            continue
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            ruta = os.path.join(base, raiz + ext)
            if os.path.isfile(ruta):
                return ruta
    return None


def _crear_foto(ruta, ancho, alto, radio):
    img = None
    if ruta:
        try:
            img = ImageOps.fit(Image.open(ruta).convert("RGBA"), (ancho, alto), RESAMPLE)
        except Exception:
            img = None
    if img is None:  # sin foto: una hoja sencilla
        img = Image.new("RGBA", (ancho, alto), "#8FA373")
        d = ImageDraw.Draw(img)
        cx, cy, r = ancho // 2, alto // 2, max(6, min(ancho, alto) // 4)
        d.ellipse((cx - r, cy - r // 2, cx + r, cy + r // 2), fill="#5E7A3A")
        d.line((cx - r, cy + r // 2, cx + r, cy - r // 2), fill=CLARO, width=max(2, r // 8))
    mascara = Image.new("L", (ancho, alto), 0)
    ImageDraw.Draw(mascara).rounded_rectangle((0, 0, ancho - 1, alto - 1), radius=radio, fill=255)
    img.putalpha(mascara)
    return ImageTk.PhotoImage(img)


def _rect(canvas, x1, y1, x2, y2, r, color, tag=""):
    r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, fill=color, outline=color, tags=tag)


# --------------------------------------------------------------------------
# Widgets
# --------------------------------------------------------------------------
class BotonPildora(tk.Canvas):
    def __init__(self, master, ancho, alto, texto, comando, color=VERDE, fg="white",
                 fondo=FONDO, fuente=(FUENTE, 10)):
        super().__init__(master, width=ancho, height=alto, bg=fondo,
                         highlightthickness=0, cursor="hand2")
        _rect(self, 0, 0, ancho, alto, alto // 2, color)
        self.create_text(ancho // 2, alto // 2, text=texto, fill=fg, font=fuente,
                         width=ancho - 20)
        self.bind("<Button-1>", lambda e: comando())


class Pildora(tk.Canvas):
    """Campo de entrada con fondo de pildora. get() / set() / limpiar()."""

    def __init__(self, master, ancho, modo="linea", color=TERRACOTA, fondo=FONDO, fg="white"):
        alto = 52 if modo == "texto" else 34
        super().__init__(master, width=ancho, height=alto, bg=fondo, highlightthickness=0)
        self.modo = modo
        _rect(self, 0, 0, ancho, alto, 18 if modo == "texto" else alto // 2, color)
        fuente = (FUENTE, 10)
        if modo == "texto":
            self.entrada = tk.Text(self, height=2, wrap="word", bd=0, relief="flat",
                                   bg=color, fg=fg, insertbackground=fg, font=fuente,
                                   highlightthickness=0, padx=0, pady=0, undo=True)
            self.create_window(ancho // 2, alto // 2, window=self.entrada,
                               width=ancho - 34, height=alto - 16)
        elif modo == "riesgo":
            self.var = tk.StringVar(value="Medio")
            menu = tk.OptionMenu(self, self.var, *OPCIONES_RIESGO)
            menu.config(bg=color, fg=fg, activebackground=color, activeforeground=fg,
                        relief="flat", bd=0, highlightthickness=0, font=fuente, anchor="w")
            menu["menu"].config(bg=color, fg=fg, font=fuente)
            self.create_window(ancho // 2, alto // 2, window=menu, width=ancho - 24)
        else:
            self.entrada = tk.Entry(self, bd=0, relief="flat", bg=color, fg=fg,
                                    insertbackground=fg, font=fuente, highlightthickness=0)
            self.create_window(ancho // 2, alto // 2, window=self.entrada,
                               width=ancho - 30, height=alto - 12)

    def get(self):
        if self.modo == "texto":
            return self.entrada.get("1.0", "end-1c")
        if self.modo == "riesgo":
            return self.var.get()
        return self.entrada.get()

    def set(self, valor):
        valor = "" if valor is None else str(valor)
        if self.modo == "texto":
            self.entrada.delete("1.0", "end")
            self.entrada.insert("1.0", valor)
        elif self.modo == "riesgo":
            self.var.set(valor if valor in OPCIONES_RIESGO else "Medio")
        else:
            self.entrada.delete(0, "end")
            self.entrada.insert(0, valor)

    def limpiar(self):
        self.set("")


class PanelRedondeado(tk.Canvas):
    """Panel de esquinas redondeadas; los widgets van en .interior."""

    def __init__(self, master, color, fondo, radio=28):
        super().__init__(master, bg=fondo, highlightthickness=0)
        self.color, self.radio = color, radio
        self.interior = tk.Frame(self, bg=color)
        self._ventana = self.create_window(radio // 2, radio // 2, window=self.interior, anchor="nw")
        self.bind("<Configure>", self._ajustar)

    def _ajustar(self, e):
        self.delete("fondo")
        _rect(self, 0, 0, e.width, e.height, self.radio, self.color, "fondo")
        self.tag_lower("fondo")
        m = self.radio // 2
        self.coords(self._ventana, m, m)
        self.itemconfigure(self._ventana, width=max(1, e.width - 2 * m),
                           height=max(1, e.height - 2 * m))


class FrameDesplazable(tk.Frame):
    """Frame con desplazamiento vertical por rueda del raton (sin bind_all)."""

    def __init__(self, master, bg):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.interior = tk.Frame(self.canvas, bg=bg)
        self._ventana = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self._ventana, width=e.width))
        self.vincular(self.canvas)
        self.vincular(self.interior)

    def vincular(self, widget):
        for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind(evento, self._rueda, add="+")

    def vincular_hijos(self, widget=None):
        widget = widget or self.interior
        for hijo in widget.winfo_children():
            if not isinstance(hijo, tk.Text):
                self.vincular(hijo)
            self.vincular_hijos(hijo)

    def _rueda(self, e):
        if self.canvas.yview() == (0.0, 1.0):
            return
        if getattr(e, "num", 0) == 4:
            paso = -1
        elif getattr(e, "num", 0) == 5:
            paso = 1
        else:
            paso = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(paso, "units")


# --------------------------------------------------------------------------
# Pantalla
# --------------------------------------------------------------------------
def _rol(usuario):
    if isinstance(usuario, dict):
        return usuario.get("rol")
    return getattr(usuario, "rol", None)


class PantallaSanidad(tk.Frame):
    POR_PAGINA = 6

    def __init__(self, master, tipo, usuario=None):
        super().__init__(master, bg=FONDO)
        self.tipo = tipo
        self.usuario = usuario
        self._fotos = {}
        self._pagina = 0
        self.cuerpo = None
        self.editando = None
        if _rol(usuario) not in ("admin", "vendedor"):
            tk.Label(self, text="No tienes acceso a esta sección.", bg=FONDO,
                     fg=TEXTO, font=(FUENTE, 14)).pack(expand=True)
            return
        self.mostrar_grid()

    # ---- apoyo ----------------------------------------------------------
    def _nueva_vista(self):
        if self.cuerpo is not None:
            self.cuerpo.destroy()
        self.cuerpo = tk.Frame(self, bg=FONDO)
        self.cuerpo.pack(fill="both", expand=True)
        return self.cuerpo

    def foto(self, ident, nombre, ancho, alto, radio):
        clave = (self.tipo.carpeta, ident, nombre, ancho, alto, radio)
        if clave not in self._fotos:
            ruta = _buscar_foto(self.tipo.carpeta, nombre, ident)
            self._fotos[clave] = _crear_foto(ruta, ancho, alto, radio)
        return self._fotos[clave]

    def _error_bd(self, error):
        messagebox.showerror("Error de base de datos",
                             f"No se pudo completar la operación.\n\n{error}", parent=self)

    def _cargar(self, filtro=""):
        t = self.tipo
        cols = ", ".join([t.pk] + [c[0] for c in t.campos])
        sql = f"SELECT {cols} FROM {t.tabla}"
        params = ()
        if filtro:
            sql += " WHERE nombre_comun ILIKE %s ESCAPE '\\'"
            params = (f"%{_escapar_like(filtro)}%",)
        sql += " ORDER BY nombre_comun"
        try:
            return _consulta(sql, params) or []
        except Exception as e:
            self._error_bd(e)
            return []

    def _obtener(self, ident):
        t = self.tipo
        cols = ", ".join([t.pk] + [c[0] for c in t.campos])
        try:
            filas = _consulta(f"SELECT {cols} FROM {t.tabla} WHERE {t.pk} = %s", (ident,))
        except Exception as e:
            self._error_bd(e)
            return None
        return filas[0] if filas else None

    # ---- vista 1: cuadricula (diap. 14 enfermedades / equivalente plagas) --
    def mostrar_grid(self, pagina=None):
        t = self.tipo
        if pagina is not None:
            self._pagina = pagina
        cuerpo = self._nueva_vista()
        filas = self._cargar()
        total = max(1, -(-len(filas) // self.POR_PAGINA))
        self._pagina = max(0, min(self._pagina, total - 1))
        ini = self._pagina * self.POR_PAGINA

        cab = tk.Frame(cuerpo, bg=FONDO)
        cab.pack(fill="x", padx=28, pady=(18, 6))
        tk.Label(cab, text=t.plural.capitalize(), bg=FONDO, fg=TERRACOTA,
                 font=(FUENTE, 22, "bold")).pack(side="left")
        enlace = tk.Label(cab, text=f"+ Agregar {t.singular}", bg=FONDO, fg=TERRACOTA,
                          font=(FUENTE, 15), cursor="hand2")
        enlace.pack(side="right")
        enlace.bind("<Button-1>", lambda e: self.mostrar_formulario())

        if not filas:
            tk.Label(cuerpo, text=f"Aún no hay {t.plural} registradas.", bg=FONDO,
                     fg=TEXTO, font=(FUENTE, 13)).pack(expand=True)
            return

        malla = tk.Frame(cuerpo, bg=FONDO)
        malla.pack(expand=True)
        for i, fila in enumerate(filas[ini:ini + self.POR_PAGINA]):
            r, c = divmod(i, 3)
            ident, nombre = fila[t.pk], fila["nombre_comun"]
            celda = tk.Frame(malla, bg=FONDO)
            celda.grid(row=r, column=c, padx=14, pady=8)
            imagen = tk.Label(celda, image=self.foto(ident, nombre, 190, 110, 30),
                              bg=FONDO, cursor="hand2")
            imagen.pack()
            imagen.bind("<Button-1>", lambda e, i=ident: self.mostrar_ficha(i))
            BotonPildora(celda, 170, 50, nombre,
                         lambda i=ident: self.mostrar_ficha(i)).pack(pady=(8, 0))

        if total > 1:
            nav = tk.Frame(cuerpo, bg=FONDO)
            nav.pack(pady=(0, 12))
            ant = tk.Label(nav, text="‹", bg=FONDO, fg=TERRACOTA, font=(FUENTE, 18, "bold"),
                           cursor="hand2")
            ant.pack(side="left", padx=10)
            ant.bind("<Button-1>", lambda e: self.mostrar_grid(self._pagina - 1))
            tk.Label(nav, text=f"Página {self._pagina + 1} de {total}", bg=FONDO,
                     fg=TEXTO, font=(FUENTE, 10)).pack(side="left")
            sig = tk.Label(nav, text="›", bg=FONDO, fg=TERRACOTA, font=(FUENTE, 18, "bold"),
                           cursor="hand2")
            sig.pack(side="left", padx=10)
            sig.bind("<Button-1>", lambda e: self.mostrar_grid(self._pagina + 1))

    # ---- vista 2: formulario + lista (diap. 12 y 15) ---------------------
    def mostrar_formulario(self, editar_id=None):
        t = self.tipo
        cuerpo = self._nueva_vista()
        self.editando = editar_id
        cuerpo.columnconfigure(0, weight=5, uniform="col")
        cuerpo.columnconfigure(1, weight=6, uniform="col")
        cuerpo.rowconfigure(0, weight=1)

        # -- izquierda: formulario
        izq = FrameDesplazable(cuerpo, FONDO)
        izq.grid(row=0, column=0, sticky="nsew", padx=(24, 8), pady=12)
        form = izq.interior
        titulo = f"Editar {t.singular}" if editar_id else f"Agregar {t.singular}"
        tk.Label(form, text=titulo, bg=FONDO, fg=TERRACOTA,
                 font=(FUENTE, 20, "bold")).pack(anchor="w", pady=(4, 8))
        self.campos = {}
        for col, etiqueta, modo, _obl, _max in t.campos:
            tk.Label(form, text=f"{etiqueta}:", bg=FONDO, fg=TEXTO,
                     font=(FUENTE, 10)).pack(anchor="w", pady=(6, 1))
            p = Pildora(form, 300, modo)
            p.pack(anchor="w")
            self.campos[col] = p
        texto_boton = "GUARDAR CAMBIOS" if editar_id else f"AGREGAR {t.singular.upper()}"
        BotonPildora(form, 260, 38, texto_boton, self._guardar, color=TERRACOTA,
                     fuente=(FUENTE, 9, "bold")).pack(anchor="w", pady=(16, 4))
        if editar_id:
            cancelar = tk.Label(form, text="Cancelar edición", bg=FONDO, fg=TERRACOTA,
                                font=(FUENTE, 10, "underline"), cursor="hand2")
            cancelar.pack(anchor="w", pady=(0, 8))
            cancelar.bind("<Button-1>", lambda e: self.mostrar_formulario())
        izq.vincular_hijos()
        if editar_id:
            self._rellenar(editar_id)

        # -- derecha: panel verde con buscador y lista
        panel = PanelRedondeado(cuerpo, VERDE, FONDO)
        panel.grid(row=0, column=1, sticky="nsew", padx=(8, 24), pady=14)
        interior = panel.interior

        barra = tk.Frame(interior, bg=VERDE)
        barra.pack(fill="x", pady=(2, 8))
        tk.Label(barra, text="🔍", bg=VERDE, fg=CLARO, font=(FUENTE, 11)).pack(side="left", padx=(4, 4))
        self.buscador = Pildora(barra, 360, "linea", color=VERDE_BUSQUEDA, fondo=VERDE)
        self.buscador.pack(side="left")
        self.buscador.entrada.bind("<KeyRelease>", lambda e: self._pintar_lista())

        cab = tk.Frame(interior, bg=VERDE)
        cab.pack(fill="x", pady=(4, 2))
        tk.Label(cab, text=f"Lista de {t.plural}", bg=VERDE, fg=CLARO,
                 font=(FUENTE, 10, "bold")).pack(side="left", padx=4)
        borrar_sel = tk.Label(cab, text="eliminar seleccionado", bg=VERDE, fg=CLARO,
                              font=(FUENTE, 10, "bold"), cursor="hand2")
        borrar_sel.pack(side="right", padx=4)
        borrar_sel.bind("<Button-1>", lambda e: self._eliminar_seleccionados())

        sub = tk.Frame(interior, bg=VERDE)
        sub.pack(fill="x", pady=(2, 4))
        tk.Label(sub, text="informacion", bg=VERDE, fg=CLARO, font=(FUENTE, 9, "bold")).pack(
            side="left", padx=(90, 0))
        tk.Label(sub, text="Acciones", bg=VERDE, fg=CLARO, font=(FUENTE, 9, "bold")).pack(
            side="right", padx=8)

        self.lista = FrameDesplazable(interior, VERDE)
        self.lista.pack(fill="both", expand=True)
        self._pintar_lista()

    def _rellenar(self, ident):
        datos = self._obtener(ident)
        if not datos:
            messagebox.showwarning("No encontrado", f"La {self.tipo.singular} ya no existe.",
                                   parent=self)
            self.mostrar_formulario()
            return
        for col, campo in self.campos.items():
            campo.set(datos.get(col))

    def _pintar_lista(self):
        t = self.tipo
        for w in self.lista.interior.winfo_children():
            w.destroy()
        self.marcas = {}
        filas = self._cargar(self.buscador.get().strip())
        if not filas:
            tk.Label(self.lista.interior, text="Sin resultados.", bg=VERDE, fg=CLARO,
                     font=(FUENTE, 10)).pack(pady=20)
        for f in filas:
            ident, nombre = f[t.pk], f["nombre_comun"]
            fila = tk.Frame(self.lista.interior, bg=VERDE)
            fila.pack(fill="x", pady=7)
            var = tk.BooleanVar(value=False)
            self.marcas[ident] = (var, nombre)
            tk.Checkbutton(fila, variable=var, bg=VERDE, activebackground=VERDE,
                           selectcolor=CLARO, highlightthickness=0, bd=0).pack(
                side="left", padx=(4, 8))
            imagen = tk.Label(fila, image=self.foto(ident, nombre, 72, 52, 16), bg=VERDE,
                              cursor="hand2")
            imagen.pack(side="left")
            imagen.bind("<Button-1>", lambda e, i=ident: self.mostrar_ficha(i))
            borrar = tk.Label(fila, text="🗑", bg=VERDE, fg=CLARO, font=(FUENTE, 12),
                              cursor="hand2")
            borrar.pack(side="right", padx=(4, 8))
            borrar.bind("<Button-1>", lambda e, i=ident, n=nombre: self._eliminar([(i, n)]))
            editar = tk.Label(fila, text="✎", bg=VERDE, fg=CLARO, font=(FUENTE, 13),
                              cursor="hand2")
            editar.pack(side="right", padx=4)
            editar.bind("<Button-1>", lambda e, i=ident: self.mostrar_formulario(i))
            nom = tk.Label(fila, text=nombre, bg=VERDE, fg=CLARO, font=(FUENTE, 10),
                           anchor="w", justify="left", wraplength=150, cursor="hand2")
            nom.pack(side="left", padx=12, fill="x", expand=True)
            nom.bind("<Button-1>", lambda e, i=ident: self.mostrar_ficha(i))
        self.lista.vincular_hijos()

    # ---- guardar / validar ---------------------------------------------
    def _validar(self, datos):
        t = self.tipo
        for col, etiqueta, modo, obligatorio, maximo in t.campos:
            valor = datos[col]
            if obligatorio and not valor:
                return f"El campo «{etiqueta}» es obligatorio."
            if len(valor) > maximo:
                return f"«{etiqueta}» admite como máximo {maximo} caracteres (tiene {len(valor)})."
        if len(datos["nombre_comun"]) < 2:
            return "El nombre común debe tener al menos 2 caracteres."
        return None

    def _guardar(self):
        t = self.tipo
        datos = {col: campo.get().strip() for col, campo in self.campos.items()}
        error = self._validar(datos)
        if error:
            messagebox.showwarning("Revisa el formulario", error, parent=self)
            return
        try:
            repetida = _consulta(
                f"SELECT 1 FROM {t.tabla} WHERE lower(nombre_comun) = lower(%s) "
                f"AND {t.pk} <> %s", (datos["nombre_comun"], self.editando or 0))
            if repetida:
                messagebox.showwarning(
                    "Nombre repetido",
                    f"Ya existe una {t.singular} llamada «{datos['nombre_comun']}».",
                    parent=self)
                return
            valores = [datos[c[0]] or None for c in t.campos]
            columnas = [c[0] for c in t.campos]
            if self.editando:
                asignar = ", ".join(f"{c} = %s" for c in columnas)
                _consulta(f"UPDATE {t.tabla} SET {asignar} WHERE {t.pk} = %s",
                          valores + [self.editando])
                mensaje = f"Se guardaron los cambios de «{datos['nombre_comun']}»."
            else:
                marcas = ", ".join(["%s"] * len(columnas))
                _consulta(f"INSERT INTO {t.tabla} ({', '.join(columnas)}) "
                          f"VALUES ({marcas}) RETURNING {t.pk}", valores)
                mensaje = f"«{datos['nombre_comun']}» se agregó correctamente."
        except Exception as e:
            self._error_bd(e)
            return
        messagebox.showinfo("Listo", mensaje, parent=self)
        if self.editando:
            self.mostrar_formulario()
        else:
            for campo in self.campos.values():
                campo.limpiar() if campo.modo != "riesgo" else campo.set("Medio")
            self._pintar_lista()

    # ---- eliminar -------------------------------------------------------
    def _eliminar_seleccionados(self):
        elegidas = [(i, n) for i, (var, n) in self.marcas.items() if var.get()]
        if not elegidas:
            messagebox.showinfo("Eliminar", f"Marca al menos una {self.tipo.singular} de la lista.",
                                parent=self)
            return
        self._eliminar(elegidas)

    def _eliminar(self, elegidas):
        t = self.tipo
        if len(elegidas) == 1:
            pregunta = f"¿Eliminar «{elegidas[0][1]}»?"
        else:
            pregunta = f"¿Eliminar las {len(elegidas)} {t.plural} seleccionadas?"
        if not messagebox.askyesno("Confirmar", pregunta + "\nEsta acción no se puede deshacer.",
                                   parent=self):
            return
        borradas, bloqueadas = 0, []
        for ident, nombre in elegidas:
            try:
                _consulta(f"DELETE FROM {t.tabla} WHERE {t.pk} = %s", (ident,))
                borradas += 1
            except Exception as e:
                if getattr(e, "pgcode", None) == "23503":  # clave foranea
                    bloqueadas.append(nombre)
                else:
                    self._error_bd(e)
                    break
        if bloqueadas:
            messagebox.showwarning(
                "No se pudo eliminar",
                "Estas no se pueden eliminar porque están relacionadas con plantas u otros "
                "registros:\n\n• " + "\n• ".join(bloqueadas), parent=self)
        if borradas:
            self._pintar_lista()

    # ---- vista 3: ficha (diap. 13 y 16) -----------------------------------
    def mostrar_ficha(self, ident):
        t = self.tipo
        datos = self._obtener(ident)
        if not datos:
            messagebox.showwarning("No encontrado", f"La {t.singular} ya no existe.", parent=self)
            self.mostrar_grid()
            return
        cuerpo = self._nueva_vista()
        tk.Label(cuerpo, text=t.titulo_ficha, bg=FONDO, fg=TERRACOTA,
                 font=(FUENTE, 22, "bold")).pack(anchor="w", padx=28, pady=(18, 6))

        centro = tk.Frame(cuerpo, bg=FONDO)
        centro.pack(expand=True)
        tk.Label(centro, image=self.foto(ident, datos["nombre_comun"], 340, 230, 36),
                 bg=FONDO).pack(side="left", padx=(10, 24))

        texto = tk.Text(centro, width=42, height=15, wrap="word", bg=FONDO, fg=TEXTO,
                        bd=0, relief="flat", highlightthickness=0, font=(FUENTE, 12),
                        cursor="arrow", padx=4, pady=4)
        texto.tag_configure("centro", justify="center")
        texto.tag_configure("neg", justify="center", font=(FUENTE, 12, "bold"))
        texto.insert("end", datos["nombre_comun"] + "\n", "neg")
        if t.salto_tras_nombre:
            texto.insert("end", "\n", "centro")
        for col, etiqueta in t.ficha:
            valor = datos.get(col)
            if not valor:
                continue
            texto.insert("end", f"{etiqueta}: ", "neg")
            texto.insert("end", f"{valor}\n", "centro")
        texto.config(state="disabled")
        texto.pack(side="left")

        pie = tk.Frame(cuerpo, bg=FONDO)
        pie.pack(fill="x", padx=28, pady=(0, 16))
        volver = tk.Label(pie, text="← Volver", bg=FONDO, fg=TERRACOTA,
                          font=(FUENTE, 12, "bold"), cursor="hand2")
        volver.pack(side="left")
        volver.bind("<Button-1>", lambda e: self.mostrar_grid())
        editar = tk.Label(pie, text="✎ Editar", bg=FONDO, fg=TERRACOTA,
                          font=(FUENTE, 12, "bold"), cursor="hand2")
        editar.pack(side="right")
        editar.bind("<Button-1>", lambda e: self.mostrar_formulario(ident))


# --------------------------------------------------------------------------
# Prueba independiente:  python plagas.py  /  python enfermedades.py
# --------------------------------------------------------------------------
def probar(tipo, rol="admin"):
    raiz = tk.Tk()
    raiz.title(f"Vivero - {tipo.plural}")
    raiz.geometry("1000x620")
    PantallaSanidad(raiz, tipo, {"rol": rol}).pack(fill="both", expand=True)
    raiz.mainloop()