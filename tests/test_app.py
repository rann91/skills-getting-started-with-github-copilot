import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestRootEndpoint:
    def test_root_redirect(self):
        """Test that root path redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307


class TestActivitiesEndpoint:
    def test_get_activities(self):
        """Test fetching all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Debate Club" in data
        assert "Science Club" in data

    def test_get_activities_contains_required_fields(self):
        """Test that activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignupEndpoint:
    def test_signup_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]

    def test_signup_duplicate_email(self):
        """Test that duplicate signups are rejected"""
        email = "duplicate@mergington.edu"
        activity = "Drama%20Club"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup with same email should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_nonexistent_activity(self):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/NonExistent%20Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_signup_full_activity(self):
        """Test signup for full activity"""
        # Get activities to find one close to full
        activities = client.get("/activities").json()
        
        # Chess Club has max 12 participants, add more until full
        activity = "Chess%20Club"
        for i in range(15):
            response = client.post(
                f"/activities/{activity}/signup?email=student{i}@mergington.edu"
            )
            if response.status_code != 200:
                assert response.status_code == 400
                assert "full" in response.json()["detail"].lower()
                break


class TestUnregisterEndpoint:
    def test_unregister_success(self):
        """Test successful unregistration from an activity"""
        email = "unregister_test@mergington.edu"
        activity = "Art%20Studio"
        
        # First, sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Then, unregister
        unregister_response = client.post(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        data = unregister_response.json()
        assert "message" in data
        
        # Verify participant is removed
        activities = client.get("/activities").json()
        assert email not in activities[activity.replace("%20", " ")]["participants"]

    def test_unregister_nonexistent_activity(self):
        """Test unregistration from non-existent activity"""
        response = client.post(
            "/activities/Fake%20Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404

    def test_unregister_student_not_in_activity(self):
        """Test unregistration of student not in activity"""
        response = client.post(
            "/activities/Debate%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_unregister_existing_participant(self):
        """Test unregistering an existing participant"""
        response = client.post(
            "/activities/Debate%20Club/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        
        # Verify they're removed
        activities = client.get("/activities").json()
        assert "alex@mergington.edu" not in activities["Debate Club"]["participants"]
