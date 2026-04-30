export const CEPHALOMETRIC_NORMS = {
  esqueletal: {
    title: "Medidas Clase Esqueletal",
    measurements: [
      { id: 'SNA', name: 'Angulo SNA', normal: 82, sd: 2, unit: '°', high: 'Posible clase II (Maxilar protruido)', low: 'Posible clase III (Maxilar retruido)', normalText: 'Posicion maxilar normal' },
      { id: 'SNB', name: 'Angulo SNB', normal: 80, sd: 2, unit: '°', high: 'Posible clase III (Prognatismo)', low: 'Posible clase II (Retrognatismo)', normalText: 'Posicion mandibular normal' },
      { id: 'ANB', name: 'Angulo ANB', normal: 2, sd: 2, unit: '°', high: 'Tendencia a Clase II', low: 'Tendencia a Clase III', normalText: 'Clase I franca (Normal)' },
      { id: 'WITS', name: 'Wits (Plano Oclusal)', normal: 0, sd: 1, unit: 'mm', high: 'AO por delante de BO -> Clase II', low: 'BO por delante de AO -> Clase III', normalText: 'Relacion base apical normal (Clase I)' }
    ]
  },
  dental: {
    title: "Inclinacion Dental (Steiner & Ricketts)",
    measurements: [
      { id: '1Sup_SN', name: 'Angulo 1Sup-SN', normal: 103, sd: 5, unit: '°', high: 'Proinclinacion dental', low: 'Retroinclinacion dental' },
      { id: '1Inf_PM', name: 'Angulo 1Inf-Plano mandibular', normal: 90, sd: 5, unit: '°', high: 'Proinclinacion dental', low: 'Retroinclinacion dental' },
      { id: 'Interincisal', name: 'Angulo Interincisal', normal: 130, sd: 5, unit: '°', high: 'Retroinclinacion dental', low: 'Proinclinacion dental' },
      { id: '1Sup_APg', name: 'Angulo 1Sup A-Pg', normal: 28, sd: 3, unit: '°', high: 'Proinclinacion dental / Protrusion', low: 'Retroinclinacion dental / Retrusion' },
      { id: '1Inf_APg', name: 'Angulo 1Inf A-Pg', normal: 22, sd: 3, unit: '°', high: 'Proinclinacion dental / Protrusion', low: 'Retroinclinacion dental / Retrusion' }
    ]
  },
  estetico: {
    title: "Linea Estetica de Ricketts",
    measurements: [
      { id: 'Ls_E', name: 'Labio Superior a Linea E', normal: -4, sd: 2, unit: 'mm', high: 'Protrusion', low: 'Retrusion' },
      { id: 'Li_E', name: 'Labio Inferior a Linea E', normal: -2, sd: 2, unit: 'mm', high: 'Protrusion', low: 'Retrusion' }
    ]
  },
  jarabak_lineal: {
    title: "Medidas Lineales Jarabak",
    measurements: [
      { id: 'Base_Craneal_Ant', name: 'Base craneal anterior', normal: 71, sd: 3, unit: 'mm', high: 'Base craneal aumentada', low: 'Base craneal disminuida' },
      { id: 'Base_Craneal_Post', name: 'Base craneal posterior', normal: 32, sd: 3, unit: 'mm', high: 'Posible crecimiento horizontal', low: 'Posible crecimiento vertical' },
      { id: 'Altura_Rama', name: 'Altura de la rama', normal: 44, sd: 5, unit: 'mm', high: 'Crecimiento horizontal (Braquifacial)', low: 'Crecimiento vertical (Dolicofacial)' },
      { id: 'Cuerpo_Mandibular', name: 'Long. cuerpo mandibula', normal: 71, sd: 5, unit: 'mm', high: 'Mandibula aumentada', low: 'Mandibula disminuida' },
      { id: 'Altura_Facial_Ant', name: 'Altura facial anterior', normal: 112, sd: 7, unit: 'mm', high: 'Crecimiento vertical', low: 'Crecimiento horizontal' }
    ]
  },
  jarabak_angular: {
    title: "Medidas Angulares Jarabak",
    measurements: [
      { id: 'Silla', name: 'Angulo Silla', normal: 123, sd: 5, unit: '°', high: 'Silla abierta (tendencia Clase III)', low: 'Silla cerrada (tendencia Clase II)' },
      { id: 'Articular', name: 'Angulo Articular', normal: 143, sd: 6, unit: '°', high: 'Retrognatismo mandibular', low: 'Prognatismo mandibular' },
      { id: 'Goniaco', name: 'Angulo Goniaco', normal: 130, sd: 7, unit: '°', high: 'Aumenta altura facial', low: 'Disminuye altura facial' },
      { id: 'Suma_Angulos', name: 'Suma de angulos', normal: 396, sd: 7, unit: '°', high: 'Hiperdivergente (Dolicofacial)', low: 'Hipodivergente (Braquifacial)' }
    ]
  }
};
