from flask import Flask, request, redirect
from flask import jsonify
from flask_cors import CORS
import time
import os


import torch
from torchvision import transforms, models
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = None


# define result
danger_res = ["非常安全", "比较安全", "不太安全", "很不安全"]
type_res = ["虚拟", "现实", "文本"]

# get predict configs
input_size = (224, 224)
out_features = 7

transform = transforms.Compose([transforms.Resize(input_size),
                                transforms.ToTensor(),
                                transforms.Normalize([0.485, 0.456, 0.406],
                                                        [0.229, 0.224, 0.225])
                                ])

# get available device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# get model
model = models.resnet101()
in_features = model.fc.in_features
model.fc = torch.nn.Linear(in_features, out_features)
model.load_state_dict(torch.load("./epoch_175.pth", map_location=device))
model.to(device)
model.eval()


def predict(image_pth):
    """
    Predict danger levels and categories for images
    :param image_pth: image file path
    :param model_pth: model file path
    """

    # get image
    img = Image.open(image_pth).convert("RGB")
    img = transform(img)
    img = img.unsqueeze(0)
    img = img.to(device)


    with torch.no_grad():
        # get forward propagation output
        output = model(img)
        _, danger_pre = torch.max(output[:, :4], 1)
        _, type_pre = torch.max(output[:, -3:], 1)
    result_danger = danger_res[danger_pre.item()]
    result_type = type_res[type_pre.item()]
    # print(
    #     "result: \ndanger level --> {} \ntype --> {}".format(danger_res[danger_pre.item()], type_res[type_pre.item()]))
    return result_danger,result_type









para={}
with open("config.cfg",'r') as f:
    line = f.readline()
    tmp = line.split('=')
    para[tmp[0]] = tmp[1]
basedir = para["basedir"]
app = Flask(__name__)
cors = CORS(app, supports_credentials=True)


@app.route('/predict', methods=['POST','GET'])
def predict_img():
    
    img = request.files.get('file')
 
    #定义一个图片存放的位置 存放在static下面
    path = basedir+"/static/upload/"
    
    #图片名称 
    imgName = img.filename
    postfix = imgName.split('.')[-1]
    
 
    #图片path和名称组成图片的保存路径
    name = str(int(time.time()*1000)) + '.' + postfix
    file_path = path + name
 
    #保存图片
    img.save(file_path)
 
    #url是图片的路径
    url = '/static/upload/'+name
    danger,type = predict(file_path)
    res = {
        "url":url,
        "danger":danger,
        "type":type
    }
    return jsonify(res)
    
# 启动运行
if __name__ == '__main__':
    app.run(host="0.0.0.0")   # 这样子会直接运行在本地服务器，也即是 localhost:5000
   # app.run(host='your_ip_address') # 这里可通过 host 指定在公网IP上运行
   #需要接口: 1.给一个数字随机返回一定数量的图片信息 2.给一个列表，把列表里面的表进行修改 3.
