from unittest.mock import MagicMock, patch

import pytest

from app.tasks.process_sla_escalations import main


def test_sla_escalation_task_success():
    mock_db = MagicMock()

    with (
        patch(
            "app.tasks.process_sla_escalations.SessionLocal",
            return_value=mock_db,
        ),
        patch(
            "app.tasks.process_sla_escalations.process_sla_escalations",
            return_value=3,
        ) as mock_process,
    ):
        main()

    mock_process.assert_called_once_with(db=mock_db)
    mock_db.close.assert_called_once()


def test_sla_escalation_task_closes_session_on_failure():
    mock_db = MagicMock()

    with (
        patch(
            "app.tasks.process_sla_escalations.SessionLocal",
            return_value=mock_db,
        ),
        patch(
            "app.tasks.process_sla_escalations.process_sla_escalations",
            side_effect=RuntimeError("Database processing failed"),
        ),pytest.raises(
        RuntimeError,
        match="Database processing failed",
    )
    ):
        main()

    mock_db.close.assert_called_once()
