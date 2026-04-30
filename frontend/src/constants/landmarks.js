// 29 landmarks - ORDEN EXACTO según src/core/landmarks.py (Aariz dataset)
// CRÍTICO: El modelo PyTorch usa ESTE orden. Cualquier desviación causa mapeo incorrecto.
// El backend envía un array de 29 elementos donde landmarks[i] tiene las coordenadas del punto i.
// Este archivo define cómo se muestra cada punto (nombre, color, categoría) en el frontend.
//
// Verificación con landmarks.py:
//  0:A, 1:ANS, 2:B, 3:Me, 4:N, 5:Or, 6:Pog, 7:PNS, 8:Pn, 9:R, 10:S, 11:Ar, 12:Co,
//  13:Gn, 14:Go, 15:Po, 16:LPM, 17:LIT, 18:LMT, 19:UPM, 20:UIA, 21:UIT, 22:UMT,
//  23:LIA, 24:Li, 25:Ls, 26:N', 27:Pog', 28:Sn

const LANDMARKS = [
  // 0: A (Subespinale) - Cranial
  { id: 0, name: 'A-point (Subespinale)', category: 'cranial', color: '#EF4444' },
  // 1: ANS (Anterior Nasal Spine) - Cranial
  { id: 1, name: 'ANS (Anterior Nasal Spine)', category: 'cranial', color: '#EF4444' },
  // 2: B (Supramental) - Mandibular
  { id: 2, name: 'B-point (Supramental)', category: 'mandibular', color: '#3B82F6' },
  // 3: Me (Menton) - Mandibular
  { id: 3, name: 'Menton (Me)', category: 'mandibular', color: '#3B82F6' },
  // 4: N (Nasion) - Cranial
  { id: 4, name: 'Nasion (N)', category: 'cranial', color: '#EF4444' },
  // 5: Or (Orbitale) - Cranial
  { id: 5, name: 'Orbitale (Or)', category: 'cranial', color: '#EF4444' },
  // 6: Pog (Pogonion óseo) - Mandibular
  { id: 6, name: 'Pogonion (Pog)', category: 'mandibular', color: '#3B82F6' },
  // 7: PNS (Posterior Nasal Spine) - Cranial
  { id: 7, name: 'PNS (Posterior Nasal Spine)', category: 'cranial', color: '#EF4444' },
  // 8: Pn (Pronasale) - Soft Tissue
  { id: 8, name: 'Pronasale (Pn)', category: 'soft-tissue', color: '#EAB308' },
  // 9: R (Ridge) - Mandibular
  { id: 9, name: 'Ridge (R)', category: 'mandibular', color: '#3B82F6' },
  // 10: S (Sella) - Cranial
  { id: 10, name: 'Sella (S)', category: 'cranial', color: '#EF4444' },
  // 11: Ar (Articulare) - Cranial
  { id: 11, name: 'Articular (Ar)', category: 'cranial', color: '#EF4444' },
  // 12: Co (Condylion) - Mandibular
  { id: 12, name: 'Condylion (Co)', category: 'mandibular', color: '#3B82F6' },
  // 13: Gn (Gnathion) - Mandibular
  { id: 13, name: 'Gnathion (Gn)', category: 'mandibular', color: '#3B82F6' },
  // 14: Go (Gonion) - Mandibular
  { id: 14, name: 'Gonion (Go)', category: 'mandibular', color: '#3B82F6' },
  // 15: Po (Porion) - Cranial
  { id: 15, name: 'Porion (Po)', category: 'cranial', color: '#EF4444' },
  // 16: LPM (Low Point Mandible) - Mandibular
  { id: 16, name: 'Low Point Mandible (LPM)', category: 'mandibular', color: '#3B82F6' },
  // 17: LIT (Lower Incisor Tip) - Dental
  { id: 17, name: 'Lower Incisor Tip (LIT)', category: 'dental', color: '#22C55E' },
  // 18: LMT (Lower Molar Tip) - Mandibular
  { id: 18, name: 'Lower Molar Tip (LMT)', category: 'mandibular', color: '#3B82F6' },
  // 19: UPM (Upper 2nd PM Cusp) - Dental
  { id: 19, name: 'Upper 2nd PM Cusp (UPM)', category: 'dental', color: '#22C55E' },
  // 20: UIA (Upper Incisor Apex) - Dental
  { id: 20, name: 'Upper Incisor Apex (UIA)', category: 'dental', color: '#22C55E' },
  // 21: UIT (Upper Incisor Tip) - Dental
  { id: 21, name: 'Upper Incisor Tip (UIT)', category: 'dental', color: '#22C55E' },
  // 22: UMT (Upper Molar Tip) - Dental
  { id: 22, name: 'Upper Molar Tip (UMT)', category: 'dental', color: '#22C55E' },
  // 23: LIA (Lower Incisor Apex) - Dental
  { id: 23, name: 'Lower Incisor Apex (LIA)', category: 'dental', color: '#22C55E' },
  // 24: Li (Labrale inferius) - Soft Tissue
  { id: 24, name: 'Labrale inferius (Li)', category: 'soft-tissue', color: '#EAB308' },
  // 25: Ls (Labrale superius) - Soft Tissue
  { id: 25, name: 'Labrale superius (Ls)', category: 'soft-tissue', color: '#EAB308' },
  // 26: N' (Soft Tissue Nasion) - Soft Tissue
  { id: 26, name: 'Soft Tissue Nasion (N\')', category: 'soft-tissue', color: '#EAB308' },
  // 27: Pog' (Soft Pogonion) - Soft Tissue
  { id: 27, name: 'Soft Pogonion (Pog\')', category: 'soft-tissue', color: '#EAB308' },
  // 28: Sn (Subnasale / Glabela) - Soft Tissue
  { id: 28, name: 'Subnasale (Sn)', category: 'soft-tissue', color: '#EAB308' },
]

export const CRANIAL_LANDMARKS = LANDMARKS.filter(l => l.category === 'cranial')
export const MANDIBULAR_LANDMARKS = LANDMARKS.filter(l => l.category === 'mandibular')
export const DENTAL_LANDMARKS = LANDMARKS.filter(l => l.category === 'dental')
export const SOFT_TISSUE_LANDMARKS = LANDMARKS.filter(l => l.category === 'soft-tissue')

export default LANDMARKS
