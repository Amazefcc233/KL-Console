from django.http import HttpResponse
from django.shortcuts import render
from django.shortcuts import redirect

import re

def legit_ip(_ip):
    compile_ip = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if compile_ip.match(_ip):
        return True
    else:
        return False

def ip_intr_extr(huanggr):
    intr = [10,127,172,192]
    intranet_ips = []
    extranet_ips = []
    for i in huanggr:
        for ii in intr:
            _ip = re.match( r'%s.*' %(ii), i)
            if _ip:
                intranet_ips.append(_ip.group())
    extranet_ips = list(set(huanggr)-set(intranet_ips))
    return intranet_ips,extranet_ips

def intranet_ip_check(ip):
    if legit_ip(ip):
        ip_lst = [ip]
        if len(ip_intr_extr(ip_lst)[0]) != 0:
            return True
        else:
            return False
    else:
        return False

def index(request):
    print(request.COOKIES.get("name"))
    print(request.COOKIES.get("passsword"))
    if request.COOKIES.get("passsword") == None:
        return redirect('/login/')
    else:
        return render(request, 'index.html')

def login(request):
    if request.COOKIES.get("passsword") == None:
        if request.method == "POST":
            # print(request.body)
            # print(request.POST.get('workerId'))
            if request.META.get('HTTP_X_FORWARDED_FOR'):
                ip = request.META.get("HTTP_X_FORWARDED_FOR")
            else:
                ip = request.META.get("REMOTE_ADDR")

            if intranet_ip_check('127.0.0.1') != True:
                return render(request, 'login.html', {"err":51400002,"reason":"Insecure login","message":"* 因安全原因，请连接至公司内网之后再进行登录操作."})
            elif request.POST.get('passwd') != "000":
                return render(request, 'login.html', {"err":51400001,"reason":"Wrong workerId or passwd","message":"* 请正确输入工号和密码. 请注意他们都是区分大小写的."})
            else:
                # return render(request, 'mfa-verify.html')
                return redirect('/mfaVerify/')
        return render(request, 'login.html')
    else:
        return redirect('/')

def mfaVerify(request):
    if request.method == "POST":
        mfaCode = request.POST.get('mfa')
        try:
            mfaCode = int(mfaCode)
        except:
            mfaCode = 0
        
        if mfaCode != 111111:
            return render(request, 'mfa-verify.html', {"err":51400002,"reason":"Wrong mfa code","message":"* MFA验证码不正确,或者服务器端时间不对"})
        else:
            # return render(request, 'mfa-verify.html')
            response = redirect('/',{"err":0,"userRealName":"张三"})
            # 设置cookies
            response.set_cookie('name','test')
            # 设置加密cookies
            response.set_signed_cookie('passsword','123456',max_age=3,salt='18268321hs')
            return response

    return render(request, 'mfa-verify.html')