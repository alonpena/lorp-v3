#!/bin/bash

module load gcc/latest
module load gurobi/11.0
module load ilog/22.1

for original in 0 1
do

for model in   1
do
	for OF in 1
	do
		for WA in 0 
		#for WA in 0  0.5 1
		do 
			for WR in 1
			do 
				#for radious in 0 10 20 30 40 50 
				for radious in 50 
				do
					#for length in 100 125 150
					for length in 150
					do
						for VFX in 0
						#for LP in 0 1
						do 
								#for inst in coord20-5-1  coord20-5-1b  coord20-5-2 coord20-5-2b coordGaskell_21_5 coordGaskell_29_5 coordGaskell_32_5b  coordGaskell_36_5 coordMin_27_5 coordChrist_50_5 coordChrist_75_10 coord50-5-1 coord50-5-1b  coord50-5-2 coord50-5-2b  coord50-5-2BIS  coord50-5-2bBIS coord50-5-3 coord50-5-3b  coord100-5-1  coord100-5-1b coord100-5-2  coord100-5-2b coord100-5-3  coord100-5-3b coord100-10-1 coord100-10-1b  coord100-10-2 coord100-10-2b coord100-10-3  coord100-10-3b  coordChrist_100_10  
								#for inst in coord20-5-1  coord20-5-1b  coord20-5-2 coord20-5-2b coord50-5-1 coord50-5-1b  coord50-5-2 coord50-5-2b coord50-5-3 coord50-5-3b   r30x5a-1	r30x5a-2	r30x5a-3	r30x5b-1	r30x5b-2	r30x5b-3	r40x5a-1	r40x5a-2	r40x5a-3	r40x5b-1	r40x5b-2	r40x5b-3
								for inst in coord20-5-1  
									do
									jobName="PR${original}_${inst}_WA${WA}_RAD${radious}_L${length}_VFX${VFX}"
									export inst
									export model
									export OF
									export WA
									export WR
									export radious
									export length
									export VFX
									export original
									echo Submitting Job $jobName
									mkdir -p output/
									mkdir -p output/logs
									sbatch -J $jobName -o output/logs/$jobName.out -e output/logs/$jobName.err startJob.sh
								done		
						done
					done
				done
			done
		done
	done
done
done





