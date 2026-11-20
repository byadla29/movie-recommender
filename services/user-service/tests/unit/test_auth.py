"""Token verification tests. No Clerk account and no network to the internet needed.

We play the identity provider ourselves: generate an RSA key pair, sign tokens with the
private key, and give the verifier only the public key. Then we try every way a token can
be wrong and check that each one is refused.
"""

import hashlib
import hmac
import json
import logging
import threading
import time
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from user_service.auth import (
    AuthenticatedUser,
    AuthUnavailableError,
    CurrentUser,
    InvalidTokenError,
    TokenVerifier,
    get_token_verifier,
    jwks_key_resolver,
)

ISSUER = "https://issuer.test.example"
KID = "test-key-1"

# Generating RSA keys takes a moment, so do it once for the whole file.
PROVIDER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
ATTACKER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(
    *,
    key: rsa.RSAPrivateKey = PROVIDER_KEY,
    kid: str = KID,
    drop: tuple[str, ...] = (),
    **claim_overrides: Any,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "sub": "user_alice",
        "sid": "sess_123",
        "iat": now,
        "nbf": now,
        "exp": now + 60,
    }
    claims.update(claim_overrides)
    for name in drop:
        claims.pop(name)
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": kid})


def make_verifier(**options: Any) -> TokenVerifier:
    public_key = PROVIDER_KEY.public_key()
    return TokenVerifier(issuer=ISSUER, resolve_signing_key=lambda _token: public_key, **options)


@pytest.fixture
def verifier() -> TokenVerifier:
    return make_verifier()


@pytest.fixture
def client(app: FastAPI, verifier: TokenVerifier) -> Iterator[TestClient]:
    """The real app plus one protected test-only route."""

    @app.get("/test/whoami")
    def whoami(user: CurrentUser) -> dict[str, str]:
        return {"sub": user.sub}

    app.dependency_overrides[get_token_verifier] = lambda: verifier
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# --- the happy path ---------------------------------------------------------------------


def test_valid_token_identifies_the_user(client: TestClient) -> None:
    response = client.get("/test/whoami", headers=bearer(make_token()))

    assert response.status_code == 200
    assert response.json() == {"sub": "user_alice"}


def test_verifier_returns_sub_and_session(verifier: TokenVerifier) -> None:
    assert verifier.verify(make_token()) == AuthenticatedUser(
        sub="user_alice", session_id="sess_123"
    )


def test_small_clock_difference_is_tolerated(verifier: TokenVerifier) -> None:
    # Expired 2 s ago, but servers' clocks can differ by a few seconds (leeway = 5 s).
    assert verifier.verify(make_token(exp=int(time.time()) - 2)).sub == "user_alice"


# --- missing credentials ----------------------------------------------------------------


def test_no_token_is_401_with_bearer_challenge(client: TestClient) -> None:
    response = client.get("/test/whoami")

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["www-authenticate"] == "Bearer"


def test_wrong_auth_scheme_is_401(client: TestClient) -> None:
    response = client.get("/test/whoami", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 401


# --- every way a token can be bad ---------------------------------------------------------


def _tampered() -> str:
    """Take a valid token and change the user inside it, keeping the old signature."""
    original = make_token()
    header, _payload, signature = original.split(".")
    claims = jwt.decode(original, options={"verify_signature": False})
    claims["sub"] = "user_mallory"
    forged_payload = jwt.utils.base64url_encode(json.dumps(claims).encode()).decode()
    return f"{header}.{forged_payload}.{signature}"


def _alg_none() -> str:
    """An unsigned token claiming 'no signature needed'."""
    return jwt.encode({"iss": ISSUER, "sub": "user_mallory"}, key=None, algorithm="none")


def _alg_hs256_with_public_key() -> str:
    """Classic attack: the public key is public, so an attacker uses it as an HMAC secret.

    A verifier that lets the TOKEN choose the algorithm would check this HMAC with the
    same public key and accept it. Ours only ever allows RS256.
    """
    public_pem = PROVIDER_KEY.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    b64 = jwt.utils.base64url_encode
    now = int(time.time())
    header = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    claims = {"iss": ISSUER, "sub": "user_mallory", "iat": now, "exp": now + 60}
    payload = b64(json.dumps(claims).encode())
    signing_input = header + b"." + payload
    signature = b64(hmac.new(public_pem, signing_input, hashlib.sha256).digest())
    return (signing_input + b"." + signature).decode()


BAD_TOKENS: dict[str, Callable[[], str]] = {
    "not a JWT at all": lambda: "not-a-jwt",
    "signed by someone else's key": lambda: make_token(key=ATTACKER_KEY),
    "payload changed after signing": _tampered,
    "alg none (unsigned)": _alg_none,
    "alg HS256 confusion": _alg_hs256_with_public_key,
    "expired": lambda: make_token(exp=int(time.time()) - 60),
    "not valid yet": lambda: make_token(nbf=int(time.time()) + 60),
    "issued by another provider": lambda: make_token(iss="https://evil.example"),
    "no subject": lambda: make_token(drop=("sub",)),
    "no expiry": lambda: make_token(drop=("exp",)),
    "empty subject": lambda: make_token(sub=""),
    "oversized": lambda: "a" * 10_000,
}


@pytest.mark.parametrize("case", BAD_TOKENS)
def test_bad_token_is_rejected_by_verifier(verifier: TokenVerifier, case: str) -> None:
    with pytest.raises(InvalidTokenError):
        verifier.verify(BAD_TOKENS[case]())


@pytest.mark.parametrize("case", BAD_TOKENS)
def test_bad_token_gets_401_problem(client: TestClient, case: str) -> None:
    response = client.get("/test/whoami", headers=bearer(BAD_TOKENS[case]()))

    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["www-authenticate"] == 'Bearer error="invalid_token"'
    # One generic message for every case: don't teach an attacker which check failed.
    assert response.json()["detail"] == "Invalid or expired token"


def test_token_is_never_written_to_logs(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    token = make_token(exp=int(time.time()) - 60)
    with caplog.at_level(logging.DEBUG):
        client.get("/test/whoami", headers=bearer(token))

    # Look at whole records, including extra fields like "reason" that end up in the JSON.
    logged = "\n".join(str(vars(record)) for record in caplog.records)
    assert any(getattr(r, "reason", None) == "ExpiredSignatureError" for r in caplog.records)
    assert token not in logged
    assert token.split(".")[2] not in logged  # not even the signature part


# --- optional audience / authorized-party checks -------------------------------------------


def test_audience_checked_when_configured() -> None:
    verifier = make_verifier(audience="movie-reco-api")

    assert verifier.verify(make_token(aud="movie-reco-api")).sub == "user_alice"
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(aud="some-other-api"))
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token())  # aud missing


