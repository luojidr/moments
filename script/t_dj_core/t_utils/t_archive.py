import time
import os.path
import os.path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from django.utils.archive import TarArchive, ZipArchive


def t_tar_archive(filename):
    archive = TarArchive(filename)
    archive.list()


def t_zip_archive(filename):
    archive = ZipArchive(filename)
    archive.list()
    # archive.extract(to_path="D:/data/zip_extract")
    print(archive.split_leading_dir(filename))


if __name__ == "__main__":
    t_zip_archive("D:/data/logs.zip")

    print('=========================================')
    # t_tar_archive("D:/data/logs.tar")
