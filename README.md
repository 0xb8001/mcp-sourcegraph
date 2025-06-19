# MCP Sourcegraph

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A Model Context Protocol (MCP) server that provides access to Sourcegraph's powerful code search capabilities through the GraphQL API.

## Features

- 🔍 **Code Search**: Search across repositories using Sourcegraph's advanced search syntax
- 🎯 **Repository Filtering**: Filter by specific repositories with `repo:` patterns
- 📁 **File Filtering**: Search specific file types with `file:` patterns  
- 🔤 **Language Filtering**: Filter by programming language with `lang:`/`language:` patterns
- 🔧 **Pattern Types**: Support for both keyword and regular expression search
- ⚙️ **Search Modifiers**: Case sensitivity, result limits, timeouts, and more
- 🌐 **Universal Support**: Works with Sourcegraph.com and private Sourcegraph instances

## Installation

### Quick Start with uvx (Recommended)

```bash
# Set your Sourcegraph credentials
export SOURCEGRAPH_URL="https://sourcegraph.com"
export SOURCEGRAPH_TOKEN="your-access-token"

# Run directly from GitHub
uvx --from git+https://github.com/0xb8001/mcp-sourcegraph mcp-sourcegraph
```

### One-liner
```bash
SOURCEGRAPH_URL="https://sourcegraph.com" SOURCEGRAPH_TOKEN="your-token" uvx --from git+https://github.com/0xb8001/mcp-sourcegraph mcp-sourcegraph
```

### Local Development

```bash
# Clone and run locally
git clone https://github.com/0xb8001/mcp-sourcegraph.git
cd mcp-sourcegraph
uvx --from . mcp-sourcegraph
```

### Getting a Sourcegraph Access Token

1. Go to [Sourcegraph Settings > Access tokens](https://sourcegraph.com/settings/tokens)
2. Click "Generate new token"
3. Give it a name and appropriate permissions
4. Copy the generated token

## Configuration

### Claude Code (CLI)

Add the MCP server to Claude Code:

```bash
export SOURCEGRAPH_URL="https://sourcegraph.com"
export SOURCEGRAPH_TOKEN="your-access-token"

claude mcp add sourcegraph -e SOURCEGRAPH_URL="$SOURCEGRAPH_URL" -e SOURCEGRAPH_TOKEN="$SOURCEGRAPH_TOKEN" -- uvx --from git+https://github.com/0xb8001/mcp-sourcegraph mcp-sourcegraph
```

## Usage

The server provides a `search` tool with the following parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | *(required)* | Search query using Sourcegraph syntax |
| `pattern_type` | string | `"keyword"` | `"keyword"` or `"regexp"` |
| `count` | integer | `10` | Maximum number of results (1-1000) |
| `timeout` | integer | `10` | Search timeout in seconds (5-60) |

### Search Query Examples

```bash
# Basic keyword search
hello world

# Repository filtering  
repo:facebook/react useState

# File filtering by extension
file:\.ts$ interface lang:typescript

# Language filtering
lang:python import requests

# Complex multi-filter query
repo:^github\.com/microsoft/ file:\.cs$ async lang:csharp

# Symbol search
type:symbol main lang:go

# Case-sensitive search
case:yes TODO

# Search with result limit
repo:kubernetes file:\.go$ context count:50
```

### Advanced Search Syntax

Sourcegraph supports many powerful search operators:

- **Repository filters**: `repo:pattern`, `-repo:pattern`
- **File filters**: `file:pattern`, `-file:pattern`
- **Language filters**: `lang:name`, `-lang:name`
- **Content filters**: `content:"text"`, `-content:"text"`
- **Symbol search**: `type:symbol`
- **Case sensitivity**: `case:yes`
- **Boolean operators**: `AND`, `OR`, `NOT`
- **Regex patterns**: `patterntype:regexp`

For a complete reference, see the [Sourcegraph search documentation](https://docs.sourcegraph.com/code_search/reference/queries).

## Development

### Testing

Run the test script to verify your setup:

```bash
python test_server.py
```

### Project Structure

```
mcp-sourcegraph/
├── mcp_sourcegraph/
│   ├── __init__.py
│   └── server.py          # Main MCP server implementation
├── test_server.py         # Test script
├── pyproject.toml         # Package configuration
├── README.md
├── LICENSE
└── .env.example           # Environment variables template
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Sourcegraph](https://sourcegraph.com) for providing the powerful code search API
- [Model Context Protocol](https://modelcontextprotocol.io) for the integration standard
- [Anthropic](https://anthropic.com) for Claude and the MCP specification