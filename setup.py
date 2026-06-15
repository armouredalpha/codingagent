"""Thin shim so `pip install -e .` works on older toolchains.
Configuration lives in pyproject.toml."""
from setuptools import setup

if __name__ == "__main__":
    setup()
