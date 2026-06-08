//
// Created by aroso on 06-05-2021.
//

#include "functions.h"


using namespace std;

void change_Ins(Solution & MyCurrentSolution, Parameters Data, int i_ins, int j_ins, int r1_ins, int r2_ins, int i_pos_ins, int j_pos_ins)
{
    //cout << "best insertion: " << delta_best_final << endl;
    //update routes (vectors)
    auto iter2 = begin(MyCurrentSolution.SolutionRoutes[r2_ins].visits) + j_pos_ins;
    //cout << "it1 best fuera marca: " << *iter1 << endl;
    //cout << "it2 best fuera marca: " << *iter2 << endl;
    //cout << "posicion de i best: " << i_pos_best << endl;
    //cout << "posicion de j best: " << j_pos_best << endl;

    if (r1_ins == r2_ins) {
        if (i_pos_ins < j_pos_ins) {
            MyCurrentSolution.SolutionRoutes[r2_ins].visits.insert(iter2, i_ins);
            //cout << "insertion ok: " << endl;
            auto iter1 = begin(MyCurrentSolution.SolutionRoutes[r1_ins].visits) + i_pos_ins;
            MyCurrentSolution.SolutionRoutes[r1_ins].visits.erase(iter1);
            //cout << "erase ok: " << endl;
        }
        else {
            MyCurrentSolution.SolutionRoutes[r2_ins].visits.insert(iter2, i_ins);
            //cout << "insertion ok: " << endl;
            auto iter1b = begin(MyCurrentSolution.SolutionRoutes[r1_ins].visits) + i_pos_ins + 1;
            MyCurrentSolution.SolutionRoutes[r1_ins].visits.erase(iter1b);
            //cout << "erase ok: " << endl;
        }


    }
    else {
        auto iter1 = begin(MyCurrentSolution.SolutionRoutes[r1_ins].visits) + i_pos_ins;
        MyCurrentSolution.SolutionRoutes[r1_ins].visits.erase(iter1);
        //cout << "erase ok: " << endl;
        MyCurrentSolution.SolutionRoutes[r2_ins].visits.insert(iter2, i_ins);
        //cout << "insertion ok: " << endl;

    }


}

void change_Swap(Solution & MyCurrentSolution, Parameters Data, int i_swap, int j_swap ,int r1_swap , int r2_swap , int i_pos_swap , int j_pos_swap)
{
    //cout << "best swap" << endl;
    //update routes (vectors)
    auto iter1 = begin(MyCurrentSolution.SolutionRoutes[r1_swap].visits) + i_pos_swap;
    auto iter2 = begin(MyCurrentSolution.SolutionRoutes[r2_swap].visits) + j_pos_swap;
    //cout << "it1 best fuera marca: " << *iter1 << endl;
    //cout << "it2 best fuera marca: " << *iter2 << endl;
    swap(*iter1, *iter2);

}

void change_ArcSwap(Solution & MyCurrentSolution, Parameters Data, int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best , int l_pos_best)
{
    auto iter1i = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + i_pos_best;
    auto iter1j = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + j_pos_best;
    auto iter2k = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
    auto iter2l = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + l_pos_best;
    //cout << "it1 i best fuera marca: " << *iter1i << endl;
    //cout << "it1 j best fuera marca: " << *iter1j << endl;
    //cout << "it2 k best fuera marca: " << *iter2k << endl;
    //cout << "it2 l best fuera marca: " << *iter2l << endl;
    swap(*iter1i, *iter2k);
    swap(*iter1j, *iter2l);

}

