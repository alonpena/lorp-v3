#include <cfloat>
#include "initial.h"


bool ratiodemandcomparation(clusters a, clusters b) {
    return a.demand < b.demand;
}

bool profitcomparation(splits a, splits b) {
    return a.bestgain > b.bestgain;
}

bool nselectedsorter(promisingconfig a, promisingconfig b) {
    return a.counter > b.counter;
}

bool solutionqualitycomparationinitial(Solution a, Solution b) {
    return a.objectivefunction < b.objectivefunction;
}

bool qualitycomparationinitial(promisingconfig a, promisingconfig b) {
    //return a.counter > b.counter;
    return a.object < b.object;
}

bool Insertion_vnd_aux(Parameters& Data, MetaParameters MetaData, Solution& MyCurrentSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {

    double delta_best = -MAXFLOAT; //if delta is positive we are saving
    Solution BestFound;
    bool improve=false;

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j



    //declaration of the number of customers affected by each edge
    int pos1=0;
    int pos2 = 0;


    for (int r1 = 0; r1 < MyCurrentSolution.SolutionRoutes.size(); r1++) {
        //cout << "r1 marca: " << r1 << endl;
        if (MyCurrentSolution.SolutionRoutes[r1].visits.size()<=3) continue;
        for (auto it1 = begin(MyCurrentSolution.SolutionRoutes[r1].visits) + 1; it1 != end(MyCurrentSolution.SolutionRoutes[r1].visits) - 1; it1++) {
            //cout << "iterador1 " << *it1 << endl;
            //cout << "iterador1 +1 pos " << *(it1+1) << endl;
            //cout << "iterador1 -1 ant " << *(it1 -1) << endl;
            if(it1 == begin(MyCurrentSolution.SolutionRoutes[r1].visits) + 1) pos1 = MyCurrentSolution.SolutionRoutes[r1].visits.size()-2;//how much clients are afect by the arc [i-1][i]
            else pos1=pos1-1;
            //cout << " clientes restantes desde iterador1 " << *it1 << "= " << pos1 << endl;
            //cout<< "posicion en el vecotr del iterador1 "<< *it1 << "= " << MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 2 <<endl;
            for (int r2 = 0; r2 < MyCurrentSolution.SolutionRoutes.size(); r2++) {
                //cout << "r2 marca: " << r2 << endl;
                for (auto it2 = begin(MyCurrentSolution.SolutionRoutes[r2].visits) + 1; it2 != end(MyCurrentSolution.SolutionRoutes[r2].visits); it2++) {
                    //cout << "iterador2 " << *it2 << endl;
                    //cout << "iterador2 -1 ant " << *(it2 - 1) << endl;
                    if(it2 == begin(MyCurrentSolution.SolutionRoutes[r2].visits) + 1) pos2 = MyCurrentSolution.SolutionRoutes[r2].visits.size()-2;//how much clients are afect by the arc [j-1][j]
                    else pos2=pos2-1;


                    if (r1 == r2)
                    {
                        if (*it1 == *it2) continue; // equals
                        //if (*it2 == *(it1 + 1)) continue; //the next to i


                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_Ins(MyCurrentCopy, Data, *it1, *it2, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2 - 1  );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data , MetaData);
                        //CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data );


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].cost- MyCurrentCopy.SolutionRoutes[r1].cost;
                        //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 <= delta_best) continue;
                        else {
                            delta_best=deltaR1;
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }


                    }
                    else {

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_Ins(MyCurrentCopy, Data, *it1, *it2, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2 - 1  );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data ,MetaData);
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data , MetaData);


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].totalcost- MyCurrentCopy.SolutionRoutes[r1].totalcost;
                        deltaR2= MyCurrentSolution.SolutionRoutes[r2].totalcost- MyCurrentCopy.SolutionRoutes[r2].totalcost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 +deltaR2<= delta_best) continue;
                        else {
                            delta_best=deltaR1+deltaR2;
                            MyCurrentCopy.infeasibleSol=SolutionFeasibility(MyCurrentCopy, Data);
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }

                    }


                }
            }
        }
    }
    //cout << " best delta: " << delta_best << " best delta 1: " << delta1_best << " best delta 2: " << delta2_best << " best i: " << i_best << " best j: " << j_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;


    //if (delta_best == 0) {
    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {

        MyCurrentSolution=BestFound;

        if(BestFound.objectivefunction< BestSolution.objectivefunction) BestSolution=BestFound;
        if(BestFound.objectivefunction< BestFeasibleSolution.objectivefunction && BestFound.infeasibleSol==false) BestFeasibleSolution=BestFound;
        return true;
    }

}

bool Swap_vnd_aux(Parameters& Data, MetaParameters MetaData, Solution& MyCurrentSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {
    //cout << "entre a la cabecera Neigh swap vns" << endl;
    //cout << "penalization swap:\t" << MetaData.penalization << endl;


    double delta_best = -MAXFLOAT; //if delta is positive we are saving
    Solution BestFound;
    bool improve=false;

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    int pos1=0;
    int pos2=0;

    for (int r1 = 0; r1 < MyCurrentSolution.SolutionRoutes.size(); r1++) {
        //cout << "r1 marca: " << r1 << endl;
        for (auto it1 = begin(MyCurrentSolution.SolutionRoutes[r1].visits) + 1; it1 != end(MyCurrentSolution.SolutionRoutes[r1].visits) - 1; it1++) {
            //cout << "iterador1 " << *it1 << endl;
            if(it1 == begin(MyCurrentSolution.SolutionRoutes[r1].visits) + 1) pos1 = MyCurrentSolution.SolutionRoutes[r1].visits.size()-2;//how much clients are afect by the arc [i-1][i]
            else pos1=pos1-1;
            //cout << " clientes restantes desde iterador1 " << *it1 << "= " << pos1 << endl;
            //cout<< "posicion en el vecotr del iterador1 "<< *it1 << "= " << MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 2 <<endl;
            for (int r2 = r1; r2 < MyCurrentSolution.SolutionRoutes.size(); r2++) {
                //cout << "r2 marca: " << r2 << endl;
                for (auto it2 = begin(MyCurrentSolution.SolutionRoutes[r2].visits) + 1; it2 != end(MyCurrentSolution.SolutionRoutes[r2].visits) - 1; it2++) {
                    //cout << "iterador2 " << *it2 << endl;
                    if(it2 == begin(MyCurrentSolution.SolutionRoutes[r2].visits) + 1) pos2 = MyCurrentSolution.SolutionRoutes[r2].visits.size()-2;//how much clients are afect by the arc [i-1][i]
                    else pos2=pos2-1;


                    if (r1 == r2)
                    {
                        //do not repeat evaluations performed
                        if (pos2 >= pos1)continue;

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_Swap(MyCurrentCopy, Data, *it1, *it2, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2 - 1  );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data , MetaData);
                        //CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data );


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].cost- MyCurrentCopy.SolutionRoutes[r1].cost;
                        //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 <= delta_best) continue;
                        else {
                            delta_best=deltaR1;
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }


                    }
                    else {

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_Swap(MyCurrentCopy, Data, *it1, *it2, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2 - 1  );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data , MetaData);
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data, MetaData );


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].totalcost- MyCurrentCopy.SolutionRoutes[r1].totalcost;
                        deltaR2= MyCurrentSolution.SolutionRoutes[r2].totalcost- MyCurrentCopy.SolutionRoutes[r2].totalcost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 +deltaR2<= delta_best) continue;
                        else {
                            delta_best=deltaR1+deltaR2;
                            MyCurrentCopy.infeasibleSol=SolutionFeasibility(MyCurrentCopy, Data);
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }


                    }

                }
            }
        }
    }
    //cout << " best delta: " << delta_best << " best i: " << i_best << " best j: " << j_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;

    //if (delta_best == 0) {
    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {

        MyCurrentSolution=BestFound;


        if(BestFound.objectivefunction< BestSolution.objectivefunction) BestSolution=BestFound;
        if(BestFound.objectivefunction< BestFeasibleSolution.objectivefunction && BestFound.infeasibleSol==false) BestFeasibleSolution=BestFound;
        return true;
    }

}

bool TwoOpt_vnd_aux(Parameters& Data, MetaParameters MetaData, Solution& MyCurrentSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {
    //cout << "entre a la cabecera Neigh 2-Opt vns" << endl;
    //cout << "penalization 2opt:\t" << MetaData.penalization << endl;


    double delta_best = -MAXFLOAT; //if delta is positive we are saving
    Solution BestFound;
    bool improve=false;

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    int pos1i =0;
    int pos1j=0;
    int pos2k=0;
    int pos2l=0;


    for (int r1 = 0; r1 < MyCurrentSolution.SolutionRoutes.size(); r1++) {
        //cout << "r1 marca: " << r1 << " size: " << MyCurrentSolution.SolutionRoutes[r1].visits.size() << endl;
        if (MyCurrentSolution.SolutionRoutes[r1].visits.size() == 2) continue;
        for (auto it1i = begin(MyCurrentSolution.SolutionRoutes[r1].visits) ; it1i != end(MyCurrentSolution.SolutionRoutes[r1].visits) - 2; it1i++) {
            auto it1j = it1i + 1;

            //cout << "iterador1 i " << *it1i << endl;
            //cout << "iterador1 j " << *it1j << endl;
            //int pos1i = distance(it1i, end(MyCurrentSolution.SolutionRoutes[r1].visits) - 1); //how much clients are afect by the arc [i-1][i]
            if(it1i == begin(MyCurrentSolution.SolutionRoutes[r1].visits)) pos1i = MyCurrentSolution.SolutionRoutes[r1].visits.size()-1;//how much clients are afect by the arc [i-1][i]
            else pos1i=pos1i-1;
            pos1j = pos1i - 1;


            //cout << " clientes restantes desde iterador1 " << *it1 << "= " << pos1 << endl;
            //cout<< "posicion en el vecotr del iterador1 "<< *it1 << "= " << MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 2 <<endl;
            for (int r2 = r1; r2 < MyCurrentSolution.SolutionRoutes.size(); r2++) {
                if (MyCurrentSolution.SolutionRoutes[r2].visits.size() == 2) continue;

                //cout << "r2 marca: " << r2 << " size: " << MyCurrentSolution.SolutionRoutes[r2].visits.size() << endl;
                for (auto it2k = begin(MyCurrentSolution.SolutionRoutes[r2].visits) ; it2k != end(MyCurrentSolution.SolutionRoutes[r2].visits) - 2; it2k++) {
                    auto it2l = it2k + 1;
                    //cout << "iterador2 k " << *it2k << endl;
                    //cout << "iterador2 l " << *it2l << endl;
                    //int pos2k = distance(it2k, end(MyCurrentSolution.SolutionRoutes[r2].visits) - 1); //how much clients are afect by the arc [j-1][j]
                    if(it2k == begin(MyCurrentSolution.SolutionRoutes[r2].visits)) pos2k = MyCurrentSolution.SolutionRoutes[r2].visits.size()-1;//how much clients are afect by the arc [ij-1][j]
                    else pos2k=pos2k-1;
                    pos2l = pos2k - 1;



                    //if it is intra route
                    if (r1 == r2)
                    {
                        if ((*it1i == *it2k) || (*it2k == *it1j))continue;
                        //do not repeat evaluations performed
                        if (pos2k >= pos1i) continue;

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_TwoOpt(MyCurrentCopy, Data, *it1i, *it1j, *it2k, *it2l, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1i - 1,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1j - 1 , MyCurrentSolution.SolutionRoutes[r2].visits.size()-pos2k-1,  MyCurrentSolution.SolutionRoutes[r2].visits.size()-pos2l-1, pos1j, pos2l  );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data , MetaData);
                        //CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data );


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].cost- MyCurrentCopy.SolutionRoutes[r1].cost;
                        //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch


                        //if we are impriving --> update
                        if (deltaR1 <= delta_best) continue;
                        else {
                            delta_best=deltaR1;
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }
                    }

                    else {
                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_TwoOpt(MyCurrentCopy, Data, *it1i, *it1j, *it2k, *it2l, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1i - 1,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1j - 1 , MyCurrentSolution.SolutionRoutes[r2].visits.size()-pos2k-1,  MyCurrentSolution.SolutionRoutes[r2].visits.size()-pos2l-1, pos1j, pos2l  );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data , MetaData);
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data , MetaData);


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].totalcost- MyCurrentCopy.SolutionRoutes[r1].totalcost;
                        deltaR2= MyCurrentSolution.SolutionRoutes[r2].totalcost- MyCurrentCopy.SolutionRoutes[r2].totalcost;  /////// until here, this is for computing from scratch


                        //if we are impriving --> update
                        if (deltaR1 +deltaR2<= delta_best) continue;
                        else {
                            delta_best=deltaR1+deltaR2;
                            MyCurrentCopy.infeasibleSol=SolutionFeasibility(MyCurrentCopy, Data);
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }

                    }


                }
            }
        }
    }
    //cout << " best delta: " << delta_best << " best i: " << i_best << " best j: " << j_best << " best k: " << k_best << " best l: " << l_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;

    //if (delta_best == 0) {
    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {
        MyCurrentSolution=BestFound;
        if(BestFound.objectivefunction< BestSolution.objectivefunction) BestSolution=BestFound;
        if(BestFound.objectivefunction< BestFeasibleSolution.objectivefunction && BestFound.infeasibleSol==false) BestFeasibleSolution=BestFound;
        return true;
    }


}

bool ArcSwap_vnd_aux(Parameters& Data, MetaParameters MetaData, Solution& MyCurrentSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {
    //cout << "entre a la cabecera Neigh swap vns" << endl;
    //cout << "penalization swap:\t" << MetaData.penalization << endl;


    double delta_best = -MAXFLOAT; //if delta is positive we are saving
    Solution BestFound;
    bool improve=false;

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    //int pos1=0;
    //int pos2=0;

    int pos1i=0;
    int pos1j=0;
    int pos2k=0;
    int pos2l=0;



    for (int r1 = 0; r1 < MyCurrentSolution.SolutionRoutes.size(); r1++) {
        //cout << "r1 marca: " << r1 << endl;
        if (MyCurrentSolution.SolutionRoutes[r1].visits.size() < 4) continue;
        for (auto it1i = begin(MyCurrentSolution.SolutionRoutes[r1].visits) + 1; it1i != end(MyCurrentSolution.SolutionRoutes[r1].visits) - 2; it1i++) {
            auto it1j = it1i + 1;
            //cout << "iterador1 i " << *it1i << endl;
            //cout << "iterador1 j " << *it1j << endl;

            if(it1i == begin(MyCurrentSolution.SolutionRoutes[r1].visits)+1) pos1i = MyCurrentSolution.SolutionRoutes[r1].visits.size()-2;//how much clients are afect by the arc [i-1][i]
            else pos1i=pos1i-1;
            pos1j = pos1i - 1;
            for (int r2 = r1; r2 < MyCurrentSolution.SolutionRoutes.size(); r2++) {
                if (MyCurrentSolution.SolutionRoutes[r2].visits.size() < 4) continue;
                //cout << "r2 marca: " << r2 << endl;
                for (auto it2k = begin(MyCurrentSolution.SolutionRoutes[r2].visits) + 1; it2k != end(MyCurrentSolution.SolutionRoutes[r2].visits) - 2; it2k++) {
                    auto it2l = it2k + 1;
                    //cout << "iterador2 k " << *it2k << endl;
                    //cout << "iterador2 l " << *it2l << endl;

                    if(it2k == begin(MyCurrentSolution.SolutionRoutes[r2].visits)+1) pos2k = MyCurrentSolution.SolutionRoutes[r2].visits.size()-2;//how much clients are afect by the arc [ij-1][j]
                    else pos2k=pos2k-1;
                    pos2l = pos2k - 1;


                    if (r1 == r2)
                    {
                        //i!=k, k!=j
                        if ((*it1i == *it2k) || (*it2k == *it1j))continue;
                        //do not repeat evaluations performed
                        if (pos2k >= pos1i)continue;

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_ArcSwap(MyCurrentCopy, Data, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1i - 1,   MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1j - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2k - 1, MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2l - 1 );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data ,MetaData);
                        //CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data );


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].cost- MyCurrentCopy.SolutionRoutes[r1].cost;
                        //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 <= delta_best) continue;
                        else {
                            delta_best=deltaR1;
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }


                    }
                    else {

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_ArcSwap(MyCurrentCopy, Data, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1i - 1,   MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1j - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2k - 1, MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2l - 1 );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data, MetaData );
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data , MetaData);


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].totalcost- MyCurrentCopy.SolutionRoutes[r1].totalcost;
                        deltaR2= MyCurrentSolution.SolutionRoutes[r2].totalcost- MyCurrentCopy.SolutionRoutes[r2].totalcost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 +deltaR2<= delta_best) continue;
                        else {
                            delta_best=deltaR1+deltaR2;
                            MyCurrentCopy.infeasibleSol=SolutionFeasibility(MyCurrentCopy, Data);
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }


                    }

                }
            }
        }
    }
    //cout << " best delta: " << delta_best << " best i: " << i_best << " best j: " << j_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;

    //if (delta_best == 0) {
    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {

        MyCurrentSolution=BestFound;


        if(BestFound.objectivefunction< BestSolution.objectivefunction) BestSolution=BestFound;
        if(BestFound.objectivefunction< BestFeasibleSolution.objectivefunction && BestFound.infeasibleSol==false) BestFeasibleSolution=BestFound;
        return true;
    }

}

