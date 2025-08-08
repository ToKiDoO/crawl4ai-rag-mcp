#!/usr/bin/env node

/**
 * Simple test script to check batch URL scraping via MCP
 * 
 * Created: 2025-08-05
 * Purpose: Test batch URL scraping functionality via MCP protocol
 * Context: Part of MCP Tools Testing to validate multiple URL processing
 * 
 * This script tests the ability to scrape multiple URLs in batch through
 * the MCP protocol interface, validating that the array parameter handling
 * works correctly for batch operations.
 * 
 * Related outcomes: See mcp_tools_test_results.md for batch scraping test results
 */
const { Client } = require('@modelcontextprotocol/sdk/client/index.js');
const { StdioClientTransport } = require('@modelcontextprotocol/sdk/client/stdio.js');
const { spawn } = require('child_process');

async function testBatchScraping() {
    console.log('Testing batch URL scraping via MCP...');
    
    // Test URLs - using simple, reliable sites
    const testUrls = [
        "https://httpbin.org/json",
        "https://httpbin.org/html"
    ];
    
    try {
        // Connect to MCP server
        const serverProcess = spawn('docker', [
            'exec', 'mcp-crawl4ai-dev', 'python', 'src/crawl4ai_mcp.py'
        ], {
            stdio: ['pipe', 'pipe', 'pipe']
        });
        
        const transport = new StdioClientTransport({
            reader: serverProcess.stdout,
            writer: serverProcess.stdin
        });
        
        const client = new Client({
            name: "test-client",
            version: "1.0.0"
        }, {
            capabilities: {}
        });
        
        await client.connect(transport);
        
        // Call scrape_urls with array of URLs
        const result = await client.request(
            { method: "tools/call" },
            {
                name: "scrape_urls",
                arguments: {
                    url: testUrls,
                    return_raw_markdown: true
                }
            }
        );
        
        console.log('Result:', JSON.stringify(result, null, 2));
        
        await client.close();
        serverProcess.kill();
        
    } catch (error) {
        console.error('Error during test:', error);
    }
}

testBatchScraping().catch(console.error);