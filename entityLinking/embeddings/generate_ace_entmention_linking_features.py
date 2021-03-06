# -*- coding: utf-8 -*-
"""
@author wujs
time: 2017/1/14
"""

import sys
sys.path.append('/home/wjs/demo/entityType/informationExtract')
sys.path.append('/home/wjs/demo/entityType/informationExtract/utils')
from description_embed_model import MyCorpus,WordVec
import Levenshtein
import cPickle
import gensim
import numpy as np
import argparse
from tqdm import tqdm
import time
import os
import codecs
import collections
from utils import getWikititle2Freebase,getWikidata2Freebase,getreverseIndex
from getctxCnnData import get_cantent_mid,get_ent_word2vec_cands,get_freebase_ent_cands,getfname2pageid,getmid2Name,getLinkedEntsFmid
from mongoUtils import mongoUtils
from NGDUtils import NGDUtils
from generate_entmention_linking_features import processDescription
from sklearn.metrics.pairwise import cosine_similarity
mongoutils= mongoUtils()
ngd = NGDUtils()
candidateEntNum=90

def get_final_ent_cands():
  all_candidate_mids=[]
  wiki_candidate_mids=[]
  freebase_candidate_mids=[]
  allentmention_numbers = 0
  
  for i in tqdm(range(len(ent_Mentions))):
    aNosNo = sentId2aNosNo[i]
    docId = aNosNo.split('_')[0]
    context_ents = docId_entstr2id[docId]
    context_ent_pageId = set()
    for key in context_ents:
      if key in title2pageId:
        context_ent_pageId.add(title2pageId[key])
    #print 'context_ent_pageId:',context_ent_pageId
    ents = ent_Mentions[i]
    
    
    for j in range(len(ents)):
      allentmention_numbers += 1
      
      enti = ents[j][2]; 
     
      enti_name = enti.lower(); entids = entstr2id[enti_name]   
      
      listentcs = []
      for entid in entids:
        listentcs += (candiate_ent[entid])
      cantent_mid1 = get_cantent_mid(mid2incomingLinks,ngd,listentcs,w2fb,wikititle2fb,mid2name)   #get wikidata&dbpedia search candidates
      
#      if enti_name in wikititle2fb:
#        wmid_id = 0.0
#        for wmid in wikititle2fb[enti_name]:
#          wmid_id += 1.0
#          #cantent_mid1[wmid] = enti_name
#          cantent_mid1[wmid] = [1/wmid_id,0,0]
  
      cantent_mid2,word2vecEnts = get_ent_word2vec_cands(mid2incomingLinks,ngd,mid2name,enti,w2fb,wikititle2fb,w2vModel,entstr2id,candiate_ent,dict(cantent_mid1)) #get word2vec coherent candidates
      
      freebaseNum = max(0,candidateEntNum - len(cantent_mid2))
      
      final_mid,freebase_cants = get_freebase_ent_cands(mid2incomingLinks,ngd,mid2name,dict(cantent_mid2),enti,context_ent_pageId,context_ents,wikititle2fb,wikititle_reverse_index,freebaseNum,word2vecEnts) 
      #print cantent_mid1,cantent_mid2,cantent_mid3
      #exit()
        
      all_candidate_mids.append(dict(final_mid))
      wiki_candidate_mids.append(dict(cantent_mid1).keys())
      freebase_candidate_mids.append(dict(freebase_cants).keys())
      
  print len(all_candidate_mids), allentmention_numbers
  return all_candidate_mids,wiki_candidate_mids,freebase_candidate_mids
  

#def get_all_candidate_mid_cocurrent():
#  allentmention_numbers = 0
#  allcandents_coents=collections.defaultdict(set)
#  k=-1
#  for i in tqdm(range(len(ent_Mentions))):
#    ents = ent_Mentions[i]
#    for j in range(len(ents)):
#      k += 1
#      allentmention_numbers += 1
#      
#      #enti = ents[j][2];enti_name = enti.lower()
#      cand_mid_dict = all_candidate_mids[k]
#      for mid in cand_mid_dict:    
#        midt = mid.replace(u'/',u'.')[1:]
#        new_mid = u'<http://rdf.freebase.com/ns/'+midt+u'>'
#        #print new_mid
#        if new_mid not in allcandents_coents:
#          allcandents_coents[new_mid] = mongoutils.get_coOccurent_ents(new_mid)
#  ##cPickle.dump(allcandents_coents,open(dir_path+'features/'+data_tag+'_ent_relcoherent.ptemp','wb'))
#  cPickle.dump(allcandents_coents,open('data/cacheFile/mid2tailmids.p','wb'))
  
