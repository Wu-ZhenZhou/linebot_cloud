# coding: utf-8

#載入LineBot所需要的模組
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
#訊息比對
import re 
#use imgur
from imgurpython import ImgurClient
import pyimgur
from PIL import Image,ImageDraw
#use OCR
import pytesseract
import cv2
import numpy as np
#爬蟲用
import requests
from bs4 import BeautifulSoup
import pandas as pd
pd.set_option('display.width', 500)    #设置整体宽度
pd.set_option('display.max_rows', None)
import time
import random
import os
from datetime import datetime, timedelta



app = Flask(__name__)

# 必須放上自己的Channel Access Token
line_bot_api = LineBotApi('YOUR Channel Access Token')

# 必須放上自己的Channel Secret
handler = WebhookHandler('YOUR Channel Secret')

#伺服器檢測
line_bot_api.push_message('YOUR_LINE_ID', TextSendMessage(text='已連接伺服器'))



#取得圖片URI
def glucose_graph(client_id, imgpath):
    im = pyimgur.Imgur(client_id)
    upload_image = im.upload_image(imgpath, title="Uploaded with PyImgur")
    return upload_image.link



def img_OCR(image_path):
    img = Image.open(image_path)
    #text data get
    custom_config = r'chi_tra'
    text = pytesseract.image_to_string(img, custom_config)
    text = re.sub(r',','',text)
    text = re.sub(r'”','',text)
    return text



#圖片區域
def tableline(img):
    x_line=[0] * img.shape[0]
    y_line=[0] * img.shape[1]
    for y in range(img.shape[0]):
        for x in range(img.shape[1]):
            if img[y,x][0] == 0 :
                x_line[y] = x_line[y] + 1
                y_line[x] = y_line[x] + 1
    return x_line,y_line
def gray_his(img_path):
    img = cv2.imread(img_path)
    # 轉為灰階圖片
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    #二值化
    ret1, his1 = cv2.threshold(gray, 205, 255, cv2.THRESH_BINARY)
    cv2.imwrite('D:/linebot_to_google/Image/his.jpg', his1)
    return 'D:/linebot_to_google/Image/his.jpg'


def crop_large(img, img1, list1):
    top = 0
    button = 0
    for i in range(int(len(list1)/2), 0, -1):
        if img[i,0][0] == 0:
            top = i
            break
    for i in range(int(len(list1)/2), len(list1)):
        if img[i,0][0] == 0:
            button = i
            break
    crop_img = img[top+1:button, 0:img.shape[1]]
    img_use = img1[top+1:button, 0:img1.shape[1]]
    cv2.imwrite('D:/linebot_to_google/Image/crop_large.jpg', img_use)
    return crop_img, img_use
def crop_little(img, y_list, x_list):
    point = [y_list[0], x_list[0]]
    text = []
    for y in range(1, len(y_list)):
        for x in range(1, len(x_list)):
            crop_img = img[point[0]+2:y_list[y]-1, point[1]+2:x_list[x]-1]
            point[1] = x_list[x]
            if point[1] == x_list[-1]:
                point[1] = x_list[0]
            if x in [3, 7, 10] and y > 1:
                cv2.imwrite('D:/linebot_to_google/Image/crop_little.jpg', crop_img)
                OCR_text = img_OCR('D:/linebot_to_google/Image/crop_little.jpg')
                OCR_text = re.sub(r'\n','',OCR_text)
                text.append(OCR_text)
        point[0] = y_list[y]
    return text


def point_pop(point):
    cord=[]
    for i in range(len(point)-1):
        if point[i+1]-point[i] < 3:
            cord.append(i)
    for i in range(len(cord)-1, -1, -1):
        point.pop(cord[i])
    return point
def table_xy_axis(x_line, y_line):
    xcount = 0
    ycount = 0
    x_point = []
    y_point = []
    yhigh = 0
    for i in range(len(x_line)):
        if (x_line[i] < len(y_line)-10) and (x_line[i] > len(y_line)-100):
            x_point.append(i)
    for i in range(len(y_line)):
        if y_line[i] > yhigh:
            yhigh = y_line[i]
    for i in range(len(y_line)):
        if y_line[i] > int(yhigh*80/100):
            y_point.append(i)
    x_point = point_pop(x_point)
    y_point = point_pop(y_point)
    return x_point, y_point



