// 29 landmarks - ORDEN EXACTO según src/core/landmarks.py (Aariz dataset)
// CRÍTICO: El modelo PyTorch usa ESTE orden. Cualquier desviación causa mapeo incorrecto.
// Categorías: cranial (red #EF4444), mandibular (blue #3B82F6), dental (green #22C55E), soft-tissue (yellow #EAB308)

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
  // 8: Pn (Pronasale / Nose Tip) - Soft Tissue
  { id: 8, name: 'Pronasale (Pn)', category: 'soft-tissue', color: '#EAB308' },
  // 9: R (Ridge) - Mandibular
  { id: 9, name: 'Ridge (R)', category: 'mandibular', color: '#3B82F6' },
  // 10: S (Sella) - Cranial
  { id: 10, name: 'Sella (S)', category: 'cranial', color: '#EF4444' },
  // 11: Ar (Articulare) - Cranial
  { id: 11, name: 'Articular (Ar)', category: 'cranial', color: '#EF4444' },
  // 12: Co (Condylion) - Mandibular
  { id: 12, name: 'Condylion (Co)', category: 'mandibular', color: '#3B82F6' },
  // 13: Go (Gonion) - Mandibular
  { id: 13, name: 'Gonion (Go)', category: 'mandibular', color: '#3B82F6' },
  // 14: Po (Porion) - Cranial
  { id: 14, name: 'Porion (Po)', category: 'cranial', color: '#EF4444' },
  // 15: LPM (Low Point Mandible) - Mandibular
  { id: 15, name: 'Low Point Mandible (LPM)', category: 'mandibular', color: '#3B82F6' },
  // 16: LMT (Lower Molar Tip) - Mandibular
  { id: 16, name: 'Lower Molar Tip (LMT)', category: 'mandibular', color: '#3B82F6' },
  // 17: UMT (Upper Molar Tip) - Dental
  { id: 17, name: 'Upper Molar Tip (UMT)', category: 'dental', color: '#22C55E' },
  // 18: UPM (Upper 2nd PM Cusp) - Dental
  { id: 18, name: 'Upper 2nd PM Cusp (UPM)', category: 'dental', color: '#22C55E' },
  // 19: UIA (Upper Incisor Apex) - Dental
  { id: 19, name: 'Upper Incisor Apex (UIA)', category: 'dental', color: '#22C55E' },
  // 20: UIT (Upper Incisor Tip) - Dental
  { id: 20, name: 'Upper Incisor Tip (UIT)', category: 'dental', color: '#22C55E' },
  // 21: UPM2 (Upper 2nd PM Cusp 2) - Dental (DUPLICADO en Aariz)
  { id: 21, name: 'Upper 2nd PM Cusp 2 (UPM2)', category: 'dental', color: '#22C55E' },
  // 22: LIA (Lower Incisor Apex) - Dental
  { id: 22, name: 'Lower Incisor Apex (LIA)', category: 'dental', color: '#22C55E' },
  // 23: LIT (Lower Incisor Tip) - Dental
  { id: 23, name: 'Lower Incisor Tip (LIT)', category: 'dental', color: '#22C55E' },
  // 24: LPM2 (Lower 2nd PM Cusp) - Dental (DUPLICADO en Aariz)
  { id: 24, name: 'Lower 2nd PM Cusp (LPM2)', category: 'dental', color: '#22C55E' },
  // 25: Ls (Labrale Superius) - Soft Tissue
  { id: 25, name: 'Labrale Superius (Ls)', category: 'soft-tissue', color: '#EAB308' },
  // 26: Sn (Subnasale) - Soft Tissue
  { id: 26, name: 'Subnasale (Sn)', category: 'soft-tissue', color: '#EAB308' },
  // 27: Pog' (Soft Pogonion) - Soft Tissue
  { id: 27, name: 'Soft Pogonion (Pog\')', category: 'soft-tissue', color: '#EAB308' },
  // 28: Glabela - Soft Tissue
  { id: 28, name: 'Glabela', category: 'soft-tissue', color: '#EAB308' },
]

export const CRANIAL_LANDMARKS = LANDMARKS.filter(l => l.category === 'cranial')
export const MANDIBULAR_LANDMARKS = LANDMARKS.filter(l => l.category === 'mandibular')
export const DENTAL_LANDMARKS = LANDMARKS.filter(l => l.category === 'dental')
export const SOFT_TISSUE_LANDMARKS = LANDMARKS.filter(l => l.category === 'soft-tissue')

export default LANDMARKS
