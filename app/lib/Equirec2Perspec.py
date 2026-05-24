import cv2
import numpy as np
from app.lib import dng_io

class Equirectangular:
    def __init__(self, img_name):
        self.is_dng = dng_io.is_dng_path(img_name)
        self.dng_metadata = None
        self._preview_img = None
        if self.is_dng:
            self._img, self.dng_metadata = dng_io.read_linear_dng(img_name)
            self._preview_img = dng_io.rawpy_preview_bgr(img_name)
        else:
            with open(img_name, 'rb') as f:
                img_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            self._img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
            del img_bytes
        [self._height, self._width, _] = self._img.shape
        self._grid_cache = {}

    def _get_base_grid(self, FOV, height, width):
        key = (float(FOV), int(height), int(width))
        use_cache = height * width <= 4_000_000
        if use_cache:
            xyz = self._grid_cache.get(key)
            if xyz is not None:
                return xyz

        wFOV = float(FOV)
        hFOV = float(height) / width * wFOV
        w_len = np.tan(np.radians(wFOV / 2.0)).astype(np.float32)
        h_len = np.tan(np.radians(hFOV / 2.0)).astype(np.float32)

        y_map, z_map = np.meshgrid(
            np.linspace(-w_len, w_len, width, dtype=np.float32),
            -np.linspace(-h_len, h_len, height, dtype=np.float32),
        )
        x_map = np.ones_like(y_map, dtype=np.float32)
        d = np.sqrt(x_map * x_map + y_map * y_map + z_map * z_map)
        xyz = np.stack((x_map / d, y_map / d, z_map / d), axis=2)
        xyz = xyz.reshape(height * width, 3).T

        if use_cache:
            if len(self._grid_cache) >= 8:
                self._grid_cache.pop(next(iter(self._grid_cache)))
            self._grid_cache[key] = xyz
        return xyz
    

    def _get_perspective(self, img, FOV, THETA, PHI, height, width, interpolation=cv2.INTER_CUBIC):
        #
        # THETA is left/right angle, PHI is up/down angle, both in degree
        #

        equ_h, equ_w = img.shape[:2]
        equ_cx = (equ_w - 1) / 2.0
        equ_cy = (equ_h - 1) / 2.0

        y_axis = np.array([0.0, 1.0, 0.0], np.float32)
        z_axis = np.array([0.0, 0.0, 1.0], np.float32)
        [R1, _] = cv2.Rodrigues(z_axis * np.radians(THETA))
        [R2, _] = cv2.Rodrigues(np.dot(R1, y_axis) * np.radians(-PHI))
        R1 = R1.astype(np.float32)
        R2 = R2.astype(np.float32)

        xyz = self._get_base_grid(FOV, height, width)
        xyz = np.dot(R1, xyz)
        xyz = np.dot(R2, xyz).T
        lat = np.arcsin(np.clip(xyz[:, 2], -1.0, 1.0))
        lon = np.arctan2(xyz[:, 1] , xyz[:, 0])

        lon = lon.reshape([height, width]) / np.pi * 180
        lat = -lat.reshape([height, width]) / np.pi * 180

        lon = lon / 180 * equ_cx + equ_cx
        lat = lat / 90  * equ_cy + equ_cy

        
            
        persp = cv2.remap(img, lon.astype(np.float32), lat.astype(np.float32), interpolation, borderMode=cv2.BORDER_WRAP)
        return persp

    def GetPerspective(self, FOV, THETA, PHI, height, width, interpolation=cv2.INTER_CUBIC):
        return self._get_perspective(self._img, FOV, THETA, PHI, height, width, interpolation)

    def GetPreviewPerspective(self, FOV, THETA, PHI, height, width, interpolation=cv2.INTER_CUBIC):
        img = self._preview_img if self._preview_img is not None else self._img
        return self._get_perspective(img, FOV, THETA, PHI, height, width, interpolation)
        

