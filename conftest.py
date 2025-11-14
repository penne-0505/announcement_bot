"""Pytest用の最小asyncサポートプラグイン。"""
from __future__ import annotations

import asyncio
import inspect

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """asyncテストを同期テストと同様に実行できるようにする。"""
    test_func = pyfuncitem.obj
    marker = pyfuncitem.get_closest_marker("asyncio")
    if marker is None and not inspect.iscoroutinefunction(test_func):
        return None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_func(**pyfuncitem.funcargs))
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            asyncio.set_event_loop(None)
            loop.close()
    return True


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "asyncio: マーカーが付与されたasyncテストをイベントループ上で実行する",
    )
