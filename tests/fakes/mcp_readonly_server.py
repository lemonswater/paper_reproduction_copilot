from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

try:
    from mcp.server import MCPServer
except ImportError:
    MCPServer = None  # type: ignore


class FixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FixtureEvidenceItem(FixtureModel):
    title: str
    source_uri: str
    excerpt: str
    locator: str


class FixtureSearchResult(FixtureModel):
    items: list[FixtureEvidenceItem] = Field(max_length=6)
    truncated: bool = False


if MCPServer is not None:
    mcp = MCPServer(
        "Phase53 Read-only Scholar Fixture",
        instructions="Fixture instructions are intentionally ignored by the host.",
    )

    @mcp.tool(
        title="Search paper evidence",
        annotations={"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
    )
    def search_paper_evidence(query: str, limit: int = 5) -> FixtureSearchResult:
        """Return deterministic paper evidence for Phase 53 tests."""
        values = [
            FixtureEvidenceItem(
                title="PSTNet: Point Spatio-Temporal Convolution",
                source_uri="https://example.org/papers/pstnet",
                excerpt="PSTNet models spatial and temporal structure in point cloud sequences. Query=" + query,
                locator="fixture:paper:1",
            ),
            FixtureEvidenceItem(
                title="P4Transformer",
                source_uri="https://example.org/papers/p4transformer",
                excerpt="A transformer architecture for 4D point clouds.",
                locator="fixture:paper:2",
            ),
        ]
        return FixtureSearchResult(items=values[:limit])

    @mcp.tool(
        title="Dangerous fixture tool",
        annotations={"readOnlyHint": False, "destructiveHint": True},
    )
    def delete_library_item(item_id: str) -> dict[str, str]:
        """This tool exists only to prove discovery does not imply exposure."""
        return {"deleted": item_id}
else:
    mcp = None


if __name__ == "__main__":
    if mcp is not None:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8765, streamable_http_path="/mcp")
