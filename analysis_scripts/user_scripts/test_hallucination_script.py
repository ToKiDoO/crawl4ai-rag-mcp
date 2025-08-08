#!/usr/bin/env python3
"""Test script with known hallucinations for testing AI script validation."""

import requests
from datetime import datetime
import json

def test_api_call():
    """Test function with hallucinated methods."""
    
    # This is a real method - should pass
    response = requests.get("https://api.example.com/data")
    
    # HALLUCINATION: extract_json_data() doesn't exist on Response object
    data = response.extract_json_data()
    
    # This is a real method - should pass
    current_time = datetime.now()
    
    # HALLUCINATION: add_days() doesn't exist on datetime object
    tomorrow = current_time.add_days(1)
    
    # HALLUCINATION: auto_retry parameter doesn't exist for requests.post
    result = requests.post(
        "https://api.example.com/submit",
        json={"data": "test"},
        auto_retry=True
    )
    
    # Real code - should pass
    json_str = json.dumps({"key": "value"})
    
    # HALLUCINATION: json.parse() doesn't exist (should be json.loads)
    parsed = json.parse(json_str)
    
    return parsed

if __name__ == "__main__":
    test_api_call()