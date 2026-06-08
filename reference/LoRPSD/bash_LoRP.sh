#!/bin/bash


instance=( "Exp10x3-b" "Exp10x3-a" "Exp8x3-b" "Exp8x3-a" "Exp5x3-b" "Exp5x3-a" "coord20-5-1"  "coord20-5-1b"  "coord20-5-2" "coord20-5-2b" "coordGaskell_21_5" "coordGaskell_29_5" "coordGaskell_32_5b"  "coordGaskell_36_5" "coordMin_27_5" "coord50-5-1" "coord50-5-1b"  "coord50-5-2" "coord50-5-2b" "coord50-5-3" "coord50-5-3b"   "r30x5a-1" "r30x5a-2"  "r30x5a-3"  "r30x5b-1"  "r30x5b-2"  "r30x5b-3"  "r40x5a-1"  "r40x5a-2"  "r40x5a-3"  "r40x5b-1"  "r40x5b-2"  "r40x5b-3")



process() {

#seed=("4017"	"9347"	"3553"	"9773"	"2283"	"4496"	"3934"	"5079"	"8885"	"7274"	"3062"	"455"	"1446"	"6734"	"4800"	"2424"	"8514"	"1151"	"212"	"8415"	"5076"	"850"	"4008"	"859"	"9858"	"3908"	"4897"	"7445"	"8590"	"7702")
#seed=("4017"	"9347"	"3553"	"9773"	"2283")
seed=("455")
  for s in "${seed[@]}"
  do


# -----------------model--------------
./LoRPSD "-instance" instances_LLRP/$1".dat" "-results" "results_llorp.txt"  "-problemID" "2" "-WR" "1" "-WA" "6" "-Radius" "0" "-LPREL" "0" "-OF" "1" "-model" "1" "-length" "20000" >&output/$1"_"$s"_TRASH_models_m3_s10.txt" 



  done


}


export -f process


printf "%s\n" "${instance[@]}" | xargs -i -n 1 -P 1 bash -c 'process {}'
#1-3


