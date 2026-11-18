import re
from pathlib import Path

from models.project import Project
from models.source_file import IncludeRef, SourceFile


class IncludeAnalyzer:
    _INCLUDE_PATTERN = re.compile(r'^\s*#\s*include\s*(?:<([^>]+)>|"([^"]+)")')

    def analyze(self, project: Project) -> list[SourceFile]:
        files_by_name = {path.name: path for path in project.get_source_files()}
        sources: list[SourceFile] = []

        for path in project.get_source_files():
            source = SourceFile(path)
            text = self._read_text(path)
            source.preview_lines = self._preview_lines(text)
            for include in self._extract_includes(text, files_by_name):
                source.add_include(include)
            sources.append(source)

        return sources

    def _read_text(self, path: Path) -> str:
        for encoding in ("utf-8", "cp1251"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="replace")

    def _preview_lines(self, text: str) -> list[str]:
        lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lines.append(stripped)
            if len(lines) == 6:
                break
        return lines

    def _extract_includes(
        self,
        text: str,
        files_by_name: dict[str, Path],
    ) -> list[IncludeRef]:
        includes: list[IncludeRef] = []

        for line in text.splitlines():
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
                    resolved=files_by_name.get(Path(name).name),
                )
            )

        return includes
