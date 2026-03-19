/**
 * 태그/카테고리 배열을 정규화한다:
 * - 공백 trim
 * - 소문자 변환
 * - 빈 항목 제거
 * - 중복 제거 (삽입 순서 유지)
 * - 최대 개수 제한 (선택)
 */
export function normalizeTags(input: unknown, maxCount?: number): string[] {
  if (!Array.isArray(input)) return [];
  const normalized = [
    ...new Set(
      input
        .map((t) => (typeof t === 'string' ? t.trim().toLowerCase() : ''))
        .filter(Boolean),
    ),
  ];
  return maxCount !== undefined ? normalized.slice(0, maxCount) : normalized;
}
