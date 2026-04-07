---
name: python-testing-patterns
description: Implement comprehensive testing strategies with pytest, fixtures, mocking, and test-driven development. Use when writing Python tests, setting up test suites, or implementing testing best practices.
---

# Python Testing Patterns

Comprehensive guide to implementing robust testing strategies in Python using pytest, fixtures, mocking, and parameterization.

## When to Use This Skill

- Writing unit tests for Python code
- Setting up test suites and infrastructure
- Implementing TDD workflows
- Mocking external dependencies
- Testing async code
- CI/CD integration

## Quick Start

```python
# test_example.py
def test_add():
    assert 2 + 3 == 5

# Run: pytest test_example.py -v
```

## Core Patterns

### Pattern 1: Basic pytest

```python
import pytest

class Calculator:
    def add(self, a: float, b: float) -> float: return a + b
    def divide(self, a: float, b: float) -> float:
        if b == 0: raise ValueError("Cannot divide by zero")
        return a / b

def test_addition():
    calc = Calculator()
    assert calc.add(2, 3) == 5
    assert calc.add(-1, 1) == 0

def test_division_by_zero():
    calc = Calculator()
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        calc.divide(5, 0)
```

### Pattern 2: Fixtures

```python
from typing import Generator

@pytest.fixture
def db() -> Generator[Database, None, None]:
    database = Database("sqlite:///:memory:")
    database.connect()
    yield database
    database.disconnect()

@pytest.fixture(scope="session")
def app_config():
    return {"database_url": "postgresql://localhost/test", "debug": True}

def test_database_query(db):
    results = db.query("SELECT * FROM users")
    assert len(results) > 0
```

### Pattern 3: Parameterized Tests

```python
@pytest.mark.parametrize("email,expected", [
    ("user@example.com", True),
    ("invalid.email", False),
    ("@example.com", False),
    ("", False),
])
def test_email_validation(email, expected):
    assert is_valid_email(email) == expected

# Custom test IDs
@pytest.mark.parametrize("value,expected", [
    pytest.param(1, True, id="positive"),
    pytest.param(0, False, id="zero"),
    pytest.param(-1, False, id="negative"),
])
def test_is_positive(value, expected):
    assert (value > 0) == expected
```

### Pattern 4: Mocking

```python
from unittest.mock import Mock, patch
import requests

class APIClient:
    def __init__(self, base_url: str): self.base_url = base_url
    def get_user(self, user_id: int) -> dict:
        response = requests.get(f"{self.base_url}/users/{user_id}")
        response.raise_for_status()
        return response.json()

def test_get_user_success():
    client = APIClient("https://api.example.com")
    mock_response = Mock()
    mock_response.json.return_value = {"id": 1, "name": "John"}
    mock_response.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_response) as mock_get:
        user = client.get_user(1)
        assert user["id"] == 1
        mock_get.assert_called_once_with("https://api.example.com/users/1")

def test_get_user_not_found():
    client = APIClient("https://api.example.com")
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404")

    with patch("requests.get", return_value=mock_response):
        with pytest.raises(requests.HTTPError):
            client.get_user(999)
```

### Pattern 5: Retry Testing

```python
def test_retries_on_transient_error():
    client = Mock()
    client.request.side_effect = [
        ConnectionError("Failed"),
        ConnectionError("Failed"),
        {"status": "ok"},
    ]
    service = ServiceWithRetry(client, max_retries=3)
    result = service.fetch()
    assert result == {"status": "ok"}
    assert client.request.call_count == 3

def test_gives_up_after_max_retries():
    client = Mock()
    client.request.side_effect = ConnectionError("Failed")
    service = ServiceWithRetry(client, max_retries=3)
    with pytest.raises(ConnectionError):
        service.fetch()
    assert client.request.call_count == 3
```

### Pattern 6: Time Control (freezegun)

```python
from freezegun import freeze_time
from datetime import datetime

@freeze_time("2026-01-15 10:00:00")
def test_token_expiry():
    token = create_token(expires_in_seconds=3600)
    assert token.expires_at == datetime(2026, 1, 15, 11, 0, 0)

@freeze_time("2026-01-15 12:00:00")
def test_is_expired():
    token = Token(expires_at=datetime(2026, 1, 15, 11, 30, 0))
    assert token.is_expired()
```

### Pattern 7: Test Markers

```python
@pytest.mark.slow
def test_slow_operation(): ...

@pytest.mark.integration
def test_database_integration(): ...

@pytest.mark.skip(reason="Feature not implemented yet")
def test_future_feature(): ...

@pytest.mark.xfail(reason="Known bug #123")
def test_known_bug(): assert False

# Run: pytest -m "not slow"
# Run: pytest -m integration
```

## Project Structure

```
tests/
  __init__.py
  conftest.py           # Shared fixtures
  unit/
    test_models.py
    test_utils.py
  integration/
    test_api.py
    test_database.py
```

## Naming Convention

```python
# test_<unit>_<scenario>_<expected_outcome>
def test_create_user_with_valid_data_returns_user(): ...
def test_create_user_with_duplicate_email_raises_conflict(): ...
def test_get_user_with_unknown_id_returns_none(): ...
```

## Coverage

```bash
pip install pytest-cov
pytest --cov=myapp --cov-report=html tests/
pytest --cov=myapp --cov-fail-under=80 tests/
pytest --cov=myapp --cov-report=term-missing tests/
```

## Best Practices

1. **One behavior per test** — focused, easy to diagnose
2. **Test error paths** — not just happy paths
3. **Use fixtures for setup/teardown** — not setUp/tearDown
4. **Parameterize similar tests** — avoid duplication
5. **Mock at the boundary** — not deep inside implementation
6. **Keep tests fast** — mark slow tests explicitly
7. **Use descriptive names** — test name is documentation
8. **Design for idempotency** — tests safe to rerun
