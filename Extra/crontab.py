from apscheduler.schedulers.blocking import BlockingScheduler
import pymysql
import time
import calendar
from datetime import date, timedelta

# ==================== mysql 连接信息 ======================
mysqlHost = '115.159.85.45'
mysqlUserName = 'kl_website'
mysqlPasswd = 'CNZ7saogHL6QpuOB'
mysqlDB = 'kl_test'
# ==================== mysql 连接信息 ======================

def ranks(level):
    if int(level) == 1:
        wScore = 'totalScore'
        wRank = 'totalRank'
    elif int(level) == 2:
        wScore = 'yearScore'
        wRank = 'yearRank'
    else:
        wScore = 'monthScore'
        wRank = 'monthRank'
    db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM `kl_score` WHERE `status` != 0 ORDER BY `{wScore}`")
    db.commit()
    data = cursor.fetchall()
    i = 1
    score = 0
    j = 1
    for data_Score in data:
        workerId = data_Score[0]
        if score != data_Score[3]:
            cursor.execute(f"UPDATE `kl_score` SET `{wRank}` = {i} WHERE `workerId` = {workerId};")
            j = i
        else:
            cursor.execute(f"UPDATE `kl_score` SET `{wRank}` = {j} WHERE `workerId` = {workerId};")
        db.commit()
        score = data_Score[3]
        i += 1

# 每日0点统计截至前一天数据
def job_dailyCount():
    db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM `kl_users` WHERE `status` != 0;")
    db.commit()
    data_all = cursor.fetchall()
    yearStart = (date.today() + timedelta(days = -1)).strftime("%m%d")
    yearTotalZero = False
    monthStart = (date.today() + timedelta(days = -1)).strftime("%d")
    monthTotalZero = False
    if yearStart == "0102":
        yearTotalZero = True
    if monthStart == "01":
        monthStart = True
    day_begin = (date.today() + timedelta(days = -1)).strftime("%Y-%m-%d 00:00:00")
    day_end = (date.today() + timedelta(days = -1)).strftime("%Y-%m-%d 23:59:59")
    timeArray = time.strptime(day_begin)   
    monStartTimeStamp = int(time.mktime(timeArray))
    timeArray = time.strptime(day_end)   
    monEndTimeStamp = int(time.mktime(timeArray))

    for datas in data_all:
        workerId = datas[0]
        realName = datas[1]
        department = datas[2]
        cursor.execute(f"SELECT * FROM `kl_score_logs_submit` WHERE `workerId` = {workerId} AND `timestamp` >= {monStartTimeStamp} AND `timestamp` <= {monEndTimeStamp} AND `status` = 1;")
        db.commit()
        data = cursor.fetchall()
        fixedScore = 0
        attendScore = 0
        eventScore = 0
        eventAddScore = 0
        eventDelScore = 0
        for data_onceChange in data:
            changeType = data_onceChange[6]
            scoreChange = data_onceChange[9]
            if changeType == 1:
                fixedScore += scoreChange
            elif changeType == 2:
                attendScore += scoreChange
            elif changeType == 3:
                if scoreChange < 0:
                    eventDelScore += 1
                else:
                    eventAddScore += 1
                    eventScore += scoreChange
        
        cursor.execute(f"SELECT * FROM `kl_score` WHERE `workerId` = {workerId} AND `status` != 0;")
        db.commit()
        data = cursor.fetchone()
        if data == None:
            cursor.execute(f"INSERT INTO `kl_score` (workerId, realName, department) VALUES ('{workerId}', '{realName}', '{department}');")
            db.commit()
            totalScore = 0
            yearScore = 0
            monthScore = 0
        else:
            totalScore = data[3]
            yearScore = data[6]
            monthScore = data[9]
        totalScore = totalScore + fixedScore + attendScore + eventScore
        if yearTotalZero == True:
            yearScore = fixedScore + attendScore + eventScore
        else:
            yearScore = yearScore + fixedScore + attendScore + eventScore
        if monthTotalZero == True:
            monthScore = fixedScore + attendScore + eventScore
        else:
            monthScore = monthScore + fixedScore + attendScore + eventScore

        cursor.execute(f"UPDATE `kl_score` SET `totalScore` = {totalScore}, `yearScore` = {yearScore}, `monthScore` = {monthScore}, `fixedScore` = {fixedScore}, `attendScore` = {attendScore},  `eventScore` = {eventScore}, `eventAddScore` = {eventAddScore}, `eventDelScore` = {eventDelScore} WHERE `workerId` = {workerId};")
        db.commit()

    
    db.close()
    ranks(1)
    ranks(2)
    ranks(3)

