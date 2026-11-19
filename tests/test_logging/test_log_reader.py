from app.core.log_reader import MAX_LIMIT, read_last_entries, tail_lines


def _write(path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _line(number, level="INFO"):
    return f"2026-11-19T17:00:{number % 60:02d}Z {level} app.test: mensaje {number}"


def test_missing_file_returns_empty_list(tmp_path):
    assert read_last_entries(tmp_path / "no-existe.log") == []


def test_returns_last_entries_oldest_first(tmp_path):
    log_file = tmp_path / "app.log"
    _write(log_file, [_line(n) for n in range(3000)])
    entries = read_last_entries(log_file, limit=3)
    assert [e["message"] for e in entries] == ["mensaje 2997", "mensaje 2998", "mensaje 2999"]
    assert entries[0] == {"timestamp": "2026-11-19T17:00:57Z", "level": "INFO", "logger": "app.test", "message": "mensaje 2997"}


def test_tail_reads_across_chunks(tmp_path):
    log_file = tmp_path / "app.log"
    _write(log_file, [_line(n) for n in range(5000)])
    assert tail_lines(log_file, 1000) == [_line(n) for n in range(4000, 5000)]


def test_limit_is_clamped(tmp_path):
    log_file = tmp_path / "app.log"
    _write(log_file, [_line(n) for n in range(MAX_LIMIT + 100)])
    assert len(read_last_entries(log_file, limit=10_000)) == MAX_LIMIT
    assert read_last_entries(log_file, limit=0) == []
    assert read_last_entries(log_file, limit=-5) == []


def test_traceback_lines_join_the_previous_entry(tmp_path):
    log_file = tmp_path / "app.log"
    _write(log_file, [_line(1), _line(2, "ERROR"), "Traceback (most recent call last):", "ValueError: x"])
    entries = read_last_entries(log_file, limit=10)
    assert len(entries) == 2
    assert entries[-1]["level"] == "ERROR"
    assert entries[-1]["message"].endswith("Traceback (most recent call last):\nValueError: x")


def test_invalid_utf8_does_not_fail(tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_bytes(_line(1).encode() + b"\n\xff\xfe basura\n")
    assert len(read_last_entries(log_file)) == 1


def test_long_traceback_keeps_its_header_line(tmp_path):
    log_file = tmp_path / "app.log"
    traceback = [f"  File \"x.py\", line {n}" for n in range(30)]
    _write(log_file, [_line(1), _line(2, "ERROR"), *traceback, _line(3)])
    entries = read_last_entries(log_file, limit=2)
    assert [e["level"] for e in entries] == ["ERROR", "INFO"]
    assert entries[0]["message"].startswith("mensaje 2\n")
    assert entries[0]["message"].count("\n") == 30


def test_partial_entry_at_window_start_is_dropped(tmp_path):
    # limit=3 -> first window of 12 lines starts inside the traceback (10 detail lines + 2 INFO).
    log_file = tmp_path / "app.log"
    _write(log_file, [_line(0, "ERROR"), *[f"  detalle {n}" for n in range(20)], _line(1), _line(2)])
    entries = read_last_entries(log_file, limit=3)
    assert [entry["level"] for entry in entries] == ["ERROR", "INFO", "INFO"]
    assert entries[0]["message"].startswith("mensaje 0\n  detalle 0")
