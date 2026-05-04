import numpy as np
import math
from src.core.config import SILLA_THRESHOLD_OPEN, SILLA_THRESHOLD_CLOSED

class CephalometricAnalysis:
    def __init__(self, coords, nombre_imagen="", escala_mm=None):
        self.coords = coords  # Array de 29 landmarks [x, y]
        self.nombre_imagen = nombre_imagen
        self.escala_mm = escala_mm  # mm por píxel

        # Single Source of Truth: importar índices desde src/core/landmarks.py
        from src.core.landmarks import (
            IDX_SELLA, IDX_NASION, IDX_A_POINT, IDX_B_POINT, IDX_POGONION,
            NAME_TO_IDX
        )
        self.IDX_SELLA = IDX_SELLA
        self.IDX_NASION = IDX_NASION
        self.IDX_A_POINT = IDX_A_POINT
        self.IDX_B_POINT = IDX_B_POINT
        self.IDX_POGONION = IDX_POGONION

        # Mapeo dinámico para landmarks adicionales vía SSOT
        self.NAME_TO_IDX = NAME_TO_IDX  # Guardar para uso en otros métodos
        self.IDX_ARTICULARE = NAME_TO_IDX.get("Ar", 11)
        self.IDX_INCISOR_SUP = NAME_TO_IDX.get("UIT", 21)
        self.IDX_INCISOR_SUP_APEX = NAME_TO_IDX.get("UIA", 22)
        self.IDX_INCISOR_INF = NAME_TO_IDX.get("LIT", 17)
        self.IDX_INCISOR_INF_APEX = NAME_TO_IDX.get("LIA", 23)
        self.IDX_GONION = NAME_TO_IDX.get("Go", 14)
        self.IDX_MOLAR_INF = NAME_TO_IDX.get("LMT", 18)
        self.IDX_MOLAR_SUP = NAME_TO_IDX.get("UPM", 19)
        self.IDX_PORION = NAME_TO_IDX.get("Po", 15)
        self.IDX_GNATHION = NAME_TO_IDX.get("Gn", 13)
        self.IDX_UPPER_LIP = NAME_TO_IDX.get("Ls", 25)
        self.IDX_LOWER_LIP = NAME_TO_IDX.get("Li", 24)
        self.IDX_SOFT_POGONION = NAME_TO_IDX.get("Pog'", 27)
        self.IDX_NOSE_TIP = NAME_TO_IDX.get("Sn", 28)
        self.IDX_MENTON = NAME_TO_IDX.get("Me", 3)

    def get_point(self, idx):
        p = self.coords[idx]
        arr = np.asarray(p)
        if arr.ndim == 0:
            return None if np.isnan(arr) else p
        if np.any(np.isnan(arr)):
            return None
        return p

    def calculate_angle(self, point_a, vertex, point_b, en_grados=True):
        if point_a is None or vertex is None or point_b is None:
            return None
        try:
            v1 = np.array([point_a[0] - vertex[0], point_a[1] - vertex[1]])
            v2 = np.array([point_b[0] - vertex[0], point_b[1] - vertex[1]])
        except (TypeError, IndexError):
            return None
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return None
        cos_theta = np.clip(np.dot(v1, v2) / (norm_v1 * norm_v2), -1.0, 1.0)
        angulo = np.arccos(cos_theta)
        return float(np.degrees(angulo)) if en_grados else float(angulo)

    def _oriented_angle(self, v1, v2):
        """Ángulo orientado de v1 a v2 en [0, 360)° vía atan2.

        Reemplaza trucos tipo 180 - ang. Clinically sound.
        """
        ang_v1 = math.atan2(v1[1], v1[0])
        ang_v2 = math.atan2(v2[1], v2[0])
        d = ang_v2 - ang_v1
        d = (d + 2 * math.pi) % (2 * math.pi)
        return math.degrees(d)

    def _clinical_angle(self, v1, v2):
        """Ángulo clínico entre dos vectores, siempre en [0, 180] vía arccos.

        Garantiza que ambos vectores estén orientados de forma que
        el arccos devuelva el ángulo clínico correcto.
        """
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return None
        cos_theta = np.clip(np.dot(v1, v2) / (norm_v1 * norm_v2), -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_theta)))

    def angle_between_lines(self, p1, p2, p3, p4):
        v1 = np.array(p2) - np.array(p1)
        v2 = np.array(p4) - np.array(p3)
        return self._clinical_angle(v1, v2)

    def dist_mm(self, p1, p2):
        if not self.escala_mm:
            return None
        if p1 is None or p2 is None:
            return None
        try:
            return float(np.linalg.norm(np.array(p1) - np.array(p2)) * self.escala_mm)
        except (TypeError, ValueError):
            return None

    def angulo_sna(self):
        return self.calculate_angle(self.get_point(self.IDX_SELLA), self.get_point(self.IDX_NASION), self.get_point(self.IDX_A_POINT))

    def angulo_snb(self):
        return self.calculate_angle(self.get_point(self.IDX_SELLA), self.get_point(self.IDX_NASION), self.get_point(self.IDX_B_POINT))

    def wits_analysis(self):
        if not self.escala_mm:
            return None
        try:
            A = np.array(self.get_point(self.IDX_A_POINT))
            B = np.array(self.get_point(self.IDX_B_POINT))
            molar_sup = np.array(self.get_point(self.IDX_MOLAR_SUP))
            molar_inf = np.array(self.get_point(self.IDX_MOLAR_INF))
            incisor_sup = np.array(self.get_point(self.IDX_INCISOR_SUP))
            incisor_inf = np.array(self.get_point(self.IDX_INCISOR_INF))
        except (IndexError, TypeError):
            return None

        # Plano Oclusal: Punto medio molares a punto medio incisivos
        molar_mid = (molar_sup + molar_inf) / 2.0
        incisor_mid = (incisor_sup + incisor_inf) / 2.0

        # Vector direccional del plano oclusal
        v_op = incisor_mid - molar_mid
        len_op = np.linalg.norm(v_op)
        if len_op == 0:
            return None
        v_op_unit = v_op / len_op

        # Proyección escalar ortogonal sobre el plano oclusal
        proj_A = np.dot(A - molar_mid, v_op_unit)
        proj_B = np.dot(B - molar_mid, v_op_unit)

        # Wits = A - B (mm)
        # Literatura médica: Wits positivo = A por delante de B (Clase II)
        #                   Wits negativo = A por detrás de B (Clase III)
        wits_value = float((proj_A - proj_B) * self.escala_mm)
        return wits_value

    def ricketts_estetico(self):
        if not self.escala_mm:
            return {"Ls_E": None, "Li_E": None}
        try:
            Pn = np.array(self.get_point(self.IDX_NOSE_TIP))
            Pos = np.array(self.get_point(self.IDX_SOFT_POGONION))
            Ls = np.array(self.get_point(self.IDX_UPPER_LIP))
            Li = np.array(self.get_point(self.IDX_LOWER_LIP))
        except (IndexError, TypeError):
            return {"Ls_E": None, "Li_E": None}

        def dist_to_eline(point):
            """Distancia perpendicular desde punto a línea Pn-Pos (E-line)."""
            line_vec = Pos - Pn
            norm_line = np.linalg.norm(line_vec)
            if norm_line == 0:
                return None
            point_vec = point - Pn
            # Producto cruzado 2D manual (evita warning de NumPy 2.0 con vectores 2D)
            cross_val = line_vec[0] * point_vec[1] - line_vec[1] * point_vec[0]
            dist = abs(cross_val) / norm_line
            sign = 1 if cross_val >= 0 else -1
            return sign * dist * self.escala_mm

        return {"Ls_E": dist_to_eline(Ls), "Li_E": dist_to_eline(Li)}

    def jarabak_analysis(self):
        N = self.get_point(self.IDX_NASION)
        S = self.get_point(self.IDX_SELLA)
        Ar = self.get_point(self.IDX_ARTICULARE)
        Go = self.get_point(self.IDX_GONION)
        Me = self.get_point(self.IDX_MENTON)

        # Ángulos internos del polígono craneal usando trigonometría pura (producto punto)
        ang_silla = self.calculate_angle(N, S, Ar)
        ang_articular = self.calculate_angle(S, Ar, Go)
        ang_goniaco = self.calculate_angle(Ar, Go, Me)

        # Manejo seguro de None para suma de ángulos
        suma_angulos = None
        if all(v is not None for v in [ang_silla, ang_articular, ang_goniaco]):
            suma_angulos = ang_silla + ang_articular + ang_goniaco

        return {
            "Base_Craneal_Ant": self.dist_mm(N, S),
            "Base_Craneal_Post": self.dist_mm(S, Ar),
            "Altura_Rama": self.dist_mm(Ar, Go),
            "Cuerpo_Mandibular": self.dist_mm(Go, Me),
            "Altura_Facial_Ant": self.dist_mm(N, Me),
            "Silla": ang_silla,
            "Articular": ang_articular,
            "Goniaco": ang_goniaco,
            "Suma_Angulos": suma_angulos
        }

    def dental_inclination(self):
        try:
            U1 = self.get_point(self.IDX_INCISOR_SUP)
            L1 = self.get_point(self.IDX_INCISOR_INF)
            U1_apex = self.get_point(self.NAME_TO_IDX.get("UIA", 22))
            L1_apex = self.get_point(self.IDX_INCISOR_INF_APEX)
            S = self.get_point(self.IDX_SELLA)
            N = self.get_point(self.IDX_NASION)
            Go = self.get_point(self.IDX_GONION)
            Gn = self.get_point(self.IDX_GNATHION)
            A = self.get_point(self.IDX_A_POINT)
            Pog = self.get_point(self.IDX_POGONION)

            # Blindaje: si algún punto es None, retornar None para todos
            puntos = [U1, L1, U1_apex, L1_apex, S, N, Go, Gn, A, Pog]
            if any(p is None for p in puntos):
                return {"1Sup_SN": None, "1Inf_PM": None, "Interincisal": None,
                        "1Sup_APg": None, "1Inf_APg": None}

            U1 = np.array(U1)
            L1 = np.array(L1)
            U1_apex = np.array(U1_apex)
            L1_apex = np.array(L1_apex)
            S = np.array(S)
            N = np.array(N)
            Go = np.array(Go)
            Gn = np.array(Gn)
            A = np.array(A)
            Pog = np.array(Pog)
        except (IndexError, TypeError, ValueError):
            return {"1Sup_SN": None, "1Inf_PM": None, "Interincisal": None,
                    "1Sup_APg": None, "1Inf_APg": None}

        # Vectores anatómicos: ápice → corona (dirección clínica)
        v_SN = N - S
        v_1Sup = U1 - U1_apex
        v_1Inf = L1 - L1_apex
        v_PM = Gn - Go
        v_APg = Pog - A

        def _oriented_clinical(v_tooth, v_ref):
            """Ángulo clínico [0,180]° usando trigonometría orientada.

            Usa atan2 para determinar cuadrante, luego mapea a ángulo
            clínico correcto. Sin trucos tipo 180 - ang.
            """
            if np.linalg.norm(v_tooth) == 0 or np.linalg.norm(v_ref) == 0:
                return None
            ang_ref = math.atan2(v_ref[1], v_ref[0])
            ang_tooth = math.atan2(v_tooth[1], v_tooth[0])
            # Ángulo orientado del plano de referencia al diente
            delta = (ang_tooth - ang_ref + 2 * math.pi) % (2 * math.pi)
            deg = math.degrees(delta)
            # Clínico: ángulo menor entre ambos vectores [0, 180]
            return deg if deg <= 180 else 360 - deg

        return {
            "1Sup_SN": _oriented_clinical(v_1Sup, v_SN),
            "1Inf_PM": _oriented_clinical(v_1Inf, v_PM),
            "Interincisal": _oriented_clinical(v_1Sup, v_1Inf),
            "1Sup_APg": _oriented_clinical(v_1Sup, v_APg),
            "1Inf_APg": _oriented_clinical(v_1Inf, v_APg)
        }

    def _clase_esqueletal(self, anb, wits):
        """Determina la clase esqueletal priorizando ANB y Wits."""
        if anb is None:
            return None
        if anb > 4 or (wits is not None and wits > 2):
            return "Clase II"
        if anb < 0 or (wits is not None and wits < -2):
            return "Clase III"
        return "Clase I"

    def _interpretar_jarabak(self, jarabak, clase):
        """Ajusta etiquetas Jarabak según clase esqueletal."""
        resultado = dict(jarabak)
        cm = jarabak.get("Cuerpo_Mandibular")
        si = jarabak.get("Silla")

        if cm is not None and clase:
            if cm > 76:
                if clase == "Clase III":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase III (mandíbula grande)"
                elif clase == "Clase II":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase II (maxilar pequeño relativo)"
                else:
                    resultado["Cuerpo_Mandibular_clase"] = "Cuerpo mandibular aumentado"
            elif cm < 66:
                if clase == "Clase III":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase III (mandíbula pequeña relativa)"
                elif clase == "Clase II":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase II (maxilar grande)"
                else:
                    resultado["Cuerpo_Mandibular_clase"] = "Cuerpo mandibular disminuido"
            else:
                resultado["Cuerpo_Mandibular_clase"] = "Cuerpo mandibular normal"

        if si is not None:
            if si > SILLA_THRESHOLD_OPEN and clase == "Clase III":
                resultado["Silla_clase"] = "Silla abierta → tendencia Clase III"
            elif si < SILLA_THRESHOLD_CLOSED and clase == "Clase II":
                resultado["Silla_clase"] = "Silla cerrada → tendencia Clase II"
            else:
                resultado["Silla_clase"] = f"Silla {si:.1f}°"

        return resultado

    def reporte_json(self):
        sna = self.angulo_sna()
        snb = self.angulo_snb()
        anb = (sna - snb) if (sna is not None and snb is not None) else None
        wits = self.wits_analysis()
        ricketts = self.ricketts_estetico()
        jarabak = self.jarabak_analysis()
        dental = self.dental_inclination()

        # Diagnóstico de clase dominante (prioridad ANB/Wits)
        clase = self._clase_esqueletal(anb, wits)
        jarabak_interp = self._interpretar_jarabak(jarabak, clase)

        def safe_round(val, decimals=2):
            if val is None:
                return None
            try:
                float_val = float(val)
                if math.isnan(float_val) or math.isinf(float_val):
                    return None
                return round(float_val, decimals)
            except (ValueError, TypeError):
                return None

        return {
            "SNA": safe_round(sna),
            "SNB": safe_round(snb),
            "ANB": safe_round(anb),
            "WITS": safe_round(wits),
            "Ls_E": safe_round(ricketts["Ls_E"]),
            "Li_E": safe_round(ricketts["Li_E"]),
            "Base_Craneal_Ant": safe_round(jarabak["Base_Craneal_Ant"]),
            "Base_Craneal_Post": safe_round(jarabak["Base_Craneal_Post"]),
            "Altura_Rama": safe_round(jarabak["Altura_Rama"]),
            "Cuerpo_Mandibular": safe_round(jarabak["Cuerpo_Mandibular"]),
            "Altura_Facial_Ant": safe_round(jarabak["Altura_Facial_Ant"]),
            "Silla": safe_round(jarabak["Silla"]),
            "Articular": safe_round(jarabak["Articular"]),
            "Goniaco": safe_round(jarabak["Goniaco"]),
            "Suma_Angulos": safe_round(jarabak["Suma_Angulos"]),
            "1Sup_SN": safe_round(dental["1Sup_SN"]),
            "1Inf_PM": safe_round(dental["1Inf_PM"]),
            "Interincisal": safe_round(dental["Interincisal"]),
            "1Sup_APg": safe_round(dental["1Sup_APg"]),
            "1Inf_APg": safe_round(dental["1Inf_APg"]),
            "clase_esqueletal": clase,
            "Silla_interp": jarabak_interp.get("Silla_clase"),
            "Cuerpo_Mandibular_interp": jarabak_interp.get("Cuerpo_Mandibular_clase")
        }
