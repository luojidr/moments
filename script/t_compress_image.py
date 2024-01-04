import cv2

imgs = cv2.imread(r'D:/data/media/tmp/7410E604-F8FC-4479-94A7-1D46A8118244220914141948.png')

# 图片缩放至原图的1/4
# resize_img = cv2.resize(imgs, (0, 0), fx=0.25, fy=0.25, interpolation=cv2.INTER_NEAREST)

# 重写图片并保存
# cv2.imwrite('king-ouv.jpg', resize_img)


# 压缩图片
cv2.imwrite(r'D:/data/media/tmp//compress1.jpg', imgs, [cv2.IMWRITE_JPEG_QUALITY, 60])