bool Shift21_vnd_aux(Parameters& Data, MetaParameters MetaData, Solution& MyCurrentSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {
    //cout << "entre a la cabecera Neigh swap vns" << endl;
    //cout << "penalization swap:\t" << MetaData.penalization << endl;


    double delta_best = -MAXFLOAT; //if delta is positive we are saving
    Solution BestFound;
    bool improve=false;

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    //int pos1=0;
    //int pos2=0;

    int pos1i=0;
    int pos1j=0;
    int pos2=0;



    for (int r1 = 0; r1 < MyCurrentSolution.SolutionRoutes.size(); r1++) {
        //cout << "r1 marca: " << r1 << endl;
        if (MyCurrentSolution.SolutionRoutes[r1].visits.size() < 4) continue;
        for (auto it1i = begin(MyCurrentSolution.SolutionRoutes[r1].visits) + 1; it1i != end(MyCurrentSolution.SolutionRoutes[r1].visits) - 2; it1i++) {
            auto it1j = it1i + 1;
            //cout << "iterador1 " << *it1 << endl;
            //cout << "iterador1 +1 pos " << *(it1+1) << endl;
            //cout << "iterador1 -1 ant " << *(it1 -1) << endl;
            //int pos1i = distance(it1i, end(MyCurrentSolution.SolutionRoutes[r1].visits) - 1); //how much clients are afect by the arc [i-1][i]
            if(it1i == begin(MyCurrentSolution.SolutionRoutes[r1].visits)+1) pos1i = MyCurrentSolution.SolutionRoutes[r1].visits.size()-2;//how much clients are afect by the arc [i-1][i]
            else pos1i=pos1i-1;
            pos1j = pos1i - 1;

            //cout << " clientes restantes desde iterador1 " << *it1 << "= " << pos1 << endl;
            //cout<< "posicion en el vecotr del iterador1 "<< *it1 << "= " << MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1 - 2 <<endl;
            for (int r2 = 0; r2 < MyCurrentSolution.SolutionRoutes.size(); r2++) {
                //cout << "r2 marca: " << r2 << endl;
                //if (r1 == r2) continue;
                if (MyCurrentSolution.SolutionRoutes[r2].visits.size() < 3) continue;
                if (r1 == r2 && MyCurrentSolution.SolutionRoutes[r2].visits.size() < 5) continue;
                for (auto it2 = begin(MyCurrentSolution.SolutionRoutes[r2].visits) + 1; it2 != end(MyCurrentSolution.SolutionRoutes[r2].visits) - 1; it2++) {
                    //cout << "iterador2 " << *it2 << endl;
                    //cout << "iterador2 -1 ant " << *(it2 - 1) << endl;
                    //int pos2 = distance(it2, end(MyCurrentSolution.SolutionRoutes[r2].visits) - 1); //how much clients are afected if I put [i] behing [j]
                    if(it2 == begin(MyCurrentSolution.SolutionRoutes[r2].visits)+1) pos2 = MyCurrentSolution.SolutionRoutes[r2].visits.size()-2;//how much clients are afect by the arc [i-1][i]
                    else pos2 = pos2-1;



                    if (r1 == r2)
                    {
                        //i!=k, k!=j
                        if ((*it1i == *it2) || (*it2 == *it1j))continue;
                        //do not repeat evaluations performed

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_Shift21(MyCurrentCopy, Data, *it1i, *it1j, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1i - 1,   MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1j - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2 - 1);
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data, MetaData );
                        //CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data );


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].cost- MyCurrentCopy.SolutionRoutes[r1].cost;
                        //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 <= delta_best) continue;
                        else {
                            delta_best=deltaR1;
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }


                    }
                    else {

                        /////// this is for computing from scratch
                        Solution MyCurrentCopy= MyCurrentSolution;
                        change_Shift21(MyCurrentCopy, Data,*it1i, *it1j, r1, r2,  MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1i - 1,   MyCurrentSolution.SolutionRoutes[r1].visits.size() - pos1j - 1,  MyCurrentSolution.SolutionRoutes[r2].visits.size() - pos2 - 1);
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r1], Data , MetaData);
                        CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data , MetaData);


                        deltaR1= MyCurrentSolution.SolutionRoutes[r1].totalcost- MyCurrentCopy.SolutionRoutes[r1].totalcost;
                        deltaR2= MyCurrentSolution.SolutionRoutes[r2].totalcost- MyCurrentCopy.SolutionRoutes[r2].totalcost;  /////// until here, this is for computing from scratch

                        //if we are impriving --> update
                        if (deltaR1 +deltaR2<= delta_best) continue;
                        else {
                            delta_best=deltaR1+deltaR2;
                            MyCurrentCopy.infeasibleSol=SolutionFeasibility(MyCurrentCopy, Data);
                            MyCurrentCopy.objectivefunction=MyCurrentSolution.objectivefunction-delta_best;
                            BestFound= MyCurrentCopy;
                            improve= true;
                        }


                    }


                }
            }
        }
    }
    //if (delta_best == 0) {
    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {

        MyCurrentSolution=BestFound;


        if(BestFound.objectivefunction< BestSolution.objectivefunction) BestSolution=BestFound;
        if(BestFound.objectivefunction< BestFeasibleSolution.objectivefunction && BestFound.infeasibleSol==false) BestFeasibleSolution=BestFound;
        return true;
    }

}

void RouteInsertion_aux(Parameters& Data, MetaParameters MetaData, Solution& MyCurrentSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {
    //this movement selects a route in a depot with more than one vehicle assigned, and assign it to another depot

    //save previous solution in case of non-acceptation
    Solution MyPreviousSol = MyCurrentSolution;
    double bestdelta=MAXFLOAT;
    int besti=-1;
    int bestk=-1;
    int bestvehicle=-1;
    double bestcost=0.0;
    Routes bestroute;
    double deltaaux=0.0;
    double deltaaux2=0.0;
    bool applied =false;

    for (int i = 0; i < MyPreviousSol.DepotsOpened.size(); ++i) {
        if (MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]].size()<2) continue;
        for (int j = 0; j < MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]].size(); ++j) {
            deltaaux=MyPreviousSol.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].totalcost;
            for (int k = 0; k < MyPreviousSol.DepotsOpened.size(); ++k) {
                if(MyPreviousSol.DepotsOpened[k]==MyPreviousSol.DepotsOpened[i]) continue;


                //cout<< "before swap:::: " << MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits[0] <<endl;

                MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits[0]=MyPreviousSol.DepotsOpened[k]+1;
                MyCurrentSolution.SolutionRoutes[ MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits[MyCurrentSolution.SolutionRoutes[ MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits.size()-1]=MyPreviousSol.DepotsOpened[k]+1 ;
                //cout<< "after swap:::: " << MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits[0] <<endl;

                //getchar();


                CalculateOF(MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]], Data, MetaData);
                bool vnd_flag=false;
                ////apply Intra LS here ////
                for (int iii = 1; iii <= 5; iii++)
                {
                    //Set initial value to flag and counters
                    vnd_flag = false;

                    // Apply LS to each neighborhood until no improvement is found
                    // Insertion
                    if (iii == 1)
                    {
                        if(  MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits.size()<4) continue;
                        do {
                            ////cout << "Apply Insertion local search" << endl;
                            if (Insertion_TSP(Data, MetaData,  MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]], deltaaux2)) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);

                    }

                    // swap
                    if (iii == 2)
                    {
                        if(MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits.size()<4) continue;
                        do {
                            ////cout << "Apply swap local search" << endl;
                            if (Swap_TSP(Data, MetaData,  MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]], deltaaux2)) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }

                    // 2-opt
                    if (iii == 3)
                    {
                        if(MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits.size()<5) continue;
                        do {
                            ////cout << "Apply 2-opt local search" << endl;
                            if (TwoOpt_TSP(Data, MetaData,  MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]], deltaaux2)) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }

                    // Arc-swap
                    if (iii == 4)
                    {
                        if(MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits.size()<6) continue;
                        do {
                            ////cout << "Apply swap local search" << endl;
                            if (ArcSwapIntra_TSP(Data, MetaData,  MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]], deltaaux2)) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }

                    // shift-21
                    if (iii == 5)
                    {
                        if(MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].visits.size()<5) continue;
                        do {
                            ////cout << "Apply swap local search" << endl;
                            if (Shift21Intra_TSP(Data, MetaData,  MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]], deltaaux2)) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }


                } // for- local search

                if (MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].totalcost-deltaaux < bestdelta){
                    bestdelta=MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].totalcost-deltaaux;
                    besti=MyPreviousSol.DepotsOpened[i];
                    bestk=MyPreviousSol.DepotsOpened[k];
                    bestvehicle=MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j];
                    bestroute=MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]];
                    bestcost=MyCurrentSolution.SolutionRoutes[MyPreviousSol.vehiclesperdepot[MyPreviousSol.DepotsOpened[i]][j]].totalcost;
                    applied=true;
                }


            }

        }
    }

/*
    cout<<"Solution Initial  |||   OF ="<< MyPreviousSol.objectivefunction << endl;
    for (int j = 0; j <MyPreviousSol.SolutionRoutes.size() ; ++j) {
        for (int k = 0; k <MyPreviousSol.SolutionRoutes[j].visits.size() ; ++k) {
            cout<<" - " << MyPreviousSol.SolutionRoutes[j].visits[k] ;
        }
        cout<< endl;
    }

    for (int j = 0; j < MyPreviousSol.DepotsOpened.size(); ++j) {
        cout<<"depot= "<<MyPreviousSol.DepotsOpened[j] +1<<endl;
    }

    for (int j = 0; j < MyPreviousSol.vehiclesperdepot.size(); ++j) {
        for (int k = 0; k < MyPreviousSol.vehiclesperdepot[j].size(); ++k) {
            cout<<"j= "<< j+1 << "   ||   k= " <<  MyPreviousSol.vehiclesperdepot[j][k] <<endl;
        }
    }*/


    if(applied==true){
        /*
        cout<< "best i = "<< besti <<endl;
        cout<< "best k = "<< bestk <<endl;
        cout<< "best vehicle = "<< bestvehicle <<endl;


        cout<<"THE PERTURBATION WAS APPLIED!"<<endl;*/

        MyPreviousSol.SolutionRoutes[bestvehicle]=bestroute;
        MyPreviousSol.SolutionRoutes[bestvehicle].totalcost=bestcost;
        MyPreviousSol.SolutionRoutes[bestvehicle].cost=bestcost-MyPreviousSol.SolutionRoutes[bestvehicle].pen;

        auto it = find( MyPreviousSol.vehiclesperdepot[besti].begin(),  MyPreviousSol.vehiclesperdepot[besti].end(), bestvehicle);

        MyPreviousSol.vehiclesperdepot[besti].erase (it);
        MyPreviousSol.vehiclesperdepot[bestk].push_back(bestvehicle);
        sort( MyPreviousSol.vehiclesperdepot[bestk].begin(), MyPreviousSol.vehiclesperdepot[bestk].end());

        MyPreviousSol.objectivefunction= MyPreviousSol.objectivefunction+bestdelta;

        MyCurrentSolution=MyPreviousSol;

        if(MyCurrentSolution.objectivefunction< BestSolution.objectivefunction) BestSolution=MyCurrentSolution;
        if(MyCurrentSolution.objectivefunction< BestFeasibleSolution.objectivefunction && MyCurrentSolution.infeasibleSol==false) BestFeasibleSolution=MyCurrentSolution;


    }

    MyCurrentSolution=MyPreviousSol;

    /*
    cout<<"Solution after perturbation  |||   OF ="<< MyPreviousSol.objectivefunction << endl;
    for (int j = 0; j <MyPreviousSol.SolutionRoutes.size() ; ++j) {
        for (int k = 0; k <MyPreviousSol.SolutionRoutes[j].visits.size() ; ++k) {
            cout<<" - " << MyPreviousSol.SolutionRoutes[j].visits[k] ;
        }
        cout<< endl;
    }

    for (int j = 0; j < MyPreviousSol.DepotsOpened.size(); ++j) {
        cout<<"depot= "<<MyPreviousSol.DepotsOpened[j] +1<<endl;
    }

    for (int j = 0; j < MyPreviousSol.vehiclesperdepot.size(); ++j) {
        for (int k = 0; k < MyPreviousSol.vehiclesperdepot[j].size(); ++k) {
            cout<<"j= "<< j+1 << "   ||   k= " <<  MyPreviousSol.vehiclesperdepot[j][k] <<endl;
        }
    }


    cout<<"Solution after Perturbation  |||   OF ="<< MyCurrentSolution.objectivefunction << endl;*/


    double ofsolution=0.0;
    for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
        CalculateOF(MyCurrentSolution.SolutionRoutes[j], Data, MetaData);
        ofsolution+=MyCurrentSolution.SolutionRoutes[j].totalcost;
    }

    //cout<<"Solution recomputed  |||   OF ="<< ofsolution << endl;
    //exit(0);


}

