"""
Pagination utilities for BabyShield
Prevents memory issues with large datasets
"""

from typing import TypeVar, Generic, List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import Query
from sqlalchemy.orm import Query as SQLQuery

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters"""

    skip: int = Query(0, ge=0, le=10000, description="Number of items to skip")
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return")

    @property
    def offset(self) -> int:
        return self.skip

    @property
    def page(self) -> int:
        """Calculate page number (1-based)"""
        return (self.skip // self.limit) + 1

    def next_params(self) -> Dict[str, int]:
        """Get params for next page"""
        return {"skip": self.skip + self.limit, "limit": self.limit}

    def prev_params(self) -> Optional[Dict[str, int]]:
        """Get params for previous page"""
        if self.skip == 0:
            return None
        prev_skip = max(0, self.skip - self.limit)
        return {"skip": prev_skip, "limit": self.limit}


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""

    items: List[T]
    total: int
    skip: int
    limit: int
    has_next: bool
    has_prev: bool
    page: int
    pages: int

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def create(cls, items: List[T], total: int, params: PaginationParams):
        """Create paginated response"""
        pages = (total + params.limit - 1) // params.limit  # Ceiling division

        return cls(
            items=items,
            total=total,
            skip=params.skip,
            limit=params.limit,
            has_next=params.skip + params.limit < total,
            has_prev=params.skip > 0,
            page=params.page,
            pages=pages,
        )


def paginate_query(query: SQLQuery, params: PaginationParams) -> tuple[List, int]:
    """
    Paginate a SQLAlchemy query
    Returns (items, total_count)
    """
    # Get total count before pagination
    total = query.count()

    # Apply pagination
    items = query.offset(params.skip).limit(params.limit).all()

    return items, total


async def paginate_async(query: SQLQuery, params: PaginationParams) -> PaginatedResponse:
    """
    Async pagination helper
    """
    items, total = paginate_query(query, params)
    return PaginatedResponse.create(items, total, params)


class CursorPaginationParams(BaseModel):
    """
    Cursor-based pagination for better performance
    """

    cursor: Optional[str] = Query(None, description="Cursor for next page")
    limit: int = Query(100, ge=1, le=1000, description="Number of items")

    def decode_cursor(self) -> Optional[int]:
        """Decode cursor to get last ID"""
        if not self.cursor:
            return None
        try:
            import base64

            decoded = base64.b64decode(self.cursor).decode()
            return int(decoded)
        except:
            return None

    @staticmethod
    def encode_cursor(last_id: int) -> str:
        """Encode last ID as cursor"""
        import base64

        return base64.b64encode(str(last_id).encode()).decode()


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """Cursor-based paginated response"""

    items: List[T]
    next_cursor: Optional[str]
    has_next: bool
    limit: int

    class Config:
        arbitrary_types_allowed = True


def paginate_with_cursor(
    query: SQLQuery, params: CursorPaginationParams, id_field: str = "id"
) -> tuple[List, Optional[str]]:
    """
    Cursor-based pagination for large datasets
    More efficient than offset/limit for deep pagination
    """
    # Decode cursor to get starting point
    last_id = params.decode_cursor()

    # Apply cursor filter if provided
    if last_id:
        query = query.filter(getattr(query.column_descriptions[0]["type"], id_field) > last_id)

    # Order by ID for consistent pagination
    query = query.order_by(getattr(query.column_descriptions[0]["type"], id_field))

    # Fetch one extra item to check if there's a next page
    items = query.limit(params.limit + 1).all()

    # Check if there's a next page
    has_next = len(items) > params.limit
    if has_next:
        items = items[:-1]  # Remove the extra item
        last_item_id = getattr(items[-1], id_field)
        next_cursor = CursorPaginationParams.encode_cursor(last_item_id)
    else:
        next_cursor = None

    return items, next_cursor


# Utility functions for common use cases


def paginate_list(items: List[T], params: PaginationParams) -> PaginatedResponse[T]:
    """
    Paginate a Python list
    """
    total = len(items)
    start = params.skip
    end = params.skip + params.limit
    paginated_items = items[start:end]

    return PaginatedResponse.create(paginated_items, total, params)


def create_pagination_links(
    base_url: str, params: PaginationParams, total: int
) -> Dict[str, Optional[str]]:
    """
    Create HATEOAS links for pagination
    """
    links = {
        "self": f"{base_url}?skip={params.skip}&limit={params.limit}",
        "first": f"{base_url}?skip=0&limit={params.limit}",
        "last": None,
        "next": None,
        "prev": None,
    }

    # Calculate last page
    if total > 0:
        last_page_skip = ((total - 1) // params.limit) * params.limit
        links["last"] = f"{base_url}?skip={last_page_skip}&limit={params.limit}"

    # Next link
    if params.skip + params.limit < total:
        links["next"] = f"{base_url}?skip={params.skip + params.limit}&limit={params.limit}"

    # Previous link
    if params.skip > 0:
        prev_skip = max(0, params.skip - params.limit)
        links["prev"] = f"{base_url}?skip={prev_skip}&limit={params.limit}"

    return links


# Decorator for automatic pagination
from functools import wraps
from fastapi import Depends


def paginated(model_class):
    """
    Decorator to automatically paginate endpoint responses
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, params: PaginationParams = Depends(), **kwargs):
            # Call the original function
            query = await func(*args, **kwargs)

            # Paginate the query
            items, total = paginate_query(query, params)

            # Return paginated response
            return PaginatedResponse.create(items, total, params)

        return wrapper

    return decorator
