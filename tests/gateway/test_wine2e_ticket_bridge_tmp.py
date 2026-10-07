

def _stress(tmp_path, accept, rounds=80):
    import time
    import gateway.runtime_bootstrap_windows as rbw
    tmp_path.mkdir()
    original = rbw._accept
    rbw._accept = accept
    server = rbw.NativeControlServer(tmp_path, lambda raw, subject: b'{"ok": true}\n')
    server.start()
    failures = []
    try:
        for i in range(rounds):
            # Land each connect near the server's 0.5 s idle-accept boundary.
            time.sleep(0.5 - 0.002 * (i % 10))
            try:
                rbw.query_runtime_control(tmp_path, b"hello", 5)
            except Exception as exc:
                failures.append(repr(exc))
    finally:
        server.close()
        rbw._accept = original
    return failures


def test_native_pipe_accept_boundary_stress_ab(tmp_path):
    import pytest
    if os.name != "nt":
        pytest.skip("native named pipe")
    import time
    import gateway.runtime_bootstrap_windows as rbw

    def old_accept(handle, budget):  # pre-fix: a connect that lands during cancel is dropped
        ov = rbw._native().ConnectNamedPipe(handle, overlapped=True)
        rbw._complete(ov, time.monotonic() + budget)
        return True

    old = _stress(tmp_path / "old", old_accept)
    new = _stress(tmp_path / "new", rbw._accept)
    receipt = json.dumps({"old_failures": len(old), "new_failures": len(new), "old": old[:3], "new": new[:3]})
    artifacts = Path(os.environ.get("UGW_ARTIFACT_DIR", str(tmp_path)))
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "pipe-accept-ab.json").write_text(receipt, encoding="utf-8")
    assert new == [], new
