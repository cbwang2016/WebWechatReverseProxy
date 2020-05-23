# coding:utf-8
import os
import re
import shutil
import time
from collections import OrderedDict

import itchat
from apscheduler.schedulers.blocking import BlockingScheduler
from flask import Flask, Response, request
from itchat.content import *

rec_tmp_dir = os.path.join(os.getcwd(), 'tmp/')
msg_information = {}
face_bug = None  # 针对表情包的内容
sched = BlockingScheduler()


def clear_cache():
    # 当前时间
    print('Clearing cache...')
    cur_time = time.time()
    # 遍历字典，如果有创建时间超过2分钟(120s)的记录，删除，非文本的话，连文件也删除
    for key in list(msg_information.keys()):
        if int(cur_time) - int(msg_information.get(key).get('msg_time')) > 120:
            if msg_information.get(key).get('msg_type') == "Attachment" \
                    or msg_information.get(key).get('msg_type') == "Video" \
                    or msg_information.get(key).get('msg_type') == 'Picture' \
                    or msg_information.get(key).get('msg_type') == 'Recording':
                file_path = os.path.join(
                    rec_tmp_dir, msg_information.get(key).get('msg_content'))
                # print('Deleting ' + file_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
            msg_information.pop(key)


def start_schedule():
    sched.add_job(clear_cache, 'interval', minutes=2)
    sched.start()


def after_logout():
    sched.shutdown()
    shutil.rmtree(rec_tmp_dir)


@itchat.msg_register([TEXT, PICTURE, FRIENDS, CARD, MAP, SHARING, RECORDING, ATTACHMENT, VIDEO], isFriendChat=True,
                     isMpChat=True)
