from os import remove
from django.http import HttpResponse, response
from django.shortcuts import render
from django.shortcuts import redirect

import pymysql
import re
import json
import hashlib
import rsa
import base64
import pyotp
import time
import calendar

# ==================== mysql 连接信息 ======================
mysqlHost = '115.159.85.45'
mysqlUserName = 'kl_website'
mysqlPasswd = 'CNZ7saogHL6QpuOB'
mysqlDB = 'kl_test'

# ==================== 综评量化 奖分最低标准线 ====================
limitScore = 150

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

# ==================== 自定义部分 start ====================
# 登录+权限认证
def verifyRequest(request,paths):
    try:
        loginStatus = request.session.get('is_login')
    except:
        loginStatus = False
    if loginStatus != True:
        return redirect('/logout/')
    else:
        if paths == "/" or paths == "/404/" or paths == "/500/":
            return True
        elif paths == "/score/look/" and "score_look" in request.session.get('permissions'):
            return True
        elif paths == "/score/submit/" and "score_submit" in request.session.get('permissions'):
            return True
        elif paths == "/score/verify/" and "score_verify" in request.session.get('permissions'):
            return True
        elif paths == "/score/analysis/" and "score_analysis" in request.session.get('permissions'):
            return True
        elif paths == "/score/details/" and "score_details" in request.session.get('permissions'):
            return True
        else:
            return redirect('/404/')
# ==================== 非django部分 end ====================
def index(request):
    verifyResult = verifyRequest(request,"/")
    if verifyResult != True:
        return verifyResult
    else:
        print(request.session.get('userBasicInfo'))
        request.session['requestPath'] = '/index/'
        return render(request, 'index.html')

def err404(request, exception):
    verifyResult = verifyRequest(request,"/404/")
    if verifyResult != True:
        return verifyResult
    else:
        return render(request, '404.html')

def err404_ne(request):
    verifyResult = verifyRequest(request,"/404/")
    if verifyResult != True:
        return verifyResult
    else:
        return render(request, '404.html')

def err500(request):
    verifyResult = verifyRequest(request,"/500/")
    if verifyResult != True:
        return verifyResult
    else:
        return render(request, '500.html')

def logout(request):
    if request.session.get('is_login') != True:
        return redirect('/login/')
    request.session.flush()
    return redirect('/login/')

def login(request):
    if request.session.get('is_login') != True:
        request.session.flush()
        if request.method == "POST":
            if request.META.get('HTTP_X_FORWARDED_FOR'):
                ip = request.META.get("HTTP_X_FORWARDED_FOR")
            else:
                ip = request.META.get("REMOTE_ADDR")

            if intranet_ip_check('127.0.0.1') != True:
                return render(request, 'login.html', {"err":51400002,"reason":"Insecure login","message":"* 因安全原因，请连接至公司内网之后再进行登录操作."})
            else:
                workerId = str(request.POST.get('workerId'))
                passwd = str(request.POST.get('passwd'))
                h = hashlib.sha256()
                h.update(bytes(passwd, encoding='utf-8'))
                passwd = h.hexdigest()

                db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
                cursor = db.cursor()
                cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = '{workerId}' AND `consolePasswd` = '{passwd}';")
                db.commit()
                data = cursor.fetchone()
                if data == None:
                    db.close()
                    return render(request, 'login.html', {"err":51400001,"reason":"Wrong workerId or passwd","message":"* 请正确输入工号和密码. 请注意他们都是区分大小写的."})
                else:
                    department = data[2]
                    realName = data[1]
                    wxLogo = data[6]
                    permissionGroup = int(data[3])
                    mfa_base32 = data[11]
                    cursor.execute(f"SELECT * FROM `kl_permission_groups` WHERE `gid` = '{permissionGroup}';")
                    db.commit()
                    data_groups = cursor.fetchone()
                    if data_groups[2] == 0:
                        db.close()
                        permissions = str(data_groups[3]).split(',')
                        context={}
                        context['workerId'] = workerId
                        context['realName'] = realName
                        context['department'] = department
                        context['wxLogo'] = wxLogo
                        request.session['userBasicInfo'] = context
                        request.session['permissions'] = permissions
                        request.session['is_login'] = True
                        request.session.set_expiry(7200)
                        return redirect('/')
                    elif data_groups[2] == 1 and mfa_base32 == None:
                        db.close()
                        return render(request, 'login.html', {"err":51400003,"reason":"high permission without mfa","message":"* 高权限组用户强制启用mfa，请联系管理员添加."})
                    elif data_groups[2] == 1 and mfa_base32 != None:
                        db.close()
                        with open('private.pem','r') as f:
                            privkey = rsa.PrivateKey.load_pkcs1(f.read().encode())
                        mfa_base32 = rsa.decrypt(base64.b64decode(mfa_base32), privkey).decode()
                        permissions = str(data_groups[3]).split(',')
                        context={}
                        context['workerId'] = workerId
                        context['realName'] = realName
                        context['department'] = department
                        context['wxLogo'] = wxLogo
                        request.session['userBasicInfo'] = context
                        request.session['permissions'] = permissions
                        request.session['is_login'] = False
                        request.session['mfa_base32'] = mfa_base32
                        request.session.set_expiry(7200)
                        return redirect('/mfaVerify/')
        return render(request, 'login.html')
    else:
        return redirect('/')

