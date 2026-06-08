
#include <sstream>
#include <cmath>
#include <stdlib.h>
#include <time.h>
#include <cstdlib>
#include <vector>

#include <iostream>
#include <fstream>
#include <iterator>
#include <string>
#include <set>
#include <algorithm>

// Own libraries
#include "files.h"
#include "initial.h"


using namespace std;
#ifndef FUNCTIONS_H
#define FUNCTIONS_H


void change_Ins(Solution & MyCurrentSolution, Parameters Data, int i_ins, int j_ins, int r1_ins, int r2_ins, int i_pos_ins, int j_pos_ins);

void change_Swap(Solution & MyCurrentSolution, Parameters Data, int i_swap, int j_swap ,int r1_swap , int r2_swap , int i_pos_swap , int j_pos_swap);

void change_TwoOpt(Solution & MyCurrentSolution, Parameters Data, int i_twopt , int j_twopt , int k_twopt , int l_twopt , int r1_twopt , int r2_twopt , int i_pos_twopt , int j_pos_twopt, int k_pos_twopt , int l_pos_twopt, int rem_clients_j_twopt, int rem_clients_l_twopt);

void change_ArcSwap(Solution & MyCurrentSolution, Parameters Data ,int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best , int l_pos_best);

void change_Shift21(Solution & MyCurrentSolution, Parameters Data,int i_best, int j_best ,int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best);

void change_Ins_tsp(Routes & MyCurrentSolution, Parameters Data, int i_ins, int j_ins, int r1_ins, int r2_ins, int i_pos_ins, int j_pos_ins);

void change_Swap_tsp(Routes & MyCurrentSolution, Parameters Data, int i_swap, int j_swap ,int r1_swap , int r2_swap , int i_pos_swap , int j_pos_swap);

void change_TwoOpt_tsp(Routes & MyCurrentSolution, Parameters Data, int i_twopt , int j_twopt , int k_twopt , int l_twopt , int r1_twopt , int r2_twopt , int i_pos_twopt , int j_pos_twopt, int k_pos_twopt , int l_pos_twopt, int rem_clients_j_twopt, int rem_clients_l_twopt);

void change_ArcSwap_tsp(Routes & MyCurrentSolution, Parameters Data ,int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best , int l_pos_best);

void change_Shift21_tsp(Routes & MyCurrentSolution, Parameters Data,int i_best, int j_best ,int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best);

//this function calculate the latency on each route of a solution
double CalculateOF_pickup(Routes MyRoute, Parameters& Data);

void CalculateOF(Routes &MyRoute, Parameters& Data, MetaParameters & MetaData) ;

//this function calculate the latency on each route of a solution
double CalculateOF_delivery(Solution &mySolution, Routes &MyRoute, Parameters& Data, MetaParameters & Metadata) ;

//this function calculate the latency of a solution
void SolutionCost(Solution & MySolution, Parameters& Data);

//this function calculates the penalization of each route
double CalculatePenal(Routes MyRoute, Parameters& Data, MetaParameters& MetaData);

//this function calculates the total costo (latency+penalization) of each route
double CalculateTotalCost(Routes MyRoute, Parameters& Data);

//this function calculates the total demand of each route
double CalculateDemand(Routes MyRoute, Parameters& Data);

//this function proves feasibility on each route of my solution
bool RouteFeasibility(Routes &MyRoute, Parameters& Data);

//this function saves a txt file with the beavior of algorithm
void SaveMetastatistics(string &Metabehavior, double temperature, Solution &BestFR, Solution &BestR, Solution &Curre);

//this function verifies feasibility of solution
bool SolutionFeasibility(Solution & MySolution, Parameters& Data);

//this function counts the number of improvements by each neighborhood
void StatisticResults(int twoOpt, int sswap, int arcsswap, int insertion, int shift21,  int twoOptSA, int sswapSA, int insertionSA, int depotExSA, int depotOpClSA, int depotInsSA);



#endif
