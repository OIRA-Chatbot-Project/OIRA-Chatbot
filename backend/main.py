from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from database import init_db
from models import HealthResponse

# Import route modules
from routes import users, sessions, messages, chat, feedback, schedule, admin

# Initialize FastAPI app
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    init_db()
    print("Database initialized successfully")


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        version=config.API_VERSION
    )


# Include all routers
app.include_router(users.router)
app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(schedule.router)
app.include_router(admin.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
