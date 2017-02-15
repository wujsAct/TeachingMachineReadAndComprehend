# -*- coding: utf-8 -*-
'''
@editor: wujs
function: we add entity linking module
revise: 2017/1/8
'''
import sys
sys.path.append('utils')

import tensorflow as tf
import time
from model import ctxSum
from entityRecog import nameEntityRecognition,pp,flags,args #get seqLSTM features
from sklearn.metrics import f1_score
from utils import nelInputUtils as inputUtils
from utils import getLinkingFeature
from TFRecordUtils import nel_read_TFRecord
import numpy  as np

def main(_):
  pp.pprint(flags.FLAGS.__flags)

  print 'start to load data...'
  start_time = time.time()
  trainUtils = inputUtils(args.rawword_dim,"train")
  train_TFfileName = trainUtils.TFfileName; train_nelShapeFile = trainUtils.nelShapeFile; 
    
  testaUtils = inputUtils(args.rawword_dim,"testa")
  testa_input = testaUtils.emb; testa_out = testaUtils.tag; testa_entliking= testaUtils.ent_linking;
  testa_ent_mention_index = testa_entliking['ent_mention_index'];
  testa_ent_mention_link_feature=testa_entliking['ent_mention_link_feature'];
  testa_ent_mention_tag = testa_entliking['ent_mention_tag']; testa_ent_relcoherent = testaUtils.ent_relcoherent
  testa_ent_linking_type = testaUtils.ent_linking_type; testa_ent_linking_candprob = testaUtils.ent_linking_candprob
  
  testbUtils = inputUtils(args.rawword_dim,"testb")
  testb_input = testbUtils.emb; testb_out = testbUtils.tag; testb_entliking= testbUtils.ent_linking
  testb_ent_mention_index = testb_entliking['ent_mention_index']; testb_ent_mention_link_feature=testb_entliking['ent_mention_link_feature'];
  testb_ent_mention_tag = testb_entliking['ent_mention_tag']; testb_ent_relcoherent = testbUtils.ent_relcoherent
  testb_ent_linking_type = testbUtils.ent_linking_type; testb_ent_linking_candprob = testbUtils.ent_linking_candprob
  print 'cost:', time.time()-start_time,' to load data'
  
  '''function: lstm_output from seqLSTM'''
  config = tf.ConfigProto(allow_soft_placement=True,intra_op_parallelism_threads=4,inter_op_parallelism_threads=4)
  config.gpu_options.allow_growth=True
  sess_ner = tf.InteractiveSession(config=config)
  nerInstance = nameEntityRecognition(sess_ner)
  
  lstm_output_testa = nerInstance.getEntityRecognition(testa_input,testa_out)
  lstm_output_testb = nerInstance.getEntityRecognition(testb_input,testb_out)
  sess_ner.close()
  
  print 'start to initialize parameters'
  start_time = time.time()
  config = tf.ConfigProto(allow_soft_placement=True,intra_op_parallelism_threads=4,inter_op_parallelism_threads=4)
  config.gpu_options.allow_growth=True
  with tf.Session(config=config) as sess:
    modelNEL = ctxSum(args)  #build named entity linking models
    loss_linking = modelNEL.linking_loss
    optimizer = tf.train.AdamOptimizer(0.05)
    train_op_linking = optimizer.minimize(loss_linking)
