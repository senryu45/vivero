"""enfermedades.py - Seccion ENFERMEDADES (diapositivas 14, 15 y 16).

Uso desde secciones.py:
    from enfermedades import crear_enfermedades
    "ENFERMEDADES": (crear_enfermedades, ("admin", "vendedor")),

Prueba suelta:  python enfermedades.py
"""
from sanidad import ENFERMEDADES, PantallaSanidad, probar


def crear_enfermedades(parent, usuario=None):
    pantalla = PantallaSanidad(parent, ENFERMEDADES, usuario)
    pantalla.pack(fill="both", expand=True)
    return pantalla


if __name__ == "__main__":
    probar(ENFERMEDADES)