from contextlib import asynccontextmanager
from typing import Annotated

from configs.database import engine, get_db
from configs.env import settings
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    # http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# import models
from routers import posts, users
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import selectinload
# from starlette.exceptions import HTTPException as StarletteHTTPException
from scalar_fastapi import add_scalar_reference

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(lifespan=lifespan)

add_scalar_reference(app)

# app.mount("/static", StaticFiles(directory="static"), name="static")

# templates = Jinja2Templates(directory="templates")

app.include_router(users.router, prefix="/api/users", tags=["users"])
# app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


# @app.middleware("http")
# async def add_security_headers(request: Request, call_next):
#     response = await call_next(request)

#     response.headers["X-Frame-Options"] = "SAMEORIGIN"

#     response.headers["X-Content-Type-Options"] = "nosniff"

#     if "Referrer-Policy" not in response.headers:
#         response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

#     if request.url.hostname not in ("localhost", "127.0.0.1"):
#         response.headers["Strict-Transport-Security"] = (
#             "max-age=63072000; includeSubDomains"
#         )

#     return response


@app.get("/health")
async def health_check(db: Annotated[AsyncSession, Depends(get_db)]):
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "healthy"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
