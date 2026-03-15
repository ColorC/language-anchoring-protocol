"""工具执行器 — OpenHands Runtime 执行层的 LAP 简化版

按 tool_name 分发执行，返回字符串结果。
每个执行器对应一个 Anthropic tool_use 工具。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


class ToolExecutor:
    """统一工具执行器

    维护 undo 备份，按 tool_name 分发到具体实现。
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._file_backups: dict[str, str] = {}  # path → last content (for undo)

    def execute(self, tool_name: str, tool_args: dict[str, Any]) -> str:
        """按 tool_name 分发执行，返回结果字符串"""
        if tool_name == "bash":
            return self.execute_bash(tool_args.get("command", ""))
        elif tool_name == "str_replace_editor":
            return self.execute_editor(tool_args)
        elif tool_name == "think":
            return self.execute_think(tool_args.get("thought", ""))
        elif tool_name == "finish":
            return self.execute_finish(tool_args.get("message", ""))
        else:
            return f"Error: Unknown tool '{tool_name}'"

    # -- bash --

    def execute_bash(self, command: str) -> str:
        """执行 bash 命令，返回 stdout+stderr"""
        if not command:
            return "[returncode: 0]"
        try:
            result = subprocess.run(
                command,
                shell=True,
                text=True,
                timeout=self.timeout,
                capture_output=True,
            )
            output = result.stdout
            if result.stderr:
                output += f"\n{result.stderr}" if output else result.stderr
            return f"[returncode: {result.returncode}]\n{output}" if output else f"[returncode: {result.returncode}]"
        except subprocess.TimeoutExpired:
            return f"[returncode: -1]\nCommand timed out after {self.timeout}s"
        except Exception as e:
            return f"[returncode: -1]\n{e}"

    # -- str_replace_editor --

    def execute_editor(self, args: dict[str, Any]) -> str:
        """文件编辑器分发"""
        command = args.get("command", "")
        path = args.get("path", "")

        if not path:
            return "Error: 'path' is required."

        if command == "view":
            return self._editor_view(path, args.get("view_range"))
        elif command == "create":
            return self._editor_create(path, args.get("file_text", ""))
        elif command == "str_replace":
            return self._editor_str_replace(path, args.get("old_str", ""), args.get("new_str", ""))
        elif command == "insert":
            return self._editor_insert(path, args.get("insert_line"), args.get("new_str", ""))
        elif command == "undo_edit":
            return self._editor_undo(path)
        else:
            return f"Error: Unknown editor command '{command}'. Use: view, create, str_replace, insert, undo_edit."

    def _editor_view(self, path: str, view_range: list[int] | None = None) -> str:
        """查看文件 (带行号) 或目录"""
        p = Path(path)

        if p.is_dir():
            return self._list_directory(p)

        if not p.exists():
            return f"Error: File '{path}' does not exist."

        try:
            content = p.read_text()
        except Exception as e:
            return f"Error reading '{path}': {e}"

        lines = content.split("\n")

        if view_range:
            start = max(1, view_range[0]) if view_range else 1
            end = view_range[1] if len(view_range) > 1 else -1
            if end == -1:
                end = len(lines)
            end = min(end, len(lines))
            selected = lines[start - 1 : end]
            numbered = [f"{i:6d}\t{line}" for i, line in enumerate(selected, start=start)]
        else:
            numbered = [f"{i:6d}\t{line}" for i, line in enumerate(lines, start=1)]

        header = f"Here's the content of {path}:\n"
        return header + "\n".join(numbered)

    def _list_directory(self, p: Path, max_depth: int = 2) -> str:
        """列出目录内容 (最多 2 层)"""
        result_lines = []

        def _walk(current: Path, depth: int, prefix: str = ""):
            if depth > max_depth:
                return
            try:
                entries = sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                result_lines.append(f"{prefix}[Permission denied]")
                return

            for entry in entries:
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    result_lines.append(f"{prefix}{entry.name}/")
                    _walk(entry, depth + 1, prefix + "  ")
                else:
                    result_lines.append(f"{prefix}{entry.name}")

        result_lines.append(f"Contents of {p}:")
        _walk(p, 1)
        return "\n".join(result_lines)

    def _editor_create(self, path: str, file_text: str) -> str:
        """创建新文件"""
        p = Path(path)

        if p.exists():
            return f"Error: File '{path}' already exists. Use str_replace to edit existing files."

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(file_text)
            return f"File created successfully at: {path}"
        except Exception as e:
            return f"Error creating '{path}': {e}"

    def _editor_str_replace(self, path: str, old_str: str, new_str: str) -> str:
        """精确字符串替换"""
        p = Path(path)

        if not p.exists():
            return f"Error: File '{path}' does not exist."

        try:
            content = p.read_text()
        except Exception as e:
            return f"Error reading '{path}': {e}"

        if not old_str:
            return "Error: 'old_str' must not be empty."

        count = content.count(old_str)
        if count == 0:
            return f"Error: 'old_str' not found in '{path}'. Make sure it matches exactly, including whitespace."
        if count > 1:
            return f"Error: 'old_str' found {count} times in '{path}'. Include more context to make it unique."

        # 备份 & 替换
        self._file_backups[path] = content
        new_content = content.replace(old_str, new_str, 1)
        try:
            p.write_text(new_content)
        except Exception as e:
            return f"Error writing '{path}': {e}"

        # 显示编辑结果
        replacement_line = new_content.find(new_str)
        if replacement_line >= 0:
            line_num = new_content[:replacement_line].count("\n") + 1
            return f"The file {path} has been edited. Here's the result of the edit around line {line_num}:\n{self._snippet(new_content, line_num)}"
        return f"The file {path} has been edited successfully."

    def _editor_insert(self, path: str, insert_line: int | None, new_str: str) -> str:
        """在指定行后插入"""
        p = Path(path)

        if not p.exists():
            return f"Error: File '{path}' does not exist."

        if insert_line is None:
            return "Error: 'insert_line' is required for insert command."

        try:
            content = p.read_text()
        except Exception as e:
            return f"Error reading '{path}': {e}"

        lines = content.split("\n")

        if insert_line < 0 or insert_line > len(lines):
            return f"Error: insert_line {insert_line} is out of range [0, {len(lines)}]."

        # 备份 & 插入
        self._file_backups[path] = content
        new_lines = new_str.split("\n")
        lines[insert_line:insert_line] = new_lines
        new_content = "\n".join(lines)

        try:
            p.write_text(new_content)
        except Exception as e:
            return f"Error writing '{path}': {e}"

        return f"The file {path} has been edited. Here's the result around line {insert_line + 1}:\n{self._snippet(new_content, insert_line + 1)}"

    def _editor_undo(self, path: str) -> str:
        """恢复上次编辑"""
        if path not in self._file_backups:
            return f"Error: No edit history for '{path}'."

        backup = self._file_backups.pop(path)
        try:
            Path(path).write_text(backup)
            return f"Last edit to {path} undone successfully."
        except Exception as e:
            return f"Error restoring '{path}': {e}"

    def _snippet(self, content: str, center_line: int, context: int = 4) -> str:
        """获取文件片段 (带行号)"""
        lines = content.split("\n")
        start = max(1, center_line - context)
        end = min(len(lines), center_line + context)
        numbered = [f"{i:6d}\t{lines[i - 1]}" for i in range(start, end + 1)]
        return "\n".join(numbered)

    # -- think --

    def execute_think(self, thought: str) -> str:
        """记录思考，返回确认"""
        return f"Your thought has been logged."

    # -- finish --

    def execute_finish(self, message: str) -> str:
        """返回完成消息 (由 LLMRouter 特殊处理)"""
        return message
