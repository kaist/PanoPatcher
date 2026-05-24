from pathlib import Path

import cv2
import numpy as np
import tifffile
from PIL import Image

try:
    import rawpy
except Exception:
    rawpy = None


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
        metadata['source_path'] = str(path)
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
    img = rawpy_preview(path)
    if img is not None:
        img.thumbnail(max_size)
        return img

    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        if page.dtype != np.uint16 or len(page.shape) != 3 or page.shape[2] != 3:
            raise ValueError('Only 3-channel uint16 Linear DNG files are supported')
        metadata = _collect_metadata(page)
        arr = page.asarray(out='memmap' if page.is_memmappable else None)
        step_y = max(1, arr.shape[0] // max_size[1])
        step_x = max(1, arr.shape[1] // max_size[0])
        sample = np.asarray(arr[::step_y, ::step_x, :])

    preview = linear_uint16_to_uint8(sample, metadata)
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


def rawpy_preview_bgr(path):
    img = rawpy_preview(path)
    if img is None:
        return None
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)


def rawpy_preview(path):
    if rawpy is None or not path:
        return None
    try:
        with rawpy.imread(str(path)) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                output_color=rawpy.ColorSpace.sRGB,
                output_bps=8,
                no_auto_bright=False,
                user_flip=0,
            )
        return Image.fromarray(rgb, 'RGB')
    except Exception:
        return None


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
    if metadata:
        baseline = metadata.get('baseline_exposure')
        if baseline is not None:
            rgb = rgb * (2.0 ** _as_scalar_float(baseline))
    rgb = _camera_rgb_to_srgb(rgb, metadata)
    rgb = np.power(rgb, 1.0 / 2.2)
    return (rgb * 255.0 + 0.5).astype(np.uint8)


def linear_uint16_to_uint8(rgb, metadata=None):
    if metadata and (metadata.get('as_shot_neutral') is not None or metadata.get('color_matrix') is not None):
        return linear_rgb_to_uint8(rgb, metadata)

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


def _camera_rgb_to_srgb(rgb, metadata=None):
    if not metadata:
        return rgb

    analog = metadata.get('analog_balance')
    if analog is not None:
        analog = _as_float_array(analog).reshape(-1)
        if analog.size >= 3 and np.all(analog[:3] > 0):
            rgb = rgb * analog[:3].reshape(1, 1, 3)

    neutral = metadata.get('as_shot_neutral')
    if neutral is not None:
        neutral = _as_float_array(neutral).reshape(-1)
        if neutral.size >= 3 and np.all(neutral[:3] > 0):
            wb = 1.0 / neutral[:3]
            wb /= max(float(wb[1]), 1e-6)
            rgb = rgb * wb.reshape(1, 1, 3)

    camera_to_xyz = _camera_to_xyz_matrix(metadata)
    if camera_to_xyz is None:
        return np.clip(rgb, 0.0, 1.0)

    camera_to_xyz = _normalize_xyz_matrix(camera_to_xyz, rgb)
    xyz = np.tensordot(rgb, camera_to_xyz.T, axes=1)
    xyz = np.tensordot(xyz, D50_TO_D65.T, axes=1)
    srgb = np.tensordot(xyz, XYZ_D65_TO_SRGB.T, axes=1)
    return np.clip(srgb, 0.0, 1.0)


XYZ_D65_TO_SRGB = np.array(
    [
        [3.2404542, -1.5371385, -0.4985314],
        [-0.9692660, 1.8760108, 0.0415560],
        [0.0556434, -0.2040259, 1.0572252],
    ],
    dtype=np.float32,
)

D50_TO_D65 = np.array(
    [
        [0.9555766, -0.0230393, 0.0631636],
        [-0.0282895, 1.0099416, 0.0210077],
        [0.0122982, -0.0204830, 1.3299098],
    ],
    dtype=np.float32,
)


