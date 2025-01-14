#!/usr/bin/env python
# -*- coding:utf-8 -*-

import argparse
import torch
import torch.nn as nn
import torch.optim as optim
from  model.seriesNet_torch import seriesNet #, gated_block
from CausalTrainTest import TrainManager
import numpy as np
import random
import glob
import itertools
import data_set.fn_500_dataset as fn_500_dataset
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt
import importlib

def argument_parser():
    """
        A parser to allow user to easily experiment different models along with datasets and differents parameters
    """
    parser = argparse.ArgumentParser(usage='\n python3 train.py [model] [dataset] [hyper_parameters]'
                                           '\n python3 train.py --model UNet [hyper_parameters]'
                                           '\n python3 train.py --model UNet --predict',
                                     description="This program allows to train different models of regression on fn_500_dataset"
                                                 )
    parser.add_argument('--company', type=str, default='AAPL_data',
                        help="Company's name")
    parser.add_argument('--nargs', nargs='+')

    parser.add_argument('--batch_size', type=int, default=20,
                        help='The size of the training batch')
    parser.add_argument('--nb_causal_blk', type=int,  nargs='+',
                        help='Nb of causal block to tack')
    parser.add_argument('--nb_filter', type=int,  nargs='+',
                        help='Nb of filter to use in SeriesNet')
    parser.add_argument('--nb_drop_blk', type=int,  nargs='+',
                        help='Nb of causal blk where to apply dropout')
    parser.add_argument('--channel_2_use', type=str, default='close', choices=["open", "close","high","low","volume"],
                        help='Channel to use')
    parser.add_argument('--optimizer', type=str, nargs='+', choices=["Adam", "SGD"],
                        help="The optimizer to use for training the model")
    parser.add_argument('--num_epochs', type=int, default=7,
                        help='The number of epochs')
    parser.add_argument('--validation', type=float, default=20,
                        help='Percentage of training data to use for validation')
    parser.add_argument('--lr', type=float,  nargs='+',
                        help='Learning rate')
    parser.add_argument('--pts_2_pred', type=int, default=20,
                        help='Points to forecast')
    parser.add_argument('--save', action='store_true',
                        help='Learning rate')
    parser.add_argument('--schuffle', action='store_true',
                        help='Schuffle or not the dataset between each epoch')
    return parser.parse_args()

if __name__ == "__main__":

    args = argument_parser()

    batch_size = args.batch_size
    num_epochs = args.num_epochs
    val_percent = args.validation
    learning_rate = args.lr
    nb_causal_blk = args.nb_causal_blk
    nb_filter = args.nb_filter
    nb_drop_blk = args.nb_drop_blk
    channel_2_use = args.channel_2_use

    #nb_causal_blk = [5, 6, 7, 8, 9]
    #learning_rate = np.random.choice(np.arange(1, 11), 3, replace=False) / 10000
    #nb_filter = [16, 24, 32]
    #nb_drop_blk = [2, 3, 4]
    optimizer = ['sgd', 'Adam']
    batch_size = 15
    num_epochs = 7
    # val_percent = args.validation
    channel_2_use = 'close'
    pts_2_pred = args.pts_2_pred
    company = 'AAPL_data'
    validation = 20
    shuffle = False
    result = {}

    for causal_b, lr, filter, drop_blk, opti in itertools.product(nb_causal_blk, learning_rate, nb_filter, nb_drop_blk,
                                                                  optimizer):
        converge = False
        print("Training for causal_b : {}, lr : {}, filter : {}, drop_blk : {}, opti : {}".format(causal_b, lr, filter,
                                                                                                  drop_blk, opti))

        while not converge:
            model = seriesNet(1, nb_causal_block=causal_b, gate_nb_filter=filter, nb_block_dropped=drop_blk)
            model.float()
            N = model.get_pts_for_Pred()
            dataset_train, dataset_eval, test_input, test_target = fn_500_dataset.create_sliding_dataset(N,
                                                                                                         pts_2_pred=pts_2_pred,
                                                                                                         proportion=validation,
                                                                                                         action_name=company,
                                                                                                         axis=channel_2_use,
                                                                                                         normalise=True)

            train_loader = DataLoader(dataset_train, batch_size=batch_size, shuffle=shuffle, drop_last=False)
            valid_loader = DataLoader(dataset_eval, batch_size=batch_size, shuffle=shuffle, drop_last=False)

            manager = TrainManager(model,
                                   train_loader,
                                   valid_loader,
                                   lr=lr,
                                   loss_fn='MeanSquared',
                                   optimizer_type=opti,
                                   pts_2pred=pts_2_pred)

            manager.train(num_epochs, display=False)
            pred = manager.predict(test_input, test_target)
            if len(np.unique(pred)) != 1:
                converge = True
                loss = np.mean((test_target.view(-1).detach().numpy() - pred) ** 2)
                result[(causal_b, lr, filter, drop_blk, opti)] = loss
            else:
                print('problemo')

    print("Combinaison gagnante : ", min(result, key=result.get))