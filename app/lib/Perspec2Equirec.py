import cv2
import numpy as np


class Perspective:
    def __init__(self, img_name, FOV, THETA, PHI):
        with open(img_name, 'rb') as f:
            img_bytes = np.frombuffer(f.read(), dtype=np.uint8)

        self._img = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        del img_bytes
        [self._height, self._width, _] = self._img.shape
        self.wFOV = FOV
        self.THETA = THETA
        self.PHI = PHI
        self.hFOV = float(self._height) / self._width * FOV

        self.w_len = np.tan(np.radians(self.wFOV / 2.0))
        self.h_len = np.tan(np.radians(self.hFOV / 2.0))

    def GetEquirec(self, height, width, chunk_rows=512):
        merge, mask, _, _ = self.GetEquirecRoi(height, width, chunk_rows=chunk_rows, roi=None)
        return merge, mask

    def GetEquirecRoi(self, height, width, chunk_rows=512, roi=None):
        x0, y0, x1, y1 = self._normalize_roi(height, width, roi)
        roi_w = max(0, x1 - x0)
        roi_h = max(0, y1 - y0)
        if roi_w == 0 or roi_h == 0:
            return np.zeros((0, 0, 3), dtype=self._img.dtype), np.zeros((0, 0), dtype=np.uint8), x0, y0

        persp = np.zeros((roi_h, roi_w, 3), dtype=self._img.dtype)
        mask = np.zeros((roi_h, roi_w), dtype=np.uint8)

        for chunk, chunk_mask, _, chunk_y0 in self.IterEquirecRoi(height, width, chunk_rows=chunk_rows, roi=(x0, y0, x1, y1)):
            out_y0 = chunk_y0 - y0
            out_y1 = out_y0 + chunk.shape[0]
            persp[out_y0:out_y1] = chunk
            mask[out_y0:out_y1] = chunk_mask

        return persp, mask, x0, y0

    def GetMaskRoi(self, height, width, chunk_rows=512, roi=None):
        x0, y0, x1, y1 = self._normalize_roi(height, width, roi)
        roi_w = max(0, x1 - x0)
        roi_h = max(0, y1 - y0)
        if roi_w == 0 or roi_h == 0:
            return np.zeros((0, 0), dtype=np.uint8), x0, y0

        mask = np.zeros((roi_h, roi_w), dtype=np.uint8)
        for _, chunk_mask, _, chunk_y0 in self.IterEquirecRoi(height, width, chunk_rows=chunk_rows, roi=(x0, y0, x1, y1)):
            out_y0 = chunk_y0 - y0
            out_y1 = out_y0 + chunk_mask.shape[0]
            mask[out_y0:out_y1] = chunk_mask
        return mask, x0, y0

    def IterEquirecRoi(self, height, width, chunk_rows=512, roi=None):
        x0, y0, x1, y1 = self._normalize_roi(height, width, roi)
        roi_w = max(0, x1 - x0)
        roi_h = max(0, y1 - y0)
        if roi_w == 0 or roi_h == 0:
            return

        mapper = self._make_mapper(height, width, x0, x1)
        for chunk_y0 in range(y0, y1, chunk_rows):
            chunk_y1 = min(chunk_y0 + chunk_rows, y1)
            chunk, mask = self._remap_chunk(chunk_y0, chunk_y1, roi_w, mapper)
            yield chunk, mask, x0, chunk_y0

    def _normalize_roi(self, height, width, roi):
        if roi is None:
            x0, y0, x1, y1 = 0, 0, width, height
        else:
            x0, y0, x1, y1 = roi
            x0 = max(0, int(x0))
            y0 = max(0, int(y0))
            x1 = min(width, int(x1))
            y1 = min(height, int(y1))
        return x0, y0, x1, y1

    def _make_mapper(self, height, width, x0, x1):
        y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        [R1, _] = cv2.Rodrigues(z_axis * np.radians(self.THETA))
        [R2, _] = cv2.Rodrigues(np.dot(R1, y_axis) * np.radians(-self.PHI))

        R1 = R1.T.astype(np.float32)
        R2 = R2.T.astype(np.float32)
        R = np.dot(R1, R2)

        x_idx = np.arange(x0, x1, dtype=np.float32)
        x_den = max(1, width - 1)
        x_rad = np.radians(-180.0 + x_idx * (360.0 / x_den))
        cos_x = np.cos(x_rad)
        sin_x = np.sin(x_rad)
        y_den = max(1, height - 1)
        return R, cos_x, sin_x, y_den

    def _remap_chunk(self, chunk_y0, chunk_y1, roi_w, mapper):
        R, cos_x, sin_x, y_den = mapper
        eps = np.finfo(np.float32).eps

        y_idx = np.arange(chunk_y0, chunk_y1, dtype=np.float32)
        y_rad = np.radians(90.0 - y_idx * (180.0 / y_den))
        cos_y = np.cos(y_rad)[:, np.newaxis]
        sin_y = np.sin(y_rad)[:, np.newaxis]

        x_map = cos_y * cos_x[np.newaxis, :]
        y_map = cos_y * sin_x[np.newaxis, :]
        z_map = np.broadcast_to(sin_y, x_map.shape)

        tx = R[0, 0] * x_map + R[0, 1] * y_map + R[0, 2] * z_map
        ty = R[1, 0] * x_map + R[1, 1] * y_map + R[1, 2] * z_map
        tz = R[2, 0] * x_map + R[2, 1] * y_map + R[2, 2] * z_map

        safe_tx = np.where(np.abs(tx) > eps, tx, eps)
        ty = ty / safe_tx
        tz = tz / safe_tx

        valid = (
            (tx > 0) &
            (-self.w_len < ty) & (ty < self.w_len) &
            (-self.h_len < tz) & (tz < self.h_len)
        )

        lon_map = np.zeros((chunk_y1 - chunk_y0, roi_w), dtype=np.float32)
        lat_map = np.zeros((chunk_y1 - chunk_y0, roi_w), dtype=np.float32)
        lon_map[valid] = ((ty[valid] + self.w_len) / (2 * self.w_len) * self._width)
        lat_map[valid] = ((-tz[valid] + self.h_len) / (2 * self.h_len) * self._height)

        chunk = cv2.remap(self._img, lon_map, lat_map, cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
        chunk[~valid] = 0
        return chunk, valid.astype(np.uint8)

    def EstimateRoi(self, height, width, pad=64):
        y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        [R1, _] = cv2.Rodrigues(z_axis * np.radians(self.THETA))
        [R2, _] = cv2.Rodrigues(np.dot(R1, y_axis) * np.radians(-self.PHI))
        R = np.dot(R2.astype(np.float32), R1.astype(np.float32))

        corners = np.array([
            [1.0, -self.w_len, -self.h_len],
            [1.0, self.w_len, -self.h_len],
            [1.0, self.w_len, self.h_len],
            [1.0, -self.w_len, self.h_len],
        ], dtype=np.float32)
        corners /= np.sqrt(np.sum(corners * corners, axis=1))[:, np.newaxis]
        xyz = np.dot(R, corners.T).T

        lat = np.arcsin(np.clip(xyz[:, 2], -1.0, 1.0))
        lon = np.arctan2(xyz[:, 1], xyz[:, 0])
        xs = (lon / np.pi * 180.0 + 180.0) / 360.0 * (width - 1)
        ys = (-lat / np.pi * 180.0 + 90.0) / 180.0 * (height - 1)

        if xs.max() - xs.min() > width * 0.5:
            return 0, 0, width, height

        x0 = int(np.floor(xs.min())) - pad
        x1 = int(np.ceil(xs.max())) + pad
        y0 = int(np.floor(ys.min())) - pad
        y1 = int(np.ceil(ys.max())) + pad
        return x0, y0, x1, y1
