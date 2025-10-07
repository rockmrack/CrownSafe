"""
Enhanced Search Service v2 with keyset pagination and snapshot isolation
Implements cursor-based pagination without OFFSET for better performance
"""

import os
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import and_, or_, func, desc, asc, text
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging
import hashlib
import json

from api.utils import (
    verify_cursor,
    create_search_cursor,
    hash_filters,
    validate_cursor_filters
)

logger = logging.getLogger(__name__)


class SearchServiceV2:
    """
    Advanced search service with keyset pagination and snapshot isolation
    """
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.signing_key = os.getenv("CURSOR_SIGNING_KEY", "default-dev-key-change-in-production")
    
    def _normalize_text(self, s: str) -> str:
        """Normalize text for search"""
        return (s or "").strip().lower()
    
    def build_keyset_query(
        self,
        # Search parameters
        query: Optional[str] = None,
        product: Optional[str] = None,
        id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        # Filters
        agencies: Optional[List[str]] = None,
        severity: Optional[str] = None,
        risk_category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        # Pagination
        limit: int = 20,
        cursor_token: Optional[str] = None
    ) -> Tuple[str, Dict[str, Any], datetime, Optional[Dict]]:
        """
        Build optimized SQL query with keyset pagination
        
        Returns:
            (sql_query, params, as_of_time, cursor_data)
        """
        
        # Parse cursor if provided
        cursor_data = None
        as_of = datetime.now(timezone.utc)
        after_tuple = None
        
        if cursor_token:
            try:
                cursor_data = verify_cursor(cursor_token, self.signing_key)
                
                # Validate cursor version
                if cursor_data.get('v') != 1:
                    raise ValueError(f"Unsupported cursor version: {cursor_data.get('v')}")
                
                # Extract snapshot time
                as_of_str = cursor_data.get('as_of')
                as_of = datetime.fromisoformat(as_of_str.replace('Z', '+00:00'))
                
                # Extract after tuple for keyset pagination
                after_tuple = cursor_data.get('after')
                
                # Validate filter hash
                current_filters = {
                    'query': query,
                    'product': product,
                    'id': id,
                    'keywords': keywords,
                    'agencies': agencies,
                    'severity': severity,
                    'risk_category': risk_category,
                    'date_from': date_from.isoformat() if date_from else None,
                    'date_to': date_to.isoformat() if date_to else None
                }
                current_hash = hash_filters(current_filters)
                validate_cursor_filters(cursor_data, current_hash)
                
            except ValueError as e:
                logger.warning(f"Invalid cursor: {e}")
                raise
        
        # Determine table (portable check)
        from sqlalchemy import inspect
        inspector = inspect(self.db.bind)
        has_enhanced = inspector.has_table('recalls_enhanced')
        table = "recalls_enhanced" if has_enhanced else "recalls"
        
        # Build base query components
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
            f"{table}.last_updated"
        ]
        
        if has_enhanced:
            select_columns.extend([
                f"{table}.severity",
                f"{table}.risk_category",
                f"{table}.manufacturer",
                f"{table}.model_number",
                f"{table}.upc"
            ])
        
        # Build WHERE conditions
        where_conditions = []
        params = {}
        
        # Snapshot isolation - filter out newer updates
        where_conditions.append(f"COALESCE({table}.last_updated, {table}.recall_date) <= :as_of")
        params['as_of'] = as_of
        
        # Exact ID lookup (highest priority)
        if id:
            where_conditions.append(f"{table}.recall_id = :recall_id")
            params['recall_id'] = id
            # For exact ID, simplified query
            sql = f"""
                SELECT 
                    {', '.join(select_columns)},
                    1.0 as score
                FROM {table}
                WHERE {' AND '.join(where_conditions)}
                LIMIT 1
            """
            return sql, params, as_of, cursor_data
        
        # Apply filters
        if agencies:
            where_conditions.append(f"{table}.source_agency = ANY(:agencies)")
            params['agencies'] = agencies
        
        if severity and has_enhanced:
            where_conditions.append(f"{table}.severity = :severity")
            params['severity'] = severity
        
        if risk_category and has_enhanced:
            where_conditions.append(f"{table}.risk_category = :risk_category")
            params['risk_category'] = risk_category
        
        if date_from:
            where_conditions.append(f"{table}.recall_date >= :date_from")
            params['date_from'] = date_from
        
        if date_to:
            where_conditions.append(f"{table}.recall_date <= :date_to")
            params['date_to'] = date_to
        
        # Text search with fuzzy matching
        text_query = self._normalize_text(product or query or "")
        score_expression = "0.0"
        
        if text_query:
            # Check if pg_trgm is available (Postgres only)
            try:
                # Only check on PostgreSQL
                if self.db.bind.dialect.name == "postgresql":
                    trgm_check = self.db.execute(text(
                        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')"
                    ))
                    has_trgm = trgm_check.scalar()
                else:
                    has_trgm = False
            except:
                has_trgm = False
            
            if has_trgm:
                # Use pg_trgm similarity
                similarity_expressions = [
                    f"similarity(lower({table}.product_name), :search_text)",
                    f"similarity(lower({table}.brand), :search_text)",
                    f"similarity(lower({table}.description), :search_text)",
                    f"similarity(lower({table}.hazard), :search_text)"
                ]
                score_expression = f"GREATEST({', '.join(similarity_expressions)})"
                where_conditions.append(f"{score_expression} >= 0.08")
                params['search_text'] = text_query
            else:
                # Fallback to ILIKE
                search_conditions = [
                    f"lower({table}.product_name) LIKE :search_pattern",
                    f"lower({table}.brand) LIKE :search_pattern",
                    f"lower({table}.description) LIKE :search_pattern",
                    f"lower({table}.hazard) LIKE :search_pattern"
                ]
                where_conditions.append(f"({' OR '.join(search_conditions)})")
                params['search_pattern'] = f"%{text_query}%"
                # Simple relevance based on exact match
                score_expression = f"""
                    CASE 
                        WHEN lower({table}.product_name) = :search_text THEN 1.0
                        WHEN lower({table}.brand) = :search_text THEN 0.9
                        WHEN lower({table}.product_name) LIKE :search_start THEN 0.8
                        WHEN lower({table}.brand) LIKE :search_start THEN 0.7
                        ELSE 0.5
                    END
                """
                params['search_start'] = f"{text_query}%"
        
        # Keyword AND logic
        if keywords:
            normalized_keywords = [k.strip().lower() for k in keywords if k and k.strip()]
            for i, keyword in enumerate(normalized_keywords):
                keyword_conditions = [
                    f"lower({table}.product_name) LIKE :keyword_{i}",
                    f"lower({table}.brand) LIKE :keyword_{i}",
                    f"lower({table}.description) LIKE :keyword_{i}",
                    f"lower({table}.hazard) LIKE :keyword_{i}"
                ]
                where_conditions.append(f"({' OR '.join(keyword_conditions)})")
                params[f'keyword_{i}'] = f"%{keyword}%"
        
        # Keyset pagination conditions
        if after_tuple:
            last_score, last_date, last_id = after_tuple
            
            # Build keyset conditions for deterministic ordering
            # Order: score DESC, recall_date DESC, recall_id ASC
            keyset_conditions = f"""
                ({score_expression} < :last_score
                 OR ({score_expression} = :last_score AND {table}.recall_date < :last_date)
                 OR ({score_expression} = :last_score AND {table}.recall_date = :last_date AND {table}.recall_id > :last_id))
            """
            where_conditions.append(keyset_conditions)
            params['last_score'] = last_score
            params['last_date'] = last_date
            params['last_id'] = last_id
        
        # Build final query
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Deterministic ordering
        order_by = [
            f"{score_expression} DESC",
            f"{table}.recall_date DESC NULLS LAST",
            f"{table}.recall_id ASC"
        ]
        
        # Fetch one extra to detect if there's a next page
        sql = f"""
            SELECT 
                {', '.join(select_columns)},
                {score_expression} as score
            FROM {table}
            WHERE {where_clause}
            ORDER BY {', '.join(order_by)}
            LIMIT :limit
        """
        
        params['limit'] = limit + 1  # Fetch one extra
        
        return sql, params, as_of, cursor_data
    
    def search_with_cursor(
        self,
        query: Optional[str] = None,
        product: Optional[str] = None,
        id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        agencies: Optional[List[str]] = None,
        severity: Optional[str] = None,
        risk_category: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 20,
        next_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute search with cursor-based pagination
        """
        try:
            # Build query
            sql_query, params, as_of, cursor_data = self.build_keyset_query(
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
                cursor_token=next_cursor
            )
            
            # Execute query
            result = self.db.execute(text(sql_query), params)
            rows = result.fetchall()
            
            # Check if there's a next page
            has_more = len(rows) > limit
            page_rows = rows[:limit] if has_more else rows
            
            # Format results
            items = []
            for row in page_rows:
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
                    "lastUpdated": row.last_updated.isoformat() if row.last_updated else None
                }
                
                # Add score if available
                if hasattr(row, 'score'):
                    item["relevanceScore"] = round(float(row.score), 3)
                
                # Add optional fields
                if hasattr(row, 'severity') and row.severity:
                    item["severity"] = row.severity
                if hasattr(row, 'risk_category') and row.risk_category:
                    item["riskCategory"] = row.risk_category
                if hasattr(row, 'manufacturer') and row.manufacturer:
                    item["manufacturer"] = row.manufacturer
                if hasattr(row, 'model_number') and row.model_number:
                    item["modelNumber"] = row.model_number
                if hasattr(row, 'upc') and row.upc:
                    item["upc"] = row.upc
                
                items.append(item)
            
            # Generate next cursor if needed
            next_cursor_token = None
            if has_more and page_rows:
                last_row = page_rows[-1]
                
                # Create filter hash for cursor validation
                filters = {
                    'query': query,
                    'product': product,
                    'id': id,
                    'keywords': keywords,
                    'agencies': agencies,
                    'severity': severity,
                    'risk_category': risk_category,
                    'date_from': date_from.isoformat() if date_from else None,
                    'date_to': date_to.isoformat() if date_to else None
                }
                filters_hash = hash_filters(filters)
                
                # Create cursor for next page
                after_tuple = (
                    float(last_row.score) if hasattr(last_row, 'score') else 0.0,
                    last_row.recall_date,
                    last_row.id
                )
                
                next_cursor_token = create_search_cursor(
                    filters_hash=filters_hash,
                    as_of=as_of,
                    limit=limit,
                    after_tuple=after_tuple
                )
            
            return {
                "ok": True,
                "data": {
                    "items": items,
                    "total": len(items),  # Note: exact total requires separate count query
                    "limit": limit,
                    "nextCursor": next_cursor_token,
                    "asOf": as_of.isoformat().replace('+00:00', 'Z')
                }
            }
            
        except ValueError as e:
            # Cursor validation errors
            logger.error(f"Cursor error: {e}")
            error_code = "INVALID_CURSOR"
            if "don't match" in str(e):
                error_code = "INVALID_CURSOR_FILTER_MISMATCH"
            
            return {
                "ok": False,
                "error": {
                    "code": error_code,
                    "message": str(e)
                },
                "data": {
                    "items": [],
                    "total": 0
                }
            }
        except Exception as e:
            logger.error(f"Search error: {e}", exc_info=True)
            return {
                "ok": False,
                "error": {
                    "code": "SEARCH_ERROR",
                    "message": str(e)
                },
                "data": {
                    "items": [],
                    "total": 0
                }
            }
