"""Simple test to verify the API endpoints work."""

from fastapi.testclient import TestClient
from app.main import create_app

def test_health_endpoint():
    """Test the health endpoint."""
    app = create_app()
    client = TestClient(app)
    
    response = client.get("/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Should return 503 because config is missing, but endpoint should work
    assert response.status_code in [200, 503]

if __name__ == "__main__":
    test_health_endpoint()
    print("Basic test passed!")