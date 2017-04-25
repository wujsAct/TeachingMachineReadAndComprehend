# -*- coding: utf-8 -*-
'''
@editor: wujs
function: we add entity linking module
revise: 2017/1/8
'''

import tensorflow as tf
import time
from model import ctxSum
from entityRecog import nameEntityRecognition,pp,flags,args #get seqLSTM features
from sklearn.metrics import f1_score
from utils import nelInputUtils as inputUtils
from utils import getLinkingFeature
import numpy  as np
import cPickle
def getData(dataTag):
  dataUtils = inputUtils(args.rawword_dim,dataTag)
  data_input = dataUtils.emb; 
  data_entliking= dataUtils.ent_linking;data_ent_mention_index = data_entliking['ent_mention_index'];
  data_ent_mention_link_feature=data_entliking['ent_mention_link_feature'];data_ent_mention_tag = data_entliking['ent_mention_tag']; 
  data_ent_relcoherent = dataUtils.ent_relcoherent
  data_ent_linking_type = dataUtils.ent_linking_type; 
  data_ent_linking_candprob = dataUtils.ent_linking_candprob
  #data_ent_surfacewordv_feature = dataUtils.ent_surfacewordv_feature
  
  data_shape = np.shape(data_input)
  if dataTag in ['train','testa','testb']:
    data_out = np.argmax(dataUtils.tag,2) 
  else:
    data_out = np.zeros([data_shape[0],data_shape[1],args.class_size],dtype=np.float32)  
    data_out = np.argmax(data_out,2)
  
  return data_input, data_out, data_ent_mention_index, data_ent_mention_link_feature, data_ent_mention_tag, data_ent_relcoherent,data_ent_linking_type,data_ent_linking_candprob#,data_ent_surfacewordv_feature


def getDataTestSets():
  aceFeatureList = getData("ace")
  aceNums = np.shape(aceFeatureList[1])[0]; aceTrainRange= int(aceNums*0.7)
  print aceNums
  msnbcFeatureList = getData("msnbc")
  msnbcNums = np.shape(msnbcFeatureList[1])[0]; msnbcTrainRange= int(msnbcNums*0.7)
  print msnbcNums
  aceTestRet=[]
  msnbcTestRet=[]
  TrainRet=[]
  #for i in range(len(aceFeatureList)):
    #aceTestRet.append(aceFeatureList[i][aceTrainRange:aceNums])
    #msnbcTestRet.append(msnbcFeatureList[i][msnbcTrainRange:msnbcNums])
    #TrainRet.append(np.concatenate((aceFeatureList[i][0:aceTrainRange],msnbcFeatureList[i][0:msnbcTrainRange])))
    #TrainRet.append(aceFeatureList[i])
  return aceFeatureList,msnbcFeatureList,msnbcFeatureList
  
  
'''
@convert ace and msnbc split into train and test()
'''
def getDataSets():
  
  aceFeatureList = getData("ace")
  aceNums = np.shape(aceFeatureList[1])[0]; aceTrainRange= int(aceNums*0.7)
  print aceNums
  msnbcFeatureList = getData("msnbc")
  msnbcNums = np.shape(msnbcFeatureList[1])[0]; msnbcTrainRange= int(msnbcNums*0.7)
  print msnbcNums
  trainFeatureList = getData("train")
  print len(trainFeatureList[1])
#  trainRet = []
#  aceTestRet=[]
#  msnbcTestRet=[]
#  for i in range(len(trainFeatureList)):
#    trainRet.append(np.concatenate((trainFeatureList[i],aceFeatureList[i][0:aceTrainRange],msnbcFeatureList[i][0:msnbcTrainRange])))
#    aceTestRet.append(aceFeatureList[i][aceTrainRange:aceNums])
#    msnbcTestRet.append(msnbcFeatureList[i][msnbcTrainRange:msnbcNums])
  return trainFeatureList,aceFeatureList,msnbcFeatureList 
  #return trainRet,aceTestRet,msnbcTestRet

