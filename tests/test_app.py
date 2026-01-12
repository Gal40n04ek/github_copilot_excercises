"""
Test suite for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities(client):
    """Reset activities to initial state before each test"""
    # This ensures tests don't interfere with each other
    # by resetting the in-memory database
    client.get("/activities")
    yield
    # Cleanup after test if needed


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Basketball Team" in data
        assert "Soccer Club" in data
        assert "Art Club" in data
        assert "Drama Club" in data
        assert "Debate Team" in data
        assert "Math Club" in data
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_activities_initial_participants(self, client):
        """Test that some activities have initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club should have initial participants
        assert len(data["Chess Club"]["participants"]) == 2
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Signed up student@mergington.edu for Basketball Team"
    
    def test_signup_adds_to_participants(self, client):
        """Test that signup actually adds participant to activity"""
        # Signup a student
        client.post(
            "/activities/Art Club/signup",
            params={"email": "artist@mergington.edu"}
        )
        
        # Verify they were added
        response = client.get("/activities")
        assert "artist@mergington.edu" in response.json()["Art Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for activity that doesn't exist"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_student(self, client):
        """Test that a student cannot signup twice for the same activity"""
        email = "duplicate@mergington.edu"
        activity = "Soccer Club"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_multiple_students(self, client):
        """Test that multiple students can signup for the same activity"""
        activity = "Math Club"
        students = ["student1@test.com", "student2@test.com", "student3@test.com"]
        
        for email in students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all students are registered
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for email in students:
            assert email in participants


class TestUnregisterEndpoint:
    """Tests for the unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "chess@mergington.edu"
        activity = "Chess Club"
        
        # First signup
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert response.status_code == 200
        assert response.json()["message"] == f"Unregistered {email} from {activity}"
    
    def test_unregister_removes_from_participants(self, client):
        """Test that unregister actually removes participant"""
        email = "drama@mergington.edu"
        activity = "Drama Club"
        
        # Signup first
        client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        # Unregister
        client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        
        # Verify removal
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from activity that doesn't exist"""
        response = client.delete(
            "/activities/Nonexistent Activity/participants/student@test.com"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_registered_student(self, client):
        """Test unregistering a student who is not signed up"""
        response = client.delete(
            "/activities/Basketball Team/participants/notregistered@test.com"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Verify they're registered
        response = client.get("/activities")
        assert email in response.json()[activity]["participants"]
        
        # Unregister
        response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert response.status_code == 200
        
        # Verify removal
        response = client.get("/activities")
        assert email not in response.json()[activity]["participants"]


class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""
    
    def test_activity_name_case_sensitivity(self, client):
        """Test if activity names are case-sensitive"""
        # Using different case
        response = client.post(
            "/activities/basketball team/signup",
            params={"email": "test@test.com"}
        )
        # Should fail since activity names are case-sensitive
        assert response.status_code == 404
    
    def test_email_with_special_characters(self, client):
        """Test signup with valid email containing special characters"""
        response = client.post(
            "/activities/Debate Team/signup",
            params={"email": "student+tag@mergington.edu"}
        )
        assert response.status_code == 200
    
    def test_multiple_signups_same_student_different_activities(self, client):
        """Test that a student can signup for multiple different activities"""
        email = "multi@test.com"
        activities = ["Basketball Team", "Art Club", "Chess Club"]
        
        for activity in activities:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify student is in all activities
        response = client.get("/activities")
        data = response.json()
        for activity in activities:
            assert email in data[activity]["participants"]