def getdata(image_path,datapath):
    img = cv2.imread(image_path)
    imgpath = gray_his(image_path)
    img_his = cv2.imread(imgpath)
    x_line, y_line = tableline(img_his)
    cropimg,  cropimg_use = crop_large(img_his, img, x_line)
    x_line, y_line = tableline(cropimg)
    x_axis, y_axis = table_xy_axis(x_line, y_line)
    text = crop_little(cropimg_use, x_axis, y_axis)
    with open(datapath, 'w') as fd: 
        for chenk in range(len(text)):
            if chenk == len(text)-1:
                fd.write(text[chenk])
            elif chenk % 3 == 2:
                fd.write(text[chenk]+"\n")
            else:
                fd.write(text[chenk]+" ")



#讀檔
def load_data(userid):
    dataexist = True
    path = 'D:/linebot_to_google/stock_data/'+ str(userid) +'.txt'
    stock_code=[]
    stock_name=[]
    stock_inventories=[]
    stock_price=[]
    if os.path.isfile(path):
        with open(path, newline='') as fd:
            for line in fd.readlines():
                line = line.rstrip()
                if len(line)==2:
                    continue
                splited = line.split(" ")
                stock_code.append(splited[0])
                stock_name.append(splited[1])
                stock_inventories.append(splited[2])
                stock_price.append(splited[3])
    else:
        dataexist = False
    return stock_code, stock_name, stock_inventories, stock_price, dataexist



#檢查
def check_data(userid):
    path = 'D:/linebot_to_google/stock_data/'+ str(userid) +'.txt'
    code, name, inventories, price, dataexist = load_data(userid)
    for each in range(len(code)):
        money = float(stock_price(code[each]))
        pay = float(price[each])
        if pay/money > 5:
            pay = pay/10
            price[each] = str(pay)
            dataexist = False
    if dataexist == False:
        with open(path, 'w') as fd: 
            for each in range(len(code)):
                fd.write(code[each]+" ")
                fd.write(name[each]+" ")
                fd.write(inventories[each]+" ")
                fd.write(price[each]+"\n")



#爬股價
def stock_price(stock_code):
    url = 'https://www.google.com/finance/quote/'+str(stock_code)+':TPE'
    response = requests.get(url=url)
    soup = BeautifulSoup(response.text, 'lxml')
    info_items = soup.find_all('div', 'AHmHk')
    price = info_items[0].find('div', 'YMlKec fxKbKc').text.split('$')[-1].strip()
    price = re.sub(r',','',str(price))
    return price


def calendar(stock_code):
    #爬行事曆
    data=''
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
        'X-Amzn-Trace-Id': 'Root=1-64455a40-45b7fed252d2832544cbf70d'
    }


    response = requests.get("https://goodinfo.tw/tw/StockDetail.asp?STOCK_ID="+str(stock_code),headers = headers) #將此頁面的HTML GET下來
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    match = re.search(r"您的瀏覽量異常", str(soup))
    if match:
        return 'website error'
    name = soup.find('a','link_blue',style="font-size:14pt;font-weight:bold;").text
    name = re.sub(r'\xa0',' ',name)
    splited = name.split(" ")
    result = soup.find('table','b1 p4_4 r10 row_mouse_over box_shadow').find_all('nobr')
    data = str(name)
    date_pattern = r'^\d{4}/\d{2}/\d{2}$'
    for item in result:
        item = str(item)
        item = re.sub('<.*?>', '', item)
        match = re.match(date_pattern, str(item))
        if match:
            item = str(item) + datecompare(str(item))
        data = data+"\n"+str(item)
    return data



#爬除息
def exdividend(name):
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'}
    response = requests.get("https://goodinfo.tw/tw/StockDividendScheduleList.asp?MARKET_CAT=%E5%85%A8%E9%83%A8&YEAR=%E5%8D%B3%E5%B0%87%E9%99%A4%E6%AC%8A%E6%81%AF&INDUSTRY_CAT=%E5%85%A8%E9%83%A8",headers = headers) #將此頁面的HTML GET下來
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    result = soup.select_one("#divDetail")

    dfs = pd.read_html(result.prettify())
    
    #資料擷取
    regex = re.compile(r'(\w+[\'\/\+\-\*\<\%\&\.\,\w+]*)')
    mylist = re.findall(regex,str(dfs))
    startsign = False
    counter = 0
    data_all = []
    data = ""
    data2 = ""
    choose = False
    for item in mylist:
        if (startsign == False) and (('上市' in item)or('上櫃' in item)or('興櫃' in item) ):
            counter = 20
            startsign = True
            continue
        if counter <= 0:
            continue
        if startsign == True and counter == 1:
            startsign = False
        if '即將發放' in item:
            continue
        if '即將除權' in item:
            continue
        if counter == 20:
            if str(item) in name:
                choose = True
                
            if data2 == "" and choose == True:
                data_register = str(item)
            elif data == "" and choose == False:
                data_register = str(item)
            else:
                data_register = data_register+"\n\n"+str(item)
        elif counter == 19:
            data_register = data_register + " " + str(item)
        elif counter == 17:
            item = re.sub(r"'",'/',str(item))
            item = "20" + item
            item = item + datecompare(item)
            data_register = data_register+"\n除息日:"+str(item)
        elif counter == 1:
            data_register = data_register+"\n股利:  "+str(item)
            if choose == True:
                data2 = data2 + data_register
                choose = False
            else:
                data = data + data_register
            data_register = ""
            if len(data)>4800:
                data_all.append(data)
                data = ""
        counter -= 1
    data_all.append(data)
    if data2 != "":
        if len(data_all)<5:
            data_all.append(data2)
        else:
            data_all.insert(4,data2)
            data_all = data_all[0:5]
    return data_all



