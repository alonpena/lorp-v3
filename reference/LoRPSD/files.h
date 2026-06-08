//
// Created by alan on 20/07/21.
//
#include <sstream>
#include <cmath>
#include <stdlib.h>
#include <time.h>
#include <cstdlib>
#include <vector>
#include <functional>
#include <algorithm>
#include <fstream>
#include <string>
#include<iostream>
#include <gurobi_c++.h>

#ifndef FILES_H
#define FILES_H


using namespace std;

struct clusters {
    double demand = 0.0;
    vector<int>customers;
    double centroidx=0.0;
    double centroidy=0.0;
    double ratiocap=0.0;
    int ID=0;
    double distacl =0.0;
};

//in this struct I'll save the route of each vehicle
struct Routes {
    int ID=0;
    double demand = 0;
    vector<int>visits;
    double cost = 0;
    bool infeasibleR = false;
    double pen = 0;
    double totalcost = 0;
};



struct promisingconfig {
    vector<bool> a; //location
    vector<vector<bool>> all; //allocation
    int counter=0; //number of times selected
    vector<clusters> clu; //clusters
    double object=0; //objective function
    vector<vector<int>> trptours; //trptours
    vector<double> latencies;
    promisingconfig(vector<bool> i, vector<vector<bool>> j, double value, vector<clusters> cc,  vector<vector<int>>newtours, vector<double>newlatencies, int contb=1) {
        a = i;
        counter=contb;
        clu=cc;
        all=j;
        object=value;
        trptours=newtours;
        latencies=newlatencies;
    }
    bool operator==(const promisingconfig &b) const {
        //cout<<"a: " << this->a << "  ||  b.a: " << b.a <<endl;
        if (this->a == b.a){
            return true;
        }
        return false;
    }
};

struct Solution {
    string ID;
    vector<Routes>SolutionRoutes;
    vector<int>DepotsOpened;
    vector<double>pendepot;
    vector<double>demanddepot;
    vector<vector<int>>vehiclesperdepot; //routes asigned, if it is close the vector is empty
    double objectivefunction = 0;
    bool infeasibleSol = false;
    vector<bool>mybinaryY;
};

struct Customers {
    int ID=0;
    double x=0;
    double y=0;
    double q=0;
};

struct Depots {
    int ID=0;
    double x=0;
    double y=0;
    //bool status=0; //opened true, closed false
    double QD=0;
    double cost=0;
    //vector<int>vehicles; //routes asigned, if it is close the vector is empty
};



struct MetaParameters {
    int vns_shakes=0;
    double penalization = 0.0;
    double pen_original = 0.0;
    double penalizationDepots = 0.0;
    int max_iter = 0;
    int SearchType=0;
    int MyRandomSeed=0;
    int problemID=0; //0 if its CLLRP, 1 LLRP, 2 MDCCVRP
    int ConfigToEvaluate=1; // number of configurations to evaluate
    double max_RR=0.0;
    int ndc=0;
    int ndc_evaluate=10;
    int TryVNS=5;
    int TryVNS_SM=5;
    int samplemeta=50;
    double WR=1.0;
    double WA=1.5;
    double Radius=5;

    ////new
    int model=0;
    bool VFX = false;
    int OF=0;
    double lenghtMax=50;
    bool originalLoRP=false;

};

struct Parameters {
    double lenghtMax = 50;
    double WR = 1.0;
    double WA = 1.5;
    double Radius = 5; //original radius
    int R = 0;//vehicles
    double Q_original = 0;
    int N = 0;//customers
    int T = 0;//depots
    int V = 0;//nodes
    int f = 0; //depots to be opened
    double Q = 0; //vehicles capacity, homogeneous fleet
    int L = 0;
    int L_mdktrp = 0;
    int L_original = 0;
    vector<double> q;//clients demand original
    vector<double> cost;//depots cost original
    vector<double> DepC;//depots capacity original
    vector<vector<double>> dist; //distance
    vector<Customers> MyCustomers;
    vector<Depots> MyDepots;
    vector<double> worstd;//to calculate big M
    double BigM = 0;
    double vehiclesfixed = 0.0;
    double totaldemandinstance = 0;
    int originalvehicles = 0;
    string instance;
    MetaParameters MetaData;
    int problemID=0;
    double a=1.0;
    double b=0.0;

    ////new
    double penalty = 10000.0; // penalty for not serving a customer
    int Omega = 1;
    int facsize = 3;
    vector<vector<double>> dep_cost;//depots cost
    vector<vector<double>> dep_cap;//depots cost
    vector<vector<double>> demand;//customers stochastic demand
    int model = 0;
    bool VFX = false;
    int OF = 1;
    double maxdist = 0.0;
    bool originalLoRP=false;
    ////***

    string dist_name;
    vector<double> prob; // prob of each scenario
    double ALPHA=0.0;
    string shortname;


};

void ReadData(string &instance, Parameters & Data);

void ReadData_sizing(string &instance, Parameters & Data);

void ReadData_stoc(string &instance, Parameters & Data);

void ReadAlgorithmParams(int argc, char **argv, MetaParameters &MetaData, string &instance, string &results);

void Instance_Generator( string instance, Parameters&Data) ;

void GraphLLoRP(string graph, Parameters&Data, vector<vector<vector <bool>>> &Y, vector<vector <bool>> &Y0);
void GraphLLoRP_withRad(string graph, Parameters&Data, vector<vector<vector <bool>>> &Y, vector<vector <bool>> &Y0, vector<bool>&Z);
void Graph_TI(string graph, Parameters&Data, vector<vector<bool>>&X);
void GraphLLoRP_withRad_cost(string graph, Parameters&Data, vector<vector<bool>> &X, vector<vector <bool>> &Y0, vector<bool>&Z);

#endif //FILES_H