//
// Created by alan on 2/27/26.
//

#ifndef LORPSD_INITIAL_H
#define LORPSD_INITIAL_H

#include <string>
#include "files.h"
#include "functions.h"
//#include "hybrid.h"


////// declare the structure for splits/////
struct splits {
    double largestedges=-1;
    int poselementsi=-1;
    double besttaillatency=-MAXFLOAT;
    //double gainreverse=-MAXFLOAT;
    double bestgain=-MAXFLOAT;
    int newdemandhead=0;
    int newdemandtail=0;
    int ID=0;
    vector<int>trp_head;
    //vector<int>trp_tail1;
    //vector<int>trp_tailreverse;
    vector<int>besttailvector;
    bool isthesamedepot_tail_st=1;
    int selecteddepot_tail=-1;
    bool besttypeoftail=0;
    bool evaluateit=1;
    double latency_head=0.0;
};

/*
struct auxroutesxdepots{
    int depot;
    int routes;
};*/

bool ratiodemandcomparation(clusters a, clusters b);

bool profitcomparation(splits a, splits b);


void InitialZ_hat(string instance, MetaParameters &MetaData, string seed, Parameters &Data, vector<double> &z_hat, vector<promisingconfig> &myconfigurations,  Solution & MyInitial, vector<Solution>&Start);

void MIPZ_hat(GRBEnv &env,  Parameters Data, MetaParameters MetaData,  vector<double> &z_hat, vector<clusters> &myclusters, vector<vector<bool>>&allocation,
              vector<bool>&location, vector<vector<GRBVar>> &X, vector<GRBVar> &Y,  vector<vector<int>>& myselectedtrptours, vector<double>&trplatencys, vector<vector<double>>&bestdistcltodep,  vector<vector<vector<int>>>&mybesttrptours,  vector<double>&mysolutionmatrix, double & objfunct);

void MIPZ_alternatives(int itera, GRBEnv &env, Parameters Data, MetaParameters MetaData,  vector<double> &z_hat, vector<clusters> &myclusters, vector<vector<bool>>&allocation,
                       vector<bool>&location,vector<vector<GRBVar>> &X, vector<GRBVar> &Y,  vector<vector<int>>& myselectedtrptours, vector<double>&trplatencys, vector<vector<double>>&bestdistcltodep,  vector<vector<vector<int>>>&mybesttrptours,  vector<double>&mysolutionmatrix, double & objfunct);

void LKH_ccvrp(Parameters & Data, MetaParameters MetaData, string & instance, string seed_var, Solution & MyInitial_LKH, vector<vector<bool>>&allocation, vector<clusters>myclusters, int depot);

void LKH_gianttour(Parameters & Data, MetaParameters MetaData, string & instance, string seed_var,vector<int> &gianttour);

void Clustering(Parameters &Data,string & instance, string seed, int pos, vector<clusters> &myclusters,  vector<int>gianttour, bool & feasible);

bool Insertion_TSP(Parameters& Data, MetaParameters MetaData, Routes&tsptour, double & cost);

bool Swap_TSP(Parameters& Data, MetaParameters MetaData, Routes&tsptour, double & cost);

bool TwoOpt_TSP(Parameters& Data, MetaParameters MetaData, Routes&tsptour, double & cost);

bool ArcSwapIntra_TSP(Parameters& Data, MetaParameters MetaData, Routes& MyCurrentSolution, double & cost);

bool Shift21Intra_TSP(Parameters& Data, MetaParameters MetaData, Routes& MyCurrentSolution, double & cost);

void splitting_New(Parameters & Data, vector<clusters> &myclusters);



#endif //LORPSD_INITIAL_H