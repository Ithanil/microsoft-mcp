import sys
from .settings import validate_runtime_settings
from .tools import mcp


def main() -> None:
    errors = validate_runtime_settings()
    if errors:
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    mcp.run()


if __name__ == "__main__":
    main()
