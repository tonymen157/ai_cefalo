"""
Modulo de geometria analitica cefalométrica.

Calculo de angulos, distancias y analisis de Steiner (SNA, SNB, ANB)
utilizando nombres de landmarks desde src.core.landmarks.

Autor: AI-Cefalo - Fase 4
Fecha: 2026-04-27
CORREGIDO: Vértices de Steiner corregidos (Nasion como vértice).
"""

from typing import Dict, Tuple, Optional
import numpy as np

from src.core.landmarks import NAME_TO_IDX, LANDMARK_NAMES, FULL_NAMES
from src.core.config import NUM_LANDMARKS, INPUT_SIZE_WH


# ============================================================================
# Funciones puras de geometria
# ============================================================================

def calculate_angle(
    point_a: Tuple[float, float],
    vertex: Tuple[float, float],
    point_b: Tuple[float, float],
    en_grados: bool = True
) -> float:
    """
    Calcula el angulo entre dos vectores: (vertex->point_a) y (vertex->point_b).

    El angulo se mide en el vértice entre los dos puntos.

    Usa producto escalar:
        cos(theta) = (v1·v2) / (|v1|·|v2|)
    donde v1 = point_a - vertex, v2 = point_b - vertex.

    Args:
        point_a: primer punto
        vertex: vertice del angulo
        point_b: segundo punto
        en_grados: si True devuelve grados, si False radianes

    Returns:
        Angulo en el vertice.
    """
    v1 = np.array([point_a[0] - vertex[0], point_a[1] - vertex[1]], dtype=np.float64)
    v2 = np.array([point_b[0] - vertex[0], point_b[1] - vertex[1]], dtype=np.float64)

    norma_v1 = np.linalg.norm(v1)
    norma_v2 = np.linalg.norm(v2)

    if norma_v1 == 0 or norma_v2 == 0:
        return 0.0

    cos_theta = np.clip(np.dot(v1, v2) / (norma_v1 * norma_v2), -1.0, 1.0)
    angulo = np.arccos(cos_theta)

    if en_grados:
        angulo = np.degrees(angulo)

    return float(angulo)


def distancia_euclidiana(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """
    Calcula la distancia euclidiana (L2) entre dos puntos 2D.

    Args:
        p1: (x, y) primer punto
        p2: (x, y) segundo punto

    Returns:
        Distancia en píxeles (o mm si las coordenadas están calibradas).
    """
    return float(np.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2))


def distancia_landmarks(
    coords: np.ndarray,
    nombre1: str,
    nombre2: str
) -> float:
    """
    Distancia entre dos landmarks dados sus nombres.

    Args:
        coords: array (N, 2) de coordenadas, N >= número del landmark
        nombre1: nombre del primer landmark (p. ej. "S")
        nombre2: nombre del segundo landmark (p. ej. "N")

    Returns:
        Distancia euclidiana.
    """
    idx1 = NAME_TO_IDX[nombre1]
    idx2 = NAME_TO_IDX[nombre2]
    p1 = (coords[idx1, 0], coords[idx1, 1])
    p2 = (coords[idx2, 0], coords[idx2, 1])
    return distancia_euclidiana(p1, p2)


def angulo_landmarks(
    coords: np.ndarray,
    vertice: str,
    extremo1: str,
    extremo2: str
) -> float:
    """
    Angulo entre tres landmarks, con el vertice en el centro.

    Args:
        coords: array (N, 2) de coordenadas
        vertice: nombre del landmark que hace de vertice
        extremo1: primer extremo
        extremo2: segundo extremo

    Returns:
        Angulo en grados.
    """
    idx_v = NAME_TO_IDX[vertice]
    idx_1 = NAME_TO_IDX[extremo1]
    idx_2 = NAME_TO_IDX[extremo2]
    p_v = (coords[idx_v, 0], coords[idx_v, 1])
    p_1 = (coords[idx_1, 0], coords[idx_1, 1])
    p_2 = (coords[idx_2, 0], coords[idx_2, 1])
    return calculate_angle(p_1, p_v, p_2, en_grados=True)


# ============================================================================
# Clase analisis cefalometrico de Steiner (CORREGIDO)
# ============================================================================

