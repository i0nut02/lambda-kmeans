from locust import HttpUser, task, between
import random
import json

PROBABILITIES = [0.3, 0.5, 0.2] # insert distribution probs
INDEX_MAP = {0:"small", 1 : "medium", 2 : "large"}
K_MIN = 2
K_MAX = 8

class WebsiteUser(HttpUser):
    """
    A Locust user class that simulates a user accessing a website,
    specifically sending POST requests to an AWS Lambda Function URL.
    """
    host = "https://7xsc6yki5razzpj4reft6ubb440idhgv.lambda-url.us-east-1.on.aws/"

    wait_time = between(1, 2)

    @task
    def send_image_processing_request(self):
        """
        This task simulates sending an image processing request to the Lambda Function URL.
        It generates a random image name based on probabilities and uses a fixed K value.
        """
        r = random.random()
        s = 0
        image_name = ""

        for i in range(len(PROBABILITIES)):
            s += PROBABILITIES[i]
            if s >= r:
                image_name = f"{INDEX_MAP[i]}_{random.randint(1, 200)}.jpg"
                break
        if not image_name:
            image_name = f"{INDEX_MAP[2]}_{random.randint(1, 200)}.jpg"

        headers = {"Content-Type": "application/json"}
        body = {
            "image_key": image_name,
            "k_clusters": random.randint(K_MIN, K_MAX)
        }

        with self.client.post("/", json=body, headers=headers, catch_response=True) as response:
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data:
                        response.success()
                        print(f"Request to Lambda Function URL successful for {image_name} with k=. Response: {response_data}")
                    else:
                        response.failure(f"Lambda Function URL response empty or unexpected for {image_name}: {response_data}")
                        print(f"Lambda Function URL response empty or unexpected: {response_data}")
                except json.JSONDecodeError:
                    response.failure(f"Lambda Function URL response not valid JSON for {image_name}: {response.text}")
                    print(f"Lambda Function URL response not JSON: {response.text}")
            else:
                response.failure(f"Lambda Function URL request failed with status {response.status_code} for {image_name}: {response.text}")
                print(f"Lambda Function URL request failed: Status {response.status_code}, Response: {response.text}")

# Instructions to run this Locust test:
# 1. Save the code above as 'locustfile.py' in a directory.
# 2. Open your terminal or command prompt.
# 3. Navigate to the directory where you saved 'locustfile.py'.
# 4. Make sure you have Locust installed: pip install locust
# 5. Run Locust using the command: locust -f locustfile.py
# 6. Open your web browser and go to http://localhost:8089 (or the address shown in your terminal)
#    to access the Locust web UI.
# 7. In the UI, enter the number of users to simulate and the spawn rate, then click "Start swarming".
