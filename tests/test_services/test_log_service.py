from app.services.log_service import LogService

ENTRY = "2026-11-19T17:00:00Z INFO app.ml.predictor: Model loaded"


def test_recent_entries_reads_the_tail(tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("\n".join([ENTRY, "2026-11-19T17:00:01Z WARNING app.test: cuidado"]) + "\n", encoding="utf-8")

    entries = LogService(log_file).recent_entries(limit=1)

    assert entries == [
        {
            "timestamp": "2026-11-19T17:00:01Z",
            "level": "WARNING",
            "logger": "app.test",
            "message": "cuidado",
        }
    ]


def test_recent_entries_returns_empty_for_a_missing_file(tmp_path):
    assert LogService(tmp_path / "missing.log").recent_entries() == []
