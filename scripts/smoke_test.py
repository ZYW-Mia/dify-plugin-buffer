"""Read-only live check. Reads a key from the environment; never prints credentials."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.client import BufferClient, BufferError  # noqa: E402
from common.queries import CHANNELS, ORGANIZATIONS  # noqa: E402


def main():
    key = os.environ.get("BUFFER_API_KEY")
    if not key:
        raise SystemExit(
            "Set BUFFER_API_KEY in your environment before running this read-only test."
        )
    try:
        with BufferClient({"api_key": key}) as client:
            organizations = client.execute(ORGANIZATIONS)["account"]["organizations"]
            print(f"Authenticated. Accessible organizations: {len(organizations)}")
            for organization in organizations:
                channels = client.execute(
                    CHANNELS, {"input": {"organizationId": organization["id"]}}
                )["channels"]
                services = sorted({channel["service"] for channel in channels})
                print(f"Organization {organization['id']}: {len(channels)} channels; {services}")
    except BufferError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