def mfaVerify(request):
    if request.session.get('is_login') != True and request.session.get('mfa_base32') != None:
        if request.method == "POST":
            mfaCode = request.POST.get('mfa')
            try:
                mfaCode = int(mfaCode)
            except:
                mfaCode = 000000
            
            totp = pyotp.TOTP(request.session.get('mfa_base32'))
            if totp.verify(mfaCode) == False:
                return render(request, 'mfa-verify.html', {"err":51400004,"reason":"Wrong mfa code","message":"* MFA验证码不正确,或者服务器端时间不对"})
            else:
                # return render(request, 'mfa-verify.html')
                response = redirect('/')
                # response =  redirect('index:index')
                # 设置cookies
                response.set_cookie('name','test')
                # 设置加密cookies
                response.set_signed_cookie('passsword','123456',max_age=7200,salt='18268321hs')
                request.session['is_login'] = True
                return response
        return render(request, 'mfa-verify.html')
    elif request.session.get('is_login') == True:
        return redirect('/')
    else:
        return redirect('/logout/')

def scoreLook(request):
    verifyResult = verifyRequest(request,"/score/look/")
    if verifyResult == True:
        if request.method == "POST":
            pass
        request.session['requestPath'] = '/score/look/'
        workerId = request.session.get('userBasicInfo')['workerId']
        empty_data = [None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None]
        userScoreInfo = {}
        userScoreInfo['dailyReport'] = {}
        userScoreInfo['monthReport'] = {}
        db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM `kl_score` WHERE `workerId` = '{workerId}';")
        db.commit()
        data = cursor.fetchone()
        if data == None:
            data = empty_data
        userScoreInfo['dailyReport']['totalMonthScore'] = data[9]               # 上月综评量化共得分
        userScoreInfo['dailyReport']['eventAddScore'] = data[14]                # 上月事件分共被奖次数
        userScoreInfo['dailyReport']['eventDelScore'] = data[15]                # 上月事件分共被奖次数
        userScoreInfo['dailyReport']['eventScore'] = data[13]                   # 上月共得事件分

        cursor.execute(f"SELECT * FROM `kl_score_cache` WHERE `workerId` = '{workerId}';")
        db.commit()
        data = cursor.fetchone()
        if data == None:
            data = empty_data
        userScoreInfo['monthReport']['totalMonthScore'] = data[9]               # 上月综评量化共得分
        userScoreInfo['monthReport']['totalMonthRank'] = data[10]               # 上月综评量化排名
        userScoreInfo['monthReport']['fixedScore'] = data[11]                   # 上月共得固定分
        userScoreInfo['monthReport']['attendScore'] = data[12]                  # 上月共得出勤分
        userScoreInfo['monthReport']['eventAddScore'] = data[14]                # 上月事件分共被奖次数
        userScoreInfo['monthReport']['eventDelScore'] = data[15]                # 上月事件分共被奖次数
        userScoreInfo['monthReport']['eventScore'] = data[13]                   # 上月共得事件分
        userScoreInfo['monthReport']['totalScore'] = data[3]                    # 总计综评量化得分
        userScoreInfo['monthReport']['totalRank'] = data[4]                     # 总计综评量化得分排名
        userScoreInfo['monthReport']['yearScore'] = data[6]                     # 年度综评量化得分
        userScoreInfo['monthReport']['yearRank'] = data[7]                      # 年度综评量化得分排名
        try:
            userScoreInfo['monthReport']['totalRankChange'] = data[5] - data[4] # 总计综评量化得分排名变化
            userScoreInfo['monthReport']['yearRankChange'] = data[8] - data[7]  # 年度综评量化得分排名变化
        except:
            userScoreInfo['monthReport']['totalRankChange'] = None              # 总计综评量化得分排名变化
            userScoreInfo['monthReport']['yearRankChange'] = None               # 年度综评量化得分排名变化
        request.session['userScoreInfo'] = userScoreInfo
        return render(request, './Score/look-score.html')
    else:
        return verifyResult