void change_Shift21(Solution & MyCurrentSolution, Parameters Data,int i_best, int j_best ,int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best){
    //auto iter1i = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + i_pos_best;
    //auto iter2k = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
    //swap(*iter1i, *iter2k);
    //cout << "swap ok: " << endl;

    if(r1_best==r2_best){
        /*
        cout<<"Solution before applying the move"  << endl;
        for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
            for (int k = 0; k <MyCurrentSolution.SolutionRoutes[j].visits.size() ; ++k) {
                cout<<" - " << MyCurrentSolution.SolutionRoutes[j].visits[k] ;
            }
            cout<< endl;
        }*/

        //auto iter2aux = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
        //cout<< " i= " << i_best << " |  j= " <<j_best << " |  k= " << *iter2aux << endl;


        if (j_pos_best < k_pos_best) {
            //cout << "case  j<k: " << endl;

            auto iter1j = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + j_pos_best;
            auto iter2k = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
            swap(*iter1j, *iter2k);


            MyCurrentSolution.SolutionRoutes[r2_best].visits.insert(iter2k, i_best);

            auto iter1 = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + i_pos_best ;
            MyCurrentSolution.SolutionRoutes[r1_best].visits.erase(iter1);


            //cout << "erase ok: " << endl;
        }
        else {
            //cout << "case  2, j>k: " << endl;

            auto iter1i = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + i_pos_best;
            auto iter2k = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
            swap(*iter1i, *iter2k);


            MyCurrentSolution.SolutionRoutes[r2_best].visits.insert(iter2k+1, j_best);
            //cout << "insertion ok: " << endl;
            auto iter1b = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + j_pos_best + 1;
            MyCurrentSolution.SolutionRoutes[r1_best].visits.erase(iter1b);
            //cout << "erase ok: " << endl;
        }
        /*
        cout<<"Solution after applying the move"  << endl;
        for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
            for (int k = 0; k <MyCurrentSolution.SolutionRoutes[j].visits.size() ; ++k) {
                cout<<" - " << MyCurrentSolution.SolutionRoutes[j].visits[k] ;
            }
            cout<< endl;
        }
        //getchar();
         */

    }
    else{
        auto iter1i = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + i_pos_best;
        auto iter2k = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
        swap(*iter1i, *iter2k);
        auto iter1j = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + j_pos_best;
        //cout << "j iterador: " << *iter1j << endl;
        MyCurrentSolution.SolutionRoutes[r1_best].visits.erase(iter1j);
        //cout << "erase ok: " << endl;
        auto iter2kb = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best + 1;
        MyCurrentSolution.SolutionRoutes[r2_best].visits.insert(iter2kb, j_best);
    }


}

void change_TwoOpt(Solution & MyCurrentSolution, Parameters Data, int i_twopt , int j_twopt , int k_twopt , int l_twopt , int r1_twopt , int r2_twopt , int i_pos_twopt , int j_pos_twopt, int k_pos_twopt , int l_pos_twopt, int rem_clients_j_twopt, int rem_clients_l_twopt)
{


    //update routes (vectors)

    //if r1 = r2 reverse the route
    if (r1_twopt == r2_twopt) {
        auto iter1j = begin(MyCurrentSolution.SolutionRoutes[r1_twopt].visits) + j_pos_twopt;
        auto iter2k = begin(MyCurrentSolution.SolutionRoutes[r2_twopt].visits) + k_pos_twopt;
        //cout << "it1 j best fuera marca: " << *iter1j << endl;
        //cout << "it2 k best fuera marca: " << *iter2k << endl;
        reverse(iter1j, iter2k + 1);
    }

        //for different routes
    else {
        int x = 0;
        //swap routes while size is the same
        while (true) {

            auto iter1j = begin(MyCurrentSolution.SolutionRoutes[r1_twopt].visits) + j_pos_twopt + x;
            auto iter2l = begin(MyCurrentSolution.SolutionRoutes[r2_twopt].visits) + l_pos_twopt + x;
            if (j_pos_twopt + x == MyCurrentSolution.SolutionRoutes[r1_twopt].visits.size() - 1 ||
                l_pos_twopt + x == MyCurrentSolution.SolutionRoutes[r2_twopt].visits.size() - 1) break;
            swap(*iter1j, *iter2l);
            //cout << "it1 j best en el while marca: " << *iter1j << endl;
            //cout << "it2 k best en el while marca: " << *iter2l << endl;

            x++;
        }
        //cout << "isalí del while" << endl;
        x = 0;
        //if route 2 is longer than 1
        if (rem_clients_j_twopt < rem_clients_l_twopt) {
            auto iter2l = end(MyCurrentSolution.SolutionRoutes[r2_twopt].visits) - 1 - (rem_clients_l_twopt - rem_clients_j_twopt);
            MyCurrentSolution.SolutionRoutes[r1_twopt].visits.insert(MyCurrentSolution.SolutionRoutes[r1_twopt].visits.end() - 1, iter2l, MyCurrentSolution.SolutionRoutes[r2_twopt].visits.end() - 1);
            MyCurrentSolution.SolutionRoutes[r2_twopt].visits.erase(iter2l, MyCurrentSolution.SolutionRoutes[r2_twopt].visits.end() - 1);
        }

        //if route 1 is longer than 2
        if (rem_clients_j_twopt > rem_clients_l_twopt) {
            auto iter1j = end(MyCurrentSolution.SolutionRoutes[r1_twopt].visits) - 1 + (rem_clients_l_twopt - rem_clients_j_twopt);
            MyCurrentSolution.SolutionRoutes[r2_twopt].visits.insert(MyCurrentSolution.SolutionRoutes[r2_twopt].visits.end() - 1, iter1j, MyCurrentSolution.SolutionRoutes[r1_twopt].visits.end() - 1);
            MyCurrentSolution.SolutionRoutes[r1_twopt].visits.erase(iter1j, MyCurrentSolution.SolutionRoutes[r1_twopt].visits.end() - 1);
            //while (iter1j != MyCurrentSolution.SolutionRoutes[r1_twopt].visits.end - 1) {

            //}
        }

    }


}

