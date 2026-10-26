"""Crea el primer administrador. Ejecutar una sola vez: python crear_admin.py"""
import getpass

import db

CORREO = input("Correo del administrador: ").strip()
PASSWORD = getpass.getpass("Contraseña del administrador: ")
CONFIRMAR = getpass.getpass("Repite la contraseña: ")

if not CORREO or not PASSWORD:
    raise SystemExit("El correo y la contraseña son obligatorios.")
if PASSWORD != CONFIRMAR:
    raise SystemExit("Las contraseñas no coinciden.")

try:
    usuario = db.consultar(
        """INSERT INTO usuarios (nombre_completo, correo, contrasena_hash, rol)
           VALUES (%s, %s, %s, 'admin') RETURNING id_usuario""",
        ("Administrador", CORREO, db.hash_contrasena(PASSWORD)), uno=True)
except db.psycopg2.errors.UniqueViolation:
    raise SystemExit("Ese correo ya está registrado.")

db.ejecutar("INSERT INTO empleados (id_usuario, cargo) VALUES (%s, 'Administrador')",
            (usuario["id_usuario"],))
print(f"Administrador creado: {CORREO}")