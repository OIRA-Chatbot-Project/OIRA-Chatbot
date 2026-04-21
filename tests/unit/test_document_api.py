from __future__ import annotations

import asyncio

from fastapi import HTTPException
from fastapi.routing import APIRoute

from src.api_endpoints.document import (
    DOCUMENT_API_DISABLED_MESSAGE,
    delete_all_documents,
    delete_document,
    download_document,
    list_documents,
    upload_catalog,
)
from src.api_endpoints.schemas import CatalogUploadRequest
from src.main import app


def test_document_routes_are_registered() -> None:
    route_map: dict[tuple[str, str], APIRoute] = {}
    for route in app.router.routes:
        if isinstance(route, APIRoute):
            for method in route.methods:
                route_map[(route.path, method)] = route

    expected_routes = {
        ("/api/document/upload", "POST"),
        ("/api/document/download/{document_id}", "GET"),
        ("/api/document/list/{user_id}", "GET"),
        ("/api/document/delete/{document_id}", "DELETE"),
        ("/api/document/delete_all/{user_id}", "DELETE"),
    }
    assert expected_routes.issubset(set(route_map.keys()))


def _assert_raises_501(coro) -> None:
    try:
        asyncio.run(coro)
        raise AssertionError("Expected HTTPException(501) but no exception was raised.")
    except HTTPException as exc:
        assert exc.status_code == 501
        assert exc.detail == DOCUMENT_API_DISABLED_MESSAGE


def test_document_endpoints_raise_consistent_501() -> None:
    _assert_raises_501(
        upload_catalog(
            CatalogUploadRequest(
                user_id="student-1",
                catalog_version_id="2026-2027",
                file_name="catalog.pdf",
                content_type="application/pdf",
                raw_text="sample",
            )
        )
    )
    _assert_raises_501(download_document("doc-1"))
    _assert_raises_501(list_documents("student-1"))
    _assert_raises_501(delete_document("doc-1"))
    _assert_raises_501(delete_all_documents("student-1"))