void change_Ins_tsp(Routes & MyCurrentSolution, Parameters Data, int i_ins, int j_ins, int r1_ins, int r2_ins, int i_pos_ins, int j_pos_ins)
{
    //cout << "best insertion: " << delta_best_final << endl;
    //update routes (vectors)
    auto iter2 = begin(MyCurrentSolution.visits) + j_pos_ins;
    //cout << "it1 best fuera marca: " << *iter1 << endl;
    //cout << "it2 best fuera marca: " << *iter2 << endl;
    //cout << "posicion de i best: " << i_pos_best << endl;
    //cout << "posicion de j best: " << j_pos_best << endl;

    if (i_pos_ins < j_pos_ins) {
        MyCurrentSolution.visits.insert(iter2, i_ins);
        //cout << "insertion ok: " << endl;
        auto iter1 = begin(MyCurrentSolution.visits) + i_pos_ins;
        MyCurrentSolution.visits.erase(iter1);
        //cout << "erase ok: " << endl;
    }
    else {
        MyCurrentSolution.visits.insert(iter2, i_ins);
        //cout << "insertion ok: " << endl;
        auto iter1b = begin(MyCurrentSolution.visits) + i_pos_ins + 1;
        MyCurrentSolution.visits.erase(iter1b);
        //cout << "erase ok: " << endl;
    }


}

void change_Swap_tsp(Routes & MyCurrentSolution, Parameters Data, int i_swap, int j_swap ,int r1_swap , int r2_swap , int i_pos_swap , int j_pos_swap)
{
    //cout << "best swap" << endl;
    //update routes (vectors)
    auto iter1 = begin(MyCurrentSolution.visits) + i_pos_swap;
    auto iter2 = begin(MyCurrentSolution.visits) + j_pos_swap;
    //cout << "it1 best fuera marca: " << *iter1 << endl;
    //cout << "it2 best fuera marca: " << *iter2 << endl;
    swap(*iter1, *iter2);

}

void change_ArcSwap_tsp(Routes & MyCurrentSolution, Parameters Data ,int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best , int l_pos_best)
{
    auto iter1i = begin(MyCurrentSolution.visits) + i_pos_best;
    auto iter1j = begin(MyCurrentSolution.visits) + j_pos_best;
    auto iter2k = begin(MyCurrentSolution.visits) + k_pos_best;
    auto iter2l = begin(MyCurrentSolution.visits) + l_pos_best;
    //cout << "it1 i best fuera marca: " << *iter1i << endl;
    //cout << "it1 j best fuera marca: " << *iter1j << endl;
    //cout << "it2 k best fuera marca: " << *iter2k << endl;
    //cout << "it2 l best fuera marca: " << *iter2l << endl;
    swap(*iter1i, *iter2k);
    swap(*iter1j, *iter2l);

}

