#!/usr/bin/env python3.9
from __future__ import annotations

import asyncio

import services


async def main() -> int:
    exit_code = 0

    try:
        await services.connect_services()

        # do stuff here

        await services.disconnect_services()
    except KeyboardInterrupt:
        exit_code = 0
    except:
        exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