void Random_RouteInsertion_aux(Parameters& Data, MetaParameters MetaData, Solution& MyCurrentSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {
    //this movement selects a route in a depot with more than one vehicle assigned, and assign it to another depot

    //save previous solution in case of non-acceptation
    //Solution MyPreviousSol = MyCurrentSolution;
    double bestdelta=MAXFLOAT;
    int besti=-1;
    int bestk=-1;
    int bestvehicle=-1;
    double bestcost=0.0;
    Routes bestroute;
    double deltaaux=0.0;
    double deltaaux2=0.0;
    bool applied =false;



    cout<<"Solution Initial  |||   OF ="<< MyCurrentSolution.objectivefunction << endl;
    for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
        for (int k = 0; k <MyCurrentSolution.SolutionRoutes[j].visits.size() ; ++k) {
            cout<<" - " << MyCurrentSolution.SolutionRoutes[j].visits[k] ;
        }
        cout<< endl;
    }

    for (int j = 0; j < MyCurrentSolution.DepotsOpened.size(); ++j) {
        cout<<"depot= "<<MyCurrentSolution.DepotsOpened[j] +1<<endl;
    }

    for (int j = 0; j < MyCurrentSolution.vehiclesperdepot.size(); ++j) {
        for (int k = 0; k < MyCurrentSolution.vehiclesperdepot[j].size(); ++k) {
            cout<<"j= "<< j+1 << "   ||   k= " <<  MyCurrentSolution.vehiclesperdepot[j][k] <<endl;
        }
    }



    //looking for the depot
    int DPT=-1;

    vector<int>depotstoplay;

    for (int i = 0; i < MyCurrentSolution.DepotsOpened.size(); ++i) {
        if (MyCurrentSolution.vehiclesperdepot[MyCurrentSolution.DepotsOpened[i]].size()>1){
            depotstoplay.push_back(MyCurrentSolution.DepotsOpened[i]);
        }
    }

    if (depotstoplay.size()<1) {
        applied=false;
    }
    else {
        if (depotstoplay.size() == 1) {
            DPT = depotstoplay[0];
        } else {
            int rdnnumber;
            rdnnumber = rand() % depotstoplay.size();
            DPT = depotstoplay[rdnnumber];
        }
        besti=DPT;

        cout << " depot selected is: " << DPT + 1 << endl;

        cout << "generating, the size of the vector is: " << MyCurrentSolution.vehiclesperdepot[DPT].size() << endl;
        int randA;

        randA = rand() % MyCurrentSolution.vehiclesperdepot[DPT].size();

        bestvehicle = MyCurrentSolution.vehiclesperdepot[DPT][randA];

        deltaaux=MyCurrentSolution.SolutionRoutes[bestvehicle].totalcost;


        while(true){
            bestk = rand() % MyCurrentSolution.DepotsOpened.size();
            if (MyCurrentSolution.DepotsOpened[bestk]!=DPT){
                bestk=MyCurrentSolution.DepotsOpened[bestk];
                break;
            }
        }

        MyCurrentSolution.SolutionRoutes[bestvehicle].visits[0]=bestk+1;

        CalculateOF(MyCurrentSolution.SolutionRoutes[bestvehicle], Data, MetaData);
        bool vnd_flag=false;
        ////apply Intra LS here ////
        for (int iii = 1; iii <= 5; iii++)
        {
            //Set initial value to flag and counters
            vnd_flag = false;

            // Apply LS to each neighborhood until no improvement is found
            // Insertion
            if (iii == 1)
            {
                if( MyCurrentSolution.SolutionRoutes[bestvehicle].visits.size()<4) continue;
                do {
                    ////cout << "Apply Insertion local search" << endl;
                    if (Insertion_TSP(Data, MetaData,  MyCurrentSolution.SolutionRoutes[bestvehicle], deltaaux2)) {
                        vnd_flag = true;
                    }

                    else {
                        vnd_flag = false;
                    }
                } while (vnd_flag == true);

            }

            // swap
            if (iii == 2)
            {
                if(MyCurrentSolution.SolutionRoutes[bestvehicle].visits.size()<4) continue;
                do {
                    ////cout << "Apply swap local search" << endl;
                    if (Swap_TSP(Data, MetaData, MyCurrentSolution.SolutionRoutes[bestvehicle], deltaaux2)) {
                        vnd_flag = true;
                    }

                    else {
                        vnd_flag = false;
                    }
                } while (vnd_flag == true);
            }

            // 2-opt
            if (iii == 3)
            {
                if(MyCurrentSolution.SolutionRoutes[bestvehicle].visits.size()<5) continue;
                do {
                    ////cout << "Apply 2-opt local search" << endl;
                    if (TwoOpt_TSP(Data, MetaData, MyCurrentSolution.SolutionRoutes[bestvehicle], deltaaux2)) {
                        vnd_flag = true;
                    }

                    else {
                        vnd_flag = false;
                    }
                } while (vnd_flag == true);
            }

            // arcswap
            if (iii == 4)
            {
                if(MyCurrentSolution.SolutionRoutes[bestvehicle].visits.size()<6) continue;
                do {
                    ////cout << "Apply 2-opt local search" << endl;
                    if (ArcSwapIntra_TSP(Data, MetaData, MyCurrentSolution.SolutionRoutes[bestvehicle], deltaaux2)) {
                        vnd_flag = true;
                    }

                    else {
                        vnd_flag = false;
                    }
                } while (vnd_flag == true);
            }
            // Shift21
            if (iii == 5)
            {
                if(MyCurrentSolution.SolutionRoutes[bestvehicle].visits.size()<5) continue;
                do {
                    ////cout << "Apply 2-opt local search" << endl;
                    if (Shift21Intra_TSP(Data, MetaData, MyCurrentSolution.SolutionRoutes[bestvehicle], deltaaux2)) {
                        vnd_flag = true;
                    }

                    else {
                        vnd_flag = false;
                    }
                } while (vnd_flag == true);
            }


        } // for- local search


            bestdelta=MyCurrentSolution.SolutionRoutes[bestvehicle].totalcost-deltaaux;
            applied=true;

    }




    if(applied==true){
        cout<< "best i = "<< besti <<endl;
        cout<< "best k = "<< bestk <<endl;
        cout<< "best vehicle = "<< bestvehicle <<endl;


        cout<<"THE PERTURBATION WAS APPLIED!"<<endl;
        auto it = find( MyCurrentSolution.vehiclesperdepot[besti].begin(),  MyCurrentSolution.vehiclesperdepot[besti].end(), bestvehicle);

        MyCurrentSolution.vehiclesperdepot[besti].erase (it);
        MyCurrentSolution.vehiclesperdepot[bestk].push_back(bestvehicle);
        sort( MyCurrentSolution.vehiclesperdepot[bestk].begin(), MyCurrentSolution.vehiclesperdepot[bestk].end());

        MyCurrentSolution.objectivefunction= MyCurrentSolution.objectivefunction+bestdelta;


        if(MyCurrentSolution.objectivefunction< BestSolution.objectivefunction) BestSolution=MyCurrentSolution;
        if(MyCurrentSolution.objectivefunction< BestFeasibleSolution.objectivefunction && MyCurrentSolution.infeasibleSol==false) BestFeasibleSolution=MyCurrentSolution;


    }


    cout<<"Solution after pert  |||   OF ="<< MyCurrentSolution.objectivefunction << endl;
    for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
        for (int k = 0; k <MyCurrentSolution.SolutionRoutes[j].visits.size() ; ++k) {
            cout<<" - " << MyCurrentSolution.SolutionRoutes[j].visits[k] ;
        }
        cout<< endl;
    }

    for (int j = 0; j < MyCurrentSolution.DepotsOpened.size(); ++j) {
        cout<<"depot= "<<MyCurrentSolution.DepotsOpened[j] +1<<endl;
    }

    for (int j = 0; j < MyCurrentSolution.vehiclesperdepot.size(); ++j) {
        for (int k = 0; k < MyCurrentSolution.vehiclesperdepot[j].size(); ++k) {
            cout<<"j= "<< j+1 << "   ||   k= " <<  MyCurrentSolution.vehiclesperdepot[j][k] <<endl;
        }
    }


    cout<<"Solution after Perturbation  |||   OF ="<< MyCurrentSolution.objectivefunction << endl;
    double ofsolution=0.0;
    for (int j = 0; j <MyCurrentSolution.SolutionRoutes.size() ; ++j) {
        CalculateOF(MyCurrentSolution.SolutionRoutes[j], Data, MetaData);
        ofsolution+=MyCurrentSolution.SolutionRoutes[j].totalcost;
    }

    cout<<"Solution recomputed  |||   OF ="<< ofsolution << endl;
    //exit(0);


}

bool Insertion_TSP(Parameters& Data, MetaParameters MetaData, Routes&MyCurrentSolution, double & cost){

    double delta_best = -MAXFLOAT; //if delta is positive we are saving
    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    int pos1=0;
    int pos2=0;
    Routes BestFound;
    bool improve=false;

    for (auto it1 = begin(MyCurrentSolution.visits) + 1; it1 != end(MyCurrentSolution.visits) - 1; it1++) {
        ////cout << "iterador1 " << *it1 << endl;
        ////cout << "iterador1 +1 pos " << *(it1+1) << endl;
        ////cout << "iterador1 -1 ant " << *(it1 -1) << endl;
        if(it1 == begin(MyCurrentSolution.visits) + 1) pos1 = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [i-1][i]
        else pos1=pos1-1;
        ////cout << " clientes restantes desde iterador1 " << *it1 << "= " << pos1 << endl;
        ////cout<< "posicion en el vecotr del iterador1 "<< *it1 << "= " << trptour.size() - pos1 - 2 <<endl;

        ////cout << "r2 marca: " << r2 << endl;
        for (auto it2 = begin(MyCurrentSolution.visits) + 1; it2 != end(MyCurrentSolution.visits); it2++) {
            ////cout << "iterador2 " << *it2 << endl;
            ////cout << "iterador2 -1 ant " << *(it2 - 1) << endl;
            if(it2 == begin(MyCurrentSolution.visits) + 1) pos2 = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [j-1][j]
            else pos2=pos2-1;

            //int position = distance(begin(trptour), it2);
            ////cout << " clientes restantes desde iterador2 " << *it2 << "= " << pos2 << endl;
            ////cout << "posicion en el vecotr del iterador2 " << *it2 << "= " << trptour.size() - pos2 - 1 << endl;
            //int distancefinal = (trptour.size()-1) -position;
            ////cout << " diferencia entre posicion y final " << distancefinal << endl;

            if (*it1 == *it2) continue; // equals
            //if (*it2 == *(it1 + 1)) continue; //the next to i


            /////// this is for computing from scratch
            Routes MyCurrentCopy= MyCurrentSolution;
            change_Ins_tsp(MyCurrentCopy, Data, *it1, *it2, 0, 0,  MyCurrentSolution.visits.size() - pos1 - 1,  MyCurrentSolution.visits.size() - pos2 - 1  );
            //bool change_Ins_tsp(Routes & MyCurrentSolution, Parameters Data, int i_ins, int j_ins, int r1_ins, int r2_ins, int i_pos_ins, int j_pos_ins);

            CalculateOF(MyCurrentCopy, Data , MetaData);


            deltaR1= MyCurrentSolution.cost- MyCurrentCopy.cost;
            //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch

            //if we are impriving --> update
            if (deltaR1 <= delta_best) continue;
            else {
                delta_best=deltaR1;
                MyCurrentCopy.totalcost=MyCurrentSolution.totalcost-delta_best;
                cost=MyCurrentCopy.totalcost;
                BestFound= MyCurrentCopy;
                improve= true;
            }

        }

    }

    ////cout << " best delta: " << delta_best << " best delta 1: " << delta1_best << " best delta 2: " << delta2_best << " best i: " << i_best << " best j: " << j_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;
    //if (delta_best == 0) {
    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {
        MyCurrentSolution=BestFound;
        cost=MyCurrentSolution.totalcost;
        return true;
    }


}

bool Swap_TSP(Parameters& Data, MetaParameters MetaData, Routes&MyCurrentSolution, double & cost) {
    ////cout << "entre a la cabecera Neigh swap intra" << endl;
    ////cout << "penalization swap:\t" << MetaData.penalization << endl;

    double delta_best = -MAXFLOAT; //if delta is positive we are saving

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    int pos1=0;
    int pos2=0;
    Routes BestFound;
    bool improve=false;

    for (auto it1 = begin(MyCurrentSolution.visits) + 1; it1 != end(MyCurrentSolution.visits) - 1; it1++) {
        ////cout << "iterador1 " << *it1 << endl;
        if(it1 == begin(MyCurrentSolution.visits) + 1) pos1 = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [i-1][i]
        else pos1=pos1-1;
        ////cout << " clientes restantes desde iterador1 " << *it1 << "= " << pos1 << endl;
        ////cout<< "posicion en el vecotr del iterador1 "<< *it1 << "= " << trptour.size() - pos1 - 2 <<endl;

        for (auto it2 = begin(MyCurrentSolution.visits) + 1; it2 != end(MyCurrentSolution.visits) - 1; it2++) {
            ////cout << "iterador2 " << *it2 << endl;
            if(it2 == begin(MyCurrentSolution.visits) + 1) pos2 = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [j-1][j]
            else pos2=pos2-1;
            //int position = distance(begin(trptour), it2);
            ////cout << " clientes restantes desde iterador2 " << *it2 << "= " << pos2 << endl;
            ////cout << "posicion en el vecotr del iterador2 " << *it2 << "= " << trptour.size() - pos2 - 1 << endl;
            //int distancefinal = (trptour.size()-1) -position;
            ////cout << " diferencia entre posicion y final " << distancefinal << endl;
            //if (*it1 == *it2) continue;

            //do not repeat evaluations performed
            if (pos2 >= pos1)continue;
            //if j is next to i

            /////// this is for computing from scratch
            Routes MyCurrentCopy= MyCurrentSolution;
            change_Swap_tsp(MyCurrentCopy, Data, *it1, *it2, 0, 0,  MyCurrentSolution.visits.size() - pos1 - 1,  MyCurrentSolution.visits.size() - pos2 - 1  );
            CalculateOF(MyCurrentCopy, Data , MetaData);
            //CalculateOF(MyCurrentCopy.SolutionRoutes[r2], Data );


            deltaR1= MyCurrentSolution.totalcost- MyCurrentCopy.totalcost;
            //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch

            //if we are impriving --> update
            if (deltaR1 <= delta_best) continue;
            else {
                delta_best=deltaR1;
                MyCurrentCopy.totalcost=MyCurrentSolution.totalcost-delta_best;
                cost= MyCurrentCopy.totalcost;
                BestFound= MyCurrentCopy;
                improve= true;
            }
        }

    }

    ////cout << " best delta: " << delta_best << " best i: " << i_best << " best j: " << j_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;

    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {
        MyCurrentSolution=BestFound;
        cost=MyCurrentSolution.totalcost;
        return true;
    }

}

