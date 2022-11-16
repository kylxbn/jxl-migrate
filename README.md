# jxl-migrate

`jxl-migrate` is a simple Python 3 script to convert all applicable image files recursively in a folder to JPEG XL (JXL, `image/jxl`).

In case the conversion of an image is successful, the original image can be deleted and the JXL file will be all that's left.

## Features

`jxl-migrate` will try to do the following:

* Convert *JPEG and JPG* files into *lossless transcoded or lossy JXL*
* Convert *PNG* files into *lossless JXL*
* Convert *lossless WebP* into *lossless or lossy JXL*
* Convert *lossy WebP* into *lossy JXL* (`-d 1`)
* Convert *GIF* files into *lossless or lossy animated JXL*

The resulting JXL files will **not** be progressively encoded.

If desired, the original source image can be deleted automatically.

`jxl-migrate` also supports rudimentary error handling. In case it fails to convert a file because `cjxl` or `dwebp` did not do its job properly, then the source file will not be deleted even if you tell it to.

`jxl-migrate` will also report the before-and-after total filesizes along with a percentage of how much file space you saved by converting to JXL.

## Requirements

`jxl-migrate` requires the following. All binaries should be added to the system's `PATH` environment variable so Python can run them.

* Python 3.x (tested working on 3.10.7)
* The `webpinfo` binary (to check if a WebP is lossless or lossy so that it can convert the file accordingly)
* The `cjxl` binary (to actually convert images)
* The `dwebp` binary (to decode WebP images into PNG images first because `cjxl` does not support WebP directly)

## Usage

Just run the script on Python while providing the required parameters and it will process all images there recursively one by one. The images are processed in multiple threads (because of that, the output is quite hard to follow but I'm thinking of a way to improve that)

### Valid arguments

```sh
python migrate.py [directory] [--delete] [--lossyjpg] [--lossywebp] [--lossygif]
```

- **directory**: the folder to process (required)
- **--delete**: delete original source file if successfully converted (default FALSE)
- **--lossyjpg**: convert JPEGs lossily (`-d 1`) instead of lossless transcode (default FALSE)
- **--lossywebp**: convert lossless WebPs lossily (`-d 1`). Lossy WebPs will always be converted lossily (default FALSE)
- **--lossygif**: convert GIFs lossily (`-d 1`) (default FALSE)

### Example

```sh
python migrate.py /home/kylxbn/Photos --lossyjpg --delete
```

## Contributing

I welcome any pull requests that will improve the script. Please feel free to submit pull requests and I'll check them out. There is no coding guide, no rules to follow. As long as you tested your pull request and it works, just submit it! Thanks!

### Contributors!

Thank you very much to everyone who contributed code to this humble Python script. I really appreciate it, and I'm sure everyone trying to adopt JPEG XL appreciates it, too!

[perk11](https://github.com/perk11) - Keep original file mtime in converted JXL, implement multithreading ([#6](https://github.com/kylxbn/jxl-migrate/pull/6))

## Disclaimer

While I did use this script to migrate my entire image folder and did not notice any issues, I still cannot guarantee that the error handling in this script is perfect and I can't help it if files get lost or damaged or anything. I cannot take responsibility for that. I did my best to avoid that, since I actually intend to use this script myself, but you never know.

The detection of file format is done purely by file extension (not case sensitive), so in case a file ends with (for example) `.jpg` but is not actually an image, then the script will be confused and try to convert it. However, `cjxl` should fail and the script should detect that. In that case, the original (impostor) `.jpg` file will not be deleted. At least that's how I intended it to function.

The script runs assuming you have all requirements satisfied and does not check if there are missing requirements. If a requirement is missing, the script might throw an error and crash. So make sure you have all requirements before running this script.

While I can't think of any bad reason (besides having a left-over PNG file converted from the original WebP with the original WebP file already deleted), cancelling the script by `Ctrl+C` or another way might be harmful and cause corrupted files. You have been warned.

# License

GNU General Public License 3 (GPL-3)

Please check `LICENSE` file for the complete license.
