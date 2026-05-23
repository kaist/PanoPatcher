import cv2
import numpy as np
import app.lib.Perspec2Equirec as P2E


class Perspective:
    def __init__(self, img_array, F_T_P_array):
        assert len(img_array) == len(F_T_P_array)

        self.img_array = img_array
        self.F_T_P_array = F_T_P_array

    def GetEquirec(self, in_img, height, width, inplace=False):
        result = in_img if inplace else in_img.copy()

        for img_dir, [F, T, P] in zip(self.img_array, self.F_T_P_array):
            per = P2E.Perspective(img_dir, F, T, P)
            pad = 64
            roi = per.EstimateRoi(height, width, pad=pad)
            merge_mask, x0, y0 = per.GetMaskRoi(height, width, roi=roi)
            if merge_mask.size == 0:
                continue

            alpha_full = self._feather_mask(merge_mask)
            if not np.any(alpha_full > 0):
                continue

            for merge_image, _, chunk_x0, chunk_y0 in per.IterEquirecRoi(height, width, roi=roi):
                local_y0 = chunk_y0 - y0
                local_y1 = local_y0 + merge_image.shape[0]
                alpha = alpha_full[local_y0:local_y1, :, np.newaxis]
                blend_area = alpha[:, :, 0] > 0
                if not np.any(blend_area):
                    continue

                y1 = chunk_y0 + merge_image.shape[0]
                x1 = chunk_x0 + merge_image.shape[1]
                target = result[chunk_y0:y1, chunk_x0:x1]
                target_f = target.astype(np.float32)
                patch_f = merge_image.astype(np.float32)
                blended = patch_f * alpha + target_f * (1.0 - alpha)
                target_f[blend_area] = blended[blend_area]

                if np.issubdtype(result.dtype, np.integer):
                    info = np.iinfo(result.dtype)
                    target[:] = np.clip(target_f, info.min, info.max).astype(result.dtype)
                else:
                    target[:] = target_f.astype(result.dtype)

        return result

    def _feather_mask(self, mask, edge_px=3, feather_px=16):
        mask = (mask > 0).astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        for _ in range(edge_px):
            mask = cv2.erode(mask, kernel)

        dist = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
        alpha = np.clip(dist / float(feather_px), 0.0, 1.0)
        return alpha.astype(np.float32)
