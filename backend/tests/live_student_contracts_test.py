#!/usr/bin/env python3
"""
Student Contracts CRUD API 測試腳本

測試學生合約管理功能，包含：
1. 列出合約 (List)
2. 建立合約 (Create) - 需要 employee/admin 權限
3. 取得單一合約 (Read)
4. 更新合約 (Update) - 需要 employee/admin 權限
5. 刪除合約 (Delete) - 需要 employee/admin 權限
6. 取得下拉選單選項 (Options)
7. 合約明細 CRUD (Details)
8. 可預約教師管理 (Teachers)
9. 請假紀錄 CRUD (Leave Records)
10. 刪除連帶清理驗證
11. 課程選項依學生篩選

使用方式:
    # 執行完整 CRUD 測試（需要 employee/admin 帳號）
    python tests/live_student_contracts_test.py --email employee@example.com --password testpass

    # 只測試列表和讀取（任何登入用戶）
    python tests/live_student_contracts_test.py --email student@example.com --password testpass --read-only

    # 保留測試建立的合約（不刪除）
    python tests/live_student_contracts_test.py --email employee@example.com --password testpass --no-cleanup

    # 自訂後端 URL
    python tests/live_student_contracts_test.py --email admin@example.com --password testpass --backend-url http://localhost:8001
"""

import httpx
import asyncio
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

# 設定
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8001")


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


@dataclass
class CreatedContract:
    id: str
    contract_no: str


