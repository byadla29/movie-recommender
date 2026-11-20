"""Who is calling? Verify the identity provider's token on every protected request.

How it works (step 2.3):
1. The browser signs in with Clerk. Clerk gives it a short-lived token (a JWT).
2. The Next.js server (BFF) forwards that token: `Authorization: Bearer <token>`.
3. This module checks the token *by itself*, using Clerk's PUBLIC key:
   - signature  -> it really came from the issuer and nobody changed a single character
   - alg        -> only RS256 is accepted (blocks "alg: none" and algorithm-swap tricks)
   - iss        -> issued by OUR identity provider, not some other one
   - exp / nbf  -> not expired, not "valid from" in the future
   - sub        -> present: this is the user's ID we key all their data on (decision D3)
   - aud / azp  -> optional: meant for us / requested by our frontend
4. Any failure -> 401. The caller learns only "invalid token"; the exact reason is logged
   for us (never the token itself).

Why not just trust a `user_id` the frontend sends? Anyone can send any user_id. A signed
token can only be produced by whoever holds the issuer's PRIVATE key, which never leaves
the identity provider.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from user_service.settings import get_settings

logger = logging.getLogger(__name__)

ALLOWED_ALGORITHMS = ["RS256"]
REQUIRED_CLAIMS = ["exp", "iat", "iss", "sub"]
MAX_TOKEN_LENGTH = 8192  # real tokens are ~1 KB; refuse absurd input before parsing it

# Looks up the public key that matches the token's "kid" (key id) header.
SigningKeyResolver = Callable[[str], Any]


@dataclass(frozen=True)
class AuthenticatedUser:
    """The verified caller. `sub` is the only identity user-service trusts."""

    sub: str
    session_id: str | None = None


class InvalidTokenError(Exception):
    """Token is missing, malformed, forged, expired or not meant for us -> 401."""


class AuthUnavailableError(Exception):
    """We can't check tokens right now (keys unreachable / not configured) -> 503."""


class TokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        resolve_signing_key: SigningKeyResolver,
        audience: str | None = None,
        authorized_parties: list[str] | None = None,
        clock_skew_seconds: int = 5,
    ) -> None:
        self._issuer = issuer
        self._resolve_signing_key = resolve_signing_key
        self._audience = audience
        self._authorized_parties = authorized_parties or []
        self._leeway = clock_skew_seconds

    def verify(self, token: str) -> AuthenticatedUser:
        if not token or len(token) > MAX_TOKEN_LENGTH:
            raise InvalidTokenError("missing or oversized token")
        try:
            key = self._resolve_signing_key(token)
        except jwt.PyJWKClientConnectionError as exc:
            raise AuthUnavailableError("signing keys unreachable") from exc
        except (jwt.PyJWKClientError, jwt.DecodeError) as exc:
            raise InvalidTokenError(f"no matching signing key ({type(exc).__name__})") from exc

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=ALLOWED_ALGORITHMS,
                issuer=self._issuer,
                audience=self._audience,
                leeway=self._leeway,
                options={
                    "require": REQUIRED_CLAIMS,
                    # Check "aud" only when we configured an expected audience.
                    "verify_aud": self._audience is not None,
                },
            )
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError(type(exc).__name__) from exc

        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub or len(sub) > 255:
            raise InvalidTokenError("unusable sub claim")
        if self._authorized_parties and claims.get("azp") not in self._authorized_parties:
            raise InvalidTokenError("azp not allowed")
        session_id = claims.get("sid")
        return AuthenticatedUser(
            sub=sub, session_id=session_id if isinstance(session_id, str) else None
        )


def jwks_key_resolver(jwks_url: str, timeout_seconds: float) -> SigningKeyResolver:
    """Fetch the issuer's public keys over HTTPS and cache them.

    PyJWKClient caches the key set (5 min) and re-fetches when it sees an unknown "kid",
    which is how key rotation at the provider keeps working without a restart.
    """
    client = jwt.PyJWKClient(jwks_url, cache_keys=True, timeout=timeout_seconds)

    def resolve(token: str) -> Any:
        return client.get_signing_key_from_jwt(token).key

    return resolve


@lru_cache
def _verifier_from_settings() -> TokenVerifier | None:
    settings = get_settings()
    jwks_url = settings.resolved_jwks_url
    if settings.auth_issuer is None or jwks_url is None:
        return None
    return TokenVerifier(
        issuer=settings.auth_issuer,
        resolve_signing_key=jwks_key_resolver(jwks_url, settings.auth_jwks_timeout_seconds),
        audience=settings.auth_audience,
        authorized_parties=settings.auth_authorized_parties,
        clock_skew_seconds=settings.auth_clock_skew_seconds,
    )


def get_token_verifier() -> TokenVerifier:
    """FastAPI dependency. Tests override it with a verifier that trusts a test key."""
    verifier = _verifier_from_settings()
    if verifier is None:
        logger.error("authentication not configured: set AUTH_ISSUER")
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    return verifier


# auto_error=False: we produce our own problem+json 401 instead of FastAPI's default 403.
# Using HTTPBearer also documents the "bearer token" requirement in the OpenAPI contract.
_bearer = HTTPBearer(auto_error=False, description="Identity provider session token (JWT)")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> AuthenticatedUser:
    """FastAPI dependency for every protected route: returns the verified caller or 401s."""
    if credentials is None:
        # RFC 6750: no credentials at all -> challenge without an error code.
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verifier.verify(credentials.credentials)
    except InvalidTokenError as exc:
        logger.info("token rejected", extra={"reason": str(exc)})
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        ) from exc
    except AuthUnavailableError as exc:
        logger.warning("cannot verify tokens", extra={"reason": str(exc)})
        raise HTTPException(
            status_code=503,
            detail="Cannot verify credentials right now",
            headers={"Retry-After": "5"},
        ) from exc


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