bool TwoOpt_TSP(Parameters& Data, MetaParameters MetaData, Routes&MyCurrentSolution, double & cost) {
    ////cout << "entre a la cabecera Neigh 2-Opt intra" << endl;
    ////cout << "penalization 2opt:\t" << MetaData.penalization << endl;

    double delta_best = -MAXFLOAT; //if delta is positive we are saving

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j


    Routes BestFound;
    bool improve=false;


    int pos1i=0;
    int pos1j=0;
    int pos2k=0;
    int pos2l=0;


    if (MyCurrentSolution.visits.size() == 2) return false;
    for (auto it1i = begin(MyCurrentSolution.visits); it1i != end(MyCurrentSolution.visits) - 2; it1i++) {
        auto it1j = it1i + 1;

        ////cout << "iterador1 i " << *it1i << endl;
        ////cout << "iterador1 j " << *it1j << endl;
        if(it1i == begin(MyCurrentSolution.visits)) pos1i = MyCurrentSolution.visits.size()-1;//how much clients are afect by the arc [i-1][i]
        else pos1i=pos1i-1;
        pos1j = pos1i - 1;

        ////cout << "r2 marca: " << r2 << " size: " << trptour.size() << endl;
        for (auto it2k = begin(MyCurrentSolution.visits); it2k != end(MyCurrentSolution.visits) - 2; it2k++) {
            auto it2l = it2k + 1;
            ////cout << "iterador2 k " << *it2k << endl;
            ////cout << "iterador2 l " << *it2l << endl;
            if(it2k == begin(MyCurrentSolution.visits)) pos2k = MyCurrentSolution.visits.size()-1;//how much clients are afect by the arc [ij-1][j]
            else pos2k=pos2k-1;
            pos2l = pos2k - 1;

            //int position = distance(begin(trptour), it2);
            ////cout << " clientes restantes desde iterador2 " << *it2 << "= " << pos2 << endl;
            ////cout << "posicion en el vecotr del iterador2 " << *it2 << "= " << trptour.size() - pos2 - 1 << endl;
            //int distancefinal = (trptour.size()-1) -position;
            ////cout << " diferencia entre posicion y final " << distancefinal << endl;

            if ((*it1i == *it2k) || (*it2k == *it1j))continue;
            //do not repeat evaluations performed
            if (pos2k >= pos1i) continue;

            /////// this is for computing from scratch
            Routes MyCurrentCopy= MyCurrentSolution;
            change_TwoOpt_tsp(MyCurrentCopy, Data, *it1i, *it1j, *it2k, *it2l, 0, 0,  MyCurrentSolution.visits.size() - pos1i - 1,  MyCurrentSolution.visits.size() - pos1j - 1 , MyCurrentSolution.visits.size()-pos2k-1,  MyCurrentSolution.visits.size()-pos2l-1, pos1j, pos2l  );
            CalculateOF(MyCurrentCopy, Data , MetaData);



            deltaR1= MyCurrentSolution.totalcost- MyCurrentCopy.totalcost;
            //deltaR2= MyCurrentSolution.SolutionRoutes[r2].cost- MyCurrentCopy.SolutionRoutes[r2].cost;  /////// until here, this is for computing from scratch


            //if we are impriving --> update
            if (deltaR1 <= delta_best) continue;
            else {
                delta_best=deltaR1;
                MyCurrentCopy.totalcost=MyCurrentSolution.totalcost-delta_best;
                cost= MyCurrentCopy.totalcost;
                BestFound= MyCurrentCopy;
                improve= true;
            }


        }

    }

    ////cout << " best delta: " << delta_best << " best i: " << i_best << " best j: " << j_best << " best k: " << k_best << " best l: " << l_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;


    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {
        MyCurrentSolution=BestFound;
        cost=MyCurrentSolution.totalcost;
        return true;
    }


}

bool ArcSwapIntra_TSP(Parameters& Data, MetaParameters MetaData, Routes& MyCurrentSolution, double & cost) {
    //cout << "entre a la cabecera Neigh swap vns" << endl;
    //cout << "penalization swap:\t" << MetaData.penalization << endl;

    double delta_best = -MAXFLOAT; //if delta is positive we are saving

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    Routes BestFound;
    bool improve=false;

    //int pos1=0;
    //int pos2=0;

    int pos1i=0;
    int pos1j=0;
    int pos2k=0;
    int pos2l=0;


    if (MyCurrentSolution.visits.size() < 4) return false;
    for (auto it1i = begin(MyCurrentSolution.visits) + 1; it1i != end(MyCurrentSolution.visits) - 2; it1i++) {
        auto it1j = it1i + 1;
        //cout << "iterador1 i " << *it1i << endl;
        //cout << "iterador1 j " << *it1j << endl;

        if(it1i == begin(MyCurrentSolution.visits)+1) pos1i = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [i-1][i]
        else pos1i=pos1i-1;
        pos1j = pos1i - 1;
        for (auto it2k = begin(MyCurrentSolution.visits) + 1; it2k != end(MyCurrentSolution.visits) - 2; it2k++) {
            auto it2l = it2k + 1;
            //cout << "iterador2 k " << *it2k << endl;
            //cout << "iterador2 l " << *it2l << endl;

            if(it2k == begin(MyCurrentSolution.visits)+1) pos2k = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [ij-1][j]
            else pos2k=pos2k-1;
            pos2l = pos2k - 1;

            //i!=k, k!=j
            if ((*it1i == *it2k) || (*it2k == *it1j))continue;
            //do not repeat evaluations performed
            if (pos2k >= pos1i)continue;

            /////// this is for computing from scratch
            Routes MyCurrentCopy= MyCurrentSolution;
            change_ArcSwap_tsp(MyCurrentCopy, Data, 0, 0,  MyCurrentSolution.visits.size() - pos1i - 1,   MyCurrentSolution.visits.size() - pos1j - 1,  MyCurrentSolution.visits.size() - pos2k - 1, MyCurrentSolution.visits.size() - pos2l - 1 );
            CalculateOF(MyCurrentCopy, Data, MetaData );
            //CalculateOF(MyCurrentCopy, Data );


            deltaR1= MyCurrentSolution.totalcost- MyCurrentCopy.totalcost;
            //deltaR2= MyCurrentSolution.cost- MyCurrentCopy.cost;  /////// until here, this is for computing from scratch

            //if we are impriving --> update
            if (deltaR1 <= delta_best) continue;
            else {
                delta_best=deltaR1;
                MyCurrentCopy.totalcost=MyCurrentSolution.totalcost-delta_best;
                cost= MyCurrentCopy.totalcost;
                BestFound= MyCurrentCopy;
                improve= true;
            }




        }

    }

    //cout << " best delta: " << delta_best << " best i: " << i_best << " best j: " << j_best << " route 1: " << r1_best << " route 2: " << r2_best << endl;

    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {
        MyCurrentSolution=BestFound;
        cost=MyCurrentSolution.totalcost;
        return true;
    }

}

bool Shift21Intra_TSP(Parameters& Data, MetaParameters MetaData, Routes& MyCurrentSolution, double & cost) {
    //cout << "entre a la cabecera Neigh swap vns" << endl;
    //cout << "penalization swap:\t" << MetaData.penalization << endl;

    double delta_best = -MAXFLOAT; //if delta is positive we are saving

    double deltaR1 = 0; //variation in OF of route of current i
    double deltaR2 = 0; //variation in OF of route of current j

    Routes BestFound;
    bool improve=false;

    //int pos1=0;
    //int pos2=0;

    int pos1i=0;
    int pos1j=0;
    int pos2=0;







    if (MyCurrentSolution.visits.size() < 5) return false;
    for (auto it1i = begin(MyCurrentSolution.visits) + 1; it1i != end(MyCurrentSolution.visits) - 2; it1i++) {
        auto it1j = it1i + 1;
        //cout << "iterador1 " << *it1 << endl;
        //cout << "iterador1 +1 pos " << *(it1+1) << endl;
        //cout << "iterador1 -1 ant " << *(it1 -1) << endl;
        //int pos1i = distance(it1i, end(MyCurrentSolution.visits) - 1); //how much clients are afect by the arc [i-1][i]
        if(it1i == begin(MyCurrentSolution.visits)+1) pos1i = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [i-1][i]
        else pos1i=pos1i-1;
        pos1j = pos1i - 1;

        for (auto it2 = begin(MyCurrentSolution.visits) + 1; it2 != end(MyCurrentSolution.visits) - 1; it2++) {
            //cout << "iterador2 " << *it2 << endl;
            //cout << "iterador2 -1 ant " << *(it2 - 1) << endl;
            //int pos2 = distance(it2, end(MyCurrentSolution.visits) - 1); //how much clients are afected if I put [i] behing [j]
            if(it2 == begin(MyCurrentSolution.visits)+1) pos2 = MyCurrentSolution.visits.size()-2;//how much clients are afect by the arc [i-1][i]
            else pos2 = pos2-1;


            //i!=k, k!=j
            if ((*it1i == *it2) || (*it2 == *it1j))continue;
            //do not repeat evaluations performed

            /////// this is for computing from scratch
            Routes MyCurrentCopy= MyCurrentSolution;
            change_Shift21_tsp(MyCurrentCopy, Data, *it1i, *it1j, 0, 0,  MyCurrentSolution.visits.size() - pos1i - 1,   MyCurrentSolution.visits.size() - pos1j - 1,  MyCurrentSolution.visits.size() - pos2 - 1);
            CalculateOF(MyCurrentCopy, Data, MetaData );
            //CalculateOF(MyCurrentCopy, Data );



            deltaR1= MyCurrentSolution.totalcost- MyCurrentCopy.totalcost;
            //deltaR2= MyCurrentSolution.cost- MyCurrentCopy.cost;  /////// until here, this is for computing from scratch

            //if we are impriving --> update
            if (deltaR1 <= delta_best) continue;
            else {
                delta_best=deltaR1;
                MyCurrentCopy.totalcost=MyCurrentSolution.totalcost-delta_best;
                cost= MyCurrentCopy.totalcost;
                BestFound= MyCurrentCopy;
                improve= true;
            }



        }

    }


    if ((delta_best < 0.0001) || (improve== false)) {
        return false;
    }
    else {
        MyCurrentSolution=BestFound;
        cost=MyCurrentSolution.totalcost;
        return true;
    }

}

void ClusterCost(Parameters & Data, MetaParameters & MetaData, vector<clusters> &myclusters, vector<vector<vector<int>>>&mybesttrptours, vector<vector<double>>&bestdistcltodep){


    //// this one applies IntraLS to the TRP /////////
    for (int i = 0; i < Data.T; ++i) {
        bestdistcltodep[i].resize(myclusters.size());
        mybesttrptours[i].resize(myclusters.size());
        bool vnd_flag=false;
        for (int j = 0; j < myclusters.size(); ++j) {
            if(myclusters[j].customers.size()>1){

                mybesttrptours[i][j]=myclusters[j].customers;
                mybesttrptours[i][j].insert(mybesttrptours[i][j].begin(), i+1);
                mybesttrptours[i][j].push_back(i+1);
                Routes mytsp;
                mytsp.visits= mybesttrptours[i][j];
                CalculateOF(mytsp, Data, MetaData);


                ////apply Intra LS here ////
                for (int iii = 1; iii <= 5; iii++)
                {
                    //Set initial value to flag and counters
                    vnd_flag = false;

                    // Apply LS to each neighborhood until no improvement is found
                    // Insertion
                    if (iii == 1)
                    {
                        if( mybesttrptours[i][j].size()<4) continue;
                        do {
                            ////cout << "Apply Insertion local search" << endl;
                            if (Insertion_TSP(Data, MetaData, mytsp,  bestdistcltodep[i][j])) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);

                    }

                    // swap
                    if (iii == 2)
                    {
                        if(mybesttrptours[i][j].size()<4) continue;
                        do {
                            ////cout << "Apply swap local search" << endl;
                            if (Swap_TSP(Data, MetaData, mytsp,  bestdistcltodep[i][j])) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }

                    // 2-opt
                    if (iii == 3)
                    {
                        if(mybesttrptours[i][j].size()<5) continue;
                        do {
                            ////cout << "Apply 2-opt local search" << endl;
                            if (TwoOpt_TSP(Data, MetaData, mytsp,  bestdistcltodep[i][j])) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }

                    if (iii == 4)
                    {
                        if(mybesttrptours[i][j].size()<6) continue;
                        do {
                            ////cout << "Apply 2-opt local search" << endl;
                            if (ArcSwapIntra_TSP(Data, MetaData, mytsp,  bestdistcltodep[i][j])) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }

                    if (iii == 5)
                    {
                        if(mybesttrptours[i][j].size()<5) continue;
                        do {
                            ////cout << "Apply 2-opt local search" << endl;
                            if (Shift21Intra_TSP(Data, MetaData, mytsp,  bestdistcltodep[i][j])) {
                                vnd_flag = true;
                            }

                            else {
                                vnd_flag = false;
                            }
                        } while (vnd_flag == true);
                    }


                } // for- local search

                mybesttrptours[i][j]=mytsp.visits;
                mybesttrptours[i][j].erase( mybesttrptours[i][j].end()-1);
                mybesttrptours[i][j][0]=mybesttrptours[i][j][0]-1;

            }
            else{
                bestdistcltodep[i][j] =2*Data.dist[i][myclusters[j].customers[0]-1+Data.T]+ Data.dist[i][myclusters[j].customers[0]-1+Data.T]*Data.MyCustomers[myclusters[j].customers[0]-1].q;
                ////cout<< "d"<<i << " - "<<j<<"= " << distcltodep[i][j]<<endl;
                ////cout<<"customer en el vector de cluster: " << myclusters[j].customers[0] << "  ,  X: " << Data.MyCustomers[myclusters[j].customers[0]-1].x << "   , Y: " << Data.MyCustomers[myclusters[j].customers[0]-1].y<<endl;
                mybesttrptours[i][j].push_back(i);
                mybesttrptours[i][j].push_back(myclusters[j].customers[0]);
            }

            //delete bucle
            /*
            //cout<<"tour right depot "<< i << " , cl " << j <<endl;
            for (int k = 0; k <  mybesttrptours[i][j].size(); ++k) {
                //cout<<  mybesttrptours[i][j][k] << " - ";
            }
            //cout<<endl;


            //cout<<"original cluster" << j <<endl;
            for (int k = 0; k <  myclusters[j].customers.size(); ++k) {
                //cout<< myclusters[j].customers[k] << " - ";
            }
            //cout<<endl;*/

        }

    }

}

void MIPZ_hat(GRBEnv &env,  Parameters Data, MetaParameters MetaData,  vector<double> &z_hat, vector<clusters> &myclusters, vector<vector<bool>>&allocation,
              vector<bool>&location, vector<vector<GRBVar>> &X, vector<GRBVar> &Y,  vector<vector<int>>& myselectedtrptours, vector<double>&trplatencys, vector<vector<double>>&bestdistcltodep,  vector<vector<vector<int>>>&mybesttrptours,  vector<double>&mysolutionmatrix, double & objfunct){

    //exit(0);


    ////// we start with the location model  /////
    GRBModel modelo(env);

    //we define var X as 1 if depot i supplies cluster j
    X.resize(Data.T);
    for (int i = 0; i < Data.T; i++)
    {
        X[i].resize(myclusters.size());
        for (int j = 0; j < myclusters.size(); j++)
        {
            X[i][j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "X_" << i + 1 << "_" << j + 1;
            X[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }


    Y.resize(Data.T);
    for (int j = 0; j < Data.T; j++)
    {
        Y[j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
        std::stringstream nn;
        nn << "Y_" << j + 1;
        Y[j].set(GRB_StringAttr_VarName, nn.str().c_str());
    }


    //we define the objective function
    GRBLinExpr cost=0.0;
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j < myclusters.size(); j++)
        {
            cost +=X[i][j]* bestdistcltodep[i][j];
        }
    }




    modelo.setObjective(cost, GRB_MINIMIZE);

    ////cout << "FO ok" << endl;


    //(2) Each customer must be allocated to 1 depot
    for (int j = 0; j < myclusters.size(); j++)
    {
        GRBLinExpr R2=0.0;
        for (int i = 0; i < Data.T; i++)
        {
            R2 += X[i][j];
        }
        modelo.addConstr(R2 == 1);
    }
    //cout << "R2 ok" << endl;

    //(2) at least one depot must perform a route if the depot i is open
    for (int i = 0; i < Data.T; i++)
    {
        GRBLinExpr R3A=0.0;
        for (int j = 0; j < myclusters.size(); j++)
        {
            R3A += X[i][j];
        }
        modelo.addConstr(R3A >= Y[i]);
    }
    //cout << "R3A ok" << endl;


    //(3) Only use open depots
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j <myclusters.size(); j++)
        {
            modelo.addConstr(X[i][j] <=Y[i]);
        }

    }
    //cout << "R3 ok" << endl;

    /// maximum p depots
    GRBLinExpr R4=0.0;
    for (int i = 0; i < Data.T; ++i) {
        R4+=Y[i];
    }
    //modelo.add(R4<=Data.f);
    modelo.addConstr(R4==Data.f);


    //modelo.set(GRB_IntParam_Threads,1);
    modelo.set(GRB_DoubleParam_MIPGap,0.0);
    modelo.set(GRB_DoubleParam_TimeLimit,100);
    modelo.set(GRB_IntParam_OutputFlag,0);



    modelo.optimize();



    cout << "It's solved correctly" << endl;

    cout << "getStatus = " << modelo.get(GRB_IntAttr_Status)  << endl;
    cout << "getObjValue = " << modelo.get(GRB_DoubleAttr_ObjVal)  << endl;
    cout << "getBestObjValue = " << modelo.get(GRB_DoubleAttr_ObjBound) << endl;
    cout << "getTime = " << modelo.get(GRB_DoubleAttr_Runtime)  << endl;
    cout << "gap = " << modelo.get(GRB_DoubleAttr_MIPGap)  << endl;



    //X
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j < myclusters.size(); j++)
        {
            allocation[i][j]=round(X[i][j].get(GRB_DoubleAttr_X));
            if (allocation[i][j]==1){
                myselectedtrptours[j]=mybesttrptours[i][j];
                trplatencys[j]=bestdistcltodep[i][j];
            }
            ////cout << "Xalloc_" << i + 1 << "_" << j + 1<< " = " << allocation[i][j] << endl;
        }
    }


    //Y
    for (int i = 0; i < Data.T; i++)
    {
        location[i]=round(Y[i].get(GRB_DoubleAttr_X));
        z_hat[i]=Y[i].get(GRB_DoubleAttr_X)*1.0;
        if (location[i]==1) {
            int clustersallocated=0;
            for (int j = 0; j < myclusters.size(); ++j) {
                clustersallocated+=allocation[i][j];
            }
        }
        ////cout << "Yloc_" << i + 1 <<  " = " << location[i] << endl;
    }

    objfunct= modelo.get(GRB_DoubleAttr_ObjVal);

    return;
}

void MIPZ_alternatives(int itera, GRBEnv &env, Parameters Data, MetaParameters MetaData,  vector<double> &z_hat, vector<clusters> &myclusters, vector<vector<bool>>&allocation,
                       vector<bool>&location,vector<vector<GRBVar>> &X, vector<GRBVar> &Y,  vector<vector<int>>& myselectedtrptours, vector<double>&trplatencys, vector<vector<double>>&bestdistcltodep,  vector<vector<vector<int>>>&mybesttrptours,  vector<double>&mysolutionmatrix, double & objfunct){

    //exit(0);


    ////// we start with the location model  /////
    GRBModel modelo(env);

    //we define var X as 1 if depot i supplies cluster j
    X.resize(Data.T);
    for (int i = 0; i < Data.T; i++)
    {
        X[i].resize(myclusters.size());
        for (int j = 0; j < myclusters.size(); j++)
        {
            X[i][j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "X_" << i + 1 << "_" << j + 1;
            X[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }


    Y.resize(Data.T);
    for (int j = 0; j < Data.T; j++)
    {
        Y[j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
        std::stringstream nn;
        nn << "Y_" << j + 1;
        Y[j].set(GRB_StringAttr_VarName, nn.str().c_str());
    }


    //we define the objective function
    GRBLinExpr cost=0.0;
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j < myclusters.size(); j++)
        {
            cost +=X[i][j]* bestdistcltodep[i][j];
        }
    }




    modelo.setObjective(cost, GRB_MINIMIZE);

    ////cout << "FO ok" << endl;


    //(2) Each customer must be allocated to 1 depot
    for (int j = 0; j < myclusters.size(); j++)
    {
        GRBLinExpr R2=0.0;
        for (int i = 0; i < Data.T; i++)
        {
            R2 += X[i][j];
        }
        modelo.addConstr(R2 == 1);
    }
    //cout << "R2 ok" << endl;

    //(2) at least one depot must perform a route if the depot i is open
    for (int i = 0; i < Data.T; i++)
    {
        GRBLinExpr R3A=0.0;
        for (int j = 0; j < myclusters.size(); j++)
        {
            R3A += X[i][j];
        }
        modelo.addConstr(R3A >= Y[i]);
    }
    //cout << "R3A ok" << endl;


    //(3) Only use open depots
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j <myclusters.size(); j++)
        {
            modelo.addConstr(X[i][j] <=Y[i]);
        }

    }
    //cout << "R3 ok" << endl;

    /// maximum p depots
    GRBLinExpr R4=0.0;
    double count=0.0;
    for (int i = 0; i < Data.T; ++i) {
        //count+=z_hat[i];
        if(itera==i) {
          //  cout<<"setting depot "<< i+1 << " to 0" <<endl;
            modelo.addConstr(Y[i]==0);
        }
        R4+=Y[i];
    }
    modelo.addConstr(R4<=Data.f);
    //cout << "R4 ok" << endl;

    //modelo.set(GRB_IntParam_Threads,1);
    modelo.set(GRB_DoubleParam_MIPGap,0.0);
    modelo.set(GRB_DoubleParam_TimeLimit,100);
    modelo.set(GRB_IntParam_OutputFlag,0);



    modelo.optimize();



    cout << "It's solved correctly" << endl;

    cout << "getStatus = " << modelo.get(GRB_IntAttr_Status)  << endl;
    cout << "getObjValue = " << modelo.get(GRB_DoubleAttr_ObjVal)  << endl;
    cout << "getBestObjValue = " << modelo.get(GRB_DoubleAttr_ObjBound) << endl;
    cout << "getTime = " << modelo.get(GRB_DoubleAttr_Runtime)  << endl;
    cout << "gap = " << modelo.get(GRB_DoubleAttr_MIPGap)  << endl;



    //X
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j < myclusters.size(); j++)
        {
            allocation[i][j]=round(X[i][j].get(GRB_DoubleAttr_X));
            if (allocation[i][j]==1){
                myselectedtrptours[j]=mybesttrptours[i][j];
                trplatencys[j]=bestdistcltodep[i][j];
            }
            ////cout << "Xalloc_" << i + 1 << "_" << j + 1<< " = " << allocation[i][j] << endl;
        }
    }


    //Y
    for (int i = 0; i < Data.T; i++)
    {
        location[i]=round(Y[i].get(GRB_DoubleAttr_X));
        z_hat[i]=Y[i].get(GRB_DoubleAttr_X)*1.0;
        if (location[i]==1) {
            int clustersallocated=0;
            for (int j = 0; j < myclusters.size(); ++j) {
                clustersallocated+=allocation[i][j];
            }
        }
        ////cout << "Yloc_" << i + 1 <<  " = " << location[i] << endl;
    }

    objfunct= modelo.get(GRB_DoubleAttr_ObjVal);



    return;
}