class CephalometricAnalysis:
    """
    Analisis cefalometrico estandar (Steiner / Ricketts).

    Calculo automatico de angulos clave a partir de 29 landmarks
    (estandar Aariz):

    - SNA: angulo en N (Nasion) entre S-N y N-A (evalua maxilar)
    - SNB: angulo en N (Nasion) entre S-N y N-B (evalua mandibula)
    - ANB: diferencia SNA - SNB (clase esqueletica)

    Atributos
    ----------
    coords : np.ndarray
        Array (29, 2) con coordenadas (x, y) normalizadas [0, 1]
        o en pixeles.
    nombre_imagen : str
        Nombre del archivo de la radiografia.
    escala_mm : float | None
        Pixel size (mm/pixel) para conversion a milimetros.
        Si es None, las distancias se reportan en pixeles.
    """

    ANGULOS_STEINER = {
        "SNA": ("S", "N", "A"),
        "SNB": ("S", "N", "B"),
        "ANB": ("A", "N", "B"),
    }

    NORMATIVOS = {
        "SNA": ("82.0 +/- 2.0", 80.0, 84.0),
        "SNB": ("80.0 +/- 2.0", 78.0, 82.0),
        "ANB": ("2.0 +/- 2.0", 0.0, 4.0),  # Clase I: 0.0 a 4.0
    }

    def __init__(
        self,
        coords: np.ndarray,
        nombre_imagen: str = "imagen",
        escala_mm: Optional[float] = None
    ):
        if coords.shape[0] != len(LANDMARK_NAMES):
            raise ValueError(
                f"Se esperaban {len(LANDMARK_NAMES)} landmarks, "
                f"se recibieron {coords.shape[0]}"
            )
        self.coords = coords.astype(np.float64)
        self.nombre_imagen = nombre_imagen
        self.escala_mm = escala_mm

    @property
    def num_landmarks(self) -> int:
        return self.coords.shape[0]

    @property
    def pixel_size(self) -> Optional[float]:
        return self.escala_mm

    def distancia(self, nombre1: str, nombre2: str) -> float:
        return distancia_landmarks(self.coords, nombre1, nombre2)

    def angulo(self, vertice: str, extremo1: str, extremo2: str) -> float:
        return angulo_landmarks(self.coords, vertice, extremo1, extremo2)

    # --- ANGULOS DE STEINER (con vertice CORRECTO en Nasion) ---
    def angulo_sna(self) -> float:
        """
        SNA = angulo en N (Nasion) entre los puntos S (Sella) y A (Punto A).

        Forma correcta: angulo S-N-A con vertice en N.
        Mide la posicion anteroposterior del maxilar superior.
        Normativo: 82.0 +/- 2.0 grados.
        """
        # Vértice = N (índice IDX_NASION), extremos = S y A
        return angulo_landmarks(self.coords, "N", "S", "A")

    def angulo_snb(self) -> float:
        """
        SNB = angulo en N (Nasion) entre los puntos S (Sella) y B (Punto B).

        Forma correcta: angulo S-N-B con vertice en N.
        Mide la posicion anteroposterior de la mandibula.
        Normativo: 80.0 +/- 2.0 grados.
        """
        # Vértice = N (índice IDX_NASION), extremos = S y B
        return angulo_landmarks(self.coords, "N", "S", "B")

    def angulo_anb(self) -> float:
        """
        ANB = diferencia SNA - SNB.

        Clase esqueletica:
        - Clase I:   ANB = 2.0 +/- 2.0 (0.0 a 4.0)
        - Clase II:  ANB > 4.0 (maxilar relativo prominente)
        - Clase III: ANB < 0.0 (mandibula relativo prominente)
        """
        sna = self.angulo_sna()
        snb = self.angulo_snb()
        return sna - snb

    def angulos_steiner(self) -> Dict[str, float]:
        return {
            "SNA": self.angulo_sna(),
            "SNB": self.angulo_snb(),
            "ANB": self.angulo_anb(),
        }

    def clase_esqueletica(self) -> str:
        anb = self.angulo_anb()
        if anb > 4.0:
            return "Clase II"
        elif anb < 0.0:
            return "Clase III"
        return "Clase I"  # 0.0 <= anb <= 4.0

    def evaluacion_steiner(self) -> Dict[str, Dict[str, float]]:
        resultados = {}
        angulos = self.angulos_steiner()
        for nombre, (_, lim_inf, lim_sup) in self.NORMATIVOS.items():
            valor = angulos[nombre]
            dentro = lim_inf <= valor <= lim_sup
            resultados[nombre] = {
                "valor": round(valor, 2),
                "limite": self.NORMATIVOS[nombre][0],
                "lim_inf": lim_inf,
                "lim_sup": lim_sup,
                "dentro": dentro,
                "estado": "OK" if dentro else "FUERA",
            }
        return resultados

    def reporte_texto(self, precision: int = 2) -> str:
        sep = "-" * 48
        line = f"\n{sep}\n"
        partes = [
            line,
            "  ANALISIS CEFALOMETRICO DE STEINER",
            line,
            f"  Imagen   : {self.nombre_imagen}",
            f"  Landmarks: {self.num_landmarks}",
        ]

        if self.escala_mm is not None:
            partes.append(f"  Escala   : {self.escala_mm:.4f} mm/pixel")
        else:
            partes.append(f"  Escala   : sin calibrar (pixeles)")

        partes.extend([
            line,
            "  Angulos (grados) - Vertice en N (Nasion):",
        ])

        angulos = self.angulos_steiner()
        for nombre, valor in angulos.items():
            norm = self.NORMATIVOS[nombre][0]
            dentro = self.NORMATIVOS[nombre][1] <= valor <= self.NORMATIVOS[nombre][2]
            marca = "OK" if dentro else "FUERA"
            partes.append(
                f"    {nombre:4s} = {valor:{precision + 3}.{precision}f} deg  "
                f"  (normativo {norm})  [{marca}]"
            )

        partes.extend([
            line,
            f"  Clase esqueletica : {self.clase_esqueletica()}",
            line,
        ])

        return "\n".join(partes)

    def reporte_json(self) -> Dict:
        angulos = self.angulos_steiner()
        evaluacion = self.evaluacion_steiner()
        return {
            "imagen": self.nombre_imagen,
            "num_landmarks": self.num_landmarks,
            "pixel_size_mm": self.escala_mm,
            "angulos": {k: round(v, 4) for k, v in angulos.items()},
            "clase_esqueletica": self.clase_esqueletica(),
            "evaluacion": evaluacion,
        }


def analisis_rapido(
    coords: np.ndarray,
    nombre: str = "imagen",
    escala_mm: Optional[float] = None,
    imprimir: bool = True
) -> CephalometricAnalysis:
    analisis = CephalometricAnalysis(coords, nombre, escala_mm)
    if imprimir:
        print(analisis.reporte_texto())
    return analisis


if __name__ == "__main__":
    print("Demostracion del modulo geometry.py\n")
    np.random.seed(42)
    demo_coords = np.random.rand(NUM_LANDMARKS, 2) * INPUT_SIZE_WH[0]
    analisis = analisis_rapido(demo_coords, "demo.png", escala_mm=0.115, imprimir=True)
