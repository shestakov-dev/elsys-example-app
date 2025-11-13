from uuid import uuid4
import io
import random
from locust import HttpUser, task, between


class FileStorageUser(HttpUser):
    """User that exercises multiple endpoints of the File Storage API.

    Each simulated user uploads a small file in on_start and then performs a
    mix of GET requests against the API (root, list files, metrics, health and
    file download).
    """

    wait_time = between(1, 3)

    def on_start(self):
        # Create a unique filename per user so downloads work reliably
        self.filename = f"locust-{uuid4().hex[:8]}.txt"
        content = b"locust load test content"
        files = {"file": (self.filename, io.BytesIO(content), "text/plain")}

        with self.client.post("/files", files=files, catch_response=True) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(
                    f"Failed to upload setup file: {resp.status_code} {resp.text}"
                )

    @task(3)
    def root_and_list(self):
        # Hit the root endpoint and the list files endpoint
        self.client.get("/")
        self.client.get("/files")

    @task(2)
    def download_file(self):
        # Attempt to download the file uploaded in on_start
        self.client.get(f"/files/{self.filename}")

    @task(1)
    def metrics_and_health(self):
        # Check health and metrics endpoints
        self.client.get("/health")
        self.client.get("/metrics")

    @task(1)
    def occasional_upload(self):
        # Occasionally upload a new small file to exercise POST /files
        # Use a small random payload to simulate real uploads
        if random.random() < 0.2:
            fname = f"locust-upload-{uuid4().hex[:6]}.bin"
            payload = io.BytesIO(b"x" * random.randint(10, 200))
            files = {"file": (fname, payload, "application/octet-stream")}
            self.client.post("/files", files=files)
