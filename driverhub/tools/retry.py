# -*- coding: utf-8 -*-
from __future__ import annotations

"""Retry e experimentação de falhas, sem dependências externas."""

import functools
import time
from typing import Any, Callable, Optional, Tuple

_EXCEPTIONS = (Exception,)


def retry(times: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: Optional[Tuple[type, ...]] = None):
    """Decorator que tenta a função `times` vezes com espera exponencial.

    Após esgotar as tentativas, a última exceção é relançada.
    """
    attempts = max(1, int(times or 1))
    wait = max(0.0, float(delay or 0.0))
    factor = max(1.0, float(backoff or 1.0))
    catch = tuple(exceptions) if exceptions else _EXCEPTIONS

    def decorate(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current = wait
            last: Optional[BaseException] = None
            for attempt in range(attempts):
                try:
                    return fn(*args, **kwargs)
                except catch as exc:
                    last = exc
                    if attempt < attempts - 1:
                        time.sleep(current)
                        current *= factor
            if last is not None:
                raise last
            return None

        return wrapper

    return decorate


def experiment(
    fn: Callable[..., Any],
    *args: Any,
    attempts: int = 5,
    delay: float = 0.01,
    **kwargs: Any,
) -> dict:
    """Executa `fn` várias vezes sem nunca lançar; retorna estatísticas."""
    total = max(1, int(attempts or 1))
    results: list = []
    errors: list = []
    start = time.monotonic()
    for _ in range(total):
        try:
            results.append(fn(*args, **kwargs))
        except Exception as exc:
            errors.append(str(exc))
        if delay and delay > 0:
            time.sleep(float(delay))
    elapsed = time.monotonic() - start
    successes = len(results)
    failures = len(errors)
    return {
        "attempts": total,
        "successes": successes,
        "failures": failures,
        "success_rate": round(successes / max(1, total), 4),
        "errors": errors,
        "elapsed": round(elapsed, 4),
        "results": results,
    }