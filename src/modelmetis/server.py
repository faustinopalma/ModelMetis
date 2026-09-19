import os

import uvicorn

from modelmetis.settings import Settings


def main() -> None:
    Settings.from_environment()
    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535.")
    uvicorn.run("modelmetis.api:app", host="127.0.0.1", port=port, proxy_headers=False)


if __name__ == "__main__":
    main()