void change_TwoOpt_tsp(Routes & MyCurrentSolution, Parameters Data, int i_twopt , int j_twopt , int k_twopt , int l_twopt , int r1_twopt , int r2_twopt , int i_pos_twopt , int j_pos_twopt, int k_pos_twopt , int l_pos_twopt, int rem_clients_j_twopt, int rem_clients_l_twopt)
{

    auto iter1j = begin(MyCurrentSolution.visits) + j_pos_twopt;
    auto iter2k = begin(MyCurrentSolution.visits) + k_pos_twopt;
    //cout << "it1 j best fuera marca: " << *iter1j << endl;
    //cout << "it2 k best fuera marca: " << *iter2k << endl;
    reverse(iter1j, iter2k + 1);

}

void change_Shift21_tsp(Routes & MyCurrentSolution, Parameters Data,int i_best, int j_best ,int r1_best , int r2_best , int i_pos_best , int j_pos_best, int k_pos_best){
    //auto iter1i = begin(MyCurrentSolution.SolutionRoutes[r1_best].visits) + i_pos_best;
    //auto iter2k = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
    //swap(*iter1i, *iter2k);
    //cout << "swap ok: " << endl;

    /*
    cout<<"Solution before applying the move"  << endl;
    for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
        for (int k = 0; k <MyCurrentSolution.SolutionRoutes[j].visits.size() ; ++k) {
            cout<<" - " << MyCurrentSolution.SolutionRoutes[j].visits[k] ;
        }
        cout<< endl;
    }*/

    //auto iter2aux = begin(MyCurrentSolution.SolutionRoutes[r2_best].visits) + k_pos_best;
    //cout<< " i= " << i_best << " |  j= " <<j_best << " |  k= " << *iter2aux << endl;


    if (j_pos_best < k_pos_best) {
        //cout << "case  j<k: " << endl;

        auto iter1j = begin(MyCurrentSolution.visits) + j_pos_best;
        auto iter2k = begin(MyCurrentSolution.visits) + k_pos_best;
        swap(*iter1j, *iter2k);


        MyCurrentSolution.visits.insert(iter2k, i_best);

        auto iter1 = begin(MyCurrentSolution.visits) + i_pos_best ;
        MyCurrentSolution.visits.erase(iter1);


        //cout << "erase ok: " << endl;
    }
    else {
        //cout << "case  2, j>k: " << endl;

        auto iter1i = begin(MyCurrentSolution.visits) + i_pos_best;
        auto iter2k = begin(MyCurrentSolution.visits) + k_pos_best;
        swap(*iter1i, *iter2k);


        MyCurrentSolution.visits.insert(iter2k+1, j_best);
        //cout << "insertion ok: " << endl;
        auto iter1b = begin(MyCurrentSolution.visits) + j_pos_best + 1;
        MyCurrentSolution.visits.erase(iter1b);
        //cout << "erase ok: " << endl;
    }
    /*
    cout<<"Solution after applying the move"  << endl;
    for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
        for (int k = 0; k <MyCurrentSolution.SolutionRoutes[j].visits.size() ; ++k) {
            cout<<" - " << MyCurrentSolution.SolutionRoutes[j].visits[k] ;
        }
        cout<< endl;
    }
    //getchar();
     */



}


