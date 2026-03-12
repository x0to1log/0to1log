export function formatPipelineError(error) {
  const raw = typeof error === 'string' ? error.trim() : '';
  if (!raw) return '';

  const contentTooShortMatch = raw.match(
    /Content too short:\s*(\d+)\s*chars\s*\(min\s*(\d+)\)/i,
  );

  if (contentTooShortMatch) {
    const [, actual, minimum] = contentTooShortMatch;
    if (/businesspost/i.test(raw)) {
      return `Business post too short: ${actual} / ${minimum} chars.`;
    }
    return `Research post too short: ${actual} / ${minimum} chars.`;
  }

  return raw;
}
