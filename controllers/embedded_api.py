"""Run the existing HTTP application inside a Streamlit worker, without a server."""

import anyio
import httpx2


class EmbeddedApiClient:
    def __init__(self, app):
        self._app = app

    def request(self, method, path, **kwargs):
        async def dispatch():
            transport = httpx2.ASGITransport(app=self._app, raise_app_exceptions=False)
            async with httpx2.AsyncClient(
                transport=transport, base_url="http://roomflow.internal", trust_env=False,
            ) as client:
                return await client.request(method, path, **kwargs)

        return anyio.run(dispatch)

    def close(self):
        # Each dispatch owns and closes its client; the SQLAlchemy pool is shared.
        pass
