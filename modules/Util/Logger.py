class Logger:
    def __init__(self, path):
        self.path = path

    def log(self, str):
        f = open(self.path, "a")
        f.write(str+"\n")
        f.close()