def paid_dividends(name):
    #爬股利
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'}
    response = requests.get("https://goodinfo.tw/tw/StockDividendScheduleList.asp?MARKET_CAT=%E5%85%A8%E9%83%A8&INDUSTRY_CAT=%E5%85%A8%E9%83%A8&YEAR=%E5%8D%B3%E5%B0%87%E7%99%BC%E6%94%BE%E8%82%A1%E5%88%A9",headers = headers) #將此頁面的HTML GET下來
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'lxml')
    result = soup.select_one("#divDetail")
    dfs = pd.read_html(result.prettify())
    
    #資料擷取
    regex = re.compile(r'(\w+[\'\/\+\-\*\<\%\&\.\,\w+]*)')
    mylist = re.findall(regex,str(dfs))
    startsign = False
    counter = 0
    data_all = []
    data = ""
    data2 = ""
    choose = False
    for item in mylist:
        if (startsign == False) and (('上市' in item)or('上櫃' in item)or('興櫃' in item) ):
            counter = 20
            startsign = True
            continue
        if counter <= 0:
            continue
        if startsign == True and counter == 1:
            startsign = False
        if '即將除息' in item:
            continue
        if '今日除息' in item:
            continue
        if counter == 20:
            if str(item) in name:
                choose = True
                
            if data2 == "" and choose == True:
                data_register = str(item)
            elif data == "" and choose == False:
                data_register = str(item)
            else:
                data_register = data_register+"\n\n"+str(item)
        elif counter == 19:
            data_register = data_register + " " + str(item)
        elif counter == 13:
            item = re.sub(r"'",'/',str(item))
            item = "20" + item
            item = item + datecompare(item)
            data_register = data_register+"\n發放日:"+str(item)
        elif counter == 1:
            data_register = data_register+"\n股利:  "+str(item)
            if choose == True:
                data2 = data2 + data_register
                choose = False
            else:
                data = data + data_register
            data_register = ""
            if len(data)>4800:
                data_all.append(data)
                data = ""
        counter -= 1
    data_all.append(data)
    if data2 != "":
        if len(data_all)<5:
            data_all.append(data2)
        else:
            data_all.insert(4,data2)
            data_all = data_all[0:5]
    return data_all



def datecompare(date):
    compare = ""
    # 要比較的日期
    compare_date = datetime.strptime(date, "%Y/%m/%d").date()

    # 將時間加上一個月
    one_month_later = datetime.now() + timedelta(days=30)
    # 進行日期比較
    if compare_date == datetime.now().date():
        compare = "\u2B05"
    elif compare_date < one_month_later.date() and compare_date > datetime.now().date():
        compare = "\u2190"
    else:
        compare = ""
    
    return compare



# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

#訊息傳遞區塊
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    UserId = event.source.user_id
    profile = line_bot_api.get_profile(UserId)
    message = event.message.text
    code, name, inventories, price ,data_exist= load_data(UserId)
    if re.match("使用說明",message):
        local_save = ['D:/linebot_to_google/Image/Guide1.png','D:/linebot_to_google/Image/Guide2.png','D:/linebot_to_google/Image/Guide3.png','D:/linebot_to_google/Image/Guide4.png']
        text = []
        for path in local_save:
            img_url = glucose_graph("YOUR clientID", path)
            img_message = ImageSendMessage(original_content_url=img_url, preview_image_url=img_url)
            text.append(img_message)
        text_message = TextSendMessage(text="日期標示：\n \u2190:近一個月內\n \u2B05:今日\n行事曆功能因需遵守爬蟲規範需等待較長時間，煩請耐心等候")
        text.append(text_message)
        line_bot_api.reply_message(event.reply_token,text)
        
    elif re.match("除權息日期",message):
        if data_exist == False:
            name = []
        else :
            name = code
        message = []
        data = exdividend(name)
        for i in range(len(data)):
            text_message = TextSendMessage(text= str(data[i]))
            message.append(text_message)
        line_bot_api.reply_message(event.reply_token,message)
        
    elif re.match("股利發放日期",message):
        if data_exist == False:
            name = []
        else :
            name = code
        message = []
        data = paid_dividends(name)
        for i in range(len(data)):
