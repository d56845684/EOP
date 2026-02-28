#!/usr/bin/env python3
"""
Teacher Contracts CRUD API 測試腳本

測試教師合約管理功能，包含：
1. 列出合約 (List) + employment_type 篩選
2. 建立合約 (Create) - 需要 employee/admin 權限
3. 取得單一合約 (Read)
4. 更新合約 (Update) - 需要 employee/admin 權限
5. 刪除合約 (Delete) - 需要 employee/admin 權限
6. 取得下拉選單選項 (Teachers + Courses)
7. 合約明細 CRUD (Details)

使用方式:
    # 執行完整 CRUD 測試（需要 employee/admin 帳號）
    python tests/live_teacher_contracts_test.py --email employee@example.com --password testpass

    # 只測試列表和讀取（任何登入用戶）
    python tests/live_teacher_contracts_test.py --email student@example.com --password testpass --read-only

    # 保留測試建立的合約（不刪除）
    python tests/live_teacher_contracts_test.py --email employee@example.com --password testpass --no-cleanup

    # 自訂後端 URL
    python tests/live_teacher_contracts_test.py --email admin@example.com --password testpass --backend-url http://localhost:8001
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


class TeacherContractsCRUDTester:
    def __init__(self, backend_url: str, no_cleanup: bool = False):
        self.backend_url = backend_url.rstrip("/")
        self.results: list[TestResult] = []
        self.cookies: dict = {}
        self.no_cleanup = no_cleanup
        self.created_contracts: list[CreatedContract] = []
        self.user_role: str = ""
        self.teacher_id: Optional[str] = None
        self.course_id: Optional[str] = None

    def _record_result(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        """記錄測試結果"""
        self.results.append(TestResult(name, passed, message, duration_ms))
        status = "✅" if passed else "❌"
        duration_str = f" ({duration_ms:.0f}ms)" if duration_ms else ""
        print(f"  {status} {name}{duration_str}")
        if message and not passed:
            print(f"     └─ {message}")

    async def login(self, email: str, password: str) -> bool:
        """登入並取得 session"""
        print("\n" + "=" * 60)
        print("🔐 登入")
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
        """取得教師和課程選項"""
        print("\n" + "=" * 60)
        print("📋 取得下拉選單選項")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 取得教師選項
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/options/teachers",
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
                        False,
                        "沒有可用的教師資料",
                        duration_ms=duration
                    )
                    return False
            else:
                self._record_result(
                    "取得教師選項",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )
                return False

            # 取得課程選項
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/options/courses",
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
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

        return True

    async def test_list_contracts(self) -> bool:
        """測試列出合約"""
        print("\n" + "=" * 60)
        print("📋 測試列出教師合約 (List)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 測試基本列表
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts",
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
                f"{self.backend_url}/api/v1/teacher-contracts",
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
                f"{self.backend_url}/api/v1/teacher-contracts",
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

            # 測試篩選僱用類型
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts",
                params={"employment_type": "hourly"},
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result(
                    "篩選僱用類型 (employment_type=hourly)",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "篩選僱用類型",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

            # 測試搜尋
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts",
                params={"search": "TC"},
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                self._record_result(
                    "搜尋合約 (search='TC')",
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
        print("➕ 測試建立教師合約 (Create)")
        print("=" * 60 + "\n")

        if not self.teacher_id:
            self._record_result(
                "建立合約",
                False,
                "缺少教師 ID，請先執行 fetch_options"
            )
            return None

        today = datetime.now().date()
        end_date = today + timedelta(days=365)

        contract_data = {
            "teacher_id": self.teacher_id,
            "contract_status": "pending",
            "start_date": today.isoformat(),
            "end_date": end_date.isoformat(),
            "employment_type": "hourly",
            "trial_to_formal_bonus": 500.0,
            "notes": "自動化測試建立的合約"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/teacher-contracts",
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
                print(f"     └─ 合約編號: {contract_no}")
                print(f"     └─ 教師: {contract.get('teacher_name')}")
                print(f"     └─ 僱用類型: {contract.get('employment_type')}")
                print(f"     └─ 轉正獎金: {contract.get('trial_to_formal_bonus')}")
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
        print("🔍 測試取得單一合約 (Read)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 測試取得存在的合約
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}",
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

                # 驗證回應包含新欄位
                has_employment_type = "employment_type" in contract
                has_details = "details" in contract
                has_total_amount = "total_amount" in contract
                if has_employment_type and has_details and has_total_amount:
                    self._record_result("回應包含 employment_type, details, total_amount", True)
                else:
                    missing = []
                    if not has_employment_type:
                        missing.append("employment_type")
                    if not has_details:
                        missing.append("details")
                    if not has_total_amount:
                        missing.append("total_amount")
                    self._record_result(
                        "回應欄位檢查",
                        False,
                        f"缺少欄位: {', '.join(missing)}"
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
                f"{self.backend_url}/api/v1/teacher-contracts/{fake_id}",
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
        print("✏️  測試更新合約 (Update)")
        print("=" * 60 + "\n")

        update_data = {
            "contract_status": "active",
            "employment_type": "full_time",
            "trial_to_formal_bonus": 800.0,
            "notes": f"已更新於 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}",
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
                print(f"     └─ 新狀態: {contract.get('contract_status')}")
                print(f"     └─ 新僱用類型: {contract.get('employment_type')}")
                print(f"     └─ 新轉正獎金: {contract.get('trial_to_formal_bonus')}")

                # 驗證更新結果
                status_ok = contract.get("contract_status") == "active"
                type_ok = contract.get("employment_type") == "full_time"
                bonus_ok = contract.get("trial_to_formal_bonus") == 800.0
                if status_ok and type_ok and bonus_ok:
                    self._record_result("更新資料驗證", True)
                else:
                    failed_checks = []
                    if not status_ok:
                        failed_checks.append(f"contract_status={contract.get('contract_status')}")
                    if not type_ok:
                        failed_checks.append(f"employment_type={contract.get('employment_type')}")
                    if not bonus_ok:
                        failed_checks.append(f"trial_to_formal_bonus={contract.get('trial_to_formal_bonus')}")
                    self._record_result("更新資料驗證", False, f"不符: {', '.join(failed_checks)}")

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
        print("🔄 測試更新不存在的合約")
        print("=" * 60 + "\n")

        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"notes": "Should Fail"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.put(
                f"{self.backend_url}/api/v1/teacher-contracts/{fake_id}",
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
        print("📝 測試合約明細 CRUD (Details)")
        print("=" * 60 + "\n")

        detail_id: Optional[str] = None

        async with httpx.AsyncClient(timeout=30.0) as client:
            # --- 列出明細（應為空）---
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                details = data.get("data", [])
                self._record_result(
                    f"列出明細 (共 {len(details)} 筆)",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "列出明細",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )
                return False

            # --- 新增 course_rate 明細 ---
            if self.course_id:
                detail_data = {
                    "detail_type": "course_rate",
                    "course_id": self.course_id,
                    "description": "測試課程時薪",
                    "amount": 600.0,
                    "notes": "自動化測試"
                }

                start = datetime.now()
                resp = await client.post(
                    f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details",
                    json=detail_data,
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    detail = data.get("data", {})
                    detail_id = detail.get("id")
                    self._record_result(
                        f"新增 course_rate 明細 (金額: {detail.get('amount')})",
                        True,
                        duration_ms=duration
                    )
                    print(f"     └─ detail_type: {detail.get('detail_type')}")
                    print(f"     └─ course_name: {detail.get('course_name')}")
                    print(f"     └─ amount: {detail.get('amount')}")
                else:
                    self._record_result(
                        "新增 course_rate 明細",
                        False,
                        f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                        duration_ms=duration
                    )
            else:
                print("  ⚠️  沒有可用的課程，跳過 course_rate 測試")

            # --- 新增 allowance 明細 ---
            allowance_data = {
                "detail_type": "allowance",
                "description": "交通津貼",
                "amount": 2000.0,
                "notes": "自動化測試津貼"
            }

            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details",
                json=allowance_data,
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            allowance_detail_id: Optional[str] = None
            if resp.status_code == 200:
                data = resp.json()
                detail = data.get("data", {})
                allowance_detail_id = detail.get("id")
                self._record_result(
                    f"新增 allowance 明細 (金額: {detail.get('amount')})",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "新增 allowance 明細",
                    False,
                    f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                    duration_ms=duration
                )

            # --- 列出明細（應有資料）---
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                details = data.get("data", [])
                expected_count = (1 if self.course_id else 0) + 1  # course_rate + allowance
                self._record_result(
                    f"新增後列出明細 (共 {len(details)} 筆，預期 {expected_count})",
                    len(details) == expected_count,
                    f"實際 {len(details)} 筆" if len(details) != expected_count else "",
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "新增後列出明細",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

            # --- 驗證合約的 total_amount（已更新為 full_time，應有值）---
            start = datetime.now()
            resp = await client.get(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}",
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 200:
                data = resp.json()
                contract = data.get("data", {})
                total_amount = contract.get("total_amount")
                emp_type = contract.get("employment_type")
                if emp_type == "full_time":
                    expected_total = (600.0 if self.course_id else 0) + 2000.0
                    self._record_result(
                        f"正職合約 total_amount 正確 (預期: {expected_total}, 實際: {total_amount})",
                        total_amount == expected_total,
                        f"預期 {expected_total}，實際 {total_amount}" if total_amount != expected_total else "",
                        duration_ms=duration
                    )
                else:
                    # 時薪合約 total_amount 應為 None
                    self._record_result(
                        f"時薪合約 total_amount 為 None (實際: {total_amount})",
                        total_amount is None,
                        f"預期 None，實際 {total_amount}" if total_amount is not None else "",
                        duration_ms=duration
                    )
            else:
                self._record_result(
                    "驗證 total_amount",
                    False,
                    f"狀態碼: {resp.status_code}",
                    duration_ms=duration
                )

            # --- 更新明細 ---
            update_target_id = allowance_detail_id or detail_id
            if update_target_id:
                update_detail_data = {
                    "description": "更新後的交通津貼",
                    "amount": 2500.0,
                }

                start = datetime.now()
                resp = await client.put(
                    f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details/{update_target_id}",
                    json=update_detail_data,
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    detail = data.get("data", {})
                    amount_ok = detail.get("amount") == 2500.0
                    desc_ok = detail.get("description") == "更新後的交通津貼"
                    self._record_result(
                        "更新明細成功",
                        amount_ok and desc_ok,
                        "" if (amount_ok and desc_ok) else f"amount={detail.get('amount')}, description={detail.get('description')}",
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "更新明細",
                        False,
                        f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                        duration_ms=duration
                    )

            # --- 刪除明細 ---
            if allowance_detail_id:
                start = datetime.now()
                resp = await client.delete(
                    f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details/{allowance_detail_id}",
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
                        f"狀態碼: {resp.status_code}, 回應: {resp.text}",
                        duration_ms=duration
                    )

                # 驗證刪除後數量
                start = datetime.now()
                resp = await client.get(
                    f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 200:
                    data = resp.json()
                    details = data.get("data", [])
                    expected_after_delete = 1 if self.course_id else 0
                    self._record_result(
                        f"刪除後明細數量 (預期: {expected_after_delete}, 實際: {len(details)})",
                        len(details) == expected_after_delete,
                        f"預期 {expected_after_delete}，實際 {len(details)}" if len(details) != expected_after_delete else "",
                        duration_ms=duration
                    )

            # --- 測試 course_rate 驗證：缺少 course_id ---
            invalid_data = {
                "detail_type": "course_rate",
                "description": "缺少 course_id",
                "amount": 100.0,
            }

            start = datetime.now()
            resp = await client.post(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details",
                json=invalid_data,
                cookies=self.cookies
            )
            duration = (datetime.now() - start).total_seconds() * 1000

            if resp.status_code == 422:
                self._record_result(
                    "course_rate 缺少 course_id 返回 422",
                    True,
                    duration_ms=duration
                )
            else:
                self._record_result(
                    "course_rate 驗證",
                    False,
                    f"預期 422，實際 {resp.status_code}",
                    duration_ms=duration
                )

        return True

    async def test_delete_contract(self, contract_id: str) -> bool:
        """測試刪除合約"""
        print("\n" + "=" * 60)
        print("🗑️  測試刪除合約 (Delete)")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            start = datetime.now()
            resp = await client.delete(
                f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}",
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
                    f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}",
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

                # 驗證明細也被連帶刪除
                start = datetime.now()
                resp = await client.get(
                    f"{self.backend_url}/api/v1/teacher-contracts/{contract_id}/details",
                    cookies=self.cookies
                )
                duration = (datetime.now() - start).total_seconds() * 1000

                if resp.status_code == 404:
                    self._record_result(
                        "刪除後明細不可存取",
                        True,
                        duration_ms=duration
                    )
                elif resp.status_code == 200:
                    data = resp.json()
                    details = data.get("data", [])
                    self._record_result(
                        "刪除後明細為空",
                        len(details) == 0,
                        f"預期 0 筆，實際 {len(details)}" if details else "",
                        duration_ms=duration
                    )
                else:
                    self._record_result(
                        "刪除後明細檢查",
                        False,
                        f"狀態碼: {resp.status_code}",
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
            print("📝 已建立的合約（保留不刪除）")
            print("=" * 60 + "\n")
            for contract in self.created_contracts:
                print(f"  ID: {contract.id}")
                print(f"  合約編號: {contract.contract_no}")
                print()
            return

        if not self.created_contracts:
            return

        print("\n" + "=" * 60)
        print("🧹 清理測試資料")
        print("=" * 60 + "\n")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for contract in self.created_contracts:
                resp = await client.delete(
                    f"{self.backend_url}/api/v1/teacher-contracts/{contract.id}",
                    cookies=self.cookies
                )
                if resp.status_code == 200:
                    print(f"  ✅ 已刪除: {contract.contract_no}")
                elif resp.status_code == 404:
                    print(f"  ⏭️  已刪除 (測試中刪除): {contract.contract_no}")
                else:
                    print(f"  ❌ 刪除失敗: {contract.contract_no}")

    def print_summary(self):
        """列印測試摘要"""
        print("\n" + "=" * 60)
        print("📊 測試摘要")
        print("=" * 60 + "\n")

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"  總計: {total} 項測試")
        print(f"  通過: {passed} ✅")
        print(f"  失敗: {failed} ❌")
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
        description="Teacher Contracts CRUD API 測試腳本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例:
  # 完整 CRUD 測試（需要 employee/admin 帳號）
  python tests/live_teacher_contracts_test.py --email employee@example.com --password testpass

  # 只測試列表和讀取
  python tests/live_teacher_contracts_test.py --email student@example.com --password testpass --read-only

  # 保留測試建立的合約
  python tests/live_teacher_contracts_test.py --email employee@example.com --password testpass --no-cleanup
        """
    )

    parser.add_argument("--email", required=True, help="登入 Email")
    parser.add_argument("--password", required=True, help="登入密碼")
    parser.add_argument("--backend-url", default=BACKEND_URL, help=f"後端 URL (預設: {BACKEND_URL})")
    parser.add_argument("--read-only", action="store_true", help="只測試讀取功能（不需要 staff 權限）")
    parser.add_argument("--no-cleanup", action="store_true", help="保留測試建立的合約")

    args = parser.parse_args()

    tester = TeacherContractsCRUDTester(args.backend_url, no_cleanup=args.no_cleanup)

    print("\n" + "🚀" * 20)
    print("\n   Teacher Contracts CRUD API 測試")
    print(f"   後端: {args.backend_url}")
    print(f"   模式: {'唯讀' if args.read_only else '完整 CRUD'}")
    print("\n" + "🚀" * 20)

    try:
        # 1. 登入
        if not await tester.login(args.email, args.password):
            tester.print_summary()
            sys.exit(1)

        # 2. 取得選項
        if not await tester.fetch_options():
            print("\n⚠️  無法取得教師選項，請確認資料庫有資料")
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
            print("\n⚠️  目前角色為 '{}'，無法執行建立/更新/刪除測試".format(tester.user_role))
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

            # 9. 測試刪除合約（如果不是 no_cleanup 模式）
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
        print("\n\n⚠️  測試中斷")
        await tester.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 測試發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        await tester.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
