"""
Tests for the Mergington High School Activities API

Uses pytest and TestClient from FastAPI to test all endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add the src directory to the path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def fresh_activities(client):
    """Reset activities to a known state before each test"""
    # Get current activities and store them
    response = client.get("/activities")
    original = response.json()
    
    # Reset activities to clean state
    from app import activities
    
    # Clear participants for testing
    for activity in activities.values():
        activity["participants"] = []
    
    yield activities
    
    # Restore original state after test
    for activity in activities.values():
        activity["participants"] = []


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_dict(self, client):
        """Test that /activities returns a dictionary of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
    
    def test_get_activities_contains_expected_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_get_activities_includes_soccer_club(self, client):
        """Test that Soccer Club is in the activities list"""
        response = client.get("/activities")
        activities = response.json()
        assert "Soccer Club" in activities


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant(self, client, fresh_activities):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "student@mergington.edu" in result["message"]
    
    def test_signup_adds_participant_to_activity(self, client, fresh_activities):
        """Test that signup actually adds the participant"""
        # Signup
        client.post(
            "/activities/Soccer Club/signup",
            params={"email": "alice@mergington.edu"}
        )
        
        # Verify
        response = client.get("/activities")
        activities = response.json()
        assert "alice@mergington.edu" in activities["Soccer Club"]["participants"]
    
    def test_signup_duplicate_participant_fails(self, client, fresh_activities):
        """Test that signing up the same person twice fails"""
        email = "bob@mergington.edu"
        
        # First signup
        client.post(
            "/activities/Soccer Club/signup",
            params={"email": email}
        )
        
        # Second signup should fail
        response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": email}
        )
        assert response.status_code == 400
        result = response.json()
        assert "already signed up" in result["detail"]
    
    def test_signup_nonexistent_activity_fails(self, client):
        """Test that signing up for a non-existent activity fails"""
        response = client.post(
            "/activities/Underwater Basket Weaving/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        result = response.json()
        assert "not found" in result["detail"]
    
    def test_signup_multiple_participants_same_activity(self, client, fresh_activities):
        """Test that multiple different participants can sign up for the same activity"""
        emails = ["alice@mergington.edu", "bob@mergington.edu", "charlie@mergington.edu"]
        
        for email in emails:
            response = client.post(
                "/activities/Soccer Club/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all are added
        response = client.get("/activities")
        activities = response.json()
        soccer_participants = activities["Soccer Club"]["participants"]
        
        for email in emails:
            assert email in soccer_participants


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client, fresh_activities):
        """Test unregistering an existing participant"""
        email = "student@mergington.edu"
        
        # Signup first
        client.post(
            "/activities/Soccer Club/signup",
            params={"email": email}
        )
        
        # Now unregister
        response = client.delete(
            "/activities/Soccer Club/unregister",
            params={"email": email}
        )
        assert response.status_code == 200
        result = response.json()
        assert "Unregistered" in result["message"]
    
    def test_unregister_removes_participant(self, client, fresh_activities):
        """Test that unregister actually removes the participant"""
        email = "alice@mergington.edu"
        
        # Signup
        client.post(
            "/activities/Soccer Club/signup",
            params={"email": email}
        )
        
        # Verify added
        response = client.get("/activities")
        assert email in response.json()["Soccer Club"]["participants"]
        
        # Unregister
        client.delete(
            "/activities/Soccer Club/unregister",
            params={"email": email}
        )
        
        # Verify removed
        response = client.get("/activities")
        assert email not in response.json()["Soccer Club"]["participants"]
    
    def test_unregister_nonexistent_activity_fails(self, client):
        """Test that unregistering from a non-existent activity fails"""
        response = client.delete(
            "/activities/Underwater Basket Weaving/unregister",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
    
    def test_unregister_participant_not_signed_up_fails(self, client, fresh_activities):
        """Test that unregistering someone not signed up fails"""
        response = client.delete(
            "/activities/Soccer Club/unregister",
            params={"email": "nobody@mergington.edu"}
        )
        assert response.status_code == 400
        result = response.json()
        assert "not signed up" in result["detail"]
    
    def test_unregister_one_of_many_participants(self, client, fresh_activities):
        """Test unregistering one participant when there are multiple"""
        emails = ["alice@mergington.edu", "bob@mergington.edu", "charlie@mergington.edu"]
        
        # Signup all
        for email in emails:
            client.post(
                "/activities/Soccer Club/signup",
                params={"email": email}
            )
        
        # Unregister one
        client.delete(
            "/activities/Soccer Club/unregister",
            params={"email": "bob@mergington.edu"}
        )
        
        # Verify only bob is removed
        response = client.get("/activities")
        participants = response.json()["Soccer Club"]["participants"]
        assert "alice@mergington.edu" in participants
        assert "bob@mergington.edu" not in participants
        assert "charlie@mergington.edu" in participants


class TestRootRedirect:
    """Tests for root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that / redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]
