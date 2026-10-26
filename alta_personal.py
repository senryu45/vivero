import re
import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import ttk, messagebox

import db
from login import patron_correo
from validaciones import (ETIQUETAS_PAISES, PAIS_POR_DEFECTO, region_de_etiqueta,
                          separar_telefono, validar_telefono)

VERDE_OSCURO = "#3F5A1A"
FONDO_SECCION = "#C5C7B5"
CAFE = "#99553A"
ROJO = "#A63D2F"
GRIS = "#7A7A6E"
BLANCO = "#FFFFFF"
FUENTE = "Open Sans"

patron_nombre = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]{3,150}$")

NOTA_ALTA = "Contraseña: mínimo 8 caracteres, con letras y números"
NOTA_EDICION = "Contraseña: déjala vacía para conservar la actual"


class AltaPersonal(tk.Frame):
    """Gestión de personal (solo administradores): alta, edición, baja y activar/desactivar."""

    def __init__(self, master, datos=None):
        super().__init__(master, bg=FONDO_SECCION)
        self.datos = datos
        self.editando = None          # id_usuario que se está editando (None = alta nueva)

        # ---------------- Formulario (izquierda) ----------------
        izq = tk.Frame(self, bg=FONDO_SECCION)
        izq.place(x=0, y=0, width=400, height=490)

        self.titulo = tk.Label(izq, text="Alta de personal", bg=FONDO_SECCION, fg=CAFE,
                               font=(FUENTE, 20, "bold"))
        self.titulo.pack(anchor="w", padx=24, pady=(16, 6))

        self.form = tk.Frame(izq, bg=FONDO_SECCION)
        self.form.pack(fill="x", padx=18)
        self.form.columnconfigure((0, 1), weight=1, uniform="col")

        self.pais = tk.StringVar(value=PAIS_POR_DEFECTO)
        self.e_nombre = self._campo(0, 0, "Nombre completo", span=2)
        self.e_correo = self._campo(1, 0, "Correo", span=2)
        self.e_telefono = self._campo_telefono(2)
        self.e_cargo = self._campo(3, 0, "Cargo (opcional)")
        self.e_salario = self._campo(3, 1, "Salario (opcional)")
        self.e_clave = self._campo(4, 0, "Contraseña", oculto=True)
        self.e_confirmar = self._campo(4, 1, "Confirmar contraseña", oculto=True)
        self.entradas = [self.e_nombre, self.e_correo, self.e_telefono, self.e_cargo,
                         self.e_salario, self.e_clave, self.e_confirmar]

        self.nota = tk.Label(self.form, text=NOTA_ALTA, bg=FONDO_SECCION,
                             fg=VERDE_OSCURO, font=(FUENTE, 9))
        self.nota.grid(row=5, column=0, columnspan=2, sticky="w", padx=6)

        fila_botones = tk.Frame(self.form, bg=FONDO_SECCION)
        fila_botones.grid(row=6, column=0, columnspan=2, sticky="we", padx=6, pady=(10, 0))
        self.btn_guardar = tk.Button(fila_botones, text="Registrar personal",
                                     command=self.registrar, bg=VERDE_OSCURO, fg=BLANCO,
                                     relief="flat", cursor="hand2",
                                     font=(FUENTE, 11, "bold"), pady=6)
        self.btn_guardar.pack(side="left", fill="x", expand=True)
        self.btn_cancelar = tk.Button(fila_botones, text="Cancelar",
                                      command=self.cancelar_edicion, bg=GRIS, fg=BLANCO,
                                      relief="flat", cursor="hand2",
                                      font=(FUENTE, 11), pady=6, padx=12)

        # Enter avanza al siguiente campo; en el último, guarda
        for i, entrada in enumerate(self.entradas):
            if i < len(self.entradas) - 1:
                siguiente = self.entradas[i + 1]
                entrada.bind("<Return>", lambda e, s=siguiente: s.focus_set())
            else:
                entrada.bind("<Return>", lambda e: self.registrar())

        # ---------------- Lista de empleados (derecha) ----------------
        der = tk.Frame(self, bg=FONDO_SECCION)
        der.place(x=400, y=0, width=600, height=490)

        tk.Label(der, text="Empleados", bg=FONDO_SECCION, fg=CAFE,
                 font=(FUENTE, 20, "bold")).pack(anchor="w", padx=8, pady=(16, 6))

        marco = tk.Frame(der, bg=FONDO_SECCION)
        marco.pack(fill="both", expand=True, padx=(8, 24))
        columnas = [("Nombre", "nombre", 170), ("Correo", "correo", 190),
                    ("Cargo", "cargo", 100), ("Rol", "rol", 70), ("Activo", "activo", 55)]
        self.tree = ttk.Treeview(marco, show="headings", selectmode="browse",
                                 columns=[c[1] for c in columnas])
        for encabezado, clave, ancho in columnas:
            self.tree.heading(clave, text=encabezado)
            self.tree.column(clave, width=ancho, anchor="w")
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=barra.set)
        self.tree.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.editar())

        botones = tk.Frame(der, bg=FONDO_SECCION)
        botones.pack(fill="x", padx=(8, 24), pady=10)
        tk.Button(botones, text="Editar", command=self.editar,
                  bg=VERDE_OSCURO, fg=BLANCO, relief="flat", padx=14, pady=4,
                  font=(FUENTE, 10)).pack(side="left")
        tk.Button(botones, text="Eliminar", command=self.eliminar,
                  bg=ROJO, fg=BLANCO, relief="flat", padx=14, pady=4,
                  font=(FUENTE, 10)).pack(side="left", padx=(8, 0))
        tk.Button(botones, text="Activar / Desactivar", command=self.alternar_activo,
                  bg=CAFE, fg=BLANCO, relief="flat", padx=14, pady=4,
                  font=(FUENTE, 10)).pack(side="left", padx=(8, 0))
        tk.Button(botones, text="Actualizar", command=self.cargar,
                  bg=GRIS, fg=BLANCO, relief="flat", padx=14, pady=4,
                  font=(FUENTE, 10)).pack(side="right")

        self.cargar()

    # ---------------- Utilidades de interfaz ----------------
    def _campo(self, fila, col, texto, span=1, oculto=False):
        marco = tk.Frame(self.form, bg=FONDO_SECCION)
        marco.grid(row=fila, column=col, columnspan=span, sticky="we", padx=6, pady=3)
        tk.Label(marco, text=texto, bg=FONDO_SECCION, fg=VERDE_OSCURO,
                 font=(FUENTE, 9)).pack(anchor="w")
        entrada = tk.Entry(marco, font=(FUENTE, 11), relief="flat", bg=BLANCO,
                           show="•" if oculto else "")
        entrada.pack(fill="x", ipady=4)
        return entrada

    def _campo_telefono(self, fila):
        """Teléfono con menú desplegable de país a su izquierda."""
        marco = tk.Frame(self.form, bg=FONDO_SECCION)
        marco.grid(row=fila, column=0, columnspan=2, sticky="we", padx=6, pady=3)
        tk.Label(marco, text="Teléfono (opcional) — elige el país del número",
                 bg=FONDO_SECCION, fg=VERDE_OSCURO, font=(FUENTE, 9)).pack(anchor="w")
        fila_tel = tk.Frame(marco, bg=FONDO_SECCION)
        fila_tel.pack(fill="x")
        ttk.Combobox(fila_tel, textvariable=self.pais, state="readonly", width=18,
                     values=ETIQUETAS_PAISES, font=(FUENTE, 10)).pack(
                         side="left", ipady=3, padx=(0, 6))
        entrada = tk.Entry(fila_tel, font=(FUENTE, 11), relief="flat", bg=BLANCO)
        entrada.pack(side="left", fill="x", expand=True, ipady=4)
        return entrada

    @staticmethod
    def _poner(entrada, texto):
        entrada.delete(0, tk.END)
        entrada.insert(0, texto or "")

    def _limpiar(self):
        for entrada in self.entradas:
            entrada.delete(0, tk.END)
        self.pais.set(PAIS_POR_DEFECTO)
        self.e_nombre.focus_set()

    def _modo_edicion(self, activo):
        """Cambia textos y botones del formulario entre 'alta' y 'edición'."""
        if activo:
            self.titulo.config(text="Editar personal")
            self.btn_guardar.config(text="Guardar cambios")
            self.nota.config(text=NOTA_EDICION)
            self.btn_cancelar.pack(side="left", padx=(8, 0))
        else:
            self.editando = None
            self.titulo.config(text="Alta de personal")
            self.btn_guardar.config(text="Registrar personal")
            self.nota.config(text=NOTA_ALTA)
            self.btn_cancelar.pack_forget()

    def cancelar_edicion(self):
        self._modo_edicion(False)
        self._limpiar()

    # ---------------- Lista ----------------
    def cargar(self):
        try:
            filas = db.consultar(
                """SELECT u.id_usuario, u.nombre_completo, u.correo, e.cargo, u.rol,
                          CASE WHEN u.activo THEN 'Sí' ELSE 'No' END AS activo
                   FROM empleados e
                   JOIN usuarios u USING (id_usuario)
                   ORDER BY u.nombre_completo""")
        except Exception as ex:
            messagebox.showerror("Error de base de datos", str(ex))
            return
        self.tree.delete(*self.tree.get_children())
        for f in filas:
            self.tree.insert("", "end", iid=str(f["id_usuario"]), values=(
                f["nombre_completo"], f["correo"], f["cargo"] or "", f["rol"], f["activo"]))

    def _seleccionado(self, accion):
        """Devuelve (id_usuario, nombre) del vendedor seleccionado o (None, None)."""
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showinfo("Personal", f"Selecciona un empleado para {accion}.")
            return None, None
        valores = self.tree.item(seleccion[0], "values")
        if valores[3] != "vendedor":
            messagebox.showwarning("Personal",
                                   f"Solo se puede {accion} al personal (vendedor).")
            return None, None
        return int(seleccion[0]), valores[0]

    def alternar_activo(self):
        id_usuario, _ = self._seleccionado("activar o desactivar")
        if id_usuario is None:
            return
        try:
            db.ejecutar(
                """UPDATE usuarios SET activo = NOT activo,
                                       fecha_actualizacion = CURRENT_TIMESTAMP
                   WHERE id_usuario = %s AND rol = 'vendedor'""", (id_usuario,))
        except Exception as ex:
            messagebox.showerror("Error de base de datos", str(ex))
            return
        self.cargar()
        if self.tree.exists(str(id_usuario)):
            self.tree.selection_set(str(id_usuario))

    # ---------------- Editar ----------------
    def editar(self):
        id_usuario, _ = self._seleccionado("editar")
        if id_usuario is None:
            return
        try:
            f = db.consultar(
                """SELECT u.nombre_completo, u.correo, u.telefono, e.cargo, e.salario
                   FROM usuarios u JOIN empleados e USING (id_usuario)
                   WHERE u.id_usuario = %s AND u.rol = 'vendedor'""",
                (id_usuario,), uno=True)
        except Exception as ex:
            messagebox.showerror("Error de base de datos", str(ex))
            return
        if f is None:
            messagebox.showwarning("Personal", "Ese empleado ya no existe.")
            self.cargar()
            return

        self._limpiar()
        pais, nacional = separar_telefono(f["telefono"])
        self.pais.set(pais)
        self._poner(self.e_nombre, f["nombre_completo"])
        self._poner(self.e_correo, f["correo"])
        self._poner(self.e_telefono, nacional)
        self._poner(self.e_cargo, f["cargo"])
        self._poner(self.e_salario, "" if f["salario"] is None else str(f["salario"]))
        self.editando = id_usuario
        self._modo_edicion(True)
        self.e_nombre.focus_set()

    # ---------------- Eliminar ----------------
    def eliminar(self):
        id_usuario, nombre = self._seleccionado("eliminar")
        if id_usuario is None:
            return
        if not messagebox.askyesno(
                "Eliminar personal",
                f"¿Eliminar a {nombre}?\n\nSe borrará su cuenta y esta acción no se puede deshacer.",
                icon="warning"):
            return
        try:
            borrado = db.eliminar_empleado(id_usuario)
        except db.EmpleadoConRegistros:
            messagebox.showwarning(
                "No se puede eliminar",
                f"{nombre} tiene ventas u otros registros asociados.\n\n"
                "Mejor desactívalo con «Activar / Desactivar» para que ya no pueda entrar.")
            return
        except Exception as ex:
            messagebox.showerror("Error de base de datos",
                                 f"No se pudo eliminar al empleado:\n{ex}")
            return
        if not borrado:
            messagebox.showwarning("Personal", "Ese empleado ya no existía.")
        if self.editando == id_usuario:
            self.cancelar_edicion()
        self.cargar()

    # ---------------- Validación y guardado ----------------
    def _validar(self):
        """Devuelve (datos, None) si todo es válido o (None, mensaje) si no."""
        nombre = self.e_nombre.get().strip()
        correo = self.e_correo.get().strip().lower()
        telefono = self.e_telefono.get().strip()
        cargo = self.e_cargo.get().strip()
        salario_txt = self.e_salario.get().strip().replace(",", "")
        clave = self.e_clave.get()
        confirmar = self.e_confirmar.get()
        en_edicion = self.editando is not None

        if not nombre or not correo:
            return None, "Completa nombre y correo."
        if not en_edicion and (not clave or not confirmar):
            return None, "Completa nombre, correo y contraseña."
        if not patron_nombre.match(nombre):
            return None, "El nombre solo puede tener letras y espacios (mínimo 3)."
        if not patron_correo.match(correo):
            return None, "Escribe un correo válido."
        telefono, error_tel = validar_telefono(telefono, region_de_etiqueta(self.pais.get()))
        if error_tel:
            return None, error_tel
        if len(cargo) > 100:
            return None, "El cargo no puede pasar de 100 caracteres."

        salario = None
        if salario_txt:
            try:
                salario = Decimal(salario_txt)
            except InvalidOperation:
                return None, "El salario debe ser un número."
            if salario < 0 or salario > Decimal("99999999.99"):
                return None, "El salario debe estar entre 0 y 99,999,999.99."
            salario = salario.quantize(Decimal("0.01"))

        # En edición la contraseña es opcional: vacía = conservar la actual
        if clave or confirmar or not en_edicion:
            if len(clave) < 8 or not re.search(r"[A-Za-z]", clave) or not re.search(r"\d", clave):
                return None, "La contraseña debe tener mínimo 8 caracteres, con letras y números."
            if clave != confirmar:
                return None, "Las contraseñas no coinciden."
        return (nombre, correo, clave, cargo, salario, telefono), None

    def registrar(self):
        """Botón principal: da de alta o guarda cambios, según el modo."""
        datos, error = self._validar()
        if error:
            messagebox.showwarning("Personal", error)
            return
        nombre, correo, clave, cargo, salario, telefono = datos

        if self.editando is not None:
            try:
                db.actualizar_empleado(self.editando, nombre, correo, clave or None,
                                       cargo, salario, telefono)
            except db.CorreoDuplicado:
                messagebox.showwarning("Correo en uso", "Ya existe una cuenta con ese correo.")
                return
            except Exception as ex:
                messagebox.showerror("Error de base de datos",
                                     f"No se pudo actualizar al empleado:\n{ex}")
                return
            id_editado = self.editando
            messagebox.showinfo("Personal", f"Los datos de {nombre} se actualizaron.")
            self.cancelar_edicion()
            self.cargar()
            if self.tree.exists(str(id_editado)):
                self.tree.selection_set(str(id_editado))
            return

        try:
            db.registrar_empleado(nombre, correo, clave, cargo, salario, telefono)
        except db.CorreoDuplicado:
            messagebox.showwarning("Correo en uso", "Ya existe una cuenta con ese correo.")
            return
        except Exception as ex:
            messagebox.showerror("Error de base de datos",
                                 f"No se pudo registrar al empleado:\n{ex}")
            return

        messagebox.showinfo("Alta de personal", f"{nombre} fue registrado como personal.")
        self._limpiar()
        self.cargar()