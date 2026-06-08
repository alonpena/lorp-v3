
	#for instance in c101  c102  c103  c104  c105  c106  c107  c108  c109  c201  c202  c203  c204  c205  c206  c207  c208  r101  r102  r103  r104  r105  r106  r107  r108  r109  r110  r110  r111  r112  r201  r202  r203  r204  r205  r206  r207  r208  r209  r210  r211  rc101 rc102 rc103 rc104 rc105 rc106 rc107 rc108 rc201 rc202 rc203 rc204 rc205 rc206 rc207 rc208

#	do
#		for size in 25 50 100
#		do 
#			
#										#awk '(NR <= 3) || (FNR > 3)' output_tradeoff/solution_solomon_${size}_${instance}*.csvBi_obj > sumaryresults.csv
#										 awk '(NR <= 13) || (FNR > 0)' output_tradeoff/solution_solomon_${size}_${instance}*.csvBi_obj > sumaryresults.csv
#		done
#	done



#!/bin/bash


# Output file
output_file="Lbs_new.txt"
> "$output_file"  # Clear the file at the beginning



#for model in  0 1 2 3
#do
#    for uncert in 0 1 2
#    do
#        for mean in 0
#        do 
#            for lambda in 0.0
#            do 
#                for alpha in 0.9 0.6 0.3 0.0
#                do
#
 #                   for scenarios in 10 20 30 40 50
 #                   do
 #                       for dist in uniform poisson
 #                       do 
 #                           for knap in 3 5 10
 #                           do
  #                              for inst in 20_25_1  20_50_1  20_75_1  25_25_1  25_50_1  25_75_1  30_25_1  30_50_1  30_75_1  35_25_1  35_50_1  35_75_1
  #                              do
  #                                  #for file in RAVSS/RAVSS_M${model}_${inst}_K${knap}_S${scenarios}_D${dist}_A${alpha}_M${mean}_L${lambda}_U${uncert}*.txt; do
  #                                       for file in RAVPI/RAVPI_M*.txt; do
  #                                      if [[ -f "$file" ]]; then
  #                                          cat "$file" >> "$output_file"
  #                                      fi
  #                                  done
  #                              done
#
#                            done
#                        done
#                    done
#                done
#            done
#        done
#    done
#done

                                    #for file in 01_RAVSS/RAVSS_M*.txt; do
                                     #   if [[ -f "$file" ]]; then
                                      #      cat "$file" >> "$output_file"
                                       # fi
                                    #done

                                    for file in output_LBs/solution_M1*.txt; do
                                        if [[ -f "$file" ]]; then
                                            cat "$file" >> "$output_file"
                                        fi
                                    done