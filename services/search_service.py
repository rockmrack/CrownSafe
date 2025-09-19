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
        offset: int = 0
    ) -> Tuple[str, Dict[str, Any], bool]:
        """
        Build optimized SQL query using pg_trgm for fuzzy search
        
        Returns:
            (sql_query, params, use_scoring)
        """
        
        # Determine which table to use
        table_check = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'recalls_enhanced'
            )
        """)
        has_enhanced = self.db.execute(table_check).scalar()
        
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
            f"{table}.country"
        ]
        
        # Check for additional columns
        if has_enhanced:
            select_columns.extend([
                f"{table}.severity",
                f"{table}.risk_category",
                f"{table}.manufacturer",
                f"{table}.model_number",
                f"{table}.upc"
            ])
        
        # Start building WHERE conditions
        where_conditions = []
        params = {}
        
        # 1. Exact ID lookup (highest priority)
        if id:
            where_conditions.append(f"{table}.recall_id = :recall_id")
            params['recall_id'] = id
            # For exact ID, no scoring needed
            sql = f"""
                SELECT 
                    {', '.join(select_columns)},
                    1.0 as score
                FROM {table}
                WHERE {' AND '.join(where_conditions)}
                LIMIT 1
            """
            return sql, params, False
        
        # 2. Apply filters
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
        
        # 3. Text search with fuzzy matching
        text_query = self._normalize_text(product or query or "")
        use_scoring = False
        score_expression = "0.0"
        
        if text_query:
            use_scoring = True
            # Use pg_trgm similarity for fuzzy matching
            # We'll calculate similarity across multiple fields and take the maximum
            similarity_expressions = [
                f"similarity(lower({table}.product_name), :search_text)",
                f"similarity(lower({table}.brand), :search_text)",
                f"similarity(lower({table}.description), :search_text)",
                f"similarity(lower({table}.hazard), :search_text)"
            ]
            
            # Take the greatest similarity as the score
            score_expression = f"GREATEST({', '.join(similarity_expressions)})"
            
            # Filter to only reasonably similar results (threshold: 0.08)
            where_conditions.append(f"{score_expression} >= 0.08")
            params['search_text'] = text_query
        
        # 4. Keyword AND logic
        if keywords:
            normalized_keywords = [k.strip().lower() for k in keywords if k and k.strip()]
            for i, keyword in enumerate(normalized_keywords):
                # Each keyword must appear in at least one text field
                keyword_conditions = [
                    f"lower({table}.product_name) LIKE :keyword_{i}",
                    f"lower({table}.brand) LIKE :keyword_{i}",
                    f"lower({table}.description) LIKE :keyword_{i}",
                    f"lower({table}.hazard) LIKE :keyword_{i}"
                ]
                where_conditions.append(f"({' OR '.join(keyword_conditions)})")
                params[f'keyword_{i}'] = f"%{keyword}%"
        
        # Build the final query
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Deterministic sorting: score DESC, recall_date DESC, id ASC
        order_by = []
        if use_scoring:
            order_by.append("score DESC")
        order_by.extend([
            f"{table}.recall_date DESC NULLS LAST",
            f"{table}.recall_id ASC"
        ])
        
        sql = f"""
            SELECT 
                {', '.join(select_columns)},
                {score_expression} as score
            FROM {table}
            WHERE {where_clause}
            ORDER BY {', '.join(order_by)}
            LIMIT :limit
            OFFSET :offset
        """
        
        params['limit'] = min(limit, 50)  # Cap at 50
        params['offset'] = offset
        
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
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute search with fuzzy matching and return results
        """
        try:
            # Handle cursor-based pagination
            actual_offset = offset
            if cursor:
                try:
                    import base64
                    import json
                    cursor_data = json.loads(base64.b64decode(cursor).decode())
                    actual_offset = cursor_data.get("offset", 0)
                    logger.info(f"Cursor decoded: offset={actual_offset}, cursor_data={cursor_data}")
                except Exception as e:
                    logger.warning(f"Invalid cursor: {e}, falling back to offset")
                    actual_offset = offset or 0
            elif offset is not None:
                actual_offset = offset
            else:
                actual_offset = 0
            
            logger.info(f"Search parameters: offset={offset}, cursor={cursor}, actual_offset={actual_offset}, limit={limit}")
            
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
                offset=actual_offset
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
                    "country": row.country
                }
                
                # Add score if using scoring
                if use_scoring:
                    item["relevanceScore"] = round(float(row.score), 3)
                
                # Add optional fields if they exist
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
                
                # Create title
                title_parts = []
                if row.brand:
                    title_parts.append(row.brand)
                if row.product_name:
                    title_parts.append(row.product_name)
                item["title"] = " - ".join(title_parts) if title_parts else "Unknown Product"
                
                items.append(item)
            
            # Get total count (without limit)
            count_sql = f"""
                SELECT COUNT(*) as total
                FROM ({sql_query.replace('LIMIT :limit', '').replace('OFFSET :offset', '')}) as subquery
            """
            count_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
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
                    "last_date": last_item.get("recallDate")
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
                    "hasMore": has_more
                }
            }
            
        except Exception as e:
            logger.error(f"Search error: {e}")
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
    
    def get_similarity_threshold(self) -> float:
        """Get current similarity threshold for fuzzy matching"""
        return 0.08  # 8% similarity minimum
    
    def check_pg_trgm_enabled(self) -> bool:
        """Check if pg_trgm extension is enabled"""
        try:
            result = self.db.execute(text(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')"
            ))
            return result.scalar()
        except:
            return False
