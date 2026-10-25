from backend.graph import graph

def test_requires_review():
    result = graph.invoke({"job_id": "test", "campaign": "Demo", "source_url": "https://example.com", "approved": False})
    assert result["status"] == "awaiting_approval"

def test_approval_does_not_publish():
    result = graph.invoke({"job_id": "test", "campaign": "Demo", "source_url": "https://example.com", "approved": True})
    assert result["status"] == "approved_for_future_processing"
