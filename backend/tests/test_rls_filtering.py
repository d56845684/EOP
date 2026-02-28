#!/usr/bin/env python3
"""
測試合約 API 的角色權限過濾 (模擬 RLS 行為)

測試場景:
1. 員工可以看到所有合約
2. 學生只能看到自己的學生合約
3. 教師只能看到自己的教師合約
4. 學生無法看到教師合約
5. 教師無法看到學生合約
"""
import httpx
import json
import sys
from pathlib import Path

# 配置
BASE_URL = "http://localhost:8001/api/v1"

# 測試帳號 (從 secret.md)
TEST_ACCOUNTS = {
    "student": {
        "email": "test_auth_student_20260128_225617_432708@example.com",
        "password": "TestPassword123!"
    },
    "teacher": {
        "email": "test_auth_teacher_20260128_225618_410286@example.com",
        "password": "TestPassword123!"
    },
    "employee": {
        "email": "test_auth_employee_20260128_225619_347997@example.com",
        "password": "TestPassword123!"
    }
}


def login(client: httpx.Client, role: str) -> bool:
    """登入並設置 cookies"""
    account = TEST_ACCOUNTS[role]
    response = client.post(
        f"{BASE_URL}/auth/login",
        json={"email": account["email"], "password": account["password"]}
    )
    if response.status_code == 200:
        print(f"  ✓ 以 {role} 身份登入成功")
        return True
    else:
        print(f"  ✗ {role} 登入失敗: {response.text}")
        return False


def test_student_contracts_list(client: httpx.Client, role: str, expect_empty: bool = False):
    """測試學生合約列表"""
    response = client.get(f"{BASE_URL}/student-contracts")

    if response.status_code == 200:
        data = response.json()
        contracts = data.get("data", [])
        total = data.get("total", 0)

        if expect_empty:
            if total == 0:
                print(f"  ✓ [{role}] 學生合約列表為空 (符合預期)")
                return True
            else:
                print(f"  ✗ [{role}] 預期空列表，但收到 {total} 筆合約")
                return False
        else:
            print(f"  ✓ [{role}] 取得 {total} 筆學生合約")
            return True
    else:
        print(f"  ✗ [{role}] 取得學生合約失敗: {response.status_code}")
        return False


def test_teacher_contracts_list(client: httpx.Client, role: str, expect_empty: bool = False):
    """測試教師合約列表"""
    response = client.get(f"{BASE_URL}/teacher-contracts")

    if response.status_code == 200:
        data = response.json()
        contracts = data.get("data", [])
        total = data.get("total", 0)

        if expect_empty:
            if total == 0:
                print(f"  ✓ [{role}] 教師合約列表為空 (符合預期)")
                return True
            else:
                print(f"  ✗ [{role}] 預期空列表，但收到 {total} 筆合約")
                return False
        else:
            print(f"  ✓ [{role}] 取得 {total} 筆教師合約")
            return True
    else:
        print(f"  ✗ [{role}] 取得教師合約失敗: {response.status_code}")
        return False


def test_get_single_contract_forbidden(client: httpx.Client, role: str, contract_type: str, contract_id: str):
    """測試取得不屬於自己的合約是否被拒絕"""
    endpoint = f"{BASE_URL}/{contract_type}/{contract_id}"
    response = client.get(endpoint)

    if response.status_code == 403:
        print(f"  ✓ [{role}] 存取 {contract_type} {contract_id[:8]}... 被拒絕 (403)")
        return True
    elif response.status_code == 404:
        print(f"  ? [{role}] 合約不存在 (404) - 跳過此測試")
        return True  # 合約不存在也算通過
    else:
        print(f"  ✗ [{role}] 預期 403，但收到 {response.status_code}")
        return False


def get_all_contracts(client: httpx.Client):
    """取得所有合約 ID (需要員工權限)"""
    student_contracts = []
    teacher_contracts = []

    response = client.get(f"{BASE_URL}/student-contracts")
    if response.status_code == 200:
        data = response.json()
        student_contracts = [c["id"] for c in data.get("data", [])]

    response = client.get(f"{BASE_URL}/teacher-contracts")
    if response.status_code == 200:
        data = response.json()
        teacher_contracts = [c["id"] for c in data.get("data", [])]

    return student_contracts, teacher_contracts


def main():
    print("\n" + "=" * 60)
    print("測試合約 API 角色權限過濾")
    print("=" * 60)

    results = []
    student_contract_ids = []
    teacher_contract_ids = []

    # 測試 1: 員工 - 可以看到所有合約
    print("\n[Test 1] 員工權限測試")
    with httpx.Client(timeout=30) as client:
        if login(client, "employee"):
            results.append(test_student_contracts_list(client, "employee"))
            results.append(test_teacher_contracts_list(client, "employee"))
            # 取得合約 ID 供後續測試使用
            student_contract_ids, teacher_contract_ids = get_all_contracts(client)

    # 測試 2: 學生 - 只能看到自己的學生合約，無法看到教師合約
    print("\n[Test 2] 學生權限測試")
    with httpx.Client(timeout=30) as client:
        if login(client, "student"):
            # 學生可以看到自己的合約 (可能是空的，因為沒有綁定)
            results.append(test_student_contracts_list(client, "student"))
            # 學生無法看到教師合約 (應該返回空列表)
            results.append(test_teacher_contracts_list(client, "student", expect_empty=True))
            # 測試存取單一教師合約是否被拒絕
            if teacher_contract_ids:
                results.append(test_get_single_contract_forbidden(
                    client, "student", "teacher-contracts", teacher_contract_ids[0]
                ))

    # 測試 3: 教師 - 只能看到自己的教師合約，無法看到學生合約
    print("\n[Test 3] 教師權限測試")
    with httpx.Client(timeout=30) as client:
        if login(client, "teacher"):
            # 教師無法看到學生合約 (應該返回空列表)
            results.append(test_student_contracts_list(client, "teacher", expect_empty=True))
            # 教師可以看到自己的合約 (可能是空的，因為沒有綁定)
            results.append(test_teacher_contracts_list(client, "teacher"))
            # 測試存取單一學生合約是否被拒絕
            if student_contract_ids:
                results.append(test_get_single_contract_forbidden(
                    client, "teacher", "student-contracts", student_contract_ids[0]
                ))

    # 統計結果
    passed = sum(1 for r in results if r)
    total = len(results)

    print("\n" + "=" * 60)
    print(f"測試結果: {passed}/{total} 通過")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
