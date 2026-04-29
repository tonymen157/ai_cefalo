// Steiner analysis normal ranges and color coding

export const STEINER_RANGES = {
  SNA: {
    name: 'SNA',
    description: 'Maxillary position relative to cranial base',
    normal: { min: 81, max: 85 },
    slight: { min: 78, max: 88 }, // outside normal but not severe
    unit: '°',
  },
  SNB: {
    name: 'SNB',
    description: 'Mandibular position relative to cranial base',
    normal: { min: 78, max: 82 },
    slight: { min: 75, max: 85 },
    unit: '°',
  },
  ANB: {
    name: 'ANB',
    description: 'Maxillomandibular relationship',
    normal: { min: 0, max: 4 },
    slight: { min: -2, max: 6 },
    unit: '°',
  },
}

// Get color for angle value
export function getAngleColor(angleName, value) {
  const range = STEINER_RANGES[angleName]
  if (!range) return 'gray'

  if (value >= range.normal.min && value <= range.normal.max) {
    return 'green' // Normal
  } else if (value >= range.slight.min && value <= range.slight.max) {
    return 'yellow' // Slight deviation
  } else {
    return 'red' // Significant deviation
  }
}

// Get skeletal classification from ANB (Standard Steiner: Class I = 0-4°, Class II > 4°, Class III < 0°)
export function getSkeletalClassification(anb) {
  if (anb > 4.0) {
    return {
      class: 'Clase II',
      description: 'Prognatismo maxilar / Retrognatismo mandibular',
      color: anb > 6 ? 'red' : 'yellow',
    }
  } else if (anb < 0.0) {
    return {
      class: 'Clase III',
      description: 'Prognatismo mandibular / Retrognatismo maxilar',
      color: anb < -2 ? 'red' : 'yellow',
    }
  } else {
    return {
      class: 'Clase I',
      description: 'Normo-oclusión',
      color: 'green',
    }
  }
}
