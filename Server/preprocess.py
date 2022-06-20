"""@package docstring
Server script for speech recognition based on PyKaldi and HanTa
"""

from __future__ import print_function

from os import listdir
from os.path import splitext, isfile, join, exists
from os import replace, remove

import time

import sox

from kaldi.asr import NnetFasterRecognizer
from kaldi.decoder import FasterDecoderOptions
from kaldi.nnet3 import NnetSimpleComputationOptions
from kaldi.util.table import SequentialMatrixReader

import nltk
import codecs
from HanTa import HanoverTagger as ht


class speechRecognizer():
  """ Class for the Kaldi Speech Recognizer
  """
  def __init__(self):
    self.dataPath = "/home/speech/data/processed/"
    self.cfgDir = "/home/speech/data/online/"
    self.tmpDir = "/home/speech/data/tmp/"
    self.txtDir = "/home/speech/data/txt/"

    self.mdlPath = "/home/speech/data/model_400k/de_400k_nnet3chain_tdnn1f_2048_sp_bi/"
    self.model_path = self.mdlPath + "final.mdl"
    self.graph_path = self.mdlPath + "HCLG.fst"
    self.symbols_path = self.mdlPath + "words.txt" 

#    self.mdlPath = "/home/speech/data/model_voxforge_250/"
#    self.model_path = self.mdlPath + "model/final.mdl"
#    self.graph_path = self.mdlPath + "model/graph/HCLG.fst"
#    self.symbols_path = self.mdlPath + "model/graph/words.txt" 

    # Construct recognizer
    self.decoder_opts = FasterDecoderOptions()
    self.decoder_opts.beam = 13
    self.decoder_opts.max_active = 7000
    self.decodable_opts = NnetSimpleComputationOptions()
    self.decodable_opts.acoustic_scale = 1.0
    self.decodable_opts.frame_subsampling_factor = 3
    self.decodable_opts.frames_per_chunk = 150

    self.asr = NnetFasterRecognizer.from_files(
      self.model_path, self.graph_path, self.symbols_path,
      decoder_opts=self.decoder_opts, decodable_opts=self.decodable_opts)

    self.feats_rspec = (
	"ark:compute-mfcc-feats --allow_downsample=true --channel=0 --config="+
	self.mdlPath+"conf/mfcc_hires.conf scp:"+self.cfgDir + "wav.scp" + " ark:- |"
    )
    self.ivectors_rspec = (
	"ark:compute-mfcc-feats --allow_downsample=true --channel=0 --config="+
	self.mdlPath+"conf/mfcc_hires.conf scp:"+self.cfgDir + "wav.scp" + " ark:- |"+
	"ivector-extract-online2 --config="+self.mdlPath+
	"ivector_extractor/ivector_extractor.conf"+" ark:"+ self.cfgDir + "spk2utt ark:- ark:- |"
    )

  def decodeSpeech(self):
    """Function for decoding wave files
 
    """
    with SequentialMatrixReader(self.feats_rspec) as f, \
      SequentialMatrixReader(self.ivectors_rspec) as i, \
      open(self.tmpDir+"decode.out", "w") as o:
      for (key, feats), (_, self.ivectors) in zip(f, i):
        out = self.asr.decode((feats, self.ivectors))
        #print(key, out["text"], file=o)
        print(out["text"], file=o)

  def writeText(self):
    """Function for writing text to file without filtering
 
    """
    with codecs.open(self.tmpDir+"decode.out", "r", "utf-8") as o:
      txt = o.read()
      
      words = txt.split()
      if not isfile(self.txtDir+"text_filtered.txt"):
        with open(self.txtDir+"text_filtered.txt", "w") as t:
          t.write(' '.join(words))
      else:
        with open(self.txtDir+"text_filtered.txt", "a+") as t:
          # t.write('\n'+'\n'.join(uppers))
          t.write(' '.join(words))
      return


  def filterText(self):
    """Function for writing text to file with filtering
 
    """
    with codecs.open(self.tmpDir+"decode.out", "r", "utf-8") as o:
      txt = o.read()
      
      tagger = ht.HanoverTagger('morphmodel_ger.pgz')
      sentences = nltk.sent_tokenize(txt,language='german')

      nouns = [] 
      sentences_tok = [nltk.tokenize.word_tokenize(sent) for sent in sentences]
      for sent in sentences_tok:
        tags = tagger.tag_sent(sent) 
        nouns_from_sent = [lemma for (word,lemma,pos) in tags if pos == "NN" or pos == "NE"]
        nouns.extend(nouns_from_sent)

      if len(nouns) == 0:
        return

      nouns = [s for s in nouns if len(s)>1]
      
      if not isfile(self.txtDir+"text_filtered.txt"):
        with open(self.txtDir+"text_filtered.txt", "w") as t:
          t.write(' '.join(nouns))
      else:
        with open(self.txtDir+"text_filtered.txt", "a+") as t:
          # t.write('\n'+'\n'.join(uppers))
          t.write(' '+' '.join(nouns))

class preprocessor():
  """ Class for checking if new wav files for processing are available
  """
  def __init__(self):
    self.dataDir = "/home/speech/data/wav/"
    self.outDir = "/home/speech/data/processed/"
    self.cfgDir = "/home/speech/data/online/"
    self.backupDir = "/home/speech/data/backup"
    self.tfm = sox.Transformer()
    self.tfm.remix(num_output_channels=1)
    self.tfm.set_output_format(rate=16000)
    self.tfm.norm()

    self.sRec = speechRecognizer()

  def process(self):
    """Function for processing wav files 
 
    """
    files = [f for f in listdir(self.dataDir) if (isfile(join(self.dataDir, f))) and (splitext(f)[1] == ".wav")]

    if len(files) > 0:
      scpFile = open(join(self.cfgDir, "wav.scp"), "w")
      uttFile = open(join(self.cfgDir, "spk2utt"), "w")

      # creating utt and scp files
      idx = 1
      for file in files:
        try:
            outfilename = self.outDir + "utt" + str(idx) + ".wav"
            self.tfm.build(join(self.dataDir, file), outfilename)
            #replace(join(self.dataDir, file), join(self.backupDir, file))
            remove(join(self.dataDir, file))
            scpFile.write("utt" + str(idx) + " " + outfilename + "\n")
            uttFile.write("utt" + str(idx) + " utt" + str(idx) + "\n")
            idx += 1
        except:
            pass

      scpFile.close()
      uttFile.close()

      # decoding
      self.sRec.decodeSpeech()
      #self.sRec.writeText()
      self.sRec.filterText()

      # cleanup
      files = [f for f in listdir(self.outDir) if isfile(join(self.outDir, f))]
      for file in files:
        if exists(join(self.outDir,file)):
          remove(join(self.outDir,file))
      files = [f for f in listdir(self.cfgDir) if isfile(join(self.cfgDir, f))]
      for file in files:
        if exists(join(self.cfgDir,file)):
          remove(join(self.cfgDir,file))

### Main ###

prep = preprocessor()

while True:
    prep.process()
    time.sleep(2)
    print("test")


