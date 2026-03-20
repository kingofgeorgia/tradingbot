from __future__ import annotations

import sys

from binance_bot.services.repair import acknowledge_issue, inspect_runtime_issues, repair_symbol_state, unblock_symbol
from binance_bot.services.runtime import build_runtime, reconcile_startup, run_loop


def run(argv: list[str] | None = None) -> None:
    arguments = argv if argv is not None else sys.argv[1:]
    runtime = build_runtime()

    if arguments:
        _run_operator_command(runtime, arguments)
        return

    reconcile_startup(runtime)
    run_loop(runtime)


def _run_operator_command(runtime, arguments: list[str]) -> None:
    state = runtime.state_store.load()
    command = arguments[0]

    if command == "inspect":
        as_json = len(arguments) >= 2 and arguments[1] == "--json"
        print(inspect_runtime_issues(settings=runtime.settings, client=runtime.client, state=state, as_json=as_json))
        return
    if command == "acknowledge" and len(arguments) >= 2:
        print(
            acknowledge_issue(
                symbol=arguments[1],
                state=state,
                state_store=runtime.state_store,
                repair_journal=runtime.repair_journal,
                loggers=runtime.loggers,
                settings=runtime.settings,
            )
        )
        return
    if command == "repair" and len(arguments) >= 3:
        print(
            repair_symbol_state(
                settings=runtime.settings,
                client=runtime.client,
                state=state,
                state_store=runtime.state_store,
                order_manager=runtime.order_manager,
                repair_journal=runtime.repair_journal,
                loggers=runtime.loggers,
                symbol=arguments[1],
                action=arguments[2],
            )
        )
        return
    if command == "unblock" and len(arguments) >= 2:
        print(
            unblock_symbol(
                settings=runtime.settings,
                client=runtime.client,
                state=state,
                state_store=runtime.state_store,
                repair_journal=runtime.repair_journal,
                loggers=runtime.loggers,
                symbol=arguments[1],
            )
        )
        return

    print("Unsupported command. Use: inspect [--json] | acknowledge <SYMBOL> | repair <SYMBOL> <ACTION> | unblock <SYMBOL>")


if __name__ == "__main__":
    run()