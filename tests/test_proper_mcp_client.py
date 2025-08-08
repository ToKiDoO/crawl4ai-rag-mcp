#!/usr/bin/env python3
"""
Proper MCP protocol implementation for testing batch URL scraping
"""

import asyncio
import json
import subprocess
import time


class MCPClient:
    def __init__(self, command):
        self.command = command
        self.process = None
        self.initialized = False

    async def __aenter__(self):
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Initialize the MCP connection
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    async def initialize(self):
        """Initialize MCP connection"""
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0",
                },
            },
        }

        response = await self.send_request(init_request)
        if "result" in response:
            self.initialized = True
            print(f"✅ MCP initialized: {response['result']['serverInfo']['name']}")

            # Send initialized notification
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }
            await self.send_notification(initialized_notification)

        else:
            raise Exception(f"Failed to initialize MCP: {response}")

    async def send_request(self, request):
        """Send a request and wait for response"""
        if not self.process:
            raise Exception("MCP process not started")

        request_json = json.dumps(request) + "\n"
        print(f"→ {request_json.strip()}")

        self.process.stdin.write(request_json)
        self.process.stdin.flush()

        response_line = self.process.stdout.readline()
        print(f"← {response_line.strip()}")

        if response_line:
            return json.loads(response_line)
        stderr_output = self.process.stderr.read()
        raise Exception(f"No response received. Stderr: {stderr_output}")

    async def send_notification(self, notification):
        """Send a notification (no response expected)"""
        if not self.process:
            raise Exception("MCP process not started")

        notification_json = json.dumps(notification) + "\n"
        print(f"→ (notification) {notification_json.strip()}")

        self.process.stdin.write(notification_json)
        self.process.stdin.flush()

    async def list_tools(self):
        """List available tools"""
        if not self.initialized:
            raise Exception("MCP not initialized")

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
        }

        return await self.send_request(request)

    async def call_tool(self, tool_name, arguments):
        """Call a tool with arguments"""
        if not self.initialized:
            raise Exception("MCP not initialized")

        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        return await self.send_request(request)


async def test_batch_url_scraping():
    """Test batch URL scraping with proper MCP protocol"""
    print("Testing batch URL scraping with proper MCP protocol...")

    command = [
        "docker",
        "exec",
        "-i",
        "mcp-crawl4ai-dev",
        "python",
        "src/crawl4ai_mcp.py",
    ]

    test_urls = [
        "https://httpbin.org/json",
        "https://httpbin.org/html",
    ]

    async with MCPClient(command) as client:
        # First, list available tools
        print("\n📋 Listing available tools...")
        tools_response = await client.list_tools()

        if "result" in tools_response:
            tools = tools_response["result"]["tools"]
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(
                    f"  - {tool['name']}: {tool.get('description', 'No description')[:100]}..."
                )

        # Test batch URL scraping
        print(f"\n🔍 Testing batch URL scraping with {len(test_urls)} URLs...")
        start_time = time.time()

        scrape_response = await client.call_tool(
            "scrape_urls",
            {
                "url": test_urls,
                "return_raw_markdown": True,
                "max_concurrent": 2,
            },
        )

        elapsed = time.time() - start_time
        print(f"Request completed in {elapsed:.2f}s")

        # Process response
        if "result" in scrape_response:
            result = (
                json.loads(scrape_response["result"])
                if isinstance(scrape_response["result"], str)
                else scrape_response["result"]
            )

            print("\nBatch scraping result:")
            print(f"- Success: {result.get('success', 'unknown')}")
            print(f"- Mode: {result.get('mode', 'unknown')}")

            if result.get("success") and "results" in result:
                results = result["results"]
                print(f"- URLs processed: {len(results)}")

                success_count = 0
                for url, content in results.items():
                    if content == "No content retrieved":
                        print(f"  ❌ {url}: No content retrieved")
                    else:
                        print(f"  ✅ {url}: {len(content)} chars retrieved")
                        success_count += 1

                if success_count == len(test_urls):
                    print(f"\n🎉 All {len(test_urls)} URLs were scraped successfully!")
                    return True
                print(
                    f"\n⚠️ Only {success_count}/{len(test_urls)} URLs were scraped successfully"
                )
                return False
            print(f"❌ Scraping failed: {result.get('error', 'unknown error')}")
            return False
        if "error" in scrape_response:
            print(f"❌ MCP error: {scrape_response['error']}")
            return False
        print(f"❌ Unexpected response: {scrape_response}")
        return False


async def test_single_url_comparison():
    """Test single URL for comparison"""
    print("\n" + "=" * 50)
    print("Testing single URL for comparison...")

    command = [
        "docker",
        "exec",
        "-i",
        "mcp-crawl4ai-dev",
        "python",
        "src/crawl4ai_mcp.py",
    ]
    test_url = "https://httpbin.org/json"

    async with MCPClient(command) as client:
        start_time = time.time()

        scrape_response = await client.call_tool(
            "scrape_urls",
            {
                "url": test_url,  # Single URL as string
                "return_raw_markdown": True,
            },
        )

        elapsed = time.time() - start_time
        print(f"Single URL request completed in {elapsed:.2f}s")

        if "result" in scrape_response:
            result = (
                json.loads(scrape_response["result"])
                if isinstance(scrape_response["result"], str)
                else scrape_response["result"]
            )

            print("Single URL result:")
            print(f"- Success: {result.get('success', 'unknown')}")

            if result.get("success"):
                content_length = result.get("content_length", 0)
                print(f"- Content length: {content_length} chars")
                return True
            print(f"- Error: {result.get('error', 'unknown')}")
            return False
        if "error" in scrape_response:
            print(f"❌ MCP error: {scrape_response['error']}")
            return False
        print(f"❌ Unexpected response: {scrape_response}")
        return False


if __name__ == "__main__":

    async def run_tests():
        print("Starting comprehensive MCP batch URL scraping tests...")

        # Test batch scraping
        try:
            batch_success = await test_batch_url_scraping()
        except Exception as e:
            print(f"❌ Batch test failed with exception: {e}")
            batch_success = False

        # Test single URL
        try:
            single_success = await test_single_url_comparison()
        except Exception as e:
            print(f"❌ Single URL test failed with exception: {e}")
            single_success = False

        print("\n" + "=" * 50)
        print("Test Results Summary:")
        print(f"- Batch URL scraping: {'✅ PASS' if batch_success else '❌ FAIL'}")
        print(f"- Single URL scraping: {'✅ PASS' if single_success else '❌ FAIL'}")

        if batch_success:
            print("\n🎉 Batch URL scraping is working correctly!")
        else:
            print("\n🚨 Batch URL scraping needs investigation")

    asyncio.run(run_tests())
