"""Test script for hallucination detection.

This script contains potential hallucinations for testing the detection tools.
"""

import requests
from fastapi import FastAPI
from pydantic import BaseModel

class DataAnalyzer:
    """Test class with potentially hallucinated methods."""
    
    def __init__(self):
        self.api = FastAPI()
        self.session = requests.Session()
    
    def analyze_data(self, data: dict) -> dict:
        """Analyze data using potentially non-existent methods."""
        # This might be a hallucination - does FastAPI have a process_request method?
        result = self.api.process_request(data)
        
        # This is a valid requests method
        response = self.session.get("http://api.example.com")
        
        # This might be hallucinated - does requests.Response have analyze method?
        analyzed = response.analyze()
        
        return {
            "processed": result,
            "analyzed": analyzed
        }
    
    def compute_metrics(self, values: list) -> float:
        """Compute metrics using potentially hallucinated functions."""
        # This might be hallucinated - does numpy have this specific function?
        import numpy as np
        result = np.compute_advanced_statistics(values)
        
        return result

def main():
    """Main function to test the analyzer."""
    analyzer = DataAnalyzer()
    
    test_data = {"key": "value"}
    result = analyzer.analyze_data(test_data)
    
    print(f"Analysis complete: {result}")

if __name__ == "__main__":
    main()