def test_authorized_party_checked_when_configured() -> None:
    verifier = make_verifier(authorized_parties=["http://127.0.0.1:3000"])

    assert verifier.verify(make_token(azp="http://127.0.0.1:3000")).sub == "user_alice"
    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(azp="https://evil.example"))


# --- when tokens can't be checked at all -> 503, not 401 ------------------------------------


def test_auth_not_configured_is_503(app: FastAPI) -> None:
    @app.get("/test/whoami")
    def whoami(user: CurrentUser) -> dict[str, str]:
        return {"sub": user.sub}

    with TestClient(app) as test_client:  # no override, and AUTH_ISSUER is not set
        response = test_client.get("/test/whoami", headers=bearer(make_token()))

    assert response.status_code == 503
    assert response.json()["detail"] == "Authentication is not configured"


def test_keys_unreachable_is_503_with_retry_after(app: FastAPI) -> None:
    def unreachable(_token: str) -> Any:
        raise jwt.PyJWKClientConnectionError("connection refused")

    @app.get("/test/whoami")
    def whoami(user: CurrentUser) -> dict[str, str]:
        return {"sub": user.sub}

    app.dependency_overrides[get_token_verifier] = lambda: TokenVerifier(
        issuer=ISSUER, resolve_signing_key=unreachable
    )
    with TestClient(app) as test_client:
        response = test_client.get("/test/whoami", headers=bearer(make_token()))

    # The token may be perfectly fine; WE can't check it. Telling the user "you're logged
    # out" (401) would be wrong, so this is "try again shortly" (503).
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"


# --- the real JWKS key lookup, against a tiny local key server -----------------------------


@pytest.fixture
def jwks_url() -> Iterator[str]:
    jwk = RSAAlgorithm.to_jwk(PROVIDER_KEY.public_key(), as_dict=True)
    body = json.dumps({"keys": [{**jwk, "kid": KID, "use": "sig", "alg": "RS256"}]}).encode()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:  # keep test output quiet
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)  # port 0 = any free port
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/.well-known/jwks.json"
    server.shutdown()


def test_jwks_resolver_finds_key_by_kid(jwks_url: str) -> None:
    verifier = TokenVerifier(issuer=ISSUER, resolve_signing_key=jwks_key_resolver(jwks_url, 2))

    assert verifier.verify(make_token()).sub == "user_alice"


def test_jwks_resolver_rejects_unknown_kid(jwks_url: str) -> None:
    verifier = TokenVerifier(issuer=ISSUER, resolve_signing_key=jwks_key_resolver(jwks_url, 2))

    with pytest.raises(InvalidTokenError):
        verifier.verify(make_token(kid="key-we-never-published"))


def test_jwks_resolver_unreachable_is_unavailable_not_invalid() -> None:
    resolver = jwks_key_resolver("http://127.0.0.1:1/.well-known/jwks.json", 1)
    verifier = TokenVerifier(issuer=ISSUER, resolve_signing_key=resolver)

    with pytest.raises(AuthUnavailableError):
        verifier.verify(make_token())
