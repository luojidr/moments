import os.path
import random
import string
from datetime import datetime

import fitz


def pdf2image(pdf_path, img_dir, zoom_x=2.0, zoom_y=2.0, rotation_angle=0):
    """ 将PDF转化为图片
        https://thepythoncode.com/article/convert-pdf-files-to-images-in-python

    :param pdf_path:        pdf文件的路径
    :param img_dir:         图像要保存的目录
    :param zoom_x:          x方向的缩放系数
    :param zoom_y:          y方向的缩放系数
    :param rotation_angle:  旋转角度
    :return: a list of image path
    """
    img_list = []
    pdf = fitz.open(pdf_path)

    # 逐页读取PDF
    for pg in range(0, pdf.page_count):
        page = pdf[pg]
        trans = fitz.Matrix(zoom_x, zoom_y).prerotate(rotation_angle)  # 设置缩放和旋转系数
        pm = page.get_pixmap(matrix=trans, alpha=False)

        random_val = ''.join(random.choices(string.digits + string.ascii_letters, k=6))
        img_name = datetime.now().strftime('%Y%m%d%H%M%S_%f') + f'_{random_val}.png'
        img_path = os.path.join(img_dir, img_name)

        pm.save(img_path)  # 开始写图像
        img_list.append(img_path)

    pdf.close()
    return img_list

