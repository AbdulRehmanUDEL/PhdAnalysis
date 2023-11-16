#!/usr/bin/env python3
########################################
## This script combines the Run data created.
## Change the directory where the data is stored 

import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
plt.rcParams["font.family"] = "serif"
plt.rcParams["mathtext.fontset"] = "dejavuserif"

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--version', type=str, default="v5", help='Dataset version to work with.')
args = parser.parse_args()

data_v = args.version
print(f"Verion of Data being used : {data_v}")

ABS_PATH_HERE=str(os.path.dirname(os.path.realpath(__file__)))

path =  ABS_PATH_HERE + f"/Dataset{data_v}"
Outpath =  path + "/ConcatinatedData"

channels = ["ant1ch0","ant1ch1","ant2ch0","ant2ch1","ant3ch0","ant3ch1"]

GoodRuns = [x for x in range(13) if x != 15]

for ich in range(len(channels)):
    channel = channels[ich]
    if not os.path.exists(Outpath):
        os.makedirs(Outpath)

    s_list = [np.load(path + f"/Run{i}_Time_{channel}_Signals.npy", allow_pickle=True) for i in GoodRuns]
    n_list = [np.load(path + f"/Run{i}_Time_{channel}_NoiseOnly.npy", allow_pickle=True) for i in GoodRuns]
    ns_list = [np.load(path + f"/Run{i}_Time_{channel}_SigPlusNoise.npy", allow_pickle=True) for i in GoodRuns]

    s = np.concatenate(s_list)
    del s_list
    n = np.concatenate(n_list)
    del n_list
    ns = np.concatenate(ns_list)
    del ns_list

    print(channel + ":")
    print("Signals Shape : ", np.shape(s))
    print("NoiseOnly Shape : ", np.shape(n))
    print("SigPlusNoise Shape : ", np.shape(ns))
    print("Len of One Trace and Total No's =", len(s[0]), len(s))

    np.savez_compressed(Outpath + f"/{channel}_AllSignals.npz", s)
    np.savez_compressed(Outpath + f"/{channel}_AllNoiseOnly.npz", n)
    np.savez_compressed(Outpath + f"/{channel}_AllSigPlusNoise.npz", ns)

######################################################################################
    ## Plot Traces
    NRows, NCols = 4, 3
    fig, axs = plt.subplots(NRows, NCols, figsize=(6*NCols, 4*NRows))
    fig.subplots_adjust(wspace=0.3, hspace=0.3)
    pltIndx = [6, 8, 17, 27]
    for i, pltIndx in enumerate(pltIndx):
        for j, data in enumerate([s, n, ns]):
            ax = axs[i, j]
            ax.plot(data[pltIndx])
            ax.set_title(f'pltIndx: {pltIndx}')
            ax.set_xlabel('Times')
            ax.set_ylabel('Amp')

    PlotsDir = ABS_PATH_HERE + "/Plots"
    if not os.path.exists(PlotsDir):
        print(f"Warning: The plots dir, {PlotsDir} does not exist. No plots will be saved")
    else:
        print(f"Saving Plots in the following dir {PlotsDir}")
        plt.savefig(PlotsDir +f"/{data_v}_{channel}_Traces.pdf", bbox_inches='tight')

    del s, n, ns