def getPageLinks(midi,midj):
  if midi in mid2incomingLinks:
    ipages = mid2incomingLinks[midi]
  else:
    ipages = getLinkedEntsFmid(ngd,mid2Name,midi)
    mid2incomingLinks[midi] = ipages
  if midj in mid2incomingLinks:
    jpages = mid2incomingLinks[midj]
  else:
    jpages = getLinkedEntsFmid(ngd,mid2Name,midj)
    mid2incomingLinks[midj] = jpages
 
  return ngd.semantic_relatedness(ipages,jpages)
  

def get_candidate_fbrel_features():
  ent_mention_relCoherent_feature=[]
  doc_ents_cand_mid_dict=collections.defaultdict(list)
  k=-1
  '''
  @get entity mention in a documents!
  '''
  for i in tqdm(range(len(ent_Mentions))):
    ents = ent_Mentions[i]
    aNosNo = sentId2aNosNo[i]
    aNo = aNosNo.split('_')[0]
    for j in range(len(ents)):
      sindex = ents[j][0];eindex = ents[j][1]
      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
      #linkTag = ent_Mentions_link_tag[key]   #get entity mention linking mid!
      #if linkTag =='NIL':  #non-linking entities, we don't not need to training!
      #  continue
      #enti = ents[j][2]; 
      k+=1
      cand_mid_dict = all_candidate_mids[k]
      doc_ents_cand_mid_dict[aNo].append([key,cand_mid_dict])
  print 'start to get the fbrel features...'
  
  k=-1
  for i in tqdm(range(len(ent_Mentions))):
    ents = ent_Mentions[i]
    aNosNo = sentId2aNosNo[i]
    aNo = aNosNo.split('_')[0]
    docEntCands = doc_ents_cand_mid_dict[aNo]
         
    senti_temprelCoherent=[]
    #print i,'sent nums:',len(ents),len(docEntCands)
    
    for j in range(len(ents)):
      #print 'ent no:',j, ents[j]
      
      sindex = ents[j][0];eindex = ents[j][1]
      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
      #linkTag = ent_Mentions_link_tag[key]   #get entity mention linking mid!
      #if linkTag =='NIL':  #non-linking entities, we don't not need to training!
      #  continue
      k+=1
      s_cand_mid_dict = all_candidate_mids[k]

      '''
      @revise time:2017/6/22
      '''
      t_cand_mid_dict = {}
      
      for idocEnt in range(len(docEntCands)):
        
        items = docEntCands[idocEnt]
        key_docEnt = items[0]; o_cand_mid_dict = items[1]
        if key != key_docEnt:
          t_cand_mid_dict  = dict(o_cand_mid_dict,**t_cand_mid_dict)
      #print len(t_cand_mid_dict)
      temprelCoherent = []
      for icand in tqdm(s_cand_mid_dict):
        hasRel = 0.0
        nums= 0
        
        for jcand in t_cand_mid_dict:
          if icand != jcand:
            keymid2mid = icand+'\t'+jcand
            keymid2mid1 = jcand+'\t'+icand
            if keymid2mid in mid2midFBLink or keymid2mid1 in mid2midFBLink:
              hasRel += 1
              nums+=1
            else:
              if keymid2mid in nonmid2midFBLink or keymid2mid1 in nonmid2midFBLink:
                hasRel+=0
              else:
                retDict,flaglink = mongoutils.getHasRel_1(icand,jcand,allcandents_coents)
                #dynamic to add the cache files...
                if len(retDict)>0:
                  for retkey in retDict:
                    allcandents_coents[retkey] = retDict[retkey]
                if flaglink:
                  hasRel += 1
                  nums+=1
                  mid2midFBLink[keymid2mid]=1
                else:
                  nonmid2midFBLink[keymid2mid] = 1
        if nums==0:
          temprelCoherent.append(0)
        else:
          temprelCoherent.append(hasRel)
      #print temprelCoherent
      senti_temprelCoherent.append(temprelCoherent)
    ent_mention_relCoherent_feature.append(senti_temprelCoherent)
  cPickle.dump(ent_mention_relCoherent_feature,open(dir_path+'features/'+str(candidateEntNum)+'/'+data_tag+'_ent_fbrelcoherent.p'+str(candidateEntNum),'wb')) 
  
