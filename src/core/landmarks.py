
"""
Single Source of Truth para landmarks cefalométricos.

Define nombres, índices y funciones auxiliares para análisis cefalométrico.
Índices basados en el estándar del dataset Aariz (29 landmarks).
"""

from typing import Dict, Tuple, Optional

# Índices de landmarks (0-28) según estándar Aariz
LANDMARK_NAMES: Tuple[str, ...] = (
    "A", "ANS", "B", "Me", "N", "Or", "Pog",
    "PNS", "Pn", "R", "S", "Ar", "Co", "Gn",
    "Go", "Po", "LPM", "LIT", "LMT", "UPM",
    "UIA", "UIT", "UMT", "LIA", "Li", "Ls",
    "N'", "Pog'", "Sn"
)

NUM_LANDMARKS = len(LANDMARK_NAMES)

# Índices clave para análisis Steiner/Ricketts
IDX_SELLA = 10      # S
IDX_NASION = 4      # N
IDX_A_POINT = 0     # A
IDX_B_POINT = 2     # B
IDX_POGONION = 6    # Pog

# Mapeo nombre -> índice
NAME_TO_IDX: Dict[str, int] = {name: i for i, name in enumerate(LANDMARK_NAMES)}

# Nombres completos (opcional, para reportes)
FULL_NAMES: Dict[str, str] = {
    "A": "Punto A (Subespinale)",
    "ANS": "Anterior Nasal Superior",
    "B": "Punto B (Supramental)",
    "Me": "Mentón (Menton)",
    "N": "Nasion",
    "Or": "Orbitale",
    "Pog": "Pogonion",
    "PNS": "Posterior Nasal Spine",
    "Pn": "Prosthion",
    "R": "Ridge",
    "S": "Sella Turcica",
    "Ar": "Articulación",
    "Co": "Cóndilo",
    "Gn": "Gnathion",
    "Go": "Gonion",
    "Po": "Porion",
    "LPM": "Low Point Mandible",
    "LIT": "Lower Incisor Tip",
    "LMT": "Lower Molar Tip",
    "UPM": "Upper Molar Tip",
    "UIA": "Upper Incisor Apex",
    "UIT": "Upper Incisor Tip",
    "UMT": "Upper Molar Tip",
    "LIA": "Lower Incisor Apex",
    "Li": "Lower Incisor",
    "Ls": "Lips",
    "N'": "N Prime",
    "Pog'": "Pogonion Prime",
    "Sn": "Subnasale"
}


def get_index(name: str) -> Optional[int]:
    """
    Obtiene el índice de un landmark por nombre.

    Args:
        name: Nombre del landmark (ej. 'S', 'N', 'A', 'B', 'Go')

    Returns:
        Índice (0-28) o None si no existe.
    """
    return NAME_TO_IDX.get(name)


def get_name(index: int) -> str:
    """
    Obtiene el nombre de un landmark por índice.

    Args:
        index: Índice del landmark (0-28)

    Returns:
        Nombre del landmark o 'LM{index}' si fuera de rango.
    """
    if 0 <= index < NUM_LANDMARKS:
        return LANDMARK_NAMES[index]
    return f"LM{index}"


def validate_indices(indices):
    """
    Valida que todos los índices estén en rango [0, NUM_LANDMARKS).

    Args:
        indices: Lista o tupla de índices

    Raises:
        ValueError: Si algún índice es inválido.
    """
    for idx in indices:
        if not (0 <= idx < NUM_LANDMARKS):
            raise ValueError(
                f"Índice {idx} fuera de rango. "
                f"Debe estar en [0, {NUM_LANDMARKS-1}]"
            )


# Tuplas nombradas para ángulos comunes
LANDMARK_ANGLE_SNA = (IDX_SELLA, IDX_NASION, IDX_A_POINT)  # S-N-A
LANDMARK_ANGLE_SNB = (IDX_SELLA, IDX_NASION, IDX_B_POINT)  # S-N-B
LANDMARK_ANGLE_POG = (IDX_SELLA, IDX_NASION, IDX_POGONION)  # S-N-Pog


def angle_key_points(key1: str, key2: str, key3: str) -> Tuple[int, int, int]:
    """
    Devuelve los índices para tres puntos clave dados por nombre.

    Args:
        key1, key2, key3: Nombres de landmarks

    Returns:
        Tupla (idx1, idx2, idx3)

    Raises:
        KeyError: Si algún nombre no existe.
    """
    return (NAME_TO_IDX[key1], NAME_TO_IDX[key2], NAME_TO_IDX[key3])
