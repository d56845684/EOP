"""共用 Pydantic 型別 / 驗證輔助。

前端表單常以空字串作為「未填」的預設值；Pydantic 對 Optional[date]/[datetime]
型別收到 "" 會嘗試解析失敗回 422 「Input should be a valid date or datetime,
input is too short」。為了讓使用者體驗一致，輸入用 schema 的 Optional 日期欄位
應改用 OptionalDate / OptionalDateTime 這兩個 Annotated 型別，會在驗證前把空字串
轉成 None。

回應用 schema 不需動（資料由後端產生，不會有空字串問題）。
"""
from datetime import date, datetime
from typing import Annotated, Optional

from pydantic import BeforeValidator


def _empty_str_to_none(value):
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


OptionalDate = Annotated[Optional[date], BeforeValidator(_empty_str_to_none)]
OptionalDateTime = Annotated[Optional[datetime], BeforeValidator(_empty_str_to_none)]
