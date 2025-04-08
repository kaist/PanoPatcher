import os
import sys
import cv2
import numpy as np
import app.lib.Perspec2Equirec as P2E
from scipy.ndimage import gaussian_filter
import gc

class Perspective:
    def __init__(self, img_array , F_T_P_array ):
        
        assert len(img_array)==len(F_T_P_array)
        
        self.img_array = img_array
        self.F_T_P_array = F_T_P_array
    

    def GetEquirec(self,in_img,height,width):
        for img_dir,[F,T,P] in zip (self.img_array,self.F_T_P_array):
            per = P2E.Perspective(img_dir,F,T,P)        # Load equirectangular image
            merge_image , merge_mask = per.GetEquirec(height,width)   # Specify parameters(FOV, theta, phi, height, width)
            del per
         
        del self.img_array
        gc.collect()
        merge_mask=gaussian_filter(merge_mask,sigma=1)
        gc.collect()
        merge_mask2=merge_mask==0
        del merge_mask
        gc.collect()

        merge_image[merge_mask2]=in_img[merge_mask2]
        del merge_mask2
        gc.collect()
        return merge_image
        






