"""
Sample HTTP Load Test
Demonstrates HTTP-based load testing with Locust
"""
import random
import time
from locust import HttpUser, TaskSet, task, between

# Import custom helpers
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))


class SampleHttpTasks(TaskSet):
    """TaskSet for sample HTTP operations"""

    def on_start(self):
        """Called when a user starts"""
        self.user_id = random.randint(1000, 9999)
        print(f"User {self.user_id} starting")

    @task(3)
    def get_user_profile(self):
        """GET request to fetch user profile"""
        with self.client.get(
            f"/api/users/{self.user_id}",
            name="/api/users/[id]",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status code: {response.status_code}")

    @task(2)
    def update_user_data(self):
        """POST request to update user data"""
        payload = {
            "user_id": self.user_id,
            "action": "update_profile",
            "timestamp": int(time.time())
        }

        with self.client.post(
            "/api/users/update",
            json=payload,
            name="/api/users/update",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"Update failed: {response.status_code}")

    @task(1)
    def get_leaderboard(self):
        """GET request to fetch leaderboard"""
        with self.client.get(
            "/api/leaderboard",
            name="/api/leaderboard",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure("Leaderboard fetch failed")

    def on_stop(self):
        """Called when a user stops"""
        print(f"User {self.user_id} stopping")


class SampleHttpUser(HttpUser):
    """HTTP User class for load testing"""
    tasks = [SampleHttpTasks]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    # host will be overridden by command line argument
    host = "http://localhost:8080"
