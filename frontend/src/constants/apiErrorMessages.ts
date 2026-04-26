export const API_ERROR_CODE_TRANSLATION_KEY_MAP: Record<string, string> = {
  AUTH_ERROR: 'apiErrors.AUTH_ERROR',
  AUTH_TOKEN_EXPIRED: 'apiErrors.AUTH_TOKEN_EXPIRED',
  AUTH_TOKEN_INVALID: 'apiErrors.AUTH_TOKEN_INVALID',
  AUTH_SESSION_EXPIRED: 'apiErrors.AUTH_SESSION_EXPIRED',
  AUTH_IDLE_TIMEOUT: 'apiErrors.AUTH_IDLE_TIMEOUT',
  AUTH_SESSION_REPLACED: 'apiErrors.AUTH_SESSION_REPLACED',
  AUTH_LOGIN_FAILED: 'apiErrors.AUTH_LOGIN_FAILED',
  AUTH_API_KEY_INVALID: 'apiErrors.AUTH_API_KEY_INVALID',
  FORBIDDEN: 'apiErrors.FORBIDDEN',
  FORBIDDEN_ROLE: 'apiErrors.FORBIDDEN_ROLE',
  FORBIDDEN_OWNER: 'apiErrors.FORBIDDEN_OWNER',
  FORBIDDEN_PROTECTED: 'apiErrors.FORBIDDEN_PROTECTED',
  FORBIDDEN_PAGE: 'apiErrors.FORBIDDEN_PAGE',
  NOT_FOUND: 'apiErrors.NOT_FOUND',
  VALIDATION_ERROR: 'apiErrors.VALIDATION_ERROR',
  DUPLICATE_ENTRY: 'apiErrors.DUPLICATE_ENTRY',
  NO_UPDATE_DATA: 'apiErrors.NO_UPDATE_DATA',
  INVALID_STATE: 'apiErrors.INVALID_STATE',
  INVALID_FILE: 'apiErrors.INVALID_FILE',
  QUOTA_EXCEEDED: 'apiErrors.QUOTA_EXCEEDED',
  WRONG_PASSWORD: 'apiErrors.WRONG_PASSWORD',
  CONFLICT: 'apiErrors.CONFLICT',
  RATE_LIMITED: 'apiErrors.RATE_LIMITED',
  INTERNAL_ERROR: 'apiErrors.INTERNAL_ERROR',
  SERVICE_UNAVAILABLE: 'apiErrors.SERVICE_UNAVAILABLE',
};

interface ApiErrorRequestTranslationRule {
  errorCode: string;
  key: string;
  requestPattern: RegExp;
}

const API_ERROR_REQUEST_TRANSLATION_RULES: ApiErrorRequestTranslationRule[] = [
  {
    requestPattern: /\/v1\/students\/[^/]+\/convert-to-formal$/,
    errorCode: 'VALIDATION_ERROR',
    key: 'apiErrorsByRequest.studentConvertToFormal.VALIDATION_ERROR',
  },
];

export const getApiErrorTranslationKey = (errorCode?: string | null) => {
  if (!errorCode) return '';
  return API_ERROR_CODE_TRANSLATION_KEY_MAP[errorCode] ?? '';
};

export const getApiErrorTranslationKeyByRequest = (
  requestUrl?: string | null,
  errorCode?: string | null,
) => {
  if (!requestUrl || !errorCode) return '';

  const normalizedUrl = requestUrl.split('?')[0] ?? '';
  const matchedRule = API_ERROR_REQUEST_TRANSLATION_RULES.find((rule) => (
    rule.errorCode === errorCode && rule.requestPattern.test(normalizedUrl)
  ));

  return matchedRule?.key ?? '';
};
