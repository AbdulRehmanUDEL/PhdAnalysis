#!/usr/bin/env python3
#################################################################
# This script search for radio events passing the provided SNR cuts
# and reconstruct the arrival direction by fitting a simple plane wave.
# The script also saves an i3 files with only the passed events.
#####################################################################

from icecube.icetray import I3Tray
from icecube import icetray, radcube, dataio, taxi_reader, dataclasses
from icecube.icetray import I3Units
icetray.I3Logger.global_logger.set_level(icetray.I3LogLevel.LOG_INFO)

import numpy as np
import sys
from modules.ChannelSelector_SNRCut_chwise import ChannelSelector_SNRCut_chwise


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, nargs="+", help="Input data files.")
parser.add_argument('--output', type=str, default="ReconstructedShowers", help='Output i3 file name.')
parser.add_argument("--gcd", required=True, type=str, help="Input GCD file.")
parser.add_argument("--month", required=True, type=str, help="Which month's SNR cuts to use options: JanFeb, MayJune")

args = parser.parse_args()
#################################################
def PassRadioShowers(frame):
  Particle = frame["EstimatedRadioShower"]
  print(f"Reconstructed Zen = {Particle.dir.zenith} and Azi = {Particle.dir.azimuth}")
  if not np.isnan(Particle.dir.zenith):
    print("---------Particle Reconstructed----------")
    return True
  else:
    print("----------Reconstruction Failed---------------")
    return False
#################################################
def PassOnlyNonCascading(frame):
  return "RadioTraceLength" in frame and frame["RadioTraceLength"].value == 1024
#########################################################################
def SelectCRTriggered(frame):
    ## To select only scint triggered events.
    return "SurfaceFilters" in frame and not frame['SurfaceFilters']['soft_flag'].condition_passed
#############################################################################
def SelectSoftTriggered(frame):
    ## To select only soft triggered events.
    return "SurfaceFilters" in frame and frame['SurfaceFilters']['soft_flag'].condition_passed
#########################################################################
taxiName = taxi_reader.taxi_tools.taxi_antenna_frame_name()
bandLimits = [100 * I3Units.megahertz, 230 * I3Units.megahertz]
electronicName = "electronicName"

tray = I3Tray()

## We use the custom LNA and Radioboard response 
tray.AddService(
    "I3ElectronicsResponseFactory",
    electronicName,
    AntennaType=dataclasses.I3AntennaGeo.AntennaType.SKALA2,
    IncludeLNA=False, 
    IncludeCables=True,
    CableTemperature=radcube.constants.cableTemp,
    IncludeRadioBoard=False,
    IncludeTaxi=False,
    CustomResponseFiles=["/cvmfs/icecube.opensciencegrid.org/users/acoleman/radcube-datasets/electronic-response/LNA_v2_Measured.dat", "/cvmfs/icecube.opensciencegrid.org/users/acoleman/radcube-datasets/electronic-response/TAXIv3.2_Radioboardv2_2021.04.27.dat"],
    InstallServiceAs=electronicName,
)

tray.AddModule("I3Reader", "Reader",
 FilenameList=[args.gcd]+args.input)

## Select Only Non Cascading data
tray.AddModule(PassOnlyNonCascading, "NonascadingOnly",  
    Streams=[icetray.I3Frame.DAQ])  

## Select Only Scinitllator triggered data
tray.AddModule(SelectCRTriggered, "Triggered",  
    Streams=[icetray.I3Frame.DAQ])   

## Remove Taxi artifacts like singlebin spikes.
tray.AddModule(radcube.modules.RemoveTAXIArtifacts, "Mangle", 
    InputName=taxiName, 
    OutputName="DemangledWaveforms",
    RemoveNegativeBins=True, 
    BinSpikeDeviance=800,
    RemoveBinSpikes=True,
    MedianOverCascades=True, 
    )

## Select the middle 1000 bins of each trace
tray.AddModule("WaveformChopper", "LilChoppy", 
    InputName="DemangledWaveforms",
    OutputName="ChoppedWaveformMap",
    MaxBin=1023-12,
    MinBin=12
    )

