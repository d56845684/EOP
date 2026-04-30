const normalizeValue = (value: unknown): unknown => {
  const rawValue = value;

  if (Array.isArray(rawValue)) {
    return rawValue.map((item) => normalizeValue(item));
  }

  if (rawValue && typeof rawValue === 'object') {
    return Object.keys(rawValue as Record<string, unknown>)
      .sort()
      .reduce<Record<string, unknown>>((acc, key) => {
        const item = (rawValue as Record<string, unknown>)[key];
        acc[key] = item === undefined ? null : normalizeValue(item);
        return acc;
      }, {});
  }

  return rawValue === undefined ? null : rawValue;
};

export const createFormSnapshot = (value: unknown) => JSON.stringify(normalizeValue(value));
