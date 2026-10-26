import re
import tkinter as tk
from tkinter import messagebox, ttk

import db
from comun import (ANCHO, ALTO, ANCHO_IZQ, FONDO_DERECHO, CAFE, TEXTO, FUENTE,
                   crear_panel_izquierdo)
from login import CampoRedondeado, BotonRedondeado, patron_correo, ANCHO_CAMPO
from validaciones import (ETIQUETAS_PAISES, PAIS_POR_DEFECTO, region_de_etiqueta,
                          validar_telefono)

patron_nombre = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]{3,150}$")
ANCHO_PAIS = 150      # ancho del menú de país; el campo de teléfono ocupa el resto


class pantalla_registro(tk.Frame):
    """Registro de nuevos clientes.

    al_registrado() se llama cuando la cuenta se creó correctamente.
    al_volver() regresa al login.
    """

    def __init__(self, master, al_registrado, al_volver):
        super().__init__(master, width=ANCHO, height=ALTO, bg=FONDO_DERECHO)
        self.al_registrado = al_registrado

        crear_panel_izquierdo(self)

        derecho = tk.Frame(self, bg=FONDO_DERECHO, width=ANCHO - ANCHO_IZQ, height=ALTO)
        derecho.place(x=ANCHO_IZQ, y=0)
        x_centro = (ANCHO - ANCHO_IZQ) / 2

        # Volver al login
        volver = tk.Label(derecho, text="← Volver", bg=FONDO_DERECHO, fg=TEXTO,
                          font=(FUENTE, 11), cursor="hand2")
        volver.place(x=24, y=20)
        volver.bind("<Button-1>", lambda e: al_volver())
        volver.bind("<Enter>", lambda e: volver.config(fg=CAFE))
        volver.bind("<Leave>", lambda e: volver.config(fg=TEXTO))

        tk.Label(derecho, text="Crear cuenta", bg=FONDO_DERECHO, fg=CAFE,
                 font=(FUENTE, 26, "bold")).place(x=x_centro, y=62, anchor="center")
        tk.Label(derecho, text="Registro de cliente", bg=FONDO_DERECHO, fg=TEXTO,
                 font=(FUENTE, 12)).place(x=x_centro, y=98, anchor="center")

        # Campos (misma clase que el login)
        self.campo_nombre = CampoRedondeado(derecho, "NOMBRE COMPLETO")
        self.campo_correo = CampoRedondeado(derecho, "CORREO")
        self.pais = tk.StringVar(value=PAIS_POR_DEFECTO)
        self.menu_pais = ttk.Combobox(derecho, textvariable=self.pais, state="readonly",
                                      values=ETIQUETAS_PAISES, font=(FUENTE, 10))
        self.campo_telefono = CampoRedondeado(derecho, "TELÉFONO",
                                              ancho=ANCHO_CAMPO - ANCHO_PAIS - 8)
        self.campo_clave = CampoRedondeado(derecho, "CONTRASEÑA", oculto=True)
        self.campo_confirmar = CampoRedondeado(derecho, "CONFIRMAR CONTRASEÑA", oculto=True)

        self.campos = [self.campo_nombre, self.campo_correo, self.campo_telefono,
                       self.campo_clave, self.campo_confirmar]
        y = 150
        for campo in self.campos:
            if campo is self.campo_telefono:
                # menú de país a la izquierda y el campo del teléfono a su lado
                izquierda = x_centro - ANCHO_CAMPO / 2
                self.menu_pais.place(x=izquierda, y=y, anchor="w",
                                     width=ANCHO_PAIS, height=30)
                campo.place(x=izquierda + ANCHO_CAMPO, y=y, anchor="e")
            else:
                campo.place(x=x_centro, y=y, anchor="center")
            y += 54

        tk.Label(derecho, text="Teléfono opcional · Contraseña: mínimo 8 caracteres, con letras y números",
                 bg=FONDO_DERECHO, fg=TEXTO, font=(FUENTE, 9)).place(
                     x=x_centro, y=y - 12, anchor="center")

        BotonRedondeado(derecho, "REGISTRARSE", self.registrar).place(
            x=x_centro, y=y + 38, anchor="center")

        # Enter avanza al siguiente campo; en el último, registra
        for i, campo in enumerate(self.campos):
            if i < len(self.campos) - 1:
                siguiente = self.campos[i + 1].entrada
                campo.entrada.bind("<Return>", lambda e, s=siguiente: s.focus_set())
            else:
                campo.entrada.bind("<Return>", lambda e: self.registrar())

    # ---------------- Validación ----------------
    def _validar(self):
        """Devuelve (datos, None) si todo es válido o (None, mensaje) si no."""
        nombre = self.campo_nombre.valor().strip()
        correo = self.campo_correo.valor().strip().lower()
        telefono = self.campo_telefono.valor().strip()
        clave = self.campo_clave.valor()
        confirmar = self.campo_confirmar.valor()

        if not nombre or not correo or not clave or not confirmar:
            return None, "Completa nombre, correo y contraseña."
        if not patron_nombre.match(nombre):
            return None, "El nombre solo puede tener letras y espacios (mínimo 3)."
        if not patron_correo.match(correo):
            return None, "Escribe un correo válido."
        telefono, error_tel = validar_telefono(telefono, region_de_etiqueta(self.pais.get()))
        if error_tel:
            return None, error_tel
        if len(clave) < 8 or not re.search(r"[A-Za-z]", clave) or not re.search(r"\d", clave):
            return None, "La contraseña debe tener mínimo 8 caracteres, con letras y números."
        if clave != confirmar:
            return None, "Las contraseñas no coinciden."
        return (nombre, correo, clave, telefono), None

    # ---------------- Guardar en la BD ----------------
    def registrar(self):
        datos, error = self._validar()
        if error:
            messagebox.showwarning("Registro", error)
            return

        nombre, correo, clave, telefono = datos
        try:
            db.registrar_cliente(nombre, correo, clave, telefono)
        except db.CorreoDuplicado:
            messagebox.showwarning("Correo en uso",
                                   "Ya existe una cuenta con ese correo.")
            return
        except Exception as e:
            messagebox.showerror("Error de base de datos",
                                 f"No se pudo crear la cuenta:\n{e}")
            return

        messagebox.showinfo("Cuenta creada",
                            "Tu cuenta se creó correctamente. Ya puedes iniciar sesión.")
        self.al_registrado()