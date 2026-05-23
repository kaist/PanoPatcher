from pathlib import Path

import cv2
import numpy as np
import tifffile
from PIL import Image


STRUCTURAL_TAGS = {
    254,  # NewSubfileType
    256,  # ImageWidth
    257,  # ImageLength
    258,  # BitsPerSample
    259,  # Compression
    262,  # PhotometricInterpretation
    273,  # StripOffsets
    277,  # SamplesPerPixel
    278,  # RowsPerStrip
    279,  # StripByteCounts
    284,  # PlanarConfiguration
    322,  # TileWidth
    323,  # TileLength
    324,  # TileOffsets
    325,  # TileByteCounts
    339,  # SampleFormat
    34665,  # ExifIFD
    34853,  # GPSIFD
    50781,  # RawDataUniqueID
    51111,  # NewRawImageDigest
}


def is_dng_path(path):
    return Path(path).suffix.lower() == '.dng'


def read_linear_dng(path):
    with tifffile.TiffFile(path) as tif:
        if not tif.is_dng:
            raise ValueError('Not a DNG file')
        page = tif.pages[0]
        if page.dtype != np.uint16 or len(page.shape) != 3 or page.shape[2] != 3:
            raise ValueError('Only 3-channel uint16 Linear DNG files are supported')
        if int(page.photometric) != 34892:
            raise ValueError('Only LinearRaw DNG files are supported')

        metadata = _collect_metadata(page)
        rgb = page.asarray()

    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr, metadata


def write_linear_dng(path, bgr_img, metadata):
    if bgr_img.dtype != np.uint16 or bgr_img.ndim != 3 or bgr_img.shape[2] != 3:
        raise ValueError('DNG output must be a 3-channel uint16 image')

    path = Path(path)
    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    height, width = rgb.shape[:2]
    extratags = _build_extratags(metadata, width, height)

    tifffile.imwrite(
        path,
        rgb,
        photometric=34892,
        planarconfig='contig',
        compression=None,
        metadata=None,
        software=metadata.get('software'),
        subfiletype=metadata.get('subfiletype'),
        extratags=extratags,
    )


def thumbnail(path, max_size=(80, 40)):
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        if page.dtype != np.uint16 or len(page.shape) != 3 or page.shape[2] != 3:
            raise ValueError('Only 3-channel uint16 Linear DNG files are supported')
        arr = page.asarray(out='memmap' if page.is_memmappable else None)
        step_y = max(1, arr.shape[0] // max_size[1])
        step_x = max(1, arr.shape[1] // max_size[0])
        sample = np.asarray(arr[::step_y, ::step_x, :])

    preview = linear_uint16_to_uint8(sample)
    img = Image.fromarray(preview, 'RGB')
    img.thumbnail(max_size)
    return img


def image_size(path):
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        return page.shape[1], page.shape[0]


def linear_bgr_to_pil(bgr_img, metadata=None):
    rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    if rgb.dtype == np.uint16:
        rgb = linear_uint16_to_uint8(rgb, metadata)
    return Image.fromarray(rgb)


def linear_rgb_to_uint8(rgb, metadata=None):
    rgb = rgb.astype(np.float32)
    black = 0.0
    white = 65535.0
    if metadata:
        black_level = metadata.get('black_level')
        white_level = metadata.get('white_level')
        if black_level:
            black = float(np.min(black_level))
        if white_level:
            white = float(np.max(white_level))

    rgb = np.clip((rgb - black) / max(1.0, white - black), 0.0, 1.0)
    rgb = np.power(rgb, 1.0 / 2.2)
    return (rgb * 255.0 + 0.5).astype(np.uint8)


def linear_uint16_to_uint8(rgb, metadata=None):
    lut = None
    if metadata is not None:
        lut = metadata.get('preview_lut')
        if lut is None:
            lut = _build_preview_lut(metadata)
            metadata['preview_lut'] = lut
    if lut is None:
        lut = _build_preview_lut(metadata)
    return lut[rgb]


def _build_preview_lut(metadata=None):
    black = 0.0
    white = 65535.0
    if metadata:
        black_level = metadata.get('black_level')
        white_level = metadata.get('white_level')
        if black_level:
            black = float(np.min(black_level))
        if white_level:
            white = float(np.max(white_level))

    values = np.arange(65536, dtype=np.float32)
    values = np.clip((values - black) / max(1.0, white - black), 0.0, 1.0)
    values = np.power(values, 1.0 / 2.2)
    return (values * 255.0 + 0.5).astype(np.uint8)


def _collect_metadata(page):
    extratags = []
    for tag in page.tags.values():
        if tag.code in STRUCTURAL_TAGS:
            continue
        if tag.name in {'ImageDescription', 'Software'}:
            continue
        extratags.append((tag.code, tag.dtype.value, tag.count, tag.value, False))

    software_tag = page.tags.get('Software')
    white_level_tag = page.tags.get('WhiteLevel')
    black_level_tag = page.tags.get('BlackLevel')
    subfiletype_tag = page.tags.get('NewSubfileType')

    return {
        'extratags': extratags,
        'software': software_tag.value if software_tag else None,
        'white_level': white_level_tag.value if white_level_tag else None,
        'black_level': black_level_tag.value if black_level_tag else None,
        'subfiletype': int(subfiletype_tag.value) if subfiletype_tag else None,
    }


def _build_extratags(metadata, width, height):
    extratags = []
    for code, dtype, count, value, writeonce in metadata.get('extratags', []):
        if code == 50720:  # DefaultCropSize
            value = (width, 1, height, 1)
        elif code == 50829:  # ActiveArea
            value = (0, 0, height, width)
        extratags.append((code, dtype, count, value, writeonce))
    return extratags
