# conftest.py — suppress pytest collection warnings for framework classes
collect_ignore_glob = []


def pytest_configure(config):
    config.addinivalue_line(
        "filterwarnings",
        "ignore::pytest.PytestCollectionWarning",
    )