class StudentContractsCRUDTester:
    def __init__(self, backend_url: str, no_cleanup: bool = False):
        self.backend_url = backend_url.rstrip("/")
        self.results: list[TestResult] = []
        self.cookies: dict = {}
        self.no_cleanup = no_cleanup
        self.created_contracts: list[CreatedContract] = []
        self.user_role: str = ""
        self.student_id: Optional[str] = None
        self.course_id: Optional[str] = None
        self.teacher_id: Optional[str] = None

    def _record_result(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        """記錄測試結果"""
        self.results.append(TestResult(name, passed, message, duration_ms))
        status = "\u2705" if passed else "\u274c"
        duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        print(f"  {status} {name}{duration_str}")
        if message and not passed:
            print(f"     \u2514\u2500 {message}")

    async def login(self, email: str, password: str) -> bool:
        """登入並取得 session"""
        print("\n" + "=" * 60)
        print("\U0001f510 登入")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/auth/login",
                json={"email": email, "password": password}
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self.cookies = dict(resp.cookies)
                data = resp.json()
                self.user_role = data.get("user", {}).get("role", "student")
                self._record_result(
                    f"登入成功 (角色: {self.user_role})",
                    True,
                    duration_ms=duration
                )
                return True
            else:
                self._record_result(
                    "登入",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

    async def fetch_options(self) -> bool:
        """取得學生、課程和教師選項"""
        print("\n" + "=" * 60)
        print("\U0001f4cb 取得下拉選單選項")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 取得學生選項
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/options/students",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                students = data.get("data", [])
                if students:
                    self.student_id = students[0].get("id")
                    self._record_result(
                        f"取得學生選項 (共 {len(students)} 筆)",
                        True,
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "取得學生選項",
                        False,
                        "沒有可用的學生資料",
                        duration_ms=duration
                    )
                    return False
            else:
                self._record_result(
                    "取得學生選項",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )
                return False

            # 取得課程選項
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/options/courses",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                courses = data.get("data", [])
                if courses:
                    self.course_id = courses[0].get("id")
                    self._record_result(
                        f"取得課程選項 (共 {len(courses)} 筆)",
                        True,
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "取得課程選項",
                        False,
                        "沒有可用的課程資料",
                        duration_ms=duration
                    )
                    return False
            else:
                self._record_result(
                    "取得課程選項",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )
                return False

            # 取得教師選項
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/options/teachers",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                teachers = data.get("data", [])
                if teachers:
                    self.teacher_id = teachers[0].get("id")
                    self._record_result(
                        f"取得教師選項 (共 {len(teachers)} 筆)",
                        True,
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "取得教師選項",
                        True,
                        "沒有可用的教師資料（教師相關測試將跳過）",
                        duration_ms=duration
                    )
            else:
                self._record_result(
                    "取得教師選項",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

        return True

    async def test_list_contracts(self) -> bool:
        """測試列出合約"""
        print("\n" + "=" * 60)
        print("\U0001f4cb 測試列出學生合約 (List)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 測試基本列表
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                total = data.get("total", 0)
                self._record_result(
                    f"列出合約 (共 {total} 筆)",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "列出合約",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )
                return False

            # 測試分頁
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts",
                params={"page": 1, "per_page": 5},
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result(
                    "分頁查詢 (page=1, per_page=5)",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "分頁查詢",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

            # 測試篩選狀態
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts",
                params={"contract_status": "active"},
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result(
                    "篩選合約狀態 (contract_status=active)",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "篩選合約狀態",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

            # 測試搜尋
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts",
                params={"search": "SC"},
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result(
                    "搜尋合約 (search='SC')",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "搜尋合約",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

        return True

    async def test_create_contract(self) -> Optional[str]:
        """測試建立合約"""
        print("\n" + "=" * 60)
        print("\u2795 測試建立學生合約 (Create)")
        print("=" * 60 + "\n")

        if not self.student_id:
            self._record_result(
                "建立合約",
                False,
                "缺少學生 ID，請先執行 fetch_options"
            )
            return None

        today = datetime.now().date()
        end_date = today + timedelta(days=365)

        contract_data = {
            "student_id": self.student_id,
            "contract_status": "pending",
            "start_date": today.isoformat(),
            "end_date": end_date.isoformat(),
            "total_lessons": 24,
            "remaining_lessons": 24,
            "notes": "自動化測試建立的合約"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-contracts",
                json=contract_data,
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                contract = data.get("data", {})
                contract_id = contract.get("id")
                contract_no = contract.get("contract_no")

                self.created_contracts.append(CreatedContract(
                    id=contract_id,
                    contract_no=contract_no
                ))

                self._record_result(
                    f"建立合約成功 (編號: {contract_no})",
                    True,
                    duration_ms=duration
                )
                print(f"     \u2514\u2500 合約編號: {contract_no}")
                print(f"     \u2514\u2500 學生: {contract.get('student_name')}")
                print(f"     \u2514\u2500 總堂數: {contract.get('total_lessons')}")
                print(f"     \u2514\u2500 可請假次數: {contract.get('total_leave_allowed')}")

                # 驗證回應中包含 details, teachers, leave_records 陣列
                has_details = isinstance(contract.get("details"), list)
                has_teachers = isinstance(contract.get("teachers"), list)
                has_leave_records = isinstance(contract.get("leave_records"), list)
                self._record_result(
                    "回應包含 details[], teachers[], leave_records[]",
                    has_details and has_teachers and has_leave_records
                )

                # 驗證 total_leave_allowed 自動計算
                expected_leave = 24 * 2  # total_lessons * 2
                actual_leave = contract.get("total_leave_allowed", 0)
                self._record_result(
                    f"total_leave_allowed 自動計算 (期望: {expected_leave}, 實際: {actual_leave})",
                    actual_leave == expected_leave
                )

                # 驗證 used_leave_count 為 0
                self._record_result(
                    "used_leave_count 初始為 0",
                    contract.get("used_leave_count", -1) == 0
                )

                return contract_id
            elif resp.status_code == 401:
                self._record_result(
                    "建立合約",
                    False,
                    "未授權 (請確認已登入)",
                    duration_ms=duration
                )
                return None
            elif resp.status_code == 403:
                self._record_result(
                    "建立合約",
                    False,
                    "權限不足 (需要 employee/admin 角色)",
                    duration_ms=duration
                )
                return None
            else:
                self._record_result(
                    "建立合約",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return None

    async def test_get_contract(self, contract_id: str) -> bool:
        """測試取得單一合約"""
        print("\n" + "=" * 60)
        print("\U0001f50d 測試取得單一合約 (Read)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 測試取得存在的合約
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                contract = data.get("data", {})
                self._record_result(
                    f"取得合約 ({contract.get('contract_no', 'N/A')})",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "取得合約",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )
                return False

            # 測試取得不存在的合約
            fake_id = "00000000-0000-0000-0000-000000000000"
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{fake_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 404:
                self._record_result(
                    "不存在的合約返回 404",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "不存在的合約檢查",
                    False,
                    f"預期 404，實際 {resp.status_code}",
                    duration_ms=duration
                )

        return True

    async def test_update_contract(self, contract_id: str) -> bool:
        """測試更新合約"""
        print("\n" + "=" * 60)
        print("\u270f\ufe0f  測試更新合約 (Update)")
        print("=" * 60 + "\n")

        update_data = {
            "contract_status": "active",
            "remaining_lessons": 20,
            "notes": f"已更新於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.put(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                json=update_data,
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                contract = data.get("data", {})
                self._record_result(
                    "更新合約成功",
                    True,
                    duration_ms=duration
                )
                print(f"     \u2514\u2500 新狀態: {contract.get('contract_status')}")
                print(f"     \u2514\u2500 剩餘堂數: {contract.get('remaining_lessons')}")

                # 驗證更新結果
                if contract.get("contract_status") == "active" and contract.get("remaining_lessons") == 20:
                    self._record_result("更新資料驗證", True)
                else:
                    self._record_result("更新資料驗證", False, "更新後的資料與預期不符")

                return True
            elif resp.status_code == 403:
                self._record_result(
                    "更新合約",
                    False,
                    "權限不足 (需要 employee/admin 角色)",
                    duration_ms=duration
                )
                return False
            else:
                self._record_result(
                    "更新合約",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

    async def test_update_nonexistent_contract(self) -> bool:
        """測試更新不存在的合約"""
        print("\n" + "=" * 60)
        print("\U0001f504 測試更新不存在的合約")
        print("=" * 60 + "\n")

        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"notes": "Should Fail"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.put(
                f"{self.backend_url}/api/v1/student-contracts/{fake_id}",
                json=update_data,
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 404:
                self._record_result(
                    "不存在的合約返回 404",
                    True,
                    duration_ms=duration
                )
                return True
            else:
                self._record_result(
                    "不存在的合約檢查",
                    False,
                    f"預期 404，實際 {resp.status_code}",
                    duration_ms=duration
                )
                return False

    async def test_contract_details(self, contract_id: str) -> bool:
        """測試合約明細 CRUD"""
        print("\n" + "=" * 60)
        print("\U0001f4dd 測試合約明細 (Details CRUD)")
        print("=" * 60 + "\n")

        if not self.course_id or not self.student_id:
            self._record_result("合約明細測試", False, "缺少課程或學生 ID")
            return False

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 先確保學生有選修課程（新增 student_course）
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-courses",
                json={
                    "student_id": self.student_id,
                    "course_id": self.course_id
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000
            enrollment_id = None
            if resp.status_code == 200:
                enrollment_id = resp.json().get("data", {}).get("id")
                self._record_result("新增學生選課（供明細測試用）", True, duration_ms=duration)
            elif resp.status_code == 400 and "已選修" in resp.text:
                self._record_result("學生已選修此課程（跳過新增）", True, duration_ms=duration)
            else:
                self._record_result(
                    "新增學生選課",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )

            # 1. 新增 lesson_price 明細
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/details",
                json={
                    "detail_type": "lesson_price",
                    "course_id": self.course_id,
                    "description": "測試課程單價",
                    "amount": 500.0,
                    "notes": "自動化測試"
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            detail_id = None
            if resp.status_code == 200:
                data = resp.json()
                detail = data.get("data", {})
                detail_id = detail.get("id")
                self._record_result(
                    f"新增 lesson_price 明細成功 (ID: {detail_id[:8]}...)",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "新增 lesson_price 明細",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

            # 2. 新增 discount 明細
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/details",
                json={
                    "detail_type": "discount",
                    "description": "測試優惠折扣",
                    "amount": -100.0,
                    "notes": "早鳥優惠"
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            discount_id = None
            if resp.status_code == 200:
                data = resp.json()
                discount_id = data.get("data", {}).get("id")
                self._record_result(
                    "新增 discount 明細成功",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "新增 discount 明細",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )

            # 3. 列出明細
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/details",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                details = data.get("data", [])
                self._record_result(
                    f"列出明細 (共 {len(details)} 筆)",
                    len(details) >= 2,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "列出明細",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

            # 4. 更新明細
            if detail_id:
                start = datetime.now()
                resp = await client.put(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/details/{detail_id}",
                    json={
                        "amount": 600.0,
                        "description": "更新後的課程單價"
                    },
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    updated = data.get("data", {})
                    self._record_result(
                        "更新明細成功",
                        updated.get("amount") == 600.0,
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "更新明細",
                        False,
                        f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                        duration_ms=duration
                    )

            # 5. 刪除 discount 明細
            if discount_id:
                start = datetime.now()
                resp = await client.delete(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/details/{discount_id}",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    self._record_result(
                        "刪除明細成功",
                        True,
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "刪除明細",
                        False,
                        f"狀態碼: {resp.status_code}",
                        duration_ms=duration
                    )

                # 驗證刪除後列表只剩 1 筆
                start = datetime.now()
                resp = await client.get(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/details",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    remaining = len(data.get("data", []))
                    self._record_result(
                        f"刪除後剩餘明細數量 ({remaining} 筆)",
                        remaining == 1,
                        duration_ms=duration
                    )

            # 清理：刪除測試用的學生選課
            if enrollment_id:
                await client.delete(
                    f"{self.backend_url}/api/v1/student-courses/{enrollment_id}",
                    cookies=self.cookies
                )

        return True

    async def test_contract_teachers(self, contract_id: str) -> bool:
        """測試可預約教師管理"""
        print("\n" + "=" * 60)
        print("\U0001f468\u200d\U0001f3eb 測試可預約教師管理 (Teachers)")
        print("=" * 60 + "\n")

        if not self.teacher_id:
            self._record_result("教師管理測試", True, "無可用教師，跳過")
            return True

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. 新增可預約教師
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/teachers",
                json={
                    "teacher_id": self.teacher_id,
                    "is_primary": True
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            binding_id = None
            if resp.status_code == 200:
                data = resp.json()
                binding = data.get("data", {})
                binding_id = binding.get("id")
                self._record_result(
                    f"新增可預約教師成功 ({binding.get('teacher_name', 'N/A')})",
                    True,
                    duration_ms=duration
                )
                print(f"     \u2514\u2500 教師: {binding.get('teacher_no')} - {binding.get('teacher_name')}")
                print(f"     \u2514\u2500 主要教師: {binding.get('is_primary')}")
            else:
                self._record_result(
                    "新增可預約教師",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

            # 2. 測試重複新增（應該失敗）
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/teachers",
                json={
                    "teacher_id": self.teacher_id,
                    "is_primary": False
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 400:
                self._record_result(
                    "重複新增教師返回 400",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "重複新增教師檢查",
                    False,
                    f"預期 400，實際 {resp.status_code}",
                    duration_ms=duration
                )

            # 3. 列出可預約教師
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/teachers",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                teachers = data.get("data", [])
                self._record_result(
                    f"列出可預約教師 (共 {len(teachers)} 位)",
                    len(teachers) >= 1,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "列出可預約教師",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

            # 4. 移除可預約教師
            if binding_id:
                start = datetime.now()
                resp = await client.delete(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/teachers/{binding_id}",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    self._record_result(
                        "移除可預約教師成功",
                        True,
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "移除可預約教師",
                        False,
                        f"狀態碼: {resp.status_code}",
                        duration_ms=duration
                    )

                # 驗證移除後列表為空
                start = datetime.now()
                resp = await client.get(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/teachers",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    remaining = len(data.get("data", []))
                    self._record_result(
                        f"移除後剩餘教師數量 ({remaining} 位)",
                        remaining == 0,
                        duration_ms=duration
                    )

        return True

    async def test_leave_records(self, contract_id: str) -> bool:
        """測試請假紀錄 CRUD"""
        print("\n" + "=" * 60)
        print("\U0001f4c5 測試請假紀錄 (Leave Records CRUD)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. 新增請假紀錄
            today = datetime.now().date()
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/leave-records",
                json={
                    "leave_date": today.isoformat(),
                    "reason": "自動化測試請假"
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            leave_record_id = None
            if resp.status_code == 200:
                data = resp.json()
                record = data.get("data", {})
                leave_record_id = record.get("id")
                self._record_result(
                    f"新增請假紀錄成功 (ID: {leave_record_id[:8]}...)",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "新增請假紀錄",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

            # 2. 驗證 used_leave_count 增加
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                contract = resp.json().get("data", {})
                used_count = contract.get("used_leave_count", 0)
                self._record_result(
                    f"used_leave_count 增加為 {used_count}",
                    used_count == 1,
                    duration_ms=duration
                )
            else:
                self._record_result("驗證 used_leave_count", False, f"狀態碼: {resp.status_code}")

            # 3. 新增第二筆請假紀錄
            tomorrow = today + timedelta(days=1)
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/leave-records",
                json={
                    "leave_date": tomorrow.isoformat(),
                    "reason": "第二次請假"
                },
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            leave_record_id_2 = None
            if resp.status_code == 200:
                leave_record_id_2 = resp.json().get("data", {}).get("id")
                self._record_result("新增第二筆請假紀錄", True, duration_ms=duration)
            else:
                self._record_result("新增第二筆請假紀錄", False, f"狀態碼: {resp.status_code}")

            # 4. 列出請假紀錄
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/leave-records",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                records = data.get("data", [])
                self._record_result(
                    f"列出請假紀錄 (共 {len(records)} 筆)",
                    len(records) == 2,
                    duration_ms=duration
                )
            else:
                self._record_result("列出請假紀錄", False, f"狀態碼: {resp.status_code}")

            # 5. 刪除第一筆請假紀錄
            if leave_record_id:
                start = datetime.now()
                resp = await client.delete(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/leave-records/{leave_record_id}",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    self._record_result("刪除請假紀錄成功", True, duration_ms=duration)
                else:
                    self._record_result("刪除請假紀錄", False, f"狀態碼: {resp.status_code}")

            # 6. 驗證 used_leave_count 減少
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                contract = resp.json().get("data", {})
                used_count = contract.get("used_leave_count", 0)
                self._record_result(
                    f"刪除後 used_leave_count 減少為 {used_count}",
                    used_count == 1,
                    duration_ms=duration
                )

            # 7. 刪除第二筆
            if leave_record_id_2:
                await client.delete(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/leave-records/{leave_record_id_2}",
                    cookies=self.cookies
                )

        return True

    async def test_course_option_filtered_by_student(self) -> bool:
        """測試課程選項依學生篩選"""
        print("\n" + "=" * 60)
        print("\U0001f4da 測試課程選項依學生篩選")
        print("=" * 60 + "\n")

        if not self.student_id:
            self._record_result("課程選項篩選", False, "缺少學生 ID")
            return False

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 不帶 student_id → 回傳全部課程
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/options/courses",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            all_courses_count = 0
            if resp.status_code == 200:
                all_courses = resp.json().get("data", [])
                all_courses_count = len(all_courses)
                self._record_result(
                    f"無 student_id 回傳全部課程 ({all_courses_count} 筆)",
                    all_courses_count > 0,
                    duration_ms=duration
                )
            else:
                self._record_result("取得全部課程", False, f"狀態碼: {resp.status_code}")

            # 帶 student_id → 只回傳該學生已選的課程
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/options/courses",
                params={"student_id": self.student_id},
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                filtered_courses = resp.json().get("data", [])
                self._record_result(
                    f"帶 student_id 回傳篩選課程 ({len(filtered_courses)} 筆)",
                    True,
                    duration_ms=duration
                )
                # 篩選結果應 <= 全部課程
                self._record_result(
                    "篩選結果 <= 全部課程",
                    len(filtered_courses) <= all_courses_count
                )
            else:
                self._record_result("篩選課程選項", False, f"狀態碼: {resp.status_code}")

        return True

    async def test_delete_cascade(self, contract_id: str) -> bool:
        """測試刪除合約連帶清理 details + teachers + leave_records"""
        print("\n" + "=" * 60)
        print("\U0001f5d1\ufe0f  測試刪除連帶清理 (Delete Cascade)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 先新增一筆明細和一位教師（如果有可用教師）
            await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/details",
                json={
                    "detail_type": "compensation",
                    "description": "測試補償堂數",
                    "amount": 200.0,
                },
                cookies=self.cookies
            )

            if self.teacher_id:
                await client.post(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}/teachers",
                    json={
                        "teacher_id": self.teacher_id,
                        "is_primary": False
                    },
                    cookies=self.cookies
                )

            # 新增請假紀錄
            await client.post(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}/leave-records",
                json={
                    "leave_date": datetime.now().date().isoformat(),
                    "reason": "測試連帶刪除"
                },
                cookies=self.cookies
            )

            # 刪除合約
            start = datetime.now()
            resp = await client.delete(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result(
                    "刪除合約成功",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "刪除合約",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

            # 驗證合約已被刪除（應該返回 404）
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 404:
                self._record_result(
                    "刪除後合約不可存取",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "刪除後合約檢查",
                    False,
                    f"預期 404，實際 {resp.status_code}",
                    duration_ms=duration
                )

        return True

    async def test_delete_contract(self, contract_id: str) -> bool:
        """測試刪除合約"""
        print("\n" + "=" * 60)
        print("\U0001f5d1\ufe0f  測試刪除合約 (Delete)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.delete(
                f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result(
                    "刪除合約成功",
                    True,
                    duration_ms=duration
                )

                # 驗證合約已被刪除（應該返回 404）
                start = datetime.now()
                resp = await client.get(
                    f"{self.backend_url}/api/v1/student-contracts/{contract_id}",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 404:
                    self._record_result(
                        "刪除後合約不可存取",
                        True,
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "刪除後合約檢查",
                        False,
                        f"預期 404，實際 {resp.status_code}",
                        duration_ms=duration
                    )

                return True
            elif resp.status_code == 403:
                self._record_result(
                    "刪除合約",
                    False,
                    "權限不足 (需要 employee/admin 角色)",
                    duration_ms=duration
                )
                return False
            else:
                self._record_result(
                    "刪除合約",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )
                return False

    async def cleanup(self):
        """清理測試建立的合約"""
        if self.no_cleanup:
            print("\n" + "=" * 60)
            print("\U0001f4dd 已建立的合約（保留不刪除）")
            print("=" * 60 + "\n")
            for contract in self.created_contracts:
                print(f"  ID: {contract.id}")
                print(f"  合約編號: {contract.contract_no}")
                print()
            return

        if not self.created_contracts:
            return

        print("\n" + "=" * 60)
        print("\U0001f9f9 清理測試資料")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for contract in self.created_contracts:
                resp = await client.delete(
                    f"{self.backend_url}/api/v1/student-contracts/{contract.id}",
                    cookies=self.cookies
                )
                if resp.status_code == 200:
                    print(f"  \u2705 已刪除: {contract.contract_no}")
                elif resp.status_code == 404:
                    print(f"  \u23ed\ufe0f  已刪除 (測試中刪除): {contract.contract_no}")
                else:
                    print(f"  \u274c 刪除失敗: {contract.contract_no}")

    def print_summary(self):
        """列印測試摘要"""
        print("\n" + "=" * 60)
        print("\U0001f4ca 測試摘要")
        print("=" * 60 + "\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"  總計: {total} 項測試")
        print(f"  通過: {passed} \u2705")
        print(f"  失敗: {failed} \u274c")
        print(f"  成功率: {passed/total*100:.1f}%" if total > 0 else "  成功率: N/A")
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
        description="Student Contracts CRUD API 測試腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 完整 CRUD 測試（需要 employee/admin 帳號）
  python tests/live_student_contracts_test.py --email employee@example.com --password testpass

  # 只測試列表和讀取
  python tests/live_student_contracts_test.py --email student@example.com --password testpass --read-only

  # 保留測試建立的合約
  python tests/live_student_contracts_test.py --email employee@example.com --password testpass --no-cleanup
        """
    )

    parser.add_argument("--email", required=True, help="登入 Email")
    parser.add_argument("--password", required=True, help="登入密碼")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"後端 URL (預設: {BACKEND_URL})")
    parser.add_argument("--read-only", action="store_true", help="只測試讀取功能（不需要 staff 權限）")
    parser.add_argument("--no-cleanup", action="store_true", help="保留測試建立的合約")

    args = parser.parse_args()

    tester = StudentContractsCRUDTester(args.backend_url, no_cleanup=args.no_cleanup)

    print("\n" + "\U0001f680" * 20)
    print("\n   Student Contracts CRUD API 測試")
    print(f"   後端: {args.backend_url}")
    print(f"   模式: {'唯讀' if args.read_only else '完整 CRUD'}")
    print("\n" + "\U0001f680" * 20)

    try:
        # 1. 登入
        if not await tester.login(args.email, args.password):
            tester.print_summary()
            sys.exit(1)

        # 2. 取得選項
        if not await tester.fetch_options():
            print("\n\u26a0\ufe0f  無法取得學生或課程選項，請確認資料庫有資料")
            tester.print_summary()
            sys.exit(1)

        # 3. 測試列出合約
        await tester.test_list_contracts()

        if args.read_only:
            # 唯讀模式：只測試列表
            tester.print_summary()
            sys.exit(0 if all(r.passed for r in tester.results) else 1)

        # 檢查是否有權限進行 CRUD
        if tester.user_role not in ["admin", "employee"]:
            print("\n\u26a0\ufe0f  目前角色為 '{}'，無法執行建立/更新/刪除測試".format(tester.user_role))
            print("   請使用 --read-only 模式或改用 employee/admin 帳號")
            tester.print_summary()
            sys.exit(1)

        # 4. 測試建立合約
        contract_id = await tester.test_create_contract()

        if contract_id:
            # 5. 測試取得合約
            await tester.test_get_contract(contract_id)

            # 6. 測試更新合約
            await tester.test_update_contract(contract_id)

            # 7. 測試更新不存在的合約
            await tester.test_update_nonexistent_contract()

            # 8. 測試合約明細 CRUD
            await tester.test_contract_details(contract_id)

            # 9. 測試可預約教師管理
            await tester.test_contract_teachers(contract_id)

            # 10. 測試請假紀錄 CRUD
            await tester.test_leave_records(contract_id)

            # 11. 測試課程選項依學生篩選
            await tester.test_course_option_filtered_by_student()

            # 12. 建立第二份合約用於測試刪除連帶清理
            contract_id_2 = await tester.test_create_contract()
            if contract_id_2:
                await tester.test_delete_cascade(contract_id_2)
                # 從 created_contracts 移除已刪除的合約
                tester.created_contracts = [c for c in tester.created_contracts if c.id != contract_id_2]

            # 13. 刪除第一份合約
            if not args.no_cleanup:
                await tester.test_delete_contract(contract_id)
                # 從 created_contracts 移除已刪除的合約
                tester.created_contracts = [c for c in tester.created_contracts if c.id != contract_id]

        # 清理
        await tester.cleanup()

        # 列印摘要
        success = tester.print_summary()
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n\n\u26a0\ufe0f  測試中斷")
        await tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n\u274c 測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        await tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
