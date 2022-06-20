import io
import docx2txt
from ftplib import FTP_TLS
from wordcloud import WordCloud
from screeninfo import get_monitors
import numpy as np
import datetime
import os



class WordCloudHelper(object):

    user = 'speech'
    pw = 'agathocles'
    client = 'livinglab-essigfabrik.online'

    lastedited = None
    ftp = None

    local_filename = "/home/pi/Downloads/filtered.txt"

##    def readFileFromCloud(self, file):
##        oc = owncloud.Client(self.client)
##        oc.login(self.user, self.pw)
##        fc = oc.get_file_contents(file)
##        file = io.BytesIO(fc)
##        return docx2txt.process(file)

    def checkLastEdited(self, file):
        dir_list = self.ftp.nlst(os.path.dirname(file))
        if file in dir_list: 
            checktime = int(self.ftp.voidcmd("MDTM " + file).split()[1])
            if self.lastedited == None or self.lastedited < checktime:
                self.lastedited = checktime
                print("true ", self.lastedited)
                return True
            else:
                self.lastedited = checktime
                print("false",self.lastedited)

                return False
        return False
    
    def cloudRead(self, file):
        f = open(self.local_filename, "wb")
        self.ftp.retrbinary("RETR " + file, f.write)
        f.close()

        f = open(self.local_filename, "r")
        text = f.read()
        f.close()

        return text
        

    def getWordCloudImage(self, text):
        monitors = get_monitors();
        primaryMonitor = monitors[0]
        w = primaryMonitor.width;
        h = primaryMonitor.height;
        ## hier geht die wordcloud los
        #x, y = np.ogrid[:w, :h]

        #mask = (x - 150) ** 2 + (y - 150) ** 2 > 130 ** 2
        #mask = 255 * mask.astype(int)

        wc = WordCloud(width=w, height=h, background_color="white", repeat=False)
        return wc.generate(text)

    def __init__(self):
        self.ftp = FTP_TLS(self.client)
        self.ftp.login(user=self.user,passwd=self.pw)

    def __del__(self):
        self.ftp.quit()

