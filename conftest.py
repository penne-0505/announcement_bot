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

    # pytest-asyncio 等によって同期ラッパに置き換えられている場合は任せる
    if marker is not None and not inspect.iscoroutinefunction(test_func):
        return None

    # pytest-asyncio (strict mode) が提供するランナーが存在する場合は、標準の実行経路に任せる
    if "_function_scoped_runner" in pyfuncitem.funcargs:
        return None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # pytest-asyncio 1.0+ では内部フィクスチャ（event_loop_policy など）が funcargs に混入するため、
    # テスト関数のシグネチャに存在する引数のみに絞って渡す。
    allowed_args = {
        name: value
        for name, value in pyfuncitem.funcargs.items()
        if name in inspect.signature(test_func).parameters
    }
    try:
        loop.run_until_complete(test_func(**allowed_args))
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
