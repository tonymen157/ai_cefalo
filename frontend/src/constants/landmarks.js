// 29 landmarks for Aariz dataset
// Categories: cranial (red), mandibular (blue), dental (green), soft-tissue (yellow)

const LANDMARKS = [
  // Cranial bones (red) - ALL skeletal points of maxilla and cranial base
  { id: 0, name: 'Sella (S)', category: 'cranial', color: '#EF4444' },
  { id: 1, name: 'Nasion (N)', category: 'cranial', color: '#EF4444' },
  { id: 2, name: 'Articular (Ar)', category: 'cranial', color: '#EF4444' },
  { id: 3, name: 'Porion (Po)', category: 'cranial', color: '#EF4444' },
  { id: 4, name: 'Posterior Nasal Spine (PNS)', category: 'cranial', color: '#EF4444' },
  { id: 5, name: 'A-point (Subspinale)', category: 'cranial', color: '#EF4444' },
  { id: 6, name: 'Anterior Nasal Spine (ANS)', category: 'cranial', color: '#EF4444' },

  // Mandibular bones (blue)
  { id: 7, name: 'B-point (Supramental)', category: 'mandibular', color: '#3B82F6' },
  { id: 8, name: 'Menton (Me)', category: 'mandibular', color: '#3B82F6' },
  { id: 9, name: 'Gonion (Go)', category: 'mandibular', color: '#3B82F6' },
  { id: 10, name: 'Pogonion (Pog)', category: 'mandibular', color: '#3B82F6' },
  { id: 11, name: 'Gnathion (Gn)', category: 'mandibular', color: '#3B82F6' },
  { id: 12, name: 'Ramus (R)', category: 'mandibular', color: '#3B82F6' },
  { id: 13, name: 'Condylion (Co)', category: 'mandibular', color: '#3B82F6' },

  // Dental (green)
  { id: 14, name: 'Upper Incisor Tip (UIT)', category: 'dental', color: '#22C55E' },
  { id: 15, name: 'Upper Incisor Apex (UIA)', category: 'dental', color: '#22C55E' },
  { id: 16, name: 'Upper Molar Cusp (UMT)', category: 'dental', color: '#22C55E' },
  { id: 17, name: 'Upper 2nd PM Cusp (UPM)', category: 'dental', color: '#22C55E' },
  { id: 18, name: 'Lower Incisor Tip (LIT)', category: 'dental', color: '#22C55E' },
  { id: 19, name: 'Lower Incisor Apex (LIA)', category: 'dental', color: '#22C55E' },
  { id: 20, name: 'Lower Molar Cusp (LMT)', category: 'dental', color: '#22C55E' },
  { id: 21, name: 'Lower 2nd PM Cusp (LPM)', category: 'dental', color: '#22C55E' },

  // Soft tissue (yellow)
  { id: 22, name: 'Pronasale (Pn)', category: 'soft-tissue', color: '#EAB308' },
  { id: 23, name: 'Subnasale (Sn)', category: 'soft-tissue', color: '#EAB308' },
  { id: 24, name: 'Soft Tissue Nasion', category: 'soft-tissue', color: '#EAB308' },
  { id: 25, name: 'Labrale superius (Ls)', category: 'soft-tissue', color: '#EAB308' },
  { id: 26, name: 'Labrale inferius (Li)', category: 'soft-tissue', color: '#EAB308' },
  { id: 27, name: 'Soft Tissue Pogonion', category: 'soft-tissue', color: '#EAB308' },
  { id: 28, name: 'Glabela', category: 'soft-tissue', color: '#EAB308' },
]

export const CRANIAL_LANDMARKS = LANDMARKS.filter(l => l.category === 'cranial')
export const MANDIBULAR_LANDMARKS = LANDMARKS.filter(l => l.category === 'mandibular')
export const DENTAL_LANDMARKS = LANDMARKS.filter(l => l.category === 'dental')
export const SOFT_TISSUE_LANDMARKS = LANDMARKS.filter(l => l.category === 'soft-tissue')

export default LANDMARKS
