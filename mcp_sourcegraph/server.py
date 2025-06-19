#!/usr/bin/env python3
"""
MCP Server for Sourcegraph GraphQL API

A Model Context Protocol server that provides access to Sourcegraph's powerful 
code search capabilities through the GraphQL API.

Copyright (c) 2025 0xb8001
Licensed under the MIT License - see LICENSE file for details.
"""

import asyncio
import os
import logging
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

import httpx
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ServerCapabilities, ToolsCapability
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SourcegraphClient:
    """Client for interacting with Sourcegraph GraphQL API."""
    
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.graphql_url = urljoin(self.base_url + '/', '.api/graphql')
        
    async def search(
        self,
        query: str,
        pattern_type: str = "keyword",
        count: int = 10,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Execute a search query using Sourcegraph GraphQL API.
        
        Args:
            query: Search query string with Sourcegraph syntax
            pattern_type: "keyword" or "regexp" 
            count: Maximum number of results
            timeout: Search timeout in seconds
            
        Returns:
            Dictionary containing search results and metadata
        """
        
        # GraphQL query for search
        graphql_query = """
        query Search($query: String!, $version: SearchVersion!, $patternType: SearchPatternType!) {
          search(query: $query, version: $version, patternType: $patternType) {
            results {
              results {
                ... on FileMatch {
                  __typename
                  file {
                    name
                    path
                    url
                  }
                  repository {
                    name
                    url
                  }
                  lineMatches {
                    preview
                    lineNumber
                    offsetAndLengths
                  }
                }
                ... on Repository {
                  __typename
                  name
                  url
                  description
                }
                ... on CommitSearchResult {
                  __typename
                  commit {
                    oid
                    message
                    url
                    author {
                      person {
                        name
                        email
                      }
                    }
                  }
                }
              }
              limitHit
              cloning {
                name
              }
              missing {
                name
              }
              timedout {
                name
              }
              matchCount
              approximateResultCount
              alert {
                title
                description
              }
            }
            stats {
              approximateResultCount
              sparkline
            }
          }
        }
        """
        
        # Add count limit to query if specified
        if count and count > 0:
            if 'count:' not in query:
                query = f"{query} count:{count}"
        
        # Map pattern type to correct enum values
        pattern_type_map = {
            "keyword": "standard",
            "regexp": "regexp"
        }
        
        variables = {
            "query": query,
            "version": "V3",
            "patternType": pattern_type_map.get(pattern_type, "standard")
        }
        
        headers = {
            "Authorization": f"token {self.access_token}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "query": graphql_query,
            "variables": variables
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    self.graphql_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                
                if "errors" in data:
                    raise Exception(f"GraphQL errors: {data['errors']}")
                    
                return data["data"]["search"]
                
            except httpx.TimeoutException:
                raise Exception(f"Search timeout after {timeout} seconds")
            except httpx.HTTPError as e:
                raise Exception(f"HTTP error: {e}")
            except Exception as e:
                raise Exception(f"Search failed: {e}")

# Initialize the MCP server
server = Server("sourcegraph")

# Global client instance
sourcegraph_client: Optional[SourcegraphClient] = None

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search",
            description="""
Search code across repositories using Sourcegraph's powerful search syntax.

## Pattern Types:
• **Keyword search** (default): Matches individual terms anywhere in document/filename. Use "..." for exact phrases
• **Regular expression**: Use /.../ for regex patterns or set pattern_type to "regexp"

## Essential Filters:
• **repo:pattern** - Filter by repository (e.g., repo:facebook/react, repo:^github\.com/microsoft/)
• **file:pattern** - Filter by file path (e.g., file:\.ts$, file:internal/)
• **lang:name** - Filter by language (e.g., lang:python, lang:javascript)
• **content:"pattern"** - Search file content with literal string
• **type:symbol** - Search for code symbols (functions, classes, etc.)
• **case:yes** - Enable case-sensitive search

## Result Control:
• **count:N** - Limit results (e.g., count:50, count:all for unlimited)
• **timeout:duration** - Set timeout (e.g., timeout:30s)

## Advanced Filters:
• **-repo:pattern** - Exclude repositories
• **-file:pattern** - Exclude files
• **before:"date"** / **after:"date"** - Filter commits by date
• **author:name** - Filter by commit author
• **fork:yes** - Include repository forks
• **archived:yes** - Include archived repositories

## Boolean Operators:
• **AND** / **and** - Both terms must match (higher precedence)
• **OR** / **or** - Either term matches
• **NOT** / **not** - Exclude term

## Common Examples:
• `repo:facebook/react useState` - Find useState in React repo
• `file:\.py$ import requests lang:python` - Python files importing requests
• `type:symbol main lang:go` - Find main functions in Go
• `repo:^github\.com/microsoft/ async lang:csharp` - Async code in Microsoft repos
• `"panic NOT ever" lang:go` - Go files with panic but not ever
• `repo:sourcegraph timeout:30s count:100` - Large search with custom limits
            """.strip(),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query using Sourcegraph syntax (supports repo:, file:, lang: filters)"
                    },
                    "pattern_type": {
                        "type": "string", 
                        "enum": ["keyword", "regexp"],
                        "default": "keyword",
                        "description": "Search pattern type: 'keyword' for standard search, 'regexp' for regular expressions"
                    },
                    "count": {
                        "type": "integer",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 1000,
                        "description": "Maximum number of results to return"
                    },
                    "timeout": {
                        "type": "integer", 
                        "default": 10,
                        "minimum": 5,
                        "maximum": 60,
                        "description": "Search timeout in seconds"
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    if name != "search":
        raise ValueError(f"Unknown tool: {name}")
    
    if not sourcegraph_client:
        raise ValueError("Sourcegraph client not initialized. Please check SOURCEGRAPH_URL and SOURCEGRAPH_TOKEN environment variables.")
    
    query = arguments.get("query", "")
    if not query:
        raise ValueError("Query parameter is required")
        
    pattern_type = arguments.get("pattern_type", "keyword")
    count = arguments.get("count", 10)
    timeout = arguments.get("timeout", 10)
    
    try:
        results = await sourcegraph_client.search(
            query=query,
            pattern_type=pattern_type,
            count=count,
            timeout=timeout
        )
        
        # Format results for LLM consumption
        output_lines = []
        search_results = results.get("results", {})
        
        # Add compact search statistics
        stats = results.get("stats", {})
        result_items = search_results.get("results", [])
        
        if not result_items:
            output_lines.append("No results found.")
        else:
            # More concise header with essential info
            approx_count = stats.get("approximateResultCount", len(result_items))
            if approx_count > len(result_items):
                output_lines.append(f"Top {len(result_items)} of ~{approx_count} results:")
            else:
                output_lines.append(f"Found {len(result_items)} results:")
            output_lines.append("")
            
            for i, result in enumerate(result_items[:int(count)], 1):
                result_type = result.get("__typename", "Unknown")
                
                if result_type == "FileMatch":
                    # More structured and LLM-friendly file match format
                    file_info = result.get("file", {})
                    repo_info = result.get("repository", {})
                    line_matches = result.get("lineMatches", [])
                    
                    # Compact single-line format with key info
                    file_path = file_info.get('path', 'Unknown')
                    repo_name = repo_info.get('name', 'Unknown')
                    
                    output_lines.append(f"{i}. {file_path}")
                    output_lines.append(f"   Repository: {repo_name}")
                    
                    # Show most relevant line match with better context
                    if line_matches:
                        best_match = line_matches[0]  # First match is usually most relevant
                        line_num = best_match.get("lineNumber", 0)
                        preview = best_match.get("preview", "").strip()
                        # Clean up preview for better readability
                        if len(preview) > 120:
                            preview = preview[:117] + "..."
                        output_lines.append(f"   Line {line_num}: {preview}")
                        
                        # Show additional matches more compactly
                        if len(line_matches) > 1:
                            additional = min(2, len(line_matches) - 1)  # Show up to 2 more
                            for match in line_matches[1:additional+1]:
                                line_num = match.get("lineNumber", 0)
                                preview = match.get("preview", "").strip()
                                if len(preview) > 80:
                                    preview = preview[:77] + "..."
                                output_lines.append(f"   Line {line_num}: {preview}")
                            
                            if len(line_matches) > 3:
                                output_lines.append(f"   ... +{len(line_matches) - 3} more matches")
                        
                elif result_type == "Repository":
                    # Repository result - keep concise
                    repo_name = result.get("name", "Unknown")
                    description = result.get("description", "")
                    
                    output_lines.append(f"{i}. Repository: {repo_name}")
                    if description and len(description) < 100:
                        output_lines.append(f"   {description}")
                        
                elif result_type == "CommitSearchResult":
                    # Commit result - more structured
                    commit = result.get("commit", {})
                    author = commit.get("author", {}).get("person", {})
                    message = commit.get('message', '').strip()
                    
                    # Truncate long commit messages
                    if len(message) > 80:
                        message = message[:77] + "..."
                    
                    output_lines.append(f"{i}. Commit: {commit.get('oid', 'Unknown')[:8]}")
                    output_lines.append(f"   {message}")
                    output_lines.append(f"   Author: {author.get('name', 'Unknown')}")
                
                output_lines.append("")  # Separator between results
        
        # Add concise status information
        status_info = []
        
        # Alerts
        alert = search_results.get("alert")
        if alert and alert.get('title'):
            status_info.append(f"Alert: {alert['title']}")
            
        # Repository status (more compact)
        if search_results.get("timedout"):
            timed_out_count = len(search_results["timedout"])
            status_info.append(f"{timed_out_count} repos timed out")
            
        if search_results.get("cloning"):
            cloning_count = len(search_results["cloning"])
            status_info.append(f"{cloning_count} repos cloning")
            
        if search_results.get("missing"):
            missing_count = len(search_results["missing"])
            status_info.append(f"{missing_count} repos missing")
        
        # Add status info if any exists
        if status_info:
            output_lines.append("Status: " + " | ".join(status_info))
        
        return [TextContent(type="text", text="\n".join(output_lines))]
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return [TextContent(type="text", text=f"Search failed: {str(e)}")]

async def main():
    """Main entry point for the server."""
    global sourcegraph_client
    
    # Initialize Sourcegraph client
    base_url = os.getenv("SOURCEGRAPH_URL", "https://sourcegraph.com")
    access_token = os.getenv("SOURCEGRAPH_TOKEN")
    
    if not access_token:
        logger.error("SOURCEGRAPH_TOKEN environment variable is required")
        raise ValueError("SOURCEGRAPH_TOKEN environment variable is required")
    
    sourcegraph_client = SourcegraphClient(base_url, access_token)
    logger.info(f"Initialized Sourcegraph client for {base_url}")
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="sourcegraph",
                server_version="0.1.3",
                capabilities=ServerCapabilities(
                    tools=ToolsCapability()
                )
            )
        )

def cli_main():
    """CLI entry point that properly handles the async main function."""
    asyncio.run(main())

if __name__ == "__main__":
    cli_main()