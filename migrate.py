#!/usr/bin/env python3

"""
jxl-migrate - Convert images to JPEG XL (JXL) format
Copyright (C) 2021-present Kyle Alexander Buan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from functools import partial
from pathlib import Path
from typing import Sequence


__version__ = "v1.0"

SUPPORTED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".apng", ".gif", ".webp"})
JPEG_EXTENSIONS = frozenset({".jpg", ".jpeg"})


@dataclass(frozen=True)
class Config:
    delete: bool = False
    lossy_jpg: bool = False
    lossy_webp: bool = False
    lossy_gif: bool = False
    slow: bool = False
    progressive: bool = False
    overwrite: bool = False
    jobs: int = 1


@dataclass(frozen=True)
class ConversionJob:
    source: Path
    destination: Path


class ResultStatus(Enum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class ConversionResult:
    job: ConversionJob
    status: ResultStatus
    source_size: int = 0
    output_size: int | None = None
    message: str = ""


class ConversionError(RuntimeError):
    """Raised when an external image conversion command fails."""


class DestinationExistsError(ConversionError):
    """Raised when a destination appears while a conversion is running."""


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def default_job_count() -> int:
    # cjxl may use multiple threads itself, so a modest default avoids spawning
    # one heavyweight encoder for every logical CPU on large machines.
    return min(4, os.cpu_count() or 1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recursively convert supported images to JPEG XL.",
    )
    parser.add_argument("directory", type=Path, help="folder to process recursively")
    parser.add_argument(
        "--delete",
        action="store_true",
        help="delete each source only after its JXL is safely written",
    )
    parser.add_argument(
        "--lossyjpg",
        action="store_true",
        help="convert JPEG files lossily with -d 1",
    )
    parser.add_argument(
        "--lossywebp",
        action="store_true",
        help="convert lossless WebP files lossily with -d 1",
    )
    parser.add_argument(
        "--lossygif",
        action="store_true",
        help="convert GIF files lossily with -d 1",
    )
    parser.add_argument(
        "--slow",
        action="store_true",
        help="use higher cjxl encoding effort (-e 9)",
    )
    parser.add_argument(
        "--progressive",
        action="store_true",
        help="enable more progressive/responsive JXL decoding (-p)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace existing JXL destinations (disabled by default)",
    )
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=default_job_count(),
        metavar="N",
        help="maximum concurrent conversions (default: %(default)s)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def destination_for(source: Path) -> Path:
    return source.with_suffix(".jxl")


def discover_sources(root: Path) -> list[Path]:
    sources: list[Path] = []
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories.sort()
        for filename in sorted(filenames):
            source = Path(directory, filename)
            if source.suffix.lower() in SUPPORTED_EXTENSIONS:
                sources.append(source)
    return sources


def plan_jobs(root: Path) -> tuple[list[ConversionJob], list[ConversionResult]]:
    destinations: dict[str, list[ConversionJob]] = defaultdict(list)
    for source in discover_sources(root):
        destination = destination_for(source)
        # Case-folding is deliberately conservative: it prevents --overwrite
        # races on case-insensitive filesystems even when running on a platform
        # that cannot reliably identify the filesystem's case behavior.
        collision_key = str(destination.resolve(strict=False)).casefold()
        destinations[collision_key].append(ConversionJob(source, destination))

    jobs: list[ConversionJob] = []
    skipped: list[ConversionResult] = []
    for matching_jobs in destinations.values():
        if len(matching_jobs) == 1:
            jobs.append(matching_jobs[0])
            continue

        destinations_list = ", ".join(
            str(job.destination) for job in matching_jobs
        )
        source_list = ", ".join(str(job.source) for job in matching_jobs)
        message = (
            f"multiple sources map to conflicting destinations "
            f"({destinations_list}): {source_list}"
        )
        for job in matching_jobs:
            try:
                source_size = job.source.stat().st_size
            except OSError:
                source_size = 0
            skipped.append(
                ConversionResult(
                    job,
                    ResultStatus.SKIPPED,
                    source_size=source_size,
                    message=message,
                )
            )

    jobs.sort(key=lambda job: str(job.source))
    skipped.sort(key=lambda result: str(result.job.source))
    return jobs, skipped


def command_error(command: Sequence[str], process: subprocess.CompletedProcess[str]) -> str:
    details = (process.stderr or process.stdout).strip()
    if len(details) > 2_000:
        details = "..." + details[-2_000:]
    suffix = f": {details}" if details else ""
    return f"{command[0]} exited with status {process.returncode}{suffix}"


def run_checked(command: Sequence[str], expected_output: Path | None = None) -> str:
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise ConversionError(f"could not run {command[0]}: {exc}") from exc

    if process.returncode != 0:
        raise ConversionError(command_error(command, process))
    if expected_output is not None:
        try:
            if not expected_output.is_file() or expected_output.stat().st_size == 0:
                raise ConversionError(f"{command[0]} did not create a valid output file")
        except OSError as exc:
            raise ConversionError(f"could not inspect {expected_output}: {exc}") from exc
    return process.stdout


def is_webp_lossless(source: Path) -> bool:
    output = run_checked(["webpinfo", str(source)])
    if "Format: Lossless" in output:
        return True
    if "Format: Lossy" in output:
        return False
    raise ConversionError("webpinfo did not report whether the WebP is lossless")


def decode_webp(source: Path, destination: Path) -> None:
    run_checked(["dwebp", str(source), "-o", str(destination)], destination)


def encode_jxl(
    source: Path,
    destination: Path,
    *,
    lossy: bool,
    lossless_jpeg: bool,
    slow: bool,
    progressive: bool,
) -> None:
    command = [
        "cjxl",
        str(source),
        str(destination),
        "-d",
        "1" if lossy else "0",
        "-j",
        "1" if lossless_jpeg else "0",
    ]
    if slow:
        command.extend(["-e", "9"])
    if progressive:
        command.append("-p")
    run_checked(command, destination)


def commit_output(temporary: Path, destination: Path, *, overwrite: bool) -> None:
    if overwrite:
        os.replace(temporary, destination)
        return

    try:
        # The temporary directory is inside destination.parent, so this creates
        # the destination atomically without overwriting a file created mid-run.
        os.link(temporary, destination)
    except FileExistsError as exc:
        raise DestinationExistsError(
            f"destination already exists: {destination} (use --overwrite to replace it)"
        ) from exc
    except OSError as exc:
        raise ConversionError(f"could not create {destination}: {exc}") from exc
    temporary.unlink()


def encoding_options(
    source: Path,
    config: Config,
    temporary_directory: Path,
) -> tuple[Path, bool, bool]:
    extension = source.suffix.lower()
    if extension in JPEG_EXTENSIONS:
        return source, config.lossy_jpg, not config.lossy_jpg
    if extension == ".webp":
        lossless = is_webp_lossless(source)
        decoded = temporary_directory / "decoded.png"
        decode_webp(source, decoded)
        return decoded, config.lossy_webp if lossless else True, False
    if extension == ".gif":
        return source, config.lossy_gif, False
    return source, False, False


def process_job(job: ConversionJob, config: Config) -> ConversionResult:
    try:
        source_stat = job.source.stat()
    except OSError as exc:
        return ConversionResult(
            job,
            ResultStatus.FAILED,
            message=f"could not inspect source: {exc}",
        )

    if not config.overwrite and job.destination.exists():
        return ConversionResult(
            job,
            ResultStatus.SKIPPED,
            source_size=source_stat.st_size,
            message=(
                f"destination already exists: {job.destination} "
                "(use --overwrite to replace it)"
            ),
        )

    output_size: int | None = None
    committed = False
    try:
        with tempfile.TemporaryDirectory(
            prefix=".jxl-migrate-",
            dir=job.destination.parent,
        ) as temporary_name:
            temporary_directory = Path(temporary_name)
            input_path, lossy, lossless_jpeg = encoding_options(
                job.source, config, temporary_directory
            )
            temporary_output = temporary_directory / "output.jxl"
            encode_jxl(
                input_path,
                temporary_output,
                lossy=lossy,
                lossless_jpeg=lossless_jpeg,
                slow=config.slow,
                progressive=config.progressive,
            )
            os.utime(
                temporary_output,
                ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
            )
            output_size = temporary_output.stat().st_size
            commit_output(temporary_output, job.destination, overwrite=config.overwrite)
            committed = True

        if config.delete:
            try:
                job.source.unlink()
            except OSError as exc:
                return ConversionResult(
                    job,
                    ResultStatus.FAILED,
                    source_size=source_stat.st_size,
                    output_size=output_size,
                    message=f"converted successfully, but could not delete source: {exc}",
                )

        return ConversionResult(
            job,
            ResultStatus.SUCCESS,
            source_size=source_stat.st_size,
            output_size=output_size,
        )
    except (ConversionError, OSError) as exc:
        message = str(exc)
        if committed:
            message = f"output was created, but post-processing failed: {message}"
        return ConversionResult(
            job,
            ResultStatus.FAILED,
            source_size=source_stat.st_size,
            output_size=output_size if committed else None,
            message=message,
        )


def missing_dependencies(jobs: Sequence[ConversionJob]) -> list[str]:
    required = {"cjxl"}
    if any(job.source.suffix.lower() == ".webp" for job in jobs):
        required.update({"dwebp", "webpinfo"})
    return sorted(command for command in required if shutil.which(command) is None)


def format_size(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def print_result(result: ConversionResult) -> None:
    if result.status is ResultStatus.SUCCESS:
        assert result.output_size is not None
        print(
            f"Converted {result.job.source} -> {result.job.destination} "
            f"({format_size(result.source_size)} -> {format_size(result.output_size)})"
        )
        return

    label = "Skipped" if result.status is ResultStatus.SKIPPED else "FAILED"
    print(f"{label} {result.job.source}: {result.message}", file=sys.stderr)


def print_summary(results: Sequence[ConversionResult]) -> None:
    successful = [result for result in results if result.status is ResultStatus.SUCCESS]
    skipped = sum(result.status is ResultStatus.SKIPPED for result in results)
    failed = sum(result.status is ResultStatus.FAILED for result in results)

    print("\nSummary")
    print(f"  Converted: {len(successful)}")
    print(f"  Skipped:   {skipped}")
    print(f"  Failed:    {failed}")

    if not successful:
        print("  Size reduction: n/a")
        return

    before = sum(result.source_size for result in successful)
    after = sum(result.output_size or 0 for result in successful)
    reduction = (1 - after / before) * 100 if before else 0.0
    print(f"  Successful input size: {format_size(before)}")
    print(f"  JXL output size:       {format_size(after)}")
    print(f"  Size reduction:        {reduction:.2f}%")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    namespace = parser.parse_args(argv)
    root = namespace.directory.expanduser()
    if not root.exists():
        parser.error(f"directory does not exist: {root}")
    if not root.is_dir():
        parser.error(f"not a directory: {root}")

    config = Config(
        delete=namespace.delete,
        lossy_jpg=namespace.lossyjpg,
        lossy_webp=namespace.lossywebp,
        lossy_gif=namespace.lossygif,
        slow=namespace.slow,
        progressive=namespace.progressive,
        overwrite=namespace.overwrite,
        jobs=namespace.jobs,
    )
    jobs, results = plan_jobs(root)

    print("jxl-migrate - Convert images to JPEG XL (JXL) format")
    print(__version__)
    print(f"Source: {root}")

    if not jobs and not results:
        print("No supported images found.")
        return 0

    missing = missing_dependencies(jobs) if jobs else []
    if missing:
        print(f"Missing required command(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    for result in results:
        print_result(result)

    worker = partial(process_job, config=config)
    try:
        with ThreadPoolExecutor(max_workers=min(config.jobs, len(jobs) or 1)) as executor:
            futures = [executor.submit(worker, job) for job in jobs]
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print_result(result)
    except KeyboardInterrupt:
        print(
            "\nInterrupted. Conversions that completed during shutdown may remain in place.",
            file=sys.stderr,
        )
        return 130

    print_summary(results)
    return 1 if any(result.status is not ResultStatus.SUCCESS for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
