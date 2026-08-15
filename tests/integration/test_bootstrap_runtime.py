from tms.bootstrap import bootstrap


def test_bootstrap_and_runtime_lifecycle_without_eager_telegram_connect(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    context = bootstrap()
    assert context.commands is not None
    assert context.clients._clients == {}
    context.runtime.start()
    try:
        assert context.runtime.network.thread_id is not None
        assert context.runtime.db_writer.thread_id is not None
    finally:
        context.runtime.stop()
