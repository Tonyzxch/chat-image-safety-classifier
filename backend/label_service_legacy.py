from unicodedata import category
from flask import Flask, request, redirect
from flask import jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime
import threading
from bot import send_single_img
import os

def dbconnect():
    mydb = mysql.connector.connect(
        host="127.0.0.1",
        user="your_user",
        passwd="your_password",
        database="image_safety"
    )
    cursor = mydb.cursor()
    return mydb,cursor

# with open("./password.txt","r") as f:
#     PASSWORD = f.read()
PASSWORD = "change_me"
LEVEL = {
    "0":"非常安全",
    "1":"比较安全",
    "2":"不太安全",
    "3":"很不安全"
}
groups = [
    {
        "id":"example_group_id",
        "name":"review_group",
        "level":1
    }
    # {
    #     "id":"693077731",
    #     "level":2,
    #     "name":"野猪群"
    # }
]
app = Flask(__name__)
cors = CORS(app, supports_credentials=True)


@app.route('/',methods=['GET', 'POST'])
def hello_world():
    return 'Hello World!'

@app.route('/getpic', methods=['GET', 'POST'])
def getpic():
    mydb,cursor = dbconnect()
    if request.get_json():
        data=request.get_json()
        number = data['number']
    else:
        number=10
    sql="SELECT * FROM picdata where is_labled=0 ORDER BY RAND() LIMIT {};".format(number)
    cursor.execute(sql)
    myresult = cursor.fetchall()
    response = []
    for i in myresult:
        response.append(
            {
                "id":i[0],
                "original":i[1],
                "thumbnail":'static/img_small/'+i[1]
            }
        )
    mydb.close()
    return jsonify(response)
@app.route('/updatepic', methods=['GET', 'POST'])
def updatepic():
    if not request.get_json():
        return "你有病吧"
    else:
        mydb,cursor = dbconnect() 
        updatelist = request.get_json()#因为不确定能不能发过来是列表，就直接放字典了。
        #updatelist 预计是含有 "id",name","danger_level","is_virtual"字典的列表
        #通过cookie获取username
        username = request.cookies.get("username")
        if not username:
            #如果是None或者空，就变成空
            username = ""

        for i in updatelist:
            sql_search = "SELECT danger_level,is_virtual,is_real,is_text,is_other,is_labled,name from \
                picdata where id={}".format(i['id'])
            cursor.execute(sql_search)
            myresult = cursor.fetchone()
            before = ""
            name = myresult[-1]
            for j in range(len(myresult)):
                if j == len(myresult)-2:
                    break
                before += str(myresult[j])
            sql="UPDATE picdata SET danger_level={},is_virtual={},\
                is_real={},is_text={},is_other={},is_labled={} \
                where id={}".format(i['danger_level'],i["is_virtual"],i["is_real"],i["is_text"],i["is_other"],i["is_labled"],i['id'])
            cursor.execute(sql)

            #判断is_labled是不是1，是的话就redirect获取+1,不是的话就
            #redirect 也需要修改
            # if myresult[-1] == 0:
            #     redirect = 0
            time_str = datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')
            after = "" + str(i['danger_level']) + str(i["is_virtual"]) + \
                str(i["is_real"]) + str(i["is_text"]) + str(i["is_other"])
            sql_2 = "INSERT INTO updatelist (username,picid,date,data_before,data_after,redirect) values ('{}',{},'{}','{}','{}',0)".format(username,i['id'],time_str,before,after)
            cursor.execute(sql_2)
            #首次判断的时候才发送
            # if before[0] == "-" and after[0] != "-" and int(after[0])>=1:
            if before[0] == "-" and after[0] != "-":
                for group in groups:
                    #对每一个组都开一个线程来发图片,单独判断要不要发
                    group_id = group["id"]
                    level = int(after[0])
                    if level >= group["level"]:
                        is_ero = 0
                        if level == 3:
                            is_ero =1
                        image = name
                        cate = ""
                        if i["is_virtual"] == 1:
                            cate = "虚拟"
                        elif i["is_real"] == 1:
                            cate = "现实"
                        elif i["is_text"] == 1:
                            cate = "文本"
                        elif i["is_other"] == 1: 
                            cate = "其他"
                        text = "分类:{}  分级:{}  图片名:{}  id:{}  判定人:{}".format(cate,LEVEL[str(level)],image,i["id"],username)

                        t = threading.Thread(target=send_single_img,args=(group_id,text,image,is_ero))
                        t.start()
        mydb.commit()
        mydb.close()
        return "ok"

@app.route('/getunlabled', methods=['GET', 'POST'])
def getUnlabled():
    mydb,cursor = dbconnect()
    response={}
    sql = "SELECT COUNT(*) FROM picdata WHERE is_labled=0"
    cursor.execute(sql)
    unlabled=cursor.fetchall()[0][0]
    response["unlabled"] = unlabled
    mydb.close()
    return jsonify(response)
@app.route('/suggestion', methods=['POST'])
def suggestion():
    data=request.get_json()
    text=data['text']
    time=data['time']
    sql = "INSERT INTO suggtion (text,time) values('{}',-1,-1);".format(text,time)
    return "OK"

@app.route('/checkcookie', methods=['POST','GET'])
def check_cookie():
    return "OK"
@app.route('/checkusername', methods=['POST','GET'])
def check_username():
    mydb,cursor = dbconnect()
    data=request.get_json()
    username = data["username"]
    if not username:
        return "0"
    sql = "select count(*) from user where username = '{}'".format(username)
    cursor.execute(sql)
    result = cursor.fetchone()[0]
    return str(result)


@app.route('/findbyid', methods=['POST','GET'])
def find_by_id():
    mydb,cursor = dbconnect()
    data=request.get_json()
    id = data["id"]
    sql="SELECT * FROM picdata where id={};".format(id)
    cursor.execute(sql)
    myresult = cursor.fetchall()
    response = []
    for i in myresult:
        response.append(
            {
                "id":i[0],
                "original":i[1],
                "thumbnail":'static/img_small/'+i[1]
            }
        )
    mydb.close()
    return jsonify(response)


@app.route('/getpicbytime', methods=['POST','GET'])
def get_pic_by_time():
    mydb,cursor = dbconnect()
    data=request.get_json()
    date = data["date"]
    sql="select picid,name,danger_level,is_virtual,is_real,is_text,is_other,username \
        from updatelist,picdata \
        where timediff(timediff('{} 00:00:00',date),'24:00:00')<0 and timediff('{} 00:00:00',date)>0 \
            and picid = picdata.id".format(date,date)
    cursor.execute(sql)
    myresult = cursor.fetchall()
    response = []
    for i in myresult:
        response.append(
            {
                "id":i[0],
                "original":i[1],
                "thumbnail":'static/img_small/'+i[1],
                "danger_level":i[2],
                "is_virtual":i[3],
                "is_real":i[4],
                "is_text":i[5],
                "is_other":i[6],
                "username":i[7]
            }
        )
    mydb.close()
    return jsonify(response)


    

# @app.before_request
# def before_request_cookie():
#     # print(request.full_path)
#     password = request.cookies.get("password")
#     if request.method == "OPTIONS":
#         return None
#     if password != PASSWORD:
#         return "密码错误",504,[]
#     else:
#         return None
    
# 启动运行
if __name__ == '__main__':
    app.run(host="127.0.0.1")   # 这样子会直接运行在本地服务器，也即是 localhost:5000
   # app.run(host='your_ip_address') # 这里可通过 host 指定在公网IP上运行
   #需要接口: 1.给一个数字随机返回一定数量的图片信息 2.给一个列表，把列表里面的表进行修改 3.
