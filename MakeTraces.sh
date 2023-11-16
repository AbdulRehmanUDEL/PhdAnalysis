#!/bin/bash

eval `/cvmfs/icecube.opensciencegrid.org/py3-v4.2.1/setup.sh`

HERE=$(dirname $(realpath -s $0))

TAXIDIR22=/data/exp/IceCube/2022/unbiased/surface/V6/radio_temp/i3_files ## location of Radio data files

SIMDIR1=/data/sim/IceCubeUpgrade/CosmicRay/Radio/coreas/data/continuous/star-pattern/proton ## location of proton sim
SIMDIR2=/data/sim/IceCubeUpgrade/CosmicRay/Radio/coreas/data/continuous/star-pattern/iron ##  location of iron sim
SIMDIR3=/data/sim/IceCubeUpgrade/CosmicRay/Radio/coreas/data/continuous/star-pattern/helium ##  location of helium sim
SIMDIR4=/data/sim/IceCubeUpgrade/CosmicRay/Radio/coreas/data/continuous/star-pattern/oxygen ##  location of oxygen sim

PYTHONSCP=$HERE/MakeTraces.py

# INPUT=$(ls -d $SIMDIR1/lgE_17.0/sin2_0.8/?????${1})

INPUT=""
for ZEN in {2..8}; do ## uncomment this
  INPUT="$INPUT $(ls -d $SIMDIR1/lgE_17.2/sin2_0.${ZEN}/?????${1} $SIMDIR1/lgE_17.3/sin2_0.${ZEN}/?????${1} $SIMDIR1/lgE_17.4/sin2_0.${ZEN}/?????${1}\
   $SIMDIR2/lgE_17.3/sin2_0.${ZEN}/?????${1} $SIMDIR2/lgE_17.4/sin2_0.${ZEN}/?????${1} $SIMDIR2/lgE_17.5/sin2_0.${ZEN}/?????${1} $SIMDIR2/lgE_17.6/sin2_0.${ZEN}/?????${1} $SIMDIR2/lgE_17.7/sin2_0.${ZEN}/?????${1})"
done

num_files=$(echo $INPUT | wc -w)
echo $num_files ## echos total number of files in the INPUT
 
# TAXIFILES=$(ls $TAXIDIR22/*2022-02-?${1}*.i3.gz)
TAXIFILES=$(ls $TAXIDIR22/*2022-05-?${1}*.i3.gz $TAXIDIR22/*2022-06-?${1}*.i3.gz)

num_TAXI_files=$(echo $TAXIFILES | wc -w)
echo $num_TAXI_files ## echos total number of files in the TAXIFILES


ICETRAY_ENV=/home/arehman/work/Git/surface-array_updated/build/env-shell.sh

$ICETRAY_ENV $PYTHONSCP --taxi $TAXIFILES --output Run${1} --input $INPUT
