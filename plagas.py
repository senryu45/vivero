"""plagas.py - Seccion PLAGAS (diapositivas 12 y 13).

Uso desde secciones.py:
    from plagas import crear_plagas
    "PLAGAS": (crear_plagas, ("admin", "vendedor")),

Prueba suelta:  python plagas.py
"""
from sanidad import PLAGAS, PantallaSanidad, probar


def crear_plagas(parent, usuario=None):
    pantalla = PantallaSanidad(parent, PLAGAS, usuario)
    pantalla.pack(fill="both", expand=True)
    return pantalla


if __name__ == "__main__":
    probar(PLAGAS)