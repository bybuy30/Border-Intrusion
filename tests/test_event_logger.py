"""Mongo event persistence contracts tested with an in-memory collection mock."""
from pathlib import Path
import pytest
from src.event_logger import EventLogger


class Cursor(list):
    def sort(self, key, direction=1):
        super().sort(key=lambda d: d.get(key), reverse=direction < 0)
        return self
    def limit(self, n): return Cursor(self[:n])


class Collection:
    def __init__(self): self.docs = []
    def create_index(self, *args, **kwargs): pass
    def insert_one(self, doc): self.docs.append(dict(doc))
    def insert_many(self, docs, ordered=True): self.docs.extend(dict(d) for d in docs)
    def find(self, query=None): return Cursor([d for d in self.docs if self.matches(d, query or {})])
    def find_one(self, query): return next(iter(self.find(query)), None)
    def count_documents(self, query): return len(self.find(query))
    def aggregate(self, pipeline):
        counts = {}
        for d in self.docs: counts[d.get("class_name")] = counts.get(d.get("class_name"), 0) + 1
        return [{"_id": k, "count": v} for k, v in counts.items()]
    def update_one(self, query, update, upsert=False):
        doc = self.find_one(query)
        if doc is None:
            if upsert:
                doc = dict(query); doc.update(update.get("$set", {})); self.docs.append(doc)
                return type("Result", (), {"matched_count": 0})()
            return type("Result", (), {"matched_count": 0})()
        doc.update(update.get("$set", {}))
        return type("Result", (), {"matched_count": 1})()
    @staticmethod
    def matches(doc, query):
        for key, expected in query.items():
            actual = doc.get(key)
            if isinstance(expected, dict):
                if "$in" in expected and actual not in expected["$in"]: return False
                if "$gte" in expected and (actual is None or actual < expected["$gte"]): return False
                if "$lte" in expected and (actual is None or actual > expected["$lte"]): return False
            elif actual != expected: return False
        return True


class Database:
    def __init__(self): self.collections = {}
    def __getitem__(self, key): return self.collections.setdefault(key, Collection())


@pytest.fixture
def logger(tmp_path: Path):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    return EventLogger(Database(), evidence)


def create(logger, cls="person", **kwargs):
    return logger.log_event(class_name=cls, confidence=.72, camera_id="cam1", pole_id="pole1", **kwargs)


def test_event_insert_retrieve_and_priority_filter(logger):
    event_id = create(logger, alert_priority="high", bbox=(1, 2, 3, 4))
    event = logger.get_event(event_id)
    assert event["class_name"] == "person" and event["bbox"] == [1, 2, 3, 4]
    assert logger.get_high_priority_events()[0]["event_id"] == event_id
    assert logger.count_by_class() == {"person": 1}


def test_filters_and_review_updates(logger):
    event_id = create(logger)
    assert len(logger.query_events(pole_id="pole1", class_name="person")) == 1
    assert logger.update_review_status(event_id, "reviewed", "operator checked")
    assert logger.get_event(event_id)["operator_notes"] == "operator checked"
    assert not logger.update_review_status("missing", "reviewed")
    with pytest.raises(ValueError): logger.update_review_status(event_id, "unknown")


def test_path_safety_and_six_image_metadata(logger, tmp_path):
    with pytest.raises(ValueError, match="outside the allowed"):
        create(logger, evidence_path=tmp_path / "outside.jpg")
    event_id = create(logger)
    directory = logger.evidence_dir / event_id
    directory.mkdir()
    paths = []
    for i in range(6):
        path = directory / f"{i+1:02}.jpg"; path.write_bytes(b"jpeg")
        paths.append(path)
    logger.add_event_images(event_id, paths)
    images = logger.get_event_images(event_id)
    assert [x["sequence"] for x in images] == [1, 2, 3, 4, 5, 6]
    assert all(x["mime_type"] == "image/jpeg" and x["size_bytes"] == 4 for x in images)
    assert logger.get_event(event_id)["image_count"] == 6
    with pytest.raises(ValueError, match="Exactly six"):
        logger.add_event_images(event_id, paths[:5])


def test_pole_heartbeat_does_not_infer_online_from_database(logger):
    logger.update_pole_heartbeat("pole1", camera_id="cam1", online=True, pole_name="North")
    pole = logger.get_poles()[0]
    assert pole["status"] == "online" and pole["last_heartbeat"]
    logger.update_pole_heartbeat("pole1", camera_id="cam1", online=False)
    assert logger.get_poles()[0]["status"] == "offline"


def test_missing_uri_is_clear_and_never_falls_back_to_sqlite(tmp_path):
    with pytest.raises(RuntimeError, match="MONGODB_URI"):
        EventLogger(evidence_dir=tmp_path / "evidence", uri="")
