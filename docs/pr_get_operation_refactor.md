```markdown
# PR: Refactor Get Property Operation for CLI/MCP Behavioral Parity

## Summary

This PR refactors the `get` property retrieval functionality to ensure behavioral consistency between the CLI (`hxc get`) and MCP (`get_entity_property_tool`) interfaces. A new shared `GetPropertyOperation` class centralizes all property retrieval logic, eliminating code duplication and ensuring identical behavior across both interfaces.

## Problem

Previously, the CLI and MCP had separate implementations for property retrieval with key differences:

- **CLI** validated property names against a canonical set, providing helpful error messages
- **MCP** had no validation, returning generic "not found or not set" errors
- **Property classification** was duplicated with potential for drift
- Users couldn't distinguish between typos (unknown property) and unset values

## Solution

### New Shared Operation (`src/hxc/core/operations/get.py`)

Created `GetPropertyOperation` class that provides:

- **Canonical property sets**: `SCALAR_PROPERTIES`, `LIST_PROPERTIES`, `COMPLEX_PROPERTIES`, `SPECIAL_PROPERTIES`
- **Property validation**: `validate_property_name()` with case-insensitive matching
- **Type classification**: `get_property_type()` returns `PropertyType.SCALAR|LIST|COMPLEX|SPECIAL`
- **Unified retrieval**: `get_property()` with index and key filter support
- **Entity lookup**: Delegates to `ShowOperation` for consistent entity resolution

### Custom Exceptions

- `UnknownPropertyError` - Property name not in canonical set
- `PropertyNotSetError` - Valid property but not set on entity
- `IndexOutOfRangeError` - Index exceeds list bounds
- `InvalidKeyFilterError` - Malformed key:value pattern
- `KeyFilterNoMatchError` - No items match key filter

### Refactored Interfaces

**CLI (`src/hxc/commands/get.py`)**:
- Uses `GetPropertyOperation` for all property logic
- Maintains existing output formatting (raw, yaml, json, pretty)
- Property sets now reference the operation class for consistency

**MCP (`src/hxc/mcp/tools.py`)**:
- Uses `GetPropertyOperation` for validation and retrieval
- Returns `available_properties` list on unknown property error
- Distinguishes "unknown property" from "property not set" errors
- Includes `property_type` in successful responses

## API Changes

### MCP Response Structure (Enhanced)

**Success Response:**
```json
{
  "success": true,
  "property": "title",
  "property_type": "scalar",
  "value": "My Project",
  "identifier": "P-001"
}
```

**Unknown Property Error (NEW):**
```json
{
  "success": false,
  "error": "Unknown property 'foobar'. Available properties: ...",
  "property": "foobar",
  "available_properties": ["title", "status", "tags", ...]
}
```

**Property Not Set Error:**
```json
{
  "success": false,
  "error": "Property 'due_date' is not set",
  "property": "due_date",
  "property_type": "scalar"
}
```

## Property Classification

| Type | Properties |
|------|------------|
| **Scalar** | `type`, `uid`, `id`, `title`, `description`, `status`, `start_date`, `due_date`, `completion_date`, `duration_estimate`, `category`, `parent`, `template` |
| **List** | `tags`, `children`, `related` |
| **Complex** | `repositories`, `storage`, `databases`, `tools`, `models`, `knowledge_bases` |
| **Special** | `all`, `path` |

## Testing

### New Test Files

- `tests/core/operations/test_get.py` - Comprehensive tests for `GetPropertyOperation`
- `tests/mcp/test_tools_get.py` - MCP tool tests with behavioral parity verification

### Test Coverage

- Property classification and validation
- All property types (scalar, list, complex, special)
- Index and key filter operations
- Error handling (unknown, unset, out of range, invalid format)
- Behavioral parity between CLI and MCP
- Integration with `ShowOperation`
- Cross-platform path handling

## Files Changed

| File | Change |
|------|--------|
| `src/hxc/core/operations/get.py` | **NEW** - Shared GetPropertyOperation class |
| `src/hxc/core/operations/__init__.py` | Export new operation and exceptions |
| `src/hxc/commands/get.py` | Refactored to use GetPropertyOperation |
| `src/hxc/mcp/tools.py` | Refactored get_entity_property_tool |
| `src/hxc/mcp/server.py` | Updated tool schema with property descriptions |
| `tests/core/operations/test_get.py` | **NEW** - Operation unit tests |
| `tests/commands/test_get.py` | Added parity and integration tests |
| `tests/mcp/test_tools_get.py` | Added parity and integration tests |

## Breaking Changes

None. All existing functionality preserved. MCP responses enhanced with additional fields.

## Checklist

- [x] `GetPropertyOperation` created with canonical property sets
- [x] Property validation with helpful error messages
- [x] MCP returns `available_properties` on unknown property error
- [x] MCP distinguishes unknown vs unset properties
- [x] CLI refactored to use shared operation
- [x] Both interfaces use identical property classification
- [x] Index handling identical across interfaces
- [x] Key filter handling identical across interfaces
- [x] Special properties (`all`, `path`) work identically
- [x] Unit tests for `GetPropertyOperation`
- [x] Integration tests for CLI/MCP parity
- [x] All existing tests pass
- [x] Cross-platform compatible (no hardcoded paths)
```