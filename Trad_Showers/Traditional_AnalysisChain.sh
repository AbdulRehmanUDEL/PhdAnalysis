#!/bin/bash

#This script runs an instance of the Traditional_AnalysisChain 
export HDF5_USE_FILE_LOCKING=FALSE

HERE=$(dirname $(realpath -s $0))
BASEDIR=$HERE
## cvmfs
eval `/cvmfs/icecube.opensciencegrid.org/py3-v4.2.1/setup.sh`

#The exe and the environment
PYTHON_SCRIPT=/home/arehman/work/DeepAnalysis/submission-scripts/Traditional_AnalysisChain_Final.py
# ICETRAY_ENV=/home/arehman/work/Git/surface-array/build/env-shell.sh
ICETRAY_ENV=/home/arehman/work/Git/surface-array_updated/build/env-shell.sh
 

TAXIDIR22=/data/exp/IceCube/2022/unbiased/surface/V6/sae_data  #SAE files dir
# TAXIDIR21=/data/exp/IceCube/2021/unbiased/surface/V6/V6 ## SAE files dir

# ##################################################
TAXIFILES=""
for i in $(seq $1 $1); do
	TAXIFILES="$TAXIFILES $(ls -d $TAXIDIR22/SAE_data_${i}_1_IT.i3.gz)"
done
# ##################################################

# TAXIFILES=$TAXIDIR22/SAE_data_136580_1_IT.i3.gz  ## Test file

# echo $TAXIFILES

GCDFILE="/home/arehman/work/DeepAnalysis/SurveyGCDFile.i3.gz"
##################################################
Month="MayJune"
OutDir='/home/arehman/work/DeepAnalysis/ShowerSearch/RadioShowers/Final_Trad/Chunks16'

CALL="$ICETRAY_ENV $PYTHON_SCRIPT"
CALL="$CALL --input $TAXIFILES --output $OutDir/$Month/$1 --gcd $GCDFILE --month $Month"

# echo The exe call is $CALL
$CALL

echo "Script completed successfully"
