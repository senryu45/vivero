"""Conexión y utilidades de PostgreSQL (viveros_db)."""
import os
from contextlib import closing

import bcrypt
import psycopg2
import psycopg2.errors
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()

# Texto de la pantalla de roles -> valor del ENUM rol_usuario
ROLES = {
    "Administrador": "admin",
    "Personal": "vendedor",
    "Cliente": "cliente",
}


class CorreoDuplicado(Exception):
    """El correo ya existe en la tabla usuarios."""

def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )



def consultar(sql, params=None, uno=False):
    """SELECT (o INSERT ... RETURNING). Devuelve lista de dicts, o un dict/None si uno=True."""
    with closing(conectar()) as con:
        with con, con.cursor(cursor_factory=RealDictCursor) as cur:   # 'with con' hace commit
            cur.execute(sql, params)
            return cur.fetchone() if uno else cur.fetchall()


def ejecutar(sql, params=None):
    """INSERT / UPDATE / DELETE. Devuelve las filas afectadas."""
    with closing(conectar()) as con:
        with con, con.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


def hash_contrasena(texto):
    return bcrypt.hashpw(texto.encode(), bcrypt.gensalt()).decode()


def validar_login(correo, contrasena, rol_pantalla):
    """Devuelve (usuario, error). error es None, 'credenciales' o 'rol'."""
    u = consultar(
        """SELECT id_usuario, nombre_completo, correo, contrasena_hash, rol
           FROM usuarios
           WHERE lower(correo) = lower(%s) AND activo""",
        (correo.strip(),), uno=True)
    if not u or not bcrypt.checkpw(contrasena.encode(), u["contrasena_hash"].encode()):
        return None, "credenciales"
    if u["rol"] != ROLES.get(rol_pantalla, rol_pantalla):
        return None, "rol"
    return u, None


def registrar_cliente(nombre, correo, contrasena, telefono=None):
    """Crea el usuario (rol cliente) y su fila en clientes en UNA transacción.

    Si algo falla, no se guarda nada. Lanza CorreoDuplicado si el correo ya existe.
    """
    con = conectar()
    try:
        with con:                                   # commit al salir, rollback si hay error
            with con.cursor() as cur:
                cur.execute(
                    """INSERT INTO usuarios (nombre_completo, correo, contrasena_hash,
                                             rol, telefono)
                       VALUES (%s, %s, %s, 'cliente', %s)
                       RETURNING id_usuario""",
                    (nombre.strip(), correo.strip(), hash_contrasena(contrasena),
                     telefono or None))
                id_usuario = cur.fetchone()[0]
                cur.execute("INSERT INTO clientes (id_usuario) VALUES (%s)",
                            (id_usuario,))
    except psycopg2.errors.UniqueViolation:
        raise CorreoDuplicado()
    finally:
        con.close()


def registrar_empleado(nombre, correo, contrasena, cargo=None, salario=None, telefono=None):
    """Crea el usuario (rol vendedor) y su fila en empleados en UNA transacción.

    Lanza CorreoDuplicado si el correo ya existe.
    """
    con = conectar()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    """INSERT INTO usuarios (nombre_completo, correo, contrasena_hash,
                                             rol, telefono)
                       VALUES (%s, %s, %s, 'vendedor', %s)
                       RETURNING id_usuario""",
                    (nombre.strip(), correo.strip(), hash_contrasena(contrasena),
                     telefono or None))
                id_usuario = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO empleados (id_usuario, cargo, salario) VALUES (%s, %s, %s)",
                    (id_usuario, cargo or None, salario))
    except psycopg2.errors.UniqueViolation:
        raise CorreoDuplicado()
    finally:
        con.close()

class EmpleadoConRegistros(Exception):
    """El empleado tiene ventas u otros registros y no se puede borrar."""


def actualizar_empleado(id_usuario, nombre, correo, contrasena=None,
                        cargo=None, salario=None, telefono=None):
    """Actualiza usuarios + empleados en UNA transacción (solo rol vendedor).

    Si contrasena viene vacía se conserva la actual.
    Lanza CorreoDuplicado si el correo ya lo usa otra cuenta.
    """
    con = conectar()
    try:
        with con:
            with con.cursor() as cur:
                if contrasena:
                    cur.execute(
                        """UPDATE usuarios
                           SET nombre_completo = %s, correo = %s, telefono = %s,
                               contrasena_hash = %s, fecha_actualizacion = CURRENT_TIMESTAMP
                           WHERE id_usuario = %s AND rol = 'vendedor'""",
                        (nombre.strip(), correo.strip(), telefono or None,
                         hash_contrasena(contrasena), id_usuario))
                else:
                    cur.execute(
                        """UPDATE usuarios
                           SET nombre_completo = %s, correo = %s, telefono = %s,
                               fecha_actualizacion = CURRENT_TIMESTAMP
                           WHERE id_usuario = %s AND rol = 'vendedor'""",
                        (nombre.strip(), correo.strip(), telefono or None, id_usuario))
                if cur.rowcount == 0:
                    raise LookupError("El empleado ya no existe o no es personal (vendedor).")
                cur.execute(
                    "UPDATE empleados SET cargo = %s, salario = %s WHERE id_usuario = %s",
                    (cargo or None, salario, id_usuario))
    except psycopg2.errors.UniqueViolation:
        raise CorreoDuplicado()
    finally:
        con.close()


def eliminar_empleado(id_usuario):
    """Borra empleados + usuarios en UNA transacción (solo rol vendedor).

    Lanza EmpleadoConRegistros si tiene ventas u otros datos ligados.
    Devuelve True si se borró, False si no existía.
    """
    con = conectar()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute(
                    """DELETE FROM empleados
                       WHERE id_usuario = %s
                         AND id_usuario IN (SELECT id_usuario FROM usuarios
                                            WHERE rol = 'vendedor')""",
                    (id_usuario,))
                cur.execute("DELETE FROM usuarios WHERE id_usuario = %s AND rol = 'vendedor'",
                            (id_usuario,))
                return cur.rowcount > 0
    except psycopg2.errors.ForeignKeyViolation:
        raise EmpleadoConRegistros()
    finally:
        con.close()