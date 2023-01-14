import hashlib
import io
import datetime
import pathlib
import multiprocessing

import click
import PIL.Image

ERROR_DATE = datetime.datetime(1900, 1, 1)


def _calc_checksum(image_path: pathlib.Path, block_size: int = 8192) -> str:
    """
    Create a sha1 checksum of just the image data (no meta/exif).

    :param image_path: a path to an image to process
    :param block_size: the block size to use when chunking up the image data
    :return: a calculated hex digest
    """
    hasher = hashlib.sha1()
    img_io = io.BytesIO()

    # open the image file and save the image data portion as a io.BytesIO object
    with PIL.Image.open(image_path) as im:
        im.save(img_io, im.format)

    # reset the cursor
    img_io.seek(0)

    # chunk_size at a time, update our hash until complete
    while chunk := img_io.read(block_size):
        hasher.update(chunk)

    return hasher.hexdigest()


def _extract_date(image_path: pathlib.Path) -> datetime.datetime:
    """
    Extract the file creation date from EXIF information.

    :param image_path: the path to a specific image file
    :return: a datetime object representing the creation date of the image
    """
    with PIL.Image.open(image_path, 'r') as im:
        try:
            # attempt to extract the creation date from EXIF tag 306
            exif = im.getexif()
            cdate = datetime.datetime.strptime(exif[306], '%Y:%m:%d %H:%M:%S')

        # the requested tag doesn't exist, use the ERROR_DATE global to signify such
        except KeyError:
            cdate = ERROR_DATE

        return cdate


def process_file(file_path: pathlib.Path):
    hash_str = _calc_checksum(file_path)
    cdate = _extract_date(file_path)

    return f"{file_path.name} -- {cdate} -- {hash_str}"


@click.command()
@click.argument('src')
@click.option('--dest', default='.', help='desired destination')
@click.option('--recurse/--no-recurse', default=False)
def cli(src: str, dest: str, recurse: bool):
    file_path = pathlib.Path(src)
    if file_path.exists():
        if file_path.is_dir():
            file_list = [ ]
            if recurse:
                for img in file_path.rglob('*.jpg'):
                    file_list.append(img)
            else:
                for img in file_path.glob('*.jpg'):
                    file_list.append(img)
            click.echo(f"COUNT: {len(file_list)}")

            pool = multiprocessing.Pool()
            for file in file_list:
                pool.apply_async(process_file, args=(file, ), callback=(lambda r: print(r, flush=True)))
            pool.close()
            pool.join()

        elif file_path.is_file():
            print(process_file(file_path))
        else:
            raise click.exceptions.BadParameter(src)
    else:
        raise click.exceptions.BadParameter(src)
