#!/usr/bin/env python3

from icecube.icetray import I3Tray
from icecube import icetray, radcube, dataclasses, taxi_reader
from icecube.radcube import defaults
from icecube.icetray import I3Units
import random
from icecube.icetray.i3logging import log_info, log_error, log_fatal, log_trace, log_warn #added log_warn
icetray.I3Logger.global_logger.set_level(icetray.I3LogLevel.LOG_INFO)
from modules.ShiftAntTraces import ShiftAntTraces
from modules.SelectCleanSig import SelectCleanSig

from icecube.radcube import SpikeFilter

# from python_tools.TAXIBackgroundReader import AddTaxiBackgroundTrace

import numpy as np
import os

ABS_PATH_HERE=str(os.path.dirname(os.path.realpath(__file__)))

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input', type=str, nargs='+', default=[], help='Input data files.')
parser.add_argument('--output', type=str, default="Run", help='Output file name.')
parser.add_argument('--taxi', type=str, nargs='+',  default=[], help='Location of taxi backround files')

args = parser.parse_args()
assert(len(args.input))

import numpy as np

#########################################################################################
class DataExtractor(icetray.I3Module):
 
  def __init__(self,ctx):
    icetray.I3Module.__init__(self,ctx)
    self.inputNameNoisy = ""
    self.AddParameter("InputNameNoisy", "Input filtered cleaned noisy voltages", self.inputNameNoisy)
    self.inputNameNoise = ""
    self.AddParameter("InputNameNoise", "Input filtered cleaned noise voltages", self.inputNameNoise)
    self.inputNameTrue = ""
    self.AddParameter("InputNameTrue", "Input filtered scaled signal", self.inputNameTrue)

  def Configure(self):
    self.inputNameNoisy = self.GetParameter("InputNameNoisy")
    self.inputNameNoise = self.GetParameter("InputNameNoise")
    self.inputNameTrue = self.GetParameter("InputNameTrue")
    self.Signals = [[[] for i in range(3*2)] for j in range(2)]
    self.SigPlusNoise  = [[[] for i in range(3*2)] for j in range(2)]
    self.NoiseOnly = [[[] for i in range(3*2)] for j in range(2)]
    self.signalcounter = 0
    self.noiseonlycounter = 0
    self.sigplusnoisecounter = 0


  def Physics(self, frame):
    Signals = frame[self.inputNameTrue] # Its an antenna data map
    SigPlusNoise = frame[self.inputNameNoisy]
    NoiseOnly = frame[self.inputNameNoise]

    def GetAntData(AntMap, List, counter): ## give it a Antenna Map and empty list, it will give you list of time series
      nant = 3
      nch = 2 # Under the assumption that all antennas have 2 channels

      for iant, antkey in enumerate(AntMap.keys()):
        channelMapSig = AntMap[antkey]
        for ich, key in enumerate(channelMapSig.keys()):
          chdata = channelMapSig[key]
          fft = chdata.GetFFTData()
          timeseries = fft.GetTimeSeries()
          # spectrum = fft.GetFrequencySpectrum()
          timeseriespy = [timeseries[i] for i in range(timeseries.GetSize())]
          # spectrumpy = [spectrum[i] for i in range(spectrum.GetSize())]
          List[0][counter % 6].append(timeseriespy)
          # List[1][counter % 6].append(spectrumpy)
          counter += 1
      return counter

    self.signalcounter = GetAntData(Signals, self.Signals, self.signalcounter) 
    self.sigplusnoisecounter = GetAntData(SigPlusNoise, self.SigPlusNoise, self.sigplusnoisecounter)
    self.noiseonlycounter = GetAntData(NoiseOnly, self.NoiseOnly, self.noiseonlycounter)

    print("Signal counter: ", self.signalcounter) # If these are non-zero, it's good
    print("NoiseOnly counter: ", self.noiseonlycounter)
    print("SigPlusNoise counter: ", self.sigplusnoisecounter)

    # Add an error readout here
    domain_list = ["time"]
    ch_list = ["ant1ch0", "ant1ch1", "ant2ch0", "ant2ch1", "ant3ch0", "ant3ch1"]
    for idom in range(len(domain_list)):
      print("\n \n Domain: ", domain_list[idom])
      for ich in range(len(ch_list)):
        print("\n Channel:", ch_list[ich])
        
        # Organization of nested lists:
        # Signals --> domains (time and freq) --> channels --> antennas --> traces

        # print("Number of events", len(self.Signals)) # should be 1
        print("Number of domains", len(self.Signals)) # should be 2
        print("Number of channels",  len(self.Signals[idom])) # should be 6
       
        print("Signals number of antennas", len(self.Signals[idom][ich])) # should be 163 (or 162 for ant3)
        print("NoiseOnly number of antennas", len(self.NoiseOnly[idom][ich])) # should be 163 (or 162 for ant3)
        print("SigPlusNoise number of antennas", len(self.SigPlusNoise[idom][ich])) # should be 163 (or 162 for ant3)

        print("Signals channel length", len(self.Signals[idom][ich][0])) # should be 4096
        print("NoiseOnly channel length", len(self.NoiseOnly[idom][ich][0])) # should be 4096
        print("SigPlusNoise channel length", len(self.SigPlusNoise[idom][ich][0])) # should be 4096

      for ich2 in range(len(ch_list)-1):
        for iant in range((len(self.Signals[idom][ich2]))-1):
          if len(self.Signals[idom][ich2][iant]) != len(self.Signals[idom][ich2+1][iant]):
            log_warn("Channels {0} and {1} have different numbers of pure signal traces in the {2} domain".format(ch_list[ich2],ch_list[ich2+1],domain_list[idom]))
            log_warn("Num traces in {0}: {1}".format(ch_list[ich2],len(self.Signals[idom][ich2][iant])))
            log_warn("Num traces in {0}: {1}".format(ch_list[ich2+1],len(self.Signals[idom][ich2+1][iant])))
          if len(self.NoiseOnly[idom][ich2][iant]) != len(self.NoiseOnly[idom][ich2+1][iant]):
            log_warn("Channels {0} and {1} have different numbers of noise only traces in the {2} domain".format(ch_list[ich2],ch_list[ich2+1],domain_list[idom]))
            log_warn("Num traces in {0}: {1}".format(ch_list[ich2],len(self.NoiseOnly[idom][ich2][iant])))
            log_warn("Num traces in {0}: {1}".format(ch_list[ich2+1],len(self.NoiseOnly[idom][ich2+1][iant])))
          if len(self.SigPlusNoise[idom][ich2][iant]) != len(self.SigPlusNoise[idom][ich2+1][iant]):
            log_warn("Channels {0} and {1} have different numbers of noisy signal traces in the {2} domain".format(ch_list[ich2],ch_list[ich2+1],domain_list[idom]))
            log_warn("Num traces in {0}: {1}".format(ch_list[ich2],len(self.SigPlusNoise[idom][ich2][iant])))
            log_warn("Num traces in {0}: {1}".format(ch_list[ich2+1],len(self.SigPlusNoise[idom][ich2+1][iant])))

  def Finish(self):
    ##########################################################################################################################
    # Counting number of pure signal and noise only traces
    SigTraces = [0,0,0,0,0,0]
    NoiseTraces = [0,0,0,0,0,0]

    for i in range(len(self.Signals[0])):
      channel = self.Signals[0][i]
      for trace in channel:
        if np.max(trace) == 0:
          NoiseTraces[i] += 1
        else:
          SigTraces[i] += 1

    print("\nTotal Number of Signal Traces (for this run): ", sum(SigTraces))
    print("Total Number of Noise Only Traces (for this run): ", sum(NoiseTraces))

    ##########################################################################################################################

    OutputDir = ABS_PATH_HERE + "/data/Datasetv8_MJ_v3/"
    ch_list = ["ant1ch0", "ant1ch1", "ant2ch0", "ant2ch1", "ant3ch0", "ant3ch1"]

    for ich in range(len(ch_list)):
      # time series
      np.save(OutputDir + "{0}_Time_{1}_Signals.npy".format(args.output, ch_list[ich]), self.Signals[0][ich])
      np.save(OutputDir + "{0}_Time_{1}_SigPlusNoise.npy".format(args.output, ch_list[ich]), self.SigPlusNoise[0][ich])
      np.save(OutputDir + "{0}_Time_{1}_NoiseOnly.npy".format(args.output, ch_list[ich]), self.NoiseOnly[0][ich])
      # np.save(OutputDir + "{0}_Spec_{1}_NoiseOnly.npy".format(args.output, ch_list[ich]), self.NoiseOnly[1][ich])


    print("Finishing up..")

