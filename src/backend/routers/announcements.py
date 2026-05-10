"""Announcement endpoints for the High School Management System API."""

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


class AnnouncementCreate(BaseModel):
    """Payload for creating a new announcement."""

    title: str = Field(..., min_length=1, max_length=120)
    message: str = Field(..., min_length=1, max_length=500)
    start_date: Optional[str] = None
    expiration_date: str

    @field_validator("title", "message", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Value must be a string")

        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Value cannot be empty")

        return trimmed

    @field_validator("start_date", "expiration_date")
    @classmethod
    def validate_date_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        try:
            date.fromisoformat(value)
            return value
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD format") from exc


class AnnouncementUpdate(BaseModel):
    """Payload for updating an announcement."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    message: Optional[str] = Field(default=None, min_length=1, max_length=500)
    start_date: Optional[str] = None
    expiration_date: Optional[str] = None

    @field_validator("title", "message", mode="before")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        if not isinstance(value, str):
            raise ValueError("Value must be a string")

        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Value cannot be empty")

        return trimmed

    @field_validator("start_date", "expiration_date")
    @classmethod
    def validate_optional_date_format(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value

        try:
            date.fromisoformat(value)
            return value
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD format") from exc


def _assert_signed_in(teacher_username: Optional[str]) -> Dict[str, Any]:
    """Validate that the request includes a known signed-in user."""
    if not teacher_username:
        raise HTTPException(status_code=401, detail="Authentication required")

    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Invalid user session")

    return teacher


def _normalize_announcement(document: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize MongoDB announcement shape for API responses."""
    return {
        "id": str(document.get("_id")),
        "title": document.get("title", ""),
        "message": document.get("message", ""),
        "start_date": document.get("start_date"),
        "expiration_date": document.get("expiration_date")
    }


def _is_active(start_date: Optional[str], expiration_date: str) -> bool:
    """Check if announcement is active for the current date."""
    today = date.today().isoformat()

    if start_date and start_date > today:
        return False

    return expiration_date >= today


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get currently active announcements for public display."""
    results: List[Dict[str, Any]] = []

    for announcement in announcements_collection.find({}, {"_id": 1, "title": 1, "message": 1, "start_date": 1, "expiration_date": 1}):
        normalized = _normalize_announcement(announcement)
        expiration_date = normalized.get("expiration_date")

        if not expiration_date:
            continue

        if _is_active(normalized.get("start_date"), expiration_date):
            results.append(normalized)

    results.sort(key=lambda item: (item.get("start_date") or "", item["expiration_date"], item["title"]))
    return results


@router.get("/manage", response_model=List[Dict[str, Any]])
def list_all_announcements(
    teacher_username: Optional[str] = Query(None)
) -> List[Dict[str, Any]]:
    """List all announcements for authenticated management UI."""
    _assert_signed_in(teacher_username)

    results = [
        _normalize_announcement(doc)
        for doc in announcements_collection.find({}, {"_id": 1, "title": 1, "message": 1, "start_date": 1, "expiration_date": 1})
    ]

    results.sort(key=lambda item: (item["expiration_date"], item.get("start_date") or "", item["title"]))
    return results


@router.post("", response_model=Dict[str, Any])
def create_announcement(
    payload: AnnouncementCreate,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Create an announcement. Expiration date is required."""
    _assert_signed_in(teacher_username)

    if payload.start_date and payload.start_date > payload.expiration_date:
        raise HTTPException(status_code=400, detail="Start date cannot be after expiration date")

    announcement_id = str(uuid4())
    insert_document = {"_id": announcement_id, **payload.model_dump()}
    inserted = announcements_collection.insert_one(insert_document)
    saved = announcements_collection.find_one({"_id": inserted.inserted_id})
    if not saved:
        raise HTTPException(status_code=500, detail="Announcement creation failed")

    return _normalize_announcement(saved)


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    payload: AnnouncementUpdate,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, Any]:
    """Update announcement fields by id."""
    _assert_signed_in(teacher_username)

    existing = announcements_collection.find_one({"_id": announcement_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")

    update_data = payload.model_dump(exclude_unset=True)
    merged_start = update_data.get("start_date", existing.get("start_date"))
    merged_expiration = update_data.get("expiration_date", existing.get("expiration_date"))

    if not merged_expiration:
        raise HTTPException(status_code=400, detail="Expiration date is required")

    if merged_start and merged_start > merged_expiration:
        raise HTTPException(status_code=400, detail="Start date cannot be after expiration date")

    if update_data:
        announcements_collection.update_one({"_id": announcement_id}, {"$set": update_data})

    updated = announcements_collection.find_one({"_id": announcement_id})
    if not updated:
        raise HTTPException(status_code=500, detail="Announcement update failed")

    return _normalize_announcement(updated)


@router.delete("/{announcement_id}", response_model=Dict[str, str])
def delete_announcement(
    announcement_id: str,
    teacher_username: Optional[str] = Query(None)
) -> Dict[str, str]:
    """Delete an announcement by id."""
    _assert_signed_in(teacher_username)

    result = announcements_collection.delete_one({"_id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")

    return {"message": "Announcement deleted"}
