from unittest.mock import Mock

import pytest

from app.core.exceptions import DomainError
from app.services.auth_service import authenticate


def test_missing_session_rejected_without_database_access():
    db = Mock()
    with pytest.raises(DomainError) as error:
        authenticate(db, None)
    assert error.value.status == 401
    assert error.value.code == "UNAUTHENTICATED"
    assert db.mock_calls == []