#             print(i," ",data[i])
            text_message = TextSendMessage(text= data[i])
            message.append(text_message)
        line_bot_api.reply_message(event.reply_token,message)
        
    elif re.match("股價查詢",message):
        if data_exist == False:
            text = "請先截圖提供個人股票資料"
        else:
            text = ''
            for each in range(len(code)):
                text = text + code[each] + '  ' + name[each] + '\n'
                if re.match("\n",price[each]):
                    text = text + '成交價：' + str(price[each])
                else:
                    text = text + '成交價：' + str(price[each]) + '\n'
                text = text + '市　價：' + str(stock_price(code[each]))+'\n'
                text = text + '股　數：' + str(inventories[each])
                if code[each] in code[-1]:
                    text = text
                else:
                    text = text + '\n\n'
            
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text))
        
    elif re.match("行事曆查詢",message):
        if data_exist == False:
            message = "請先截圖提供個人股票資料"
        else:
            message=''
            for eachcode in code:
                text = calendar(eachcode)
#                 print(text)
                if re.match("website error", text):
                    message = message + '網站繁忙中，請使用其他功能'
                    break
                if eachcode != code[-1]:
                    message = message+text+'\n\n'
                    time.sleep(random.randint(15,20))
                elif eachcode == code[-1]:
                    message = message + calendar(eachcode)
                
        line_bot_api.reply_message(event.reply_token,TextSendMessage(message))
        
    elif re.match("損益查詢",message):
        if data_exist == False:
            text = "請先截圖提供個人股票資料"
        else:
            text = ''
            sum_profit_loss=0
            sum_price = 0
            for each in range(len(code)):
                public_price = stock_price(code[each])
                profit_loss = (float(public_price) - float(price[each])) * int(inventories[each])
                Profit_loss_ratio = int((float(public_price) - float(price[each])) / float(price[each]) * 10000)/100
                text = text + code[each] + ' ' + name[each] + '\n'
                text = text + '損益值：' + str(round(profit_loss,2)) + '\n'
                text = text + '損益比：' + str(Profit_loss_ratio) + "%\n"
                text = text + '\n'
                sum_profit_loss = round(sum_profit_loss + profit_loss,2)
                sum_price = sum_price + round(float(price[each]) * float(inventories[each]), 2)
                sum_Profit_loss_ratio = round((float(sum_profit_loss) / float(sum_price))*100, 2)
            text = text + '總  損  益：' + str(sum_profit_loss) + '\n'
            text = text + '總損益比：' + str(sum_Profit_loss_ratio) + '%'
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text))
    else:
        line_bot_api.reply_message(event.reply_token,TextSendMessage("麻煩上傳正確截圖或使用圖文選單~~"))
    
    


@handler.add(MessageEvent, message=ImageMessage)
def handle_message(event):
    #頻道紀錄
    UserId = event.source.user_id
    profile = line_bot_api.get_profile(UserId)

    
    #活動顯示
    SendImage = line_bot_api.get_message_content(event.message.id)
    local_save = 'D:/linebot_to_google/Image/'+ UserId +'.jpg'
    with open(local_save, 'wb') as fd:
        for chenk in SendImage.iter_content():
            fd.write(chenk)

    img_url = glucose_graph("YOUR client ID", local_save)
    
    stock_save = 'D:/linebot_to_google/stock_data/'+ UserId +'.txt'
    
    #擷取資料
    getdata(local_save,stock_save)
    check_data(UserId)
    code, name, inventories, price ,data_exist= load_data(UserId)
    text = ''
    for each in range(len(code)):
        text = text + code[each] + '  ' + name[each] + '\n'
        if re.match("\n",price[each]):
            text = text + '成交價：' + str(price[each])
        else:
            text = text + '成交價：' + str(price[each]) + '\n'
        text = text + '市　價：' + str(stock_price(code[each]))+'\n'
        text = text + '股　數：' + str(inventories[each])
        if code[each] in code[-1]:
            text = text
        else:
            text = text + '\n\n'
    line_bot_api.reply_message(event.reply_token,TextSendMessage(text))#"上傳截圖成功~~"

#主程式
import os 
if (__name__ == "__main__"):
    port = int(os.environ.get('PORT', 400))
    app.run(host='0.0.0.0', port=port)