#include "gurobi_c++.h"
#include <sstream>
#include <cmath>
#include <stdlib.h>
#include <time.h>
#include <cstdlib>
#include <vector>
#include <functional>
#include <algorithm>
#include <omp.h>
#include <string>
#include <iostream>
#include <fstream>
#include <list>
#include<tuple>

#include "initial.h"


using namespace std;

// Own libraries
#include "files.h"

#include "models.h"
#include "stcmodels.h"


bool sorterlat(double a, double b) {
    return a < b;
}

bool demandsorter(double a, double b) {
    return a < b;
}

void llrpopt(string instance, double & latencyopt, double &lr, double &ur){
    if (instance== "instances_LLRP/coord20-5-1.dat"){
        
        latencyopt=330.00;
        lr=3.0;
        ur=20.0;
    }
    else{
        if (instance== "instances_LLRP/coord20-5-1b.dat"){
            
            latencyopt=608.06;
            lr=5.0;
            ur=40.0;
        }
        else{
            if (instance== "instances_LLRP/coord20-5-2.dat"){
                
                latencyopt=301.97;
                lr=3.0;
                ur=20.0;
            }
            else{
                if (instance== "instances_LLRP/coord20-5-2b.dat"){
                    
                    latencyopt=486.55;
                    lr=3.0;
                    ur=30.0;
                }
                else{
                    if (instance== "instances_LLRP/coord50-5-1.dat"){
                        
                        latencyopt=843.94;
                        lr=3.0;
                        ur=20.0;
                    }
                    else{
                        if (instance== "instances_LLRP/coord50-5-1b.dat"){
                            
                            latencyopt=1293.46;
                            lr=3.0;
                            ur=40.0;
                        }
                        else{

                            if (instance== "instances_LLRP/coord50-5-2.dat"){
                                
                                latencyopt=684.13;
                                lr=3.0;
                                ur=20.0;
                            }
                            else{
                                if (instance== "instances_LLRP/coord50-5-2b.dat"){
                                    
                                    latencyopt=953.25;
                                    lr=3.0;
                                    ur=20.0;
                                }
                                else{

                                    if (instance== "instances_LLRP/coord50-5-2BIS.dat"){
                                        
                                        latencyopt=945.45;
                                        lr=3.0;
                                        ur=30.0;
                                    }
                                    else{
                                        if (instance== "instances_LLRP/coord50-5-2bBIS.dat"){
                                            
                                            latencyopt=803.90;
                                            lr=3.0;
                                            ur=30.0;
                                        }
                                        else{
                                            if (instance== "instances_LLRP/coord50-5-3.dat"){
                                                
                                                latencyopt=831.57;
                                                lr=3.0;
                                                ur=20.0;
                                            }
                                            else{
                                                if (instance== "instances_LLRP/coord50-5-3b.dat"){
                                                    
                                                    latencyopt=1101.57;
                                                    lr=3.0;
                                                    ur=30.0;
                                                }
                                                else{
                                                    if (instance== "instances_LLRP/coordChrist_50_5.dat"){
                                                        
                                                        latencyopt=1661.64;
                                                        lr=3.0;
                                                        ur=35.0;
                                                    }
                                                    else{
                                                        if (instance== "instances_LLRP/coordGaskell_21_5.dat"){
                                                            
                                                            latencyopt=653.48;
                                                            lr=5.0;
                                                            ur=30.0;
                                                        }
                                                        else{
                                                            if (instance== "instances_LLRP/coordGaskell_29_5.dat"){
                                                                
                                                                latencyopt=1199.33;
                                                                lr=5.0;
                                                                ur=40.0;
                                                            }
                                                            else{
                                                                if (instance== "instances_LLRP/coordGaskell_32_5b.dat"){
                                                                    
                                                                    latencyopt=1552.84;
                                                                    lr=5.0;
                                                                    ur=50.0;
                                                                }
                                                                else{
                                                                    if (instance== "instances_LLRP/coordGaskell_36_5.dat"){
                                                                        
                                                                        latencyopt=1627.17;
                                                                        lr=3.0;
                                                                        ur=20.0;
                                                                    }
                                                                    else{
                                                                        if (instance== "instances_LLRP/coordMin_27_5.dat"){
                                                                            
                                                                            latencyopt=5387.55;
                                                                            lr=30.0;
                                                                            ur=180.0;
                                                                        }
                                                                        else{
                                                                            cout<<"not found";
                                                                        }
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }

                                        }

                                    }
                                }
                            }
                        }
                    }
                }
            }

        }

    }
}

void scaledistance(Parameters& Data){
    //filling the distance matrix
    Data.maxdist=0.0;
    Data.dist.resize(Data.V);
    Data.worstd.resize(Data.V);
    for (int i = 0; i < Data.V; ++i) {
        Data.dist[i].resize(Data.V);
        Data.worstd[i] = 0;
        for (int j = 0; j < Data.V; ++j) {
            if (i < Data.T) {
                if (j < Data.T) {
                    Data.dist[i][j] = (sqrt(pow(Data.MyDepots[i].x - Data.MyDepots[j].x, 2)
                                            + pow(Data.MyDepots[i].y - Data.MyDepots[j].y, 2)));
                }
                else {
                    Data.dist[i][j] = (sqrt(pow(Data.MyDepots[i].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                            + pow(Data.MyDepots[i].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2)));
                }

            }
            else {
                if (j < Data.T) {
                    Data.dist[i][j] = (sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyDepots[j].x, 2)
                                            + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyDepots[j].y, 2)));
                }
                else {
                    Data.dist[i][j] = (sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                            + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2)));
                }
            }
            if (Data.dist[i][j] > Data.worstd[i]) Data.worstd[i] = Data.dist[i][j];
            if (Data.dist[i][j]>Data.maxdist) Data.maxdist=Data.dist[i][j];
            //cout << "dist[" << i + 1 << "]" << "[" << j + 1 << "]" << Data.dist[i][j] << endl;
        }
    }


    if (Data.problemID==0){
        //// scaling used by Arslan
        for (int i = 0; i < Data.V; ++i) {
            Data.worstd[i]=Data.worstd[i]*100/Data.maxdist;
            for (int j = 0; j < Data.V; ++j) {
                Data.dist[i][j]=Data.dist[i][j]*(100/Data.maxdist);
            }
        }
        Data.vehiclesfixed=Data.vehiclesfixed*Data.VFX;
    }
    else{
        //// scaling used by Prodhon
        for (int i = 0; i < Data.V; ++i) {
            Data.worstd[i]=1.0*int(ceil(Data.worstd[i]*100));
            for (int j = 0; j < Data.V; ++j) {
                Data.dist[i][j]=1.0*int(ceil(Data.dist[i][j]*100));
            }
        }

        for (int i = 0; i < Data.T; ++i) {
            for (int j = 0; j < Data.facsize; ++j) {
                //Data.dep_cost[i][j]=1.0*int(Data.dep_cost[i][j]);
                Data.dep_cost[i][j]=1.0*round(Data.dep_cost[i][j]);
                cout<<"size= " << j+1 << " | cap: " << Data.dep_cap[i][j]<< " | cost: " <<Data.dep_cost[i][j] <<endl;
            }
        }
    }




    //Big M
    Data.BigM = 0;
    for (int i = 0; i < Data.V; i++)
    {
        Data.BigM += Data.worstd[i];
        //	cout << " Worst[" << i + 1 << "] =" << Data.worstd[i] << endl;
    }


}

int main(int argc, char** argv) {
    cout << "-- Benders LLRP build " << __DATE__ << " " << __TIME__ << std::endl;
    //cout.setf(std::ios_base::fixed);

    //strings
    string instance;
    string results;




    ///////reading alg. params////////
    MetaParameters MetaData;


    ReadAlgorithmParams(argc, argv, MetaData, instance, results);


    //////read instance//////
    Parameters Data;

    Data.WR=MetaData.WR;
    Data.WA=MetaData.WA;
    Data.Radius=MetaData.Radius;
    Data.lenghtMax=MetaData.lenghtMax;
    Data.model=MetaData.model;
    Data.VFX= MetaData.VFX; //vehicles fixed cost
    Data.OF=1; //always cost
    Data.problemID=MetaData.problemID;
    Data.originalLoRP=MetaData.originalLoRP;

    ReadData_sizing(instance, Data);
    //Instance_Generator(instance, Data);

    //ReadData_stoc(instance, Data);

    //exit(0);


    /// scale the matrix (if necessary)
   if(Data.problemID<2) scaledistance(Data); // 0: Arslan, 1: Prodhon LRP (int), 2: Akca instances for LRP (no scaling)


    ///// deterministic model /////
    double getobjective=0.0;

    if (Data.originalLoRP==1)   createmodelnew(instance, Data, results, getobjective); // standard LoRP
    else  create_detLoRP_sizing(instance, Data, results, getobjective); // LoRP-FSD

    //create_LRPDSD(instance, Data, results, getobjective); // LRP-FSD (ITOR)


    //// stoc model /// (this is not working yet)
    //createstc(instance, Data, results, getobjective);


///// From here I'm trying to do a heuristic for depot selection (not ready yet)/////
///
///
   /*
    // create the initial depot configurations
    vector<promisingconfig>myconfigurations;
    Solution MyInitial;
    vector<Solution> Start;
    vector<double> z_hat;
    z_hat.resize(Data.T);

    InitialZ_hat(instance, MetaData, "1", Data, z_hat, myconfigurations,MyInitial, Start);

    for (int i = 0; i < Start.size(); ++i) {
        cout<<"Solution Initial n° " << i+1 << "  |||   OF ="<< Start[i].objectivefunction << endl;
        for (int j = 0; j <Start[i].SolutionRoutes.size() ; ++j) {
            for (int k = 0; k <Start[i].SolutionRoutes[j].visits.size() ; ++k) {
                cout<<" - " << Start[i].SolutionRoutes[j].visits[k] ;
            }
            cout<< endl;
        }
    }

    for (int i = 0; i < Start.size(); ++i) {
        cout<<"Solution n° " << i+1 << "  |||   infeasible? ="<< SolutionFeasibility(Start[i], Data) << endl;
    }

    //exit(0);


    cout<<"Objective function main : "<< Start[0].objectivefunction<<endl;

    // set the penalization
    MetaData.penalization=0.1*Start[0].objectivefunction/100;
    MetaData.penalizationDepots=0.1*Start[0].objectivefunction/100;
    cout<<"pen vehic: " <<  MetaData.penalization<< endl;
    cout<<"pen depot: " <<  MetaData.penalizationDepots<< endl;


    Solution MyMetaSolution=Start[0];
    Solution BestSolution =Start[0];
    Solution BestFeasibleSolution=Start[0];
*/



    cout<<"finished"<<endl;
    return 0;

}

