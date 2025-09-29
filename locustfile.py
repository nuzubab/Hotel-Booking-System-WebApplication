from locust import HttpUser, TaskSet, task, between

class HbsTasks(TaskSet):
    @task
    def home_page(self):
        self.client.get("/")

    @task
    def login_page(self):
        self.client.get("/auth/")

    @task
    def bookings_page(self):
        self.client.get("/my-bookings/")

class HbsUser(HttpUser):
    tasks = [HbsTasks]
    wait_time = between(1, 3)  # seconds between tasks
