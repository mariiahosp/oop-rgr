import re
from pathlib import Path

from models.project import Project
from models.source_file import IncludeRef, SourceFile


class IncludeAnalyzer:
    MAX_PREVIEW_LINES = 10
    MAX_DESCRIPTION_LENGTH = 120

    _INCLUDE_PATTERN = re.compile(r'^\s*#\s*include\s*(?:<([^>]+)>|"([^"]+)")')
    _CONDITION_PATTERN = re.compile(
        r"^\s*#\s*(ifdef|ifndef|if|elif|else|endif)\b(.*)"
    )
    _ENTRY_PATTERN = re.compile(r"\b(?:w?WinMain|_tWinMain|wmain|main)\s*\(")

    def analyze(self, project: Project) -> list[SourceFile]:
        files_by_name = {path.name: path for path in project.get_source_files()}
        sources: list[SourceFile] = []

        for path in project.get_source_files():
            source = SourceFile(path)
            text = self._read_text(path)
            active = self._active_lines(text)
            for include in self._extract_includes(active, files_by_name):
                source.add_include(include)
            source.preview_lines = self._preview_lines(text, active)
            source.description = self._description(text)
            sources.append(source)

        return sources

    def _read_text(self, path: Path) -> str:
        for encoding in ("utf-8-sig", "cp1251"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="replace")

    def _strip_comments(self, text: str) -> str:
        """Removes comments but keeps line breaks, so line numbers stay the same."""
        result: list[str] = []
        index, length = 0, len(text)
        in_block = False

        while index < length:
            char = text[index]
            following = text[index + 1] if index + 1 < length else ""

            if in_block:
                if char == "*" and following == "/":
                    in_block = False
                    index += 2
                    continue
                if char == "\n":
                    result.append(char)
                index += 1
                continue

            if char == "/" and following == "*":
                in_block = True
                result.append(" ")
                index += 2
                continue

            if char == "/" and following == "/":
                while index < length and text[index] != "\n":
                    index += 1
                continue

            if char in "\"'":
                end = index + 1
                while end < length and text[end] not in (char, "\n"):
                    end += 2 if text[end] == "\\" else 1
                result.append(text[index:end + 1])
                index = end + 1
                continue

            result.append(char)
            index += 1

        return "".join(result)

    def _active_lines(self, text: str) -> list[str | None]:
        """Returns code lines without comments; lines inside `#if 0` become None."""
        lines: list[str | None] = []
        branches: list[str] = []

        for line in self._strip_comments(text).splitlines():
            match = self._CONDITION_PATTERN.match(line)
            if match is not None:
                keyword, condition = match.group(1), match.group(2).strip()
                if keyword.startswith("if"):
                    if keyword == "if" and condition == "0":
                        branches.append("disabled")
                    elif keyword == "if" and condition == "1":
                        branches.append("enabled")
                    else:
                        branches.append("unknown")
                elif keyword in ("elif", "else") and branches:
                    if branches[-1] == "enabled":
                        branches[-1] = "disabled"
                    elif branches[-1] == "disabled":
                        branches[-1] = "unknown"
                elif keyword == "endif" and branches:
                    branches.pop()
                lines.append(line)
                continue

            lines.append(None if "disabled" in branches else line)

        return lines

    def _extract_includes(
        self,
        lines: list[str | None],
        files_by_name: dict[str, Path],
    ) -> list[IncludeRef]:
        includes: list[IncludeRef] = []

        for line in lines:
            if line is None:
                continue
            match = self._INCLUDE_PATTERN.match(line)
            if match is None:
                continue

            system_name, local_name = match.group(1), match.group(2)
            if system_name is not None:
                includes.append(IncludeRef(system_name.strip(), is_system=True))
                continue

            name = local_name.strip()
            includes.append(
                IncludeRef(
                    name,
                    is_system=False,
                    resolved=files_by_name.get(Path(name.replace("\\", "/")).name),
                )
            )

        return includes

    def _preview_lines(self, text: str, active: list[str | None]) -> list[str]:
        """Builds a short listing like in the lecture: includes separated by '...'."""
        original = text.splitlines()
        shown: list[str] = []
        skipped = False

        for index, line in enumerate(original):
            stripped = line.strip()
            if not stripped:
                continue

            code = active[index] if index < len(active) else None
            is_header_comment = not shown and not skipped and stripped.startswith(
                ("//", "/*")
            )
            is_include = code is not None and self._INCLUDE_PATTERN.match(code)
            is_entry = code is not None and self._ENTRY_PATTERN.search(code)

            if not (is_header_comment or is_include or is_entry):
                skipped = True
                continue

            if skipped and shown:
                shown.append("...")
            shown.append(stripped)
            skipped = False

        if skipped and shown:
            shown.append("...")

        if not any(line != "..." for line in shown):
            shown = self._first_code_lines(original)

        if len(shown) > self.MAX_PREVIEW_LINES:
            shown = shown[:self.MAX_PREVIEW_LINES - 1] + ["..."]
        return shown

    def _first_code_lines(self, lines: list[str]) -> list[str]:
        code = [line.strip() for line in lines if line.strip()]
        limit = self.MAX_PREVIEW_LINES - 1
        if len(code) > limit:
            return code[:limit] + ["..."]
        return code

    def _description(self, text: str) -> str:
        """Takes the leading comment block of a file as its human readable description."""
        parts: list[str] = []
        in_block = False

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped and not parts and not in_block:
                continue

            if in_block:
                if "*/" in stripped:
                    stripped = stripped.split("*/", 1)[0]
                    in_block = False
                parts.append(stripped.lstrip("*"))
                if not in_block:
                    break
                continue

            if stripped.startswith("//"):
                parts.append(stripped[2:])
                continue

            if stripped.startswith("/*") and not parts:
                body = stripped[2:]
                if "*/" in body:
                    parts.append(body.split("*/", 1)[0])
                    break
                parts.append(body)
                in_block = True
                continue

            break

        words = []
        for part in parts:
            cleaned = part.strip(" /*-=\t")
            if cleaned and "{{" not in cleaned:
                words.append(cleaned)

        description = " ".join(words)
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            description = description[:self.MAX_DESCRIPTION_LENGTH - 3].rstrip() + "..."
        return description