def handle_receive_msg(msg):
    global face_bug
    msg_time_rec = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime())  # 接受消息的时间
    msg_from = itchat.search_friends(userName=msg['FromUserName'])[
        'NickName']  # 在好友列表中查询发送信息的好友昵称
    msg_time = msg['CreateTime']  # 信息发送的时间
    msg_id = msg['MsgId']  # 每条信息的id
    msg_content = None  # 储存信息的内容
    msg_share_url = None  # 储存分享的链接，比如分享的文章和音乐
    print(msg['Type'])
    print(msg['MsgId'])
    if msg['Type'] == 'Text' or msg['Type'] == 'Friends':  # 如果发送的消息是文本或者好友推荐
        msg_content = msg['Text']
        print(msg_content)

    # 如果发送的消息是附件、视屏、图片、语音
    elif msg['Type'] == "Attachment" or msg['Type'] == "Video" \
            or msg['Type'] == 'Picture' \
            or msg['Type'] == 'Recording':
        msg_content = msg['FileName']  # 内容就是他们的文件名
        msg['Text'](rec_tmp_dir + msg['FileName'])  # 下载文件
        # print( msg_content
    elif msg['Type'] == 'Card':  # 如果消息是推荐的名片
        msg_content = msg['RecommendInfo']['NickName'] + '的名片'  # 内容就是推荐人的昵称和性别
        if msg['RecommendInfo']['Sex'] == 1:
            msg_content += '性别为男'
        else:
            msg_content += '性别为女'

        print(msg_content)
    elif msg['Type'] == 'Map':  # 如果消息为分享的位置信息
        x, y, location = re.search(
            "<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1, 2, 3)
        if location is None:
            msg_content = r"纬度->" + x.__str__() + " 经度->" + y.__str__()  # 内容为详细的地址
        else:
            msg_content = r"" + location
    elif msg['Type'] == 'Sharing':  # 如果消息为分享的音乐或者文章，详细的内容为文章的标题或者是分享的名字
        msg_content = msg['Text']
        msg_share_url = msg['Url']  # 记录分享的url
        print(msg_share_url)
    face_bug = msg_content

    # 将信息存储在字典中，每一个msg_id对应一条信息
    msg_information.update(
        {
            msg_id: {
                "msg_from": msg_from, "msg_time": msg_time, "msg_time_rec": msg_time_rec,
                "msg_type": msg["Type"],
                "msg_content": msg_content, "msg_share_url": msg_share_url
            }
        }
    )


# 这个是用于监听是否有friend消息撤回
@itchat.msg_register(NOTE, isFriendChat=True, isGroupChat=True, isMpChat=True)
def information(msg):
    # 这里如果这里的msg['Content']中包含消息撤回和id，就执行下面的语句
    if '撤回了一条消息' in msg['Content']:
        # 在返回的content查找撤回的消息的id
        old_msg_id = re.search(
            "\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
        old_msg = msg_information.get(old_msg_id)  # 得到消息
        print(old_msg)
        if len(old_msg_id) < 11:  # 如果发送的是表情包
            itchat.send_file(face_bug, toUserName='filehelper')
        else:  # 发送撤回的提示给文件助手
            msg_body = "【" \
                       + old_msg.get('msg_from') + " 撤回了 】\n" \
                       + old_msg.get("msg_type") + " 消息：" + "\n" \
                       + old_msg.get('msg_time_rec') + "\n" \
                       + r"" + old_msg.get('msg_content')
            # 如果是分享的文件被撤回了，那么就将分享的url加在msg_body中发送给文件助手
            if old_msg['msg_type'] == "Sharing":
                msg_body += "\n就是这个链接➣ " + old_msg.get('msg_share_url')

            # 将撤回消息发送到文件助手
            itchat.send_msg(msg_body, toUserName='filehelper')
            # 有文件的话也要将文件发送回去
            if old_msg["msg_type"] == "Picture" \
                    or old_msg["msg_type"] == "Recording" \
                    or old_msg["msg_type"] == "Video" \
                    or old_msg["msg_type"] == "Attachment":
                file = '@fil@%s' % (rec_tmp_dir + old_msg['msg_content'])
                itchat.send(msg=file, toUserName='filehelper')
                os.remove(rec_tmp_dir + old_msg['msg_content'])
            # 删除字典旧消息
            msg_information.pop(old_msg_id)


@itchat.msg_register([TEXT, PICTURE, FRIENDS, CARD, MAP, SHARING, RECORDING, ATTACHMENT, VIDEO], isGroupChat=True)
def handle_receive_msg2(msg):
    global face_bug
    msg_time_rec = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime())  # 接受消息的时间
    # groupid = msg['FromUserName']
    # chatroom = itchat.search_chatrooms(userName=groupid)
    msg_Actual_from = msg['ActualNickName']
    # msg_Actual_from = msg['User']
    # msg_from = msg_Actual_from['Self']['NickName']
    msg_from = msg_Actual_from
    msg_time = msg['CreateTime']  # 信息发送的时间
    msg_id = msg['MsgId']  # 每条信息的id
    msg_content = None  # 储存信息的内容
    msg_share_url = None  # 储存分享的链接，比如分享的文章和音乐
    print(msg['Type'])
    print(msg['MsgId'])
    if msg['Type'] == 'Text' or msg['Type'] == 'Friends':  # 如果发送的消息是文本或者好友推荐
        msg_content = msg['Text']
        print(msg_content)

    # 如果发送的消息是附件、视屏、图片、语音
    elif msg['Type'] == "Attachment" or msg['Type'] == "Video" \
            or msg['Type'] == 'Picture' \
            or msg['Type'] == 'Recording':
        msg_content = msg['FileName']  # 内容就是他们的文件名
        msg['Text'](rec_tmp_dir + msg['FileName'])  # 下载文件
        # print( msg_content
    elif msg['Type'] == 'Card':  # 如果消息是推荐的名片
        msg_content = msg['RecommendInfo']['NickName'] + '的名片'  # 内容就是推荐人的昵称和性别
        if msg['RecommendInfo']['Sex'] == 1:
            msg_content += '性别为男'
        else:
            msg_content += '性别为女'

        print(msg_content)
    elif msg['Type'] == 'Map':  # 如果消息为分享的位置信息
        x, y, location = re.search(
            "<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1, 2, 3)
        if location is None:
            msg_content = r"纬度->" + x.__str__() + " 经度->" + y.__str__()  # 内容为详细的地址
        else:
            msg_content = r"" + location
    elif msg['Type'] == 'Sharing':  # 如果消息为分享的音乐或者文章，详细的内容为文章的标题或者是分享的名字
        msg_content = msg['Text']
        msg_share_url = msg['Url']  # 记录分享的url
        print(msg_share_url)
    face_bug = msg_content

    # 将信息存储在字典中，每一个msg_id对应一条信息
    msg_information.update(
        {
            msg_id: {
                "msg_from": msg_from, "msg_time": msg_time, "msg_time_rec": msg_time_rec,
                "msg_type": msg["Type"],
                "msg_content": msg_content, "msg_share_url": msg_share_url
            }
        }
    )


# 这个是用于监听是否有Group消息撤回
@itchat.msg_register(NOTE, isGroupChat=True, isMpChat=True)
def information2(msg):
    # 这里如果这里的msg['Content']中包含消息撤回和id，就执行下面的语句
    if '撤回了一条消息' in msg['Content']:
        # 在返回的content查找撤回的消息的id
        old_msg_id = re.search(
            "\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
        old_msg = msg_information.get(old_msg_id)  # 得到消息
        print(old_msg)
        if len(old_msg_id) < 11:  # 如果发送的是表情包
            itchat.send_file(face_bug, toUserName='filehelper')
        else:  # 发送撤回的提示给文件助手
            msg_body = "【" \
                       + old_msg.get('msg_from') + " 群消息撤回提醒】\n" \
                       + " 撤回了 " + old_msg.get("msg_type") + " 消息：" + "\n" \
                       + old_msg.get('msg_time_rec') + "\n" \
                       + r"" + old_msg.get('msg_content')
            # 如果是分享的文件被撤回了，那么就将分享的url加在msg_body中发送给文件助手
            if old_msg['msg_type'] == "Sharing":
                msg_body += "\n就是这个链接➣ " + old_msg.get('msg_share_url')

            # 将撤回消息发送到文件助手
            itchat.send_msg(msg_body, toUserName='filehelper')
            # 有文件的话也要将文件发送回去
            if old_msg["msg_type"] == "Picture" \
                    or old_msg["msg_type"] == "Recording" \
                    or old_msg["msg_type"] == "Video" \
                    or old_msg["msg_type"] == "Attachment":
                file = '@fil@%s' % (rec_tmp_dir + old_msg['msg_content'])
                itchat.send(msg=file, toUserName='filehelper')
                os.remove(rec_tmp_dir + old_msg['msg_content'])
            # 删除字典旧消息
            msg_information.pop(old_msg_id)


app = Flask(__name__)

WX_URL = "https://wx.qq.com/"
FILE_URL = "https://file.wx.qq.com/"
RES_URL = "https://res.wx.qq.com/"
PUSH_URL = "https://webpush.weixin.qq.com/"
LOCAL_URL = "127.0.0.1:5000"


@app.route('/', methods=['GET'])
def show_index():
    # headers = {'User-Agent': itchat.config.USER_AGENT}
    # return itchat.originInstance.s.get(itchat.originInstance.loginInfo['url'], headers=headers).content
    return show_subpath('')


@app.route('/<path:subpath>', methods=['GET', 'POST'])
def show_subpath(subpath):
    # show the subpath after /path/
    if 'webwxstatreport' in subpath:  # block stat report
        return ''
    # if 'webwxlogout' in subpath:
    #     print('\n\n\n\n\n\n\nERROR??????????!!!!!!!!!!!!!!!!!!!!!\n\n\n\n\n\n\n')
    #     return ''

    data = request.data

    if subpath.startswith('cgi-bin/mmwebwx-bin/synccheck'):
        base_url = PUSH_URL
    elif subpath.startswith('a/wx_fed/'):
        base_url = RES_URL
    elif subpath.startswith('cgi-bin/mmwebwx-bin/webwxuploadmedia') or subpath.startswith(
            'cgi-bin/mmwebwx-bin/webwxgetmedia'):
        base_url = FILE_URL
    else:
        base_url = WX_URL
    url = base_url + subpath
    # print('\nurl =', url, '\n')

    if request.content_type:
        headers = {'Content-Type': request.content_type,
                   'User-Agent': itchat.config.USER_AGENT}
    else:
        headers = {'User-Agent': itchat.config.USER_AGENT}

    if request.method == 'POST':
        if subpath.startswith('cgi-bin/mmwebwx-bin/webwxuploadmedia'):
            headers = {'User-Agent': itchat.config.USER_AGENT}
            if 'filename' not in request.files:
                return ''
            f = request.files['filename']
            files = OrderedDict()
            for k in request.form:
                files[k] = (None, request.form[k])
            files['filename'] = (f.filename, f.read(), f.content_type)

            r = itchat.originInstance.s.post(
                url, params=request.args, files=files, headers=headers, timeout=itchat.config.TIMEOUT)

        else:
            r = itchat.originInstance.s.post(
                url, params=request.args, headers=headers, data=data)
    else:
        r = itchat.originInstance.s.get(
            url, headers=headers, params=request.args)

    try:
        rtn = r.content.decode('utf-8').replace('webpush.weixin.qq.com', LOCAL_URL).replace(
            'res.wx.qq.com', LOCAL_URL).replace('file.wx.qq.com', LOCAL_URL).replace('js.aq.qq.com',
                                                                                     '127.0.0.1').replace('https://',
                                                                                                          'http://')
        # rtn = rtn.replace('loginout:', 'hahaha:')  # ban logout function
    except:
        rtn = r.content

    resp = Response(rtn, content_type=r.headers['content-type'])
    cookies = itchat.originInstance.s.cookies.get_dict()
    for k in cookies:
        resp.set_cookie(k, cookies[k])
    return resp


if __name__ == '__main__':

    print('main started!')
    if not os.path.exists(rec_tmp_dir):
        os.mkdir(rec_tmp_dir)
    itchat.auto_login(hotReload=True, exitCallback=after_logout, enableCmdQR=False)
    itchat.run(blockThread=False)
    print('itchat started!')

    import threading

    ScheduleThread = threading.Thread(target=start_schedule)
    ScheduleThread.setDaemon(True)
    ScheduleThread.start()

    app.run(debug=True, host='127.0.0.1', port=5000)
