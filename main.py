# coding:utf-8
import logging
import os
import re
import time
from collections import OrderedDict

import coloredlogs
import itchat
from flask import Flask, Response, request, redirect
from itchat.content import *

coloredlogs.install()
rev_tmp_dir = os.path.join(os.getcwd(), 'tmp/')
msg_dict = {}


@itchat.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS], isFriendChat=True,
                     isGroupChat=True, isMpChat=True)
# 定义消息ID和消息时间，并且加以判断是群消息或者是好友消息
def handler_receive_msg(msg):
    # 每条消息id
    msg_id = msg['MsgId']
    # 接受消息的时间
    msg_time_rec = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 消息发送的时间
    msg_time = msg['CreateTime']
    # 储存信息的内容
    msg_content = None
    # 储存分享的链接，比如分享的文章和音乐
    msg_share_url = None

    group_name = group_members = ''

    # 判断是群消息或者是好友消息
    if 'ActualNickName' in msg:
        from_user = msg['ActualUserName']  # 群消息的发送者,用户的唯一标识
        msg_from = msg['ActualNickName']  # 发消息人的群内昵称
        # 获取所有好友
        friends = itchat.get_friends(update=True)

        for friend in friends:
            if from_user == friend['UserName']:  # 判断群里撤回消息的是否为自己好友
                if friend['RemarkName']:  # 优先使用好友的备注名称，没有则使用昵称
                    msg_from = friend['RemarkName']
                else:
                    msg_from = friend['NickName']
                break
        if msg['User']:
            group_name = msg['User']['NickName']
            group_members = msg['User']['MemberCount']
        else:
            # 获取所有的群
            groups = itchat.get_chatrooms(update=True)
            for group in groups:
                if msg['FromUserName'] == group['UserName']:  # 根据群消息的FromUserName匹配是哪个群
                    group_name = group['NickName']
                    group_members = group['MemberCount']
                    break

        if group_members:
            group_name = (group_name + "(" + str(group_members) + ")")
        else:
            group_name = 'failed to get group name!'
            logging.warning('failed to get group name!!')
            logging.warning(str(msg))
    # 否则是个人好友消息
    else:
        try:
            if itchat.search_friends(userName=msg['FromUserName'])['RemarkName']:  # 优先使用备注名称
                msg_from = itchat.search_friends(userName=msg['FromUserName'])['RemarkName']
            else:
                msg_from = itchat.search_friends(userName=msg['FromUserName'])['NickName']  # 在好友列表中查询发送信息的好友昵称
        except TypeError:
            logging.warning(str(msg))
            msg_from = "failed to get nick name"

    if msg['Type'] in ('Text', 'Friends'):
        msg_content = msg['Text']

        logging.info('[Text/Friends]: %s' % msg_content)
    elif msg['Type'] in ('Recording', 'Attachment', 'Video', 'Picture'):
        msg_content = r"" + msg['FileName']
        msg['Text'](rev_tmp_dir + msg_content)  # 保存文件

        logging.info('[Attachment/Video/Picture/Recording]: %s' % msg_content)
    elif msg['Type'] == 'Card':
        msg_content = msg['RecommendInfo']['NickName'] + r" 的名片"  # 内容就是推荐人的昵称和性别
        if msg['RecommendInfo']['Sex'] == 1:
            msg_content += '，性别为男'
        else:
            msg_content += '，性别为女'

        logging.info('[Card]: %s' % msg_content)
    elif msg['Type'] == 'Map':
        x, y, location = re.search("<location x=\"(.*?)\" y=\"(.*?)\".*label=\"(.*?)\".*", msg['OriContent']).group(1,
                                                                                                                    2,
                                                                                                                    3)
        if location is None:
            msg_content = r"纬度->" + x.__str__() + " 经度->" + y.__str__()
        else:
            msg_content = r"" + location

        logging.info('[Map]: %s' % msg_content)
    elif msg['Type'] == 'Sharing':
        msg_content = msg['Text']
        msg_share_url = msg['Url']  # 记录分享的url

        logging.info('[Sharing]: %s' % msg_content)

    # 更新字典
    msg_dict.update(
        {
            msg_id: {
                "msg_from": msg_from,
                "msg_time": msg_time,
                "msg_time_rec": msg_time_rec,
                "msg_type": msg["Type"],
                "msg_content": msg_content,
                "msg_share_url": msg_share_url,
                "group_name": group_name
            }
        }
    )

    # 自动删除130秒之前的消息，避免数据量太大后引起内存不足
    del_info = []
    for k in msg_dict:
        m_time = msg_dict[k]['msg_time']  # 取得消息时间
        if int(time.time()) - m_time > 130:
            del_info.append(k)
    if del_info:
        for i in del_info:
            msg_dict.pop(i)


