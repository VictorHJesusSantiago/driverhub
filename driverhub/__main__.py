# -*- coding: utf-8 -*-
"""Entrypoint: python -m driverhub ..."""
import sys

from .cli import run

if __name__ == "__main__":
    sys.exit(run())