def get_candidate_rel_features(ngdType):
  ent_mention_relCoherent_feature=[]
  doc_ents_cand_mid_dict=collections.defaultdict(list)
  k=-1
  '''
  @get entity mention in a documents!
  '''
  for i in tqdm(range(len(ent_Mentions))):
    ents = ent_Mentions[i]
    aNosNo = sentId2aNosNo[i]
    aNo = aNosNo.split('_')[0]
    for j in range(len(ents)):
      sindex = ents[j][0];eindex = ents[j][1]
      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
      #linkTag = ent_Mentions_link_tag[key]   #get entity mention linking mid!
      #if linkTag =='NIL':  #non-linking entities, we don't not need to training!
      #  continue
      #enti = ents[j][2]; 
      k+=1
      cand_mid_dict = all_candidate_mids[k]
      doc_ents_cand_mid_dict[aNo].append([key,cand_mid_dict])
    
  k=-1
  for i in tqdm(range(len(ent_Mentions))):
    ents = ent_Mentions[i]
    aNosNo = sentId2aNosNo[i]
    aNo = aNosNo.split('_')[0]
    senti_temprelCoherent=[]
    for j in range(len(ents)):
      sindex = ents[j][0];eindex = ents[j][1]
      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
      #linkTag = ent_Mentions_link_tag[key]   #get entity mention linking mid!
      #if linkTag =='NIL':  #non-linking entities, we don't not need to training!
      #  continue
      k+=1
      s_cand_mid_dict = all_candidate_mids[k]
      
      t_cand_mid_dict = {}
      docEntCands = doc_ents_cand_mid_dict[aNo]
      for idocEnt in range(len(docEntCands)):
        items = docEntCands[idocEnt]
        key_docEnt = items[0]; o_cand_mid_dict = items[1]
        if key != key_docEnt:
          t_cand_mid_dict  = dict(o_cand_mid_dict,**t_cand_mid_dict)  
      temprelCoherent = []
      for icand in s_cand_mid_dict:
        #hasNGD = 0.0
        ngdList= []
        nums= 0
        for jcand in t_cand_mid_dict:
          pl_key = icand +"\t"+jcand
          
          if pl_key in mid2midpageLinkNums:
            #hasNGD += mid2midpageLinkNums[pl_key]
            ngdList.append(mid2midpageLinkNums[pl_key])
            
          else:  
            if icand != jcand and icand in mid2Name and jcand in mid2Name:
              temp_pl_nums = getPageLinks(icand,jcand)
              #hasNGD += temp_pl_nums
              ngdList.append(temp_pl_nums)
              mid2midpageLinkNums[pl_key] = temp_pl_nums
              nums+=1
        if nums==0:
          temprelCoherent.append(0)
        else:
          if ngdType=='max':
            temprelCoherent.append(np.max(ngdList))
          elif ngdType=='average':
            temprelCoherent.append(np.average(ngdList))
          else:
            temprelCoherent.append(np.sum(ngdList))
      #print temprelCoherent
      senti_temprelCoherent.append(temprelCoherent)
    ent_mention_relCoherent_feature.append(senti_temprelCoherent)
  cPickle.dump(ent_mention_relCoherent_feature,open(dir_path+'features/'+str(candidateEntNum)+'/'+data_tag+'_ent_relcoherent.p'+str(candidateEntNum)+ngdType,'wb'))  

def cosineSimilarity(mention,cand_mid):
  cand_ents = []
  #print 'comput entity mention...'
  if cand_mid in fid2title:
    for item in fid2title[cand_mid]:    
      twordv = np.zeros((100,))
      ent_words = processDescription(item)
      for word in ent_words:
        if word in wordsVectors:
          twordv += wordsVectors[word]
      cand_ents.append(twordv)
    
  twordv = np.zeros((100,))
  ent_words = processDescription(mention)
  for word in ent_words:
    if word in wordsVectors:
      twordv += wordsVectors[word]
  twordv = np.reshape(twordv,(1,-1))
  max_similar=0
  ret=np.zeros((100,))
  ikey = 0
  for key in cand_ents:
    tempkey = np.reshape(key,(1,-1))
    cosSim= 0
    if cand_mid in fid2title:
      cosSim = cosine_similarity(tempkey,twordv)[0][0] + Levenshtein.ratio(str(mention.lower()),str(fid2title[cand_mid][ikey].lower()))
    ikey+=1
    if cosSim > max_similar:
      max_similar = cosSim
      ret = key
  return ret

def get_candidate_ent_features():

  descrip_lent=[]
  
  ent_mention_cand_prob_feature=[]
  ent_mention_surface_wordv=[]
  
  ent_mention_index=[]
  ent_mention_link_feature=[] #shape: [line,ent_mention_num, 30(candidates number) * 100(dimension)]
  ent_mention_tag = []  #shape:[line,ent_mention_num,30]
  ent_mention_type_feature=[]   #shape:[line,ent_mention_num,30* 113(one hot type dimension)]
  rightCandHasNoDescripNums = 0
  RecallEnts = 0
  nilNums = 0
  allEnts = 0
  k  = -1
  for i in tqdm(range(len(ent_Mentions))):
  #for i in tqdm(range(100)):
    aNosNo = sentId2aNosNo[i]
    
    ents = ent_Mentions[i]
    temps_cand_prob=[]
    temps_mentwordv=[]
    
    temps =[]
    temps_type=[]
    temps_tag = []
    
    temps_ent_index=[]
    #print i,'\tentM:',len(ents)
    for j in range(len(ents)):
      allEnts +=1
      enti = ents[j][2]
      sindex = ents[j][0];eindex = ents[j][1]
      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
      
      
      linkTag = ent_Mentions_link_tag[key]   #get entity mention linking mid!
      if linkTag =='NIL':  #non-linking entities, we don't not need to training!
        nilNums += 1
        #continue
      k +=1
      enti_name = enti.lower()
     
      #ent_mention_tag_temp = np.zeros((candidateEntNum,))
      '''
      @revise time: 2017/6/21 we need to add the NIL tag, the candidateEntNum-th stands for NIL entities.
      '''
      ent_mention_tag_temp = np.zeros((candidateEntNum,))
      