def scoreSubmit(request):
    verifyResult = verifyRequest(request,"/score/submit/")
    if verifyResult == True:
        if request.method == "POST":
            # 调试命令。在发送后一律返回True
            # message = '{"err":0,"reason":"ok","message":""}'
            # return HttpResponse(message)
            workerId = request.POST.get('workerId')
            scoreChange = int(request.POST.get('scoreChange'))
            changeReason = str(request.POST.get('changeReason'))
            scoreType = int(request.POST.get('scoreType'))
            operator = request.session.get('userBasicInfo')['workerId']

            db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
            cursor = db.cursor()

            try:
                cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = '{workerId}';")
                db.commit()
                data = cursor.fetchone()
                if data == None:
                    db.close()
                    message = '{"err":51400005,"reason":"Could not find that person","message":"未寻找到此员工"}'
                    return HttpResponse(message)
                else:
                    department = data[2]
                    realName = data[1]
                    rawTime = time.localtime()
                    dateTime = time.strftime("%Y-%m-%d %H:%M:%S", rawTime)
                    times = int(time.mktime(rawTime))

                    cursor.execute(f"INSERT INTO `kl_score_logs_submit` (workerId, realName, department, timestamp, dateTime, lastUpdateStamp, lastUpdate, changeType, scoreChange, reason, operator, status) VALUES ('{workerId}', '{realName}', '{department}', '{times}', '{dateTime}', '{times}','{dateTime}', {scoreType}, {scoreChange}, '{changeReason}', '{operator}', 0);")
                    db.commit()
                    db.close()
                    message = '{"err":0,"reason":"ok","message":""}'
                    return HttpResponse(message)
            except Exception as e:
                db.close()
                message = '{"err":-2,"reason":"Unknown","message":'+repr(e).replace('"','\\"')+'}'
                return HttpResponse(message)
        
        # 这一段写错了。全注释掉了。
        # day_now = time.localtime()
        # day_begin = '%d-%02d-01 00:00:00' % (day_now.tm_year, day_now.tm_mon)  # 月初肯定是1号
        # wday, monthRange = calendar.monthrange(day_now.tm_year, day_now.tm_mon)  # 得到本月的天数 第一返回为月第一日为星期几（0-6）, 第二返回为此月天数
        # day_end = '%d-%02d-%02d 23:59:59' % (day_now.tm_year, day_now.tm_mon, monthRange)
        # timeArray = time.strptime(day_begin, "%Y-%m-%d %H:%M:%S")   
        # monStartTimeStamp = int(time.mktime(timeArray))
        # timeArray = time.strptime(day_end, "%Y-%m-%d %H:%M:%S")   
        # monEndTimeStamp = int(time.mktime(timeArray))

        timeStampToday = int(time.time())
        timeStampBefore = timeStampToday - 604800
        

        operator = request.session.get('userBasicInfo')['workerId']

        db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM `kl_score_logs_submit` WHERE `operator` = '{operator}' AND `lastUpdateStamp` >= {timeStampBefore} AND `lastUpdateStamp` <= {timeStampToday};")
        db.commit()
        data = cursor.fetchall()
        db.close()
        addScore = 0
        removeScore = 0
        lst = []
        if data != None:
            for i in range(0,len(data)):
                context = {}
                context["id"] = data[i][0]
                context["realName"] = data[i][2]
                if int(data[i][8]) == 1:
                    context["type"] = '固定分'
                elif int(data[i][8]) == 2:
                    context["type"] = '出勤分'
                elif int(data[i][8]) == 3:
                    context["type"] = '事件分'
                context["change"] = data[i][9]
                if int(data[i][9]) >= 0:
                    addScore = addScore + int(data[i][9])
                else:
                    removeScore = removeScore + int(data[i][9])
                context["date"] = data[i][5]
                context["reason"] = data[i][10]
                if int(data[i][12]) == 0:
                    context["status"] = '待审核'
                elif int(data[i][12]) == 1:
                    context["status"] = '<span style="color:green">已通过</span>'
                elif int(data[i][12]) == 2:
                    context["status"] = '<span style="color:red">已驳回</span>'
                lst.append(context)
        else:
            context = {}
        # addScore = 150
        # removeScore = 10
        userScoreManagerInfo = {}
        userScoreManagerInfo['addScore'] = addScore
        userScoreManagerInfo['removeScore'] = abs(removeScore)
        userScoreManagerInfo['limitScore'] = limitScore
        if addScore == 0:
            userScoreManagerInfo['arper'] = 0.0
            userScoreManagerInfo['lastScore'] = limitScore
        else:
            userScoreManagerInfo['arper'] = float('%.2f' % (userScoreManagerInfo['removeScore'] / userScoreManagerInfo['addScore'] * 100))
            if userScoreManagerInfo['arper'] < 10.0:
                userScoreManagerInfo['lastScore'] = int(userScoreManagerInfo['addScore'] * 0.1 - userScoreManagerInfo['removeScore'])
            else:
                userScoreManagerInfo['lastScore'] = 0
        userScoreManagerInfo['needAddScore'] = userScoreManagerInfo['limitScore'] - userScoreManagerInfo['addScore']
        
        # response = render(request, './Score/submit-score.html')
        request.session['userScoreManagerInfo'] = userScoreManagerInfo
        # return response
        # datas = {"submitHistory": [{"id":1,"realName":"张三","change":10,"date":"2020-02-20","reason":"test","status":"已通过"},{"id":2,"realName":"张三","change":-100,"date":"2020-02-20","reason":"打人","status":"已驳回"},{"id":3,"realName":"张三","change":10,"date":"2020-02-20","reason":"扫地积极","status":"待审核"}]}
        datas = {}
        datas["submitHistory"] = lst
        request.session['requestPath'] = '/score/submit/'
        return render(request, './Score/submit-score.html', datas)
    else:
        return verifyResult

