from datetime import datetime

import requests

# Test script with known hallucinations

# Hallucination 1: response.extract_json_data() - method doesn't exist on Response object
response = requests.get("https://api.example.com/data")
data = response.extract_json_data()

# Hallucination 2: datetime.now().add_days(1) - method doesn't exist on datetime object
tomorrow = datetime.now().add_days(1)

# Hallucination 3: requests.post(..., auto_retry=True) - parameter doesn't exist
result = requests.post(
    "https://api.example.com/endpoint", json={"key": "value"}, auto_retry=True
)

print("Test completed")