#      if linkTag =='NIL':
#        ent_mention_tag_temp[-1] = 1 
                            
      tcandprob = [];tdescip = [];tcanditetype=[];tmentwordv=[]
      
      cand_mid_dict = all_candidate_mids[k]
      imidNo = -1
      candisRightFlag=False
      for mid in cand_mid_dict: 
        imidNo += 1
#        if mid not in mid2description:
#          print 'mid not in mid2description', mid
          #exit(-1)
        tmentv = cosineSimilarity(enti_name,mid)
        if mid in linkTag:
          ent_mention_tag_temp[imidNo] = 1
          candisRightFlag=True
          if mid not in mid2description:
            rightCandHasNoDescripNums+=1
            print 'right candidate entity mid not in mid2description', mid
          
        
        twordv = np.zeros((100,)) 
        ttypev = np.zeros((113,))
        if mid in mid2figer:
          for midtype in mid2figer[mid]:
            ttypev[midtype]=1
        
        if mid in mid2description:           
          line = mid2description[mid]
          descript = processDescription(line)
          descrip_lent.append(len(descript))
          #print descript
#          for i in range(min(15,len(descript))):  //abandon methods
#            word = descript[i]
#            #print 'word:',word
#            if word in descript_Words:
#              twordv += descript_Words[word]
          #@2017/1/25 position encoding(PE)
          qlent = 0
          tempWordEmbed=[]
          for idescrip in range(min(15,len(descript))):
            word = descript[idescrip]
            if word in wordsVectors:
              qlent +=1
              tempWordEmbed.append(wordsVectors[word])
              
          for idescrip in range(qlent):
            li =[]
            for jdescrip in range(100):  #100 stands for embedding dimension
              li.append(min((idescrip+1)*100/((jdescrip+1)*qlent),((jdescrip+1)*qlent)/((idescrip+1)*100)))
            twordv += tempWordEmbed[idescrip] * np.asarray(li)
        
        
        '''
        @add candidate entity type features!
        '''
        
        if len(tcanditetype)==0:
          #tcanditetype = ttypev   #may cause a lot of problem
          tcanditetype = np.array(ttypev)
        else:
          tcanditetype = np.concatenate((tcanditetype,ttypev))
         
        if len(tdescip)==0:
          tdescip = np.array(twordv)  #gurantee to copy the data, not refer to the same array
        else:
          tdescip = np.concatenate((tdescip,twordv))
        
        if len(tcandprob)==0:
          tcandprob = np.array(cand_mid_dict[mid])
         
        else:
          tcandprob = np.concatenate((tcandprob,np.array(cand_mid_dict[mid])))

        if len(tmentwordv)==0:
          tmentwordv = np.array(tmentv)
        else:
          tmentwordv = np.concatenate((tmentwordv,tmentv))
      assert np.shape(tcanditetype)[0]/113 == np.shape(tdescip)[0]/100
      assert np.shape(tcandprob)[0]/3 == np.shape(tcanditetype)[0]/113
      if candisRightFlag:
        RecallEnts+=1
      temps_mentwordv.append(tmentwordv)
      temps_cand_prob.append(tcandprob)
      temps_type.append(tcanditetype)
      temps.append(tdescip)
      temps_tag.append(ent_mention_tag_temp)
      
      temps_ent_index.append((ents[j][0],ents[j][1],key,linkTag)) 
      
    ent_mention_surface_wordv.append(temps_mentwordv)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
    ent_mention_cand_prob_feature.append(temps_cand_prob)
    
    ent_mention_type_feature.append(temps_type)
    
    ent_mention_link_feature.append(temps)
    ent_mention_tag.append(temps_tag)
    ent_mention_index.append(temps_ent_index)  
    
  print 'allEnts:', allEnts
  print 'RecallEnts:',RecallEnts