#    tvars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,scope='ctxSum')
#    print 'tvars_linking:',tvars
#    grads,_ = tf.clip_by_global_norm(tf.gradients(loss_linking,tvars),10)
#    train_op_linking = optimizer.apply_gradients(zip(grads,tvars))
    sess.run(tf.global_variables_initializer())

    if modelNEL.load(sess,args.restore,"aida"):
      print "[*] ctxSum is loaded..."
    else:
      print "[*] There is no checkpoint for aida"

    
    '''@train named entity linking models'''
    maximum_linking=0
    id_epoch = 0
    maxsess = 0
    
    average_linking_accuracy_train = 0;average_loss_train = 0
    for label,f1,f2,f3,f4,f5 in nel_read_TFRecord(sess,train_TFfileName,train_nelShapeFile,256,args.epoch):
      ent_mention_linking_tag_list,candidate_ent_linking_feature,candidate_ent_type_feature,candidate_ent_prob_feature,ent_mention_lstm_feature,candidate_ent_relcoherent_feature = \
                                             getLinkingFeature(args,lstm_output_testa,testa_ent_mention_index,testa_ent_mention_tag,\
                                             testa_ent_relcoherent,testa_ent_mention_link_feature,testa_ent_linking_type,testa_ent_linking_candprob,0,flag='testa')
      loss2,accuracy,pred = sess.run([loss_linking,modelNEL.accuracy,modelNEL.prediction],
                            {modelNEL.ent_mention_linking_tag:ent_mention_linking_tag_list,
                             modelNEL.candidate_ent_coherent_feature:candidate_ent_relcoherent_feature,
                             modelNEL.candidate_ent_linking_feature:candidate_ent_linking_feature,
                             modelNEL.candidate_ent_type_feature:candidate_ent_type_feature,
                             modelNEL.candidate_ent_prob_feature:candidate_ent_prob_feature,
                             modelNEL.ent_mention_lstm_feature:ent_mention_lstm_feature,
                             modelNEL.keep_prob:1
                            })
      
      
      if accuracy > maximum_linking: 
        print "-----------------"
        f1_micro,f1_macro = f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='micro'),\
                                      f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='macro')
        print 'testa total loss:',loss2,' accuracy:',accuracy,' f1_micro:',f1_micro,' f1_macro:',f1_macro
        maximum_linking = accuracy
        maxsess = sess
        ent_mention_linking_tag_list,candidate_ent_linking_feature,candidate_ent_type_feature,candidate_ent_prob_feature,ent_mention_lstm_feature,candidate_ent_relcoherent_feature=\
                                             getLinkingFeature(args,lstm_output_testb,testb_ent_mention_index,testb_ent_mention_tag,\
                                             testb_ent_relcoherent,testb_ent_mention_link_feature,testb_ent_linking_type,testb_ent_linking_candprob,0,flag='testb')
        loss2,accuracy,pred = sess.run([loss_linking,modelNEL.accuracy,modelNEL.prediction],
                            {modelNEL.ent_mention_linking_tag:ent_mention_linking_tag_list,
                             modelNEL.candidate_ent_coherent_feature:candidate_ent_relcoherent_feature,
                             modelNEL.candidate_ent_linking_feature:candidate_ent_linking_feature,
                             modelNEL.candidate_ent_type_feature:candidate_ent_type_feature,
                             modelNEL.candidate_ent_prob_feature:candidate_ent_prob_feature,
                             modelNEL.ent_mention_lstm_feature:ent_mention_lstm_feature,
                             modelNEL.keep_prob:1
                            })
        f1_micro,f1_macro=f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='micro'),f1_score(np.argmax(ent_mention_linking_tag_list,1),np.argmax(pred,1),average='macro')
        print 'testb total loss:',loss2,' accuracy:',accuracy,' f1_micro:',f1_micro,' f1_macro:',f1_macro
        print "-----------------"
      _,loss2,accuracy,pred = sess.run([train_op_linking,loss_linking,modelNEL.accuracy,modelNEL.prediction],
                              {modelNEL.ent_mention_linking_tag:label,
                               modelNEL.candidate_ent_coherent_feature:f1,
                               modelNEL.candidate_ent_linking_feature:f2,
                               modelNEL.candidate_ent_type_feature:f3,
                               modelNEL.candidate_ent_prob_feature:f4,
                               modelNEL.ent_mention_lstm_feature:f5,
                               modelNEL.keep_prob:0.8
                              })
      average_linking_accuracy_train += accuracy
      average_loss_train += loss2
      id_epoch += 1
      if id_epoch %10==0:
        print 'train total loss:',loss2,' accuracy:',accuracy
    print 'average linking accuracy:',average_linking_accuracy_train/id_epoch, average_loss_train/id_epoch
    modelNEL.save(maxsess,args.restore,"aida")
      

if __name__=="__main__":
  tf.app.run()
  #å®ä¹linking model
