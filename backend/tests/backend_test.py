"""DocuSense AI - Backend API tests."""
from __future__ import annotations

import io
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("BACKEND_URL", "https://smart-doc-query-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

TEST_DOC_TEXT_A = (
    "Project Apollo Report - 2024.\n"
    "The Apollo project was led by NASA and successfully landed humans on the Moon in 1969. "
    "The total program cost was approximately 25 billion dollars. The first crewed lunar landing was Apollo 11, "
    "commanded by Neil Armstrong on July 20, 1969. The program ended in 1972 with Apollo 17. "
    "Six successful crewed Moon landings occurred during the program. "
    "The Saturn V rocket was used as the launch vehicle for all crewed Apollo missions.\n"
)

TEST_DOC_TEXT_B = (
    "Project Apollo Critique - 2025.\n"
    "Recent revisionist analysis disputes earlier figures. The Apollo program reportedly cost 28 billion dollars, "
    "not 25 billion. Apollo 11 landed on July 21, 1969, and was commanded by Buzz Aldrin. "
    "There were five successful Moon landings, not six. The program concluded in 1973. "
    "Saturn IB rockets, not Saturn V, were used for the lunar missions.\n"
)

# Minimal valid PDF with the text 'Hello DocuSense PDF Test Document'
MINIMAL_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 78>>stream\n"
    b"BT /F1 18 Tf 50 720 Td (Hello DocuSense PDF Test Document about apples) Tj ET\n"
    b"endstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000054 00000 n \n0000000100 00000 n \n"
    b"0000000186 00000 n \n0000000301 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n360\n%%EOF\n"
)


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    return s


@pytest.fixture(scope="session")
def created_doc_ids():
    ids: list[str] = []
    yield ids
    # Cleanup at end
    for did in ids:
        try:
            requests.delete(f"{API}/documents/{did}", timeout=30)
        except Exception:
            pass


# ------------- Health -------------
class TestHealth:
    def test_health(self, session):
        r = session.get(f"{API}/health", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["mongo"] is True
        assert d["llm_key"] is True


# ------------- Upload -------------
class TestUpload:
    def test_upload_txt(self, session, created_doc_ids):
        files = {"file": ("TEST_apollo_a.txt", TEST_DOC_TEXT_A.encode(), "text/plain")}
        r = session.post(f"{API}/upload", files=files, timeout=300)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d and d["name"] == "TEST_apollo_a.txt"
        assert d["num_chunks"] >= 1
        assert d["num_pages"] >= 1
        created_doc_ids.append(d["id"])
        # store on class
        TestUpload.doc_a_id = d["id"]

    def test_upload_second_txt(self, session, created_doc_ids):
        files = {"file": ("TEST_apollo_b.txt", TEST_DOC_TEXT_B.encode(), "text/plain")}
        r = session.post(f"{API}/upload", files=files, timeout=300)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["num_chunks"] >= 1
        created_doc_ids.append(d["id"])
        TestUpload.doc_b_id = d["id"]

    def test_upload_pdf(self, session, created_doc_ids):
        files = {"file": ("TEST_sample.pdf", MINIMAL_PDF, "application/pdf")}
        r = session.post(f"{API}/upload", files=files, timeout=300)
        # Some minimal PDFs may not parse; accept 200 or 422 with clear error
        if r.status_code == 200:
            d = r.json()
            assert d["num_pages"] >= 1
            assert d["num_chunks"] >= 1
            created_doc_ids.append(d["id"])
        else:
            pytest.fail(f"PDF upload failed: {r.status_code} {r.text}")

    def test_upload_unsupported_ext(self, session):
        files = {"file": ("evil.exe", b"MZ\x90\x00binary", "application/octet-stream")}
        r = session.post(f"{API}/upload", files=files, timeout=30)
        assert r.status_code == 400

    def test_upload_empty(self, session):
        files = {"file": ("empty.txt", b"", "text/plain")}
        r = session.post(f"{API}/upload", files=files, timeout=30)
        assert r.status_code == 400


# ------------- Documents list -------------
class TestDocumentsList:
    def test_list_includes_uploaded(self, session):
        r = session.get(f"{API}/documents", timeout=30)
        assert r.status_code == 200
        items = r.json()
        ids = {it["id"] for it in items}
        assert TestUpload.doc_a_id in ids
        assert TestUpload.doc_b_id in ids


# ------------- Query -------------
class TestQuery:
    def test_query_relevant(self, session):
        body = {
            "question": "Who commanded Apollo 11 and when did it land?",
            "doc_ids": [TestUpload.doc_a_id],
            "top_k": 4,
        }
        r = session.post(f"{API}/query", json=body, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["answer"], str) and len(d["answer"]) > 0
        assert len(d["citations"]) >= 1
        assert d["citations"][0]["doc_id"] == TestUpload.doc_a_id

    def test_query_no_answer(self, session):
        body = {
            "question": "What is the airspeed velocity of an unladen swallow on Mars?",
            "doc_ids": [TestUpload.doc_a_id],
            "top_k": 4,
        }
        r = session.post(f"{API}/query", json=body, timeout=120)
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["answer"], str) and len(d["answer"]) > 0


# ------------- Summary -------------
class TestSummary:
    def test_summary_valid(self, session):
        r = session.post(f"{API}/summary", json={"doc_id": TestUpload.doc_a_id}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["doc_id"] == TestUpload.doc_a_id
        s = d["summary"].lower()
        assert "overview" in s
        assert "key points" in s
        assert "conclusion" in s

    def test_summary_invalid_doc(self, session):
        r = session.post(f"{API}/summary", json={"doc_id": "non-existent-id-xyz"}, timeout=30)
        assert r.status_code == 404


# ------------- Insights -------------
class TestInsights:
    def test_insights_valid(self, session):
        r = session.post(f"{API}/insights", json={"doc_id": TestUpload.doc_a_id}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "raw" in d
        assert "insights" in d["raw"].lower()


# ------------- Compare -------------
class TestCompare:
    def test_compare_two(self, session):
        r = session.post(
            f"{API}/compare",
            json={"doc_id_a": TestUpload.doc_a_id, "doc_id_b": TestUpload.doc_b_id},
            timeout=180,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "comparison" in d
        c = d["comparison"].lower()
        assert "common ground" in c or "differences" in c

    def test_compare_same(self, session):
        r = session.post(
            f"{API}/compare",
            json={"doc_id_a": TestUpload.doc_a_id, "doc_id_b": TestUpload.doc_a_id},
            timeout=30,
        )
        assert r.status_code == 400


# ------------- Contradictions -------------
class TestContradictions:
    def test_contradictions(self, session):
        r = session.post(
            f"{API}/contradictions",
            json={"doc_id_a": TestUpload.doc_a_id, "doc_id_b": TestUpload.doc_b_id},
            timeout=180,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "contradictions" in d
        assert len(d["contradictions"]) > 0


# ------------- Delete -------------
class TestDelete:
    def test_delete_and_verify(self, session, created_doc_ids):
        # delete doc B and verify removal
        did = TestUpload.doc_b_id
        r = session.delete(f"{API}/documents/{did}", timeout=30)
        assert r.status_code == 200
        if did in created_doc_ids:
            created_doc_ids.remove(did)
        time.sleep(0.5)
        r2 = session.get(f"{API}/documents", timeout=30)
        ids = {it["id"] for it in r2.json()}
        assert did not in ids