## Makes the P-Frame for this Q-Frame
tray.AddModule("I3NullSplitter", "splitter",
    SubEventStreamName="RadioEvent")

tray.AddModule("PedestalRemover", "pedestalRemover",
    InputName="ChoppedWaveformMap",
    OutputName="PedestalRemoved",
    ElectronicsResponse=electronicName,
    ConvertToVoltage=True)

## Apply spike filter to get rid of broad-band noise 
tray.AddModule(radcube.modules.ApplySpikeFilter, "SpikeFilter",
    InputName="PedestalRemoved",
    OutputName="SpikeFilteredVoltageMap",
    ApplyInDAQ=False,
    FilterFile="/home/arehman/work/DeepAnalysis/AlanAnalysisDir/icecube-analysis/detection-efficiency/data/spike-filter/SpikeFilter_v6_Feb_TAXIBased.dat"
    )

## Apply bandpass filter 
tray.AddModule("BandpassFilter", "BoxRawFilter",
    InputName="SpikeFilteredVoltageMap",
    OutputName="FilteredMap",
    FilterType=radcube.eBox,
    FilterLimits=bandLimits
    )

## Remove all the electronic responses, LNA, cabels, etc
tray.AddModule("ElectronicResponseRemover", "RemoveElectronics",
               InputName="FilteredMap",
               OutputName="DeconvolvedMap",
               ElectronicsResponse=electronicName
              )


## Upsample the waveforms by a factor of 8.
NBins = 1000    #Number of bins at 1ns sampling
upsampleFactor = 8 # This gives a final sampling rate of 0.125ns
tray.AddModule("ZeroPadder", "iPadTraces",
            InputName="DeconvolvedMap",
           OutputName="UpsampledMap",
           ApplyInDAQ = False,
           AddToFront = False,
           AddToTimeSeries = False,
           AppendN = int(NBins/2) * (upsampleFactor - 1)
          )
#############################################################################################################
## SNR Cut values 95% Rejection of background
if args.month == "JanFeb":
    # snr_cut_values = [[39, 38], [30, 33], [37, 44]] ## Old vals without Upsampling
    snr_cut_values = [[43, 42], [33, 35], [41, 49]] ## Vals With upsampling

elif args.month == "MayJune":
    # snr_cut_values = [[51, 142], [63, 48], [25, 33]] ## Old vals without Upsampling
    snr_cut_values = [[56, 153], [69, 53], [27, 36]] ## Vals With upsampling


## Apply SNR cut on channles, Select event if at least one of the channel of antenna passes the cut.
tray.AddModule(ChannelSelector_SNRCut_chwise, "select",
    InputName="UpsampledMap",
    RequireAllChannels=False,
    # SNRThresholds_Values=[[0.1, 0.1], [0.1, 0.1], [0.1, 0.1]],  ## Fake values
    SNRThresholds_Values=snr_cut_values,
    NoOfSubtraces=16,
    OutputName="RejectedAntennasList", ## List of Bad Antennas not passing the cuts.
    )


## Estimate the arrival direction of the radio events.
tray.AddModule("EstimateRadioShower", "estimateShowerParticle",
   InputName="UpsampledMap",
   AntennaBadList="RejectedAntennasList",
   OutputName="EstimatedRadioShower",
   UseOnlyTopThree=False                            
    )

## Select only reconstructed events.
tray.AddModule(PassRadioShowers, "RadioEvents",  ## Select only specific events
    Streams=[icetray.I3Frame.Physics])   ## Runs only on P frame

# Delete the un-necessary items from the frame
tray.AddModule("Delete", "Deleting",
              Keys=["PedestalRemoved", "ChoppedWaveformMap","FilteredMap",
              "RejectedAntennasList","SpikeFilteredVoltageMap"],
              )

tray.AddModule("I3Writer", "writer",
 Filename=args.output+".i3.gz",
 Streams=[icetray.I3Frame.Physics, icetray.I3Frame.DAQ],
 DropOrphanStreams=[icetray.I3Frame.DAQ])

tray.Execute()
