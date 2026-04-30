import numpy as np
import math

class CephalometricAnalysis:
    def __init__(self, coords, nombre_imagen="", escala_mm=None):
        self.coords = coords  # Array de 29 landmarks [x, y]
        self.nombre_imagen = nombre_imagen
        self.escala_mm = escala_mm  # mm por píxel

        # Índices de landmarks críticos
        self.IDX_A_POINT = 0
        self.IDX_B_POINT = 2
        self.IDX_ARTICULARE = 3
        self.IDX_NASION = 4
        self.IDX_INCISOR_SUP = 5
        self.IDX_INCISOR_INF = 8
        self.IDX_GONION = 9
        self.IDX_SELLA = 10
        self.IDX_MOLAR_INF = 11
        self.IDX_MOLAR_SUP = 12
        self.IDX_PORION = 13
        self.IDX_GNATHION = 14
        self.IDX_UPPER_LIP = 17
        self.IDX_LOWER_LIP = 18
        self.IDX_SOFT_POGONION = 20
        self.IDX_NOSE_TIP = 21
        self.IDX_MENTON = 24

    def get_point(self, idx):
        return self.coords[idx]

    def calculate_angle(self, point_a, vertex, point_b, en_grados=True):
        v1 = np.array([point_a[0] - vertex[0], point_a[1] - vertex[1]])
        v2 = np.array([point_b[0] - vertex[0], point_b[1] - vertex[1]])
        cos_theta = np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1.0, 1.0)
        angulo = np.arccos(cos_theta)
        return float(np.degrees(angulo)) if en_grados else float(angulo)

    def angle_between_lines(self, p1, p2, p3, p4):
        v1 = np.array(p2) - np.array(p1)
        v2 = np.array(p4) - np.array(p3)
        cos_theta = np.clip(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)), -1.0, 1.0)
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

        # Plano Oclusal (Proxy): Punto medio molares a punto medio incisivos
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
        Pn = np.array(self.get_point(self.IDX_NOSE_TIP))
        Pos = np.array(self.get_point(self.IDX_SOFT_POGONION))
        Ls = np.array(self.get_point(self.IDX_UPPER_LIP))
        Li = np.array(self.get_point(self.IDX_LOWER_LIP))

        # Determinar si la cara mira a la derecha o izquierda dinámicamente
        is_right_facing = Pn[0] > self.get_point(self.IDX_PORION)[0]

        def dist_to_eline(point):
            # Calcular X sobre la recta en el mismo Y del labio
            if Pos[1] != Pn[1]:
                x_line = Pn[0] + (Pos[0] - Pn[0]) * (point[1] - Pn[1]) / (Pos[1] - Pn[1])
                # Signo basado en la orientación del paciente
                sign = 1 if (point[0] > x_line and is_right_facing) or (point[0] < x_line and not is_right_facing) else -1
            else:
                sign = 1

            # Distancia perpendicular pura
            num = abs((Pos[0]-Pn[0])*(Pn[1]-point[1]) - (Pn[0]-point[0])*(Pos[1]-Pn[1]))
            den = np.linalg.norm(Pos - Pn)
            return sign * (num / den) * self.escala_mm

        return {"Ls_E": dist_to_eline(Ls), "Li_E": dist_to_eline(Li)}

    def jarabak_analysis(self):
        N = self.get_point(self.IDX_NASION)
        S = self.get_point(self.IDX_SELLA)
        Ar = self.get_point(self.IDX_ARTICULARE)
        Go = self.get_point(self.IDX_GONION)
        Me = self.get_point(self.IDX_MENTON)

        ang_silla = self.calculate_angle(N, S, Ar)
        ang_articular = self.calculate_angle(S, Ar, Go)
        ang_goniaco = self.calculate_angle(Ar, Go, Me)

        return {
            "Base_Craneal_Ant": self.dist_mm(N, S),
            "Base_Craneal_Post": self.dist_mm(S, Ar),
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
        U1 = self.get_point(self.IDX_INCISOR_SUP)
        L1 = self.get_point(self.IDX_INCISOR_INF)
        S = self.get_point(self.IDX_SELLA)
        N = self.get_point(self.IDX_NASION)
        Go = self.get_point(self.IDX_GONION)
        Gn = self.get_point(self.IDX_GNATHION)

        # Ángulos suplementarios dinámicos
        ang_1Sup_SN = 180 - self.angle_between_lines(S, N, A, U1)
        ang_IMPA = self.angle_between_lines(Go, Gn, B, L1)
        if ang_IMPA > 90:
            ang_IMPA = 180 - ang_IMPA
        ang_inter = self.angle_between_lines(A, U1, B, L1)
        if ang_inter < 90:
            ang_inter = 180 - ang_inter

        return {
            "1Sup_SN": ang_1Sup_SN,
            "1Inf_PM": ang_IMPA,
            "Interincisal": ang_inter
        }

    def reporte_json(self):
        # Ejecutar matemáticas
        wits = self.wits_analysis()
        ricketts = self.ricketts_estetico()
        jarabak = self.jarabak_analysis()
        dental = self.dental_inclination()

        # Diccionario maestro para el Radar Recursivo de React
        def safe_round(val, decimals=2):
            return round(val, decimals) if val is not None else None

        result = {
            "SNA": safe_round(self.angulo_sna()),
            "SNB": safe_round(self.angulo_snb()),
            "ANB": safe_round(self.angulo_sna() - self.angulo_snb()),
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
            "Interincisal": safe_round(dental["Interincisal"])
        }
        return result
