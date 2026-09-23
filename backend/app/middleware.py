import uuid
import anyio
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.errors import APIError, error_body
from app.services.rate_limit import check_limit

class SafetyMiddleware:
    def __init__(self, app, factory, settings):
        self.app, self.factory, self.settings = app, factory, settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def secured_send(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([(b"x-request-id", request_id.encode()),
                    (b"x-content-type-options", b"nosniff"), (b"referrer-policy", b"no-referrer")])
                if scope["path"].startswith("/api"):
                    headers.append((b"cache-control", b"no-store"))
                message["headers"] = headers
            await send(message)

        if not scope["path"].startswith("/api") or scope["method"] == "OPTIONS":
            return await self.app(scope, receive, secured_send)
        try:
            client = scope.get("client") or ("unknown", 0)
            await anyio.to_thread.run_sync(check_limit, self.factory, self.settings.secret_key,
                "request:" + client[0], self.settings.request_limit_per_minute, 60)
            header_map = dict(scope.get("headers", []))
            content_length = header_map.get(b"content-length")
            if content_length is not None:
                try:
                    length = int(content_length)
                except ValueError:
                    raise APIError(400, "INVALID_CONTENT_LENGTH", "잘못된 요청입니다.")
                if length < 0 or length > self.settings.max_request_bytes:
                    raise APIError(413, "REQUEST_TOO_LARGE", "요청 본문이 너무 큽니다.")
            chunks, size = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > self.settings.max_request_bytes:
                    raise APIError(413, "REQUEST_TOO_LARGE", "요청 본문이 너무 큽니다.")
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            delivered = False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type":"http.request", "body":b"".join(chunks), "more_body":False}
                return await receive()
            return await self.app(scope, replay, secured_send)
        except APIError as exc:
            response = JSONResponse(error_body(exc.code, exc.message, request_id), status_code=exc.status,
                                    headers=exc.headers)
            return await response(scope, receive, secured_send)
