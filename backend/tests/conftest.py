import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast unit tests, no external services")
    config.addinivalue_line("markers", "evals: RAG evaluation tests, slower and use LLM/API tokens")
