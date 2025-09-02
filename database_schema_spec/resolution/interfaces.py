from typing import Any, Protocol


class IJSONRefResolver(Protocol):
    def resolve_references(
        self, schema: dict[str, Any], current_file: str | None = None
    ) -> dict[str, Any]: ...
