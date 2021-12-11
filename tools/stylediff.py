#!/usr/bin/env python3.8
"""
Script showing a diff combining changes from black and isort.
"""

# Future Imports
from __future__ import annotations

# Standard Library Imports
from abc import ABC, abstractmethod
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, Generator, Optional, Tuple
import asyncio
import dataclasses
import difflib
import os
import sys

# Dependency Imports
import black
import isort
import isort.api
import isort.files
import isort.settings

ROOT_PATH = Path(__file__).parent.parent.resolve()
BLACK_ALLOWED_MODE_KEYS = {
    field.name for field in dataclasses.fields(black.Mode)
}


# FileInfo and Results classes based on
# https://github.com/jack1142/JackCogs/blob/a1015f991c35e7ea9deca6fcf74418326055d63e/.tools/_infogen/results.py
class FileInfo:
    def __init__(self, path: Path, src_contents: str) -> None:
        self.path = path
        self.src_contents = src_contents
        self._dst_contents: Optional[str] = None

    @classmethod
    def from_path(cls, path: Path, *, must_exist: bool = True) -> FileInfo:
        try:
            with path.open("r", encoding="utf-8") as fp:
                return cls(path, fp.read())
        except FileNotFoundError:
            if must_exist:
                raise
            return cls(path, "")

    @property
    def contents(self) -> str:
        if self._dst_contents is None:
            return self.src_contents
        return self._dst_contents

    @property
    def dst_contents(self) -> Optional[str]:
        return self._dst_contents

    @dst_contents.setter
    def dst_contents(self, value: str) -> None:
        self._dst_contents = value

    @property
    def changed(self) -> bool:
        return (
            self._dst_contents is not None
            and self.src_contents != self._dst_contents
        )

    def diff(self) -> str:
        relative_path = self.path.relative_to(ROOT_PATH)
        a_lines = [f"{line}\n" for line in self.src_contents.splitlines()]
        b_lines = [f"{line}\n" for line in self.contents.splitlines()]
        return "".join(
            difflib.unified_diff(
                a_lines,
                b_lines,
                str("a" / relative_path),
                str("b" / relative_path),
                n=5,
            )
        )


class Results:
    def __init__(self) -> None:
        self._files: Dict[Path, FileInfo] = {}

    @property
    def files_changed(self) -> bool:
        return any(file_info.changed for file_info in self._files.values())

    def get_file(self, path: Path) -> str:
        if (file_info := self._files.get(path)) is None:
            self._files[path] = file_info = FileInfo.from_path(path)

        return file_info.contents

    def update_file(self, path: Path, dst_contents: str) -> None:
        if (file_info := self._files.get(path)) is None:
            self._files[path] = file_info = FileInfo.from_path(
                path, must_exist=False
            )

        file_info.dst_contents = dst_contents

    def iter_changed_files(self) -> Generator[FileInfo, None, None]:
        for file_info in self._files.values():
            if file_info.changed:
                yield file_info

    def print(self) -> None:
        changed = 0
        unchanged = 0
        for file_info in self._files.values():
            if file_info.changed:
                print(file_info.diff())
                print(
                    f"Would reformat {file_info.path.relative_to(ROOT_PATH)}"
                )
                changed += 1
            else:
                unchanged += 1
        if changed:
            print(
                "Oh no! \N{COLLISION SYMBOL} \N{BROKEN HEART} \N{COLLISION SYMBOL}"
            )
            if changed > 1:
                print(f"{changed} files would be reformatted, ", end="")
            else:
                print("1 file would be reformatted, ", end="")
        else:
            print("All done! \N{SPARKLES} \N{SHORTCAKE} \N{SPARKLES}")
        print(f"{unchanged} files would be left unchanged.")


class Formatter(ABC):
    @abstractmethod
    def __init__(self, results: Results) -> None:
        raise NotImplementedError

    @abstractmethod
    def format_all(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def format_file(self, src_contents: str) -> str:
        raise NotImplementedError


class BlackFormatter(Formatter):
    def __init__(self, results: Results) -> None:
        self.results = results
        config_file = black.find_pyproject_toml((str(ROOT_PATH),))
        if config_file is not None:
            self.config = black.parse_pyproject_toml(config_file)
        else:
            self.config = {}
        self.mode = black.Mode(
            **{
                k: v
                for k, v in self.config.items()
                if k in BLACK_ALLOWED_MODE_KEYS
            }
        )

    def format_all(self) -> None:
        # concurrency is needed here for significant speed gains
        executor = ProcessPoolExecutor(max_workers=os.cpu_count())
        try:
            asyncio.run(self._format_all(executor))
        finally:
            executor.shutdown()

    async def _format_all(self, executor: ProcessPoolExecutor) -> None:
        include = black.re_compile_maybe_verbose(
            self.config.get("include", black.DEFAULT_INCLUDES)
        )
        exclude = black.re_compile_maybe_verbose(
            self.config.get("exclude", black.DEFAULT_EXCLUDES)
        )
        # commented code will be part of next version of Black
        #
        # extend_exclude = None
        # if "extend_exclude" in self.config:
        #     extend_exclude = re.compile(self.config["extend_exclude"])
        force_exclude = None
        if "force_exclude" in self.config:
            force_exclude = black.re_compile_maybe_verbose(
                self.config["force_exclude"]
            )
        gitignore = black.get_gitignore(ROOT_PATH)

        loop = asyncio.get_running_loop()
        aws = [
            loop.run_in_executor(
                executor, self._update_file, file, self.results.get_file(file)
            )
            for file in black.gen_python_files(
                ROOT_PATH.iterdir(),
                ROOT_PATH,
                include,
                exclude,
                # extend_exclude,
                force_exclude,
                black.Report(),
                gitignore,
            )
        ]
        for coro in asyncio.as_completed(aws):
            self.results.update_file(*(await coro))

    def _update_file(self, file: Path, src_contents: str) -> Tuple[Path, str]:
        return file, self.format_file(src_contents)

    def format_file(self, src_contents: str) -> str:
        try:
            return black.format_file_contents(
                src_contents, fast=False, mode=self.mode
            )
        except black.NothingChanged:
            return src_contents


class IsortFormatter(Formatter):
    def __init__(self, results: Results) -> None:
        self.results = results
        self.config = isort.settings.Config(settings_path=ROOT_PATH)

    def format_all(self) -> None:
        for path in isort.files.find([str(ROOT_PATH)], self.config, [], []):
            file = Path(path)
            src_contents = self.results.get_file(file)
            self.results.update_file(file, self.format_file(src_contents))

    def format_file(self, src_contents: str) -> str:
        return isort.api.sort_code_string(src_contents, config=self.config)


def main() -> None:
    # DEP-WARN
    # While the Black one might be a bit annoying, the API provided by Black is not stable.
    # Please ensure that this script is accurate when updating Black.
    if black.__version__ != "20.8b1":
        print("`stylediff.py` script only supports Black 20.8b1.")
        sys.exit(1)
    if isort.__version__.split(".", maxsplit=1)[0] != "5":
        print("`stylediff.py` script only supports isort 5.")
        sys.exit(1)

    results = Results()
    formatters = [BlackFormatter(results)]
    for formatter in formatters:
        formatter.format_all()
    results.print()
    sys.exit(int(results.files_changed))


if __name__ == "__main__":
    main()
