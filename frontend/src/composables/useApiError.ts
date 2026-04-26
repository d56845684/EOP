import { ElMessage } from 'element-plus';
import { getApiErrorMessage } from '@/api/response';

interface ShowApiErrorOptions {
  closable?: boolean;
  onError?: (message: string, error: unknown) => void;
  showMessage?: boolean;
}

export function useApiError() {
  const getApiError = (error: unknown, fallback = '操作失敗') => getApiErrorMessage(error, fallback);

  const showApiError = (
    error: unknown,
    fallback = '操作失敗',
    options: ShowApiErrorOptions = {},
  ) => {
    const message = getApiError(error, fallback);

    if (options.showMessage !== false) {
      if (options.closable !== false) {
        ElMessage.closeAll();
      }
      ElMessage.error(message);
    }

    options.onError?.(message, error);
    return message;
  };

  const createApiErrorHandler = (fallback = '操作失敗', options?: ShowApiErrorOptions) => {
    return (error: unknown) => showApiError(error, fallback, options);
  };

  return {
    getApiError,
    showApiError,
    createApiErrorHandler,
  };
}