def scoreVerify(request):
    verifyResult = verifyRequest(request,"/score/verify/")
    if verifyResult == True:
        if request.method == "POST":
            id = int(request.POST.get('id'))
            verify = int(request.POST.get('verify'))
            verifier = request.session.get('userBasicInfo')['workerId']

            db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
            cursor = db.cursor()

            try:
                cursor.execute(f"SELECT * FROM `kl_score_logs_submit` WHERE `id` = {id};")
                db.commit()
                data = cursor.fetchone()
                if data == None:
                    db.close()
                    message = '{"err":51400006,"reason":"Fail to search target id","message":"无法查询到提交的id所对应的数据，请刷新后重试"}'
                    return HttpResponse(message)
                else:
                    status = data[11]
                    # workerId = data[1]
                    # changeType = data[8]
                    # scoreChange = data[9]
                    # changeReason = data[10]
                    if status != 0:
                        db.close()
                        message = '{"err":51400007,"reason":"Target id is not under verifying","message":"所提交的目标id已被审核完成，请刷新后重试"}'
                        return HttpResponse(message)
                    times = int(time.time())
                    dateTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

                    cursor.execute(f"UPDATE `kl_score_logs_submit` SET `status` = {verify}, `verifier` = '{verifier}', `lastUpdateStamp` = {times}, `lastUpdate` = '{dateTime}' WHERE `id` = {id};")
                    db.commit()
                    db.close()
                    # if verify == 2:
                    #     db.close()
                    # else:
                    #     cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = '{workerId}';")
                    #     db.commit()
                    #     data = cursor.fetchone()
                    #     beforeChange = int(data[4])
                    #     department = data[2]
                    #     realName = data[1]
                    #     afterChange = beforeChange + scoreChange
                    #     cursor.execute(f"INSERT INTO `kl_score_logs_confirm` (workerId, realName, department, timestamp, dateTime, changeType, beforeChange, afterChange, scoreChange, reason, submitId) VALUES ('{workerId}', '{realName}', '{department}','{times}', '{dateTime}', {changeType}, {beforeChange}, {afterChange}, {scoreChange}, '{changeReason}', {id});")
                    #     db.commit()s
                    #     db.close()
                    message = '{"err":0,"reason":"ok","message":""}'
                    return HttpResponse(message)
            except Exception as e:
                db.close()
                message = '{"err":-2,"reason":"Unknown","message":'+repr(e).replace('"','\\"')+'}'
                return HttpResponse(message)

        db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
        cursor = db.cursor()
        cursor.execute(f"SELECT * FROM `kl_score_logs_submit` WHERE `status` = 0;")
        db.commit()
        data = cursor.fetchall()
        lst = []
        if data != None:
            for i in range(0,len(data)):
                context = {}
                context["id"] = data[i][0]
                context["realName"] = data[i][2]
                context["change"] = data[i][9]
                context["date"] = data[i][5]
                context["reason"] = data[i][10]
                author_workerId = data[i][11]
                if int(data[i][8]) == 1:
                    context["type"] = '固定分'
                elif int(data[i][8]) == 2:
                    context["type"] = '出勤分'
                elif int(data[i][8]) == 3:
                    context["type"] = '事件分'
                cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = {author_workerId};")
                db.commit()
                data_user = cursor.fetchone()
                context["author"] = data_user[1]
                lst.append(context)
        else:
            context = {}
        
        datas = {}
        datas["waitingVerify"] = lst

        cursor.execute(f"SELECT * FROM `kl_score_logs_submit`;")
        db.commit()
        data = cursor.fetchall()
        lst = []
        if data != None:
            for i in range(0,len(data)):
                context = {}
                context["id"] = data[i][0]
                context["realName"] = data[i][2]
                context["change"] = data[i][9]
                context["date"] = data[i][5]
                context["reason"] = data[i][10]
                author_workerId = data[i][11]
                if int(data[i][8]) == 1:
                    context["type"] = '固定分'
                elif int(data[i][8]) == 2:
                    context["type"] = '出勤分'
                elif int(data[i][8]) == 3:
                    context["type"] = '事件分'
                cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = {author_workerId};")
                db.commit()
                data_user = cursor.fetchone()
                context["author"] = data_user[1]
                if data[i][13] != None:
                    cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = {data[i][13]};")
                    db.commit()
                    data_user = cursor.fetchone()
                    context["verifier"] = data_user[1]
                else:
                    context["verifier"] = ''
                if int(data[i][12]) == 0:
                    context["status"] = '待审核'
                elif int(data[i][12]) == 1:
                    context["status"] = '<span style="color:green">已通过</span>'
                elif int(data[i][12]) == 2:
                    context["status"] = '<span style="color:red">已驳回</span>'
                lst.append(context)
        else:
            context = {}
        db.close()
        datas["allRequestsHistory"] = lst

        request.session['requestPath'] = '/score/verify/'
        return render(request, './Score/verify-score-request.html', datas)
    else:
        return verifyResult

