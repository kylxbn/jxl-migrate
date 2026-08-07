import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import migrate


class FakeToolchain:
    def __init__(self, *, cjxl_returncode=0, webp_lossless=True):
        self.cjxl_returncode = cjxl_returncode
        self.webp_lossless = webp_lossless
        self.commands = []

    def __call__(self, command, **kwargs):
        self.commands.append(command)
        executable = command[0]
        if executable == "webpinfo":
            kind = "Lossless" if self.webp_lossless else "Lossy"
            return subprocess.CompletedProcess(command, 0, f"Format: {kind}\n", "")
        if executable == "dwebp":
            destination = Path(command[command.index("-o") + 1])
            destination.write_bytes(b"decoded webp")
            return subprocess.CompletedProcess(command, 0, "", "")
        if executable == "cjxl":
            if self.cjxl_returncode == 0:
                Path(command[2]).write_bytes(b"encoded jxl")
            return subprocess.CompletedProcess(command, self.cjxl_returncode, "", "encode failed")
        raise AssertionError(f"unexpected command: {command}")


class PlanningTests(unittest.TestCase):
    def test_sources_with_the_same_stem_are_skipped_as_a_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "photo.jpg").write_bytes(b"jpeg")
            (root / "photo.png").write_bytes(b"png")

            jobs, skipped = migrate.plan_jobs(root)

            self.assertEqual(jobs, [])
            self.assertEqual(len(skipped), 2)
            self.assertTrue(
                all(result.status is migrate.ResultStatus.SKIPPED for result in skipped)
            )
            self.assertTrue(
                all("multiple sources map" in result.message for result in skipped)
            )

    def test_case_variant_destinations_are_treated_as_a_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "photo.jpg").write_bytes(b"jpeg")
            (root / "PHOTO.png").write_bytes(b"png")

            jobs, skipped = migrate.plan_jobs(root)

            self.assertEqual(jobs, [])
            self.assertEqual(len(skipped), 2)

    def test_apng_extension_is_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "animation.apng"
            source.write_bytes(b"apng")

            jobs, skipped = migrate.plan_jobs(root)

            self.assertEqual(skipped, [])
            self.assertEqual(jobs, [migrate.ConversionJob(source, root / "animation.jxl")])


class ConversionTests(unittest.TestCase):
    def test_progressive_option_is_forwarded_to_cjxl(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "photo.png"
            destination = root / "photo.jxl"
            source.write_bytes(b"png")
            job = migrate.ConversionJob(source, destination)
            toolchain = FakeToolchain()

            with mock.patch("migrate.subprocess.run", side_effect=toolchain):
                result = migrate.process_job(job, migrate.Config(progressive=True))

            self.assertEqual(result.status, migrate.ResultStatus.SUCCESS)
            cjxl_command = next(
                command for command in toolchain.commands if command[0] == "cjxl"
            )
            self.assertIn("-p", cjxl_command)

    def test_existing_destination_is_not_overwritten_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "photo.jpg"
            destination = root / "photo.jxl"
            source.write_bytes(b"jpeg")
            destination.write_bytes(b"existing")
            job = migrate.ConversionJob(source, destination)

            with mock.patch("migrate.subprocess.run") as run:
                result = migrate.process_job(job, migrate.Config())

            self.assertEqual(result.status, migrate.ResultStatus.SKIPPED)
            self.assertEqual(destination.read_bytes(), b"existing")
            run.assert_not_called()

    def test_webp_uses_a_temporary_png_and_deletes_source_only_after_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "photo.webp"
            sibling_png = root / "photo.png"
            destination = root / "photo.jxl"
            source.write_bytes(b"webp")
            sibling_png.write_bytes(b"original png")
            job = migrate.ConversionJob(source, destination)
            toolchain = FakeToolchain()

            with mock.patch("migrate.subprocess.run", side_effect=toolchain):
                result = migrate.process_job(job, migrate.Config(delete=True))

            self.assertEqual(result.status, migrate.ResultStatus.SUCCESS)
            self.assertFalse(source.exists())
            self.assertEqual(sibling_png.read_bytes(), b"original png")
            self.assertEqual(destination.read_bytes(), b"encoded jxl")
            dwebp_command = next(
                command for command in toolchain.commands if command[0] == "dwebp"
            )
            self.assertNotEqual(Path(dwebp_command[-1]), sibling_png)

    def test_webp_source_survives_a_failed_jxl_encode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "photo.webp"
            destination = root / "photo.jxl"
            source.write_bytes(b"webp")
            job = migrate.ConversionJob(source, destination)
            toolchain = FakeToolchain(cjxl_returncode=1)

            with mock.patch("migrate.subprocess.run", side_effect=toolchain):
                result = migrate.process_job(job, migrate.Config(delete=True))

            self.assertEqual(result.status, migrate.ResultStatus.FAILED)
            self.assertTrue(source.exists())
            self.assertFalse(destination.exists())
            self.assertEqual(list(root.glob(".jxl-migrate-*")), [])

    def test_commit_without_overwrite_does_not_replace_a_racing_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            temporary = root / "temporary.jxl"
            destination = root / "photo.jxl"
            temporary.write_bytes(b"new")
            destination.write_bytes(b"existing")

            with self.assertRaises(migrate.DestinationExistsError):
                migrate.commit_output(temporary, destination, overwrite=False)

            self.assertEqual(temporary.read_bytes(), b"new")
            self.assertEqual(destination.read_bytes(), b"existing")


class CliTests(unittest.TestCase):
    def test_empty_directory_exits_successfully_without_dividing_by_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = migrate.main([directory])

            self.assertEqual(exit_code, 0)
            self.assertIn("No supported images found", output.getvalue())


if __name__ == "__main__":
    unittest.main()
