from __future__ import annotations

from binance_bot.services.runtime import build_runtime, run_loop


def run() -> None:
    runtime = build_runtime()
    run_loop(runtime)


if __name__ == "__main__":
    run()