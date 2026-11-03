"""Reglas compartidas para etiquetas de tickets y filtros de búsqueda."""
import unicodedata


def normalize_labels(values: list[str]) -> list[str]:
    result = []
    for value in values:
        label = " ".join(unicodedata.normalize("NFKC", value).split()).casefold()
        if not label or len(label) > 40 or "," in label or any(unicodedata.category(c).startswith("C") for c in label):
            raise ValueError("Cada etiqueta debe tener entre 1 y 40 caracteres visibles, sin comas")
        if label not in result:
            result.append(label)
    if len(result) > 10:
        raise ValueError("Se permiten hasta 10 etiquetas por ticket")
    return result