#  print len(ent_mention_link_feature),len(ent_mention_link_feature[3]),len(ent_mention_link_feature[3][0])
#  print len(ent_mention_tag),len(ent_mention_tag[3]),len(ent_mention_tag[3][0])
#  print len(ent_mention_index),len(ent_mention_index[3]),len(ent_mention_index[3][0])
#  print  max(descrip_lent),min(descrip_lent),sum(descrip_lent) / float(len(descrip_lent))
  param_dict = {'ent_mention_index':ent_mention_index,'ent_mention_link_feature':ent_mention_link_feature,'ent_mention_tag':ent_mention_tag}
  cPickle.dump(param_dict,open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_linking.p"+str(candidateEntNum),'wb'))
 # print len(ent_mention_type_feature),len(ent_mention_type_feature[3]),len(ent_mention_type_feature[3][0])
  cPickle.dump(ent_mention_type_feature,open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_linking_type.p"+str(candidateEntNum),'wb'))
  
  cPickle.dump(ent_mention_cand_prob_feature,open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_linking_candprob.p"+str(candidateEntNum),'wb'))
  cPickle.dump(ent_mention_surface_wordv,open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_mentwordv.p"+str(candidateEntNum),'wb'))
  
def RecallsThread():
  print 'candidateEntNum:',candidateEntNum
  #{'all_candidate_mids':all_candidate_mids,'wiki_candidate_mids':wiki_candidate_mids,'freebase_candidate_mids':freebase_candidate_mids}
  NERentCands = data_param['all_candidate_mids']
  wiki_candidate_mids = data_param['wiki_candidate_mids']
  freebase_candidate_mids = data_param['freebase_candidate_mids']
  all_candidate_mids=[]
  ambiguous=[];refine_ambiguous=[];ambiguous_without_refine=[]
  passEnts = 0;passEntsCandidateIsNULL= 0
  rightEnts =0;refineEnts =0;rightEnts_inall = 0
  wrongEnts=0
  rightWiki = 0;rightFb=0;rightWord2vec = 0;rightWord2vec1=0
  allEnts = 0.0; all_linkable_ents = 0.0
  k  = -1
  for i in range(len(ent_Mentions)):
  #for i in tqdm(range(100)):
    aNosNo = sentId2aNosNo[i]
    
    ents = ent_Mentions[i]
    
    #print i,'\tentM:',len(ents)
    for j in range(len(ents)):
      sindex = ents[j][0];eindex = ents[j][1]
      
      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
      
      linkTag = ent_Mentions_link_tag[key]  #get entity mention linking mid!
     
      k += 1  
  
      cand_mid_dict = dict(NERentCands[k])
      
      candMids = NERentCands[k].keys()
      wikicands = wiki_candidate_mids[k]
      FBcands = freebase_candidate_mids[k]
      
      
      allEnts +=1
      if linkTag=='NIL':  #we also need to regard the entities.
        passEnts += 1
        if len(NERentCands[k]):
          #rightEnts_inall += 1 #for NIL, if their candidates is wrong, we just give the NIL.
          passEntsCandidateIsNULL += 1
      else:
        all_linkable_ents += 1
        #continue
     
      ambiguous_without_refine.append(len(set(cand_mid_dict.keys())))
      rel_cand_mid_dict={}
      oreder_cand_mid_dict={}
      linkTag = linkTag[0]
      if linkTag in candMids:
        rightEnts_inall += 1
      #print linkTag
      for key in NERentCands[k]:
        if NERentCands[k][key][2]==0 and NERentCands[k][key][1]==0 and key not in wikicands:
          candMids.remove(key)
          FBcands.remove(key)
          cand_mid_dict.pop(key)
      refine_ambiguous.append(len(candMids))
      if linkTag in candMids:
        refineEnts += 1
      for key in candMids:
        if key in wikicands:
          rel_cand_mid_dict[key] = NERentCands[k][key]
        else:
          oreder_cand_mid_dict[key] = NERentCands[k][key]
          
      sorted_cand_mid_dict= sorted(oreder_cand_mid_dict.items(), key=lambda oreder_cand_mid_dict:oreder_cand_mid_dict[1][2])[0:max(0,candidateEntNum-len(rel_cand_mid_dict))]
            
      sorted_cand_mid_dict = dict(sorted_cand_mid_dict)
      
      dictMerged2=dict(rel_cand_mid_dict, **sorted_cand_mid_dict)
      all_candidate_mids.append(dictMerged2)
      candisRightFlag=False
      for mid in dictMerged2:
        if mid in wikititle2fb:
          relmid = wikititle2fb[mid]
          #print relmid
        else:
          relmid = mid
          
        if relmid in linkTag:
          candisRightFlag=True
          
      ambiguous.append(len(dictMerged2))
      if linkTag !='NIL':
        if candisRightFlag:
          rightEnts +=1
          if linkTag in wikicands:
            rightWiki += 1
          if linkTag in FBcands:
            rightFb+= 1
          if linkTag not in FBcands and linkTag not in wikicands:
            rightWord2vec1 += 1
          if NERentCands[k][linkTag][1] !=0:
            rightWord2vec += 1
        else:
          wrongEnts += 1
          print ents[j][2],'\t',linkTag
          print cand_mid_dict
          print '--------------'
  
  cPickle.dump(all_candidate_mids,open(dir_path+'features/'+str(candidateEntNum)+'/'+data_tag+'_ent_cand_mid_new.p'+str(candidateEntNum),'wb'))
  print '-------------------------------'
  print 'candidateEntNum:',candidateEntNum
  print 'data tag:',data_tag
  print 'allEnts:', allEnts
  print 'NIL:',passEnts,' NIL has no candidates:', passEntsCandidateIsNULL
  print 'right Ents:',rightEnts,' wrongEnts:',wrongEnts, 'all linkable entities:', all_linkable_ents
  print 'linkable recall:', rightEnts_inall/all_linkable_ents
  print 'refined linkable recall:',rightEnts*1.0/all_linkable_ents
  print 'all recall:',  (passEntsCandidateIsNULL + rightEnts_inall)/ allEnts
  print 'refined all recall:',(passEntsCandidateIsNULL + rightEnts) /allEnts
  print '-----------------------------------------------'
  print 'refine recall:', refineEnts*1.0/(rightEnts+wrongEnts-passEnts)
  print 'fixed c precision:', rightEnts*1.0/(rightEnts+wrongEnts)
  print 'rightWiki:',rightWiki, rightWiki*1.0/(rightEnts+wrongEnts)
  print 'rightFB:',rightFb, rightFb*1.0/(rightEnts+wrongEnts)
  print 'rightWord2vec:',rightWord2vec, rightWord2vec*1.0/(rightEnts+wrongEnts)
  print 'rightWord2vec1:',rightWord2vec1, rightWord2vec1*1.0/(rightEnts+wrongEnts)
  print 'fixed candidate ambiguous:',np.average(ambiguous)         
  print 'nurefined ambiguous:',np.average(ambiguous_without_refine)
  print 'refined ambiguous:',np.average(refine_ambiguous)
def Recalls():
  #{'all_candidate_mids':all_candidate_mids,'wiki_candidate_mids':wiki_candidate_mids,'freebase_candidate_mids':freebase_candidate_mids}
  NERentCands = data_param['all_candidate_mids']
  wiki_candidate_mids = data_param['wiki_candidate_mids']
  freebase_candidate_mids = data_param['freebase_candidate_mids']
  
  ambiguous=[]
  
  passEnts = 0
  rightEnts =0
  wrongEnts=0
  rightWiki = 0
  rightFb=0
  rightWord2vec = 0
  rightWord2vec1=0
  
  allEnts = 0
  k  = -1
  for i in range(len(ent_Mentions)):
  #for i in tqdm(range(100)):
    aNosNo = sentId2aNosNo[i]
    
    ents = ent_Mentions[i]
    
    #print i,'\tentM:',len(ents)
    for j in range(len(ents)):
      sindex = ents[j][0];eindex = ents[j][1]
      
      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
      
      linkTag = ent_Mentions_link_tag[key]  #get entity mention linking mid!
     
      k += 1  
  
      cand_mid_dict = NERentCands[k]
      
      candMids = NERentCands[k].keys()
      wikicands = wiki_candidate_mids[k]
      FBcands = freebase_candidate_mids[k]
      
      allEnts +=1
      if linkTag=='NIL':
        passEnts += 1
        continue
      
      linkTag = linkTag[0]
      #print linkTag
      for key in NERentCands[k]:
        if NERentCands[k][key][2]==0 and NERentCands[k][key][1]==0 and key not in wikicands:
          candMids.remove(key)
          FBcands.remove(key)
          cand_mid_dict.pop(key)

      candisRightFlag=False
      for mid in candMids:
        if mid in wikititle2fb:
          relmid = wikititle2fb[mid]
          #print relmid
        else:
          relmid = mid
          
        if relmid in linkTag:
          candisRightFlag=True
          
      ambiguous.append(len(candMids)) 
      if candisRightFlag:
        rightEnts +=1
        if linkTag in wikicands:
          rightWiki += 1
        if linkTag in FBcands:
          rightFb+= 1
        if linkTag not in FBcands and linkTag not in wikicands:
          rightWord2vec1 += 1
        if NERentCands[k][linkTag][1] !=0:
          rightWord2vec += 1
      else:
        wrongEnts += 1
        print ents[j][2]
        print linkTag
        print cand_mid_dict[k]
        print '--------------'
  print '--------------------------'
  print 'data tag:',data_tag
  print 'allEnts:', allEnts
  print 'NIL:',passEnts
  print 'right Ents:',rightEnts
  print 'wrongEnts:',wrongEnts
  print 'precision:', rightEnts*1.0/(rightEnts+wrongEnts)
  print 'rightWiki:',rightWiki, rightWiki*1.0/(rightEnts+wrongEnts)
  print 'rightFB:',rightFb, rightFb*1.0/(rightEnts+wrongEnts)
  print 'rightWord2vec:',rightWord2vec, rightWord2vec*1.0/(rightEnts+wrongEnts)
  print 'rightWord2vec1:',rightWord2vec1, rightWord2vec1*1.0/(rightEnts+wrongEnts)
  print 'ambiguous:',np.average(ambiguous)
      
      
parser = argparse.ArgumentParser()
parser.add_argument('--data_tag', type=str, help='which data file(ace or msnbc)', required=True)
parser.add_argument('--dir_path', type=str, help='data directory path(data/ace or data/msnbc) ', required=True)
  
data_args = parser.parse_args()
t=[]
data_tag = data_args.data_tag
dir_path = data_args.dir_path

start_time = time.time()
ent_Mentions = cPickle.load(open(dir_path+'features/ent_mention_index.p'))

ent_Mentions_link_tag = cPickle.load(open(dir_path+data_tag+'_entMentsTags.p')) #aNosNo \t start_index \t end_index
sentid = 0
sentId2aNosNo = {}
with codecs.open(dir_path+'sentid2aNosNoid.txt','r','utf-8') as file:
  for line in file:
    line = line.strip()
    sentId2aNosNo[sentid] = line
    sentid += 1
    
print 'load ent_Mentions cost time:',time.time()-start_time


'''
Step1: get the complete candidates entities..
'''
#f_input = dir_path+"features/"+data_tag+"_candEnts.p"
#f_output = dir_path+"features/"+data_tag+"_ent_cand_mid.p"
#
#data = cPickle.load(open(f_input,'r'))
#entstr2id_org = data['entstr2id']
#id2entstr_org = {value:key for key,value in entstr2id_org.items()}
#entstr2id= collections.defaultdict(set)
#for key,value in entstr2id_org.items():
#  entstr2id[key.lower()].add(value)
#print 'entstr2id',len(entstr2id)
#print 'entstr2id_org:',len(entstr2id_org)
#'''
#hasEntstr=0
#nilents = 0
#allents = 0
#allEntMents = 0                                   
#for i in range(len(ent_Mentions)):
#  #for i in tqdm(range(100)):
#    aNosNo = sentId2aNosNo[i]
#    ents = ent_Mentions[i]
#    
#    #print i,'\tentM:',len(ents)
#    for j in range(len(ents)):
#      enti = ents[j][2]
#      if enti.lower() in entstr2id:
#        hasEntstr += 1
#      else:
#        print 'enti:',enti
#      allEntMents +=1
#      sindex = ents[j][0];eindex = ents[j][1]
#      key = aNosNo+'\t'+str(sindex)+'\t'+str(eindex)
#      
#      linkTag = ent_Mentions_link_tag[key]   #get entity mention linking mid!
#      if linkTag=='NIL':
#        nilents+=1
#        print enti, linkTag
#print 'all NIL Ents:',nilents
#print 'all ents:',len(ent_Mentions_link_tag)
#print hasEntstr
#print 'allEntMents:',allEntMents
#exit(0)
#'''
#wikititle2fb = getWikititle2Freebase()
#docId_entstr2id= collections.defaultdict(dict)
#'''
#@2017/3/1, we revise the entstr2id  to docid_entstr2id
#@2017/6/15, revise a enti_name.lower()
#'''
#for i in tqdm(range(len(ent_Mentions))):
#  aNosNo = sentId2aNosNo[i]
#  docId = aNosNo.split('_')[0]
#  ents = ent_Mentions[i]
#  
#  for j in range(len(ents)):
#    enti = ents[j]
#    #print enti
#    enti_name = enti[2]
#    value = entstr2id_org.get(enti_name)
#    if enti_name.lower() not in docId_entstr2id[docId]:
#      
#      docId_entstr2id[docId][enti_name.lower()]= {value}
#    else:
#      docId_entstr2id[docId][enti_name.lower()].add(value)
#
#
#candiate_ent = data['candiate_ent'] #;candiate_coCurrEnts = data['candiate_coCurrEnts']
#mid2name = getmid2Name()
#title2pageId = getfname2pageid()
#w2fb = getWikidata2Freebase()
#print 'start to load wikititle_reverse_index...'
#wikititle_reverse_index  = getreverseIndex()
#
##print wikititle_reverse_index
##print wikititle_reverse_index['calif.']
#print 'start to solve problems...'
#w2vModel = gensim.models.Word2Vec.load_word2vec_format('/home/wjs/demo/entityType/informationExtract/data/GoogleNews-vectors-negative300.bin',binary=True)
#
#wikititle_reverse_index={}
#w2vModel={}
#mid2incomingLinks={}
#if os.path.isfile('data/cacheFile/mid2incomingLinks.p'):
#  print 'start to load mid2incomingLinks ... '
#  mid2incomingLinks=cPickle.load(open('data/cacheFile/mid2incomingLinks.p','rb'))
#
#all_candidate_mids,wiki_candidate_mids,freebase_candidate_mids = get_final_ent_cands()
#data_param={'all_candidate_mids':all_candidate_mids,'wiki_candidate_mids':wiki_candidate_mids,'freebase_candidate_mids':freebase_candidate_mids}
#cPickle.dump(data_param,open(f_output,'wb'))
#
#'''
#@step1-2: get thread candidate entities!
#@we need to add features for NIL taggingd...
wikititle2fb = getWikititle2Freebase()
data_param = cPickle.load(open(dir_path+"features/"+data_tag+"_ent_cand_mid.p"))
#Recalls()
RecallsThread()

'''
Step2: @generate all candidate mid cocurrent features!
'''
#if not os.path.isfile('data/cacheFile/mid2tailmids.p'):
#  all_candidate_mids =  cPickle.load(open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_cand_mid_new.p"+str(candidateEntNum)))
##  print all_candidate_mids
#  get_all_candidate_mid_cocurrent()

'''
Step3: generate NGD cocurrent features...
'''
#mid2incomingLinks={}
##if os.path.isfile('data/cacheFile/mid2incomingLinks.p'):
##  print 'start to load mid2incomingLinks ... '
##  mid2incomingLinks=cPickle.load(open('data/cacheFile/mid2incomingLinks.p','rb'))
#    
#mid2midpageLinkNums = {}
##if os.path.isfile('data/cacheFile/mid2midpageLink.p'):
##  print 'start to load mid2midpageLink ... '
##  mid2midpageLinkNums=cPickle.load(open('data/cacheFile/mid2midpageLink.p','rb'))
#
#  
#mid2Name = getmid2Name()
#all_candidate_mids = cPickle.load(open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_cand_mid_new.p"+str(candidateEntNum)))
#print len(all_candidate_mids)
###allcandents_coents = cPickle.load(open(dir_path+'features/'+data_tag+'_ent_relcoherent.ptemp','rb'))
#ngdType= 'average'
#get_candidate_rel_features(ngdType)
##cPickle.dump(mid2incomingLinks,open('data/cacheFile/mid2incomingLinks.p','wb'))
##cPickle.dump(mid2midpageLinkNums,open('data/cacheFile/mid2midpageLink.p','wb'))

'''
step4: get fb rel coherent
'''
#allcandents_coents = cPickle.load(open('data/cacheFile/mid2tailmids.p','rb'))
#nonmid2midFBLink={}
#mid2midFBLink={}
#if os.path.isfile('data/cacheFile/mid2midFBLink.p'):
#  print 'start to load mid2midFBLink ... '
#  mid2midFBLink=cPickle.load(open('data/cacheFile/mid2midFBLink.p','rb'))
#  nonmid2midFBLink=cPickle.load(open('data/cacheFile/nonmid2midFBLink.p','rb'))
#  
# 
#all_candidate_mids = cPickle.load(open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_cand_mid_new.p"+str(candidateEntNum)))
#
#get_candidate_fbrel_features()
##cPickle.dump(mid2midFBLink,open('data/cacheFile/mid2midFBLink.p','wb'))
##cPickle.dump(nonmid2midFBLink,open('data/cacheFile/nonmid2midFBLink.p','wb'))
##cPickle.dump(allcandents_coents,open('data/cacheFile/mid2tailmids.p','wb'))

'''
Step5 other features...
'''
'''
#@time: 2017/2/8
#@function: load re-rank type
##'''
all_candidate_mids = cPickle.load(open(dir_path+"features/"+str(candidateEntNum)+'/'+data_tag+"_ent_cand_mid_new.p"+str(candidateEntNum)))
print 'load fid2title...'
fid2title = collections.defaultdict(list)
fid2vec = collections.defaultdict(list)
wtitle2fid = getWikititle2Freebase() #cPickle.load(open('/home/wjs/demo/entityType/informationExtract/data/wtitle2fbid.p','rb'))
for key in tqdm(wtitle2fid):
  for item in wtitle2fid[key]:
    fid2title[item].append(key)

'''
@time: 2016/12/23
@function: load re-rank featureÂ£Âºentity type
'''
stime = time.time()
descript_Words = cPickle.load(open('/home/wjs/demo/entityType/informationExtract/data/wordvec_model_100.p', 'rb'))
print 'load wordvec_model_100 cost time: ', time.time()-stime

'''
compute entity vector===>adpot the type vector is more feasible!
'''
wordsVectors = descript_Words.wvec_model
        
stime = time.time()
mid2figer = cPickle.load(open('/home/wjs/demo/entityType/informationExtract/data/mid2figer.p','rb'))
print 'load mid2figer cost time:',time.time()-stime


stime = time.time()
mid2description={}  #nearly 2.3G
with codecs.open('/home/wjs/demo/entityType/informationExtract/data/mid2description.txt','r','utf-8') as file:
  for line in tqdm(file):
    items = line.strip().split('\t')
    if len(items) >=2:
      mid2description[items[0]] =items[1]
print 'load mid2descriptioon cost time: ', time.time()-stime

get_candidate_ent_features()
