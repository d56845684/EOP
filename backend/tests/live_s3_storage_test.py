#!/usr/bin/env python3
"""
S3 Storage 上傳/下載/安全驗證 測試腳本

測試合約檔案的 S3 presigned URL 上傳與下載功能，包含：
1. 學生合約上傳 (presigned PUT → S3 → confirm-upload)
2. 學生合約下載 (presigned GET URL)
3. 教師合約上傳
4. 教師合約下載
5. 安全驗證 - Path traversal 防護
6. 安全驗證 - 錯誤前綴防護
7. 安全驗證 - S3 檔案不存在防護

使用方式:
    # 完整測試（需要 employee/admin 帳號，且需要已存在的合約）
    python tests/live_s3_storage_test.py --email employee@example.com --password testpass

    # 指定合約 ID
    python tests/live_s3_storage_test.py --email employee@example.com --password testpass \\
        --student-contract-id <uuid> --teacher-contract-id <uuid>

    # 自訂後端 URL
    python tests/live_s3_storage_test.py --email employee@example.com --password testpass \\
        --backend-url http://localhost:8001
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

# 設定
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")

# 最小合法 PDF 內容
TEST_PDF_CONTENT = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<<>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 100 700 Td (S3 Test) Tj ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000052 00000 n
0000000101 00000 n
0000000220 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
314
%%EOF"""


def load_env():
    """載入 .env 檔案"""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


load_env()


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0


