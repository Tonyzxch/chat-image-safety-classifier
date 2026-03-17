from operator import is_
import requests
import threading
import json
import time
from datetime import datetime
BASE_URL = "http://127.0.0.1:5700/"
BASE_IMG_URL = "http://127.0.0.1:3000/"

class MyThread(threading.Thread):
    def __init__(self,func,args=()):
        super(MyThread,self).__init__()
        self.func = func
        self.args = args
  
    def run(self):
        self.result = self.func(*self.args)
    
    def get_result(self):
        try:
            return self.result  # 如果子线程不使用join方法，此处可能会报没有self.result的错误
        except Exception:
            return None


def send_single_img(group,text,image,is_ero):
    """
    需要在另外开一个线程来进行发送处理，不然寄了就麻烦
    """
    #ero的不能放出来
    msg_ero = {
        "group_id": group,
        # "message": text + "[CQ:image,file=" + BASE_IMG_URL + "{}]".format(image)
        "message": text + "\n" + BASE_IMG_URL + image
    }
    msg_not_ero = {
        "group_id": group,
        "message": text + "[CQ:image,file=" + BASE_IMG_URL + "{}]".format(image)
    }
    msg = msg_not_ero
    if is_ero ==1:
        msg = msg_ero
    count = 2
    while count:
        res = requests.post(BASE_URL + "send_group_msg",msg).json()
        #print(res)
        if type(res) != dict or res["status"] != "ok":
            print("图片{}发送到群{}的过程中出错了,等待三秒后重新发送".format(image,group))
            time.sleep(3)
        else:
            break
        count -= 1
    if count == 0:
        print("图片{}无法发送到群{}!!!".format(image,group))
        #发送失败，多半是图炸了，需要发群里提醒
        #TODO： 增加私发功能
        with open("ERROR.txt",'a') as f:
            time_str = datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')
            f.write("图片{}无法发送到群{}!!! ------ {}\n".format(image,group,time_str))
        send_text_group(group,text +"\n图发不了,自己找吧\n" + "图片名:" +image)

def send_text_group(group,text):
    msg = {
        "group_id":group,
        "message": text
    }
    res = requests.post(BASE_URL + "send_group_msg", msg).json()
    if res.get("status") != "ok":
        with open("ERROR.txt",'a') as f:
            time_str = datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')
            f.write("发送群聊消息失败!! group_id: {}, image:{} ------ {}\n".format(group,text,time_str))
        print("发送群聊消息失败!! group_id: {}, image:{}".format(group,text))


def send_private_img(user_id,image):
    msg = {
        "user_id" : user_id,
        "message" : "[CQ:image,file=" + BASE_IMG_URL + "{}]".format(image)
    }
    res = requests.post(BASE_URL + "send_private_msg", msg).json()
    if res.get("status") != "ok":
        with open("ERROR.txt",'a') as f:
            time_str = datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')
            f.write("发送私聊消息失败!! user_id：{}, image:{} ------ {}\n".format(user_id,image,time_str))
        print("发送私聊消息失败!! user_id：{}, image:{}".format(user_id,image))


def send_performance(data):
    """
    发送所有人的表现，
    """
    pass
if __name__ == "__main__":
    groups = ["example_group_id"]
    text = "分级：2  图片id:{}  判定人：{}".format("1","cab")
    image = "1614323562.jpg"
    t=threading.Thread(target=send_single_img,args=(groups,text,image))
    t.start()
