//
// Created by alan on 11/12/25.
//
#include "gurobi_c++.h"
#include <sstream>
#include <cmath>
#include <stdlib.h>
#include <time.h>
#include <cstdlib>
#include <vector>
//// Own libraries
#include "files.h"
using namespace std;

#ifndef LORPSD_STCMODELS_H
#define LORPSD_STCMODELS_H


void LoRPSD_2IF(string instance, int obj, string &results, GRBEnv &env, Parameters &Data,  vector<vector<GRBVar>>&Y, vector<vector<GRBVar>>&V, vector<vector<GRBVar>>&NSC,  vector<vector<vector<GRBVar>>>&X, vector<vector<vector<GRBVar>>> &W, vector<vector<vector<GRBVar>>> &f, vector<vector<vector<GRBVar>>>&A,  vector<vector<vector<GRBVar>>> &NC, vector<vector<vector<GRBVar>>> &t, vector<vector<vector<bool>>>&X_graph, vector<vector<vector<bool>>>&A_graph, vector<bool>&Z_graph) ;
void createstc(string instance, Parameters &Data, string &results, double &of);

void create_LRPDSD(string instance, Parameters &Data, string &results, double &of);

void create_detLoRP_sizing(string instance, Parameters &Data, string &results, double &of);

#endif //LORPSD_STCMODELS_H
