# Command Execution Rules

## Never Use `cd` in Shell Commands

When executing shell commands, **never** use `cd` to change directories. Instead, use the `cwd` parameter on the tool to set the working directory.

### Why

- `cd` commands are not supported and will fail
- Using `cwd` makes commands easier to review and approve
- Each command execution is independent — `cd` has no effect on subsequent calls

### Examples

**❌ Wrong:**
```bash
cd lambda/event_log_checkpoint/test/python && pants test test_checkpoint.py
```

**✅ Correct:**
Use `cwd` parameter set to the target directory, then run the command directly:
```bash
pants test lambda/event_log_checkpoint/test/python/test_checkpoint.py
```

Or if you need to run a script relative to a subdirectory, set `cwd` to that directory and run the command without `cd`.

### Applies To

- All `execute_bash` tool calls
- All `control_bash_process` tool calls
- All shell commands in any context
