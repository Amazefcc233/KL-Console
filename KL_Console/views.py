from django.http import HttpResponse, response
from django.shortcuts import render
from django.shortcuts import redirect

import re
import json

# ==================== ip查询部分 start ====================
# ip真实性核验
def legit_ip(_ip):
    compile_ip = re.compile('^((25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(25[0-5]|2[0-4]\d|[01]?\d\d?)$')
    if compile_ip.match(_ip):
        return True
    else:
        return False
# ip内网/外网区分
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
# ip内网检验
def intranet_ip_check(ip):
    if legit_ip(ip):
        ip_lst = [ip]
        if len(ip_intr_extr(ip_lst)[0]) != 0:
            return True
        else:
            return False
    else:
        return False

# ==================== 非django部分 end ====================
def index(request):
    print(request.session.get('userBasicInfo'))
    print(request.COOKIES.get("name"))
    print(request.COOKIES.get("passsword"))
    # if request.COOKIES.get("passsword") == None:
    if request.session.get('is_login') != True:
        return redirect('/login/')
    else:
        return render(request, 'index.html')

def logout(request):
    if request.session.get('is_login') != True:
        return redirect('/login/')
    request.session.flush()
    return redirect('/login/')

def login(request):
    # if request.COOKIES.get("passsword") == None:
    if request.session.get('is_login') != True:
        if request.method == "POST":
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
            # response =  redirect('index:index')
            # 设置cookies
            response.set_cookie('name','test')
            # 设置加密cookies
            response.set_signed_cookie('passsword','123456',max_age=7200,salt='18268321hs')
            context={}
            context['realName'] = '张三'
            context['department'] = '综合办'
            request.session['userBasicInfo'] = context
            request.session['permissions'] = ['score_submit','0']
            request.session['is_login'] = True
            request.session.set_expiry(7200)
            return response

    return render(request, 'mfa-verify.html')

def scoreSubmit(request):
    if request.session.get('is_login') == True:
        addScore = 1300
        removeScore = 100
        userScoreManagerInfo = {}
        userScoreManagerInfo['addScore'] = addScore
        userScoreManagerInfo['removeScore'] = removeScore
        userScoreManagerInfo['arper'] = float('%.2f' % (userScoreManagerInfo['removeScore'] / userScoreManagerInfo['addScore'] * 100))
        if userScoreManagerInfo['arper'] < 10.0:
            userScoreManagerInfo['lastScore'] = int(userScoreManagerInfo['addScore'] * 0.1 - userScoreManagerInfo['removeScore'])
        else:
            userScoreManagerInfo['lastScore'] = 0
        if request.method == "POST":
            pass
        # response = render(request, './Score/submit-score.html')
        request.session['userScoreManagerInfo'] = userScoreManagerInfo
        # return response
        return render(request, './Score/submit-score.html')
    else:
        logout(request)

def api_memberCheck(request):
    if request.method == "POST":
        if request.POST.get('workerId') == '0':
            return HttpResponse('true')
        else:
            return HttpResponse('false')
    else:
        return redirect('/')

def api_memberInfoLoad(request):
    if request.method == "POST":
        if request.POST.get('workerId') == '0':
            message = {'err':0,'message':{'department':'综合办','realName':'张三'}}
            return HttpResponse(json.dumps(message))
        else:
            message = {'err':404,'message':'0'}
            return HttpResponse(json.dumps(message))
    else:
        return redirect('/')