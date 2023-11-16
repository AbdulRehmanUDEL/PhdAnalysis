from I3Tray import I3Tray
from icecube import icetray, radcube, dataclasses
from icecube.icetray.i3logging import log_info, log_error, log_fatal, log_trace
icetray.I3Logger.global_logger.set_level(icetray.I3LogLevel.LOG_INFO)
import numpy as np
import random

class ShiftAntTraces(icetray.I3Module):

  def __init__(self,ctx):
    icetray.I3Module.__init__(self,ctx)
    self.inputName = ""
    self.AddParameter("InputName", "Input Antenna DataMap", self.inputName)
    self.outputName = ""
    self.AddParameter("OutputName", "Output Antenna DataMap", self.outputName)
    self.applyInDAQ = True
    self.AddParameter("ApplyInDAQ", "If true, will apply filter on Q Frames, else P Frames", self.applyInDAQ)

  def Configure(self):
    log_info("Configuring " + self.name)
    self.inputName = self.GetParameter("InputName")
    self.outputName = self.GetParameter("OutputName")
    self.applyInDAQ = self.GetParameter("ApplyInDAQ")
    log_info("Will apply in the "+("P", "Q")[self.applyInDAQ]+ " Frame")


  def RunOnFrame(self, frame):
    log_trace("({0}) Applying the SNR Cut and scaling the waveforms".format(self.name))
    
    antDataMap = frame[self.inputName]
    outputAntDataMap = dataclasses.I3AntennaDataMap()

    for iant, antkey in enumerate(antDataMap.keys()):
      chMap = antDataMap[antkey]
      outputChMap = dataclasses.I3AntennaChannelMap()
      ## Band Pass filter also shift the signals within traces, check to make sure that you have
      ## correct phase delayed applied to keep them at the center of trace 
      spread = 300
      shifInd = random.randint(-spread,spread)

      for ich, chkey in enumerate(chMap.keys()):
        fftData = chMap[chkey].GetFFTData()
        timeseries = fftData.GetTimeSeries()
        timeseries.Roll(shifInd)
        
        outputFFT = dataclasses.FFTData(timeseries)

        outputChMap[chkey] = dataclasses.I3AntennaChannel(outputFFT)

      outputAntDataMap[antkey] = outputChMap

    frame[self.outputName] = outputAntDataMap

  def DAQ(self, frame):
    if self.applyInDAQ:
      self.RunOnFrame(frame)
    self.PushFrame(frame)

  def Physics(self, frame):
    if not self.applyInDAQ:
      self.RunOnFrame(frame)
    self.PushFrame(frame)