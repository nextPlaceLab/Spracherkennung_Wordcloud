from WordCloudHelper import WordCloudHelper
import matplotlib.pyplot as plt

path = '/home/speech/data/txt/text_filtered.txt'


wch = WordCloudHelper()
plt.axis("off")
plt.ion()

while True:
    if wch.checkLastEdited(path):
        text = wch.cloudRead(path)
        #print(text.getvalue().decode("utf-8"))
        #print(type(text.getvalue().decode("utf-8")))
        #wc = wch.getWordCloudImage(text.getvalue().decode("utf-8"))
        wc = wch.getWordCloudImage(text)
        plt.imshow(wc, interpolation="bilinear")
        plt.show()
    plt.pause(10)