##########################################################################################################################
NBins = 1000    #Number of bins at 1ns sampling
upsampleFactor = 4
bandLimits = [60 * I3Units.megahertz, 350 * I3Units.megahertz]

tray = I3Tray()

#Includes the tables of the antenna gain patterns
AntennaServiceName = defaults.CreateDefaultAntennaResponse(tray)
#Includes the tables of the electronics: LNA, radioboard, etc.
# ElectronicServiceName = defaults.CreateDefaultElectronicsResponse(tray,"ElectronicServiceName")

## Note: I was using ElectronicServiceName, but for 2022 I am using custom one
# electronicName = "electronicName"
ElectronicServiceName = "ElectronicServiceName"

tray.AddService(
    "I3ElectronicsResponseFactory",
    ElectronicServiceName,
    AntennaType=dataclasses.I3AntennaGeo.AntennaType.SKALA2,
    IncludeLNA=False, ## On for T3.2
    IncludeCables=True,    ## ON
    CableTemperature=radcube.constants.cableTemp,
    IncludeRadioBoard=False, ## OFF
    IncludeTaxi=False,  ## OFF
    CustomResponseFiles=["/cvmfs/icecube.opensciencegrid.org/users/acoleman/radcube-datasets/electronic-response/LNA_v2_Measured.dat", "/cvmfs/icecube.opensciencegrid.org/users/acoleman/radcube-datasets/electronic-response/TAXIv3.2_Radioboardv2_2021.04.27.dat"],
    # CustomResponseFiles=["/cvmfs/icecube.opensciencegrid.org/users/acoleman/radcube-datasets/electronic-response/TAXIv3.2_Radioboardv2_2021.04.27.dat"],
    InstallServiceAs=ElectronicServiceName,
)


