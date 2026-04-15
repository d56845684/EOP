export const triggerDownload = (blob: Blob, fileName: string) => {
  // 建立一個指向 Blob 的 URL
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;
  link.download = fileName; // 指定下載後的檔名

  // 為了相容性，將標籤加入 body 後再觸發
  document.body.appendChild(link);
  link.click();

  // 釋放記憶體與移除標籤
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export const getFileNameFromResponse = (response: any) => {
  const disposition = response.headers['content-disposition'];
  let fileName = 'default.docx';

  if (disposition) {
    const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
    if (utf8Match && utf8Match[1]) {
      fileName = decodeURIComponent(utf8Match[1]);
    } else {
      // 如果沒有 filename*，退而求其次找一般的 filename
      const normalMatch = disposition.match(/filename=(["']?)(.*?[^\\])\1(?:;|$)/i);
      if (normalMatch && normalMatch[2]) {
        fileName = normalMatch[2];
      }
    }
  }
  return fileName;
}