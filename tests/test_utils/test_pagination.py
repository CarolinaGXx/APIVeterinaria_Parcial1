"""
Tests for pagination utilities.

Tests cover:
- Pagination metadata calculation
- Paginated response creation
- Skip/offset calculation
- Edge cases
"""

import pytest
from datetime import datetime

from core.pagination import (
    calculate_pagination_meta,
    create_paginated_response,
    calculate_skip,
    PaginationMeta,
    PaginationParams
)


class TestPaginationMetaCalculation:
    """Tests for pagination metadata calculation."""
    
    def test_calculate_pagination_meta_primera_pagina(self):
        """Test pagination metadata for first page."""
        meta = calculate_pagination_meta(
            page=0,
            page_size=10,
            total_items=50
        )
        
        assert meta.page == 0
        assert meta.page_size == 10
        assert meta.total_items == 50
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_previous is False
    
    def test_calculate_pagination_meta_pagina_intermedia(self):
        """Test pagination metadata for middle page."""
        meta = calculate_pagination_meta(
            page=2,
            page_size=10,
            total_items=50
        )
        
        assert meta.page == 2
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_previous is True
    
    def test_calculate_pagination_meta_ultima_pagina(self):
        """Test pagination metadata for last page."""
        meta = calculate_pagination_meta(
            page=4,
            page_size=10,
            total_items=50
        )
        
        assert meta.page == 4
        assert meta.total_pages == 5
        assert meta.has_next is False
        assert meta.has_previous is True
    
    def test_calculate_pagination_meta_items_parciales(self):
        """Test pagination with partial last page."""
        meta = calculate_pagination_meta(
            page=0,
            page_size=10,
            total_items=25
        )
        
        # 25 items with page_size 10 = 3 pages (10, 10, 5)
        assert meta.total_pages == 3
        assert meta.has_next is True
    
    def test_calculate_pagination_meta_sin_items(self):
        """Test pagination with no items."""
        meta = calculate_pagination_meta(
            page=0,
            page_size=10,
            total_items=0
        )
        
        assert meta.total_pages == 0
        assert meta.has_next is False
        assert meta.has_previous is False
    
    def test_calculate_pagination_meta_items_exactos(self):
        """Test pagination when items exactly fill pages."""
        meta = calculate_pagination_meta(
            page=0,
            page_size=10,
            total_items=100
        )
        
        # Exactly 10 pages
        assert meta.total_pages == 10
    
    def test_calculate_pagination_meta_menos_items_que_page_size(self):
        """Test pagination when total items less than page size."""
        meta = calculate_pagination_meta(
            page=0,
            page_size=10,
            total_items=5
        )
        
        assert meta.total_pages == 1
        assert meta.has_next is False
        assert meta.has_previous is False


class TestPaginatedResponseCreation:
    """Tests for creating paginated responses."""
    
    def test_create_paginated_response_estructura(self):
        """Test paginated response has correct structure."""
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        response = create_paginated_response(
            items=items,
            page=0,
            page_size=10,
            total_items=50
        )
        
        # Verify top-level structure
        assert "success" in response
        assert "data" in response
        assert "pagination" in response
        assert "timestamp" in response
        
        assert response["success"] is True
        assert response["data"] == items
        assert isinstance(response["timestamp"], datetime)
    
    def test_create_paginated_response_pagination_data(self):
        """Test paginated response contains correct pagination data."""
        items = [{"id": i} for i in range(10)]
        
        response = create_paginated_response(
            items=items,
            page=1,
            page_size=10,
            total_items=50
        )
        
        pagination = response["pagination"]
        
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["total_items"] == 50
        assert pagination["total_pages"] == 5
        assert pagination["has_next"] is True
        assert pagination["has_previous"] is True
    
    def test_create_paginated_response_lista_vacia(self):
        """Test paginated response with empty list."""
        response = create_paginated_response(
            items=[],
            page=0,
            page_size=10,
            total_items=0
        )
        
        assert response["data"] == []
        assert response["pagination"]["total_items"] == 0
        assert response["pagination"]["total_pages"] == 0
    
    def test_create_paginated_response_timestamp_reciente(self):
        """Test paginated response has recent timestamp."""
        before = datetime.utcnow()
        
        response = create_paginated_response(
            items=[{"id": 1}],
            page=0,
            page_size=10,
            total_items=1
        )
        
        after = datetime.utcnow()
        timestamp = response["timestamp"]
        
        # Timestamp should be between before and after
        assert before <= timestamp <= after


