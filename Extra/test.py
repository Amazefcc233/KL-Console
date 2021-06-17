from datetime import date, timedelta
import time

print(time.localtime())
print(time.time())
yesterday = (date.today() + timedelta(days = -1)).strftime("%m%d")
print(yesterday == "0614")