tray.AddModule("CoreasReader", "coreasReader",
               DirectoryList=args.input,
               MakeGCDFrames=True,
               MakeDAQFrames=True
              )

# "GeneratedNoiseMap" # OutPut name of BringTheNoise Module

#Add zeros to the front of the EFields so that the total length is
#5000 bins
tray.AddModule("ZeroPadder", "iPad",
               InputName=radcube.GetDefaultSimEFieldName(),
               OutputName="ZeroPaddedMap",
               ApplyInDAQ = True,
               AddToFront = True,
               AddToTimeSeries = True,
               FixedLength = int(5 * NBins)
              )


#Convolves the EFields with the antenna gain patterns. After this module
#all data will be I3AntennaDataMaps with voltages in them
tray.AddModule("ChannelInjector", "ChannelInjector",
                InputName="ZeroPaddedMap",
                OutputName="ChannelInjectedMap",
                AntennaResponseName=AntennaServiceName
              )

#Will change the sampling rate of a trace to a higher/lower one
tray.AddModule("TraceResampler", "Resampler",
               InputName="ChannelInjectedMap",
               OutputName="ResampledVoltageMap",
               ResampledBinning=1*I3Units.ns
              )

#Adds a phase delay to the signals which "rotates" the bins
tray.AddModule("AddPhaseDelay", "AddPhaseDelay",
                InputName="ResampledVoltageMap",
                OutputName="PhaseDelayed",
                ApplyInDAQ=True,
                DelayTime=-120*I3Units.ns
              )


tray.AddModule(SelectCleanSig, "SelectOnlyCleanSig",
                InputName="PhaseDelayed",
                OutputName="CleanSignals",
                SNRCutoffValue=50,
                ApplyInDAQ=True,
              )

# tray.AddModule("BandpassFilter", "ButterworthFilter_OnSig",
#                InputName="PhaseDelayed",
#                OutputName="RawVoltageMap",
#                FilterType=radcube.eButterworth,
#                FilterLimits=[50 * I3Units.megahertz, 5000 * I3Units.megahertz],
#                ButterworthOrder=13,
#                ApplyInDAQ=True
#               )

tray.AddModule(ShiftAntTraces, "ShiftAntTraces",
               InputName="CleanSignals",
               OutputName="ShiftedSignals",
              ApplyInDAQ=True,
               )

### The Band pass is only for Pure signals
tray.AddModule("BandpassFilter", "BandpassFilterBox", ### The pure sig is band passed and then give to data extractor (lables for Denoiser)
                 InputName="ShiftedSignals",
                 OutputName="FilteredConvolvedSignal",
                 # FilterType=radcube.eButterworth,
                 FilterType=radcube.eBox,
                 FilterLimits=bandLimits,
                 # ButterworthOrder=13,
                 ApplyInDAQ=True
                )

