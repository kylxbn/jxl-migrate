# jxl-migrate

`jxl-migrate` is a Python 3 command-line tool that recursively converts supported image files to JPEG XL (JXL, `image/jxl`).

Original images can optionally be deleted. A source is deleted only after its final JXL output has been written successfully.

## Features

`jxl-migrate` will try to do the following:

* Convert *JPEG and JPG* files into *lossless transcoded or lossy JXL*
* Convert *PNG and animated PNG (APNG)* files into *lossless JXL*
* Convert *lossless WebP* into *lossless or lossy JXL*
* Convert *lossy WebP* into *lossy JXL* (`-d 1`)
* Convert *GIF* files into *lossless or lossy animated JXL*
* Optionally enable more progressive and responsive decoding
* Convert files concurrently with a configurable worker limit
* Preserve source access and modification timestamps on converted files
* Write outputs through per-conversion temporary directories before committing them

Progressive encoding is optional. Pass `--progressive` to enable `cjxl`'s more progressive and responsive decoding mode (`-p`). This can improve how quickly a partial image becomes useful while downloading, but it may produce significantly larger files—especially for lossless or animated inputs.

### APNG timing note

APNG files are supported whether they use a `.png` or `.apng` extension. `jxl-migrate` passes them directly to `cjxl`, which detects animation from the PNG animation-control and frame-data chunks.

With `cjxl` 0.12.0, fractional APNG frame delays may be rounded down to whole milliseconds. For example, the included 24 FPS demo uses a delay of exactly `1/24` second per frame, but `cjxl` stores it as 41 milliseconds. Its frames, pixels, loop behavior, and animation are preserved, but playback is approximately 1.6% faster. Keep this timing limitation in mind when exact animation timing matters.

If desired, the original source image can be deleted automatically.

Failed conversions keep their source files and produce a nonzero exit status. Existing JXL files are not replaced unless `--overwrite` is supplied.

If multiple source files would map to the same destination—for example, `photo.jpg` and `photo.png` both mapping to `photo.jxl`—all conflicting sources are skipped. Rename or move them before retrying so the intended output is unambiguous.

At the end of a run, `jxl-migrate` reports success, skip, and failure counts. Its size comparison includes successful conversions only.

## Requirements

`jxl-migrate` requires the following. All binaries should be added to the system's `PATH` environment variable so Python can run them.

* Python 3.10 or newer (tested working on 3.14.6)
* The `webpinfo` binary (to check if a WebP is lossless or lossy so that it can convert the file accordingly)
* The `cjxl` binary (to actually convert images)
* The `dwebp` binary (to decode WebP images into PNG images first because `cjxl` does not support WebP directly)

The `cjxl` command syntax used by this script is compatible and tested with libjxl 0.12. The `webpinfo` and `dwebp` calls have been tested with libwebp 1.6.0. Using the [latest libjxl release](https://github.com/libjxl/libjxl/releases/latest) is strongly recommended because recent releases include security fixes.

For JPEG input, the script does not rely on `cjxl` defaults: it explicitly requests lossless JPEG recompression with `-d 0 -j 1`, or pixel-based lossy encoding with `-d 1 -j 0` when `--lossyjpg` is used.

## Usage

Run the script with the directory to process. File discovery is recursive, while conversion is concurrent and completion messages are printed from the main process so they remain readable.

### Valid arguments

```sh
python migrate.py [directory] [--delete] [--lossyjpg] [--lossywebp] [--lossygif] [--slow] [--progressive] [--overwrite] [--jobs N]
```

- **directory**: the folder to process (required)
- **--delete**: delete original source file if successfully converted (default FALSE)
- **--lossyjpg**: convert JPEGs lossily (`-d 1`) instead of lossless transcode (default FALSE)
- **--lossywebp**: convert lossless WebPs lossily (`-d 1`). Lossy WebPs will always be converted lossily (default FALSE)
- **--lossygif**: convert GIFs lossily (`-d 1`) (default FALSE)
- **--slow**: use higher `cjxl` encoding effort (`-e 9`) for generally improved compression at the cost of encoding speed (default FALSE)
- **--progressive**: enable more progressive/responsive decoding (`-p`), potentially at the cost of a larger output (default FALSE)
- **--overwrite**: atomically replace existing JXL destinations (default FALSE)
- **--jobs N**: run at most `N` conversions concurrently (default: the smaller of 4 or the available CPU count)

### Example

```sh
python migrate.py /home/kylxbn/Photos --lossyjpg --slow --progressive --delete --jobs 2
```

Use `python migrate.py --help` to see the complete command-line reference.

### Exit status

- **0**: every discovered source was converted successfully, or no supported images were found
- **1**: one or more sources failed or were skipped
- **2**: invalid arguments or a required command was missing
- **130**: the run was interrupted

## Contributing

I welcome any pull requests that will improve the script. Please feel free to submit pull requests and I'll check them out. There is no coding guide, no rules to follow. As long as you tested your pull request and it works, just submit it! Thanks!

### Contributors!

Thank you very much to everyone who contributed code to this humble Python script. I really appreciate it, and I'm sure everyone trying to adopt JPEG XL appreciates it, too!

[perk11](https://github.com/perk11) - Keep original file mtime in converted JXL, implement multithreading ([#6](https://github.com/kylxbn/jxl-migrate/pull/6))

## Disclaimer

Image conversion and deletion always carry some risk, so keep backups when processing valuable files. Without `--delete`, source images are never intentionally removed. With `--delete`, each source is retained until its JXL output has been successfully committed.

The detection of file format is done purely by file extension (not case sensitive), so in case a file ends with (for example) `.jpg` but is not actually an image, then the script will be confused and try to convert it. However, `cjxl` should fail and the script should detect that. In that case, the original (impostor) `.jpg` file will not be deleted. At least that's how I intended it to function.

The script checks for required commands before conversion begins. `webpinfo` and `dwebp` are required only when the run contains WebP sources.

Temporary PNG and JXL files are isolated from source filenames and cleaned up after each conversion. Final outputs are committed only after `cjxl` reports success and creates a nonempty file.

## Development

The regression suite uses Python's standard library and does not invoke the real image conversion binaries:

```sh
python -m unittest discover -s tests -v
```

# License

GNU General Public License 3 (GPL-3)

Please check `LICENSE` file for the complete license.
