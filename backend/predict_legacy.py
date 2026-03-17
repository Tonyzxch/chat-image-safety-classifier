import torch
from torchvision import transforms, models
from PIL import Image, ImageFile
# solve: DecompressionBombWarning
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
    print(
        "result: \ndanger level --> {} \ntype --> {}".format(danger_res[danger_pre.item()], type_res[type_pre.item()]))
    return result_danger,result_type


if __name__ == "__main__":
    model_pth_temp = "./epoch_175.pth"
    image_pth_temp = input("输入图片路径:\n")
    predict(image_pth_temp)