//this function calculate the cost of each route of a solution
void CalculateOF(Routes &MyRoute, Parameters& Data, MetaParameters & MetaData) {
    MyRoute.cost = 0;
    double cumulativedemand=0;
    MyRoute.visits[MyRoute.visits.size()-1]=MyRoute.visits[0];
    for (int i = MyRoute.visits.size()-1; i > 0 ; --i) {
        //cout<< i <<endl;
        if (i==MyRoute.visits.size()-1){
            MyRoute.cost+= Data.dist[MyRoute.visits[i]- 1][MyRoute.visits[i-1] - 1 + Data.T]*(Data.a);
            cumulativedemand+=Data.MyCustomers[MyRoute.visits[i-1]- 1].q;
        }
        else{
            if (i == 1){
                MyRoute.cost+= Data.dist[MyRoute.visits[i] - 1 + Data.T][MyRoute.visits[0]- 1]*(Data.a+cumulativedemand*Data.b);
            }
            else{
                //cumulativedemand+=Data.MyCustomers[MyRoute.visits[i-1]- 1].q;
                MyRoute.cost+= Data.dist[MyRoute.visits[i] - 1 + Data.T][MyRoute.visits[i-1] - 1 + Data.T]*(Data.a+cumulativedemand*Data.b);
                cumulativedemand+=Data.MyCustomers[MyRoute.visits[i-1]- 1].q;
            }
        }
    }

    MyRoute.demand=cumulativedemand;
    if (MyRoute.demand > Data.Q) {
        MyRoute.infeasibleR= true;
        MyRoute.pen= (MyRoute.demand - Data.Q)*MetaData.penalization;
    }
    else {
        MyRoute.infeasibleR= false;
        MyRoute.pen= 0.0;
    }

    MyRoute.totalcost=MyRoute.cost+MyRoute.pen;
    //return MyRoute.cost;
}

//this function calculate the cost on each route of a solution
double CalculateOF_delivery(Solution &mySolution, Routes &MyRoute, Parameters& Data, MetaParameters & Metadata) {
    MyRoute.cost = 0;
    double cumulativedemand=0;


    if (Metadata.problemID==1){
        MyRoute.visits[MyRoute.visits.size()-1]=MyRoute.visits[0];
    }
    else{
        int selecteddepot=-1;
        double obj=MAXFLOAT*1.0;
        for (int i = 0; i < mySolution.DepotsOpened.size(); ++i) {
            if(Data.dist[MyRoute.visits[MyRoute.visits.size()-2] -1 +Data.T][mySolution.DepotsOpened[i]-1] < obj) {
                selecteddepot=mySolution.DepotsOpened[i];  //// check here if we have to use -1
                obj=Data.dist[MyRoute.visits[MyRoute.visits.size()-2] -1 +Data.T][mySolution.DepotsOpened[i]-1];
            }
        }
        MyRoute.visits[MyRoute.visits.size()-1]=selecteddepot; //// check here if we have to use -1
    }



    for (int i = MyRoute.visits.size()-1; i > 0 ; --i) {
        //cout<< i <<endl;
        if (i==MyRoute.visits.size()-1){
            MyRoute.cost+= Data.dist[MyRoute.visits[i]- 1][MyRoute.visits[i-1] - 1 + Data.T]*(Data.a);
            cumulativedemand+=Data.MyCustomers[MyRoute.visits[i-1]- 1].q;
        }
        else{
            if (i == 1){
                MyRoute.cost+= Data.dist[MyRoute.visits[i] - 1 + Data.T][MyRoute.visits[0]- 1]*(Data.a+cumulativedemand*Data.b);
            }
            else{
                //cumulativedemand+=Data.MyCustomers[MyRoute.visits[i-1]- 1].q;
                MyRoute.cost+= Data.dist[MyRoute.visits[i] - 1 + Data.T][MyRoute.visits[i-1] - 1 + Data.T]*(Data.a+cumulativedemand*Data.b);
                cumulativedemand+=Data.MyCustomers[MyRoute.visits[i-1]- 1].q;
            }
        }
    }

    cout<<"demand: " << cumulativedemand <<endl;
    MyRoute.demand=cumulativedemand;
    if (MyRoute.demand > Data.Q) {
        MyRoute.infeasibleR= true;
        MyRoute.pen= (MyRoute.demand - Data.Q)*Metadata.penalization;
    }
    else {
        MyRoute.infeasibleR= false;
        MyRoute.pen= 0.0;
    }

    MyRoute.totalcost=MyRoute.cost+MyRoute.pen;
    cout<<"Infeasible?: " << MyRoute.infeasibleR <<endl;

    return MyRoute.cost;
}

//this function calculates the penalization of each route
///// block from here

double CalculatePenal(Routes MyRoute, Parameters& Data, MetaParameters& MetaData) {
    MyRoute.pen = max(0.0, (MyRoute.demand - Data.Q) * MetaData.penalization);
    //cout << " demand functions.h:" << MyRoute.ID << " = " << MyRoute.demand << endl;
    return MyRoute.pen;
}