class TestSkipCalculation:
    """Tests for skip/offset calculation."""
    
    def test_calculate_skip_primera_pagina(self):
        """Test skip for first page is 0."""
        skip = calculate_skip(page=0, page_size=10)
        
        assert skip == 0
    
    def test_calculate_skip_segunda_pagina(self):
        """Test skip for second page."""
        skip = calculate_skip(page=1, page_size=10)
        
        assert skip == 10
    
    def test_calculate_skip_tercera_pagina(self):
        """Test skip for third page."""
        skip = calculate_skip(page=2, page_size=10)
        
        assert skip == 20
    
    def test_calculate_skip_diferentes_page_sizes(self):
        """Test skip calculation with different page sizes."""
        # Page 2, page_size 25
        skip = calculate_skip(page=2, page_size=25)
        assert skip == 50
        
        # Page 5, page_size 100
        skip = calculate_skip(page=5, page_size=100)
        assert skip == 500
    
    def test_calculate_skip_page_size_uno(self):
        """Test skip with page size of 1."""
        skip = calculate_skip(page=10, page_size=1)
        
        assert skip == 10


class TestPaginationParams:
    """Tests for PaginationParams model."""
    
    def test_pagination_params_valores_default(self):
        """Test PaginationParams has correct default values."""
        params = PaginationParams()
        
        assert params.page == 0
        assert params.page_size == 50
    
    def test_pagination_params_custom_values(self):
        """Test PaginationParams with custom values."""
        params = PaginationParams(page=2, page_size=25)
        
        assert params.page == 2
        assert params.page_size == 25
    
    def test_pagination_params_validacion_page_negativo(self):
        """Test PaginationParams rejects negative page."""
        with pytest.raises(ValueError):
            PaginationParams(page=-1, page_size=10)
    
    def test_pagination_params_validacion_page_size_cero(self):
        """Test PaginationParams rejects zero page size."""
        with pytest.raises(ValueError):
            PaginationParams(page=0, page_size=0)
    
    def test_pagination_params_validacion_page_size_muy_grande(self):
        """Test PaginationParams rejects page size > 100."""
        with pytest.raises(ValueError):
            PaginationParams(page=0, page_size=101)


class TestPaginationMeta:
    """Tests for PaginationMeta model."""
    
    def test_pagination_meta_creation(self):
        """Test creating PaginationMeta instance."""
        meta = PaginationMeta(
            page=0,
            page_size=10,
            total_items=50,
            total_pages=5,
            has_next=True,
            has_previous=False
        )
        
        assert meta.page == 0
        assert meta.page_size == 10
        assert meta.total_items == 50
        assert meta.total_pages == 5
        assert meta.has_next is True
        assert meta.has_previous is False
    
    def test_pagination_meta_serialization(self):
        """Test PaginationMeta can be serialized."""
        meta = PaginationMeta(
            page=1,
            page_size=20,
            total_items=100,
            total_pages=5,
            has_next=True,
            has_previous=True
        )
        
        dict_meta = meta.model_dump()
        
        assert isinstance(dict_meta, dict)
        assert dict_meta["page"] == 1
        assert dict_meta["page_size"] == 20
        assert dict_meta["total_items"] == 100


class TestPaginationEdgeCases:
    """Tests for pagination edge cases."""
    
    def test_pagination_un_solo_item(self):
        """Test pagination with only one item."""
        meta = calculate_pagination_meta(
            page=0,
            page_size=10,
            total_items=1
        )
        
        assert meta.total_pages == 1
        assert meta.has_next is False
        assert meta.has_previous is False
    
    def test_pagination_page_size_mayor_que_total(self):
        """Test pagination when page size is larger than total items."""
        meta = calculate_pagination_meta(
            page=0,
            page_size=100,
            total_items=10
        )
        
        assert meta.total_pages == 1
        assert meta.has_next is False
    
    def test_pagination_pagina_fuera_de_rango(self):
        """Test pagination with page number beyond available pages."""
        # Page 10 but only 5 pages exist
        meta = calculate_pagination_meta(
            page=10,
            page_size=10,
            total_items=50
        )
        
        # Should calculate correctly even if page is out of range
        assert meta.total_pages == 5
        assert meta.has_next is False
        # has_previous is True because page > 0
        assert meta.has_previous is True
    
    def test_pagination_muchos_items(self):
        """Test pagination with large number of items."""
        meta = calculate_pagination_meta(
            page=50,
            page_size=100,
            total_items=10000
        )
        
        assert meta.total_pages == 100
        assert meta.has_next is True
        assert meta.has_previous is True
    
    def test_skip_calculation_limites(self):
        """Test skip calculation at boundaries."""
        # First page
        assert calculate_skip(0, 50) == 0
        
        # Last page (theoretically)
        assert calculate_skip(99, 100) == 9900
        
        # Large numbers
        assert calculate_skip(1000, 100) == 100000
