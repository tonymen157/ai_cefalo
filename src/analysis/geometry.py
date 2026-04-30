import numpy as np
import math

class CephalometricAnalysis:
    def __init__(self, coords, nombre_imagen="", escala_mm=None):
        self.coords = coords  # Array de 29 landmarks [x, y]
        self.nombre_imagen = nombre_imagen
        self.escala_mm = escala_mm  # mm por píxel

        # Índices de landmarks (alineados con src/core/landmarks.py)
        self.IDX_A_POINT = 0          # A (Subespinale)
        self.IDX_B_POINT = 2          # B (Supramental)
        self.IDX_ARTICULARE = 11      # Ar (Articulación)
        self.IDX_NASION = 4           # N (Nasion)
        self.IDX_INCISOR_SUP = 21     # UIT (Upper Incisor Tip)
        self.IDX_INCISOR_INF = 17     # LIT (Lower Incisor Tip)
        self.IDX_INCISOR_INF_APEX = 23 # LIA (Lower Incisor Apex)
        self.IDX_GONION = 14          # Go (Gonion)
        self.IDX_SELLA = 10           # S (Sella)
        self.IDX_MOLAR_INF = 18       # LMT (Lower Molar Tip)
        self.IDX_MOLAR_SUP = 19       # UPM (Upper Molar Tip)
        self.IDX_PORION = 15          # Po (Porion)
        self.IDX_GNATHION = 13        # Gn (Gnathion)
        self.IDX_UPPER_LIP = 25       # Ls (Upper Lip)
        self.IDX_LOWER_LIP = 24       # Li (Lower Lip)
        self.IDX_SOFT_POGONION = 27   # Pog' (Soft Pogonion)
        self.IDX_NOSE_TIP = 28        # Sn (Subnasale/Nose Tip)
        self.IDX_MENTON = 3           # Me (Menton)
        self.IDX_POGONION = 6          # Pog (Pogonion óseo)

    def get_point(self, idx):
        return self.coords[idx]

    def calculate_angle(self, point_a, vertex, point_b, en_grados=True):
        v1 = np.array([point_a[0] - vertex[0], point_a[1] - vertex[1]])
        v2 = np.array([point_b[0] - vertex[0], point_b[1] - vertex[1]])
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        cos_theta = np.clip(np.dot(v1, v2) / (norm_v1 * norm_v2), -1.0, 1.0)
        angulo = np.arccos(cos_theta)
        return float(np.degrees(angulo)) if en_grados else float(angulo)

    def angle_between_lines(self, p1, p2, p3, p4):
        v1 = np.array(p2) - np.array(p1)
        v2 = np.array(p4) - np.array(p3)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 == 0 or norm_v2 == 0:
            return 0.0
        cos_theta = np.clip(np.dot(v1, v2) / (norm_v1 * norm_v2), -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_theta)))

    def dist_mm(self, p1, p2):
        if not self.escala_mm:
            return None
        return float(np.linalg.norm(np.array(p1) - np.array(p2)) * self.escala_mm)

    def angulo_sna(self):
        return self.calculate_angle(self.get_point(self.IDX_SELLA), self.get_point(self.IDX_NASION), self.get_point(self.IDX_A_POINT))

    def angulo_snb(self):
        return self.calculate_angle(self.get_point(self.IDX_SELLA), self.get_point(self.IDX_NASION), self.get_point(self.IDX_B_POINT))

    def wits_analysis(self):
        if not self.escala_mm:
            return None
        A = np.array(self.get_point(self.IDX_A_POINT))
        B = np.array(self.get_point(self.IDX_B_POINT))

        # Plano Oclusal: Punto medio molares a punto medio incisivos
        molar_mid = (np.array(self.get_point(self.IDX_MOLAR_SUP)) + np.array(self.get_point(self.IDX_MOLAR_INF))) / 2.0
        incisor_mid = (np.array(self.get_point(self.IDX_INCISOR_SUP)) + np.array(self.get_point(self.IDX_INCISOR_INF))) / 2.0

        # Vector direccional del plano oclusal
        v_op = incisor_mid - molar_mid
        len_op = np.linalg.norm(v_op)
        if len_op == 0:
            return 0.0
        v_op_unit = v_op / len_op

        # Proyección escalar ortogonal
        proj_A = np.dot(A - molar_mid, v_op_unit)
        proj_B = np.dot(B - molar_mid, v_op_unit)

        # Diferencia en mm (Positivo = A por delante de B)
        return float((proj_A - proj_B) * self.escala_mm)

    def ricketts_estetico(self):
        if not self.escala_mm:
            return {"Ls_E": None, "Li_E": None}
        # Pn = Nose Tip (Sn, 28), Pos = Soft Pogonion (Pog', 27)
        Pn = np.array(self.get_point(self.IDX_NOSE_TIP))
        Pos = np.array(self.get_point(self.IDX_SOFT_POGONION))
        Ls = np.array(self.get_point(self.IDX_UPPER_LIP))
        Li = np.array(self.get_point(self.IDX_LOWER_LIP))

        # Paciente mira a la derecha (X aumenta hacia la cara)
        is_right_facing = Pn[0] > self.get_point(self.IDX_PORION)[0]

        def dist_to_eline(point):
            if Pos[1] != Pn[1]:
                x_line = Pn[0] + (Pos[0] - Pn[0]) * (point[1] - Pn[1]) / (Pos[1] - Pn[1])
                # Signo: positivo si detrás de la línea, negativo si por delante (protrusión)
                if is_right_facing:
                    sign = -1 if point[0] > x_line else 1
                else:
                    sign = 1 if point[0] > x_line else -1
            else:
                sign = 1

            num = abs((Pos[0]-Pn[0])*(Pn[1]-point[1]) - (Pn[0]-point[0])*(Pos[1]-Pn[1]))
            den = np.linalg.norm(Pos - Pn)
            if den == 0:
                return 0.0
            return sign * (num / den) * self.escala_mm

        return {"Ls_E": dist_to_eline(Ls), "Li_E": dist_to_eline(Li)}

    def jarabak_analysis(self):
        N = self.get_point(self.IDX_NASION)
        S = self.get_point(self.IDX_SELLA)
        Ar = self.get_point(self.IDX_ARTICULARE)
        Go = self.get_point(self.IDX_GONION)
        Me = self.get_point(self.IDX_MENTON)

        # Ángulos internos del polígono (120-150°)
        ang_silla = self.calculate_angle(N, S, Ar)
        ang_articular = self.calculate_angle(S, Ar, Go)
        ang_goniaco = self.calculate_angle(Ar, Go, Me)

        # Corregir si el cálculo devolvió el ángulo externo
        ang_silla = ang_silla if ang_silla > 90 else 180 - ang_silla
        ang_articular = ang_articular if ang_articular > 90 else 180 - ang_articular
        ang_goniaco = ang_goniaco if ang_goniaco > 90 else 180 - ang_goniaco

        return {
            "Base_Craneal_Ant": self.dist_mm(N, S),
            "Base_Craneal_Post": self.dist_mm(S, Ar),  # Ahora usa Ar (11) en lugar de Me (3)
            "Altura_Rama": self.dist_mm(Ar, Go),
            "Cuerpo_Mandibular": self.dist_mm(Go, Me),
            "Altura_Facial_Ant": self.dist_mm(N, Me),
            "Silla": ang_silla,
            "Articular": ang_articular,
            "Goniaco": ang_goniaco,
            "Suma_Angulos": ang_silla + ang_articular + ang_goniaco
        }

    def dental_inclination(self):
        A = self.get_point(self.IDX_A_POINT)
        B = self.get_point(self.IDX_B_POINT)
        U1 = self.get_point(self.IDX_INCISOR_SUP)       # Upper Incisor Tip (21)
        L1 = self.get_point(self.IDX_INCISOR_INF)       # Lower Incisor Tip (17)
        L1_apex = self.get_point(self.IDX_INCISOR_INF_APEX) # Lower Incisor Apex (23)
        S = self.get_point(self.IDX_SELLA)
        N = self.get_point(self.IDX_NASION)
        Go = self.get_point(self.IDX_GONION)
        Gn = self.get_point(self.IDX_GNATHION)
        Pog = self.get_point(self.IDX_POGONION)       # Pogonion óseo (6)

        # Ángulo 1Sup-SN (suplementario dinámico)
        ang_1Sup_SN = 180 - self.angle_between_lines(S, N, A, U1)

        # 1Inf-PM: Ángulo entre eje incisivo inferior y plano mandibular (Go-Gn)
        # Eje incisivo: Apex (LIA, 23) → Tip (LIT, 17)
        ang_IMPA = self.angle_between_lines(Go, Gn, L1_apex, L1)
        if ang_IMPA > 90:
            ang_IMPA = 180 - ang_IMPA

        # Interincisal angle
        ang_inter = self.angle_between_lines(A, U1, B, L1)
        if ang_inter < 90:
            ang_inter = 180 - ang_inter

        # 1Sup-APg: Ángulo entre eje incisivo superior y línea A-Pg
        ang_1Sup_APg = self.angle_between_lines(A, Pog, A, U1)
        if ang_1Sup_APg > 90:
            ang_1Sup_APg = 180 - ang_1Sup_APg

        # 1Inf-APg: Ángulo entre eje incisivo inferior y línea A-Pg
        ang_1Inf_APg = self.angle_between_lines(A, Pog, L1_apex, L1)
        if ang_1Inf_APg > 90:
            ang_1Inf_APg = 180 - ang_1Inf_APg

        return {
            "1Sup_SN": ang_1Sup_SN,
            "1Inf_PM": ang_IMPA,
            "Interincisal": ang_inter,
            "1Sup_APg": ang_1Sup_APg,
            "1Inf_APg": ang_1Inf_APg
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
        """Ajusta las etiquetas de Jarabak según la clase esqueletal dominante."""
        resultado = dict(jarabak)

        # Cuerpo Mandibular: si es grande y la clase es III, decir Clase III; si es grande y clase II, decir Clase II
        if jarabak["Cuerpo_Mandibular"] is not None and clase:
            if jarabak["Cuerpo_Mandibular"] > 76:  # Por encima de norma+sd
                if clase == "Clase III":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase III (mandíbula grande)"
                elif clase == "Clase II":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase II (maxilar pequeño relativo)"
                else:
                    resultado["Cuerpo_Mandibular_clase"] = "Cuerpo mandibular aumentado"
            elif jarabak["Cuerpo_Mandibular"] < 66:  # Por debajo de norma-sd
                if clase == "Clase III":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase III (mandíbula pequeña relativa)"
                elif clase == "Clase II":
                    resultado["Cuerpo_Mandibular_clase"] = "Clase II (maxilar grande)"
                else:
                    resultado["Cuerpo_Mandibular_clase"] = "Cuerpo mandibular disminuido"
            else:
                resultado["Cuerpo_Mandibular_clase"] = "Cuerpo mandibular normal"

        # Silla: ángulo aumentado (>128) sugiere crecimiento plano → tendencia Clase III
        if jarabak["Silla"] is not None:
            if jarabak["Silla"] > 128 and clase == "Clase III":
                resultado["Silla_clase"] = "Silla abierta → tendencia Clase III"
            elif jarabak["Silla"] < 118 and clase == "Clase II":
                resultado["Silla_clase"] = "Silla cerrada → tendencia Clase II"
            else:
                resultado["Silla_clase"] = f"Silla {jarabak['Silla']:.1f}°"

        return resultado

    def reporte_json(self):
        sna = self.angulo_sna()
        snb = self.angulo_snb()
        anb = sna - snb
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

        result = {
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
            # Campo de diagnóstico coherente
            "clase_esqueletal": clase,
            "Silla_interp": jarabak_interp.get("Silla_clase"),
            "Cuerpo_Mandibular_interp": jarabak_interp.get("Cuerpo_Mandibular_clase")
        }
        return result
