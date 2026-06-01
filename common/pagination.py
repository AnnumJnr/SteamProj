"""
Custom pagination classes.
StandardResultsPagination is set as the default in REST_FRAMEWORK settings.
"""

from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    """
    Default pagination for all list endpoints.
    Returns 20 results per page.
    Clients can override page size up to a maximum of 100.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class LargeResultsPagination(PageNumberPagination):
    """
    Used for endpoints that may legitimately return more results,
    such as course listings with many filters applied.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200