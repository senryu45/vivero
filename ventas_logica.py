"""ventas_logica.py - Reglas puras de VENTAS y CAPACITACIONES.

No importa Tkinter ni la base de datos, asi que se puede probar sola:
    python ventas_logica.py
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MESES = ("ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic")

# Estados reales de la base -> texto que muestra el diseno
ESTADO_VISIBLE = {"pagada": "completada", "pendiente": "pendiente",
                  "cancelada": "cancelada"}
METODOS_PAGO = ("Efectivo", "Tarjeta", "Transferencia")
MAX_CANTIDAD = 9999


def fecha_corta(valor):
    """date/datetime -> '28/sep/26' (como en el diseno)."""
    if isinstance(valor, datetime):
        valor = valor.date()
    if not isinstance(valor, date):
        return "" if valor is None else str(valor)
    return f"{valor.day:02d}/{MESES[valor.month - 1]}/{valor.year % 100:02d}"


def fecha_larga(valor):
    """date -> '28/09/2026' (lo que se escribe en el formulario)."""
    if isinstance(valor, datetime):
        valor = valor.date()
    return f"{valor.day:02d}/{valor.month:02d}/{valor.year}"


def parsear_fecha(texto, hoy=None):
    """Devuelve (date, None) o (None, mensaje_de_error).

    Acepta dd/mm/aaaa, dd-mm-aaaa, dd/mm/aa y aaaa-mm-dd. No permite fechas futuras.
    """
    texto = (texto or "").strip()
    if not texto:
        return None, "Escribe la fecha de la venta."
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2}|\d{4})", texto)
    if m:
        d, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
        if not m:
            return None, "La fecha debe tener el formato dd/mm/aaaa (por ejemplo 28/09/2026)."
        a, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if a < 100:
        a += 2000
    try:
        f = date(a, mo, d)
    except ValueError:
        return None, "La fecha escrita no existe en el calendario."
    hoy = hoy or date.today()
    if f > hoy:
        return None, "La fecha de la venta no puede ser futura."
    if f.year < 2000:
        return None, "La fecha es demasiado antigua."
    return f, None


def parsear_cantidad(texto, disponible=None):
    """Devuelve (entero, None) o (None, mensaje_de_error)."""
    texto = (texto or "").strip()
    if not texto:
        return None, "Escribe la cantidad."
    if not texto.isdigit():
        return None, "La cantidad debe ser un número entero."
    n = int(texto)
    if n < 1:
        return None, "La cantidad debe ser al menos 1."
    if n > MAX_CANTIDAD:
        return None, f"La cantidad máxima por venta es {MAX_CANTIDAD}."
    if disponible is not None and n > disponible:
        return None, f"Solo hay {disponible} disponibles de esa planta."
    return n, None


def calcular_total(cantidad, precio):
    """cantidad * precio como Decimal con dos decimales."""
    try:
        total = Decimal(str(precio)) * int(cantidad)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Precio o cantidad no válidos")
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def formato_dinero(valor):
    """150 -> '$150';  150.5 -> '$150.50'."""
    try:
        d = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return "" if valor is None else str(valor)
    if d == d.to_integral_value():
        return f"${int(d):,}"
    return f"${d:,.2f}"


def repartir_pesos(n):
    """Reparte 100 entre n subtemas; la suma siempre es exactamente 100.

    Devuelve la lista de pesos (los primeros reciben el sobrante) o lanza
    ValueError si n no esta entre 1 y 100.
    """
    if not 1 <= n <= 100:
        raise ValueError("Debe haber entre 1 y 100 subtemas")
    base, resto = divmod(100, n)
    return [base + 1] * resto + [base] * (n - resto)


def separar_subtemas(texto):
    """Texto con un subtema por linea (o separados por coma) -> lista limpia.

    Quita vacios y repetidos (sin distinguir mayusculas), conserva el orden.
    """
    vistos, salida = set(), []
    for crudo in re.split(r"[\n,;]+", texto or ""):
        item = " ".join(crudo.split())
        if item and item.lower() not in vistos:
            vistos.add(item.lower())
            salida.append(item)
    return salida


def _probar():
    hoy = date(2026, 10, 31)
    assert fecha_corta(date(2026, 9, 28)) == "28/sep/26"
    assert fecha_larga(date(2026, 9, 8)) == "08/09/2026"
    assert parsear_fecha("28/09/2026", hoy) == (date(2026, 9, 28), None)
    assert parsear_fecha("28-9-26", hoy)[0] == date(2026, 9, 28)
    assert parsear_fecha("2026-09-28", hoy)[0] == date(2026, 9, 28)
    assert parsear_fecha("31/11/2026", hoy)[0] is None      # noviembre no tiene 31
    assert parsear_fecha("01/11/2026", hoy)[0] is None      # futura
    assert parsear_fecha("29", hoy)[0] is None              # el caso del diseno
    assert parsear_fecha("", hoy)[0] is None
    assert parsear_cantidad("3", 5) == (3, None)
    assert parsear_cantidad("6", 5)[0] is None
    assert parsear_cantidad("0")[0] is None
    assert parsear_cantidad("2.5")[0] is None
    assert parsear_cantidad("-1")[0] is None
    assert parsear_cantidad("10000")[0] is None
    assert calcular_total(3, "50.00") == Decimal("150.00")
    assert calcular_total(3, 19.99) == Decimal("59.97")
    assert formato_dinero(150) == "$150"
    assert formato_dinero(Decimal("150.50")) == "$150.50"
    assert formato_dinero(1234.5) == "$1,234.50"
    for n in range(1, 101):
        p = repartir_pesos(n)
        assert len(p) == n and sum(p) == 100 and min(p) >= 1, n
    assert repartir_pesos(3) == [34, 33, 33]
    try:
        repartir_pesos(0)
        raise AssertionError("debio fallar")
    except ValueError:
        pass
    assert separar_subtemas("Riego\nSuelo, riego ;  Revisión  de plantas\n\n") == \
        ["Riego", "Suelo", "Revisión de plantas"]
    print("ventas_logica: todas las pruebas pasaron")


if __name__ == "__main__":
    _probar()