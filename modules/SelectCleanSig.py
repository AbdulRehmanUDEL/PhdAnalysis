from I3Tray import I3Tray
from icecube import icetray, radcube, dataclasses
from icecube.icetray.i3logging import log_info, log_error, log_fatal, log_trace
icetray.I3Logger.global_logger.set_level(icetray.I3LogLevel.LOG_INFO)
import numpy as np

class SelectCleanSig(icetray.I3Module):

  def __init__(self,ctx):
    icetray.I3Module.__init__(self,ctx)
    self.inputName = ""
    self.AddParameter("InputName", "Input Antenna DataMap", self.inputName)
    self.outputName = ""
    self.AddParameter("OutputName", "Output Antenna DataMap", self.outputName)
    self.snrCutoffValue = 40
    self.AddParameter("SNRCutoffValue", "Will only keep traces with SNRs higher than this value", self.snrCutoffValue)

    self.applyInDAQ = True
    self.AddParameter("ApplyInDAQ", "If true, will apply filter on Q Frames, else P Frames", self.applyInDAQ)

  def Configure(self):
    log_info("Configuring " + self.name)
    self.inputName = self.GetParameter("InputName")
    self.outputName = self.GetParameter("OutputName")
    self.snrCutoffValue = self.GetParameter("SNRCutoffValue")
    self.applyInDAQ = self.GetParameter("ApplyInDAQ")
    log_info("Will apply in the "+("P", "Q")[self.applyInDAQ]+ " Frame")


  def RunOnFrame(self, frame):
    ## The following function assumes that the signals are located at the center of traces
    def GetSNR(trace, binlow=510):
      Trace_Peak = np.max(np.abs(trace)) 
      chunk = np.array(trace[binlow:810])
      RMS_squared = sum(chunk ** 2) / len(chunk)
      SNR = Trace_Peak ** 2 / RMS_squared
      return SNR
    #####################################################################################
    log_trace("({0}) Applying the SNR Cut and scaling the waveforms".format(self.name))
    
    antDataMap = frame[self.inputName]
    outputAntDataMap = dataclasses.I3AntennaDataMap()

    for iant, antkey in enumerate(antDataMap.keys()):
      chMap = antDataMap[antkey]
      outputChMap = dataclasses.I3AntennaChannelMap()

      chPassed = 0
      for ich, chkey in enumerate(chMap.keys()):
        fftData = chMap[chkey].GetFFTData()
        timeseries = fftData.GetTimeSeries()
        times, tsPy = radcube.RadTraceToPythonList(timeseries)
        # PeakTime = dataclasses.fft.GetHilbertPeakTime(timeseries)
        # peak, rms, snr = radcube.GetChunkSNR(tsPy, No_Chunks=16)
        snr = GetSNR(tsPy, binlow=510)
        if snr < self.snrCutoffValue: #We only keep the "pretty" signals
          # continue ## Modify if you want noise only traces.
          #Make these zero
          for ibin in range(len(timeseries)):
            timeseries[ibin] = 0.
          outputFFT = dataclasses.FFTData(timeseries)
        else:
          chPassed+=1
          outputFFT = dataclasses.FFTData(timeseries)

        outputChMap[chkey] = dataclasses.I3AntennaChannel(outputFFT)

      if chPassed ==2: ## If both channel passed the snr cut only then store the antData
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