# 每月1号0点统计截至前一月数据
def job_monthCount():
    db = pymysql.connect(mysqlHost, mysqlUserName, mysqlPasswd, mysqlDB)
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM `kl_users` WHERE `status` != 0;")
    db.commit()
    data_all = cursor.fetchall()
    day_now = time.localtime()
    yearTotalZero = False
    if day_now.tm_mon == 1:
        local_yr = day_now.tm_year - 1
        local_mon = 12
    elif day_now.tm_mon == 2:
        yearTotalZero = True
        local_yr = day_now.tm_year
        local_mon = day_now.tm_mon - 1
    else:
        local_yr = day_now.tm_year
        local_mon = day_now.tm_mon - 1
    day_begin = '%d-%02d-01 00:00:00' % (local_yr, local_mon)  # 月初肯定是1号
    wday, monthRange = calendar.monthrange(local_yr, local_mon)  # 得到本月的天数 第一返回为月第一日为星期几（0-6）, 第二返回为此月天数
    day_end = '%d-%02d-%02d 23:59:59' % (local_yr, local_mon, monthRange)
    timeArray = time.strptime(day_begin, "%Y-%m-%d %H:%M:%S")   
    monStartTimeStamp = int(time.mktime(timeArray))
    timeArray = time.strptime(day_end, "%Y-%m-%d %H:%M:%S")   
    monEndTimeStamp = int(time.mktime(timeArray))
    for datas in data_all:
        workerId = datas[0]
        realName = datas[1]
        department = datas[2]
        cursor.execute(f"SELECT * FROM `kl_score_logs_submit` WHERE `workerId` = {workerId} AND `timestamp` >= {monStartTimeStamp} AND `timestamp` <= {monEndTimeStamp} AND `status` = 1;")
        db.commit()
        data = cursor.fetchall()
        fixedScore = 0
        attendScore = 0
        eventScore = 0
        eventAddScore = 0
        eventDelScore = 0
        for data_onceChange in data:
            changeType = data_onceChange[6]
            scoreChange = data_onceChange[9]
            if changeType == 1:
                fixedScore += scoreChange
            elif changeType == 2:
                attendScore += scoreChange
            elif changeType == 3:
                if scoreChange < 0:
                    eventDelScore += 1
                else:
                    eventAddScore += 1
                    eventScore += scoreChange
        cursor.execute(f"SELECT * FROM `kl_score_cache` WHERE `workerId` = {workerId};")
        db.commit()
        data = cursor.fetchone()
        if data == None:
            cursor.execute(f"INSERT INTO `kl_score_cache` (workerId, realName, department) VALUES ('{workerId}', '{realName}', '{department}');")
            db.commit()
            totalScore = 0
            totalRankLast = 0
            yearScore = 0
            yearRankLast = 0
            monthScore = 0
        else:
            totalScore = data[3]
            totalRankLast = data[4]
            yearScore = data[6]
            yearRankLast = data[7]
        totalScore = totalScore + fixedScore + attendScore + eventScore
        if yearTotalZero == True:
            yearScore = fixedScore + attendScore + eventScore
            yearRankLast = 0
        else:
            yearScore = yearScore + fixedScore + attendScore + eventScore
        monthScore = fixedScore + attendScore + eventScore

        cursor.execute(f"UPDATE `kl_score_cache` SET `totalScore` = {totalScore}, `totalRankLast` = {totalRankLast}, `yearScore` = {yearScore}, `yearRankLast` = {yearRankLast}, `monthScore` = {monthScore}, `fixedScore` = {fixedScore}, `attendScore` = {attendScore},  `eventScore` = {eventScore}, `eventAddScore` = {eventAddScore}, `eventDelScore` = {eventDelScore} WHERE `workerId` = {workerId};")
        db.commit()

    db.close()
    ranks(1)
    ranks(2)
    ranks(3)
    

# BlockingScheduler
scheduler = BlockingScheduler()
scheduler.add_job(job_dailyCount, 'cron', day="*", hour="0", minute="0", second="0")
scheduler.add_job(job_monthCount, 'cron', month="*", day="1", hour="0", minute="0", second="0")
scheduler.start()