void LKH_ccvrp(Parameters & Data, MetaParameters MetaData, string & instance, string seed_var, Solution & MyInitial_LKH, vector<vector<bool>>&allocation, vector<clusters>myclusters, int depot){
    ////// creating the files: instance, output and params   /////
    //int clck_int= round((float)clock()*100);
    int clck_int= (int)clock();
    string clk_str = to_string(clck_int);
    string instancen = to_string(int(Data.N))+"_"+to_string(int(Data.R))+"_"+to_string(int(Data.T))+"_"+to_string(int(Data.f))+"_"+to_string(int(Data.Q));
    if (clk_str[0]=='-') clk_str.erase(clk_str.begin());
    string config = to_string(int(1.0))+"_" +to_string(int(1.0))+"_"+to_string(int(MetaData.max_iter))+"_"+to_string(int(MetaData.MyRandomSeed))+"_"+
                    to_string(int(MetaData.penalizationDepots*100))+"_"+to_string(int(MetaData.penalization*100))+"_"+to_string(int(1.0))+"_"+to_string(int(1.0))+"_"+to_string(int(1.0));

    if (config[0]=='-') config.erase(config.begin());
    if (seed_var[0]=='-') seed_var.erase(seed_var.begin());
    string name_tour_file = clk_str+"_"+instancen+"_"+config+"_"+seed_var+"_ccvrp_tour";
    string name_vrp_file = clk_str+"_"+instancen+"_"+config+"_"+seed_var+"_ccvrp_instance";
    string name_params_file = clk_str+"_"+instancen+"_"+config+"_"+seed_var+"_ccvrp_params";

    ////// here we define the minimum number of vehicles necessary for satisfy the demand   /////
    vector<int>customersaux;
    int vehic=0;
    double demandtd=0;
    int ncustomers=0;
    for (int i = 0; i <myclusters.size() ; ++i) {
        if(allocation[depot][i]==1){
            demandtd+=myclusters[i].demand;
            ncustomers+=myclusters[i].customers.size();
            vehic++;
            for (int j = 0; j < myclusters[i].customers.size(); ++j) {
                customersaux.push_back(myclusters[i].customers[j]);
            }
        }
    }

    //if there's only one customer we don't apply LKH
    if(ncustomers==1){
        ////// adding the routes to the initial solution structure   /////
        Routes myroute;
        myroute.visits.push_back(depot+1);
        myroute.visits.push_back(customersaux[0]);
        ////cout<<"insertó"<<endl;
        myroute.visits.push_back(depot+1);

        MyInitial_LKH.demanddepot.resize(Data.T);
        MyInitial_LKH.pendepot.resize(Data.T);
        for (int i = 0; i < Data.T; ++i) {
            MyInitial_LKH.pendepot[i]=0;
            MyInitial_LKH.demanddepot[i]=0;
        }


        CalculateOF(myroute, Data, MetaData);
        //myroute.cost= CalculateOF(myroute, Data);
       // myroute.demand=CalculateDemand(myroute, Data);
        //myroute.pen=CalculatePenal(myroute, Data, MetaData);
        //myroute.totalcost=CalculateTotalCost(myroute, Data);
        //myroute.infeasibleR=RouteFeasibility(myroute, Data);
        MyInitial_LKH.SolutionRoutes.push_back(myroute);


    }
    else {
        if (vehic == customersaux.size()) {
            //cout << "sucedio 1 vehicle per customer!!!!!!" << endl;
            for (int i = 0; i < vehic; ++i) {
                ////// adding the routes to the initial solution structure   /////
                Routes myroute;
                myroute.visits.push_back(depot + 1);
                myroute.visits.push_back(customersaux[i]);
                ////cout<<"insertó"<<endl;
                myroute.visits.push_back(depot + 1);

                MyInitial_LKH.demanddepot.resize(Data.T);
                MyInitial_LKH.pendepot.resize(Data.T);
                for (int i = 0; i < Data.T; ++i) {
                    MyInitial_LKH.pendepot[i] = 0;
                    MyInitial_LKH.demanddepot[i] = 0;
                }


                /// check here ALAN
                CalculateOF(myroute, Data, MetaData);
                //myroute.cost = CalculateOF(myroute, Data);
                //myroute.demand = CalculateDemand(myroute, Data);
                //myroute.pen = CalculatePenal(myroute, Data, MetaData);
                //myroute.totalcost = CalculateTotalCost(myroute, Data);
                //myroute.infeasibleR = RouteFeasibility(myroute, Data);
                MyInitial_LKH.SolutionRoutes.push_back(myroute);
            }
        } else {
            //cout << "ncustomers: " << ncustomers << " , customersaux: " << customersaux.size() << endl;
            if (vehic > customersaux.size()) vehic = customersaux.size();

            //cout << "ncustomers: " << ncustomers << " , customersaux: " << customersaux.size() << endl;

            ////// sub-instance file   /////
            ofstream myfile;
            myfile.open(name_vrp_file + ".vrp");
            myfile << "NAME : " << name_vrp_file << ".vrp\n";
            myfile << "COMMENT : " << name_vrp_file << ".vrp\n";
            myfile << "TYPE : CCVRP\n";
            myfile << "VEHICLES: " << vehic << "\n";
            myfile << "DIMENSION : " << ncustomers + 1 << "\n";
            myfile << "EDGE_WEIGHT_TYPE : EUC_2D\n";
            myfile << "CAPACITY : " << Data.Q << "\n";
            myfile << "NODE_COORD_SECTION\n";
            myfile << "1 " << Data.MyDepots[depot].x << " " << Data.MyDepots[depot].y << "\n";
            for (int i = 0; i < customersaux.size(); ++i) {
                myfile << i + 2 << " " << Data.MyCustomers[customersaux[i] - 1].x << " "
                       << Data.MyCustomers[customersaux[i] - 1].y << "\n";
            }
            myfile << "DEMAND_SECTION\n";
            myfile << "1 " << "0 \n";
            for (int i = 0; i < customersaux.size(); ++i) {
                myfile << i + 2 << " " << Data.MyCustomers[customersaux[i] - 1].q << "\n";
            }
            myfile << "DEPOT_SECTION\n";
            myfile << "1\n";
            myfile << "-1\n";
            myfile << "EOF\n";
            myfile.close();

            ////// params file   /////
            ofstream myfile2;
            myfile2.open(name_params_file + ".par");
            myfile2 << "SPECIAL\n";
            myfile2 << "PROBLEM_FILE = " << name_vrp_file + ".vrp" << "\n";
            myfile2 << "SALESMEN = " << vehic << "\n";  //EDITAR EL N° DE VEHICULOS!!!!!!!!!!!!!!**********///////
            myfile2 << "MAX_TRIALS = 1000\n";
            myfile2 << "RUNS = 1\n";
            //myfile2 << "TIME_LIMIT = 3\n";
            myfile2 << "TRACE_LEVEL = 0\n";
            myfile2 << "SEED = " << seed_var << "\n";
            myfile2 << "OUTPUT_TOUR_FILE = " << name_tour_file << ".out\n";
            myfile2.close();
            string command5 = "./LKH " + name_params_file + ".par";
            system(command5.c_str());

            ////// reading the output file   /////
            vector<int> tour_output;
            vector<int> tour_original;
            double cost_tour = -1;
            string line;

            ifstream myfile3(name_tour_file + ".out");
            if (!myfile3) {
                cout << "Error opening file output lkh-3" << endl;
                exit(0);
            }
            int tempi;
            char tempc[1024];
            string temps;
            int theroutes;

            myfile3.getline(tempc, 1024); // NAME
            ////cout<<"NAME: " <<tempc<<endl;

            myfile3.getline(tempc, 1024); // COMMENT 1
            ////cout<<"COMMENT1: " <<tempc<<endl;

            myfile3.getline(tempc, 1024); // COMMENT 2
            ////cout<<"COMMENT2: " <<tempc<<endl;

            myfile3.getline(tempc, 1024); // TYPE
            ////cout<<"TYPE: " <<tempc<<endl;

            myfile3 >> temps >> temps >> theroutes; //DIMENSION
            ////cout<<"THEROUTES: " <<theroutes<<endl;

            myfile3 >> temps; // Tour section
            ////cout<<"TOUR SECTION: " <<tempc<<endl;

            if (temps != "TOUR_SECTION") {
                //cout << "error leyendo temps tour section" << endl;
                exit(0);
            }

            vector<vector<int>> routes;
            vector<int> raux;
            int routeconunter = 0;
            while (temps != "-1") {
                myfile3 >> temps;
                tempi = stoi(temps);
                ////cout<< "i: " << tempi <<endl;
                if (tempi == 1) {
                    vector<int> r;
                    routes.push_back(r);
                    routes[routeconunter].push_back(depot + 1);
                } else {
                    if (tempi > ncustomers + 1) {
                        routes[routeconunter].push_back(depot + 1);
                        routeconunter++;
                        vector<int> r;
                        routes.push_back(r);
                        routes[routeconunter].push_back(depot + 1);
                    } else {
                        if (tempi != -1) routes[routeconunter].push_back(customersaux[tempi - 2]);
                    }
                }

            }

            myfile3.close();

            ////// adding the routes to the initial solution structure   /////
            routes[routes.size() - 1].push_back(depot + 1);
            ////cout<<"insertó"<<endl;


            vector<Routes> mylkhroutes;
            mylkhroutes.resize(routes.size());
            MyInitial_LKH.demanddepot.resize(Data.T);
            MyInitial_LKH.pendepot.resize(Data.T);
            for (int i = 0; i < Data.T; ++i) {
                MyInitial_LKH.pendepot[i] = 0;
                MyInitial_LKH.demanddepot[i] = 0;
            }

            for (int i = 0; i < routes.size(); ++i) {
                //cout << "r" << i << ": ";
                for (int j = 0; j < routes[i].size(); ++j) {
                    ////cout<<routes[i][j]<< " - ";
                    mylkhroutes[i].visits.push_back(routes[i][j]);
                    //cout << mylkhroutes[i].visits[j] << " - ";
                }
                //cout << endl;

                //// check here Alan
               CalculateOF(mylkhroutes[i], Data, MetaData);

                /*mylkhroutes[i].cost = CalculateOF(mylkhroutes[i], Data);
                mylkhroutes[i].demand = CalculateDemand(mylkhroutes[i], Data);
                mylkhroutes[i].pen = CalculatePenal(mylkhroutes[i], Data, MetaData);
                mylkhroutes[i].totalcost = CalculateTotalCost(mylkhroutes[i], Data);
                mylkhroutes[i].infeasibleR = RouteFeasibility(mylkhroutes[i], Data);
                */
                 MyInitial_LKH.SolutionRoutes.push_back(mylkhroutes[i]);

            }

            ////// deleting the lkh's files   /////
            string command1lkh = "rm " + name_tour_file + ".out";
            string command2lkh = "rm " + name_vrp_file + ".vrp";
            string command3lkh = "rm " + name_params_file + ".par";

            system(command1lkh.c_str());
            system(command2lkh.c_str());
            system(command3lkh.c_str());

        }

    }

}

