"""Validaciones compartidas: teléfono con selección de país.

Requiere:  pip install phonenumbers
"""
import re

import phonenumbers

# (nombre que ve el usuario, código ISO del país). Agrega o quita los que necesites.
PAISES = [
    ("México", "MX"), ("Estados Unidos", "US"), ("Canadá", "CA"),
    ("Guatemala", "GT"), ("Belice", "BZ"), ("El Salvador", "SV"),
    ("Honduras", "HN"), ("Nicaragua", "NI"), ("Costa Rica", "CR"),
    ("Panamá", "PA"), ("Cuba", "CU"), ("Rep. Dominicana", "DO"),
    ("Puerto Rico", "PR"), ("Colombia", "CO"), ("Venezuela", "VE"),
    ("Ecuador", "EC"), ("Perú", "PE"), ("Bolivia", "BO"), ("Chile", "CL"),
    ("Argentina", "AR"), ("Uruguay", "UY"), ("Paraguay", "PY"),
    ("Brasil", "BR"), ("España", "ES"), ("Portugal", "PT"), ("Francia", "FR"),
    ("Alemania", "DE"), ("Italia", "IT"), ("Reino Unido", "GB"),
    ("China", "CN"), ("Japón", "JP"), ("India", "IN"),
]

PAIS_POR_DEFECTO = "México (+52)"


def _etiqueta(nombre, region):
    return f"{nombre} (+{phonenumbers.country_code_for_region(region)})"


# Textos del menú desplegable: "México (+52)", "Estados Unidos (+1)", ...
ETIQUETAS_PAISES = [_etiqueta(n, r) for n, r in PAISES]
_REGION_POR_ETIQUETA = {_etiqueta(n, r): r for n, r in PAISES}


def region_de_etiqueta(etiqueta):
    """'México (+52)' -> 'MX'. Si no se reconoce, usa México."""
    return _REGION_POR_ETIQUETA.get(etiqueta, "MX")


def validar_telefono(texto, region="MX"):
    """Devuelve (telefono_e164, None) o (None, mensaje_de_error).

    texto:  lo que escribió la persona (puede traer espacios, guiones o paréntesis).
    region: país elegido en el menú ('MX', 'US', 'ES'...).
    El teléfono es opcional: texto vacío devuelve ("", None).
    Se guarda en formato internacional, por ejemplo +529621234567.
    """
    texto = texto.strip()
    if not texto:
        return "", None

    if not re.fullmatch(r"[0-9+() -]+", texto):
        return None, "El teléfono solo puede llevar números, espacios, guiones y paréntesis."

    codigo_pais = phonenumbers.country_code_for_region(region)
    try:
        if texto.startswith("+"):
            num = phonenumbers.parse(texto, None)          # ya trae su código de país
        else:
            num = phonenumbers.parse(texto, region)         # se interpreta según el país elegido
    except phonenumbers.NumberParseException:
        return None, "El teléfono no tiene un formato válido."

    if num.country_code != codigo_pais:
        return None, (f"El número empieza con +{num.country_code}, pero elegiste un país "
                      f"con código +{codigo_pais}. Cambia el país o corrige el número.")

    digitos = str(num.national_number)
    if region == "MX" and len(digitos) != 10:
        return None, "Un teléfono de México debe tener 10 dígitos."

    if not phonenumbers.is_valid_number(num):
        return None, "Ese número no existe en el plan de numeración del país elegido."

    # Descartar números de relleno: 5555555555, 1234567890, 9876543210...
    if len(digitos) >= 7 and (len(set(digitos)) <= 2
                              or digitos in "01234567890123456789"
                              or digitos in "98765432109876543210"):
        return None, "Escribe un número de teléfono real."

    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164), None


def separar_telefono(guardado):
    """'+529621234567' -> ('México (+52)', '9621234567'). Sirve para editar un registro."""
    if not guardado:
        return PAIS_POR_DEFECTO, ""
    try:
        num = phonenumbers.parse(guardado, None)
    except phonenumbers.NumberParseException:
        return PAIS_POR_DEFECTO, guardado
    region = phonenumbers.region_code_for_number(num)
    if region not in {r for _, r in PAISES}:
        region = next((r for _, r in PAISES
                       if phonenumbers.country_code_for_region(r) == num.country_code), None)
    if region is None:
        return PAIS_POR_DEFECTO, guardado          # país fuera de la lista: se deja tal cual
    nombre = next(n for n, r in PAISES if r == region)
    return _etiqueta(nombre, region), str(num.national_number)