#Convolves the voltages with the electronics response
tray.AddModule("ElectronicResponseAdder", "AddElectronics", ### Pure Sig is convolved with electronics and then given to digitizer (Noise will be added to them)
               InputName="ShiftedSignals",
               OutputName="ConvolvedSignal",
               ElectronicsResponse=ElectronicServiceName
              )


#Changes the real-valued waveforms to ADC bits like TAXI would do
tray.AddModule("WaveformDigitizer", "waveformdigitizer",
               InputName="ConvolvedSignal",
               OutputName="DigitizedSignal",
               ElectronicsResponse=ElectronicServiceName
              )

#Add measured noise waveforms to the simulated ones
tray.AddModule(radcube.modules.MeasuredNoiseAdder, "AddTaxiBackgroundTrace",
               InputName="DigitizedSignal",
               OutputName="WaveformWithBackground",
               TaxiFile=args.taxi,
               NTimeBins=NBins,
               NTraces=600000,
               InsertNoiseOnly=True,
               ConvertToVoltage = False,
               Overuse=False, ## Use background waveforms more than once if necessary
               ## Only using Non-cascaded waveforms
               RequiredWaveformLength=1024,

               ## Applying the spike filter
               SpikeFilter=SpikeFilter(filename="/home/arehman/work/DeepAnalysis/AlanAnalysisDir/icecube-analysis/detection-efficiency/data/spike-filter/SpikeFilter_v6_Feb_TAXIBased.dat"),
               SpikePower =2,

               ## ArtifactRemover arguments
               RemoveNegativeBins=True, ############
               RemoveBinSpikes=True,
               BinSpikeDeviance=800,
               MedianOverCascades=True
              )

#############################################################
#Makes the P-Frame for this Q-Frame
tray.AddModule("I3NullSplitter","splitter",
               SubEventStreamName="RadioEvent"
                ) 

#Converts the ADC counts back into voltages and removes the baseline
for framename in ['WaveformWithBackground', 'TAXINoiseMap']:
  tray.AddModule("PedestalRemover", "pedestalRemover{0}".format(framename),
               InputName="{0}".format(framename),
               OutputName="{0}Voltage".format(framename),
               ElectronicsResponse=ElectronicServiceName,       #Name of I3ElectronicsResponse service
               ConvertToVoltage=True
              )

#Applies a filter to the data with the given limits and filter type
for framename in ['WaveformWithBackgroundVoltage', 'TAXINoiseMapVoltage']:
  tray.AddModule("BandpassFilter", "BandpassFilterBoxForNoisy{0}".format(framename),
                 InputName="{0}".format(framename),
                 OutputName="Filtered{0}".format(framename),
                 # FilterType=radcube.eButterworth,
                 FilterType=radcube.eBox,
                 FilterLimits=bandLimits,
                 # ButterworthOrder=13,
                 ApplyInDAQ=False
                )

# for framename in ['FilteredWaveformWithBackgroundVoltage', 'FilteredTAXINoiseMapVoltage', 'FilteredScaledSignal']:
for framename in ['FilteredWaveformWithBackgroundVoltage', 'FilteredTAXINoiseMapVoltage']:
  tray.AddModule("ElectronicResponseRemover", f"RemoveElectronics{framename}",
               InputName=f"{framename}",
               OutputName=f"Deconvolved{framename}",
               ElectronicsResponse=ElectronicServiceName
              )


# for framename in ['DeconvolvedFilteredWaveformWithBackgroundVoltage', 'DeconvolvedFilteredTAXINoiseMapVoltage', 'DeconvolvedShiftedFilteredScaledSignal']:
#   tray.AddModule("ZeroPadder", "iPadSig{0}".format(framename),
#                InputName=framename,
#                OutputName="The{0}".format(framename),
#                ApplyInDAQ = False,
#                AddToFront = False,
#                AddToTimeSeries = False,
#                AppendN = int(NBins/2) * (upsampleFactor - 1)
#               )



tray.AddModule(DataExtractor, "DataExtract",
               InputNameNoisy="DeconvolvedFilteredWaveformWithBackgroundVoltage",
               InputNameNoise="DeconvolvedFilteredTAXINoiseMapVoltage",
               InputNameTrue="FilteredConvolvedSignal"
               # InputNameTrue="RawVoltageMap"
              )

tray.AddModule("TrashCan", "trashcan")
tray.Execute()
tray.Finish()
