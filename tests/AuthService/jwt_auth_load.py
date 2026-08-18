"""
JWT Authentication Load Test
Tests the JWT token creation endpoint for  API
"""
import random
import os
from locust import HttpUser, TaskSet, task, between, events
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class JWTAuthTasks(TaskSet):
    """TaskSet for JWT Authentication operations"""

    # Class attribute for test user IDs (accessible before instance creation)
    test_user_ids = [662, 663, 664, 665, 666]

    def on_start(self):
        """Called when a user starts"""
        # Sample user IDs for testing (already set as class attribute)
        self.test_phone_numbers = [
            "5550000001",
            "5550000001",
            "5550000001",
            "5550000002",
            "5550000002"
        ]
        self.current_user_idx = random.randint(0, len(self.test_user_ids) - 1)
        print(f"User {self.test_user_ids[self.current_user_idx]} starting JWT auth test")

    @task(5)
    def create_jwt_token(self):
        """POST request to create JWT token"""
        user_id = self.test_user_ids[self.current_user_idx]
        phone_number = self.test_phone_numbers[self.current_user_idx]

        headers = {
            "userId": str(user_id),
            "phoneNumber": phone_number,
            "Content-Type": "application/json"
        }

        with self.client.post(
            "/auth/token",
            headers=headers,
            name="/auth/token",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    if "token" in json_response or "jwt" in json_response:
                        response.success()
                    else:
                        response.failure("No token found in response")
                except Exception as e:
                    response.failure(f"Failed to parse JSON: {str(e)}")
            elif response.status_code == 201:
                response.success()
            else:
                response.failure(f"JWT creation failed with status: {response.status_code}")

    @task(1)
    def create_jwt_token_with_rotation(self):
        """POST request with different user credentials (simulates user rotation)"""
        # Rotate to a different test user
        self.current_user_idx = (self.current_user_idx + 1) % len(self.test_user_ids)

        user_id = self.test_user_ids[self.current_user_idx]
        phone_number = self.test_phone_numbers[self.current_user_idx]

        headers = {
            "userId": str(user_id),
            "phoneNumber": phone_number,
            "Content-Type": "application/json"
        }

        with self.client.post(
            "/auth/token",
            headers=headers,
            name="/auth/token [rotation]",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"JWT creation failed: {response.status_code}")

    def on_stop(self):
        """Called when a user stops"""
        print(f"User {self.test_user_ids[self.current_user_idx]} stopping JWT auth test")


class JWTAuthUser(HttpUser):
    """HTTP User class for JWT authentication load testing"""
    tasks = [JWTAuthTasks]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    # Default host - will be overridden by command line or environment variable
    host = os.getenv("TARGET_HOST", "https://qa-api.example.com")


# Event listeners for custom logging and reporting
@events.test_start.add_listener
def on_test_start(_environment, **_kwargs):
    """Called when test starts"""
    print("=" * 60)
    print("JWT Authentication Load Test Starting")
    print(f"Target Host: {os.getenv('TARGET_HOST', 'https://qa-api.example.com')}")
    print(f"Test Users: {JWTAuthTasks.test_user_ids}")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(_environment, **_kwargs):
    """Called when test stops"""
    print("=" * 60)
    print("JWT Authentication Load Test Complete")
    print("=" * 60)
