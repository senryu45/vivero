"""capacitaciones.py - Seccion CAPACITACIONES (diapositiva 10).

Tarjetas con icono, titulo, subtemas y boton INICIAR, mas el enlace
"+ Agregar Capacitacion". INICIAR abre el detalle de la capacitacion y permite
marcarla como completada por el empleado que inicio sesion.

Uso desde secciones.py:
    from capacitaciones import crear_capacitaciones
    "CAPACITACIONES": (crear_capacitaciones, ("admin", "vendedor")),

Prueba suelta:  python capacitaciones.py

Tablas y columnas que asume este modulo (ajusta el bloque SQL_* si difieren):
    capacitaciones(id_capacitacion, nombre)
    subtemas_capacitacion(id_subtema, id_capacitacion, nombre, peso)   -- pesos suman 100
    capacitacion_empleado(id_capacitacion, id_empleado, completada)
"""
import tkinter as tk
from tkinter import messagebox

import db
from sanidad import (CLARO, FONDO, FUENTE, TERRACOTA, TEXTO, VERDE, BotonPildora,
                     FrameDesplazable, _consulta)
from ventas_logica import repartir_pesos, separar_subtemas

CAFE = "#4E3B31"
COLORES = (CAFE, TERRACOTA, VERDE)          # como en el diseno: cafe, terracota, verde

SQL_CAPACITACIONES = "SELECT id_capacitacion, nombre FROM capacitaciones ORDER BY id_capacitacion"
SQL_SUBTEMAS = ("SELECT id_capacitacion, nombre, peso FROM subtemas_capacitacion "
                "ORDER BY id_capacitacion, id_subtema")
SQL_COMPLETADAS = ("SELECT id_capacitacion FROM capacitacion_empleado "
                   "WHERE id_empleado = %s AND completada")


def _usuario(usuario, clave):
    if isinstance(usuario, dict):
        return usuario.get(clave)
    return getattr(usuario, clave, None)


# --------------------------------------------------------------------------
# Iconos vectoriales sencillos (se eligen por palabras del titulo)
# --------------------------------------------------------------------------
def dibujar_icono(c, titulo, color):
    t = (titulo or "").lower()
    w = 4
    if "plaga" in t:                                           # insecto
        c.create_oval(40, 52, 80, 100, outline=color, width=w)
        c.create_oval(48, 30, 72, 52, outline=color, width=w)
        for y in (62, 76, 90):
            c.create_line(40, y, 20, y - 8, fill=color, width=w)
            c.create_line(80, y, 100, y - 8, fill=color, width=w)
        c.create_line(52, 32, 44, 18, fill=color, width=w)
        c.create_line(68, 32, 76, 18, fill=color, width=w)
    elif "quim" in t or "químic" in t:                         # matraz
        c.create_polygon(48, 14, 72, 14, 72, 50, 100, 100, 20, 100, 48, 50,
                         outline=color, fill="", width=w)
        c.create_polygon(36, 80, 84, 80, 100, 100, 20, 100, fill=color, outline=color)
        c.create_line(42, 14, 78, 14, fill=color, width=w + 2)
    elif "prevent" in t:                                       # engranaje
        c.create_oval(34, 34, 86, 86, outline=color, width=w + 2)
        c.create_oval(50, 50, 70, 70, outline=color, width=w)
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            c.create_line(60 + dx * 28, 60 + dy * 28, 60 + dx * 40, 60 + dy * 40,
                          fill=color, width=w + 4)
    else:                                                      # hoja
        c.create_oval(24, 30, 96, 90, outline=color, width=w)
        c.create_line(24, 90, 96, 30, fill=color, width=w)