void LKH_gianttour(Parameters & Data, MetaParameters MetaData, string & instance, string seed_var,vector<int> &gianttour){
    ////// creating the files: instance, output and params   /////
    //int clck_int= round((float)clock()*100);
    int clck_int= (int)clock();
    string config = to_string(int(1.0))+"_" +to_string(int(1.0))+"_"+to_string(int(MetaData.max_iter))+"_"+to_string(int(MetaData.MyRandomSeed))+"_"+
                    to_string(int(MetaData.penalizationDepots*100))+"_"+to_string(int(MetaData.penalization*100))+"_"+to_string(int(1.0))+"_"+to_string(int(1.0))+"_"+to_string(int(1.0));

    string clk_str = to_string(clck_int);
    string instancen = to_string(int(Data.N))+"_"+to_string(int(Data.R))+"_"+to_string(int(Data.T))+"_"+to_string(int(Data.f))+"_"+to_string(int(Data.Q));
    if (clk_str[0]=='-') clk_str.erase(clk_str.begin());
    if (config[0]=='-') config.erase(config.begin());
    if (seed_var[0]=='-') seed_var.erase(seed_var.begin());

    string name_tour_file = clk_str+"_"+instancen+"_"+config+"_"+seed_var+"_tsp_tour";
    string name_tsp_file = clk_str+"_"+instancen+"_"+config+"_"+seed_var+"_tsp_instance";
    string name_params_file = clk_str+"_"+instancen+"_"+config+"_"+seed_var+"_tsp_params";



    ////// sub-instance file   /////
    ofstream myfile;
    myfile.open (name_tsp_file+".tsp");
    myfile << "NAME : "<< name_tsp_file <<".tsp\n";
    myfile << "COMMENT : "<< name_tsp_file <<".tsp\n";
    myfile << "TYPE : TSP\n";
    myfile << "DIMENSION : "<<Data.N<<"\n";
    //myfile << "EDGE_WEIGHT_TYPE : EUC_2D\n";
    //myfile << "NODE_COORD_SECTION\n";
    //for (int i = 0; i < Data.N; ++i) {
    // myfile << i+1 << " " <<Data.MyCustomers[i].x << " " <<Data.MyCustomers[i].y << "\n";
    //}
    myfile << "EDGE_WEIGHT_TYPE : EXPLICIT\n";
    myfile << "EDGE_WEIGHT_FORMAT : FULL_MATRIX\n";
    myfile << "EDGE_WEIGHT_SECTION\n";
    for (int i = Data.T; i < Data.V; i++)
    {
        for (int j = Data.T; j < Data.V; ++j) {
            myfile << Data.dist[i][j] << "\t" ;
            //<< "\t" << instance.t_stop[i] << "\n";
        }
        myfile << "\n";
    }
    myfile << "EOF\n";
    myfile.close();

    ////// params file   /////
    ofstream myfile2;
    myfile2.open (name_params_file+".par");
    myfile2 << "SPECIAL\n";
    myfile2 << "PROBLEM_FILE = "<<  name_tsp_file+".tsp" <<"\n";
    myfile2 << "SALESMEN = "<<1<<"\n";  //EDITAR EL N° DE VEHICULOS!!!!!!!!!!!!!!**********///////
    myfile2 << "MAX_TRIALS = 1000\n";
    myfile2 << "RUNS = 3\n";
    //myfile2 << "TIME_LIMIT = 3\n";
    myfile2 << "TRACE_LEVEL = 0\n";
    myfile2 << "SEED = "<<seed_var<<"\n";
    myfile2 << "OUTPUT_TOUR_FILE = "<< name_tour_file <<".out\n";
    myfile2.close();
    string command5 = "./LKH "+name_params_file+".par";
    system(command5.c_str());


    ////// reading the output file   /////
    vector<int> tour_output;
    vector<int> tour_original;
    double cost_tour=-1;
    string line;

    ifstream myfile3 (name_tour_file+".out");
    if (!myfile3) {
        cout << "Error opening file output lkh-3" << endl;
        exit(0);
    }
    int tempi;
    char tempc[1024];
    string temps;
    int theroutes;

    myfile3.getline(tempc, 1024); // NAME
    ////cout<<"NAME: " <<tempc<<endl;

    myfile3.getline(tempc, 1024); // COMMENT 1
    ////cout<<"COMMENT1: " <<tempc<<endl;

    myfile3.getline(tempc, 1024); // COMMENT 2
    ////cout<<"COMMENT2: " <<tempc<<endl;

    myfile3.getline(tempc, 1024); // TYPE
    ////cout<<"TYPE: " <<tempc<<endl;

    myfile3 >> temps >> temps >> theroutes; //DIMENSION
    ////cout<<"THEROUTES: " <<theroutes<<endl;

    myfile3 >> temps; // Tour section
    ////cout<<"TOUR SECTION: " <<tempc<<endl;

    if(temps != "TOUR_SECTION"){
        //cout<< "error leyendo temps tour section" <<endl;
        exit (0);
    }


    gianttour;
    while(temps != "-1"){
        myfile3 >> temps;
        tempi= stoi(temps);
        //cout<< "i: " << tempi <<endl;

        if(tempi==-1) break;
        else gianttour.push_back(tempi);

    }

    myfile3 >> temps; // EOF
    ////cout<<"EOF: " <<temps<<endl;
    if(temps != "EOF"){
        //cout<< "error leyendo temps EOF" <<endl;
        exit (0);
    }
    myfile3.close();


    ////// deleting the lkh's files   /////
    string command1lkh = "rm "+name_tour_file+".out";
    string command2lkh = "rm "+name_tsp_file+".tsp";
    string command3lkh = "rm "+name_params_file+".par";

    system(command1lkh.c_str());
    system(command2lkh.c_str());
    system(command3lkh.c_str());

    //exit(0);

}

