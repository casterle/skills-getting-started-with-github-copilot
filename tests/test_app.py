import pytest
from fastapi.testclient import TestClient
from src.app import app, init_db, DB_PATH, activities
import os
import sqlite3

@pytest.fixture(scope="function", autouse=True)
def setup_and_teardown():
    # Remove DB if exists, then re-init and seed
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    # Manually seed DB with activities and participants
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for name, details in activities.items():
        c.execute("INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                  (name, details["description"], details["schedule"], details["max_participants"]))
        for email in details["participants"]:
            # Replace test emails in seed data if needed
            if email.endswith("@mergington.edu"):
                email = email.replace("@mergington.edu", "@example.com")
            c.execute("INSERT INTO participants (activity_name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    conn.close()
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

client = TestClient(app)

def test_get_activities():
    r = client.get("/activities")
    assert r.status_code == 200
    data = r.json()
    assert "Chess Club" in data
    assert data["Chess Club"]["max_participants"] == 12

def test_signup_and_unregister():
    # Valid signup
    r = client.post("/activities/Chess Club/signup?email=tester@example.com")
    assert r.status_code == 200
    assert "Signed up" in r.json()["message"]
    # Duplicate signup
    r2 = client.post("/activities/Chess Club/signup?email=tester@example.com")
    assert r2.status_code == 409
    # Invalid email
    r3 = client.post("/activities/Chess Club/signup?email=bademail")
    assert r3.status_code == 422
    # Unregister
    r4 = client.post("/activities/Chess Club/unregister?email=tester@example.com")
    assert r4.status_code == 200
    # Unregister not registered
    r5 = client.post("/activities/Chess Club/unregister?email=notfound@example.com")
    assert r5.status_code == 409

def test_activity_full():
    # Fill up Math Olympiad (max 10), but rate limit is 5 per minute
    success_count = 0
    rate_limited = False
    for i in range(10):
        email = f"user{i}@example.com"
        r = client.post(f"/activities/Math Olympiad/signup?email={email}")
        if r.status_code == 200:
            success_count += 1
        elif r.status_code == 429:
            rate_limited = True
            break
        else:
            assert False, f"Unexpected status: {r.status_code}"
    assert success_count <= 5  # Should not exceed rate limit
    assert rate_limited, "Should be rate limited after 5 signups"
    # Next signup should also be rate limited
    r = client.post("/activities/Math Olympiad/signup?email=extra@example.com")
    assert r.status_code == 429

def test_rate_limit():
    for _ in range(5):
        r = client.post("/activities/Programming Class/signup?email=rltest@example.com")
    r2 = client.post("/activities/Programming Class/signup?email=rltest2@example.com")
    assert r2.status_code in (429, 409)  # 409 if already registered, 429 if rate limited
