from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: str
    password: str
    display_name: str


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    created_at: str
    last_sync_at: str | None = None

    model_config = {"from_attributes": True}
