#!/usr/bin/env python3
"""
End-to-End Teacher Management Flow Test

完整教師管理流程：
  建立教師 → 建立合約 → 新增合約明細（課程費率）
  → 建立可用時段 → 教師總覽 API → 教師詳情 API
  → 編輯/停用 → 清理

使用方式:
    python tests/live_e2e_teacher_flow_test.py \
        --email employee@eop-test.com --password TestPassword123!
"""

import httpx
import asyncio
import argparse
import sys
import os
import struct
import zlib
from datetime import datetime, date, timedelta

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2ETCR{_TS}_"


def _make_1x1_png() -> bytes:
    """產生一個 1x1 紅色像素的合法 PNG 檔案"""
    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw_row = b"\x00\xff\x00\x00"  # filter=None, R=255 G=0 B=0
    idat = _chunk(b"IDAT", zlib.compress(raw_row))
    iend = _chunk(b"IEND", b"")
    return header + ihdr + idat + iend


class TeacherFlowTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None
        self.course_id = None
        self.teacher_id = None
        self.teacher_contract_id = None
        self.teacher_contract_detail_id = None
        self.teacher_slot_id = None
        self.slot_date = (date.today() + timedelta(days=14)).isoformat()
        self._upload_url = None
        self._avatar_storage_path = None

    async def _post(self, path, json):
        return await self.client.post(f"{self.url}{path}", json=json)

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

    async def _put(self, path, json):
        return await self.client.put(f"{self.url}{path}", json=json)

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

            print(f"\n{'=' * 60}")
            print(f"  E2E Teacher Management Flow Test")
            print(f"{'=' * 60}\n")

            resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
            if resp.status_code != 200:
                print("  ✗ Login failed"); return False
            print("  ✓ Login")

            # 前置：建立課程
            resp = await self._post("/api/v1/courses", {
                "course_code": f"{TEST_PREFIX}C01", "course_name": f"{TEST_PREFIX}數學課",
                "duration_minutes": 60,
            })
            if resp.status_code == 200:
                self.course_id = resp.json()["data"]["id"]

            print("\n  Phase 1: 教師 CRUD")
            print("  " + "-" * 40)

            await self._test("建立教師", self._create_teacher)
            await self._test("查詢教師列表", self._search_teacher)
            await self._test("取得教師詳情", self._get_teacher_detail)

            print("\n  Phase 2: 合約與明細")
            print("  " + "-" * 40)

            await self._test("建立時薪合約", self._create_contract)
            await self._test("新增課程費率明細", self._create_contract_detail)
            await self._test("驗證合約含明細", self._verify_contract_with_detail)

            print("\n  Phase 3: 可用時段")
            print("  " + "-" * 40)

            await self._test("建立時段：缺 teacher_contract_id → 422", self._create_slot_missing_contract)
            await self._test("建立時段：合約不屬於該老師 → 400", self._create_slot_cross_teacher_contract)
            await self._test("建立時段：合約非 active → 400", self._create_slot_inactive_contract)
            await self._test("建立教師時段 (09:00-12:00)", self._create_slot)
            await self._test("查詢時段列表", self._list_slots)
            await self._test("編輯時段（改為不可用）", self._update_slot_unavailable)
            await self._test("編輯時段（恢復可用）", self._update_slot_available)
            await self._test("更新時段：合約非 active → 400", self._update_slot_inactive_contract)

            print("\n  Phase 4: 總覽 API 驗證")
            print("  " + "-" * 40)

            await self._test("教師總覽 — 能找到測試教師", self._verify_teacher_overview)
            await self._test("教師詳情 — 合約/時段區段", self._verify_teacher_detail_view)

            print("\n  Phase 5: 頭像上傳")
            print("  " + "-" * 40)

            await self._test("取得頭像上傳 URL", self._get_avatar_upload_url)
            await self._test("上傳圖片到 S3", self._upload_avatar_to_s3)
            await self._test("確認頭像上傳", self._confirm_avatar_upload)
            await self._test("驗證頭像 URL 已設定", self._verify_avatar_set)

            print("\n  Phase 6: 編輯與停用")
            print("  " + "-" * 40)

            await self._test("編輯教師（改 bio）", self._update_teacher)
            await self._test("驗證修改結果", self._verify_teacher_update)
            await self._test("停用教師", self._deactivate_teacher)
            await self._test("刪除教師", self._delete_teacher)
            await self._test("驗證刪除（應回 404）", self._verify_teacher_deleted)

            # Cleanup (teacher already deleted)
            print("\n  Cleanup")
            print("  " + "-" * 40)
            await self._cleanup()

            passed = sum(1 for _, ok, _ in self.results if ok)
            failed = sum(1 for _, ok, _ in self.results if not ok)
            print(f"\n{'=' * 60}")
            print(f"  Results: {passed}/{len(self.results)} passed — {'ALL PASSED' if failed == 0 else f'{failed} FAILED'}")
            if failed:
                for name, ok, msg in self.results:
                    if not ok: print(f"    ✗ {name}: {msg}")
            print(f"{'=' * 60}\n")
            return failed == 0

    # ── Test implementations ──

    async def _create_teacher(self):
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T01", "name": f"{TEST_PREFIX}李老師",
            "email": f"{TEST_PREFIX}t@example.com", "teacher_level": 2,
            "bio": "E2E 測試教師",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.teacher_id = resp.json()["data"]["id"]
        return True

    async def _search_teacher(self):
        resp = await self._get("/api/v1/teachers", {"search": TEST_PREFIX})
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not any(d["id"] == self.teacher_id for d in data): return "搜尋找不到"
        return True

    async def _get_teacher_detail(self):
        resp = await self._get(f"/api/v1/teachers/{self.teacher_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        d = resp.json()["data"]
        if d.get("teacher_level") != 2: return f"level={d.get('teacher_level')}"
        return True

    async def _create_contract(self):
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": self.teacher_id, "contract_status": "active",
            "start_date": start, "end_date": end, "employment_type": "hourly",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.teacher_contract_id = resp.json()["data"]["id"]
        return True

    async def _create_contract_detail(self):
        resp = await self._post(f"/api/v1/teacher-contracts/{self.teacher_contract_id}/details", {
            "detail_type": "course_rate", "course_id": self.course_id,
            "description": "數學課時薪", "amount": 900,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.teacher_contract_detail_id = resp.json()["data"]["id"]
        return True

    async def _verify_contract_with_detail(self):
        resp = await self._get(f"/api/v1/teacher-contracts/{self.teacher_contract_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        d = resp.json()["data"]
        details = d.get("details", [])
        if not details: return "合約無明細"
        rate_detail = [x for x in details if x.get("detail_type") == "course_rate"]
        if not rate_detail: return "找不到 course_rate 明細"
        if rate_detail[0].get("amount") != 900: return f"amount={rate_detail[0].get('amount')}"
        return True

    async def _create_slot(self):
        resp = await self._post("/api/v1/teacher-slots", {
            "teacher_id": self.teacher_id,
            "teacher_contract_id": self.teacher_contract_id,
            "slot_date": self.slot_date, "start_time": "09:00", "end_time": "12:00",
            "is_available": True,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.teacher_slot_id = resp.json()["data"]["id"]
        return True

    async def _create_slot_missing_contract(self):
        """schema 必填：teacher_contract_id 缺漏 → 422"""
        resp = await self._post("/api/v1/teacher-slots", {
            "teacher_id": self.teacher_id,
            "slot_date": self.slot_date, "start_time": "13:00", "end_time": "14:00",
            "is_available": True,
        })
        if resp.status_code != 422: return f"expected 422, got {resp.status_code} {resp.text[:200]}"
        return True

    async def _create_slot_cross_teacher_contract(self):
        """合約屬於別的老師 → 400"""
        # 建第二個 teacher + active 合約
        resp = await self._post("/api/v1/teachers", {
            "teacher_no": f"{TEST_PREFIX}T02", "name": f"{TEST_PREFIX}陳老師",
            "email": f"{TEST_PREFIX}t2@example.com", "teacher_level": 1,
        })
        if resp.status_code != 200: return f"create teacher2: {resp.status_code} {resp.text[:200]}"
        other_teacher_id = resp.json()["data"]["id"]
        self._other_teacher_id = other_teacher_id  # for cleanup

        start = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": other_teacher_id, "contract_status": "active",
            "start_date": start, "end_date": end, "employment_type": "hourly",
        })
        if resp.status_code != 200: return f"create contract2: {resp.status_code} {resp.text[:200]}"
        other_contract_id = resp.json()["data"]["id"]
        self._other_contract_id = other_contract_id

        # 用 teacher1 + 別人的合約 → 應該 400
        resp = await self._post("/api/v1/teacher-slots", {
            "teacher_id": self.teacher_id,
            "teacher_contract_id": other_contract_id,
            "slot_date": self.slot_date, "start_time": "13:00", "end_time": "14:00",
            "is_available": True,
        })
        if resp.status_code != 400: return f"expected 400, got {resp.status_code} {resp.text[:200]}"
        return True

    async def _create_slot_inactive_contract(self):
        """合約 status != active → 400"""
        # 建一個 pending 合約
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=365)).isoformat()
        resp = await self._post("/api/v1/teacher-contracts", {
            "teacher_id": self.teacher_id, "contract_status": "pending",
            "start_date": start, "end_date": end, "employment_type": "hourly",
        })
        if resp.status_code != 200: return f"create pending contract: {resp.status_code} {resp.text[:200]}"
        pending_contract_id = resp.json()["data"]["id"]
        self._pending_contract_id = pending_contract_id

        resp = await self._post("/api/v1/teacher-slots", {
            "teacher_id": self.teacher_id,
            "teacher_contract_id": pending_contract_id,
            "slot_date": self.slot_date, "start_time": "13:00", "end_time": "14:00",
            "is_available": True,
        })
        if resp.status_code != 400: return f"expected 400, got {resp.status_code} {resp.text[:200]}"
        return True

    async def _update_slot_inactive_contract(self):
        """更新 slot 時若帶非 active 合約 → 400"""
        resp = await self._put(f"/api/v1/teacher-slots/{self.teacher_slot_id}", {
            "teacher_contract_id": self._pending_contract_id,
        })
        if resp.status_code != 400: return f"expected 400, got {resp.status_code} {resp.text[:200]}"
        return True

    async def _list_slots(self):
        resp = await self._get("/api/v1/teacher-slots", {
            "teacher_id": self.teacher_id, "per_page": 10,
        })
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not any(d["id"] == self.teacher_slot_id for d in data): return "列表找不到時段"
        return True

    async def _update_slot_unavailable(self):
        resp = await self._put(f"/api/v1/teacher-slots/{self.teacher_slot_id}", {
            "is_available": False,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _update_slot_available(self):
        resp = await self._put(f"/api/v1/teacher-slots/{self.teacher_slot_id}", {
            "is_available": True,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _verify_teacher_overview(self):
        resp = await self._get("/api/v1/teachers/overview/list", {"search": TEST_PREFIX})
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not any(d.get("teacher_id") == self.teacher_id or d.get("id") == self.teacher_id for d in data):
            return "總覽找不到"
        return True

    async def _verify_teacher_detail_view(self):
        resp = await self._get(f"/api/v1/teachers/{self.teacher_id}/view")
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", {})
        checks = []
        if "contracts" not in data and "teacher_contracts" not in data:
            checks.append("missing contracts")
        return True if not checks else "; ".join(checks)

    async def _get_avatar_upload_url(self):
        resp = await self._post(
            f"/api/v1/teachers/{self.teacher_id}/avatar/upload-url",
            json={"file_name": "test_avatar.png"},
        )
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        data = resp.json()
        self._upload_url = data.get("upload_url")
        self._avatar_storage_path = data.get("storage_path")
        if not self._upload_url: return "missing upload_url"
        if not self._avatar_storage_path: return "missing storage_path"
        return True

    async def _upload_avatar_to_s3(self):
        png_bytes = _make_1x1_png()
        async with httpx.AsyncClient(timeout=30.0) as raw_client:
            resp = await raw_client.put(
                self._upload_url,
                content=png_bytes,
                headers={"Content-Type": "image/png"},
            )
        if resp.status_code not in (200, 201): return f"S3 PUT {resp.status_code} {resp.text[:200]}"
        return True

    async def _confirm_avatar_upload(self):
        resp = await self._post(
            f"/api/v1/teachers/{self.teacher_id}/avatar/confirm-upload",
            json={"storage_path": self._avatar_storage_path, "file_name": "test_avatar.png"},
        )
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _verify_avatar_set(self):
        resp = await self._get(f"/api/v1/teachers/{self.teacher_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        avatar = resp.json()["data"].get("avatar_url")
        if not avatar: return "avatar_url is empty after upload"
        return True

    async def _update_teacher(self):
        resp = await self._put(f"/api/v1/teachers/{self.teacher_id}", {
            "bio": "E2E 測試教師 — updated",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _verify_teacher_update(self):
        resp = await self._get(f"/api/v1/teachers/{self.teacher_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        if resp.json()["data"].get("bio") != "E2E 測試教師 — updated": return "bio not updated"
        return True

    async def _deactivate_teacher(self):
        resp = await self._put(f"/api/v1/teachers/{self.teacher_id}", {"is_active": False})
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _delete_teacher(self):
        resp = await self._delete(f"/api/v1/teachers/{self.teacher_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self._deleted_teacher_id = self.teacher_id
        self.teacher_id = None  # skip in cleanup
        return True

    async def _verify_teacher_deleted(self):
        resp = await self._get(f"/api/v1/teachers/{self._deleted_teacher_id}")
        if resp.status_code == 404: return True
        if resp.status_code == 200:
            if resp.json().get("data", {}).get("is_deleted") is True: return True
            return f"GET 200 but is_deleted={resp.json().get('data', {}).get('is_deleted')}"
        return f"expected 404, got {resp.status_code}"

    async def _cleanup(self):
        # 額外建立的 teacher2 / 合約（cross-teacher / pending 測試用）
        other_teacher_id = getattr(self, "_other_teacher_id", None)
        other_contract_id = getattr(self, "_other_contract_id", None)
        pending_contract_id = getattr(self, "_pending_contract_id", None)

        for name, path in [
            ("slot", f"/api/v1/teacher-slots/{self.teacher_slot_id}" if self.teacher_slot_id else None),
            ("detail", f"/api/v1/teacher-contracts/{self.teacher_contract_id}/details/{self.teacher_contract_detail_id}" if self.teacher_contract_id and self.teacher_contract_detail_id else None),
            ("contract", f"/api/v1/teacher-contracts/{self.teacher_contract_id}" if self.teacher_contract_id else None),
            ("pending_contract", f"/api/v1/teacher-contracts/{pending_contract_id}" if pending_contract_id else None),
            ("other_contract", f"/api/v1/teacher-contracts/{other_contract_id}" if other_contract_id else None),
            ("teacher", f"/api/v1/teachers/{self.teacher_id}" if self.teacher_id else None),
            ("other_teacher", f"/api/v1/teachers/{other_teacher_id}" if other_teacher_id else None),
            ("course", f"/api/v1/courses/{self.course_id}" if self.course_id else None),
        ]:
            if not path: continue
            resp = await self._delete(path)
            s = "OK" if resp.status_code in (200, 204, 404) else f"WARN({resp.status_code})"
            print(f"    {name}: {s}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    ok = await TeacherFlowTester().run(args.email, args.password)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    asyncio.run(main())
