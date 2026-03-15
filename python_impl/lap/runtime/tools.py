"""工具定义 — Anthropic tool_use 格式

复刻 OpenHands CodeAct Agent 的 4 个核心工具:
    bash            — 执行 bash 命令
    str_replace_editor — 文件查看/创建/编辑 (view, create, str_replace, insert, undo_edit)
    finish          — 信号任务完成
    think           — 记录推理过程 (无副作用)
"""

BASH_TOOL = {
    "name": "bash",
    "description": (
        "Execute a bash command in a persistent shell session.\n"
        "* One command at a time. Chain with && or ; if needed.\n"
        "* For long-running commands, run in background: command > out.log 2>&1 &\n"
        "* Verify parent directory exists before creating files.\n"
        "* Use absolute paths when possible."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The bash command to execute.",
            },
        },
        "required": ["command"],
    },
}

STR_REPLACE_EDITOR_TOOL = {
    "name": "str_replace_editor",
    "description": (
        "Custom editing tool for viewing, creating and editing files.\n"
        "* If path is a file, 'view' displays with line numbers (cat -n).\n"
        "  If path is a directory, 'view' lists files up to 2 levels deep.\n"
        "* 'create' creates a new file (fails if file already exists).\n"
        "* 'str_replace' replaces old_str with new_str. old_str must match exactly\n"
        "  and uniquely in the file. Include 3-5 lines of context for uniqueness.\n"
        "* 'insert' inserts new_str AFTER the specified insert_line.\n"
        "* 'undo_edit' reverts the last edit made to the file.\n"
        "* Always use absolute file paths (starting with /)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The command to run: view, create, str_replace, insert, undo_edit.",
                "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
            },
            "path": {
                "type": "string",
                "description": "Absolute path to file or directory.",
            },
            "file_text": {
                "type": "string",
                "description": "Required for 'create': content of the new file.",
            },
            "old_str": {
                "type": "string",
                "description": "Required for 'str_replace': exact string to replace.",
            },
            "new_str": {
                "type": "string",
                "description": (
                    "For 'str_replace': replacement string (empty to delete). "
                    "For 'insert': string to insert after insert_line."
                ),
            },
            "insert_line": {
                "type": "integer",
                "description": "Required for 'insert': line number after which to insert new_str.",
            },
            "view_range": {
                "type": "array",
                "items": {"type": "integer"},
                "description": (
                    "Optional for 'view': [start_line, end_line] to show. "
                    "1-indexed. Use [start, -1] for start to end of file."
                ),
            },
        },
        "required": ["command", "path"],
    },
}

FINISH_TOOL = {
    "name": "finish",
    "description": (
        "Signal completion of the current task.\n"
        "Use when you have successfully completed the task, "
        "cannot proceed further, or need to ask for clarification.\n"
        "Include a clear summary of actions taken and results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Final message summarizing the result.",
            },
        },
        "required": ["message"],
    },
}

THINK_TOOL = {
    "name": "think",
    "description": (
        "Log a thought or reasoning step. No side effects.\n"
        "Use for: brainstorming fixes, analyzing test results, "
        "planning refactoring, organizing hypotheses."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "thought": {
                "type": "string",
                "description": "The thought to log.",
            },
        },
        "required": ["thought"],
    },
}

ALL_TOOLS = [BASH_TOOL, STR_REPLACE_EDITOR_TOOL, FINISH_TOOL, THINK_TOOL]
