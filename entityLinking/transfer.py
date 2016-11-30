# -*- coding: utf-8 -*-

import sys
sys.path.append('utils')
sys.path.append('main1')
sys.path.append('main2')

import codecs
from spacyUtils import spacyUtils
from PhraseRecord import EntRecord
from spacy.en import English
import cPickle

def extractEntMention(mentag,sentence_list):
  entMen = set()
  #utilzie two pointers to solve the problem, need to improve the algorithms ability!
  lent = len(mentag)
  entMen = []
  entType= []
  p = 0;q = 0
  while(q<lent and p < lent):
    if mentag[p]==U'O':
      p = p + 1
      q = p
    else:
      if mentag[q]==U'O':
        temp = EntRecord(p,q)
        temp.setContent(sentence_list)
        entMen.append(temp)
        entType.append(mentag[p])
        #print u' '.join(sentence_list[p:q]),'\t',mentag[p]
        p=q+1
        q=p
      else:
        if mentag[q] == mentag[p]:
          q = q + 1
          if q == lent-1:
            #print u' '.join(sentence_list[p:q]),'\t',mentag[p]
            temp = EntRecord(p,q)
            temp.setContent(sentence_list)
            entMen.append(temp)
            entType.append(mentag[p])
            break
        else:
          temp = EntRecord(p,q)
          temp.setContent(sentence_list)
          entMen.append(temp)
          entType.append(mentag[p])
          #print u' '.join(sentence_list[p:q]),'\t',mentag[p]
          p = q
  return entMen,entType
      
      


if __name__=='__main__':
  if len(sys.argv) !=4:
    print 'usage: python pyfile dir_path inputfile outputfile'
    exit(1)
  
  dir_path = sys.argv[1]
  f_input = dir_path + sys.argv[2]
  f_output = dir_path +'process/' + sys.argv[3]
  
  article_No = -1
  sentence_No = -1
  nlp = English() #need to feed in unicode sentence!
  sentence_list=[]; postag=[];mentag =[]
  aNosNo2id = {};id2aNosNo={};aNosNoId = 0;ents=[];sents=[];depTrees=[];tags=[];
  with codecs.open(f_input,'r','utf-8') as file:
    for line in file:
      line = line[:-1]
      #start of the article
      if line == '-DOCSTART- -X- -X- O':
        article_No += 1
        sentence_No=-1
      else:
        if line != u'':
          item = line.split(u' ')
          sentence_list.append(item[0])
          mentag.append(item[3])
        else:
          #start an new sentence
          if len(sentence_list)!=0:
            #sentence_No = sentence_No+1
            sentence = u' '.join(sentence_list)
            sputils=spacyUtils(sentence,nlp)
            tag = sputils.getPosTags()
            depTree = sputils.getDepTree()
            #print sentence
            entMen,entType = extractEntMention(mentag,sentence_list)
            if entMen!=[]:
              sentence_No = sentence_No+1
              #print sentence_list
              aNosNo_str = str(article_No)+'_'+str(sentence_No)
              #print tags
              print aNosNo_str
              if tag is None:
                print 'tag is None'
                exit(-1)
              if aNosNo_str in aNosNo2id:
                print 'dict_aNosNo is already in the dict!'
                
              aNosNo2id[aNosNo_str] = aNosNoId
              id2aNosNo[aNosNoId] = aNosNo_str
              aNosNoId = aNosNoId + 1
              ents.append([entMen,entType])
              tags.append(tag)
              sents.append(sentence)
              depTrees.append(depTree)
              
            sentence_list=[]; postag=[];mentag =[]
    para_dict={'aNosNo2id':aNosNo2id,'id2aNosNo':id2aNosNo,'sents':sents,'tags':tags,'ents':ents,'depTrees':depTrees}
  cPickle.dump(para_dict,open(f_output,'wb'))
  
