from fastapi import Response

from app.config import Settings


def set_auth_cookies(
    response: Response,
    *,
    session_token: str,
    csrf_token: str,
    settings: Settings,
) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_idle_seconds,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.session_idle_seconds,
        path="/",
    )


def clear_auth_cookies(response: Response, settings: Settings) -> None:
    if "set-cookie" in response.headers:
        del response.headers["set-cookie"]
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
