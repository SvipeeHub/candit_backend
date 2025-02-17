# middleware.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from typing import List, Optional
from urllib.parse import urlparse

class StaticFilesDomainMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, 
        app,
        allowed_domains: List[str],
        protected_paths: List[str] = ["/uploads/"],
        allow_direct_access: bool = False
    ):
        super().__init__(app)
        self.allowed_domains = allowed_domains
        self.protected_paths = protected_paths
        self.allow_direct_access = allow_direct_access

    async def dispatch(self, request: Request, call_next):
        # Check if the request is for protected static files
        if any(request.url.path.startswith(path) for path in self.protected_paths):
            referer = request.headers.get("referer")
            
            # If direct access is not allowed and there's no referer
            if not self.allow_direct_access and not referer:
                raise HTTPException(status_code=403, detail="Direct access not allowed")
            
            # Check referer domain if it exists
            if referer:
                referer_domain = urlparse(referer).netloc
                if not any(domain in referer_domain for domain in self.allowed_domains):
                    raise HTTPException(
                        status_code=403,
                        detail="Access not allowed from this domain"
                    )
        
        response = await call_next(request)
        return response

