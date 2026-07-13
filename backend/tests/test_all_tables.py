from sqlalchemy import inspect
from sqlalchemy.orm import Session


def test_all_core_tables_are_created(db_session: Session) -> None:
    expected = {
        "inspections",
        "review_tasks",
        "feedback_samples",
        "dataset_versions",
        "model_versions",
        "data_quality_reports",
        "audit_logs",
    }

    assert expected.issubset(set(inspect(db_session.get_bind()).get_table_names()))