def main(_):
  pp.pprint(flags.FLAGS.__flags)

  print 'start to load data...'
  start_time = time.time()
  
  testa_input, testa_out, testa_ent_mention_index, testa_ent_mention_link_feature, \
  testa_ent_mention_tag, testa_ent_relcoherent,testa_ent_linking_type,\
  testa_ent_linking_candprob =  getData("testa") 
  
  train_input, train_out, train_ent_mention_index, train_ent_mention_link_feature, \
  train_ent_mention_tag, train_ent_relcoherent,train_ent_linking_type,\
  train_ent_linking_candprob = getData("train") 
  
  testb_input, testb_out, testb_ent_mention_index, testb_ent_mention_link_feature, \
  testb_ent_mention_tag, testb_ent_relcoherent,testb_ent_linking_type,\
  testb_ent_linking_candprob =  getData("testb")
  print 'cost:', time.time()-start_time,' to load data'
  
  #function: lstm_output from seqLSTM
  config = tf.ConfigProto(allow_soft_placement=True,intra_op_parallelism_threads=4,inter_op_parallelism_threads=4)
  config.gpu_options.allow_growth=True
  sess_ner = tf.InteractiveSession(config=config)
  
  nerInstance = nameEntityRecognition(sess_ner,'data/aida/','aida')

  lstm_output_testa = nerInstance.getEntityRecognition(testa_input,testa_out)
  lstm_output_testb = nerInstance.getEntityRecognition(testb_input,testb_out)
  lstm_output_train = nerInstance.getEntityRecognition(train_input,train_out)
  sess_ner.close()
  
  
  
  print 'start to initialize parameters'
  start_time = time.time()
  config = tf.ConfigProto(allow_soft_placement=True,intra_op_parallelism_threads=4,inter_op_parallelism_threads=4)
  config.gpu_options.allow_growth=True
  with tf.Session(config=config) as sess:
    modelNEL = ctxSum(args)  #build named entity linking models
    optimizer = tf.train.AdamOptimizer(0.01)
    tvars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,scope='ctxSum')
    print 'tvars_linking:',tvars
    #
    #@l2 loss may help to train the model to avoid overfitting
    #
    #lossL2 = tf.add_n([ tf.nn.l2_loss(v) for v in tvars if 'bias' not in v.name]) * 0.01
    loss_linking = modelNEL.linking_loss # + lossL2
    grads,_ = tf.clip_by_global_norm(tf.gradients(loss_linking,tvars),10)
    train_op_linking = optimizer.apply_gradients(zip(grads,tvars))
    sess.run(tf.global_variables_initializer())
    
    if modelNEL.load(sess,args.restore,"aida"):
      print "[*] ctxSum is loaded..."
    else:
      print "[*] There is no checkpoint for aida"

    #@train named entity linking models
    #avoid overfitting
    maximum_linking=0
    id_epoch=0
    for e in range(100):
      for ptr in xrange(0,len(train_input),args.batch_size):
        ent_mention_linking_tag_list,candidate_ent_linking_feature,candidate_ent_type_feature,candidate_ent_prob_feature,\
        ent_mention_lstm_feature,candidate_ent_relcoherent_feature = \
           getLinkingFeature(args,lstm_output_testa,testa_ent_mention_index,testa_ent_mention_tag,
                             testa_ent_relcoherent,testa_ent_mention_link_feature,testa_ent_linking_type,
                             testa_ent_linking_candprob,0,flag='testa')
        loss2,accuracy,pred = sess.run([loss_linking,modelNEL.accuracy,modelNEL.prediction],
                                 {modelNEL.ent_mention_linking_tag:ent_mention_linking_tag_list,
                                  modelNEL.candidate_ent_coherent_feature:candidate_ent_relcoherent_feature,
                                  modelNEL.candidate_ent_linking_feature:candidate_ent_linking_feature,
                                  modelNEL.candidate_ent_type_feature:candidate_ent_type_feature,
                                  modelNEL.candidate_ent_prob_feature:candidate_ent_prob_feature,
                                  modelNEL.ent_mention_lstm_feature:ent_mention_lstm_feature,
                                  #modelNEL.ent_surfacewordv_feature:ent_surfacewordv_feature,
                                  modelNEL.keep_prob:1
                                 })
        if accuracy > maximum_linking:
          maximum_linking = accuracy
          f1_micro,f1_macro = f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='micro'),\
                                        f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='macro')
          print '-------------------------------'
          print 'Epoch: %d------------' %(e)
          print 'testa loss:',loss2,' accuracy:',accuracy,' f1_micro:',f1_micro,' f1_macro:',f1_macro
          cPickle.dump(pred,open('data/aida/testa_entityLinkingResult.p','wb'))
