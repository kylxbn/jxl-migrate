#!/usr/bin/env python

'''
jxl-migrate - Convert images to JPEG XL (JXL) format
Copyright (C) 2021-present Kyle Alexander Buan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''

import os, sys
import subprocess
import time
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from subprocess import check_output

fsbefore = 0
fsafter = 0

arguments = {}

def is_webp_lossless(p):
    res = check_output(args=[
        'webpinfo',
        p
    ], text=True)

    return 'Format: Lossless' in res

def convert(p, lossy=False, remove=False):
    res = '.'.join(p.split('.')[0:-1]) + '.jxl'
    proc = subprocess.run(args=[
        'cjxl',
        p,
        res,
        '-d',
        '1' if lossy else '0'
    ], capture_output=True)

    if proc.returncode != 0 or not os.path.exists(res):
        return None
    else:
        os.utime(res, (time.time(), os.path.getmtime(p)))
        if remove:
            os.remove(p)
        return res

def decode(p, remove=False):
    res = '.'.join(p.split('.')[0:-1]) + '.png'

    proc = subprocess.run(args=[
        'dwebp',
        p,
        '-o',
        res
    ], capture_output=True)

    if proc.returncode != 0 or not os.path.exists(res):
        return None
    else:
        os.utime(res, (time.time(), os.path.getmtime(p)))
        if remove:
            os.remove(p)
        return res
def handle_file(filename, root):
    global fsbefore
    global fsafter

    extension = filename.split('.')[-1].lower()
    if extension in ['jpg', 'jpeg', 'png', 'apng', 'gif', 'webp']:
        fullpath = os.path.join(root, filename)
        filesize = os.path.getsize(fullpath)
        fsbefore += filesize
        print('    Found ' + fullpath)
        if extension in ['jpg', 'jpeg']:
            print('        Converting JPG to JXL')
            ret = convert(fullpath, lossy=arguments['lossyjpg'], remove=arguments['delete'])
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['png']:
            print('        Converting PNG to JXL')
            ret = convert(fullpath, remove=arguments['delete'])
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['apng']:
            print('        Converting APNG to JXL')
            ret = convert(fullpath, remove=arguments['delete'])
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['gif']:
            print('        Converting GIF to JXL')
            ret = convert(fullpath, remove=arguments['delete'])
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['webp']:
            print('        Converting WebP to JXL')
            webp_is_lossless = is_webp_lossless(fullpath)
            ret = decode(fullpath, remove=arguments['delete'])
            if ret is not None:
                if webp_is_lossless:
                    ret = convert(ret, lossy=arguments['lossywebp'], remove=True)
                    if ret is not None:
                        filesize = os.path.getsize(ret)
                        fsafter += filesize
                    else:
                        print('        Conversion FAILED: ', fullpath)
                else:
                    ret = convert(ret, lossy=True)
                    if ret is not None:
                        filesize = os.path.getsize(ret)
                        fsafter += filesize
                    else:
                        print('        Conversion FAILED: ', fullpath)
            else:
                print('        Conversion FAILED: ', fullpath)
    else:
        if (extension != 'jxl'):
            print('    Not supported: ' + filename)
def try_handle_file(filename, root):
    try:
        handle_file(filename, root)
    except Exception as inst:
        print('Error processing ' + os.path.join(root, filename) + ': ', inst)

def run():
    print('jxl-migrate - Convert images to JPEG XL (JXL) format\n')

    if len(sys.argv) <= 1:
        print('Program usage:')
        print('migrate.py [directory] [--delete] [--lossyjpg]\n')
        print('directory: the folder to process')
        print('--delete: delete original source files if conversion succeeded (default FALSE)')
        print('--lossyjpg: convert JPEG files lossily (-d 1) (default FALSE)')
        print('--lossywebp: convert lossless WebP lossily (-d 1) (default FALSE)')
        exit()

    arguments = {
        'delete': False,
        'lossyjpg': False,
        'lossywebp': False,
        'source': None
    }

    for arg in sys.argv[1:]:
        if arg.startswith('--'):
            if arg == '--delete':
                arguments['delete'] = True
            elif arg == '--lossyjpg':
                arguments['lossyjpg'] = True
            elif arg == '--lossywebp':
                arguments['lossywebp'] = True
            else:
                print('Unrecognized flag: ' + arg)
                exit()
        else:
            arguments['source'] = arg

    if arguments['source'] is None:
        print('Missing directory to process.')
        exit()

    pool = ThreadPool(cpu_count())
    for root, subdirs, files in os.walk(arguments['source']):
        for filename in files:
            pool.apply_async(try_handle_file, (filename, root))
    pool.close()
    pool.join()

    print('Before conversion: ' + str(fsbefore / 1024) + 'KB')
    print('After conversion: ' + str(fsafter / 1024) + 'KB')
    print('Reduction: ' + str((1 - fsafter / fsbefore) * 100) + '%')

    print('Exiting. Press ENTER to continue. Thank you.')
    input()

if __name__ == '__main__':
    run()