void MIP_gianttour(Parameters & Data, MetaParameters MetaData, string & instance, string seed_var,vector<int> &gianttour, vector<int> &warmsolution){
    GRBEnv env;
    GRBModel modelo(env);

    vector<vector<GRBVar>> X(Data.N);
    for (int i = 0; i < Data.N; i++)
    {
        X[i].resize(Data.N);
        for (int j = 0; j < Data.N; j++)
        {
            if (i==j) continue;
            X[i][j]= modelo.addVar(0.0, 1, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "X_" << i + 1 << "_" << j + 1;
            X[i][j].set(GRB_StringAttr_VarName,nn.str().c_str());
        }
    }

    vector<GRBVar> u(Data.N);
    for (int i = 1; i < Data.N; i++)
    {
            u[i]= modelo.addVar(2, Data.N, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "u_" << i + 1;
            u[i].set(GRB_StringAttr_VarName,nn.str().c_str());
    }

    GRBLinExpr cost=0;
    for (int i = 0; i < Data.N; i++)
    {
        for (int j = 0; j < Data.N; j++) {
            if(i==j) continue;
            cost += Data.dist[i+Data.T][j+Data.T]*X[i][j];
        }
    }


    modelo.setObjective(cost, GRB_MINIMIZE);

    //////// Each customer must be visited /////////
    for (int i = 0; i < Data.N; ++i) {
        GRBLinExpr R2=0.0;
        GRBLinExpr R3=0.0;

        for (int j = 0; j <Data.N ; ++j) {
            if(i==j) continue;
            R2+=X[j][i];
            R3+=X[i][j];
        }
        modelo.addConstr(R2 ==1);
        modelo.addConstr(R3 ==1);
    }


    ///////// Valid inequalities for the edges
    /*
    for (int i = 0; i < Data.N; i++)
    {
        for (int j = 0; j < Data.N; j++)
        {
            if (i == j) continue;
            modelo.addConstr(X[j][i]+X[i][j]<= 1);

        }
    }*/

    ///////// Valid inequalities for the edges
    for (int i = 1; i < Data.N; i++)
    {
        for (int j = 1; j < Data.N; j++)
        {
            if (i != j){
                modelo.addConstr(u[i]-u[j]+1<= (Data.N-1)*(1-X[i][j]));
            }

        }
    }


    ///// reading the initial
    vector<vector<bool>>X_aux(Data.N);
    for (int i = 0; i < Data.N; ++i) {
        X_aux[i]=vector<bool>(Data.N);
        for (int j = 0; j <Data.N ; ++j) {
            if(i==j) continue;
            X_aux[i][j]=0;
        }
    }
    for (int i = 0; i <  warmsolution.size()-1; ++i) {
        X_aux[warmsolution[i]-1][warmsolution[i+1]-1]=1;
        //cout<<warmsolution[i] << " - " <<endl;
    }
    X_aux[warmsolution[warmsolution.size()-1]-1][warmsolution[0]-1]=1;


    //// setting the initial solution equal to the LKH one
    for (int i = 0; i < Data.N; ++i) {
        for (int j = 0; j <Data.N ; ++j) {
            if(i==j) continue;
            X[i][j].set(GRB_DoubleAttr_Start, X_aux[i][j]);
        }
    }



    //modelo.set(GRB_IntParam_Threads,1);
    modelo.set(GRB_DoubleParam_MIPGap,0.0);
    modelo.set(GRB_DoubleParam_TimeLimit,10);
    modelo.set(GRB_IntParam_OutputFlag,0);



    modelo.optimize();



    cout << "It's solved correctly" << endl;

    cout << "getStatus = " << modelo.get(GRB_IntAttr_Status)  << endl;
    cout << "getObjValue = " << modelo.get(GRB_DoubleAttr_ObjVal)  << endl;
    cout << "getBestObjValue = " << modelo.get(GRB_DoubleAttr_ObjBound) << endl;
    cout << "getTime = " << modelo.get(GRB_DoubleAttr_Runtime)  << endl;
    cout << "gap = " << modelo.get(GRB_DoubleAttr_MIPGap)  << endl;


/*
    for (int i = 0; i < Data.N; ++i) {
        for (int j = 0; j < Data.N; ++j) {
            if(i==j) continue;
            if(X[i][j].get(GRB_DoubleAttr_X)>0.001){
                cout<< "X_"<< i+1 << " _ " << j+1<<endl;
            }
        }
    }
*/

    int index=0;
    gianttour.push_back(index+1);
    while(true){
        int i=0;
        while ( i< Data.N)
        {
            //cout<< "i: " <<i+1 <<endl;
            //cout<< "index: " <<index+1 <<endl;
            if(i==index) {
                i++;
                //continue;
            }
            else{
                if(X[index][i].get(GRB_DoubleAttr_X)>0.001){
                    gianttour.push_back(i+1);
                    index=i;
                    i=0;
                    if (gianttour.size()==Data.N) break;
                }
                else i++;
            }

        }
        if (gianttour.size()==Data.N) break;
        cout<<gianttour.size()<<endl;
    }



    /*
    for (int i = 0; i < Data.N; ++i) {
        cout<< gianttour[i]<<endl;
    }

    exit(0);
*/

}

void Clustering(Parameters &Data,string & instance, string seed, int pos, vector<clusters> &myclusters,  vector<int>gianttour, bool & feasible){
    //cout<<"clustr"<<endl;
    vector<clusters> myclustersaux;
    myclusters=myclustersaux;
    clusters clx;
    clusters clxaux;
    double equity=0.0;
    for (int i = 0; i < Data.N; ++i) {
        equity+=Data.MyCustomers[i].q;
    }
    double sumademand=equity;
    equity=ceil(equity/Data.R)*1.0;
    cout<<"equity= "<<  equity << "||  Q=" << Data.Q<<endl;
    cout<<"suma demand= "<<  sumademand << "||  Q=" << Data.Q<<endl;
    //exit(0);

    int ID=0;
    //// original clustering
    /*
    cout<<"sumademand: " << sumademand << " ||  total capacity: " << Data.Q*Data.R<<endl;
    cout<<"ratio= " << 1.0*(1.0*sumademand/(1.0*Data.Q*Data.R))<<endl;
    exit(0);
    if (sumademand<=Data.Q){
        equity=ceil(Data.N/Data.R);
        cout<<"equity new= " <<equity <<endl;
        int flagaux=0;
        int countercustomers=0;
        for (int i = pos; i < Data.N; ++i) {
            if(flagaux*1.0 <equity){
                clx.customers.push_back(gianttour[i]);
                clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                countercustomers++;
                flagaux++;
            }
            else{
                flagaux=0;
                clx.ID=ID;
                ID++;
                clx.ratiocap=clx.demand/Data.Q; //delete
                myclusters.push_back(clx);
                clx=clxaux;
                i--;
            }
            //cout<<"i: " << i <<endl;
        }
        if (pos>0){
            for (int i = 0; i < pos; ++i) {
                if(flagaux*1.0 <equity){
                    clx.customers.push_back(gianttour[i]);
                    clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                    countercustomers++;
                    flagaux++;
                }
                else{
                    flagaux=0;
                    clx.ID=ID;
                    ID++;
                    clx.ratiocap=clx.demand/Data.Q; //delete
                    myclusters.push_back(clx);
                    clx=clxaux;
                    i--;
                }
            }
        }
        clx.ID=ID;
        myclusters.push_back(clx);
    }
    else{
        for (int i = pos; i < Data.N; ++i) {
            if((clx.demand+Data.MyCustomers[gianttour[i]-1].q <= equity )&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q )){
                clx.customers.push_back(gianttour[i]);
                clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
            }
            else{
                if( (Data.MyCustomers[gianttour[i]-1].q >= equity )&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                    clx.customers.push_back(gianttour[i]);
                    clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                }
                else{
                    clx.ID=ID;
                    ID++;
                    clx.ratiocap=clx.demand/Data.Q; //delete
                    myclusters.push_back(clx);
                    clx=clxaux;
                    i--;
                }

            }
            //cout<<"i: " << i <<endl;
        }
        if (pos>0){
            for (int i = 0; i < pos; ++i) {
                if((clx.demand+Data.MyCustomers[gianttour[i]-1].q <= equity )&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q ) ){
                    clx.customers.push_back(gianttour[i]);
                    clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                }
                else{
                    if( (Data.MyCustomers[gianttour[i]-1].q >= equity )&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                        clx.customers.push_back(gianttour[i]);
                        clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                    }
                    else {
                        clx.ID = ID;
                        ID++;
                        clx.ratiocap = clx.demand / Data.Q; //delete
                        myclusters.push_back(clx);
                        clx = clxaux;
                        i--;
                    }
                }
            }
        }
        clx.ID=ID;
        myclusters.push_back(clx);
    }*/ // until here original clustering


    int sizecls_down=floor(Data.N/Data.R);
    int sizecls_up=sizecls_down+1;
    int modulo= (Data.N % Data.R);
    int vehicles_not=Data.R - modulo; // vehicles which will have 1 customer less
    int counter_cust=0;
    cout<<"down: " <<sizecls_down<<endl;
    cout<<"up: " <<sizecls_up<<endl;
    cout<<"modulo: " <<modulo<<endl;

    for (int i = pos; i < Data.N; ++i) {
        if (modulo==0){
            if((counter_cust < sizecls_down)&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                clx.customers.push_back(gianttour[i]);
                clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                counter_cust++;
            }
            else{
                clx.ID=ID;
                ID++;
                clx.ratiocap=clx.demand/Data.Q; //delete
                myclusters.push_back(clx);
                clx=clxaux;
                i--;
                counter_cust=0;
            }
        }
        else{
            if (ID < modulo){
                if((counter_cust < sizecls_up)&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                    clx.customers.push_back(gianttour[i]);
                    clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                    counter_cust++;
                }
                else{
                    clx.ID=ID;
                    ID++;
                    clx.ratiocap=clx.demand/Data.Q; //delete
                    myclusters.push_back(clx);
                    clx=clxaux;
                    i--;
                    counter_cust=0;
                }
            }
            else{
                if((counter_cust < sizecls_down)&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                    clx.customers.push_back(gianttour[i]);
                    clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                    counter_cust++;
                }
                else{
                    clx.ID=ID;
                    ID++;
                    clx.ratiocap=clx.demand/Data.Q; //delete
                    myclusters.push_back(clx);
                    clx=clxaux;
                    i--;
                    counter_cust=0;
                }
            }

        }

        //cout<<"i: " << i <<endl;
    }
    if (pos>0){
        for (int i = 0; i < pos; ++i) {
            if (modulo==0){

                if((counter_cust < sizecls_down)&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                    clx.customers.push_back(gianttour[i]);
                    clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                    counter_cust++;
                }
                else{
                    clx.ID=ID;
                    ID++;
                    clx.ratiocap=clx.demand/Data.Q; //delete
                    myclusters.push_back(clx);
                    clx=clxaux;
                    i--;
                    counter_cust=0;
                }
            }
            else{
                if (ID < modulo){
                    if((counter_cust < sizecls_up)&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                        clx.customers.push_back(gianttour[i]);
                        clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                        counter_cust++;
                    }
                    else{
                        clx.ID=ID;
                        ID++;
                        clx.ratiocap=clx.demand/Data.Q; //delete
                        myclusters.push_back(clx);
                        clx=clxaux;
                        i--;
                        counter_cust=0;
                    }
                }
                else{
                    if((counter_cust < sizecls_down)&&(clx.demand+Data.MyCustomers[gianttour[i]-1].q <= Data.Q)){
                        clx.customers.push_back(gianttour[i]);
                        clx.demand+=Data.MyCustomers[gianttour[i]-1].q;
                        counter_cust++;
                    }
                    else{
                        clx.ID=ID;
                        ID++;
                        clx.ratiocap=clx.demand/Data.Q; //delete
                        myclusters.push_back(clx);
                        clx=clxaux;
                        i--;
                        counter_cust=0;
                    }
                }

            }

        }
    }
    clx.ID=ID;
    myclusters.push_back(clx);



    //delete bucle
    /*
    cout<<"number of cluster created: " << myclusters.size()<<endl;
    for (int i = 0; i < myclusters.size(); ++i) {
        cout<< "C"<<myclusters[i].ID<<"  demand: "<< myclusters[i].demand <<endl;
        for (int j = 0; j < myclusters[i].customers.size(); ++j) {
            cout<< myclusters[i].customers[j] << " - ";
        }
        cout<<endl;
    }


    cout<< "CL size = " << myclusters.size() <<endl;
    exit(0);
*/

    //// repair in case |clusters|> max vehicles
    if(myclusters.size()>Data.R){
        cout<<"sucedio!!!!" <<endl;
        //exit(0);
        for (int i = 0; i < myclusters.size(); ++i) {
            for (int j = 0; j < myclusters[i].customers.size()-1; ++j) {
                myclusters[i].distacl+=Data.dist[myclusters[i].customers[j]-1+Data.T][myclusters[i].customers[j+1]-1+Data.T];
            }
        }
        vector<clusters> sortedclusters=myclusters;
        sort(sortedclusters.begin(), sortedclusters.end(), ratiodemandcomparation);
        int feasiblemove=0;
        int auxpenal=1000;

        while(sortedclusters.size()>Data.R){
            double best_score = DBL_MAX;
            double current_score = 0.0;
            int best_position=-1;
            int best_cluster=-1;

            //// local search for the best insertion ////
            for (int i = 1; i < sortedclusters.size(); ++i) {
                //cout << "ok1" << endl;
                for (int j = 0; j < sortedclusters[i].customers.size()+1; ++j) {
                    if (j==0){
                        //cout << "ok2" << endl;
                        //cout<<"term 1: " << Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[0].customers[0] -1+Data.T]<<endl;
                        //cout<<"term 2: " << Data.MyCustomers[sortedclusters[0].customers[0]-1].q<<endl;

                        current_score=Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[0].customers[0] -1+Data.T]+
                                      auxpenal*max(0.0, sortedclusters[i].demand +Data.MyCustomers[sortedclusters[0].customers[0]-1].q - Data.Q);

                    }else if (j==sortedclusters[i].customers.size()){
                        //cout << "ok3" << endl;
                        current_score=Data.dist[sortedclusters[i].customers[j-1]-1+Data.T][sortedclusters[0].customers[0] -1+Data.T]+
                                      auxpenal*max(0.0, sortedclusters[i].demand +Data.MyCustomers[sortedclusters[0].customers[0]-1].q - Data.Q);

                    }else {
                        //cout << "ok4" << endl;
                        current_score=Data.dist[sortedclusters[i].customers[j-1]-1+Data.T][sortedclusters[0].customers[0] -1+Data.T]+
                                      +Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[0].customers[0] -1+Data.T]+
                                      auxpenal*max(0.0, sortedclusters[i].demand +Data.MyCustomers[sortedclusters[0].customers[0]-1].q - Data.Q)-
                                      Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T];
                    }

                    if (current_score<best_score){
                        //cout<<"current score: " << current_score << " | |  best score: "<< best_score <<endl;
                        best_position=j;
                        best_cluster=i;
                        best_score=current_score;
                    }
                }
            }

            //// apply the insertion and update the clusters (including all the info) ////
            //cout << "ok33" << endl;
            sortedclusters[best_cluster].demand= sortedclusters[best_cluster].demand + Data.MyCustomers[sortedclusters[0].customers[0]-1].q;

            sortedclusters[best_cluster].customers.insert(sortedclusters[best_cluster].customers.begin()+best_position, sortedclusters[0].customers[0]);
            //cout << "ok44" << endl;
            sortedclusters[0].customers.erase(sortedclusters[0].customers.begin());
            //cout << "ok5" << endl;
            if (sortedclusters[0].customers.size() == 0) {
                //  //cout << "ok6" << endl;
                sortedclusters.erase(sortedclusters.begin());
                sort(sortedclusters.begin(), sortedclusters.end(), ratiodemandcomparation);
                if (sortedclusters[sortedclusters.size()-1].demand>Data.Q) feasiblemove=0;
                else feasiblemove=1;
                ////cout << "ok7" << endl;
                //break;
            }
            sort(sortedclusters.begin(), sortedclusters.end(), ratiodemandcomparation);

        }

        //// finally we save the clusters
        myclusters=sortedclusters;


        //cout << "feasiblemove: "<< feasiblemove << endl;
        if (feasiblemove==0){
            int counteriterations=0;
            while(true){
                ////////// we apply swap until reaching feasibility
                //cout<<"n° clst : " << sortedclusters.size() <<endl;
                double best_score = DBL_MAX;
                double current_score = 0.0;

                int best_j=-1;
                int best_l=-1;
                int best_c1=-1;
                int best_c2=-1;

                //// local search for the best swap ////
                for (int i = 0; i < sortedclusters.size()-1; ++i) {
                    //cout << "ok1" << endl;
                    for (int j = 0; j < sortedclusters[i].customers.size(); ++j) {
                        for (int k = i+1; k <sortedclusters.size() ; ++k) {
                            if (sortedclusters[i].demand<=Data.Q && sortedclusters[k].demand<=Data.Q) continue;
                            for (int l = 0; l < sortedclusters[k].customers.size(); ++l) {
                                if (j==0){
                                    if (l==0){
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);

                                    }else if(l==sortedclusters[k].customers.size()-1){
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);
                                    }else{
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);
                                    }
                                }else if(j==sortedclusters[i].customers.size()-1){
                                    if (l==0){
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);

                                    }else if(l==sortedclusters[k].customers.size()-1){
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);
                                    }else{
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);
                                    }
                                }else{
                                    if (l==0){
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);

                                    }else if(l==sortedclusters[k].customers.size()-1){
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);
                                    }else{
                                        current_score=-(Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])+
                                                      (Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j-1]-1+Data.T]+ Data.dist[sortedclusters[k].customers[l]-1+Data.T][sortedclusters[i].customers[j+1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l-1]-1+Data.T]+ Data.dist[sortedclusters[i].customers[j]-1+Data.T][sortedclusters[k].customers[l+1]-1+Data.T])
                                                      + auxpenal*max(0.0, sortedclusters[i].demand - Data.MyCustomers[sortedclusters[i].customers[j]-1].q+Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q)+
                                                      auxpenal*max(0.0, sortedclusters[k].demand + Data.MyCustomers[sortedclusters[i].customers[j]-1].q-Data.MyCustomers[sortedclusters[k].customers[l]-1].q - Data.Q);
                                    }
                                }

                                if (current_score<best_score){
                                    //cout<<"current score: " << current_score << " | |  best score: "<< best_score <<endl;
                                    best_j=j;
                                    best_l=l;
                                    best_c1=i;
                                    best_c2=k;
                                    best_score=current_score;
                                }

                            }

                        }

                    }
                }

                //// apply the insertion and update the clusters (including all the info) ////
                //cout << "ok33" << endl;
                int auxswap1=sortedclusters[best_c1].customers[best_j];
                int auxswap2= sortedclusters[best_c2].customers[best_l];

                sortedclusters[best_c1].demand= sortedclusters[best_c1].demand - Data.MyCustomers[sortedclusters[best_c1].customers[best_j]-1].q+Data.MyCustomers[sortedclusters[best_c2].customers[best_l]-1].q;
                sortedclusters[best_c2].demand= sortedclusters[best_c2].demand + Data.MyCustomers[sortedclusters[best_c1].customers[best_j]-1].q-Data.MyCustomers[sortedclusters[best_c2].customers[best_l]-1].q;

                sortedclusters[best_c1].customers[best_j]=auxswap2;
                sortedclusters[best_c2].customers[best_l]=auxswap1;

                //cout << "ok5" << endl;

                sort(sortedclusters.begin(), sortedclusters.end(), ratiodemandcomparation);

                if (sortedclusters[sortedclusters.size()-1].demand <= Data.Q) {
                    //  //cout << "ok6" << endl;
                    feasible=true;
                    break;
                }
                if (counteriterations>50){
                    feasible=false;
                    break;
                }

                counteriterations++;
            }
        }

        //// finally we save the clusters
        if (sortedclusters[sortedclusters.size()-1].demand <= Data.Q) {
            //  //cout << "ok6" << endl;
            feasible=true;
        }

        myclusters=sortedclusters;

    }

    else {
        feasible=true;
    }



}

void splitting_New(Parameters & Data, vector<clusters> &myclusters) {

    int vehiclesused = myclusters.size();


    ///// iterate until no profit or until the number of vehicles is equal to R or N ////
    while(true){

        clusters newcluster;
        double longestedge = -MAXFLOAT;
        int besti=-1;
        int bestcl=-1;
        //////// evaluate each trp tour ///////
        for (int i = 0; i < myclusters.size(); ++i) {
            if (myclusters[i].customers.size() ==1) continue;
            //////// find the largest edge on the cluster ///////
            for (int j = 0; j < myclusters[i].customers.size()-1; ++j) {
                if (Data.dist[myclusters[i].customers[j] - 1 + Data.T][myclusters[i].customers[j] - 1 + Data.T] > longestedge) {
                    longestedge = Data.dist[myclusters[i].customers[j] - 1 + Data.T][myclusters[i].customers[j+1] - 1 + Data.T];
                    besti =j;
                    bestcl=i;
                }
            }
        }

        vector<int>customersselected;
        double demandnewcl=0.0;

        for (int i = besti+1; i < myclusters[bestcl].customers.size(); ++i) {
            customersselected.push_back( myclusters[bestcl].customers[i]);
            demandnewcl+= Data.MyCustomers[myclusters[bestcl].customers[i]-1].q;
        }
        newcluster.customers=customersselected;
        newcluster.demand=demandnewcl;
        newcluster.ID=vehiclesused;

        myclusters[bestcl].customers.erase(myclusters[bestcl].customers.begin()+besti+1, myclusters[bestcl].customers.end());
        myclusters[bestcl].demand= myclusters[bestcl].demand- demandnewcl;

        myclusters.push_back(newcluster);


        vehiclesused++;
        ////cout<< "n° clusters: " << vehiclesused <<endl;
        if ( (vehiclesused == Data.R) || (vehiclesused==Data.N) )break;


    }

}

