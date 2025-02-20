from fastapi import FastAPI
from contextlib import asynccontextmanager
import ngrok
from os import getenv
from . import models
from .database import engine,Base
from .routers import users,auths,schools,post,memories,friends,danks,chating
from app.models import Otp_model,Post_model,School_model,User_model,Friendship_model,Post_restriction_model,Danks_model,Chat_model,Message_model
from fastapi.staticfiles import StaticFiles
from app.middleware.postVisiblity_middleware import StaticFilesDomainMiddleware
from app.routers import chating

Base.metadata.create_all(bind=engine)
NGROK_AUTH_TOKEN = getenv("NGROK_AUTHTOKEN", "")
NGROK_EDGE = getenv("NGROK_EDGE", "edge:edghts_")
APPLICATION_PORT = 5000

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Setting up Ngrok Tunnel")
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    ngrok.forward(
        addr=APPLICATION_PORT,
        labels=NGROK_EDGE,
        proto="labeled",
    )
    yield
    print("Tearing Down Ngrok Tunnel")
    ngrok.disconnect()

app = FastAPI()
manager = chating.ConnectionManager()
app.include_router(users.router)
app.include_router(auths.router)
app.include_router(schools.router)
app.include_router(post.router)
app.include_router(memories.router)
app.include_router(friends.router)
app.include_router(danks.router)
app.include_router(chating.router)


# app.include_router(comments.router)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
# app.add_middleware(
#     StaticFilesDomainMiddleware,
#     allowed_domains=["127.0.0.1:8000"],
#     protected_paths=["/uploads/"]
# )

@app.get("/")
def read_root():
    return {"message": "Welcome to the API"}