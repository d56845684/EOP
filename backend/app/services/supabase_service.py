import asyncpg
import json
import uuid
import re
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, Any
from passlib.hash import bcrypt

import logging
logger = logging.getLogger(__name__)


async def _init_connection(conn: asyncpg.Connection):
    """Set up JSONB codec so asyncpg can handle Python dicts natively."""
    await conn.set_type_codec(
        'jsonb', encoder=json.dumps, decoder=json.loads,
        schema='pg_catalog'
    )
    await conn.set_type_codec(
        'json', encoder=json.dumps, decoder=json.loads,
        schema='pg_catalog'
    )


class SupabaseAuthResponse:
    """Auth response wrapper"""
    def __init__(self, data: dict):
        self._data = data
        self.user = SupabaseUser(data.get("user")) if data.get("user") else None
        self.session = SupabaseSession(data.get("session")) if data.get("session") else None
        self.error = data.get("error")


class SupabaseUser:
    """User data wrapper"""
    def __init__(self, data: dict):
        self._data = data or {}
        self.id = self._data.get("id")
        self.email = self._data.get("email")
        self.email_confirmed_at = self._data.get("email_confirmed_at")
        self.created_at = self._data.get("created_at")
        self.user_metadata = self._data.get("user_metadata", {})


class SupabaseSession:
    """Session data wrapper"""
    def __init__(self, data: dict):
        self._data = data or {}
        self.access_token = self._data.get("access_token")
        self.refresh_token = self._data.get("refresh_token")
        self.expires_in = self._data.get("expires_in")
        self.token_type = self._data.get("token_type")


