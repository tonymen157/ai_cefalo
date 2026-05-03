import unittest
import numpy as np
import math
import sys
from pathlib import Path

# Añadir path para importar desde src/
sys.path.append(str(Path(__file__).parent.parent / "src"))

from analysis.geometry import CephalometricAnalysis


class TestCephalometricGeometry(unittest.TestCase):
    """Pruebas unitarias de caja blanca para validar fórmulas geométricas cefalométricas."""

    def setUp(self):
        """Configurar coordenadas de prueba con escala 1.0 (1 px = 1 mm)."""
        # Crear 29 landmarks con coordenadas dummy (solo usaremos los índices necesarios)
        self.coords = np.zeros((29, 2))
        # Configurar escala: 1 píxel = 1 milímetro exacto
        self.escala_mm = 1.0

    def _crear_analisis(self, coords_dict):
        """Crear instancia de CephalometricAnalysis con coordenadas específicas."""
        coords = np.zeros((29, 2))
        for idx, (x, y) in coords_dict.items():
            coords[idx] = [x, y]
        return CephalometricAnalysis(
            coords=coords,
            nombre_imagen="test",
            escala_mm=self.escala_mm
        )

    # ============================================================
    # TEST 1: Ángulo Recto (SNA a 90°)
    # ============================================================

    def test_sna_90_grados(self):
        """
        Coordenadas para SNA = 90° exactos:

        S = [100, 200]   (Sella - vértice)
        N = [100, 100]   (Nasion - punto en Y)
        A = [200, 100]   (Punto A - punto en X)

        Vector S-N: [0, -100]   (hacia abajo)
        Vector A-N: [100, 0]    (hacia la derecha)

        ∠S-N-A = 90° (triángulo rectángulo perfecto)
        """
        analisis = self._crear_analisis({
            10: [100, 200],   # S (Sella)
            4: [100, 100],    # N (Nasion)
            0: [200, 100],    # A (Subespinale)
        })

        sna = analisis.angulo_sna()
        self.assertAlmostEqual(sna, 90.0, places=1,
            msg=f"SNA debería ser 90.0°, obtuvo {sna}°")

    def test_snb_45_grados(self):
        """
        Coordenadas para SNB = 45° exactos:

        S = [100, 200]   (Sella - vértice)
        N = [100, 100]   (Nasion - punto en Y)
        B = [150, 150]   (Punto B - Diagonal: 50px right, 50px up)

        Vector S-N: [0, -100]
        Vector B-N: [50, 50]

        Ángulo = arctan(50/50) = 45°
        """
        analisis = self._crear_analisis({
            10: [100, 200],   # S (Sella)
            4: [100, 100],    # N (Nasion)
            2: [150, 150],    # B (Supramental)
        })

        snb = analisis.angulo_snb()
        self.assertAlmostEqual(snb, 45.0, places=1,
            msg=f"SNB debería ser 45.0°, obtuvo {snb}°")

    def test_anb_resta_directa(self):
        """
        ANB = SNA - SNB

        Con SNA = 90° y SNB = 45°:
        ANB = 90 - 45 = 45° (Clase II, ya que > 4)
        """
        analisis = self._crear_analisis({
            10: [100, 200],   # S (Sella)
            4: [100, 100],    # N (Nasion)
            0: [200, 100],    # A (Subespinale) → SNA = 90°
            2: [150, 150],    # B (Supramental) → SNB = 45°
        })

        sna = analisis.angulo_sna()
        snb = analisis.angulo_snb()
        anb = sna - snb

        self.assertAlmostEqual(anb, 45.0, places=1,
            msg=f"ANB (SNA-SNB) debería ser 45.0°, obtuvo {anb}°")
        self.assertGreater(anb, 4, "ANB > 4 debería indicar Clase II")

    # ============================================================
    # TEST 2: Proyección de Wits (Plano Oclusal Horizontal)
    # ============================================================

    def test_wits_a_delante_b_30mm(self):
        """
        Wits Analysis con plano oclusal PERFECTAMENTE HORIZONTAL:

        Plano Oclusal:
        - Molares: UPM [0, 150] + LMT [200, 150] → molar_mid = [100, 150]
        - Incisivos: UIT [0, 100] + LIT [200, 100] → incisor_mid = [100, 100]

        Vector del plano oclusal: incisor_mid - molar_mid = [0, -50] (vertical!)
        Pero espera, el usuario dice que es horizontal...

        Revisemos: El usuario dice Molares [0,150] e Incisivos [200,150]
        Si tomamos esos puntos directamente (no los midpoints):
        - Molar: [0, 150]
        - Incisivo: [200, 150]

        Esto crea una línea horizontal en y=150.

        Pero el código usa los midpoints. Vamos a usar los valores correctos:

        UPM = [0, 150], LMT = [200, 150] → molar_mid = [100, 150]
        UIT = [0, 150], LIT = [200, 150] → incisor_mid = [100, 150]

        Esto da un plano oclusal de un solo punto. Necesitamos coordenadas
        que produzcan un plano horizontal claro.

        Para un plano horizontal en y=150:
        - UPM = [0, 150], LMT = [200, 150] → molar_mid = [100, 150]
        - UIT = [50, 150], LIT = [150, 150] → incisor_mid = [100, 150]

        Todavía es un punto... Necesitamos que molar_mid != incisor_mid.

        Usaremos:
        - UPM = [0, 150], LMT = [0, 150] → molar_mid = [0, 150]
        - UIT = [200, 150], LIT = [200, 150] → incisor_mid = [200, 150]

        Plano oclusal: de [0, 150] a [200, 150] (horizontal en y=150)
        Vector: [200, 0], unitario: [1, 0]

        A = [150, 100]
        B = [120, 200]

        Proyección A: (A - molar_mid) · [1, 0] = [150, -50] · [1, 0] = 150
        Proyección B: (B - molar_mid) · [1, 0] = [120, 50] · [1, 0] = 120

        Wits = 150 - 120 = 30.0 mm (Clase II)
        """
        analisis = self._crear_analisis({
            # Puntos para plano oclusal (y=150, línea horizontal)
            19: [0, 150],     # UPM (Upper Molar Tip) → molar_mid.x = 0
            18: [0, 150],     # LMT (Lower Molar Tip)
            21: [200, 150],   # UIT (Upper Incisor Tip) → incisor_mid.x = 200
            17: [200, 150],   # LIT (Lower Incisor Tip)
            # Puntos A y B
            0: [150, 100],    # A (x=150, y=100)
            2: [120, 200],    # B (x=120, y=200)
        })

        wits = analisis.wits_analysis()

        self.assertAlmostEqual(wits, 30.0, places=1,
            msg=f"Wits debería ser 30.0mm (A delante de B), obtuvo {wits}mm")
        self.assertGreater(wits, 2, "Wits > 2 debería indicar Clase II")

    def test_wits_a_detras_b_clase_iii(self):
        """
        Wits con A POR DETRÁS de B (Clase III):

        Plano Oclusal: y=150 (horizontal)
        - molar_mid = [0, 150]
        - incisor_mid = [200, 150]

        Vector plano: [200, 0], unitario: [1, 0]

        A = [100, 100]   (x=100)
        B = [130, 200]   (x=130)

        Proyección A: (A - molar_mid) · [1, 0] = [100, -50] · [1, 0] = 100
        Proyección B: (B - molar_mid) · [1, 0] = [130, 50] · [1, 0] = 130

        Wits = 100 - 130 = -30.0 mm (Clase III)
        """
        analisis = self._crear_analisis({
            # Plano Oclusal (y=150, horizontal)
            19: [0, 150],     # UPM
            18: [0, 150],     # LMT
            21: [200, 150],   # UIT
            17: [200, 150],   # LIT
            # Puntos A y B
            0: [100, 100],    # A (x=100)
            2: [130, 200],    # B (x=130)
        })

        wits = analisis.wits_analysis()

        self.assertAlmostEqual(wits, -30.0, places=1,
            msg=f"Wits debería ser -30.0mm (A detrás de B), obtuvo {wits}mm")
        self.assertLess(wits, -2, "Wits < -2 debería indicar Clase III")

    # ============================================================
    # TEST 3: Ricketts Estético (Línea E)
    # ============================================================

    def test_ricketts_ls_li_distancia_perpendicular(self):
        """
        Ricketts Línea E: distancia perpendicular desde labio a línea Pn-Pos.

        Pn = [100, 100] (Nose Tip)
        Pos = [200, 100] (Soft Pogonion) → Línea E horizontal y=100

        Ls = [100, 80] (arriba de la línea, y < 100)
        Li = [200, 120] (abajo de la línea, y > 100)

        Con producto cruz:
        - Ls: cross([100,0], [0,-20]) = -2000 → signo -1 → Ls_E = -20.0
        - Li: cross([100,0], [100,20]) = 2000 → signo +1 → Li_E = +20.0

        Signo negativo = por delante (protrusión)
        Signo positivo = por detrás (retrusión)
        """
        analisis = self._crear_analisis({
            28: [100, 100],   # Sn (Nose Tip) = Pn
            27: [200, 100],   # Pog' (Soft Pogonion) = Pos
            25: [100, 80],    # Ls (Upper Lip)
            24: [200, 120],   # Li (Lower Lip)
        })

        ricketts = analisis.ricketts_estetico()

        self.assertAlmostEqual(ricketts["Ls_E"], -20.0, places=1,
            msg=f"Ls-E debería ser -20.0mm (por delante), obtuvo {ricketts['Ls_E']}mm")
        self.assertAlmostEqual(ricketts["Li_E"], 20.0, places=1,
            msg=f"Li-E debería ser 20.0mm (por detrás), obtuvo {ricketts['Li_E']}mm")

    # ============================================================
    # TEST 4: Diagnóstico de Clase Esqueletal
    # ============================================================

    def test_clase_esqueletal_i(self):
        """ANB = 2° (< 4 y > 0) → Clase I"""
        analisis = self._crear_analisis({})
        clase = analisis._clase_esqueletal(anb=2.0, wits=0.5)
        self.assertEqual(clase, "Clase I")

    def test_clase_esqueletal_ii(self):
        """ANB = 5° (> 4) → Clase II"""
        analisis = self._crear_analisis({})
        clase = analisis._clase_esqueletal(anb=5.0, wits=3.0)
        self.assertEqual(clase, "Clase II")

    def test_clase_esqueletal_iii(self):
        """ANB = -2° (< 0) → Clase III"""
        analisis = self._crear_analisis({})
        clase = analisis._clase_esqueletal(anb=-2.0, wits=-3.0)
        self.assertEqual(clase, "Clase III")


if __name__ == '__main__':
    unittest.main(verbosity=2)
