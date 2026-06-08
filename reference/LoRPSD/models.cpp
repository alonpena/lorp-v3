//
// Created by alan on 07/04/22.
//

#include "models.h"


void LoRP_2IF_new(string instance, int obj, string &results, GRBEnv &env, Parameters &Data,  vector<vector<GRBVar>>&X, vector<GRBVar>&Y, vector<vector<GRBVar>> &W, vector<vector<GRBVar>> &f, vector<vector<GRBVar>>&A,  vector<vector<GRBVar>> &NC, vector<vector<GRBVar>> &t, vector<vector<bool>>&X_graph, vector<vector<bool>>&A_graph, vector<bool>&Z_graph)
{

    cout<<" ----------------- This model is based on the one proposed by Loffler et all 2023 returning to the same depot -----------------------" << endl;

    GRBModel modelo(env);


    X.resize(Data.V);
    X_graph.resize(Data.V);
    for (int i = 0; i < Data.V; i++)
    {
        X[i].resize(Data.V);
        X_graph[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;

            X[i][j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "X_" << i + 1 << "_" <<j + 1 ;
            X[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());

        }
    }


    Y.resize(Data.T);
    Z_graph.resize(Data.T);
    for (int j = 0; j < Data.T; j++)
    {
        Y[j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
        std::stringstream nn;
        nn << "Y_" << j + 1;
        Y[j].set(GRB_StringAttr_VarName, nn.str().c_str());
    }



    f.resize(Data.T);
    for (int i = 0; i < Data.T; i++)
    {
        f[i].resize(Data.N);
        for (int j = 0; j < Data.N; j++)
        {
            f[i][j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "f_" << i + 1 << "_" <<j + 1 ;
            f[i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
    }


    W.resize(Data.V);
    for (int i = 0; i < Data.V; i++)
    {
        W[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            W[i][j]= modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "V_" << i + 1 << "_" << j + 1;
            W[i][j].set(GRB_StringAttr_VarName,nn.str().c_str());
        }
    }

    //new variables
    A.resize(Data.N);
    A_graph.resize(Data.N);
    for (int i = 0; i < Data.N; i++)
    {
        A[i].resize(Data.T);
        A_graph[i].resize(Data.T);
        for (int j = 0; j <Data.T; j++)
        {
            A[i][j]= modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "A_" << i + 1 << "_" << j + 1;
            A[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout << "oley2" << endl;

    NC.resize(Data.V);
    for (int i = 0; i < Data.V; i++)
    {
        NC[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            NC[i][j]= modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "NC_" << i + 1 << "_" << j + 1;
            NC[i][j].set(GRB_StringAttr_VarName,nn.str().c_str());
        }
    }

    //// new variable
    t.resize(Data.V);
    for (int i = 0; i < Data.V; i++)
    {
        t[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            t[i][j]= modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "t_" << i + 1 << "_" << j + 1;
            t[i][j].set(GRB_StringAttr_VarName,nn.str().c_str());
        }
    }



    //we define the objective function
    //we define the objective function
    GRBLinExpr Lat1=0.0;
    GRBLinExpr Latency=0.0;
    GRBLinExpr Cost=0.0;
    GRBLinExpr Cost1=0.0;
    GRBLinExpr Cost2=0.0;
    GRBLinExpr Cost3=0.0;
    GRBLinExpr Cost4=0.0;


    //latency
    for (int i = 0; i < Data.V; i++)
    {
        for (int j = Data.T; j < Data.V; j++) {
            if (i==j) continue;
            //if ((i<Data.T)&(j<Data.T)) continue;
            Lat1 += Data.WR*Data.dist[i][j]* NC[i][j];

        }
    }

    //cost 1
    for (int i = 0; i < Data.V; i++){
        for (int j = 0; j < Data.V; j++) {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            Cost1 += Data.WR*Data.dist[i][j]* X[i][j];

        }
    }


    //cost 4 depots
    for (int i = 0; i < Data.T; i++)
    {
        Cost4 += Data.cost[i]* Y[i];
    }

    //cost 2 vehicles
    for (int j = 0; j < Data.T; ++j) {
        for (int i = Data.T; i < Data.V; i++)
        {
            Cost2 += Data.vehiclesfixed* X[j][i];
        }
    }


    //direct allocation
    GRBLinExpr DirectALL=0;
    for (int i = 0; i < Data.N; i++)
    {
        for (int j = 0; j < Data.T; j++)
        {
            DirectALL += Data.WA*Data.dist[i+Data.T][j]*A[i][j];
        }
    }
    cout << "FO B ok" << endl;

    Latency=Lat1+DirectALL;
    Cost=Cost1+Cost2+Cost4+DirectALL;


    modelo.setObjective(Cost, GRB_MINIMIZE);



    //////// R4 and R5 Each customer must be visited either by a vehicle or by direct allocation /////////
    for (int i = Data.T; i < Data.V; ++i) {
        GRBLinExpr R2=0.0;
        GRBLinExpr R2b=0.0;
        for (int j = 0; j <Data.V ; ++j) {
            if(i==j) continue;
            R2+=X[j][i];
            R2b+=X[i][j];
        }

        GRBLinExpr Rauxi=0.0;
        for (int j = 0; j <Data.T ; ++j) {
            Rauxi+=A[i-Data.T][j];
        }
        modelo.addConstr(R2 +Rauxi==1);
        modelo.addConstr(R2b +Rauxi==1);
    }

    //////// R6,R7 for latency and XXXX for cost: Each customer must be allocated to an open depot:CHECK HERE FOR WRITTING THE MODEL!!! ************************************** /////////
    for (int i = Data.T; i < Data.V; ++i) {
        for (int j = 0; j <Data.T ; ++j) {
            modelo.addConstr(X[j][i] <= f[j][i - Data.T]); //17
            modelo.addConstr(X[i][j] <= f[j][i - Data.T]); //16
            modelo.addConstr(f[j][i - Data.T] <= Y[j]); //15
        }
    }


    //////// R8 flow balance /////////
    for (int i = 0; i < Data.V; ++i) {
        GRBLinExpr R3_a=0.0;
        GRBLinExpr R3_b=0.0;
        for (int j = 0; j <Data.V ; ++j) {
            if(i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            R3_a+=X[i][j];
            R3_b+=X[j][i];
        }
        modelo.addConstr(R3_a-R3_b ==0);
    }
    cout << "R8 ok  "  << endl;

    //////// R9 and R10: Customers can be directly allocated just to an open depot and within the coverage range /////////
    for (int i = Data.T; i < Data.V; ++i) {
        for (int j = 0; j <Data.T ; ++j) {
            modelo.addConstr(Data.dist[i][j]*A[i-Data.T][j] <= Data.Radius*Y[j]);
            modelo.addConstr(A[i-Data.T][j] <= Y[j]);
        }
    }

    /////// R11 and R10: Cumulative demand and number of customers in the routes /////////
    for (int i = Data.T; i < Data.V; i++)
    {
        GRBLinExpr DEM1=0.0;
        GRBLinExpr DEM2=0.0;

        GRBLinExpr NEW1=0.0;
        GRBLinExpr NEW2=0.0;

        GRBLinExpr Rnew=0.0;
        for (int j = 0; j < Data.T; ++j) {
            Rnew+=A[i-Data.T][j];
        }

        for (int j = 0; j < Data.V; j++)
        {
            if (i == j) continue;
            DEM1 += W[i][j];
            DEM2 += W[j][i];

            NEW1 += NC[i][j];
            NEW2 += NC[j][i];
        }
        modelo.addConstr(DEM2 - DEM1 ==(1-Rnew)* Data.MyCustomers[i-Data.T].q);
        //modelo.addConstr(NEW2 - NEW1 == (1-Rnew));
    }


    /////// R13 and R14: Vehicles Capacity and maximum number of customers in a route /////////
    for (int i = 0; i < Data.V; i++)
    {
        for (int j = 0; j < Data.V; j++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            modelo.addConstr(W[i][j] <= (Data.Q)*X[i][j]);
            //modelo.addConstr(NC[i][j] <= (Data.L-2)*X[i][j]);
        }
    }


    /////// R15 and R16: Lower bounds for W and NC/////////
    for (int j = Data.T; j < Data.V; j++)
    {
        for (int i = 0; i < Data.V; i++)
        {
            if (i==j) continue;
            modelo.addConstr(W[i][j]  >= (Data.MyCustomers[j-Data.T].q)*X[i][j]);
            //modelo.addConstr(NC[i][j]  >= X[i][j]);
        }
    }

    ///////// R17: Valid inequalities symmetry breaking
    for (int i = Data.T; i < Data.V; i++)
    {
        for (int j = Data.T; j < Data.V; j++)
        {
            if (i == j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            modelo.addConstr(X[j][i]+X[i][j]<= 1);

        }
    }



/// new things
    //////// Each customer must be allocated to a depot or directly allocated, just for cost/////////
    for (int i = 0; i < Data.N; ++i) {
        GRBLinExpr R1_aux=0.0;
        GRBLinExpr R1_aux_b=0.0;
        for (int j = 0; j <Data.T ; ++j) {
            R1_aux+=f[j][i];
            R1_aux_b+=A[i][j];
        }
        modelo.addConstr(R1_aux+R1_aux_b == 1);
    }



    ///////  consistency on the depots, JUST FOR COST    ***************************/////////
    for (int j = Data.T; j < Data.V; j++) {
        for (int u = Data.T; u < Data.V; u++) {
            if (j == u) continue;
            for (int i = 0; i < Data.T; i++) {
                modelo.addConstr((X[j][u] <= 1 - f[i][j - Data.T] + f[i][u - Data.T]));//new
                modelo.addConstr((X[j][u] <= 1 + f[i][j - Data.T] - f[i][u - Data.T]));//new
            }
        }
    }



    ///// these are new variables for maximum lenght constraints, just for cost
    /////// R9: Cumulative time /////////
    for (int i = Data.T; i < Data.V; i++) {
        GRBLinExpr time1 = 0.0;
        GRBLinExpr time2 = 0.0;
        GRBLinExpr time3 = 0.0;
        GRBLinExpr Tnew = 0.0;
        for (int j = 0; j < Data.T; ++j) {
            Tnew += X[i][j] * Data.dist[i][j];
        }

        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            time1 += t[i][j];
            time2 += t[j][i];
            time3 += Data.dist[j][i] * X[j][i];
        }
        modelo.addConstr(time2 - time1 == time3 + Tnew);

    }
    //cout << " R9 ok" << endl;

    /////// R11: Maximum lengh constraint /////////
    for (int i = 0; i < Data.V; i++) {
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            modelo.addConstr(t[i][j] <= Data.lenghtMax * X[i][j]);
        }
    }
    cout << "R11 ok" << endl;


    /////// Depots capacity constraints: not used by Arslan/////////
    for (int j = 0; j < Data.T; j++)
    {
        GRBLinExpr demandssum=0.0;
        for (int i = 0; i < Data.N; i++)
        {
            demandssum+= (f[j][i]+ A[i][j])*Data.MyCustomers[i].q;
        }
        modelo.addConstr(demandssum  <= Data.MyDepots[j].QD*Y[j]);
    }
    cout << "R12 ok" << endl;




///until here


        modelo.set(GRB_IntParam_Threads,1);
        modelo.set(GRB_DoubleParam_MIPGap,0.0);
        modelo.set(GRB_DoubleParam_TimeLimit,7200);



        modelo.optimize();


        cout << "It's solved correctly" << endl;

        cout << "getStatus = " << modelo.get(GRB_IntAttr_Status)  << endl;
        cout << "getObjValue = " << modelo.get(GRB_DoubleAttr_ObjVal)  << endl;
        cout << "getBestObjValue = " << modelo.get(GRB_DoubleAttr_ObjBound) << endl;
        cout << "getTime = " << modelo.get(GRB_DoubleAttr_Runtime)  << endl;
        cout << "gap = " << modelo.get(GRB_DoubleAttr_MIPGap)  << endl;


        string objectivefun;
        if (Data.OF==0) objectivefun="latency";
        else objectivefun="cost";

        fstream out(results, ios::app);
        //out << instance << "\t"  <<  "2index"<<"\t" << Data.WR<< "\t" << Data.WA<< "\t" << Data.Radius<<"\t" <<modelo.get(GRB_DoubleAttr_ObjVal) << "\t" << modelo.get(GRB_DoubleAttr_ObjBound)<< "\t" << modelo.get(GRB_IntAttr_Status)<< "\t" << modelo.get(GRB_DoubleAttr_Runtime)<< "\t" << modelo.get(GRB_DoubleAttr_MIPGap)<< "\t" << "depots"<<  "\t";

    int NDEP=0;
    int NVE=0;
    double avgratio=0.0;
    out << instance << "\t"  <<  "LoRP_orig" <<"\t" << objectivefun <<"\t" << Data.WR<< "\t" << Data.WA<< "\t" << Data.Radius<<"\t"<< Data.lenghtMax<< "\t"  << Data.f<<"\t" <<modelo.get(GRB_DoubleAttr_ObjVal) << "\t" << modelo.get(GRB_DoubleAttr_ObjBound)<< "\t" << modelo.get(GRB_IntAttr_Status)<< "\t" << modelo.get(GRB_DoubleAttr_Runtime)<< "\t" << modelo.get(GRB_DoubleAttr_MIPGap)<< "\t" <<Cost1.getValue()<< "\t" <<Cost2.getValue()<< "\t" <<Cost4.getValue()<< "\t" <<DirectALL.getValue()<< "\t"<< "depots"<<  "\t";
    for (int i = 0; i < Data.T; i++) {
        double sumademand=0.0;
        for (int k = 0; k < Data.N; k++)
        {
            sumademand+= (f[i][k].get(GRB_DoubleAttr_X)+ A[k][i].get(GRB_DoubleAttr_X))*Data.MyCustomers[k].q;
        }
            if (Y[i].get(GRB_DoubleAttr_X) > 0.0001) {
                int sumV=0;
                for (int j = Data.T; j < Data.V; ++j) {
                    sumV+=round(X[i][j].get(GRB_DoubleAttr_X));
                }
                NVE+=sumV;
                NDEP++;
                avgratio+=100*(sumademand/ Data.MyDepots[i].QD);

                out << "d" << i + 1 << "\t";
                out  <<  Data.MyDepots[i].QD << "\t";
                out  << sumademand << "\t";
                out  << 100*(sumademand/ Data.MyDepots[i].QD) << "\t";
                out <<  sumV << "\t";

            }
    }
    out << "ND"<< "\t" << NDEP << "\t";
    out << "NV"<< "\t" << NVE << "\t";
    out << "RAT"<< "\t" << avgratio/NDEP << "\t";

    out<<endl;
    out.close();


        for (int j = 0; j < Data.V; j++)
        {
            for (int i = 0; i < Data.V; i++)
            {
                if (i==j) continue;
                if ((i<Data.T)&(j<Data.T)) continue;
                X_graph[i][j]=X[i][j].get(GRB_DoubleAttr_X);
            }
        }
        cout<< "X ok "<<endl;

        for (int i = 0; i < Data.T; i++)
        {
            Z_graph[i]=round(Y[i].get(GRB_DoubleAttr_X));
            if (Y[i].get(GRB_DoubleAttr_X)) {
                cout<< "Y_"<<i+1 << " = " << Y[i].get(GRB_DoubleAttr_X) <<endl;
            }
        }

        int direct=0;
        for (int i = 0; i < Data.N; i++)
        {
            for (int r = 0; r <Data.T; r++)
            {
                A_graph[i][r]=round(A[i][r].get(GRB_DoubleAttr_X)*1.0);
                if (A[i][r].get(GRB_DoubleAttr_X)>0.0001) {
                    direct++;
                    cout<< "A_"<<i+1 << "_"<< r+1 <<" = " << A[i][r].get(GRB_DoubleAttr_X) <<endl;
                }
            }
        }



    cout<<"model finished "<<endl;

}

void createmodelnew(string instance, Parameters &Data, string &results, double &of){

    try {

        cout << "Nodos:" << Data.V << endl;
        cout<<"Customers: " << Data.N <<endl;
        cout << "BigM:" << Data.BigM << endl;
        cout << "Vehiculos:" << Data.R << endl;
        cout<<"capacidad: " << Data.Q<<endl;

        string auxname;
        int number=-1;
        for (int i = 0; i < instance.size(); ++i) {
            if(instance[i]== '/') {
                number =i+1;
                break;
            }
        }

        for (int i = number; i < instance.size(); ++i) {
            auxname.push_back(instance[i]);
        }


        int L= Data.L;
        GRBEnv envGur;

        /******* new things ******/

        /// Lofler two index formulation returning to the depot
        string graph2if =auxname+ to_string(Data.Radius)+ to_string(Data.WA)+"solution_cost_2IF_new.gml";
        GRBEnv env_2if;
        vector<vector<GRBVar>> W_2if;
        vector<vector<GRBVar>>X_2if;
        vector<GRBVar>Y_2if;
        vector<vector<bool>>X_graph_2if;
        vector<vector<bool>>A_graph_2if;
        vector<bool>Z_graph_2if;
        vector<vector<GRBVar>> NC_2if;
        vector<vector<GRBVar>>A_2if;
        vector<vector<GRBVar>> f_2if;
        vector<vector<GRBVar>> t_2if;
        LoRP_2IF_new(instance, Data.OF, results, env_2if, Data, X_2if, Y_2if ,W_2if, f_2if, A_2if, NC_2if, t_2if, X_graph_2if, A_graph_2if, Z_graph_2if);
        //GraphLLoRP_withRad_cost(graph2if, Data, X_graph_2if, A_graph_2if, Z_graph_2if);


    }


    catch (...) {
        cerr << "Error" << endl;
    }


}