def _camera_to_xyz_matrix(metadata):
    color_matrix = metadata.get('color_matrix')
    if color_matrix is not None:
        matrix = _as_float_array(color_matrix)
        if matrix.size == 9:
            matrix = matrix.reshape(3, 3)

            calibration = metadata.get('camera_calibration')
            if calibration is not None:
                calibration = _as_float_array(calibration)
                if calibration.size == 9:
                    matrix = matrix @ calibration.reshape(3, 3)

            # DNG ColorMatrix maps CIE XYZ D50 to camera RGB. Invert it for preview display.
            try:
                return np.linalg.inv(matrix)
            except np.linalg.LinAlgError:
                pass

    forward_matrix = metadata.get('forward_matrix')
    if forward_matrix is not None:
        matrix = _as_float_array(forward_matrix)
        if matrix.size == 9:
            return matrix.reshape(3, 3)

    return None


def _normalize_xyz_matrix(matrix, rgb):
    neutral = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    xyz_neutral = matrix @ neutral
    if xyz_neutral.size == 3 and xyz_neutral[1] > 1e-6:
        matrix = matrix / xyz_neutral[1]
    return matrix.astype(np.float32)


def _as_float_array(value):
    if isinstance(value, (list, tuple)) and len(value) == 1:
        return _as_float_array(value[0])
    if isinstance(value, tuple) and len(value) == 2 and _is_number_like(value[0]) and _is_number_like(value[1]):
        den = float(value[1])
        return np.array(float(value[0]) / den if den else 0.0, dtype=np.float32)
    arr = np.asarray(value)
    if arr.ndim >= 1 and arr.shape[-1] == 2 and np.issubdtype(arr.dtype, np.number):
        den = arr[..., 1].astype(np.float32)
        return np.divide(
            arr[..., 0].astype(np.float32),
            den,
            out=np.zeros(arr.shape[:-1], dtype=np.float32),
            where=den != 0,
        )
    if arr.dtype == object:
        return np.array([_to_float(x) for x in arr.reshape(-1)], dtype=np.float32).reshape(arr.shape)
    return arr.astype(np.float32)


def _as_scalar_float(value, default=0.0):
    try:
        arr = _as_float_array(value).reshape(-1)
        if arr.size:
            return float(arr[0])
    except Exception:
        pass
    return float(default)


def _to_float(value):
    if isinstance(value, tuple) and len(value) == 2 and _is_number_like(value[0]) and _is_number_like(value[1]):
        den = float(value[1])
        return float(value[0]) / den if den else 0.0
    return float(value)


def _is_number_like(value):
    try:
        float(value)
        return True
    except Exception:
        return False


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
    neutral_tag = page.tags.get('AsShotNeutral')
    color_matrix_tag = page.tags.get('ColorMatrix2') or page.tags.get('ColorMatrix1')
    forward_matrix_tag = page.tags.get('ForwardMatrix2') or page.tags.get('ForwardMatrix1')
    calibration_tag = page.tags.get('CameraCalibration2') or page.tags.get('CameraCalibration1')
    analog_balance_tag = page.tags.get('AnalogBalance')
    baseline_exposure_tag = page.tags.get('BaselineExposure')

    return {
        'extratags': extratags,
        'software': software_tag.value if software_tag else None,
        'white_level': white_level_tag.value if white_level_tag else None,
        'black_level': black_level_tag.value if black_level_tag else None,
        'subfiletype': int(subfiletype_tag.value) if subfiletype_tag else None,
        'as_shot_neutral': neutral_tag.value if neutral_tag else None,
        'color_matrix': color_matrix_tag.value if color_matrix_tag else None,
        'forward_matrix': forward_matrix_tag.value if forward_matrix_tag else None,
        'camera_calibration': calibration_tag.value if calibration_tag else None,
        'analog_balance': analog_balance_tag.value if analog_balance_tag else None,
        'baseline_exposure': baseline_exposure_tag.value if baseline_exposure_tag else None,
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
