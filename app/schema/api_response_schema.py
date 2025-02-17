from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class ApiResponse(BaseModel):
    status: str
    status_code: int
    message: Optional[str] = None
    data: Optional[List[dict]] = None
    total: Optional[int] = None
    page: Optional[int] = None
    pages: Optional[int] = None

    class Config:
        from_attributes = True

    def calculate_pages(self, total: int, limit: int) -> int:
        if total and limit:
            return (total + limit - 1) // limit
        return 0

    def model_dump(self) -> dict:
        return {
            "status": self.status,
            "status_code": self.status_code,
            "message": self.message,
            "data": self.data,
            "total": self.total,
            "page": self.page,
            "pages": self.pages
        }