# 这个是用于监听是否有friend消息撤回
@itchat.msg_register(NOTE, isFriendChat=True, isGroupChat=True, isMpChat=True)
# 收到note通知类消息，判断是不是撤回并进行相应操作
def send_msg_helper(msg):
    if re.search(r"\<\!\[CDATA\[.*撤回了一条消息\]\]\>", msg['Content']) is not None:
        # 获取消息id
        old_msg_id = re.search("\<msgid\>(.*?)\<\/msgid\>", msg['Content']).group(1)
        # 得到消息
        old_msg = msg_dict.get(old_msg_id)
        logging.info('[Recall]: %s' % old_msg)

        msg_body = "告诉你一个秘密~" '\n' \
                   + "【" + old_msg.get('msg_from') + "】" + " 撤回了一条消息！ " + '\n' \
                   + '➣消息类型：' + old_msg.get("msg_type") + '\n' \
                   + '➣时间：' + old_msg.get('msg_time_rec') + '\n' \
                   + (('➣群名：' + old_msg.get('group_name') + '\n') if old_msg.get('group_name') else '') \
                   + '快看看ta撤回了什么?' + '\n' \
                   + '⇣' + '\n' \
                   + r"【%s】" % old_msg.get('msg_content')

        # 如果分享的文件被撤回了，那么就将分享的url加在msg_body中发送给文件助手
        if old_msg['msg_type'] == "Sharing":
            msg_body += "\n就是这个链接➣ " + old_msg.get('msg_share_url')

        # 将撤回消息发送到文0 件助手
        itchat.send(msg_body, toUserName='filehelper')
        logging.info(msg_body)

        # 有文件的话也要将文件发送回去
        if old_msg["msg_type"] in ("Picture", "Recording", "Video", "Attachment"):
            file = '@fil@%s' % (rev_tmp_dir + old_msg['msg_content'])
            itchat.send(msg=file, toUserName='filehelper')
            os.remove(rev_tmp_dir + old_msg['msg_content'])

        # 删除字典旧信息
        msg_dict.pop(old_msg_id)


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
    if subpath.startswith('cgi-bin/mmwebwx-bin/webwxstatreport'):  # block stat report
        return ''
    if subpath.startswith('cgi-bin/mmwebwx-bin/webwxlogout'):  # block logout
        logging.warning('Warning: logout detected!')
        return ''
    if subpath.startswith('cgi-bin/mmwebwx-bin/webwxcheckurl'):
        url = request.args['requrl']
        return redirect(url)

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
                                                                                     '127.0.0.1')
        if not args.https:
            rtn = rtn.replace('https://', 'http://')
        rtn = rtn.replace('loginout:', 'hahaha:')  # ban logout function
    except:
        rtn = r.content

    resp = Response(rtn, content_type=r.headers['content-type'])
    cookies = itchat.originInstance.s.cookies.get_dict()
    for k in cookies:
        resp.set_cookie(k, cookies[k])
    return resp


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="wx.qq.com reverse proxy.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-a", "--address", type=str, help="the address of this web server", default="127.0.0.1:5000")
    parser.add_argument("-p", "--port", type=int, help="listening port", default=5000)
    parser.add_argument("-o", "--host", type=str, help="listening host", default="127.0.0.1")
    parser.add_argument("-s", '--https', action="store_true", help="whether this web server uses https")
    parser.add_argument("-d", '--debug', action="store_true", help="use flask debug")
    parser.add_argument("-q", type=int, choices=[0, 1, 2],
                        help="show qrcode in command line; integers can be used to fit strange char length",
                        default=2)
    args = parser.parse_args()
    LOCAL_URL = args.address

    logging.info('main started!')
    if not os.path.exists(rev_tmp_dir):
        os.mkdir(rev_tmp_dir)

    itchat.auto_login(hotReload=True, enableCmdQR=args.q, exitCallback=lambda: os.kill(os.getpid(), signal.SIGINT))
    itchat.run(blockThread=False)
    logging.info('itchat started!')

    app.run(debug=args.debug, host=args.host, port=args.port)
