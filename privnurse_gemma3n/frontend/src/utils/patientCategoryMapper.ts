/**
 * Patient category mapping utilities
 * Ensures consistent patient category values across the application
 */

export const VALID_PATIENT_CATEGORIES = ['NHI General', 'NHI Injury', 'Self-Pay'] as const;
export type PatientCategory = typeof VALID_PATIENT_CATEGORIES[number];

/**
 * Validates and normalizes patient category values
 * Handles common mistakes and typos
 */
export function normalizePatientCategory(category: string | undefined | null): PatientCategory {
  if (!category) {
    return 'NHI General'; // Default value
  }

  // Direct match
  if (VALID_PATIENT_CATEGORIES.includes(category as PatientCategory)) {
    return category as PatientCategory;
  }

  // Common mistake mappings
  const categoryLower = category.toLowerCase();
  
  // Handle 'NHI Insurance' -> 'NHI General'
  if (categoryLower.includes('insurance') && categoryLower.includes('nhi')) {
    return 'NHI General';
  }
  
  // Case-insensitive matching
  for (const validCategory of VALID_PATIENT_CATEGORIES) {
    if (category.toLowerCase() === validCategory.toLowerCase()) {
      return validCategory;
    }
  }
  
  // Partial matching
  if (categoryLower.includes('general')) return 'NHI General';
  if (categoryLower.includes('injury')) return 'NHI Injury';
  if (categoryLower.includes('self') || categoryLower.includes('pay')) return 'Self-Pay';
  
  // Default fallback
  console.warn(`Unknown patient category: '${category}', defaulting to 'NHI General'`);
  return 'NHI General';
}