//this function calculates the total cost (latency+penalization) of each route
double CalculateTotalCost(Routes MyRoute, Parameters& Data) {
    MyRoute.totalcost =0;
    MyRoute.totalcost = MyRoute.cost + MyRoute.pen;
    //cout << " total cost functions.h:" << MyRoute.totalcost << endl;
    return MyRoute.totalcost;
}
///// until here


//this function calculates the total cost (latency+penalization) of the solution
void SolutionCost(Solution & MySolution, Parameters& Data) {
    MySolution.objectivefunction = 0;
    for (int i = 0; i < MySolution.SolutionRoutes.size(); ++i) {
        MySolution.objectivefunction += MySolution.SolutionRoutes[i].totalcost;
    }
}


//this function calculates the total demand of each route
///// block from here
double CalculateDemand(Routes MyRoute, Parameters& Data) {
    MyRoute.demand = 0;
    for (auto client = begin(MyRoute.visits) + 1; client != end(MyRoute.visits) - 1; client++) {
        MyRoute.demand += Data.MyCustomers[*client - 1].q;
        //cout << " cliente i:" << *client << "demanda: "<< Data.MyCustomers[*client - 1].q << endl;

        //cout << " posicion de i:" << pos << endl;
    }
    //cout << " demand functions.h:" << MyRoute.ID << " = " << MyRoute.demand << endl;
    return MyRoute.demand;
}

//this function proves feasibility on each route of my solution
bool RouteFeasibility(Routes & MyRoute, Parameters& Data) {
    if (MyRoute.demand > Data.Q) return true;
    else return false;
}

///// until here

//this function proves solution feasibility
bool SolutionFeasibility(Solution &MySolution, Parameters& Data) {
    int infeasibles = 0;

    for (int i = 0; i < MySolution.SolutionRoutes.size(); i++) {
        if (MySolution.SolutionRoutes[i].infeasibleR ==true) {
            infeasibles++;
            break;
        }
    }
    if (infeasibles > 0) {
        MySolution.infeasibleSol=true;
        return true;
    }
    else {
        MySolution.infeasibleSol=false;
        return false;
    }
/*
    else{
        for (int i = 0; i < Data.T; ++i) {
            if (MySolution.demanddepot[i]>Data.MyDepots[i].QD){
                infeasibles++;
                break;
            }
        }

        if (infeasibles > 0) {
            return true;
        }
        else {
            return false;
        }
    }*/

}

//this function saves a txt file with the beavior of algorithm
void SaveMetastatistics(string &Metabehavior, double temperature, Solution &BestFR, Solution &BestR, Solution &Curre)
{
    fstream ReturnStatistics(Metabehavior, ios::app);
    ReturnStatistics << temperature  << "\t" << BestFR.objectivefunction << "\t" << BestR.objectivefunction << "\t" << Curre.objectivefunction << "\t"; //iteration, best feasible, best, current
    if (Curre.infeasibleSol == true) ReturnStatistics << "infeasible" << "\t" << std::endl;
    else(ReturnStatistics << "feasible" << "\t" << std::endl);
    ReturnStatistics.close();
}

//this function counts the number of improvements by each neighborhood
void StatisticResults(int twoOpt, int sswap, int arcsswap, int insertion, int shift21,  int twoOptSA, int sswapSA, int insertionSA, int depotExSA, int depotOpClSA, int depotInsSA)
{

    cout << "Improvements by Neighbourhood" << endl;
    cout << "2-opt       " << twoOpt << endl;
    cout << "Swap         " << sswap << endl;
    cout << "Arc-Swap         " << arcsswap << endl;
    cout << "Insertion            " << insertion << endl;
    cout << "Shift 2-1            " << shift21 << endl;
    cout << "Insertion SA           " << insertionSA << endl;
    cout << "2-opt SA      " << twoOptSA << endl;
    cout << "Swap SA        " << sswapSA << endl;
    cout << "depot Ex       " << depotExSA << endl;
    cout << "depot Open-close         " << depotOpClSA << endl;
    cout << "depot Insertion         " << depotInsSA << endl;
}