#          if maximum_linking > 0.7:
#            modelNEL.save(sess,args.restore,"aida")
          
          ent_mention_linking_tag_list,candidate_ent_linking_feature,candidate_ent_type_feature,candidate_ent_prob_feature,\
        ent_mention_lstm_feature,candidate_ent_relcoherent_feature = \
          getLinkingFeature(args,lstm_output_testb,testb_ent_mention_index,testb_ent_mention_tag,
                             testb_ent_relcoherent,testb_ent_mention_link_feature,testb_ent_linking_type,
                             testb_ent_linking_candprob,0,flag='testb')
          loss2,accuracy,pred = sess.run([loss_linking,modelNEL.accuracy,modelNEL.prediction],
                               {modelNEL.ent_mention_linking_tag:ent_mention_linking_tag_list,
                                modelNEL.candidate_ent_coherent_feature:candidate_ent_relcoherent_feature,
                                modelNEL.candidate_ent_linking_feature:candidate_ent_linking_feature,
                                modelNEL.candidate_ent_type_feature:candidate_ent_type_feature,
                                modelNEL.candidate_ent_prob_feature:candidate_ent_prob_feature,
                                modelNEL.ent_mention_lstm_feature:ent_mention_lstm_feature,
                                #modelNEL.ent_surfacewordv_feature:ent_surfacewordv_feature,
                                modelNEL.keep_prob:1
                               })
        
          f1_micro,f1_macro=f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='micro'),f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='macro')
          print 'testb loss:',loss2,' accuracy:',accuracy,' f1_micro:',f1_micro,' f1_macro:',f1_macro
          #cPickle.dump(pred,open('data/aida/testb_entityLinkingResult.p','wb'))
          
          
        lstm_output = lstm_output_train[ptr:min(ptr+args.batch_size,len(train_input))];

        ent_mention_linking_tag_list,candidate_ent_linking_feature,candidate_ent_type_feature,candidate_ent_prob_feature,\
         ent_mention_lstm_feature,candidate_ent_relcoherent_feature= \
                                                getLinkingFeature(args,lstm_output,train_ent_mention_index,train_ent_mention_tag,
                                                train_ent_relcoherent,train_ent_mention_link_feature,train_ent_linking_type,
                                                train_ent_linking_candprob,ptr,flag='train')
        if len(ent_mention_lstm_feature)==0:
          continue
        _,loss2,accuracy,pred = sess.run([train_op_linking,loss_linking,modelNEL.accuracy,modelNEL.prediction],
                               {modelNEL.ent_mention_linking_tag:ent_mention_linking_tag_list,
                                modelNEL.candidate_ent_coherent_feature:candidate_ent_relcoherent_feature,
                                modelNEL.candidate_ent_linking_feature:candidate_ent_linking_feature,
                                modelNEL.candidate_ent_type_feature:candidate_ent_type_feature,
                                modelNEL.candidate_ent_prob_feature:candidate_ent_prob_feature,
                                modelNEL.ent_mention_lstm_feature:ent_mention_lstm_feature, 
                                #modelNEL.ent_surfacewordv_feature:ent_surfacewordv_feature,
                                modelNEL.keep_prob:1
                               })
        f1_micro,f1_macro=f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='micro'),f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='macro')
        id_epoch += 1
        
        if id_epoch %100==0:
          print 'train loss:',loss2,' accuracy:',accuracy,' f1_micro:',f1_micro,' f1_macro:',f1_macro       

if __name__=="__main__":
  tf.app.run()