class S3StorageTester:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip("/")
        self.results: list[TestResult] = []
        self.cookies: dict = {}
        self.user_role: str = ""

    def _record(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        self.results.append(TestResult(name, passed, message, duration_ms))
        status = "✅" if passed else "❌"
        dur = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        print(f"  {status} {name}{dur}")
        if message and not passed:
            print(f"     └─ {message}")

    async def login(self, email: str, password: str) -> bool:
        print("\n" + "=" * 60)
        print("🔐 登入")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            dur = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self.cookies = dict(resp.cookies)
                data = resp.json()
                self.user_role = data.get("user", {}).get("role", "unknown")
                self._record(f"登入成功 (角色: {self.user_role})", True, duration_ms=dur)
                return True
            else:
                self._record("登入", False,
                             f"狀態碼: {resp.status_code}, 回應: {resp.text[:200]}",
                             duration_ms=dur)
                return False

    async def _find_contract_id(self, contract_type: str) -> Optional[str]:
        """自動找一個存在的合約 ID"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.backend_url}/api/v1/{contract_type}",
                params={"per_page": 1},
                cookies=self.cookies,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    return data[0]["id"]
        return None

    # ─── Upload Tests ───

    async def test_upload(self, contract_type: str, contract_id: str) -> bool:
        """測試上傳流程：取得 presigned URL → PUT 到 S3 → confirm-upload"""
        label = "學生" if "student" in contract_type else "教師"
        print(f"\n" + "=" * 60)
        print(f"📤 測試{label}合約上傳 (S3 Presigned PUT)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: 取得 presigned upload URL
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/{contract_type}/{contract_id}/upload-url",
                cookies=self.cookies,
            )
            dur = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code != 200:
                self._record(f"{label}合約 - 取得上傳 URL", False,
                             f"狀態碼: {resp.status_code}, {resp.text}", duration_ms=dur)
                return False

            data = resp.json()
            upload_url = data.get("upload_url", "")
            storage_path = data.get("storage_path", "")

            has_s3 = "s3." in upload_url and "amazonaws.com" in upload_url
            has_sig = "X-Amz-Signature" in upload_url
            self._record(
                f"{label}合約 - 取得 presigned upload URL",
                has_s3 and has_sig,
                "" if has_s3 and has_sig else f"URL 格式異常: {upload_url[:100]}",
                duration_ms=dur,
            )
            print(f"     └─ storage_path: {storage_path}")

            # Step 2: PUT 檔案到 S3
            start = datetime.now()
            resp = await client.put(
                upload_url,
                content=TEST_PDF_CONTENT,
                headers={"Content-Type": "application/pdf"},
            )
            dur = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record(f"{label}合約 - PUT 檔案到 S3", True, duration_ms=dur)
            else:
                self._record(f"{label}合約 - PUT 檔案到 S3", False,
                             f"狀態碼: {resp.status_code}, {resp.text[:200]}", duration_ms=dur)
                return False

            # Step 3: confirm-upload
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/{contract_type}/{contract_id}/confirm-upload",
                json={"storage_path": storage_path, "file_name": "test_s3.pdf"},
                cookies=self.cookies,
            )
            dur = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                result = resp.json()
                status = result.get("data", {}).get("contract_status", "")
                self._record(f"{label}合約 - confirm-upload (狀態: {status})", True, duration_ms=dur)
                return True
            else:
                self._record(f"{label}合約 - confirm-upload", False,
                             f"狀態碼: {resp.status_code}, {resp.text[:200]}", duration_ms=dur)
                return False

    # ─── Download Tests ───

    async def test_download(self, contract_type: str, contract_id: str) -> bool:
        """測試下載流程：取得 presigned GET URL → 從 S3 下載檔案"""
        label = "學生" if "student" in contract_type else "教師"
        print(f"\n" + "=" * 60)
        print(f"📥 測試{label}合約下載 (S3 Presigned GET)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Step 1: 取得 presigned download URL
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/{contract_type}/{contract_id}/download-url",
                cookies=self.cookies,
            )
            dur = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code != 200:
                self._record(f"{label}合約 - 取得下載 URL", False,
                             f"狀態碼: {resp.status_code}, {resp.text}", duration_ms=dur)
                return False

            data = resp.json()
            download_url = data.get("download_url", "")
            file_name = data.get("file_name", "")

            has_s3 = "s3." in download_url and "amazonaws.com" in download_url
            has_sig = "X-Amz-Signature" in download_url
            self._record(
                f"{label}合約 - 取得 presigned download URL",
                has_s3 and has_sig,
                "" if has_s3 and has_sig else f"URL 格式異常: {download_url[:100]}",
                duration_ms=dur,
            )
            print(f"     └─ file_name: {file_name}")

            # Step 2: 從 S3 下載檔案
            start = datetime.now()
            resp = await client.get(download_url)
            dur = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                content_len = len(resp.content)
                self._record(
                    f"{label}合約 - 從 S3 下載成功 ({content_len} bytes, {content_type})",
                    True, duration_ms=dur,
                )
                return True
            else:
                self._record(f"{label}合約 - 從 S3 下載", False,
                             f"狀態碼: {resp.status_code}", duration_ms=dur)
                return False

    # ─── Security Tests ───

    async def test_security(self, contract_id: str) -> None:
        """測試安全驗證：path traversal、錯誤前綴、S3 檔案不存在"""
        print("\n" + "=" * 60)
        print("🔒 測試安全驗證 (confirm-upload)")
        print("=" * 60 + "\n")

        test_cases = [
            {
                "name": "Path traversal 攻擊",
                "storage_path": "../../../etc/passwd",
                "file_name": "hack.pdf",
                "expected_status": 400,
                "expected_detail": "無效的檔案路徑格式",
            },
            {
                "name": "錯誤前綴 (teacher → student endpoint)",
                "storage_path": "teacher-contracts/abc-def/aabbccdd.pdf",
                "file_name": "test.pdf",
                "expected_status": 400,
                "expected_detail": "無效的檔案路徑格式",
            },
            {
                "name": "非法副檔名 (.exe)",
                "storage_path": f"student-contracts/{contract_id}/aabbccdd11223344.exe",
                "file_name": "test.exe",
                "expected_status": 400,
                "expected_detail": "無效的檔案路徑格式",
            },
            {
                "name": "合法格式但 S3 檔案不存在",
                "storage_path": f"student-contracts/{contract_id}/aaaa1111bbbb2222cccc3333dddd4444.pdf",
                "file_name": "test.pdf",
                "expected_status": 400,
                "expected_detail": "檔案尚未上傳至 S3",
            },
        ]

        async with httpx.AsyncClient(timeout=30.0) as client:
            for tc in test_cases:
                start = datetime.now()
                resp = await client.post(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/confirm-upload",
                    json={"storage_path": tc["storage_path"], "file_name": tc["file_name"]},
                    cookies=self.cookies,
                )
                dur = (datetime.now() - start).total_seconds() * 1000

                actual_status = resp.status_code
                actual_detail = resp.json().get("detail", "") if resp.status_code >= 400 else ""

                passed = (actual_status == tc["expected_status"]
                          and tc["expected_detail"] in actual_detail)
                self._record(
                    f"拒絕 {tc['name']}",
                    passed,
                    "" if passed else f"預期 {tc['expected_status']}({tc['expected_detail']}), "
                                      f"實際 {actual_status}({actual_detail})",
                    duration_ms=dur,
                )

    # ─── Summary ───

    def print_summary(self) -> bool:
        print("\n" + "=" * 60)
        print("📊 測試摘要")
        print("=" * 60 + "\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"  總計: {total} 項測試")
        print(f"  通過: {passed} ✅")
        print(f"  失敗: {failed} ❌")
        print(f"  成功率: {passed / total * 100:.1f}%" if total > 0 else "  成功率: N/A")
        print()

        if failed > 0:
            print("  失敗的測試:")
            for r in self.results:
                if not r.passed:
                    print(f"    - {r.name}: {r.message}")
            print()

        return failed == 0


async def main():
    parser = argparse.ArgumentParser(
        description="S3 Storage 上傳/下載/安全驗證 測試腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 完整測試（自動尋找合約）
  python tests/live_s3_storage_test.py --email employee@example.com --password testpass

  # 指定合約 ID
  python tests/live_s3_storage_test.py --email employee@example.com --password testpass \\
      --student-contract-id <uuid> --teacher-contract-id <uuid>
        """,
    )

    parser.add_argument("--email", required=True, help="登入 Email")
    parser.add_argument("--password", required=True, help="登入密碼")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"後端 URL (預設: {BACKEND_URL})")
    parser.add_argument("--student-contract-id", default=None, help="指定學生合約 ID")
    parser.add_argument("--teacher-contract-id", default=None, help="指定教師合約 ID")

    args = parser.parse_args()

    tester = S3StorageTester(args.backend_url)

    print("\n" + "🚀" * 20)
    print("\n   S3 Storage 上傳/下載/安全驗證 測試")
    print(f"   後端: {args.backend_url}")
    print("\n" + "🚀" * 20)

    try:
        # 1. 登入
        if not await tester.login(args.email, args.password):
            tester.print_summary()
            return 1

        if tester.user_role not in ["admin", "employee"]:
            print(f"\n⚠️  目前角色為 '{tester.user_role}'，上傳測試需要 employee/admin 權限")
            tester.print_summary()
            return 1

        # 2. 取得合約 ID
        student_cid = args.student_contract_id or await tester._find_contract_id("student-contracts")
        teacher_cid = args.teacher_contract_id or await tester._find_contract_id("teacher-contracts")

        if not student_cid:
            print("\n⚠️  找不到學生合約，請先建立或用 --student-contract-id 指定")
        if not teacher_cid:
            print("\n⚠️  找不到教師合約，請先建立或用 --teacher-contract-id 指定")

        # 3. 學生合約上傳/下載
        if student_cid:
            await tester.test_upload("student-contracts", student_cid)
            await tester.test_download("student-contracts", student_cid)

        # 4. 教師合約上傳/下載
        if teacher_cid:
            await tester.test_upload("teacher-contracts", teacher_cid)
            await tester.test_download("teacher-contracts", teacher_cid)

        # 5. 安全驗證（用學生合約 endpoint）
        if student_cid:
            await tester.test_security(student_cid)

        # 6. 摘要
        success = tester.print_summary()
        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n\n⚠️  測試中斷")
        return 1
    except Exception as e:
        print(f"\n❌ 測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
