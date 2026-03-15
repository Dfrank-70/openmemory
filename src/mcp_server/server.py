from __future__ import annotations

import uvicorn
from fastmcp import FastMCP
from fastmcp.server.auth import AccessToken, TokenVerifier

from src.config.settings import get_logger, get_settings
from src.mcp_server.tools import get_context_tool, get_project_tool, search_tool

settings = get_settings()
logger = get_logger("mcp_server")


class StaticTokenVerifier(TokenVerifier):
    def __init__(self, expected_token: str):
        super().__init__()
        self.expected_token = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if token != self.expected_token:
            return None
        return AccessToken(token=token, client_id="open-memory-client", scopes=[])


auth = StaticTokenVerifier(settings.auth_token) if settings.auth_token else None
mcp = FastMCP(f"Open Memory ({settings.profile})", auth=auth)


@mcp.tool(name="search")
def search(query: str, scope: str = "all", type: str = "all", limit: int = 10) -> list[dict]:
    return search_tool(query=query, scope=scope, item_type=type, limit=limit)


@mcp.tool(name="get_project")
def get_project(name: str) -> str:
    return get_project_tool(name)


@mcp.tool(name="get_context")
def get_context(scope: str = "all") -> str:
    return get_context_tool(scope)


app = mcp.http_app(path="/mcp", stateless_http=True)


if __name__ == "__main__":
    logger.info("starting_mcp_server host=%s port=%s profile=%s", settings.mcp_host, settings.mcp_port, settings.profile)
    uvicorn.run(app, host=settings.mcp_host, port=settings.mcp_port)
