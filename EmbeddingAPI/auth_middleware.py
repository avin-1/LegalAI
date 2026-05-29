"""
JWT validation middleware for Flask microservices.

The API Gateway performs the phantom-token swap and forwards requests to
downstream services with a short-lived JWT in the Authorization header.
This module provides a `jwt_required` decorator that validates that JWT
and injects the claims into Flask's `g` object.

Usage:
    from auth_middleware import jwt_required

    @app.route('/protected')
    @jwt_required
    def protected():
        user = g.user_claims  # {"sub": "...", "username": "...", "roles": [...]}
        ...
"""

import os
import functools
from flask import request, jsonify, g
import jwt  # PyJWT


def _get_secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is not set")
    return secret


def jwt_required(f):
    """Decorator that validates the JWT forwarded by the API Gateway."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "missing Authorization Bearer header"}), 401

        token = auth_header[len("Bearer "):]
        try:
            claims = jwt.decode(
                token,
                _get_secret(),
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "token has expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"invalid token: {e}"}), 401

        g.user_claims = claims
        return f(*args, **kwargs)

    return decorated
