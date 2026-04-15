#!/usr/bin/env python3
"""
End-to-End Contracts Flow Test (Student + Teacher)

學生合約：建立 → 查詢 → 修改 → 明細 CRUD → 產生 PDF → S3 上傳/下載 → 刪除
教師合約：建立 → 查詢 → 修改 → 明細 CRUD（課程費率）→ 產生 PDF → S3 上傳/下載 → 刪除

使用方式:
    python tests/live_e2e_contracts_test.py \
        --email eopAdmin@example.com --password yourpassword
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, timedelta

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2ECTR{_TS}_"


class ContractsTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None

        # base data
        self.student_id = None
        self.teacher_id = None
        self.course_id = None

        # student contract
        self.sc_id = None
        self.sc_detail_id = None

        # teacher contract
        self.tc_id = None
        self.tc_detail_id = None

    async def _post(self, path, json_data=None):
        return await self.client.post(f"{self.url}{path}", json=json_data or {})

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _put(self, path, json_data=None):
        return await self.client.put(f"{self.url}{path}", json=json_data or {})

    async def _delete(self, path):
        return await self.client.delete(f"{self.url}{path}")

    async def _test(self, name, fn):
        try:
            result = await fn()
            passed = result is True
            msg = "" if passed else str(result)
            self.results.append((name, passed, msg))
            print(f"  {'✓' if passed else '✗'} {name}" + (f" — {msg}" if msg else ""))
            return passed
        except Exception as e:
            self.results.append((name, False, str(e)))
            print(f"  ✗ {name} — ERROR: {e}")
            return False

    async def run(self, email: str, password: str):
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            self.client = client

            print(f"\n{'=' * 65}")
            print(f"  E2E Contracts Flow Test (Student + Teacher)")
            print(f"  Backend: {self.url}")
            print(f"{'=' * 65}")

            # Login
            resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
            if resp.status_code != 200:
                print(f"\n  ✗ Login failed: {resp.status_code}")
                return False
            print(f"\n  ✓ Login")

            # Prereqs
            print(f"\n  Prereqs: 建立基礎資料")
            print("  " + "-" * 40)
            await self._test("建立課程", self._create_course)
            await self._test("建立學生", self._create_student)
            await self._test("建立教師", self._create_teacher)

            # Phase 1: Student Contract
            print(f"\n  Phase 1: 學生合約 CRUD")
            print("  " + "-" * 40)
            await self._test("建立學生合約", self._sc_create)
            await self._test("查詢學生合約", self._sc_get)
            await self._test("修改學生合約", self._sc_update)
            await self._test("驗證修改結果", self._sc_verify_update)

            print(f"\n  Phase 1.5: 學生合約明細")
            print("  " + "-" * 40)
            await self._test("新增合約明細", self._sc_add_detail)
            await self._test("查詢明細列表", self._sc_list_details)
            await self._test("刪除合約明細", self._sc_delete_detail)

            print(f"\n  Phase 1.6: 學生合約 PDF + S3")
            print("  " + "-" * 40)
            await self._test("產生合約 DOCX", self._sc_generate_docx)
            await self._test("取得上傳 URL", self._sc_get_upload_url)
            await self._test("上傳檔案到 S3", self._sc_upload_to_s3)
            await self._test("確認上傳", self._sc_confirm_upload)
            await self._test("下載驗證", self._sc_download_verify)

            # Phase 2: Teacher Contract
            print(f"\n  Phase 2: 教師合約 CRUD")
            print("  " + "-" * 40)
            await self._test("建立教師合約", self._tc_create)
            await self._test("查詢教師合約", self._tc_get)
            await self._test("修改教師合約", self._tc_update)
            await self._test("驗證修改結果", self._tc_verify_update)

            print(f"\n  Phase 2.5: 教師合約明細（課程費率）")
            print("  " + "-" * 40)
            await self._test("新增課程費率明細", self._tc_add_detail)
            await self._test("驗證合約含明細", self._tc_verify_detail)
            await self._test("刪除明細", self._tc_delete_detail)

            print(f"\n  Phase 2.6: 教師合約 PDF + S3")
            print("  " + "-" * 40)
            await self._test("產生合約 PDF", self._tc_generate_pdf)
            await self._test("取得上傳 URL", self._tc_get_upload_url)
            await self._test("上傳檔案到 S3", self._tc_upload_to_s3)
            await self._test("確認上傳", self._tc_confirm_upload)
            await self._test("下載驗證", self._tc_download_verify)

            # Phase 3: S3 安全驗證
            print(f"\n  Phase 3: S3 安全驗證")
            print("  " + "-" * 40)
            await self._test("拒絕 Path traversal 攻擊", self._sec_path_traversal)
            await self._test("拒絕錯誤前綴路徑", self._sec_wrong_prefix)
            await self._test("拒絕非法副檔名 (.exe)", self._sec_bad_extension)
            await self._test("拒絕 S3 檔案不存在", self._sec_file_not_exists)

            # Phase 4: 刪除
            print(f"\n  Phase 4: 刪除合約")
            print("  " + "-" * 40)
            await self._test("刪除學生合約", self._sc_delete)
            await self._test("驗證學生合約已刪除", self._sc_verify_deleted)
            await self._test("刪除教師合約", self._tc_delete)
            await self._test("驗證教師合約已刪除", self._tc_verify_deleted)

            # Cleanup
            print(f"\n  Cleanup")
            print("  " + "-" * 40)
            await self._cleanup()

            passed = sum(1 for _, ok, _ in self.results if ok)
            failed = sum(1 for _, ok, _ in self.results if not ok)
            print(f"\n{'=' * 65}")
            print(f"  Results: {passed}/{len(self.results)} passed — {'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
            if failed:
                for name, ok, msg in self.results:
                    if not ok:
                        print(f"    ✗ {name}: {msg}")
            print(f"{'=' * 65}\n")
            return failed == 0

    # ── Prereqs ──

    async def _create_course(self):
        resp = await self._post("/api/v1/courses", {
            "course_code": f"{TEST_PREFIX}C01", "course_name": f"{TEST_PREFIX}測試課程",
            "duration_minutes": 60,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.course_id = resp.json()["data"]["id"]
        return True

    async def _create_student(self):
        resp = await self._post("/api/v1/students", {
            "student_no": f"{TEST_PREFIX}S01", "name": f"{TEST_PREFIX}合約測試學生",
            "email": f"{TEST_PREFIX}s@example.com", "student_type": "formal",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_id = resp.json()["data"]["id"]
        return True

    async def _create_teacher(self):
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T01", "name": f"{TEST_PREFIX}合約測試教師",
            "email": f"{TEST_PREFIX}t@example.com", "teacher_level": 2,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.teacher_id = resp.json()["data"]["id"]
        return True

    # ── Student Contract CRUD ──

    async def _sc_create(self):
        today = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/student-contracts", {
            "student_id": self.student_id, "contract_status": "pending",
            "start_date": today, "end_date": end,
            "total_lessons": 24, "remaining_lessons": 24, "total_amount": 36000,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        self.sc_id = data["id"]
        if data.get("total_lessons") != 24: return f"total_lessons={data.get('total_lessons')}"
        return True

    async def _sc_get(self):
        resp = await self._get(f"/api/v1/student-contracts/{self.sc_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json()["data"]
        if data.get("remaining_lessons") != 24: return f"remaining={data.get('remaining_lessons')}"
        return True

    async def _sc_update(self):
        resp = await self._put(f"/api/v1/student-contracts/{self.sc_id}", {
            "contract_status": "active", "notes": f"{TEST_PREFIX} updated",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _sc_verify_update(self):
        resp = await self._get(f"/api/v1/student-contracts/{self.sc_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json()["data"]
        if data.get("contract_status") != "active": return f"status={data.get('contract_status')}"
        return True

    # Student Contract Details

    async def _sc_add_detail(self):
        resp = await self._post(f"/api/v1/student-contracts/{self.sc_id}/details", {
            "detail_type": "discount", "description": f"{TEST_PREFIX} 折扣", "amount": 5000,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.sc_detail_id = resp.json()["data"]["id"]
        return True

    async def _sc_list_details(self):
        resp = await self._get(f"/api/v1/student-contracts/{self.sc_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        details = resp.json()["data"].get("details", [])
        if not any(d.get("id") == self.sc_detail_id for d in details): return "detail not found in contract"
        return True

    async def _sc_delete_detail(self):
        resp = await self._delete(f"/api/v1/student-contracts/{self.sc_id}/details/{self.sc_detail_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        return True

    # Student Contract PDF + S3

    async def _sc_generate_docx(self):
        resp = await self._get(f"/api/v1/student-contracts/{self.sc_id}/generate-docx")
        if resp.status_code != 200: return f"{resp.status_code}"
        ct = resp.headers.get("content-type", "")
        if "application/" not in ct: return f"unexpected content-type: {ct}"
        if len(resp.content) < 100: return f"file too small: {len(resp.content)} bytes"
        return True

    async def _sc_get_upload_url(self):
        resp = await self._post(f"/api/v1/student-contracts/{self.sc_id}/upload-url", {
            "file_name": f"{TEST_PREFIX}signed.pdf",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()
        self._sc_upload_url = data.get("upload_url")
        self._sc_storage_path = data.get("storage_path")
        if not self._sc_upload_url: return "no upload_url"
        return True

    async def _sc_upload_to_s3(self):
        self._sc_upload_content = f"%PDF-1.4 student contract test {TEST_PREFIX}".encode()
        async with httpx.AsyncClient(timeout=30.0) as raw:
            resp = await raw.put(self._sc_upload_url, content=self._sc_upload_content, headers={"Content-Type": "application/pdf"})
        if resp.status_code not in (200, 201): return f"S3 PUT {resp.status_code}"
        return True

    async def _sc_confirm_upload(self):
        resp = await self._post(f"/api/v1/student-contracts/{self.sc_id}/confirm-upload", {
            "storage_path": self._sc_storage_path, "file_name": f"{TEST_PREFIX}signed.pdf",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _sc_download_verify(self):
        resp = await self._get(f"/api/v1/student-contracts/{self.sc_id}/download-url")
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()
        download_url = data.get("download_url") or data.get("data", {}).get("download_url")
        if not download_url: return "no download_url"
        # 實際下載並比對內容
        async with httpx.AsyncClient(timeout=30.0) as raw:
            dl_resp = await raw.get(download_url)
        if dl_resp.status_code != 200: return f"download failed: {dl_resp.status_code}"
        if dl_resp.content != self._sc_upload_content:
            return f"content mismatch: uploaded {len(self._sc_upload_content)} bytes, downloaded {len(dl_resp.content)} bytes"
        return True

    # Student Contract Delete

    async def _sc_delete(self):
        resp = await self._delete(f"/api/v1/student-contracts/{self.sc_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self._deleted_sc_id = self.sc_id
        self.sc_id = None
        return True

    async def _sc_verify_deleted(self):
        resp = await self._get(f"/api/v1/student-contracts/{self._deleted_sc_id}")
        if resp.status_code == 404: return True
        if resp.status_code == 200:
            if resp.json().get("data", {}).get("is_deleted") is True: return True
        return f"expected 404, got {resp.status_code}"

    # ── Teacher Contract CRUD ──

    async def _tc_create(self):
        today = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": self.teacher_id, "contract_status": "pending",
            "start_date": today, "end_date": end,
            "employment_type": "hourly", "trial_to_formal_bonus": 500,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()["data"]
        self.tc_id = data["id"]
        if data.get("employment_type") != "hourly": return f"employment_type={data.get('employment_type')}"
        return True

    async def _tc_get(self):
        resp = await self._get(f"/api/v1/teacher-contracts/{self.tc_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json()["data"]
        if data.get("teacher_id") != self.teacher_id: return "teacher_id mismatch"
        return True

    async def _tc_update(self):
        resp = await self._put(f"/api/v1/teacher-contracts/{self.tc_id}", {
            "contract_status": "active", "trial_to_formal_bonus": 800,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _tc_verify_update(self):
        resp = await self._get(f"/api/v1/teacher-contracts/{self.tc_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json()["data"]
        if data.get("contract_status") != "active": return f"status={data.get('contract_status')}"
        bonus = data.get("trial_to_formal_bonus")
        if bonus is not None and float(bonus) != 800: return f"bonus={bonus}, expected 800"
        return True

    # Teacher Contract Details

    async def _tc_add_detail(self):
        resp = await self._post(f"/api/v1/teacher-contracts/{self.tc_id}/details", {
            "detail_type": "course_rate", "course_id": self.course_id,
            "description": f"{TEST_PREFIX} 課程費率", "amount": 900,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.tc_detail_id = resp.json()["data"]["id"]
        return True

    async def _tc_verify_detail(self):
        resp = await self._get(f"/api/v1/teacher-contracts/{self.tc_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        details = resp.json()["data"].get("details", [])
        rate_details = [d for d in details if d.get("detail_type") == "course_rate"]
        if not rate_details: return "no course_rate detail found"
        if rate_details[0].get("amount") != 900: return f"amount={rate_details[0].get('amount')}"
        return True

    async def _tc_delete_detail(self):
        resp = await self._delete(f"/api/v1/teacher-contracts/{self.tc_id}/details/{self.tc_detail_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        return True

    # Teacher Contract PDF + S3

    async def _tc_generate_pdf(self):
        resp = await self._get(f"/api/v1/teacher-contracts/{self.tc_id}/generate-pdf")
        if resp.status_code != 200: return f"{resp.status_code}"
        ct = resp.headers.get("content-type", "")
        if "application/" not in ct: return f"unexpected content-type: {ct}"
        if len(resp.content) < 100: return f"file too small: {len(resp.content)} bytes"
        return True

    async def _tc_get_upload_url(self):
        resp = await self._post(f"/api/v1/teacher-contracts/{self.tc_id}/upload-url", {
            "file_name": f"{TEST_PREFIX}signed.pdf",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()
        self._tc_upload_url = data.get("upload_url")
        self._tc_storage_path = data.get("storage_path")
        if not self._tc_upload_url: return "no upload_url"
        return True

    async def _tc_upload_to_s3(self):
        self._tc_upload_content = f"%PDF-1.4 teacher contract test {TEST_PREFIX}".encode()
        async with httpx.AsyncClient(timeout=30.0) as raw:
            resp = await raw.put(self._tc_upload_url, content=self._tc_upload_content, headers={"Content-Type": "application/pdf"})
        if resp.status_code not in (200, 201): return f"S3 PUT {resp.status_code}"
        return True

    async def _tc_confirm_upload(self):
        resp = await self._post(f"/api/v1/teacher-contracts/{self.tc_id}/confirm-upload", {
            "storage_path": self._tc_storage_path, "file_name": f"{TEST_PREFIX}signed.pdf",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _tc_download_verify(self):
        resp = await self._get(f"/api/v1/teacher-contracts/{self.tc_id}/download-url")
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()
        download_url = data.get("download_url") or data.get("data", {}).get("download_url")
        if not download_url: return "no download_url"
        # 實際下載並比對內容
        async with httpx.AsyncClient(timeout=30.0) as raw:
            dl_resp = await raw.get(download_url)
        if dl_resp.status_code != 200: return f"download failed: {dl_resp.status_code}"
        if dl_resp.content != self._tc_upload_content:
            return f"content mismatch: uploaded {len(self._tc_upload_content)} bytes, downloaded {len(dl_resp.content)} bytes"
        return True

    # ── S3 Security Tests ──

    async def _sec_confirm(self, storage_path: str, file_name: str) -> int:
        """呼叫 confirm-upload 並回傳 status code"""
        resp = await self._post(f"/api/v1/student-contracts/{self.sc_id}/confirm-upload", {
            "storage_path": storage_path, "file_name": file_name,
        })
        return resp.status_code

    async def _sec_path_traversal(self):
        code = await self._sec_confirm("../../../etc/passwd", "hack.pdf")
        if code != 400: return f"expected 400, got {code}"
        return True

    async def _sec_wrong_prefix(self):
        code = await self._sec_confirm("teacher-contracts/abc-def/aabbccdd.pdf", "test.pdf")
        if code != 400: return f"expected 400, got {code}"
        return True

    async def _sec_bad_extension(self):
        code = await self._sec_confirm(f"student-contracts/{self.sc_id}/aabb1122.exe", "test.exe")
        if code != 400: return f"expected 400, got {code}"
        return True

    async def _sec_file_not_exists(self):
        code = await self._sec_confirm(f"student-contracts/{self.sc_id}/aaaa1111bbbb2222cccc3333dddd4444.pdf", "test.pdf")
        if code != 400: return f"expected 400, got {code}"
        return True

    # Teacher Contract Delete

    async def _tc_delete(self):
        resp = await self._delete(f"/api/v1/teacher-contracts/{self.tc_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self._deleted_tc_id = self.tc_id
        self.tc_id = None
        return True

    async def _tc_verify_deleted(self):
        resp = await self._get(f"/api/v1/teacher-contracts/{self._deleted_tc_id}")
        if resp.status_code == 404: return True
        if resp.status_code == 200:
            if resp.json().get("data", {}).get("is_deleted") is True: return True
        return f"expected 404, got {resp.status_code}"

    # ── Cleanup ──

    async def _cleanup(self):
        for name, path in [
            ("sc_detail", f"/api/v1/student-contracts/{self.sc_id}/details/{self.sc_detail_id}" if self.sc_id and self.sc_detail_id else None),
            ("student_contract", f"/api/v1/student-contracts/{self.sc_id}" if self.sc_id else None),
            ("tc_detail", f"/api/v1/teacher-contracts/{self.tc_id}/details/{self.tc_detail_id}" if self.tc_id and self.tc_detail_id else None),
            ("teacher_contract", f"/api/v1/teacher-contracts/{self.tc_id}" if self.tc_id else None),
            ("teacher", f"/api/v1/teachers/{self.teacher_id}" if self.teacher_id else None),
            ("student", f"/api/v1/students/{self.student_id}" if self.student_id else None),
            ("course", f"/api/v1/courses/{self.course_id}" if self.course_id else None),
        ]:
            if not path: continue
            resp = await self._delete(path)
            s = "OK" if resp.status_code in (200, 204, 404) else f"WARN({resp.status_code})"
            print(f"    {name}: {s}")


async def main():
    parser = argparse.ArgumentParser(description="E2E Contracts Flow Test")
    parser.add_argument("--email", required=True, help="Login email")
    parser.add_argument("--password", required=True, help="Login password")
    args = parser.parse_args()
    ok = await ContractsTester().run(args.email, args.password)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
