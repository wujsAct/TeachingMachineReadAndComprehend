# -*- coding: utf-8 -*-
"""
Created on Fri May 05 14:47:15 2017

@author: wujs
@function: generate MLP,LSTM layers
"""
import tensorflow as tf


class CNN(object):
  '''
  CNN layer for Text
  '''
  def __init__(self,filters,word_embedding_size,num_filters):
    self.filters = filters
    self.embedding_size  = word_embedding_size
    self.num_filters = num_filters
    self.Ws = []
    self.bs = []
    for i,filter_size in enumerate(self.filters):
      with tf.name_scope("conv-maxpool-%s" % filter_size):
        filter_shape =[filter_size,self.embedding_size,1,self.num_filters]
        self.Ws.append(tf.Variable(tf.truncated_normal(filter_shape, stddev=0.1), name="W"))
        self.bs.append(tf.Variable(tf.constant(0.1, shape=[self.num_filters]), name="b"))
  '''
  x: [batch,sequence_length,feature_dimension,1] === >[batch,in_height,in_width,in_channels]
  filter: [filter_height,filter_widht,in_channels,out_channels]
  '''
  def __call__(self,x,sequence_length):
    self.pooled_outputs = []
    for i,filter_size in enumerate(self.filters):
      with tf.name_scope("conv-maxpool-%s" % filter_size):
        #convolution layer
        W = self.Ws[i]; b = self.bs[i]
        conv = tf.nn.conv2d(
            x,
            W,
            strides=[1,1,1,1],
            padding='VALID',
            name='conv')
        # Apply nonlinearity
        h = tf.nn.relu(tf.nn.bias_add(conv, b), name="relu")
      
         # Max-pooling over the outputs
        pooled = tf.nn.max_pool(
            h,
            ksize = [1, sequence_length-filter_size + 1, 1, 1],
            strides=[1,1,1,1],
            padding='VALID',
            name='pool')
        
      
        self.pooled_outputs.append(pooled)
    print 'self.pooled_outputs:',self.pooled_outputs
    #Combine all the pooled features
    num_filters_total = self.num_filters * len(self.filters) #?a little weird
    self.h_pool = tf.concat(self.pooled_outputs,3)
    self.h_pool_flat = tf.reshape(self.h_pool, [-1, num_filters_total])
    
    return self.h_pool_flat
        
    
    
class BiLSTM(object):
  '''
  LSTM layers using dynamic rnn
  '''
  def __init__(self,cell_size,num_layers=1,keep_prob=1.0,name='LSTM'):
    self.cell_size = cell_size
    self.num_layers = num_layers
    self.keep_prob = keep_prob
    self.reuse = None
    self.trainable_weights = None
    self.name = name
    
    self.fw_cell = tf.contrib.rnn.MultiRNNCell([
          tf.contrib.rnn.LSTMCell(self.cell_size,state_is_tuple=True,reuse=tf.get_variable_scope().reuse)
          ])
  
    self.bw_cell = tf.contrib.rnn.MultiRNNCell([
          tf.contrib.rnn.LSTMCell(self.cell_size,state_is_tuple=True,reuse=tf.get_variable_scope().reuse)
          ])
  

  #x() equals to x.__call___()
  def __call__(self,x,seq_length=None):  #__call__ is very efficient when the state of instance changes frequently 
    with tf.variable_scope(self.name,reuse = self.reuse) as vs:
      if seq_length ==None:  #get the real sequence length (suppose that the padding are zeros)
        used = tf.sign(tf.reduce_max(tf.abs(x),reduction_indices=2))
        seq_length = tf.cast(tf.reduce_sum(used,reduction_indices=1),tf.int32)
      
      lstm_out,next_state =  tf.nn.bidirectional_dynamic_rnn(self.fw_cell,self.bw_cell,x,
                                            dtype=tf.float32,sequence_length=seq_length,scope='LSTM_1')
      
      #shape(lstm_out) = (batch_size,sequence_length,2*cell_size)
      lstm_out = tf.concat(lstm_out, 2)  #concate the forward and backward
      
      
      if self.keep_prob < 1.:
        lstm_out = tf.nn.dropout(lstm_out, self.keep_prob)
        
      if self.reuse is None:
        self.trainable_weights = vs.global_variables()
        
    self.reuse =True
    return lstm_out,next_state,seq_length

class FullyConnection(object):
  def __init__(self,output_size):
    self.output_size = output_size
    
  def __call__(self,inputs,activation_fn):
    out = tf.contrib.layers.fully_connected(inputs,self.output_size, 
                                           activation_fn=activation_fn,
                                           )
    return out
'''
There are a lot of loss function defined in tensorflow!
'''
def classification_loss(flag,labels,logits):
  if flag == 'figer':
    loss = tf.losses.mean_pairwise_squared_error(labels,logits)
  elif flag=='sigmoid':
    loss = tf.losses.sigmoid_cross_entropy(labels,logits)
  else:
    loss = tf.losses.tf.losses.softmax_cross_entropy(labels,logits)  #must one-hot entropy
  
  return loss