class _Boton(tk.Canvas):
    """Pildora con texto clicable (usa el color pedido)."""

    def __init__(self, master, texto, color, comando, ancho=84, alto=34):
        super().__init__(master, width=ancho, height=alto, bg=FONDO, highlightthickness=0,
                         cursor="hand2")
        from sanidad import _rect
        _rect(self, 0, 0, ancho, alto, alto // 2, color)
        self.create_text(ancho // 2, alto // 2, text=texto, fill="white",
                         font=(FUENTE, 9))
        self.bind("<Button-1>", lambda e: comando())


# --------------------------------------------------------------------------
# Pantalla
# --------------------------------------------------------------------------
class PantallaCapacitaciones(tk.Frame):
    POR_PAGINA = 3

    def __init__(self, master, usuario=None):
        super().__init__(master, bg=FONDO)
        self.usuario = usuario
        self.id_empleado = _usuario(usuario, "id_empleado")
        self.cuerpo = None
        self._pagina = 0
        if _usuario(usuario, "rol") not in ("admin", "vendedor"):
            tk.Label(self, text="No tienes acceso a esta sección.", bg=FONDO, fg=TEXTO,
                     font=(FUENTE, 14)).pack(expand=True)
            return
        self.mostrar_lista()

    def _nueva_vista(self):
        if self.cuerpo is not None:
            self.cuerpo.destroy()
        self.cuerpo = tk.Frame(self, bg=FONDO)
        self.cuerpo.pack(fill="both", expand=True)
        return self.cuerpo

    def _error_bd(self, error):
        messagebox.showerror("Error de base de datos",
                             f"No se pudo completar la operación.\n\n{error}", parent=self)

    def _cargar(self):
        """Devuelve (lista de capacitaciones, {id: [subtemas]}, set de completadas)."""
        caps = _consulta(SQL_CAPACITACIONES) or []
        subs = {}
        for s in _consulta(SQL_SUBTEMAS) or []:
            subs.setdefault(s["id_capacitacion"], []).append((s["nombre"], s["peso"]))
        hechas = set()
        if self.id_empleado:
            hechas = {f["id_capacitacion"] for f in _consulta(SQL_COMPLETADAS, (self.id_empleado,)) or []}
        return caps, subs, hechas

    # ---- lista (diapositiva 10) -------------------------------------------
    def mostrar_lista(self, pagina=None):
        if pagina is not None:
            self._pagina = pagina
        cuerpo = self._nueva_vista()
        try:
            caps, subs, hechas = self._cargar()
        except Exception as e:
            self._error_bd(e)
            caps, subs, hechas = [], {}, set()

        cab = tk.Frame(cuerpo, bg=FONDO)
        cab.pack(fill="x", padx=28, pady=(18, 4))
        tk.Label(cab, text="CAPACITACIONES", bg=FONDO, fg=TERRACOTA,
                 font=(FUENTE, 22, "bold")).pack(side="left")
        enlace = tk.Label(cab, text="+ Agregar Capacitacion", bg=FONDO, fg=TERRACOTA,
                          font=(FUENTE, 15), cursor="hand2")
        enlace.pack(side="right")
        enlace.bind("<Button-1>", lambda e: self._agregar())

        if not caps:
            tk.Label(cuerpo, text="Aún no hay capacitaciones registradas.", bg=FONDO,
                     fg=TEXTO, font=(FUENTE, 13)).pack(expand=True)
            return

        total = max(1, -(-len(caps) // self.POR_PAGINA))
        self._pagina = max(0, min(self._pagina, total - 1))
        ini = self._pagina * self.POR_PAGINA
        lista = tk.Frame(cuerpo, bg=FONDO)
        lista.pack(fill="both", expand=True, padx=28, pady=6)
        for i, cap in enumerate(caps[ini:ini + self.POR_PAGINA]):
            color = COLORES[(ini + i) % len(COLORES)]
            ident, nombre = cap["id_capacitacion"], cap["nombre"]
            fila = tk.Frame(lista, bg=FONDO)
            fila.pack(fill="x", expand=True, pady=6)
            icono = tk.Canvas(fila, width=120, height=120, bg=FONDO, highlightthickness=0)
            icono.pack(side="left", padx=(8, 24))
            dibujar_icono(icono, nombre, color)
            texto = tk.Frame(fila, bg=FONDO)
            texto.pack(side="left", fill="x", expand=True)
            titulo = nombre + ("   ✓ completada" if ident in hechas else "")
            tk.Label(texto, text=titulo, bg=FONDO, fg=color, font=(FUENTE, 11, "bold"),
                     anchor="w", justify="left").pack(anchor="w")
            temas = ", ".join(n for n, _ in subs.get(ident, [])) or "Sin subtemas registrados"
            tk.Label(texto, text=temas, bg=FONDO, fg=color, font=(FUENTE, 10), anchor="w",
                     justify="left", wraplength=430).pack(anchor="w")
            _Boton(fila, "INICIAR", color,
                   lambda i=ident: self.mostrar_detalle(i)).pack(side="right", padx=(10, 8))

        if total > 1:
            nav = tk.Frame(cuerpo, bg=FONDO)
            nav.pack(pady=(0, 10))
            for simbolo, destino in (("‹", self._pagina - 1), ("›", self._pagina + 1)):
                if simbolo == "›":
                    tk.Label(nav, text=f"Página {self._pagina + 1} de {total}", bg=FONDO,
                             fg=TEXTO, font=(FUENTE, 10)).pack(side="left")
                b = tk.Label(nav, text=simbolo, bg=FONDO, fg=TERRACOTA,
                             font=(FUENTE, 18, "bold"), cursor="hand2")
                b.pack(side="left", padx=10)
                b.bind("<Button-1>", lambda e, d=destino: self.mostrar_lista(d))

    # ---- detalle -------------------------------------------------------------
    def mostrar_detalle(self, ident):
        try:
            caps, subs, hechas = self._cargar()
        except Exception as e:
            self._error_bd(e)
            return
        cap = next((c for c in caps if c["id_capacitacion"] == ident), None)
        if not cap:
            messagebox.showwarning("No encontrada", "La capacitación ya no existe.", parent=self)
            self.mostrar_lista()
            return
        cuerpo = self._nueva_vista()
        tk.Label(cuerpo, text=cap["nombre"], bg=FONDO, fg=TERRACOTA,
                 font=(FUENTE, 20, "bold"), wraplength=700, justify="left").pack(
            anchor="w", padx=28, pady=(18, 4))
        tk.Label(cuerpo, text="Temas que se cubren (peso en la evaluación):", bg=FONDO,
                 fg=TEXTO, font=(FUENTE, 11)).pack(anchor="w", padx=28, pady=(0, 8))
        marco = FrameDesplazable(cuerpo, FONDO)
        marco.pack(fill="both", expand=True, padx=40)
        temas = subs.get(ident, [])
        if not temas:
            tk.Label(marco.interior, text="Esta capacitación no tiene subtemas.", bg=FONDO,
                     fg=TEXTO, font=(FUENTE, 11)).pack(anchor="w", pady=10)
        for nombre, peso in temas:
            tk.Label(marco.interior, text=f"•  {nombre}   ({peso}%)", bg=FONDO, fg=TEXTO,
                     font=(FUENTE, 12), anchor="w", justify="left", wraplength=650).pack(
                anchor="w", pady=3)
        marco.vincular_hijos()

        pie = tk.Frame(cuerpo, bg=FONDO)
        pie.pack(fill="x", padx=28, pady=(6, 16))
        volver = tk.Label(pie, text="← Volver", bg=FONDO, fg=TERRACOTA,
                          font=(FUENTE, 12, "bold"), cursor="hand2")
        volver.pack(side="left")
        volver.bind("<Button-1>", lambda e: self.mostrar_lista())
        if ident in hechas:
            tk.Label(pie, text="✓ Ya la completaste", bg=FONDO, fg=VERDE,
                     font=(FUENTE, 12, "bold")).pack(side="right")
        elif self.id_empleado:
            BotonPildora(pie, 220, 36, "MARCAR COMPLETADA",
                         lambda: self._completar(ident), color=VERDE).pack(side="right")
        else:
            tk.Label(pie, text="Tu usuario no está registrado como empleado: no se puede "
                               "guardar tu avance.", bg=FONDO, fg=TEXTO, font=(FUENTE, 9),
                     wraplength=320, justify="right").pack(side="right")

    def _completar(self, ident):
        if not messagebox.askyesno("Marcar completada",
                                   "¿Confirmas que terminaste esta capacitación?", parent=self):
            return
        try:
            actualizadas = _consulta(
                "UPDATE capacitacion_empleado SET completada = TRUE "
                "WHERE id_capacitacion = %s AND id_empleado = %s RETURNING id_capacitacion AS id",
                (ident, self.id_empleado))
            if not actualizadas:
                _consulta("INSERT INTO capacitacion_empleado (id_capacitacion, id_empleado, "
                          "completada) VALUES (%s, %s, TRUE)", (ident, self.id_empleado))
        except Exception as e:
            self._error_bd(e)
            return
        messagebox.showinfo("Listo", "Capacitación marcada como completada.", parent=self)
        self.mostrar_detalle(ident)

    # ---- agregar ---------------------------------------------------------------
    def _agregar(self):
        dlg = tk.Toplevel(self)
        dlg.title("Agregar capacitación")
        dlg.configure(bg=FONDO)
        dlg.resizable(False, False)
        dlg.transient(self.winfo_toplevel())

        tk.Label(dlg, text="Nombre de la capacitación:", bg=FONDO, fg=TEXTO,
                 font=(FUENTE, 10)).pack(anchor="w", padx=16, pady=(14, 2))
        nombre = tk.Entry(dlg, width=52, font=(FUENTE, 10), relief="flat",
                          highlightthickness=1, highlightbackground=TERRACOTA)
        nombre.pack(padx=16)
        tk.Label(dlg, text="Subtemas (uno por línea):", bg=FONDO, fg=TEXTO,
                 font=(FUENTE, 10)).pack(anchor="w", padx=16, pady=(10, 2))
        temas = tk.Text(dlg, width=52, height=8, font=(FUENTE, 10), relief="flat",
                        highlightthickness=1, highlightbackground=TERRACOTA, wrap="word")
        temas.pack(padx=16)
        tk.Label(dlg, text="El peso de cada subtema se reparte en partes iguales y suma 100.",
                 bg=FONDO, fg=TEXTO, font=(FUENTE, 9)).pack(anchor="w", padx=16, pady=(4, 8))

        def guardar():
            titulo = " ".join(nombre.get().split())
            lista = separar_subtemas(temas.get("1.0", "end"))
            if len(titulo) < 3 or len(titulo) > 150:
                return messagebox.showwarning("Revisa el formulario",
                                              "El nombre debe tener entre 3 y 150 caracteres.",
                                              parent=dlg)
            if not lista:
                return messagebox.showwarning("Revisa el formulario",
                                              "Escribe al menos un subtema.", parent=dlg)
            if len(lista) > 100 or any(len(t) > 100 for t in lista):
                return messagebox.showwarning("Revisa el formulario",
                                              "Máximo 100 subtemas, de hasta 100 caracteres cada uno.",
                                              parent=dlg)
            try:
                if _consulta("SELECT 1 FROM capacitaciones WHERE lower(nombre) = lower(%s)",
                             (titulo,)):
                    return messagebox.showwarning("Nombre repetido",
                                                  f"Ya existe una capacitación llamada «{titulo}».",
                                                  parent=dlg)
                self._insertar(titulo, lista)
            except Exception as e:
                return messagebox.showerror("Error de base de datos",
                                            f"No se pudo guardar.\n\n{e}", parent=dlg)
            dlg.destroy()
            self.mostrar_lista()

        fila = tk.Frame(dlg, bg=FONDO)
        fila.pack(pady=(0, 14))
        BotonPildora(fila, 130, 34, "Guardar", guardar, color=TERRACOTA).pack(side="left", padx=6)
        BotonPildora(fila, 130, 34, "Cancelar", dlg.destroy, color=CAFE).pack(side="left", padx=6)
        nombre.focus_set()
        dlg.update_idletasks()
        dlg.geometry(f"+{self.winfo_rootx() + 80}+{self.winfo_rooty() + 60}")
        dlg.grab_set()

    @staticmethod
    def _insertar(titulo, subtemas):
        """Crea la capacitacion y sus subtemas (pesos que suman 100) en una transaccion."""
        pesos = repartir_pesos(len(subtemas))
        conn = db.conectar()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO capacitaciones (nombre) VALUES (%s) "
                            "RETURNING id_capacitacion AS id", (titulo,))
                fila = cur.fetchone()
                ident = fila["id"] if isinstance(fila, dict) else fila[0]
                for nombre, peso in zip(subtemas, pesos):
                    cur.execute("INSERT INTO subtemas_capacitacion (id_capacitacion, nombre, "
                                "peso) VALUES (%s, %s, %s)", (ident, nombre, peso))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def crear_capacitaciones(parent, usuario=None):
    pantalla = PantallaCapacitaciones(parent, usuario)
    pantalla.pack(fill="both", expand=True)
    return pantalla


if __name__ == "__main__":
    raiz = tk.Tk()
    raiz.title("Vivero - Capacitaciones")
    raiz.geometry("1000x620")
    crear_capacitaciones(raiz, {"rol": "admin", "id_empleado": 1})
    raiz.mainloop()