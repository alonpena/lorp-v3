#!/bin/bash
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 0-2:30:0     
#SBATCH --mem=32768 
#SBATCH --constraint=EPYC_7262

solPath="output/solution_PR${original}_${inst}_VFX${VFX}_WA${WA}_RAD${radious}_L${length}.txt"



instPath="instances_LLRP/${inst}.dat"


./LLoRP "-results" ${solPath}  "-problemID" "0" "-WR" "1" "-WA" ${WA} "-Radius" ${radious} "-instance" ${instPath}  "-OF" ${OF} "-model" "1" "-length" ${length} "-original" ${original} "-VFX" ${VFX}