class SupabaseService:
    """Database service - asyncpg direct connection replacing Supabase httpx calls"""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self, dsn: str):
        """Initialize asyncpg connection pool"""
        self._pool = await asyncpg.create_pool(
            dsn, min_size=2, max_size=10, init=_init_connection
        )
        logger.info("asyncpg connection pool created")

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("Database pool not initialized. Call connect() first.")
        return self._pool

    # ========== Helpers ==========

    @staticmethod
    def _sanitize_identifier(name: str) -> str:
        """Sanitize a SQL identifier (table/column name) to prevent injection.
        Removes double quotes to prevent breaking out of quoted identifiers.
        Only allows alphanumeric, underscore, and dot characters.
        """
        # Remove any double quotes that could break out of quoting
        sanitized = name.replace('"', '')
        # Validate: only allow safe identifier characters
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', sanitized):
            raise ValueError(f"Invalid SQL identifier: {name}")
        return sanitized

    @staticmethod
    def _row_to_dict(record: asyncpg.Record) -> dict:
        """Convert asyncpg Record to dict with JSON-compatible types"""
        result = {}
        for key, value in record.items():
            if isinstance(value, uuid.UUID):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, date):
                result[key] = value.isoformat()
            elif isinstance(value, time):
                result[key] = value.isoformat()
            elif isinstance(value, Decimal):
                result[key] = float(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _coerce_value(val: str) -> Any:
        """Coerce string values to native Python types for asyncpg.

        asyncpg is strict about types — PostgreSQL boolean columns need
        real bools, integer columns need ints, UUID columns need UUIDs,
        date/time columns need native date/time objects, etc.
        """
        low = val.lower()
        if low == "true":
            return True
        if low == "false":
            return False
        if low == "null":
            return None
        # Try integer
        try:
            return int(val)
        except ValueError:
            pass
        # Try UUID
        try:
            return uuid.UUID(val)
        except ValueError:
            pass
        # Try datetime (contains 'T' separator)
        if 'T' in val:
            try:
                return datetime.fromisoformat(val)
            except (ValueError, TypeError):
                pass
        # Try date (YYYY-MM-DD, exactly 10 chars)
        if len(val) == 10 and val[4:5] == '-' and val[7:8] == '-':
            try:
                return date.fromisoformat(val)
            except (ValueError, TypeError):
                pass
        # Try time (HH:MM:SS or HH:MM)
        if len(val) >= 5 and val[2:3] == ':':
            try:
                return time.fromisoformat(val)
            except (ValueError, TypeError):
                pass
        return val

    @staticmethod
    def _coerce_datetime_str(value: Any) -> Any:
        """Coerce ISO date/time/datetime strings to native Python types.

        Used for INSERT/UPDATE data values where .isoformat() was called
        before passing to the service. Only converts strings matching
        date/time patterns — other strings are left as-is.
        """
        if not isinstance(value, str):
            return value
        # Try datetime (contains 'T' separator)
        if 'T' in value:
            try:
                return datetime.fromisoformat(value)
            except (ValueError, TypeError):
                pass
        # Try date (YYYY-MM-DD, exactly 10 chars)
        if len(value) == 10 and value[4:5] == '-' and value[7:8] == '-':
            try:
                return date.fromisoformat(value)
            except (ValueError, TypeError):
                pass
        # Try time (HH:MM:SS or HH:MM)
        if len(value) >= 5 and value[2:3] == ':':
            try:
                return time.fromisoformat(value)
            except (ValueError, TypeError):
                pass
        return value

    @classmethod
    def _parse_filter(cls, key: str, value: Any, params: list) -> str:
        """Parse PostgREST-style filter into SQL WHERE clause fragment.

        Supports: eq., neq., gt., gte., lt., lte., is.null/true/false,
                  in.(a,b,c), like., ilike., and bare values (default eq).
        """
        col = f'"{cls._sanitize_identifier(key)}"'

        if not isinstance(value, str):
            params.append(value)
            return f"{col} = ${len(params)}"

        # is. operator (null / true / false)
        if value.startswith("is."):
            literal = value[3:].lower()
            if literal == "null":
                return f"{col} IS NULL"
            elif literal == "true":
                return f"{col} IS TRUE"
            elif literal == "false":
                return f"{col} IS FALSE"

        # in.(a,b,c)
        m = re.match(r'^in\.\((.+)\)$', value)
        if m:
            items = [v.strip() for v in m.group(1).split(",")]
            placeholders = []
            for item in items:
                params.append(item)
                placeholders.append(f"${len(params)}")
            return f"{col} IN ({', '.join(placeholders)})"

        # Operators with value
        operators = {
            "eq.": "=",
            "neq.": "!=",
            "gt.": ">",
            "gte.": ">=",
            "lt.": "<",
            "lte.": "<=",
            "like.": "LIKE",
            "ilike.": "ILIKE",
        }

        for prefix, sql_op in operators.items():
            if value.startswith(prefix):
                val = value[len(prefix):]
                params.append(cls._coerce_value(val))
                return f"{col} {sql_op} ${len(params)}"

        # Default: treat as eq
        params.append(cls._coerce_value(value))
        return f"{col} = ${len(params)}"

    @classmethod
    def _parse_select(cls, select: str) -> str:
        """Convert select string to SQL column list"""
        if select == "*":
            return "*"
        cols = [f'"{cls._sanitize_identifier(c.strip())}"' for c in select.split(",")]
        return ", ".join(cols)

    _VALID_DIRECTIONS = {"ASC", "DESC"}
    _VALID_NULLS = {"FIRST", "LAST"}

    @classmethod
    def _parse_order(cls, order_by: str) -> str:
        """Convert PostgREST order string to SQL ORDER BY.
        e.g. 'created_at.desc' -> '"created_at" DESC'
        Supports comma-separated: 'slot_date.asc,start_time.asc'
        """
        order_parts = []
        for segment in order_by.split(","):
            parts = segment.strip().split(".")
            col = f'"{cls._sanitize_identifier(parts[0])}"'
            direction = parts[1].upper() if len(parts) > 1 else "ASC"
            if direction not in cls._VALID_DIRECTIONS:
                raise ValueError(f"Invalid ORDER BY direction: {direction}")
            nulls = ""
            if len(parts) > 2:
                nulls_val = parts[2].upper()
                if nulls_val not in cls._VALID_NULLS:
                    raise ValueError(f"Invalid NULLS option: {nulls_val}")
                nulls = f" NULLS {nulls_val}"
            order_parts.append(f"{col} {direction}{nulls}")
        return ", ".join(order_parts)

    # ========== Auth API ==========

    async def sign_up(
        self,
        email: str,
        password: str,
        metadata: dict = None
    ) -> SupabaseAuthResponse:
        """User registration"""
        hashed = bcrypt.using(rounds=10).hash(password)
        meta = metadata or {}

        row = await self.pool.fetchrow(
            """
            INSERT INTO public.users (email, encrypted_password, email_confirmed_at, raw_user_meta_data)
            VALUES ($1, $2, NOW(), $3)
            RETURNING id, email, email_confirmed_at, raw_user_meta_data, created_at
            """,
            email, hashed, meta
        )

        if not row:
            raise Exception("Registration failed")

        user_data = self._row_to_dict(row)
        return SupabaseAuthResponse({
            "user": {
                "id": user_data["id"],
                "email": user_data["email"],
                "email_confirmed_at": user_data["email_confirmed_at"],
                "created_at": user_data["created_at"],
                "user_metadata": user_data.get("raw_user_meta_data", {}),
            },
            "session": None
        })

    async def sign_in_with_password(
        self,
        email: str,
        password: str
    ) -> SupabaseAuthResponse:
        """Password login"""
        row = await self.pool.fetchrow(
            "SELECT id, email, encrypted_password, email_confirmed_at, raw_user_meta_data, created_at FROM public.users WHERE email = $1",
            email
        )

        if not row:
            raise Exception("Invalid login credentials")

        if not bcrypt.verify(password, row["encrypted_password"]):
            raise Exception("Invalid login credentials")

        user_data = self._row_to_dict(row)
        return SupabaseAuthResponse({
            "user": {
                "id": user_data["id"],
                "email": user_data["email"],
                "email_confirmed_at": user_data["email_confirmed_at"],
                "created_at": user_data["created_at"],
                "user_metadata": user_data.get("raw_user_meta_data", {}),
            },
            "session": {
                "access_token": "direct-db",
                "refresh_token": None,
                "expires_in": 0,
                "token_type": "bearer"
            }
        })

    async def sign_out(self, access_token: str) -> bool:
        """Sign out (no-op, session managed by Redis)"""
        return True

    async def get_user(self, access_token: str) -> Optional[SupabaseUser]:
        """Get current user (no-op stub)"""
        return None

    async def refresh_session(self, refresh_token: str) -> SupabaseAuthResponse:
        """Refresh session (no-op stub)"""
        raise Exception("Not supported in direct DB mode")

    async def reset_password_email(
        self,
        email: str,
        redirect_url: str = None
    ) -> bool:
        """Send password reset email (stub)"""
        return False

    # ========== Admin Auth API ==========

    async def admin_get_user(self, user_id: str) -> Optional[SupabaseUser]:
        """Admin get user"""
        row = await self.pool.fetchrow(
            "SELECT id, email, email_confirmed_at, raw_user_meta_data, created_at FROM public.users WHERE id = $1",
            uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        )

        if not row:
            return None

        d = self._row_to_dict(row)
        return SupabaseUser({
            "id": d["id"],
            "email": d["email"],
            "email_confirmed_at": d["email_confirmed_at"],
            "created_at": d["created_at"],
            "user_metadata": d.get("raw_user_meta_data", {}),
        })

    async def admin_list_users(
        self,
        page: int = 1,
        per_page: int = 50
    ) -> list:
        """Admin list users"""
        offset = (page - 1) * per_page
        rows = await self.pool.fetch(
            "SELECT id, email, email_confirmed_at, raw_user_meta_data, created_at FROM public.users ORDER BY created_at LIMIT $1 OFFSET $2",
            per_page, offset
        )

        result = []
        for row in rows:
            d = self._row_to_dict(row)
            result.append(SupabaseUser({
                "id": d["id"],
                "email": d["email"],
                "email_confirmed_at": d["email_confirmed_at"],
                "created_at": d["created_at"],
                "user_metadata": d.get("raw_user_meta_data", {}),
            }))
        return result

    async def admin_delete_user(self, user_id: str) -> bool:
        """Admin delete user"""
        result = await self.pool.execute(
            "DELETE FROM public.users WHERE id = $1",
            uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        )
        return result == "DELETE 1"

    async def admin_update_user(
        self,
        user_id: str,
        attributes: dict
    ) -> Optional[SupabaseUser]:
        """Admin update user"""
        sets = []
        params = []
        idx = 1

        if "email" in attributes:
            sets.append(f"email = ${idx}")
            params.append(attributes["email"])
            idx += 1
        if "password" in attributes:
            sets.append(f"encrypted_password = ${idx}")
            params.append(bcrypt.using(rounds=10).hash(attributes["password"]))
            idx += 1
        if "user_metadata" in attributes:
            sets.append(f"raw_user_meta_data = ${idx}")
            params.append(attributes["user_metadata"])
            idx += 1

        if not sets:
            return await self.admin_get_user(user_id)

        sets.append(f"updated_at = NOW()")
        params.append(uuid.UUID(user_id) if isinstance(user_id, str) else user_id)

        row = await self.pool.fetchrow(
            f"UPDATE public.users SET {', '.join(sets)} WHERE id = ${idx} RETURNING id, email, email_confirmed_at, raw_user_meta_data, created_at",
            *params
        )

        if not row:
            return None

        d = self._row_to_dict(row)
        return SupabaseUser({
            "id": d["id"],
            "email": d["email"],
            "email_confirmed_at": d["email_confirmed_at"],
            "created_at": d["created_at"],
            "user_metadata": d.get("raw_user_meta_data", {}),
        })

    # ========== Database API (replaces PostgREST) ==========

    async def table_select(
        self,
        table: str,
        select: str = "*",
        filters: dict = None,
    ) -> list[dict]:
        """Query table"""
        tbl = self._sanitize_identifier(table)
        cols = self._parse_select(select)
        params = []
        where_clauses = []

        if filters:
            for key, value in filters.items():
                where_clauses.append(self._parse_filter(key, value, params))

        sql = f'SELECT {cols} FROM "{tbl}"'
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        rows = await self.pool.fetch(sql, *params)
        return [self._row_to_dict(r) for r in rows]

    async def table_select_with_pagination(
        self,
        table: str,
        select: str = "*",
        filters: dict = None,
        order_by: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]:
        """Query table with pagination and ordering"""
        tbl = self._sanitize_identifier(table)
        cols = self._parse_select(select)
        params = []
        where_clauses = []

        if filters:
            for key, value in filters.items():
                where_clauses.append(self._parse_filter(key, value, params))

        sql = f'SELECT {cols} FROM "{tbl}"'
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        if order_by:
            sql += " ORDER BY " + self._parse_order(order_by)

        params.append(limit)
        sql += f" LIMIT ${len(params)}"
        params.append(offset)
        sql += f" OFFSET ${len(params)}"

        rows = await self.pool.fetch(sql, *params)
        return [self._row_to_dict(r) for r in rows]

    async def table_insert(
        self,
        table: str,
        data: dict,
    ) -> Optional[dict]:
        """Insert data"""
        tbl = self._sanitize_identifier(table)
        columns = []
        placeholders = []
        params = []

        for key, value in data.items():
            columns.append(f'"{self._sanitize_identifier(key)}"')
            if isinstance(value, str) and value == "now()":
                placeholders.append("NOW()")
            elif value is None:
                placeholders.append("NULL")
            else:
                params.append(self._coerce_datetime_str(value))
                placeholders.append(f"${len(params)}")

        sql = f'INSERT INTO "{tbl}" ({", ".join(columns)}) VALUES ({", ".join(placeholders)}) RETURNING *'
        row = await self.pool.fetchrow(sql, *params)

        if not row:
            raise Exception("Insert failed")

        return self._row_to_dict(row)

    async def table_update(
        self,
        table: str,
        data: dict,
        filters: dict,
    ) -> Optional[dict]:
        """Update data"""
        tbl = self._sanitize_identifier(table)
        set_parts = []
        params = []

        for key, value in data.items():
            safe_key = self._sanitize_identifier(key)
            if isinstance(value, str) and value == "now()":
                set_parts.append(f'"{safe_key}" = NOW()')
            elif value is None:
                set_parts.append(f'"{safe_key}" = NULL')
            else:
                params.append(self._coerce_datetime_str(value))
                set_parts.append(f'"{safe_key}" = ${len(params)}')

        where_clauses = []
        for key, value in filters.items():
            where_clauses.append(self._parse_filter(key, value, params))

        sql = f'UPDATE "{tbl}" SET {", ".join(set_parts)} WHERE {" AND ".join(where_clauses)} RETURNING *'
        row = await self.pool.fetchrow(sql, *params)

        if not row:
            return None

        return self._row_to_dict(row)

    async def table_delete(
        self,
        table: str,
        filters: dict,
    ) -> bool:
        """Delete data"""
        tbl = self._sanitize_identifier(table)
        params = []
        where_clauses = []

        for key, value in filters.items():
            # table_delete filters don't use operator prefixes in existing code
            safe_key = self._sanitize_identifier(key)
            params.append(self._coerce_datetime_str(value))
            where_clauses.append(f'"{safe_key}" = ${len(params)}')

        sql = f'DELETE FROM "{tbl}" WHERE {" AND ".join(where_clauses)}'
        result = await self.pool.execute(sql, *params)
        return result.startswith("DELETE")

    # ========== Cleanup ==========

    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None


# Singleton
supabase_service = SupabaseService()
