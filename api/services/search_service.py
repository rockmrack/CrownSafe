"""
Enhanced Search Service with pg_trgm fuzzy matching, keyword AND logic, and deterministic sorting
"""

from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import and_, or_, func, desc, asc, literal, text
from sqlalchemy.orm import Session
from datetime import date
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """
    Advanced search service using PostgreSQL pg_trgm for fuzzy matching
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    def _normalize_text(self, s: str) -> str:
        """Normalize text for search"""
        return (s or "").strip().lower()

    def build_search_query(
        self,
        # Text search
        query: Optional[str] = None,
        product: Optional[str] = None,
        id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        # Filters
        agencies: Optional[List[str]] = None,
        severity: Optional[str] = None,
        risk_category: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        # Pagination
        limit: int = 20,
        offset: int = 0,
        cursor_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Dict[str, Any], bool]:
        """
        Build optimized SQL query using pg_trgm for fuzzy search

        Returns:
            (sql_query, params, use_scoring)
        """

        # Determine which table to use (portable check)
        from sqlalchemy import inspect

        inspector = inspect(self.db.bind)
        has_enhanced = inspector.has_table("recalls_enhanced")
        has_legacy = inspector.has_table("recalls")

        if not has_enhanced and not has_legacy:
            # No recall tables exist - return empty query tuple
            from core_infra.search_constants import EMPTY_QUERY, EMPTY_PARAMS

            return EMPTY_QUERY, EMPTY_PARAMS, False

        table = "recalls_enhanced" if has_enhanced else "recalls"

        # Base columns to select
        select_columns = [
            f"{table}.recall_id as id",
            f"{table}.product_name",
            f"{table}.brand",
            f"{table}.hazard",
            f"{table}.recall_date",
            f"{table}.source_agency",
            f"{table}.description",
            f"{table}.url",
            f"{table}.country",
        ]

        # Check for additional columns
        if has_enhanced:
            select_columns.extend(
                [
                    f"{table}.severity",
                    f"{table}.risk_category",
                    f"{table}.manufacturer",
                    f"{table}.model_number",
                    f"{table}.upc",
                ]
            )

        # Start building WHERE conditions
        where_conditions = []
        params = {}

        # 1. Exact ID lookup (highest priority)
        if id:
            where_conditions.append(f"{table}.recall_id = :recall_id")
            params["recall_id"] = id
            # For exact ID, no scoring needed
            sql = f"""
                SELECT 
                    {", ".join(select_columns)},
                    1.0 as score
                FROM {table}
                WHERE {" AND ".join(where_conditions)}
                LIMIT 1
            """
            return sql, params, False

        # 2. Apply filters
        if agencies:
            where_conditions.append(f"{table}.source_agency = ANY(:agencies)")
            params["agencies"] = agencies

        if severity and has_enhanced:
            where_conditions.append(f"{table}.severity = :severity")
            params["severity"] = severity

        if risk_category and has_enhanced:
            where_conditions.append(f"{table}.risk_category = :risk_category")
            params["risk_category"] = risk_category

        if date_from:
            where_conditions.append(f"{table}.recall_date >= :date_from")
            params["date_from"] = date_from

        if date_to:
            where_conditions.append(f"{table}.recall_date <= :date_to")
            params["date_to"] = date_to

        # 3. Text search with fuzzy matching
        text_query = self._normalize_text(product or query or "")
        use_scoring = False
        score_expression = "0.0"

        if text_query:
            use_scoring = True

            # Check database dialect for compatibility
            dialect = self.db.bind.dialect.name

            # Check if pg_trgm is available before using it
            use_pg_trgm = False
            if dialect == "postgresql":
                try:
                    use_pg_trgm = self.check_pg_trgm_enabled()
                    if not use_pg_trgm:
                        logger.warning("[WARN] pg_trgm extension not enabled, falling back to LIKE search")
                except Exception as e:
                    logger.warning(f"[WARN] pg_trgm check failed: {e}, falling back to LIKE search")

            if dialect == "postgresql" and use_pg_trgm:
                # Use pg_trgm similarity for fuzzy matching (PostgreSQL only)
                similarity_expressions = [
                    f"similarity(lower({table}.product_name), :search_text)",
                    f"similarity(lower({table}.brand), :search_text)",
                    f"similarity(lower({table}.description), :search_text)",
                    f"similarity(lower({table}.hazard), :search_text)",
                ]

                # Take the greatest similarity as the score
                score_expression = f"GREATEST({', '.join(similarity_expressions)})"

                # Filter to only reasonably similar results (threshold: 0.08)
                where_conditions.append(f"{score_expression} >= 0.08")
                params["search_text"] = text_query
            else:
                # SQLite-compatible search using LIKE
                search_conditions = [
                    f"lower({table}.product_name) LIKE :search_pattern",
                    f"lower({table}.brand) LIKE :search_pattern",
                    f"lower({table}.description) LIKE :search_pattern",
                    f"lower({table}.hazard) LIKE :search_pattern",
                ]
                where_conditions.append(f"({' OR '.join(search_conditions)})")
                params["search_pattern"] = f"%{text_query}%"

                # Simple relevance scoring for SQLite
                score_expression = f"""
                    CASE 
                        WHEN lower({table}.product_name) = :search_text THEN 1.0
                        WHEN lower({table}.brand) = :search_text THEN 0.9
                        WHEN lower({table}.product_name) LIKE :search_start THEN 0.8
                        WHEN lower({table}.brand) LIKE :search_start THEN 0.7
                        ELSE 0.5
                    END
                """
                params["search_text"] = text_query
                params["search_start"] = f"{text_query}%"

        # 4. Keyword AND logic
        if keywords:
            normalized_keywords = [k.strip().lower() for k in keywords if k and k.strip()]
            for i, keyword in enumerate(normalized_keywords):
                # Each keyword must appear in at least one text field
                keyword_conditions = [
                    f"lower({table}.product_name) LIKE :keyword_{i}",
                    f"lower({table}.brand) LIKE :keyword_{i}",
                    f"lower({table}.description) LIKE :keyword_{i}",
                    f"lower({table}.hazard) LIKE :keyword_{i}",
                ]
                where_conditions.append(f"({' OR '.join(keyword_conditions)})")
                params[f"keyword_{i}"] = f"%{keyword}%"

        # Build the final query
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

        # Deterministic sorting: score DESC, recall_date DESC, id ASC
        order_by = []
        if use_scoring:
            order_by.append("score DESC")

        # Handle NULLS LAST syntax for different dialects
        dialect = self.db.bind.dialect.name
        if dialect == "postgresql":
            order_by.extend([f"{table}.recall_date DESC NULLS LAST", f"{table}.recall_id ASC"])
        else:
            # SQLite doesn't support NULLS LAST, use COALESCE
            order_by.extend(
                [
                    f"COALESCE({table}.recall_date, '1900-01-01') DESC",
                    f"{table}.recall_id ASC",
                ]
            )

        # Handle cursor-based pagination
        if cursor_data:
            # Add cursor-based WHERE conditions for proper pagination
            cursor_conditions = []
            last_id = cursor_data.get("last_id")
            last_date = cursor_data.get("last_date")

            if last_date and last_id:
                # For cursor pagination: get records after the last seen record
                # (recall_date < last_date) OR (recall_date = last_date AND recall_id > last_id)
                cursor_conditions.append(
                    f"""
                    ({table}.recall_date < :cursor_date) OR 
                    ({table}.recall_date = :cursor_date AND {table}.recall_id > :cursor_id)
                """
                )
                params["cursor_date"] = last_date
                params["cursor_id"] = last_id
                logger.info(f"Cursor pagination: last_date={last_date}, last_id={last_id}")

            if cursor_conditions:
                if where_clause:
                    where_clause = f"({where_clause}) AND ({' AND '.join(cursor_conditions)})"
                else:
                    where_clause = " AND ".join(cursor_conditions)

        sql = f"""
            SELECT 
                {", ".join(select_columns)},
                {score_expression} as score
            FROM {table}
            WHERE {where_clause}
            ORDER BY {", ".join(order_by)}
            LIMIT :limit
        """

        # Only add OFFSET for non-cursor pagination
        if not cursor_data:
            sql += " OFFSET :offset"
            params["offset"] = offset

        params["limit"] = min(limit, 50)  # Cap at 50

        return sql, params, use_scoring

    def search(
        self,
        query: Optional[str] = None,
        product: Optional[str] = None,
        id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        agencies: Optional[List[str]] = None,
        severity: Optional[str] = None,
        risk_category: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 20,
        offset: Optional[int] = None,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute search with fuzzy matching and return results
        """
        try:
            # Handle cursor-based pagination
            cursor_data = None
            actual_offset = offset
            use_cursor_pagination = False

            if cursor:
                try:
                    import base64
                    import json

                    cursor_data = json.loads(base64.b64decode(cursor).decode())
                    actual_offset = cursor_data.get("offset", 0)
                    use_cursor_pagination = True
                    logger.info(f"Cursor decoded: offset={actual_offset}, cursor_data={cursor_data}")
                except Exception as e:
                    logger.warning(f"Invalid cursor: {e}, falling back to offset")
                    actual_offset = offset or 0
            elif offset is not None:
                actual_offset = offset
            else:
                actual_offset = 0

            logger.info(
                f"Search parameters: offset={offset}, cursor={cursor}, actual_offset={actual_offset}, limit={limit}, use_cursor={use_cursor_pagination}"
            )

            # Build the query
            sql_query, params, use_scoring = self.build_search_query(
                query=query,
                product=product,
                id=id,
                keywords=keywords,
                agencies=agencies,
                severity=severity,
                risk_category=risk_category,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=actual_offset,
                cursor_data=cursor_data if use_cursor_pagination else None,
            )

            # Execute query
            result = self.db.execute(text(sql_query), params)
            rows = result.fetchall()

            # Format results
            items = []
            for row in rows:
                item = {
                    "id": row.id,
                    "productName": row.product_name,
                    "brand": row.brand,
                    "hazard": row.hazard,
                    "recallDate": str(row.recall_date) if row.recall_date else None,
                    "agencyCode": row.source_agency,
                    "description": row.description,
                    "url": row.url,
                    "country": row.country,
                }

                # Add score if using scoring
                if use_scoring:
                    item["relevanceScore"] = round(float(row.score), 3)

                # Add optional fields if they exist
                if hasattr(row, "severity") and row.severity:
                    item["severity"] = row.severity
                if hasattr(row, "risk_category") and row.risk_category:
                    item["riskCategory"] = row.risk_category
                if hasattr(row, "manufacturer") and row.manufacturer:
                    item["manufacturer"] = row.manufacturer
                if hasattr(row, "model_number") and row.model_number:
                    item["modelNumber"] = row.model_number
                if hasattr(row, "upc") and row.upc:
                    item["upc"] = row.upc

                # Create title
                title_parts = []
                if row.brand:
                    title_parts.append(row.brand)
                if row.product_name:
                    title_parts.append(row.product_name)
                item["title"] = " - ".join(title_parts) if title_parts else "Unknown Product"

                items.append(item)

            # Get total count (without limit)
            # Handle empty query case
            if sql_query == "SELECT 1 WHERE 1=0":
                total = 0
            else:
                count_sql = f"""
                    SELECT COUNT(*) as total
                    FROM ({sql_query.replace("LIMIT :limit", "").replace("OFFSET :offset", "")}) as subquery
                """
                count_params = {k: v for k, v in params.items() if k not in ["limit", "offset"]}
                total_result = self.db.execute(text(count_sql), count_params)
                total = total_result.scalar() or 0

            # Generate next cursor if there are more results
            next_cursor = None
            has_more = len(items) == limit and (actual_offset + limit) < total

            if has_more and items:
                # Create cursor from the last item
                last_item = items[-1]
                cursor_data = {
                    "offset": actual_offset + limit,
                    "last_id": last_item.get("id"),
                    "last_date": last_item.get("recallDate"),
                }
                import base64
                import json

                next_cursor = base64.b64encode(json.dumps(cursor_data).encode()).decode()

            return {
                "ok": True,
                "data": {
                    "items": items,
                    "total": min(total, len(items)) if id else total,
                    "limit": limit,
                    "offset": actual_offset,
                    "nextCursor": next_cursor,
                    "hasMore": has_more,
                },
            }

        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "ok": False,
                "error": {"code": "SEARCH_ERROR", "message": str(e)},
                "data": {"items": [], "total": 0},
            }

    def get_similarity_threshold(self) -> float:
        """Get current similarity threshold for fuzzy matching"""
        return 0.08  # 8% similarity minimum

    def check_pg_trgm_enabled(self) -> bool:
        """Check if pg_trgm extension is enabled (Postgres only)"""
        try:
            # Only check on PostgreSQL
            if self.db.bind.dialect.name != "postgresql":
                return False
            result = self.db.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')"))
            return result.scalar()
        except:
            return False
