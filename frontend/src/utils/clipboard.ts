import { ElMessage } from 'element-plus';

/**
 * 複製文字到剪貼簿的共用函式
 * @param text 要複製的文字
 * @param successMessage 複製成功時的提示文字，預設為 '已複製'
 */
export const copyToClipboardUtil = async (text: string, successMessage: string = '已複製') => {
  if (!text) return;
  try {
    if (navigator.clipboard) {
      await navigator.clipboard.writeText(text);
    } else {
      // 降級處理 (舊版瀏覽器)
      const textArea = document.createElement('textarea');
      textArea.value = text;
      // 確保不影響畫面佈局
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      textArea.style.top = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      try {
        document.execCommand('copy');
      } catch (err) {
        console.error('Fallback copy execCommand failed', err);
        ElMessage.error('複製失敗');
        document.body.removeChild(textArea);
        return;
      }
      document.body.removeChild(textArea);
    }
    ElMessage.success(successMessage);
  } catch (err) {
    console.error('Failed to copy text: ', err);
    ElMessage.error('複製失敗，請檢查瀏覽器權限');
  }
};