def scoreDetails(request):
    verifyResult = verifyRequest(request,"/score/details/")
    if verifyResult == True:
        if request.method == "POST":
            pass
        request.session['requestPath'] = '/score/details/'
        return render(request, './Score/score-details.html')
    else:
        return verifyResult

def scoreAnalysis(request):
    verifyResult = verifyRequest(request,"/score/analysis/")
    if verifyResult == True:
        if request.method == "POST":
            pass
        request.session['requestPath'] = '/score/analysis/'
        datas = {"data":[28, 48, 40, 19, 86, 27, 90]}
        request.session['datas'] = datas
        return render(request, './Score/score-analysis.html', datas)
    else:
        return verifyResult

def api_memberCheck(request):
    if request.method == "POST":
        if request.session.get('is_login'):
            workerId = request.POST.get("workerId")
            db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
            cursor = db.cursor()
            cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = '{workerId}';")
            db.commit()
            data = cursor.fetchone()
            db.close()
            if data == None:
                return HttpResponse('false')
            else:
                return HttpResponse('true')
        else:
            return HttpResponse('false')
    else:
        return redirect('/')

def api_memberInfoLoad(request):
    if request.method == "POST":
        if request.session.get('is_login'):
            workerId = request.POST.get("workerId")
            db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
            cursor = db.cursor()
            cursor.execute(f"SELECT * FROM `kl_users` WHERE `workerId` = '{workerId}';")
            db.commit()
            data = cursor.fetchone()
            db.close()
            if data == None:
                message = {'err':51400005,'message':'idk'}
                return HttpResponse(json.dumps(message))
            else:
                department = data[2]
                realName = data[1]
                message = {'err':0,'message':{'department':'%s'%department,'realName':'%s'%realName}}
                return HttpResponse(json.dumps(message))
        else:
            message = {'err':51400005,'message':'idk'}
            return HttpResponse(json.dumps(message))
    else:
        return redirect('/')
