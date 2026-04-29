#!/usr/bin/env python3
"""
End-to-End Student Management Flow Test

完整學生管理流程：
  建立學生 → 建立合約 → 學生選課 → 設定教師偏好
  → 學生總覽 API 驗證 → 學生詳情 API 驗證 → 合約堂數驗證
  → 全部清理

使用方式:
    python tests/live_e2e_student_flow_test.py \
        --email employee@eop-test.com --password TestPassword123!
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, date, timedelta

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")
_TS = datetime.now().strftime("%H%M%S")
TEST_PREFIX = f"E2ESTD{_TS}_"


class StudentFlowTester:
    def __init__(self):
        self.url = BACKEND_URL.rstrip("/")
        self.results = []
        self.client = None
        # 資源 ID
        self.course_id = None
        self.teacher_id = None
        self.student_id = None
        self.student_contract_id = None
        self.student_course_id = None
        self.preference_id = None

    async def _post(self, path, json):
        return await self.client.post(f"{self.url}{path}", json=json)

    async def _get(self, path, params=None):
        return await self.client.get(f"{self.url}{path}", params=params)

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
            print(f"  E2E Student Management Flow Test")
            print(f"{'=' * 60}\n")

            # Login
            resp = await self._post("/api/v1/auth/login", {"email": email, "password": password})
            if resp.status_code != 200:
                print("  ✗ Login failed"); return False
            print("  ✓ Login")

            # 先建立一個教師（教師偏好需要）
            resp = await self._post("/api/v1/teachers", {
                "teacher_no": f"{TEST_PREFIX}T01", "name": f"{TEST_PREFIX}教師",
                "email": f"{TEST_PREFIX}t@example.com", "teacher_level": 1,
            })
            if resp.status_code == 200:
                self.teacher_id = resp.json()["data"]["id"]

            # 建立課程
            resp = await self._post("/api/v1/courses", {
                "course_code": f"{TEST_PREFIX}C01", "course_name": f"{TEST_PREFIX}英文課",
                "duration_minutes": 60,
            })
            if resp.status_code == 200:
                self.course_id = resp.json()["data"]["id"]

            print("\n  Phase 1: 學生 CRUD")
            print("  " + "-" * 40)

            # 建立學生
            await self._test("建立正式學生", self._create_student)
            await self._test("查詢學生列表（搜尋）", self._search_student)
            await self._test("取得學生詳情", self._get_student_detail)

            print("\n  Phase 2: 合約與選課")
            print("  " + "-" * 40)

            await self._test("建立學生合約（48堂）", self._create_contract)
            await self._test("學生選課", self._create_enrollment)
            await self._test("設定教師偏好", self._create_preference)
            await self._test("驗證合約剩餘堂數 = 48", self._verify_contract_lessons)

            print("\n  Phase 3: 總覽 API 驗證")
            print("  " + "-" * 40)

            await self._test("學生總覽 — 能找到測試學生", self._verify_student_overview)
            await self._test("學生總覽 — 篩選正式學生", self._verify_overview_filter)
            await self._test("學生詳情 — 合約/選課/偏好區段", self._verify_student_detail_view)

            print("\n  Phase 4: 編輯與停用")
            print("  " + "-" * 40)

            await self._test("編輯學生資料（加英文名）", self._update_student)
            await self._test("驗證修改結果", self._verify_student_update)
            await self._test("停用學生", self._deactivate_student)
            await self._test("總覽篩選已停用 — 能找到", self._verify_deactivated_filter)
            await self._test("刪除學生", self._delete_student)
            await self._test("驗證刪除（應回 404）", self._verify_student_deleted)

            # Cleanup (student already deleted)
            print("\n  Cleanup")
            print("  " + "-" * 40)
            await self._cleanup()

            # Summary
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

    async def _create_student(self):
        resp = await self._post("/api/v1/students", {
            "student_no": f"{TEST_PREFIX}S01", "name": f"{TEST_PREFIX}王小明",
            "eng_name": "Wang Xiaoming",
            "email": f"{TEST_PREFIX}s@example.com",
            "phone": "0900000000",
            "student_type": "formal",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_id = resp.json()["data"]["id"]
        return True

    async def _search_student(self):
        resp = await self._get("/api/v1/students", {"search": TEST_PREFIX, "per_page": 5})
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not data: return "搜尋不到測試學生"
        if not any(d["id"] == self.student_id for d in data): return "搜尋結果不含測試學生"
        return True

    async def _get_student_detail(self):
        resp = await self._get(f"/api/v1/students/{self.student_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        d = resp.json()["data"]
        if d.get("name") != f"{TEST_PREFIX}王小明": return f"name mismatch: {d.get('name')}"
        return True

    async def _create_contract(self):
        start = date.today().isoformat()
        end = (date.today() + timedelta(days=180)).isoformat()
        resp = await self._post("/api/v1/student-contracts", {
            "student_id": self.student_id, "contract_status": "active",
            "start_date": start, "end_date": end,
            "total_lessons": 48, "remaining_lessons": 48, "total_amount": 96000,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_contract_id = resp.json()["data"]["id"]
        return True

    async def _create_enrollment(self):
        resp = await self._post("/api/v1/student-courses", {
            "student_id": self.student_id, "course_id": self.course_id,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.student_course_id = resp.json()["data"]["id"]
        return True

    async def _create_preference(self):
        resp = await self._post("/api/v1/student-teacher-preferences/", {
            "student_id": self.student_id, "primary_teacher_ids": [self.teacher_id],
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        self.preference_id = resp.json()["data"]["id"]
        return True

    async def _verify_contract_lessons(self):
        resp = await self._get(f"/api/v1/student-contracts/{self.student_contract_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        remaining = resp.json()["data"].get("remaining_lessons")
        if remaining != 48: return f"remaining={remaining}, expected 48"
        return True

    async def _verify_student_overview(self):
        resp = await self._get("/api/v1/students/overview/list", {"search": TEST_PREFIX})
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not any(d.get("student_id") == self.student_id or d.get("id") == self.student_id for d in data):
            return "總覽找不到測試學生"
        return True

    async def _verify_overview_filter(self):
        resp = await self._get("/api/v1/students/overview/list", {"student_type": "formal"})
        if resp.status_code != 200: return f"{resp.status_code}"
        return True

    async def _verify_student_detail_view(self):
        resp = await self._get(f"/api/v1/students/{self.student_id}/view")
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", {})
        # 驗證基本區段存在
        checks = []
        if "contracts" not in data and "student_contracts" not in data:
            checks.append("missing contracts section")
        if "courses" not in data and "student_courses" not in data:
            checks.append("missing courses section")
        return True if not checks else "; ".join(checks)

    async def _update_student(self):
        resp = await self.client.put(f"{self.url}/api/v1/students/{self.student_id}", json={
            "eng_name": "Xiao Ming Wang",
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _verify_student_update(self):
        resp = await self._get(f"/api/v1/students/{self.student_id}")
        if resp.status_code != 200: return f"{resp.status_code}"
        if resp.json()["data"].get("eng_name") != "Xiao Ming Wang": return "eng_name not updated"
        return True

    async def _deactivate_student(self):
        resp = await self.client.put(f"{self.url}/api/v1/students/{self.student_id}", json={
            "is_active": False,
        })
        if resp.status_code != 200: return f"{resp.status_code} {resp.text[:200]}"
        return True

    async def _verify_deactivated_filter(self):
        resp = await self._get("/api/v1/students", {"is_active": "false"})
        if resp.status_code != 200: return f"{resp.status_code}"
        data = resp.json().get("data", [])
        if not any(d["id"] == self.student_id for d in data):
            return "停用篩選找不到測試學生"
        return True

    async def _delete_student(self):
        resp = await self._delete(f"/api/v1/students/{self.student_id}")
        if resp.status_code not in (200, 204): return f"{resp.status_code} {resp.text[:200]}"
        self._deleted_student_id = self.student_id
        self.student_id = None  # skip in cleanup
        return True

    async def _verify_student_deleted(self):
        resp = await self._get(f"/api/v1/students/{self._deleted_student_id}")
        if resp.status_code == 404: return True
        if resp.status_code == 200:
            if resp.json().get("data", {}).get("is_deleted") is True: return True
            return f"GET 200 but is_deleted={resp.json().get('data', {}).get('is_deleted')}"
        return f"expected 404, got {resp.status_code}"

    async def _cleanup(self):
        for name, path in [
            ("preference", f"/api/v1/student-teacher-preferences/{self.preference_id}" if self.preference_id else None),
            ("enrollment", f"/api/v1/student-courses/{self.student_course_id}" if self.student_course_id else None),
            ("contract", f"/api/v1/student-contracts/{self.student_contract_id}" if self.student_contract_id else None),
            ("student", f"/api/v1/students/{self.student_id}" if self.student_id else None),
            ("teacher", f"/api/v1/teachers/{self.teacher_id}" if self.teacher_id else None),
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
    ok = await StudentFlowTester().run(args.email, args.password)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    asyncio.run(main())
