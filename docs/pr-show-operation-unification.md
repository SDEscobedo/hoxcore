# Pull Request: Unify Show Operation Between CLI and MCP

## Summary

This PR introduces a shared `ShowOperation` class that provides consistent entity retrieval behavior between the CLI `hxc show` command and the MCP `get_entity_tool`. Previously, both interfaces had separate implementations with different lookup patterns, which could lead to behavioral differences.

## Changes

### New Core Operation Module

- **`src/hxc/core/operations/show.py`**: New shared operation class with:
  - Two-phase entity lookup (fast path: filename match, slow path: content search)
  - Entity data loading and validation
  - Raw content retrieval support
  - Consistent response structure for both interfaces
  - Custom exceptions: `ShowOperationError`, `EntityNotFoundError`, `InvalidEntityError`

### CLI Refactoring

- **`src/hxc/commands/show.py`**: Updated to use `ShowOperation.get_entity()` for entity retrieval
  - `find_file()` method now delegates to `ShowOperation.find_entity_file()`
  - Removed duplicate lookup logic
  - Display formatting remains CLI-specific

### MCP Refactoring

- **`src/hxc/mcp/tools.py`**: Updated `get_entity_tool` to use `ShowOperation`
  - Added `include_raw` parameter for raw YAML content retrieval
  - Consistent error handling with CLI
  - Same two-phase search strategy as CLI

- **`src/hxc/mcp/server.py`**: Updated tool schema to include `include_raw` parameter with description

### Module Exports

- **`src/hxc/core/operations/__init__.py`**: Added exports for `ShowOperation`, `ShowOperationError`, `ShowEntityNotFoundError`, `InvalidEntityError`

### Tests

- **`tests/core/operations/test_show.py`**: Comprehensive unit tests for `ShowOperation`
- **`tests/commands/test_show.py`**: Updated CLI tests to verify shared operation usage
- **`tests/mcp/test_tools.py`**: Added tests for `include_raw` parameter and behavioral parity

## Key Features

| Feature | Before | After |
|---------|--------|-------|
| Entity lookup | Duplicated in CLI and MCP | Single `ShowOperation` class |
| Search strategy | Different patterns | Unified two-phase search |
| Raw content access | CLI only (`--raw`) | Both (MCP via `include_raw`) |
| Error handling | Inconsistent | Shared exception types |
| Response structure | Different | Consistent dictionary format |

## API Changes

### MCP `get_entity` Tool

New optional parameter:
```
include_raw: boolean (default: false)
  Whether to include raw YAML file content in response.
  Useful for debugging or external processing.
```

When `include_raw=true`, response includes:
```json
{
  "success": true,
  "entity": {...},
  "file_path": "/path/to/file.yml",
  "identifier": "P-001",
  "raw_content": "type: project\nuid: proj-123\n..."
}
```

## Backward Compatibility

- ✅ All existing CLI behavior preserved
- ✅ All existing MCP `get_entity_tool` calls work unchanged
- ✅ New `include_raw` parameter defaults to `false`
- ✅ No breaking changes

## Testing

- All existing tests pass
- New unit tests for `ShowOperation` class
- Behavioral parity tests between CLI and MCP
- Tests for `include_raw` functionality
- Error scenario coverage (not found, invalid YAML, security violations)

## Related Issues

Resolves entity retrieval implementation divergence between CLI and MCP interfaces.