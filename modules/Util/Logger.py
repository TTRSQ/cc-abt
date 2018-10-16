rom datetime import datetime, timedelta, timezone

class Logger:
    JST = timezone(timedelta(hours=+9), 'JST')
    def __init__(self, path):
        self.path = path

    def log(self, str):
        f = open(self.path, "a")
        f.write(str(datetime.now(Logger.JST))+' '+str+"\n")
        f.close()