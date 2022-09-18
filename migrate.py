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

import os
import subprocess
import time
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from subprocess import check_output

fsbefore = 0
fsafter = 0

def is_webp_lossless(p):
    res = check_output(args=[
        'webpinfo',
        p
    ], text=True)

    return 'Format: Lossless' in res

def convert(p, lossy=False):
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
        os.remove(p)
        return res

def decode(p):
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
            ret = convert(fullpath)
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['png']:
            print('        Converting PNG to JXL')
            ret = convert(fullpath)
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['apng']:
            print('        Converting APNG to JXL')
            ret = convert(fullpath)
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['gif']:
            print('        Converting GIF to JXL')
            ret = convert(fullpath)
            if ret is not None:
                filesize = os.path.getsize(ret)
                fsafter += filesize
            else:
                print('        Conversion FAILED: ', fullpath)
        elif extension in ['webp']:
            print('        Converting WebP to PNG')
            webp_is_lossless = is_webp_lossless(fullpath)
            ret = decode(fullpath)
            if ret is not None:
                if webp_is_lossless:
                    print('        Converting PNG to JXL (lossless)')
                    ret = convert(ret)
                    if ret is not None:
                        filesize = os.path.getsize(ret)
                        fsafter += filesize
                    else:
                        print('        Conversion FAILED: ', fullpath)
                else:
                    print('        Converting PNG to JXL (lossy)')
                    ret = convert(ret, lossy=True)
                    if ret is not None:
                        filesize = os.path.getsize(ret)
                        fsafter += filesize
                    else:
                        print('        Conversion FAILED: ', fullpath)
            else:
                print('        Conversion FAILED: ', fullpath)
    else:
        print('    Not supported: ' + filename)
def try_handle_file(filename, root):
    try:
        handle_file(filename, root)
    except Exception as inst:
        print('Error processing ' + os.path.join(root, filename) + ': ', inst)

def run():
    walk_dir = input('Root: ')
    pool = ThreadPool(cpu_count())
    for root, subdirs, files in os.walk(walk_dir):
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
