#!/usr/bin/env python3
"""
Performance Dashboard Generator for Pytest Performance Metrics

This script generates an interactive, self-contained HTML dashboard
from pytest performance metrics JSON.
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class PerformanceDashboard:
    def __init__(self, metrics_file: str):
        """
        Initialize dashboard with performance metrics.
        
        :param metrics_file: Path to JSON performance metrics file
        """
        try:
            with open(metrics_file, 'r') as f:
                data = json.load(f)
            
            # Handle both custom plugin format and pytest-json-report format
            if isinstance(data, dict) and 'tests' in data:
                # Custom performance plugin format
                self.metrics = list(data['tests'].values())
                self.summary = data.get('summary', {})
            elif isinstance(data, dict) and 'tests' in data:
                # pytest-json-report format
                self.metrics = []
                for test in data.get('tests', []):
                    self.metrics.append({
                        'name': test.get('nodeid', 'Unknown'),
                        'duration': test.get('call', {}).get('duration', 0) or test.get('duration', 0),
                        'outcome': test.get('outcome', 'unknown')
                    })
                self.summary = data.get('summary', {})
            elif isinstance(data, list):
                # Simple list format
                self.metrics = data
                self.summary = {}
            else:
                # Fallback - empty metrics
                print(f"Warning: Unknown metrics format in {metrics_file}")
                self.metrics = []
                self.summary = {}
                
        except FileNotFoundError:
            print(f"Error: Metrics file '{metrics_file}' not found")
            self.metrics = []
            self.summary = {}
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON from '{metrics_file}': {e}")
            self.metrics = []
            self.summary = {}
        except Exception as e:
            print(f"Error loading metrics: {e}")
            self.metrics = []
            self.summary = {}
        
        self.now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    def _extract_test_data(self) -> tuple[List[str], List[float]]:
        """Extract test names and durations from metrics."""
        test_names = []
        test_times = []
        
        for test in self.metrics:
            if isinstance(test, dict):
                name = test.get('name', 'Unknown')
                duration = test.get('duration', 0)
                
                # Clean up test names for display
                if '::' in name:
                    name = name.split('::')[-1]
                
                test_names.append(name)
                test_times.append(float(duration) if duration else 0)
        
        return test_names, test_times
    
    def _generate_plotly_script(self) -> str:
        """
        Generate Plotly.js script for visualizations.
        
        :return: Plotly.js configuration script
        """
        test_names, test_times = self._extract_test_data()
        
        if not test_names:
            return '''
            <script>
            document.addEventListener('DOMContentLoaded', function() {
                document.getElementById('testTimesChart').innerHTML = '<p>No test data available</p>';
            });
            </script>
            '''
        
        return f'''
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            var testTimesTrace = {{
                x: {json.dumps(test_names)},
                y: {json.dumps(test_times)},
                type: 'bar',
                name: 'Test Execution Times'
            }};
            
            var testTimesLayout = {{
                title: 'Test Execution Times',
                xaxis: {{title: 'Test Name', tickangle: 45}},
                yaxis: {{title: 'Duration (seconds)'}}
            }};
            
            Plotly.newPlot('testTimesChart', [testTimesTrace], testTimesLayout);
        }});
        </script>
        '''
    
    def _generate_slowest_tests_table(self) -> str:
        """
        Generate HTML table of slowest tests.
        
        :return: HTML table of slowest tests
        """
        test_data = []
        for test in self.metrics:
            if isinstance(test, dict) and 'duration' in test:
                test_data.append({
                    'name': test.get('name', 'Unknown'),
                    'duration': float(test.get('duration', 0))
                })
        
        if not test_data:
            return '''
            <div class="slowest-tests">
                <h2>Slowest Tests</h2>
                <p>No test data available</p>
            </div>
            '''
        
        sorted_tests = sorted(test_data, key=lambda x: x['duration'], reverse=True)[:10]
        
        table_rows = ''.join([
            f'<tr><td>{test["name"]}</td><td>{test["duration"]:.2f}s</td></tr>'
            for test in sorted_tests if test['duration'] > 0
        ])
        
        if not table_rows:
            table_rows = '<tr><td colspan="2">No test timing data available</td></tr>'
        
        return f'''
        <div class="slowest-tests">
            <h2>10 Slowest Tests</h2>
            <table>
                <thead>
                    <tr><th>Test Name</th><th>Duration</th></tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        '''
    
    def _generate_summary_section(self) -> str:
        """Generate summary statistics section."""
        total_tests = len(self.metrics)
        total_duration = sum(float(test.get('duration', 0)) for test in self.metrics if isinstance(test, dict))
        
        passed_tests = sum(1 for test in self.metrics if isinstance(test, dict) and test.get('outcome') == 'passed')
        failed_tests = sum(1 for test in self.metrics if isinstance(test, dict) and test.get('outcome') == 'failed')
        
        return f'''
        <div class="summary">
            <h2>Test Summary</h2>
            <ul>
                <li>Total Tests: {total_tests}</li>
                <li>Total Duration: {total_duration:.2f}s</li>
                <li>Passed: {passed_tests}</li>
                <li>Failed: {failed_tests}</li>
            </ul>
        </div>
        '''
    
    def generate_dashboard(self) -> str:
        """
        Generate complete performance dashboard HTML.
        
        :return: Complete HTML dashboard
        """
        dashboard_html = f'''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Performance Dashboard</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
                .dashboard-header {{ text-align: center; margin-bottom: 30px; }}
                .summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin-bottom: 30px; }}
                .summary ul {{ list-style: none; padding: 0; }}
                .summary li {{ margin: 10px 0; font-size: 16px; }}
                .charts {{ display: flex; flex-wrap: wrap; margin-bottom: 30px; }}
                .chart {{ width: 100%; height: 400px; }}
                .slowest-tests {{ margin-top: 30px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                table, th, td {{ border: 1px solid #ddd; }}
                th, td {{ padding: 8px; text-align: left; }}
                th {{ background-color: #f5f5f5; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <h1>Performance Dashboard</h1>
                <p>Generated: {self.now}</p>
            </div>
            
            {self._generate_summary_section()}
            
            <div class="charts">
                <div id="testTimesChart" class="chart"></div>
            </div>
            
            {self._generate_slowest_tests_table()}
            
            {self._generate_plotly_script()}
        </body>
        </html>
        '''
        return dashboard_html


def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_performance_dashboard.py <metrics_json_file>")
        sys.exit(1)
    
    metrics_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(metrics_file):
        print(f"Error: Metrics file '{metrics_file}' not found")
        # Generate a minimal dashboard anyway
        dashboard_html = '''
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Performance Dashboard - No Data</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
                .error { color: red; text-align: center; margin-top: 50px; }
            </style>
        </head>
        <body>
            <div class="error">
                <h1>Performance Dashboard</h1>
                <p>No performance metrics data available.</p>
                <p>The metrics file was not found or could not be parsed.</p>
            </div>
        </body>
        </html>
        '''
        
        output_file = 'performance_dashboard.html'
        with open(output_file, 'w') as f:
            f.write(dashboard_html)
        
        print(f"Performance dashboard generated: {output_file} (no data)")
        sys.exit(0)
    
    dashboard = PerformanceDashboard(metrics_file)
    
    output_file = 'performance_dashboard.html'
    with open(output_file, 'w') as f:
        f.write(dashboard.generate_dashboard())
    
    print(f"Performance dashboard generated: {output_file}")


if __name__ == '__main__':
    main()