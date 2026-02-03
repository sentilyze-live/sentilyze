/**
 * Format a number with Turkish locale formatting
 * Uses Turkish number formatting with spaces as thousand separators
 */
export function formatTurkishNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '0';
  }
  
  // Format with Turkish locale (spaces for thousands)
  return new Intl.NumberFormat('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a number with Turkish locale for prices (more decimals)
 */
export function formatTurkishPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return '0.00';
  }
  
  return new Intl.NumberFormat('tr-TR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}
