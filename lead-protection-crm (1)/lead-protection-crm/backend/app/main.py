from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1 import auth, workspaces, users, companies, contacts, opportunities, custom_fields, leads, integrations, webhooks
from app.jobs.scheduler import start_scheduler, shutdown_scheduler

from sqlalchemy import text

def ensure_schema_compatibility():
    """Ensure any newly added columns in models are present in existing SQLite/Postgres databases."""
    try:
        with engine.connect() as conn:
            if engine.dialect.name == "sqlite":
                res = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                cols = [r[1] for r in res]
                if cols and "last_assigned_at" not in cols:
                    conn.execute(text("ALTER TABLE users ADD COLUMN last_assigned_at DATETIME"))
                    conn.commit()
            elif engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_assigned_at TIMESTAMP WITHOUT TIME ZONE"))
                conn.commit()
    except Exception as e:
        pass

# Create all database tables and start database-backed job scheduler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist and schema is up to date
    Base.metadata.create_all(bind=engine)
    ensure_schema_compatibility()
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Multi-tenant Lead Protection CRM with strict tenant isolation and timed escalations.",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for hackathon dev/demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(workspaces.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(companies.router, prefix=settings.API_V1_STR)
app.include_router(contacts.router, prefix=settings.API_V1_STR)
app.include_router(opportunities.router, prefix=settings.API_V1_STR)
app.include_router(custom_fields.router, prefix=settings.API_V1_STR)
app.include_router(leads.router, prefix=settings.API_V1_STR)
app.include_router(integrations.router, prefix=settings.API_V1_STR)
app.include_router(webhooks.router, prefix=settings.API_V1_STR)

@app.get("/health")
@app.get("/api/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
