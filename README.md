# WebWechatReverseProxy
带有撤回提醒小助手的Web Wechat反向代理。

![https://i.loli.net/2020/05/24/lGjE6PWs9HutgIm.png](https://i.loli.net/2020/05/24/lGjE6PWs9HutgIm.png)
## Features
 - Notify you the messages recalled by your friend.
 - Let you use web wechat client normally while this bot is online.
 - Optimized web wechat external link redirection.
 - Blocked web wechat stat analysis.
 - If you have a server(e.g. raspberry pi), you can stay online persistently. You can also use nginx to make it accessible from outside localhost. Note that you should take security measures such as [HTTP Basic Authentication](https://docs.nginx.com/nginx/admin-guide/security-controls/configuring-http-basic-authentication/).
 
## Installations
```
pip install -r requirements.txt
```

## Usage
```
>python main.py -h
usage: main.py [-h] [-a ADDRESS] [-p PORT] [-o HOST] [-s] [-d] [-q {0,1,2}]

wx.qq.com reverse proxy.

optional arguments:
  -h, --help            show this help message and exit
  -a ADDRESS, --address ADDRESS
                        the address of this web server
  -p PORT, --port PORT  listening port
  -o HOST, --host HOST  listening host
  -s, --https           whether this web server uses https
  -d, --debug           use flask debug
  -q {0,1,2}            show qrcode in command line; integers can be used to
                        fit strange char length

```

## Disclaimer
You are responsible for your own actions. If you mess something up, get banned or break any laws while using this software, it's your fault, and your fault only.

## Licence
[GPLv3](./LICENSE)