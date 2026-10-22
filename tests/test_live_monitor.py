"""Camera discovery and monitor failure behavior with mocked OpenCV capture."""
from src.live_monitor import discover_cameras, LiveMonitor


class Capture:
    def __init__(self, index, backend): self.index = index
    def isOpened(self): return self.index == 1
    def read(self): return (self.index == 1, object() if self.index == 1 else None)
    def release(self): pass


def test_camera_discovery_reports_only_opening_indexes(monkeypatch):
    monkeypatch.setattr("src.live_monitor.cv2.VideoCapture", Capture)
    assert discover_cameras(3) == [{"camera_index": 1, "camera_id": "camera_01", "status": "available"}]


def test_failed_camera_sets_offline_and_does_not_crash_worker(tmp_path):
    class Cfg:
        camera_index = 0; camera_id = "cam"; pole_id = "pole"; pole_name = "Pole"
        pole_location = ""; evidence_dir = tmp_path; event_cooldown_seconds = 5
    class Logger:
        def __init__(self): self.online = []
        def update_pole_heartbeat(self, pole, **kwargs): self.online.append(kwargs["online"])
    class BadCapture(Capture):
        def isOpened(self): return False
    logger = Logger()
    monitor = LiveMonitor(Cfg(), None, logger, None, capture_factory=BadCapture)
    monitor.start()
    monitor._thread.join(timeout=1)
    status = monitor.status()
    assert not status["connected"] and not status["running"]
    assert "could not be opened" in status["error"]
    assert logger.online == [False]
