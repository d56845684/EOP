FROM python:3.12-slim

WORKDIR /app

# WeasyPrint 系統依賴（pango/cairo/CJK 字型）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev libcairo2 fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 執行
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]