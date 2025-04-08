import os
import sys
import cv2
import numpy as np
import gc






class Perspective:
    def __init__(self, img_name , FOV, THETA, PHI ):
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

    



    def GetEquirec(self, height, width):
        # Используем float32 для экономии памяти
        x, y = np.meshgrid(np.linspace(-180, 180, width, dtype=np.float32),
                        np.linspace(90, -90, height, dtype=np.float32))
        
        x_rad = np.radians(x)
        y_rad = np.radians(y)
        
        x_map = np.cos(x_rad) * np.cos(y_rad)
        y_map = np.sin(x_rad) * np.cos(y_rad)
        z_map = np.sin(y_rad)

        xyz = np.stack((x_map, y_map, z_map), axis=2)

        y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        z_axis = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        [R1, _] = cv2.Rodrigues(z_axis * np.radians(self.THETA))
        [R2, _] = cv2.Rodrigues(np.dot(R1, y_axis) * np.radians(-self.PHI))

        R1 = np.linalg.inv(R1)
        R2 = np.linalg.inv(R2)

        xyz = xyz.reshape([height * width, 3]).T
        xyz = np.dot(R2, xyz)
        xyz = np.dot(R1, xyz).T

        xyz = xyz.reshape([height, width, 3])
        inverse_mask = np.where(xyz[:, :, 0] > 0, 1, 0)

        # Оптимизация: выполняем деление на месте
        xyz[:, :, :] /= xyz[:, :, 0][:, :, np.newaxis]

        lon_map = np.where((-self.w_len < xyz[:, :, 1]) & (xyz[:, :, 1] < self.w_len) &
                        (-self.h_len < xyz[:, :, 2]) & (xyz[:, :, 2] < self.h_len),
                        (xyz[:, :, 1] + self.w_len) / (2 * self.w_len) * self._width, 0)
        lat_map = np.where((-self.w_len < xyz[:, :, 1]) & (xyz[:, :, 1] < self.w_len) &
                        (-self.h_len < xyz[:, :, 2]) & (xyz[:, :, 2] < self.h_len),
                        (-xyz[:, :, 2] + self.h_len) / (2 * self.h_len) * self._height, 0)
        mask = np.where((-self.w_len < xyz[:, :, 1]) & (xyz[:, :, 1] < self.w_len) &
                        (-self.h_len < xyz[:, :, 2]) & (xyz[:, :, 2] < self.h_len), 1, 0)

        persp = cv2.remap(self._img, lon_map.astype(np.float32), lat_map.astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
        
        # Освобождаем память, удаляя ненужные массивы
        del lon_map, lat_map,self._img
        gc.collect()

        mask = mask * inverse_mask
        del inverse_mask

        # Используем np.broadcast_to для избежания создания нового массива
        mask = np.broadcast_to(mask[:, :, np.newaxis], (height, width, 3))

        persp = persp * mask
        
        return persp, mask
        