void VND_short(Parameters& Data, MetaParameters MetaData, Solution& MyMetaSolution, Solution& BestSolution, Solution& BestFeasibleSolution) {

    bool Meta_flag=false;
    bool LS_flag=false;
    int myaux=1;
    int tabudepot=-1;
    tuple<int, int> tabutuple (-1,  -1)  ;
    bool infeasiblemove=false;


for(int yy=0;yy<2;yy++) {
            do{
            Meta_flag=false;
            myaux=1;

            for (int i = 1; i <= 5; i++) {
                //Set initial value to flag and counters
                cout<<"Starting search " << MyMetaSolution.objectivefunction << endl;
                LS_flag = false;

                // Apply LS to each neighborhood until no improvement is found

                // Insertion
                if (i == 1)
                {
                    do {
                        ////cout << "Apply Insertion local search" << endl;
                        if (Insertion_vnd_aux(Data, MetaData, MyMetaSolution, BestSolution, BestFeasibleSolution)) {
                            //Data.insertionVND++;
                            Meta_flag = true;
                            LS_flag=true;
                            myaux=1;
                            //cout<<"accepted ins " << MyMetaSolution.objectivefunction << endl;
                            //save variations on a txt file
                            //SaveMetastatistics(Metabehavior, temperature, iteration, BestFeasibleSolution, BestSolution, MyMetaSolution);
                        }

                        else {
                            LS_flag = false;
                        }
                    } while (LS_flag == true);

                }

                // swap
                if (i == 2)
                {
                    do {
                        ////cout << "Apply swap local search" << endl;
                        if (Swap_vnd_aux(Data, MetaData, MyMetaSolution, BestSolution, BestFeasibleSolution)) {
                            //Data.sswapVND++;
                            Meta_flag = true;
                            LS_flag = true;
                            myaux=2;
                            //cout<<"accepted swap " << MyMetaSolution.objectivefunction << endl;
                            //save variations on a txt file
                            // SaveMetastatistics(Metabehavior, temperature, iteration, BestFeasibleSolution, BestSolution, MyMetaSolution);
                        }

                        else {
                            LS_flag = false;
                        }
                    } while (LS_flag == true);
                }

                // 2-opt
                if (i == 3)
                {
                    do {
                        ////cout << "Apply 2-opt local search" << endl;

                        if (TwoOpt_vnd_aux(Data, MetaData, MyMetaSolution, BestSolution, BestFeasibleSolution)) {
                            //Data.twoOptVND++;
                            Meta_flag = true;
                            LS_flag = true;
                            myaux=3;
                            //cout<<"accepted 2-opt " << MyMetaSolution.objectivefunction << endl;
                            //save variations on a txt file
                            // SaveMetastatistics(Metabehavior, temperature, iteration, BestFeasibleSolution, BestSolution, MyMetaSolution);
                        }

                        else {
                            LS_flag = false;
                        }


                    } while (LS_flag == true);
                }

                // Arc-swap
                if (i == 4)
                {
                    //continue;
                    do {
                        ////cout << "Apply Arc-swap local search" << endl;

                        if (ArcSwap_vnd_aux(Data, MetaData, MyMetaSolution, BestSolution, BestFeasibleSolution)) {
                            //Data.twoOptVND++;
                            Meta_flag = true;
                            LS_flag = true;
                            myaux=4;
                            //cout<<"accepted 2-opt " << MyMetaSolution.objectivefunction << endl;
                            //save variations on a txt file
                            // SaveMetastatistics(Metabehavior, temperature, iteration, BestFeasibleSolution, BestSolution, MyMetaSolution);
                        }

                        else {
                            LS_flag = false;
                        }


                    } while (LS_flag == true);
                }

                // Shift 2-1
                if (i == 5)
                {
                    //continue;
                    do {
                        ////cout << "Apply Shift 2-1 local search" << endl;
                        //getchar();

                        if (Shift21_vnd_aux(Data, MetaData, MyMetaSolution, BestSolution, BestFeasibleSolution)) {
                            //Data.twoOptVND++;
                            Meta_flag = true;
                            LS_flag = true;
                            myaux=5;
                            //cout<<"accepted 2-opt " << MyMetaSolution.objectivefunction << endl;
                            //save variations on a txt file
                            // SaveMetastatistics(Metabehavior, temperature, iteration, BestFeasibleSolution, BestSolution, MyMetaSolution);
                            //getchar();
                        }

                        else {
                            LS_flag = false;
                        }


                    } while (LS_flag == true);
                }

            } // for- neighborhoods

        }while( (Meta_flag==true)&& (myaux!=1)  );
if(yy<1) {
    if (MyMetaSolution.DepotsOpened.size()>1) {
        //RouteInsertion_aux(Data, MetaData, MyMetaSolution, BestSolution, BestFeasibleSolution);
        Random_RouteInsertion_aux(Data, MetaData, MyMetaSolution, BestSolution, BestFeasibleSolution);
    }

}
}


}

void InitialZ_hat(string instance, MetaParameters &MetaData, string seed, Parameters &Data, vector<double> &z_hat, vector<promisingconfig> &myconfigurations,  Solution & MyInitial, vector<Solution>&Start){
    ////// here we define the minimum number of vehicles necessary for satisfy the demand   /////
    double totaldemand=0;
    for (int i = 0; i < Data.N; ++i) {
        totaldemand+=Data.MyCustomers[i].q;
    }
    int vehicles=ceil(totaldemand/Data.Q);
    //cout<<"vehicles: "<< vehicles <<endl;


    ///// here we declare the cluster vector, the giant tour vector, and the solutions ////
    vector<int>gianttour;
    vector<int>warmsolution;
    vector<clusters>myclusters;
    vector<double>mysolutionmatrix;
    double mybestof= MAXFLOAT;
    int bestindex=-1;
    vector<vector<bool>>bestallocation;
    vector<bool>bestlocation;
    vector<vector<int>>mybestselectedtrptours;
    vector<double>besttrplatencys;

    double equity=0.0;
    equity=ceil(Data.N/Data.R)*1.0;

    ///////create the giant tour using LKH-3 //////////
    LKH_gianttour(Data, MetaData, instance, seed, warmsolution);
    MIP_gianttour(Data, MetaData, instance, seed, gianttour, warmsolution);


    ///////clustering procedure - clustering until the first feasible solution is found //////////
    int ic=0;
    int counter=0;
    while(true){
        bool feasible=false;
        cout<<"ic= "<<ic << "   ||  counter=   "<< counter <<endl;
        while (true){
            ///////calling the clustering procedure //////////
            cout<<"ic= "<<ic << "   ||  counter=   "<< counter <<endl;
            Clustering(Data,instance, seed, ic, myclusters, gianttour, feasible);
            //Clustering_Voriginal(Data,instance, seed, ic, myclusters, gianttour, feasible);
            /*cout<< "CL size = " << myclusters.size() <<endl;
            for (int i = 0; i < Data.R; ++i) {
                cout<<" C"<<i+1<<" _ demand = " << myclusters[i].demand<<endl;
            }
            exit(0);*/

            ic++;
            if (feasible==true) counter++;
            /*
            if((feasible==false)||(ic==Data.N)) {
                break;
            }*/
            if((feasible==true)||(ic==Data.N)) {
                cout<<"BREAKING! ic= "<<ic << "   ||  counter=   "<< counter <<endl;
                break;
            }
        }

        /*
        for (int i = 0; i < Data.R; ++i) {
            cout<<" C"<<i+1<<" _ demand = " << myclusters[i].demand<<endl;
        }
        exit(0);
*/


        if(myclusters.size()<Data.R){
            splitting_New(Data, myclusters);
            //exit(0);
        }
        //cout<< "number of clusters after = "<< myclusters.size()<<endl;


        ///// this vectors will save the trp tours and the latency of them /////
        vector<vector<int>>myselectedtrptours;
        vector<double>trplatencys;

        trplatencys.resize(myclusters.size());
        myselectedtrptours.resize(myclusters.size());

        vector<vector<vector<int>>>mybesttrptours;
        vector<vector<double>>bestdistcltodep;
        bestdistcltodep.resize(Data.T);
        mybesttrptours.resize(Data.T);

        ////// calculate the cost matrix cluster-depots //////
        ClusterCost(Data, MetaData, myclusters, mybesttrptours, bestdistcltodep);

        ////// this vector will save the variable X in MIP   /////
        vector<vector<bool>>allocation;
        allocation.resize(Data.T);
        for (int r = 0; r < Data.T; ++r) {
            allocation[r].resize(myclusters.size());
        }

        ////// this vector will save the variable Y in MIP   /////
        vector<bool>location;
        location.resize(Data.T);


        //int newp=Data.f;
        //int forbidendepot=-1;
        double objfunct=0.0;
        vector<int>locationoriginal;

        ////// 1st calling to the CPLEX environment and the location MIP    /////
        try {
            GRBEnv env;
            GRBModel modelo(env);

            //CALLING MODEL

            vector<GRBVar>Y;
            vector<vector<GRBVar>>X;
            objfunct=0.0;

            //cout<<"before the mip" <<endl;
            MIPZ_hat(env, Data, MetaData, z_hat, myclusters, allocation, location, X, Y, myselectedtrptours,trplatencys, bestdistcltodep, mybesttrptours, mysolutionmatrix, objfunct);
            //cout<<"after the mip" <<endl;

            //// saving the promising configurations and counting the times they are selected /////
            auto puntero= find (myconfigurations.begin(), myconfigurations.end(),promisingconfig(location, allocation,objfunct , myclusters, myselectedtrptours, trplatencys,1));
            if ( puntero == myconfigurations.end()){
                myconfigurations.push_back(promisingconfig(location, allocation, objfunct , myclusters, myselectedtrptours, trplatencys,1));
            }
            else{
                puntero->counter++;
                if(puntero->object >objfunct ){
                    //cout<<"puntero= "<< puntero->object << " ||  new value= "<< mysolutionmatrix[i]<<endl;
                    puntero->object =objfunct;
                    puntero->clu =myclusters;
                    puntero->all = allocation;
                    puntero->trptours=myselectedtrptours;
                    puntero->latencies=trplatencys;
                }
            }


            cout<< "original"<< endl;
            for (int j = 0; j < location.size(); ++j) {
                cout<< "-" <<location[j] ;
                if (location[j]>0.9) locationoriginal.push_back(j);
            }
            cout<<endl;

        }

        catch (...) {
            cerr << "Error" << endl;
        }

        //// finding the neighbor solutions of Z
        for (int i = 0; i < Data.f; ++i) {
            try {
                GRBEnv env1;
                GRBModel modelo(env1);

                //CALLING MODEL

                vector<GRBVar>Y;
                vector<vector<GRBVar>>X;
                objfunct=0.0;
                //cout<<"before the mip" <<endl;
                MIPZ_alternatives(locationoriginal[i], env1, Data, MetaData, z_hat, myclusters, allocation, location, X, Y, myselectedtrptours,trplatencys, bestdistcltodep, mybesttrptours, mysolutionmatrix, objfunct);
                //cout<<"after the mip" <<endl;
                auto puntero= find (myconfigurations.begin(), myconfigurations.end(),promisingconfig(location, allocation,objfunct , myclusters, myselectedtrptours, trplatencys,1));
                if ( puntero == myconfigurations.end()){
                    myconfigurations.push_back(promisingconfig(location, allocation, objfunct , myclusters, myselectedtrptours, trplatencys,1));
                }
                else{
                    puntero->counter++;
                    if(puntero->object >objfunct ){
                        //cout<<"puntero= "<< puntero->object << " ||  new value= "<< mysolutionmatrix[i]<<endl;
                        puntero->object =objfunct;
                        puntero->clu =myclusters;
                        puntero->all = allocation;
                        puntero->trptours=myselectedtrptours;
                        puntero->latencies=trplatencys;
                    }
                }


            }
            catch (...) {
                cerr << "Error" << endl;
            }
        }

        if((ic==Data.N) || counter==equity) {
            cout<<" breaking!  ic=" << ic << "  ||  counter= " << counter<<endl;
            break;
        }

    }


    ///// sort the configurations according the number of times they were selected
    sort(myconfigurations.begin(), myconfigurations.end(), qualitycomparationinitial);

    /*
    fstream out("initial_vectors.txt", ios::app);
    out<< instance <<"\t" << myconfigurations.size() <<endl;

    out.close();
*/
    //exit(0);

    //// create an initial solution only from the X most selected
    int nctoevaluate;
    if (myconfigurations.size()< Data.f+1) nctoevaluate=myconfigurations.size();
    else nctoevaluate=Data.f+1;
    //nctoevaluate=round(myconfigurations.size());

    for (int i = 0; i < nctoevaluate; ++i) {
        ////// splitting section   /////

        if (myclusters.size()<Data.R){
            cout<< "ERROR! n de clusters= " << myclusters.size() << endl;
            exit(0);
        }


        Solution Empty;
        MyInitial=Empty;


        MyInitial.demanddepot.resize(Data.T);
        MyInitial.pendepot.resize(Data.T);
        for (int j = 0; j < Data.T; ++j) {
            MyInitial.pendepot[j]=0;
            MyInitial.demanddepot[j]=0;
        }

        for (int j = 0; j < Data.R; ++j) {
            Routes myroute;
            myroute.visits.push_back(myconfigurations[i].trptours[j][0]+1);

            for (int k = 1; k < myconfigurations[i].trptours[j].size(); ++k) {
                myroute.visits.push_back(myconfigurations[i].trptours[j][k]);
            }
            //cout<<endl;

            //// check here Alan
            myroute.visits.push_back(myconfigurations[i].trptours[j][0]+1);
            CalculateOF(myroute, Data, MetaData);

            /*
            myroute.cost= CalculateOF(myroute, Data);
            myroute.demand=CalculateDemand(myroute, Data);
            myroute.pen=CalculatePenal(myroute, Data, MetaData);
            myroute.totalcost=CalculateTotalCost(myroute, Data);
            myroute.infeasibleR=RouteFeasibility(myroute, Data);
             */
            MyInitial.SolutionRoutes.push_back(myroute);
        }



        ////// LKH section   /////
        double fixed_d=0.0;
        for (int j = 0; j < Data.T; ++j) {
            MyInitial.pendepot[i]=0;
            MyInitial.demanddepot[i]=0;
            if (myconfigurations[i].a[j]==0) continue;
            fixed_d+=Data.MyDepots[j].cost;
            MyInitial.DepotsOpened.push_back(j);
        }

        MyInitial.mybinaryY=myconfigurations[i].a;
        MyInitial.vehiclesperdepot.resize(Data.T);

        ///// calculate the load at each open depot, then the OF and feasibility
        for (int r = 0; r < MyInitial.SolutionRoutes.size(); ++r) {
            ////cout<<"demand route " << i << "  : " << MyInitial.SolutionRoutes[i].demand << endl;
            MyInitial.demanddepot[MyInitial.SolutionRoutes[r].visits[0]-1]+=MyInitial.SolutionRoutes[r].demand;
            MyInitial.vehiclesperdepot[MyInitial.SolutionRoutes[r].visits[0]-1].push_back(r);
        }
        MyInitial.infeasibleSol=SolutionFeasibility(MyInitial, Data);
        SolutionCost(MyInitial , Data); // remove this - change!

        //delete bucle
        //cout<<"latency sin LS solution : "<< MyInitial.objectivefunction<<endl;


        //// for the rest of the algorithm the number of vehicles is equal to the current number of routes
        Data.R=MyInitial.SolutionRoutes.size();
        //cout<<"number of vehicles: " << Data.R <<endl;


        ////// local search section   /////
        Solution MyCurrentSolution= MyInitial;
        Solution BestSolution= MyInitial;
        double lat_lkh_alone=MyInitial.objectivefunction;
        MetaData.penalization=MetaData.penalization*MyInitial.objectivefunction/100;
        MetaData.penalizationDepots= MetaData.penalizationDepots*MyInitial.objectivefunction/100;
        //cout<<"pen vehic: " <<  MetaData.penalization<< endl;
        //cout<<"pen depot: " <<  MetaData.penalizationDepots<< endl;
        VND_short(Data,MetaData, MyCurrentSolution, BestSolution,  MyInitial);
        //cout<< "after vnd "  << endl;

        //delete bucle
        //GraphHeuristic("graph_LS.gml", Data, MyInitial); //graph of initial solution
        //cout<<"latency con LS solution : "<< MyInitial.objectivefunction<<endl;
        //cout<<"latency con best solution : "<< BestSolution.objectivefunction<<endl;
        //GraphHeuristic("graph_best.gml", Data, BestSolution); //graph of initial solution


        Start.push_back(MyInitial);
    }

    ///// sort the selected configurations according the O.F
    sort(Start.begin(), Start.end(), solutionqualitycomparationinitial);




}
