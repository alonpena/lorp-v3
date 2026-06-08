//
// Created by alan on 11/12/25.
//

#include "stcmodels.h"

void LRP_DSD(string instance, int obj, string &results, GRBEnv &env, Parameters &Data,  vector<vector<GRBVar>>&Y, vector<vector<GRBVar>>&VVV,  vector<vector<GRBVar>>&X,vector<vector<GRBVar>> &W, vector<vector<GRBVar>> &f,  vector<vector<GRBVar>> &NCCC, vector<vector<GRBVar>> &ttt, vector<vector<bool>>&X_graph, vector<vector<bool>>&A_graph, vector<bool>&Z_graph) {

    cout
            << " ----------------- The problem considered in Tordecilla ITOR, pure Location-Routing, no length constraints -----------------------"
            << endl;

    GRBModel modelo(env);

    //// first stage variables Y: location, V, Vehicles fleet.
    Y.resize(Data.T);
    Z_graph.resize(Data.T);
    for (int j = 0; j < Data.T; j++) {
        Y[j].resize(Data.facsize);
        for (int i = 0; i < Data.facsize; ++i) {
            Y[j][i] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "Y_" << j + 1 << "_"<< i+1;
            Y[j][i].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout<<"y ok"<< endl;


    X.resize(Data.V);
    X_graph.resize(Data.V);
    for (int i = 0; i < Data.V; i++) {
        X[i].resize(Data.V);
        X_graph[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            X[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "X_"  << i + 1 << "_" << j + 1;
            X[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());

        }
    }
    cout<<"x ok"<< endl;


    f.resize(Data.T);
    for (int i = 0; i < Data.T; i++) {
        f[i].resize(Data.N);
        for (int j = 0; j < Data.N; j++) {
            f[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "f_"<< i + 1 << "_" << j + 1;
            f[i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
    }
    cout<<"f ok"<< endl;

    W.resize(Data.V);
    for (int i = 0; i < Data.V; i++) {
        W[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            W[i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "W_"<< i + 1 << "_" << j + 1;
            W[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout<<"W ok"<< endl;


    A_graph.resize(Data.N);
    for (int i = 0; i < Data.N; i++) {
        A_graph[i].resize(Data.T);
        for (int j = 0; j < Data.T; j++) {
        }
    }
    cout << "A_graph ok" << endl;


    //we define the objective function
    GRBLinExpr Cost=0.0;
    GRBLinExpr Cost1=0.0;
    GRBLinExpr Cost2=0.0;
    GRBLinExpr Cost3=0.0;
    GRBLinExpr Cost4=0.0;


    //cost 4 depots
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j < Data.facsize; ++j) {
            Cost4 += Data.dep_cost[i][j]* Y[i][j];
        }
    }

    //cost 2 vehicles
    for (int i = Data.T; i < Data.V; i++)
    {
        for (int j = 0; j < Data.T; ++j) {
            Cost2 += Data.vehiclesfixed* X[j][i];
        }
    }


    //cost 1
    for (int i = 0; i < Data.V; i++) {
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            Cost1 += Data.WR * Data.dist[i][j] * X[i][j];

        }
    }

    Cost=Cost1+Cost2+Cost4;


    modelo.setObjective(Cost, GRB_MINIMIZE);


    /////// R2: maximum number of depots to open, just for latency /////////
    if(Data.OF==0){
        GRBLinExpr R16=0.0;
        for (int i = 0; i < Data.T; ++i) {
            for (int j = 0; j <Data.facsize ; ++j) {
                R16+=Y[i][j];
            }
        }
        modelo.addConstr(R16 <= Data.f);
        cout << "R3 ok  "  << endl;
    }

    //////// R0: depot sizing /////////
    for (int i = 0; i < Data.T; ++i) {
        GRBLinExpr RD=0.0;
        for (int j = 0; j < Data.facsize; ++j) {
            RD+=Y[i][j];
        }
        modelo.addConstr(RD <= 1);// R0
    }

    //////// vehicles can be departed only from open depots /////////
    for (int l = Data.T; l <Data.V ; ++l) {
        for (int i = 0; i < Data.T; ++i) {
            GRBLinExpr RD = 0.0;
            for (int j = 0; j < Data.facsize; ++j) {
                RD += Y[i][j];
            }
            modelo.addConstr(X[i][l] <= RD);//
        }
    }


    //////// R4 and R5 Each customer must be visited either by a vehicle or by direct allocation /////////
    for (int i = Data.T; i < Data.V; ++i) {
        GRBLinExpr R2 = 0.0;
        GRBLinExpr R2b = 0.0;
        for (int j = 0; j < Data.V; ++j) {
            if (i == j) continue;
            R2 += X[j][i];
            R2b += X[i][j];
        }

        modelo.addConstr(R2  == 1);
        modelo.addConstr(R2b  == 1);
    }

    //////// R6,R7 for latency and XXXX for cost: Each customer must be allocated to an open depot:CHECK HERE FOR WRITTING THE MODEL!!! ************************************** /////////
    for (int i = Data.T; i < Data.V; ++i) {
        for (int j = 0; j < Data.T; ++j) {
            GRBLinExpr RD=0.0;
            for (int x = 0; x < Data.facsize; ++x) {
                RD+=Y[j][x];
            }
            if (Data.OF == 0) {
                modelo.addConstr(X[j][i] <= RD);
                modelo.addConstr(X[i][j] <= RD);
            }

            if (Data.OF == 1) {
                modelo.addConstr(X[j][i] <= f[j][i - Data.T]); //17
                modelo.addConstr(X[i][j] <= f[j][i - Data.T]); //16
                modelo.addConstr(f[j][i - Data.T] <= RD); //15
            }
        }
    }


    //////// R8 flow balance /////////
    for (int i = 0; i < Data.V; ++i) {
        GRBLinExpr R3_a = 0.0;
        GRBLinExpr R3_b = 0.0;
        for (int j = 0; j < Data.V; ++j) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            R3_a += X[i][j];
            R3_b += X[j][i];

        }
        modelo.addConstr(R3_a - R3_b == 0);
    }
    cout << "R8 ok  " << endl;


    /////// R11 and R10: Cumulative demand and number of customers in the routes /////////
    for (int i = Data.T; i < Data.V; i++) {
        GRBLinExpr DEM1 = 0.0;
        GRBLinExpr DEM2 = 0.0;

        GRBLinExpr NEW1 = 0.0;
        GRBLinExpr NEW2 = 0.0;


        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            DEM1 += W[i][j];
            DEM2 += W[j][i];

            //NEW1 += NC[i][j];
            //NEW2 += NC[j][i];
        }
        modelo.addConstr(DEM2 - DEM1 ==  Data.MyCustomers[i - Data.T].q);
        //modelo.addConstr(NEW2 - NEW1 == 1);
    }


    /////// R13 and R14: Vehicles Capacity and maximum number of customers in a route /////////
    for (int i = 0; i < Data.V; i++) {
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            modelo.addConstr(W[i][j] <= (Data.Q) * X[i][j]);
            //modelo.addConstr(NC[i][j] <= (Data.L - 2) * X[i][j]);
        }
    }


    /////// R15 and R16: Lower bounds for W and NC/////////
    for (int j = Data.T; j < Data.V; j++) {
        for (int i = 0; i < Data.V; i++) {
            if (i == j) continue;
            modelo.addConstr(W[i][j] >= (Data.MyCustomers[j - Data.T].q) * X[i][j]);
            //modelo.addConstr(NC[i][j] >= X[i][j]);
        }
    }

    ///////// R17: Valid inequalities symmetry breaking
    for (int i = Data.T; i < Data.V; i++) {
        for (int j = Data.T; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            modelo.addConstr(X[j][i] + X[i][j] <= 1);

        }
    }


/// new things
    //////// Each customer must be allocated to a depot or directly allocated, just for cost/////////
    if (Data.OF == 1) {
        for (int i = 0; i < Data.N; ++i) {
            GRBLinExpr R1_aux = 0.0;
            for (int j = 0; j < Data.T; ++j) {
                R1_aux += f[j][i];
            }
            modelo.addConstr(R1_aux == 1);
        }
    }


    ///////  consistency on the depots, JUST FOR COST    ***************************/////////
    if (Data.OF == 1) {
        for (int j = Data.T; j < Data.V; j++) {
            for (int u = Data.T; u < Data.V; u++) {
                if (j == u) continue;
                for (int i = 0; i < Data.T; i++) {
                    modelo.addConstr((X[j][u] <= 1 - f[i][j - Data.T] + f[i][u - Data.T]));//new
                    modelo.addConstr((X[j][u] <= 1 + f[i][j - Data.T] - f[i][u - Data.T]));//new
                }
            }
        }
    }


    /////// Depots capacity constraints: not used by Arslan/////////

    for (int j = 0; j < Data.T; j++)
    {
        GRBLinExpr demandssum=0.0;
        for (int i = 0; i < Data.N; i++)
        {
            demandssum+= (f[j][i])*Data.MyCustomers[i].q;
        }

        GRBLinExpr sizesum=0.0;
        for (int x = 0; x < Data.facsize; ++x) {
            sizesum+=Data.dep_cap[j][x]*Y[j][x];
        }
        modelo.addConstr(demandssum  <= sizesum);

    }
    cout << "R12 ok" << endl;

///until here




    //modelo.set(GRB_IntParam_Threads,1);
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

    out << instance << "\t"  <<  "2index" <<"\t" << objectivefun <<"\t" << Data.WR<< "\t" << Data.WA<< "\t" << Data.Radius<<"\t"<< Data.lenghtMax<< "\t"  << Data.f<<"\t" <<modelo.get(GRB_DoubleAttr_ObjVal) << "\t" << modelo.get(GRB_DoubleAttr_ObjBound)<< "\t" << modelo.get(GRB_IntAttr_Status)<< "\t" << modelo.get(GRB_DoubleAttr_Runtime)<< "\t" << modelo.get(GRB_DoubleAttr_MIPGap)<< "\t" <<Cost1.getValue()<< "\t" <<Cost2.getValue()<< "\t" <<Cost4.getValue()<< "\t"<< "depots"<<  "\t";
    for (int i = 0; i < Data.T; i++) {
        for (int x = 0; x < Data.facsize; ++x) {
            if (Y[i][x].get(GRB_DoubleAttr_X) > 0.0001) {
                int sumV=0;
                for (int j = Data.T; j < Data.V; ++j) {
                    sumV+=round(X[i][j].get(GRB_DoubleAttr_X));
                }
                out << "d" << i + 1 << "\t";
                out << "s" << x + 1 << "\t";
                out <<  sumV << "\t";

            }
        }

    }
    out<<endl;
    out.close();



    ///// for graph, determinisitc ///
    for (int i = 0; i < Data.T; i++)
    {
        int sumz=0;
        for (int j = 0; j < Data.facsize; ++j) {
            sumz+=round(Y[i][j].get(GRB_DoubleAttr_X));
        }
        Z_graph[i]=round(sumz);
    }
    cout<<"z ok" <<endl;


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

    int direct=0;
    for (int i = 0; i < Data.N; i++)
    {
        for (int r = 0; r <Data.T; r++)
        {
            A_graph[i][r]=0;
        }
    }



    cout<<"model finished "<<endl;

}

void create_LRPDSD(string instance, Parameters &Data, string &results, double &of){

    cout<<" creating the (deterministic) LRP with sizing decisions, studied by Tordecilla " <<endl ;

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
        /// Lofler two index formulation returning to the depot
        string graph2if =auxname+ to_string(Data.Radius)+ to_string(Data.WA)+"solution_cost_2IF_new.gml";
        GRBEnv env_2if;
        vector<vector<GRBVar>> W_2if;
        vector<vector<GRBVar>>X_2if;

        vector<vector<bool>>X_graph_2if;
        vector<vector<bool>>A_graph_2if;
        vector<bool>Z_graph_2if;
        vector<vector<GRBVar>> NC_2if;
        vector<vector<GRBVar>> f_2if;
        vector<vector<GRBVar>> t_2if;


        //vector<GRBVar>Y_2if; //location
        vector<vector<GRBVar>>Y_2if;
        vector<vector<GRBVar>> V_2if; //fleet size,fleet alloc.


        LRP_DSD(instance, Data.OF, results, env_2if, Data, Y_2if, V_2if,  X_2if ,W_2if, f_2if, NC_2if, t_2if, X_graph_2if, A_graph_2if, Z_graph_2if);
        GraphLLoRP_withRad_cost(graph2if, Data, X_graph_2if, A_graph_2if, Z_graph_2if);

    }

    catch (...) {
        cerr << "Error" << endl;
    }


}

void det_LoRP_DSD(string instance, int obj, string &results, GRBEnv &env, Parameters &Data,  vector<vector<GRBVar>>&Y, vector<vector<GRBVar>>&VVV,  vector<vector<GRBVar>>&X,vector<vector<GRBVar>> &W, vector<vector<GRBVar>> &f,vector<vector<GRBVar>>&A,  vector<vector<GRBVar>> &NCC, vector<vector<GRBVar>> &t, vector<vector<bool>>&X_graph, vector<vector<bool>>&A_graph, vector<bool>&Z_graph) {

    cout
            << " ----------------- LoRP_DSD: This model is deterministic and includes depot sizing decisions, direct allocation included -----------------------"
            << endl;

    GRBModel modelo(env);

    //// first stage variables Y: location, V, Vehicles fleet.
    Y.resize(Data.T);
    Z_graph.resize(Data.T);
    for (int j = 0; j < Data.T; j++) {
        Y[j].resize(Data.facsize);
        for (int i = 0; i < Data.facsize; ++i) {
            Y[j][i] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "Y_" << j + 1 << "_"<< i+1;
            Y[j][i].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout<<"y ok"<< endl;

    /*
    V.resize(Data.R);
    for (int i = 0; i < Data.R; i++) {
        V[i].resize(Data.T);
        for (int j = 0; j < Data.T; j++) {
            V[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "V_" << i + 1 << "_" << j + 1;
            V[i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
    }
    cout<<"V ok"<< endl;
*/


    X.resize(Data.V);
    X_graph.resize(Data.V);
    for (int i = 0; i < Data.V; i++) {
        X[i].resize(Data.V);
        X_graph[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            X[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "X_"  << i + 1 << "_" << j + 1;
            X[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());

        }
    }
    cout<<"x ok"<< endl;


    f.resize(Data.T);
    for (int i = 0; i < Data.T; i++) {
        f[i].resize(Data.N);
        for (int j = 0; j < Data.N; j++) {
            f[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "f_"<< i + 1 << "_" << j + 1;
            f[i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
    }
    cout<<"f ok"<< endl;

    W.resize(Data.V);
    for (int i = 0; i < Data.V; i++) {
        W[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            W[i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "W_"<< i + 1 << "_" << j + 1;
            W[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout<<"W ok"<< endl;

    //new variables
    A.resize(Data.N);
    A_graph.resize(Data.N);
    for (int i = 0; i < Data.N; i++) {
        A[i].resize(Data.T);
        A_graph[i].resize(Data.T);
        for (int j = 0; j < Data.T; j++) {
            A[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "A_"<< i + 1 << "_" << j + 1;
            A[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout << "A ok" << endl;

    /*
    NC.resize(Data.V);
    for (int i = 0; i < Data.V; i++) {
        NC[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            NC[i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "NC_"<< i + 1 << "_" << j + 1;
            NC[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout<<"nc ok"<< endl;
*/

    //// new variable
    t.resize(Data.V);
    for (int i = 0; i < Data.V; i++) {
        t[i].resize(Data.V);
        for (int j = 0; j < Data.V; j++) {
            if (i == j) continue;
            if ((i < Data.T) & (j < Data.T)) continue;
            t[i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
            std::stringstream nn;
            nn << "t_"<< i + 1 << "_" << j + 1;
            t[i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout<<"t ok"<< endl;



    //we define the objective function
    GRBLinExpr Cost=0.0;
    GRBLinExpr Cost1=0.0;
    GRBLinExpr Cost2=0.0;
    GRBLinExpr Cost3=0.0;
    GRBLinExpr Cost4=0.0;
    GRBLinExpr DirectALL = 0;

    //cost 4 depots
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j < Data.facsize; ++j) {
            Cost4 += Data.dep_cost[i][j]* Y[i][j];
        }
    }

    //cost 2 vehicles
    for (int i = Data.T; i < Data.V; i++)
    {
        for (int j = 0; j < Data.T; ++j) {
            Cost2 += Data.vehiclesfixed* X[j][i];
        }
    }


        //cost 1
        for (int i = 0; i < Data.V; i++) {
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                Cost1 += Data.WR * Data.dist[i][j] * X[i][j];

            }
        }

        //direct allocation
        for (int i = 0; i < Data.N; i++) {
            for (int j = 0; j < Data.T; j++) {
                DirectALL += Data.WA * Data.dist[i + Data.T][j] * A[i][j];
            }
        }
        cout << "FO B ok" << endl;

    Cost=Cost1+Cost2+Cost4+DirectALL;


 modelo.setObjective(Cost, GRB_MINIMIZE);


    /////// R2: maximum number of depots to open, just for latency /////////
    /*
    if(Data.OF==0){
        GRBLinExpr R16=0.0;
        for (int i = 0; i < Data.T; ++i) {
            for (int j = 0; j <Data.facsize ; ++j) {
                R16+=Y[i][j];
            }
        }
        modelo.addConstr(R16 <= Data.f);
        cout << "R3 ok  "  << endl;
    }
     */

    //////// R0: depot sizing /////////
    for (int i = 0; i < Data.T; ++i) {
        GRBLinExpr RD=0.0;
        for (int j = 0; j < Data.facsize; ++j) {
            RD+=Y[i][j];
        }
        modelo.addConstr(RD <= 1);// R0
    }

    //////// vehicles can be departed only from open depots /////////
    for (int l = Data.T; l <Data.V ; ++l) {
        for (int i = 0; i < Data.T; ++i) {
            GRBLinExpr RD = 0.0;
            for (int j = 0; j < Data.facsize; ++j) {
                RD += Y[i][j];
            }
            modelo.addConstr(X[i][l] <= RD);//
        }
    }



    //////// R3: A maximum of k vehicles can be used, just for latency /////////
    /*
    if(Data.OF==0) {
        for (int i = 0; i < Data.T; ++i) {
            GRBLinExpr R17A = 0.0;
            for (int j = Data.T; j < Data.V; ++j) {
                R17A += X[i][j];
            }
            modelo.addConstr(R17A <= Data.R);// we may use less than or equal to
        }
    }
     */


        //////// R4 and R5 Each customer must be visited either by a vehicle or by direct allocation /////////
        for (int i = Data.T; i < Data.V; ++i) {
            GRBLinExpr R2 = 0.0;
            GRBLinExpr R2b = 0.0;
            for (int j = 0; j < Data.V; ++j) {
                if (i == j) continue;
                R2 += X[j][i];
                R2b += X[i][j];
            }

            GRBLinExpr Rauxi = 0.0;
            for (int j = 0; j < Data.T; ++j) {
                Rauxi += A[i - Data.T][j];
            }
            modelo.addConstr(R2 + Rauxi == 1);
            modelo.addConstr(R2b + Rauxi == 1);
        }

        //////// R6,R7 for latency and XXXX for cost: Each customer must be allocated to an open depot:CHECK HERE FOR WRITTING THE MODEL!!! ************************************** /////////
        for (int i = Data.T; i < Data.V; ++i) {
            for (int j = 0; j < Data.T; ++j) {
                GRBLinExpr RD=0.0;
                for (int x = 0; x < Data.facsize; ++x) {
                    RD+=Y[j][x];
                }
                if (Data.OF == 0) {
                    modelo.addConstr(X[j][i] <= RD);
                    modelo.addConstr(X[i][j] <= RD);
                }

                if (Data.OF == 1) {
                    modelo.addConstr(X[j][i] <= f[j][i - Data.T]); //17
                    modelo.addConstr(X[i][j] <= f[j][i - Data.T]); //16
                    modelo.addConstr(f[j][i - Data.T] <= RD); //15
                }
            }
        }


        //////// R8 flow balance /////////
        for (int i = 0; i < Data.V; ++i) {
            GRBLinExpr R3_a = 0.0;
            GRBLinExpr R3_b = 0.0;
            for (int j = 0; j < Data.V; ++j) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                R3_a += X[i][j];
                R3_b += X[j][i];

            }
            modelo.addConstr(R3_a - R3_b == 0);
        }
        cout << "R8 ok  " << endl;

        //////// R9 and R10: Customers can be directly allocated just to an open depot and within the coverage range /////////
        for (int i = Data.T; i < Data.V; ++i) {
            for (int j = 0; j < Data.T; ++j) {
                GRBLinExpr RD=0.0;
                for (int x = 0; x < Data.facsize; ++x) {
                    RD+=Data.Radius *Y[j][x];
                }

                modelo.addConstr(Data.dist[i][j] * A[i - Data.T][j] <=  RD);
                modelo.addConstr(A[i - Data.T][j] <= RD);
            }
        }

        /////// R11 and R10: Cumulative demand and number of customers in the routes /////////
        for (int i = Data.T; i < Data.V; i++) {
            GRBLinExpr DEM1 = 0.0;
            GRBLinExpr DEM2 = 0.0;

            //GRBLinExpr NEW1 = 0.0;
            //GRBLinExpr NEW2 = 0.0;

            GRBLinExpr Rnew = 0.0;
            for (int j = 0; j < Data.T; ++j) {
                Rnew += A[i - Data.T][j];
            }

            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                DEM1 += W[i][j];
                DEM2 += W[j][i];

                //NEW1 += NC[i][j];
                //NEW2 += NC[j][i];
            }
            modelo.addConstr(DEM2 - DEM1 == (1 - Rnew) * Data.MyCustomers[i - Data.T].q);
            //modelo.addConstr(NEW2 - NEW1 == (1 - Rnew));
        }


        /////// R13 and R14: Vehicles Capacity and maximum number of customers in a route /////////
        for (int i = 0; i < Data.V; i++) {
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                modelo.addConstr(W[i][j] <= (Data.Q) * X[i][j]);
               // modelo.addConstr(NC[i][j] <= (Data.L - 2) * X[i][j]);
            }
        }


        /////// R15 and R16: Lower bounds for W and NC/////////
        for (int j = Data.T; j < Data.V; j++) {
            for (int i = 0; i < Data.V; i++) {
                if (i == j) continue;
                modelo.addConstr(W[i][j] >= (Data.MyCustomers[j - Data.T].q) * X[i][j]);
                //modelo.addConstr(NC[i][j] >= X[i][j]);
            }
        }

        ///////// R17: Valid inequalities symmetry breaking
        for (int i = Data.T; i < Data.V; i++) {
            for (int j = Data.T; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                modelo.addConstr(X[j][i] + X[i][j] <= 1);

            }
        }


/// new things
        //////// Each customer must be allocated to a depot or directly allocated, just for cost/////////
        if (Data.OF == 1) {
            for (int i = 0; i < Data.N; ++i) {
                GRBLinExpr R1_aux = 0.0;
                GRBLinExpr R1_aux_b = 0.0;
                for (int j = 0; j < Data.T; ++j) {
                    R1_aux += f[j][i];
                    R1_aux_b += A[i][j];
                }
                modelo.addConstr(R1_aux + R1_aux_b == 1);
            }
        }


        ///////  consistency on the depots, JUST FOR COST    ***************************/////////
        if (Data.OF == 1) {
            for (int j = Data.T; j < Data.V; j++) {
                for (int u = Data.T; u < Data.V; u++) {
                    if (j == u) continue;
                    for (int i = 0; i < Data.T; i++) {
                        modelo.addConstr((X[j][u] <= 1 - f[i][j - Data.T] + f[i][u - Data.T]));//new
                        modelo.addConstr((X[j][u] <= 1 + f[i][j - Data.T] - f[i][u - Data.T]));//new
                    }
                }
            }
        }



        ///// these are new variables for maximum lenght constraints, just for cost
        /////// R9: Cumulative time /////////
        if (Data.OF == 1) {
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
        }

        /////// Depots capacity constraints: not used by Arslan/////////

        for (int j = 0; j < Data.T; j++)
        {
            GRBLinExpr demandssum=0.0;
            for (int i = 0; i < Data.N; i++)
            {
                demandssum+= (f[j][i]+ A[i][j])*Data.MyCustomers[i].q;
            }

            GRBLinExpr sizesum=0.0;
            for (int x = 0; x < Data.facsize; ++x) {
                sizesum+=Data.dep_cap[j][x]*Y[j][x];
            }
            modelo.addConstr(demandssum  <= sizesum);

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
    out << instance << "\t"  <<  "LoRP-SD" <<"\t" << objectivefun <<"\t" << Data.WR<< "\t" << Data.WA<< "\t" << Data.Radius<<"\t"<< Data.lenghtMax<< "\t"  << Data.f<<"\t" <<modelo.get(GRB_DoubleAttr_ObjVal) << "\t" << modelo.get(GRB_DoubleAttr_ObjBound)<< "\t" << modelo.get(GRB_IntAttr_Status)<< "\t" << modelo.get(GRB_DoubleAttr_Runtime)<< "\t" << modelo.get(GRB_DoubleAttr_MIPGap)<< "\t" <<Cost1.getValue()<< "\t" <<Cost2.getValue()<< "\t" <<Cost4.getValue()<< "\t" <<DirectALL.getValue()<< "\t"<< "depots"<<  "\t";
    for (int i = 0; i < Data.T; i++) {
        double sumademand=0.0;
        for (int k = 0; k < Data.N; k++)
        {
            sumademand+= (f[i][k].get(GRB_DoubleAttr_X)+ A[k][i].get(GRB_DoubleAttr_X))*Data.MyCustomers[k].q;
        }
        for (int x = 0; x < Data.facsize; ++x) {
            if (Y[i][x].get(GRB_DoubleAttr_X) > 0.0001) {
                int sumV=0;
                for (int j = Data.T; j < Data.V; ++j) {
                    sumV+=round(X[i][j].get(GRB_DoubleAttr_X));
                }
                NVE+=sumV;
                NDEP++;
                avgratio+=100*(sumademand/Data.dep_cap[i][x]);

                out << "d" << i + 1 << "\t";
                out << "s" << "\t" << x + 1 << "\t";
                out  << Data.dep_cap[i][x] << "\t";
                out  << sumademand << "\t";
                out  << 100*(sumademand/Data.dep_cap[i][x]) << "\t";
                out <<  sumV << "\t";

            }
        }
    }
    out << "ND"<< "\t" << NDEP << "\t";
    out << "NV"<< "\t" << NVE << "\t";
    out << "RAT"<< "\t" << avgratio/NDEP << "\t";

    out<<endl;
    out.close();


    int sumv=0;
    for (int i = Data.T; i < Data.V; ++i) {
        for (int j = 0; j < Data.T; ++j) {
            if (X[j][i].get(GRB_DoubleAttr_X) > 0.0001) cout<< " V_ "<< i+1 << " _ D_ " << j+1 << endl;
            sumv+=round (X[j][i].get(GRB_DoubleAttr_X));
        }
    }
    cout<<" total vehicles departed: " << sumv <<endl;



    ///// for graph, determinisitc ///
    for (int i = 0; i < Data.T; i++)
    {
        int sumz=0;
        for (int j = 0; j < Data.facsize; ++j) {
            sumz+=round(Y[i][j].get(GRB_DoubleAttr_X));
        }
        Z_graph[i]=round(sumz);
    }
    cout<<"z ok" <<endl;


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

void create_detLoRP_sizing(string instance, Parameters &Data, string &results, double &of){

    cout<<" creating the (deterministic) LoRP with sizing decisions, this problem is new" <<endl ;

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
        /// Lofler two index formulation returning to the depot
        string graph2if =auxname+ to_string(Data.Radius)+ to_string(Data.WA)+"solution_cost_2IF_new.gml";
        GRBEnv env_2if;
        vector<vector<GRBVar>> W_2if;
        vector<vector<GRBVar>>X_2if;

        vector<vector<bool>>X_graph_2if;
        vector<vector<bool>>A_graph_2if;
        vector<bool>Z_graph_2if;
        vector<vector<GRBVar>> NC_2if;
        vector<vector<GRBVar>>A_2if;
        vector<vector<GRBVar>> f_2if;
        vector<vector<GRBVar>> t_2if;


        //vector<GRBVar>Y_2if; //location
        vector<vector<GRBVar>>Y_2if;
        vector<vector<GRBVar>> V_2if; //fleet size,fleet alloc.


        det_LoRP_DSD(instance, Data.OF, results, env_2if, Data, Y_2if, V_2if,  X_2if ,W_2if, f_2if, A_2if, NC_2if, t_2if, X_graph_2if, A_graph_2if, Z_graph_2if);
        //GraphLLoRP_withRad_cost(graph2if, Data, X_graph_2if, A_graph_2if, Z_graph_2if);

    }

    catch (...) {
        cerr << "Error" << endl;
    }


}

void LoRPSD_DS_2IF(string instance, int obj, string &results, GRBEnv &env, Parameters &Data,  vector<vector<GRBVar>>&Y, vector<vector<GRBVar>>&V, vector<vector<GRBVar>>&NSC,  vector<vector<vector<GRBVar>>>&X, vector<vector<vector<GRBVar>>> &W, vector<vector<vector<GRBVar>>> &f, vector<vector<vector<GRBVar>>>&A,  vector<vector<vector<GRBVar>>> &NC, vector<vector<vector<GRBVar>>> &t, vector<vector<bool>>&X_graph, vector<vector<bool>>&A_graph, vector<bool>&Z_graph) {

    cout
            << " ----------------- This model is considers stochastic demand and depot sizing -----------------------"
            << endl;

    GRBModel modelo(env);

    //// first stage variables Y: location, V, Vehicles fleet.
    Y.resize(Data.T);
    Z_graph.resize(Data.T);
    for (int j = 0; j < Data.T; j++) {
        Y[j].resize(Data.facsize);
        for (int i = 0; i < Data.facsize; ++i) {
            Y[j][i] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nn;
            nn << "Y_" << j + 1 << "_"<< i+1;
            Y[j][i].set(GRB_StringAttr_VarName, nn.str().c_str());
        }
    }
    cout<<"y ok"<< endl;

    V.resize(Data.R);
    for (int i = 0; i < Data.R; i++) {
        V[i].resize(Data.T);
        for (int j = 0; j < Data.T; j++) {
            V[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "V_" << i + 1 << "_" << j + 1;
            V[i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
    }
    cout<<"V ok"<< endl;



    //// second stage variables
    X.resize(Data.Omega);
    f.resize(Data.Omega);
    W.resize(Data.Omega);
    A.resize(Data.Omega);
    NC.resize(Data.Omega);
    t.resize(Data.Omega);
    NSC.resize(Data.Omega);

    for (int s = 0; s < Data.Omega; ++s) {

        NSC[s].resize(Data.N);
        for (int j = 0; j < Data.N; j++) {
            NSC[s][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "NSC_" << s + 1 << "_" << j + 1;
            NSC[s][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
        cout<<"NSC ok"<< endl;

        X[s].resize(Data.V);
        X_graph.resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            X[s][i].resize(Data.V);
            X_graph[i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                X[s][i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
                std::stringstream nn;
                nn << "X_" << s + 1 << "_" << i + 1 << "_" << j + 1;
                X[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());

            }
        }
        cout<<"x ok"<< endl;


        f[s].resize(Data.T);
        for (int i = 0; i < Data.T; i++) {
            f[s][i].resize(Data.N);
            for (int j = 0; j < Data.N; j++) {
                f[s][i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
                std::stringstream nnn;
                nnn << "f_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                f[s][i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
            }
        }
        cout<<"f ok"<< endl;

        W[s].resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            W[s][i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                W[s][i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
                std::stringstream nn;
                nn << "W_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                W[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout<<"W ok"<< endl;

        //new variables
        A[s].resize(Data.N);
        A_graph.resize(Data.N);
        for (int i = 0; i < Data.N; i++) {
            A[s][i].resize(Data.T);
            A_graph[i].resize(Data.T);
            for (int j = 0; j < Data.T; j++) {
                A[s][i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
                std::stringstream nn;
                nn << "A_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                A[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout << "A ok" << endl;

        NC[s].resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            NC[s][i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                NC[s][i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
                std::stringstream nn;
                nn << "NC_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                NC[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout<<"nc ok"<< endl;

        //// new variable
        t[s].resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            t[s][i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                t[s][i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
                std::stringstream nn;
                nn << "t_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                t[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout<<"t ok"<< endl;
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
    GRBLinExpr DirectALL = 0;

    //cost 4 depots
    for (int i = 0; i < Data.T; i++)
    {
        for (int j = 0; j < Data.facsize; ++j) {
            Cost4 += Data.dep_cost[i][j]* Y[i][j];
        }
    }

    //cost 2 vehicles
    for (int i = 0; i < Data.R; i++)
    {
        for (int j = 0; j < Data.T; ++j) {
            Cost2 += Data.vehiclesfixed* V[i][j];
        }
    }

    for (int s = 0; s < Data.Omega; ++s) {

        //latency
        for (int i = 0; i < Data.V; i++) {
            for (int j = Data.T; j < Data.V; j++) {
                if (i == j) continue;
                //if ((i<Data.T)&(j<Data.T)) continue;
                Lat1 += Data.WR * Data.dist[i][j] * NC[s][i][j];

            }
        }

        //cost 1
        for (int i = 0; i < Data.V; i++) {
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                Cost1 += Data.WR * Data.dist[i][j] * X[s][i][j];

            }
        }

        //direct allocation
        for (int i = 0; i < Data.N; i++) {
            for (int j = 0; j < Data.T; j++) {
                DirectALL += Data.WA * Data.dist[i + Data.T][j] * A[s][i][j];
            }
        }
        cout << "FO B ok" << endl;

        //penalty for not serving a customer
        for (int i = 0; i < Data.N; i++)
        {
            Cost4 += Data.penalty* NSC[s][i];
        }


    }

    Latency=Lat1+DirectALL;
    Cost=Cost1+Cost2+Cost4+DirectALL;



    if(obj==0) modelo.setObjective(Latency, GRB_MINIMIZE);
    else  modelo.setObjective(Cost, GRB_MINIMIZE);


    /////// R2: maximum number of depots to open, just for latency /////////
    if(Data.OF==0){
        GRBLinExpr R16=0.0;
        for (int i = 0; i < Data.T; ++i) {
            for (int j = 0; j <Data.facsize ; ++j) {
                R16+=Y[i][j];
            }
        }
        modelo.addConstr(R16 <= Data.f);
        cout << "R3 ok  "  << endl;
    }

    //////// R0: depot sizing /////////
    for (int i = 0; i < Data.T; ++i) {
        GRBLinExpr RD=0.0;
        for (int j = 0; j < Data.facsize; ++j) {
            RD+=Y[i][j];
        }
        modelo.addConstr(RD <= 1);// R0
    }

    //////// RA, RB: fleet sizing /////////
    for (int k = 0; k < Data.R; ++k) {
        GRBLinExpr RA=0.0;
        for (int i = 0; i < Data.T; ++i) {
            RA+=V[k][i];

            GRBLinExpr RD=0.0;
            for (int j = 0; j < Data.facsize; ++j) {
                RD+=Y[i][j];
            }
            modelo.addConstr(V[k][i] <= RD);// RB
        }
        modelo.addConstr(RA <= 1);// RA
    }



    //// Second stage: the following constraints are valid for each scenario
    for (int s = 0; s < Data.Omega; ++s) {

        //////// R3: A maximum of k vehicles can be used, just for latency /////////
        for (int i = 0; i < Data.T; ++i) {
            GRBLinExpr R17A=0.0;
            GRBLinExpr R17B=0.0;
            for (int j = Data.T; j <Data.V ; ++j) {
                R17A+=X[s][i][j];
            }
            for (int k = 0; k <Data.R ; ++k) {
                R17B+=V[k][i];
            }
            modelo.addConstr(R17A == R17B);// we may use less than or equal to
        }


    //////// R4 and R5 Each customer must be visited either by a vehicle or by direct allocation /////////
        for (int i = Data.T; i < Data.V; ++i) {
            GRBLinExpr R2 = 0.0;
            GRBLinExpr R2b = 0.0;
            for (int j = 0; j < Data.V; ++j) {
                if (i == j) continue;
                R2 += X[s][j][i];
                R2b += X[s][i][j];
            }

            GRBLinExpr Rauxi = 0.0;
            for (int j = 0; j < Data.T; ++j) {
                Rauxi += A[s][i - Data.T][j];
            }
            modelo.addConstr(R2 + Rauxi == 1);
            modelo.addConstr(R2b + Rauxi == 1);
        }

        //////// R6,R7 for latency and XXXX for cost: Each customer must be allocated to an open depot:CHECK HERE FOR WRITTING THE MODEL!!! ************************************** /////////
        for (int i = Data.T; i < Data.V; ++i) {
            for (int j = 0; j < Data.T; ++j) {
                GRBLinExpr RD=0.0;
                for (int x = 0; x < Data.facsize; ++x) {
                    RD+=Y[j][x];
                }
                if (Data.OF == 0) {
                    modelo.addConstr(X[s][j][i] <= RD);
                    modelo.addConstr(X[s][i][j] <= RD);
                }

                if (Data.OF == 1) {
                    modelo.addConstr(X[s][j][i] <= f[s][j][i - Data.T]); //17
                    modelo.addConstr(X[s][i][j] <= f[s][j][i - Data.T]); //16
                    modelo.addConstr(f[s][j][i - Data.T] <= RD); //15
                }
            }
        }


        //////// R8 flow balance /////////
        for (int i = 0; i < Data.V; ++i) {
            GRBLinExpr R3_a = 0.0;
            GRBLinExpr R3_b = 0.0;
            for (int j = 0; j < Data.V; ++j) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                R3_a += X[s][i][j];
                R3_b += X[s][j][i];

            }
            modelo.addConstr(R3_a - R3_b == 0);
        }
        cout << "R8 ok  " << endl;

        //////// R9 and R10: Customers can be directly allocated just to an open depot and within the coverage range /////////
        for (int i = Data.T; i < Data.V; ++i) {
            for (int j = 0; j < Data.T; ++j) {
                GRBLinExpr RD=0.0;
                for (int x = 0; x < Data.facsize; ++x) {
                    RD+=Data.Radius *Y[j][x];
                }

                modelo.addConstr(Data.dist[i][j] * A[s][i - Data.T][j] <=  RD);
                modelo.addConstr(A[s][i - Data.T][j] <= RD);
            }
        }

        /////// R11 and R10: Cumulative demand and number of customers in the routes /////////
        for (int i = Data.T; i < Data.V; i++) {
            GRBLinExpr DEM1 = 0.0;
            GRBLinExpr DEM2 = 0.0;

            GRBLinExpr NEW1 = 0.0;
            GRBLinExpr NEW2 = 0.0;

            GRBLinExpr Rnew = 0.0;
            for (int j = 0; j < Data.T; ++j) {
                Rnew += A[s][i - Data.T][j];
            }

            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                DEM1 += W[s][i][j];
                DEM2 += W[s][j][i];

                NEW1 += NC[s][i][j];
                NEW2 += NC[s][j][i];
            }
            modelo.addConstr(DEM2 - DEM1 == (1 - Rnew) * Data.MyCustomers[i - Data.T].q);
            modelo.addConstr(NEW2 - NEW1 == (1 - Rnew));
        }


        /////// R13 and R14: Vehicles Capacity and maximum number of customers in a route /////////
        for (int i = 0; i < Data.V; i++) {
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                modelo.addConstr(W[s][i][j] <= (Data.Q) * X[s][i][j]);
                modelo.addConstr(NC[s][i][j] <= (Data.L - 2) * X[s][i][j]);
            }
        }


        /////// R15 and R16: Lower bounds for W and NC/////////
        for (int j = Data.T; j < Data.V; j++) {
            for (int i = 0; i < Data.V; i++) {
                if (i == j) continue;
                modelo.addConstr(W[s][i][j] >= (Data.MyCustomers[j - Data.T].q) * X[s][i][j]);
                modelo.addConstr(NC[s][i][j] >= X[s][i][j]);
            }
        }

        ///////// R17: Valid inequalities symmetry breaking
        for (int i = Data.T; i < Data.V; i++) {
            for (int j = Data.T; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                modelo.addConstr(X[s][j][i] + X[s][i][j] <= 1);

            }
        }


/// new things
        //////// Each customer must be allocated to a depot or directly allocated, just for cost/////////
        if (Data.OF == 1) {
            for (int i = 0; i < Data.N; ++i) {
                GRBLinExpr R1_aux = 0.0;
                GRBLinExpr R1_aux_b = 0.0;
                for (int j = 0; j < Data.T; ++j) {
                    R1_aux += f[s][j][i];
                    R1_aux_b += A[s][i][j];
                }
                modelo.addConstr(R1_aux + R1_aux_b == 1);
            }
        }


        ///////  consistency on the depots, JUST FOR COST    ***************************/////////
        if (Data.OF == 1) {
            for (int j = Data.T; j < Data.V; j++) {
                for (int u = Data.T; u < Data.V; u++) {
                    if (j == u) continue;
                    for (int i = 0; i < Data.T; i++) {
                        modelo.addConstr((X[s][j][u] <= 1 - f[s][i][j - Data.T] + f[s][i][u - Data.T]));//new
                        modelo.addConstr((X[s][j][u] <= 1 + f[s][i][j - Data.T] - f[s][i][u - Data.T]));//new
                    }
                }
            }
        }



        ///// these are new variables for maximum lenght constraints, just for cost
        /////// R9: Cumulative time /////////
        if (Data.OF == 1) {
            for (int i = Data.T; i < Data.V; i++) {
                GRBLinExpr time1 = 0.0;
                GRBLinExpr time2 = 0.0;
                GRBLinExpr time3 = 0.0;
                GRBLinExpr Tnew = 0.0;
                for (int j = 0; j < Data.T; ++j) {
                    Tnew += X[s][i][j] * Data.dist[i][j];
                }

                for (int j = 0; j < Data.V; j++) {
                    if (i == j) continue;
                    time1 += t[s][i][j];
                    time2 += t[s][j][i];
                    time3 += Data.dist[j][i] * X[s][j][i];
                }
                modelo.addConstr(time2 - time1 == time3 + Tnew);

            }
            //cout << " R9 ok" << endl;

            /////// R11: Maximum lengh constraint /////////
            for (int i = 0; i < Data.V; i++) {
                for (int j = 0; j < Data.V; j++) {
                    if (i == j) continue;
                    if ((i < Data.T) & (j < Data.T)) continue;
                    modelo.addConstr(t[s][i][j] <= Data.lenghtMax * X[s][i][j]);
                }
            }
            cout << "R11 ok" << endl;
        }

        /////// Depots capacity constraints: not used by Arslan/////////

        for (int j = 0; j < Data.T; j++)
        {
            GRBLinExpr demandssum=0.0;
            for (int i = 0; i < Data.N; i++)
            {
                demandssum+= (f[s][j][i]+ A[s][i][j])*Data.MyCustomers[i].q;
            }

            GRBLinExpr sizesum=0.0;
            for (int x = 0; x < Data.facsize; ++x) {
                sizesum+=Data.dep_cap[j][x]*Y[j][x];
            }
            modelo.addConstr(demandssum  <= sizesum);

        }
        cout << "R12 ok" << endl;



    }
///until here




        //modelo.set(GRB_IntParam_Threads,1);
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

        out << instance << "\t"  <<  "2index" <<"\t" << objectivefun <<"\t" << Data.WR<< "\t" << Data.WA<< "\t" << Data.Radius<<"\t"<< Data.lenghtMax<< "\t"  << Data.f<<"\t" <<modelo.get(GRB_DoubleAttr_ObjVal) << "\t" << modelo.get(GRB_DoubleAttr_ObjBound)<< "\t" << modelo.get(GRB_IntAttr_Status)<< "\t" << modelo.get(GRB_DoubleAttr_Runtime)<< "\t" << modelo.get(GRB_DoubleAttr_MIPGap)<< "\t" <<Cost1.getValue()<< "\t" <<Cost2.getValue()<< "\t" <<Cost4.getValue()<< "\t" <<DirectALL.getValue()<< "\t"<< "depots"<<  "\t";
        for (int i = 0; i < Data.T; i++) {
            for (int x = 0; x < Data.facsize; ++x) {
                if (Y[i][x].get(GRB_DoubleAttr_X) > 0.0001) {
                    int sumV=0;
                    for (int j = 0; j < Data.R; ++j) {
                        sumV+=round(V[j][i].get(GRB_DoubleAttr_X));
                    }
                    out << "d" << i + 1 << "\t";
                    out << "s" << x + 1 << "\t";
                    out <<  sumV << "\t";

                }
            }

        }
        out<<endl;
        out.close();


        int sumv=0;
    for (int i = 0; i < Data.R; ++i) {
        for (int j = 0; j < Data.T; ++j) {
            if (V[i][j].get(GRB_DoubleAttr_X) > 0.0001) cout<< " V_ "<< i+1 << " _ D_ " << j+1 << endl;
            sumv+=round (V[i][j].get(GRB_DoubleAttr_X));
        }
    }
    cout<<" total vehicles departed: " << sumv <<endl;



    ///// for graph, determinisitc ///
    for (int i = 0; i < Data.T; i++)
    {
        int sumz=0;
        for (int j = 0; j < Data.facsize; ++j) {
            sumz+=round(Y[i][j].get(GRB_DoubleAttr_X));
        }
        Z_graph[i]=round(sumz);
    }
    cout<<"z ok" <<endl;


    for (int j = 0; j < Data.V; j++)
    {
        for (int i = 0; i < Data.V; i++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            X_graph[i][j]=X[0][i][j].get(GRB_DoubleAttr_X);
        }
    }
    cout<< "X ok "<<endl;

    int direct=0;
    for (int i = 0; i < Data.N; i++)
    {
        for (int r = 0; r <Data.T; r++)
        {
            A_graph[i][r]=round(A[0][i][r].get(GRB_DoubleAttr_X)*1.0);
            if (A[0][i][r].get(GRB_DoubleAttr_X)>0.0001) {
                direct++;
                cout<< "A_"<<i+1 << "_"<< r+1 <<" = " << A[0][i][r].get(GRB_DoubleAttr_X) <<endl;
            }
        }
    }



    cout<<"model finished "<<endl;

}

void createstc_DS(string instance, Parameters &Data, string &results, double &of){

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
        /// Lofler two index formulation returning to the depot
        string graph2if =auxname+ to_string(Data.Radius)+ to_string(Data.WA)+"solution_cost_2IF_new.gml";
        GRBEnv env_2if;
        vector<vector<vector<GRBVar>>> W_2if;
        vector<vector<vector<GRBVar>>>X_2if;

        vector<vector<bool>>X_graph_2if;
        vector<vector<bool>>A_graph_2if;
        vector<bool>Z_graph_2if;
        vector<vector<vector<GRBVar>>> NC_2if;
        vector<vector<vector<GRBVar>>>A_2if;
        vector<vector<vector<GRBVar>>> f_2if;
        vector<vector<vector<GRBVar>>> t_2if;

        vector<vector<GRBVar>>NSC;

        //vector<GRBVar>Y_2if; //location
        vector<vector<GRBVar>>Y_2if;
        vector<vector<GRBVar>> V_2if; //fleet size,fleet alloc.


        LoRPSD_DS_2IF(instance, Data.OF, results, env_2if, Data, Y_2if, V_2if, NSC,  X_2if ,W_2if, f_2if, A_2if, NC_2if, t_2if, X_graph_2if, A_graph_2if, Z_graph_2if);
        GraphLLoRP_withRad_cost(graph2if, Data, X_graph_2if, A_graph_2if, Z_graph_2if);

    }

    catch (...) {
        cerr << "Error" << endl;
    }


}

void LoRPSD_2IF(string instance, int obj, string &results, GRBEnv &env, Parameters &Data, GRBVar& eta,  vector<GRBVar>&Psi, vector<GRBVar>&Y, vector<vector<GRBVar>>&V, vector<vector<GRBVar>>&NSC,  vector<vector<vector<GRBVar>>>&X, vector<vector<vector<GRBVar>>> &W, vector<vector<vector<GRBVar>>> &f, vector<vector<vector<GRBVar>>>&A,  vector<vector<vector<GRBVar>>> &NC, vector<vector<vector<GRBVar>>> &t, vector<vector<bool>>&X_graph, vector<vector<bool>>&A_graph, vector<bool>&Z_graph) {

    cout
            << " ----------------- This model is considers stochastic demand WITHOUT depot sizing -----------------------"
            << endl;

    GRBModel modelo(env);

    //// first stage variables Y: location, V, Vehicles fleet.
    Y.resize(Data.T);
    Z_graph.resize(Data.T);
    for (int j = 0; j < Data.T; j++) {
        Y[j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
        std::stringstream nn;
        nn << "Y_" << j + 1 ;
        Y[j].set(GRB_StringAttr_VarName, nn.str().c_str());
    }
    cout<<"y ok"<< endl;

    V.resize(Data.R);
    for (int i = 0; i < Data.R; i++) {
        V[i].resize(Data.T);
        for (int j = 0; j < Data.T; j++) {
            V[i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "V_" << i + 1 << "_" << j + 1;
            V[i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
    }
    cout<<"V ok"<< endl;

    eta = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
    std::stringstream aaa;
    aaa << "eta" ;
    eta.set(GRB_StringAttr_VarName, aaa.str().c_str());


    //// second stage variables
    X.resize(Data.Omega);
    f.resize(Data.Omega);
    W.resize(Data.Omega);
    A.resize(Data.Omega);
    NC.resize(Data.Omega);
    t.resize(Data.Omega);
    NSC.resize(Data.Omega);
    Psi.resize(Data.Omega);

    for (int s = 0; s < Data.Omega; ++s) {

        Psi[s] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
        std::stringstream nnn;
        nnn << "Psi_" << s + 1 ;
        Psi[s].set(GRB_StringAttr_VarName, nnn.str().c_str());

        cout<<"y ok"<< endl;

        NSC[s].resize(Data.N);
        for (int j = 0; j < Data.N; j++) {
            NSC[s][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
            std::stringstream nnn;
            nnn << "NSC_" << s + 1 << "_" << j + 1;
            NSC[s][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
        }
        cout<<"NSC ok"<< endl;

        X[s].resize(Data.V);
        X_graph.resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            X[s][i].resize(Data.V);
            X_graph[i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                X[s][i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
                std::stringstream nn;
                nn << "X_" << s + 1 << "_" << i + 1 << "_" << j + 1;
                X[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());

            }
        }
        cout<<"x ok"<< endl;


        f[s].resize(Data.T);
        for (int i = 0; i < Data.T; i++) {
            f[s][i].resize(Data.N);
            for (int j = 0; j < Data.N; j++) {
                f[s][i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
                std::stringstream nnn;
                nnn << "f_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                f[s][i][j].set(GRB_StringAttr_VarName, nnn.str().c_str());
            }
        }
        cout<<"f ok"<< endl;

        W[s].resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            W[s][i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                W[s][i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
                std::stringstream nn;
                nn << "W_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                W[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout<<"W ok"<< endl;

        //new variables
        A[s].resize(Data.N);
        A_graph.resize(Data.N);
        for (int i = 0; i < Data.N; i++) {
            A[s][i].resize(Data.T);
            A_graph[i].resize(Data.T);
            for (int j = 0; j < Data.T; j++) {
                A[s][i][j] = modelo.addVar(0.0, 1.0, 0.0, GRB_BINARY);
                std::stringstream nn;
                nn << "A_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                A[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout << "A ok" << endl;

        NC[s].resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            NC[s][i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                NC[s][i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
                std::stringstream nn;
                nn << "NC_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                NC[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout<<"nc ok"<< endl;

        //// new variable
        t[s].resize(Data.V);
        for (int i = 0; i < Data.V; i++) {
            t[s][i].resize(Data.V);
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                t[s][i][j] = modelo.addVar(0.0, GRB_INFINITY, 0.0, GRB_CONTINUOUS);
                std::stringstream nn;
                nn << "t_"<< s + 1 << "_" << i + 1 << "_" << j + 1;
                t[s][i][j].set(GRB_StringAttr_VarName, nn.str().c_str());
            }
        }
        cout<<"t ok"<< endl;
    }


    //we define the objective function
    //we define the objective function
    GRBLinExpr Lat1=0.0;
    GRBLinExpr Latency=0.0;
    //GRBLinExpr Cost=0.0;

    GRBLinExpr CostDepot=0.0;
    GRBLinExpr CostVehicle=0.0;
    GRBLinExpr TranspCost=0.0;
    GRBLinExpr PenaltyCust=0.0;
    GRBLinExpr DirectALL = 0;

    //cost  depots
    for (int i = 0; i < Data.T; i++)
    {
        CostDepot += Data.cost[i]* Y[i];
    }
    cout<<"cost 4 ok" <<endl;

    //cost 2 vehicles
    for (int i = 0; i < Data.R; i++)
    {
        for (int j = 0; j < Data.T; ++j) {
            CostVehicle += Data.vehiclesfixed* V[i][j];
        }
    }
    cout<<"cost 2 ok" <<endl;

    for (int s = 0; s < Data.Omega; ++s) {

        //latency
        for (int i = 0; i < Data.V; i++) {
            for (int j = Data.T; j < Data.V; j++) {
                if (i == j) continue;
                //if ((i<Data.T)&(j<Data.T)) continue;
                Lat1 += Data.prob[s]*Data.WR * Data.dist[i][j] * NC[s][i][j];

            }
        }

        //cost 1
        for (int i = 0; i < Data.V; i++) {
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                TranspCost += Data.prob[s]*Data.WR * Data.dist[i][j] * X[s][i][j];

            }
        }

        //direct allocation
        for (int i = 0; i < Data.N; i++) {
            for (int j = 0; j < Data.T; j++) {
                DirectALL += Data.prob[s]*Data.WA * Data.dist[i + Data.T][j] * A[s][i][j];
            }
        }
        cout << "FO B ok" << endl;

        //penalty for not serving a customer
        for (int i = 0; i < Data.N; i++)
        {
            PenaltyCust += Data.prob[s]*Data.penalty* NSC[s][i];
        }


    }

    cout<<"penalty is= " << Data.penalty <<endl;
    Latency=Lat1+DirectALL;
    //Cost=Cost1+Cost2+Cost4+DirectALL;


    GRBLinExpr mean=0.0;
    mean=TranspCost+DirectALL+PenaltyCust;

    GRBLinExpr minCVAR=0.0;
    for (int w = 0; w <Data.Omega ; ++w) {
        minCVAR += Data.prob[w]*Psi[w];
        //cout<< Data.prob[w]<<endl;
    }

    double lambda=1.0;

    minCVAR= minCVAR/(1.0-Data.ALPHA);



    if(obj==0) modelo.setObjective(Latency, GRB_MINIMIZE);
    //else  modelo.setObjective(CostDepot+CostVehicle+(1-lambda)*(mean)+lambda*(eta+minCVAR), GRB_MINIMIZE);
    else  modelo.setObjective(CostDepot+CostVehicle+(eta+minCVAR), GRB_MINIMIZE);


    /////// R2: maximum number of depots to open, just for latency /////////
    if(Data.OF==0){
        GRBLinExpr R16=0.0;
        for (int i = 0; i < Data.T; ++i) {
                R16+=Y[i];
        }
        modelo.addConstr(R16 <= Data.f);
        cout << "R3 ok  "  << endl;
    }


    ////compute CVaR
    for (int s = 0; s < Data.Omega; ++s) {
        //latency
        GRBLinExpr Lat1CT=0.0;
        for (int i = 0; i < Data.V; i++) {
            for (int j = Data.T; j < Data.V; j++) {
                if (i == j) continue;
                //if ((i<Data.T)&(j<Data.T)) continue;
                Lat1CT += Data.WR * Data.dist[i][j] * NC[s][i][j];

            }
        }

        //cost 1
        GRBLinExpr Cost1CT=0.0;
        for (int i = 0; i < Data.V; i++) {
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                Cost1CT += Data.WR * Data.dist[i][j] * X[s][i][j];

            }
        }

        //direct allocation
        GRBLinExpr DirectCT=0.0;
        for (int i = 0; i < Data.N; i++) {
            for (int j = 0; j < Data.T; j++) {
                DirectCT += Data.WA * Data.dist[i + Data.T][j] * A[s][i][j];
            }
        }
        cout << "FO B ok" << endl;

        //penalty for not serving a customer
        GRBLinExpr penaltyCT=0.0;
        for (int i = 0; i < Data.N; i++)
        {
            penaltyCT += Data.penalty* NSC[s][i];
        }

        modelo.addConstr(Psi[s] >= Cost1CT+DirectCT+penaltyCT- eta);
    }



    //////// RA, RB: fleet sizing /////////
    for (int k = 0; k < Data.R; ++k) {
        GRBLinExpr RA=0.0;
        for (int i = 0; i < Data.T; ++i) {
            RA+=V[k][i];
            modelo.addConstr(V[k][i] <= Y[i]);// RB
        }
        modelo.addConstr(RA <= 1);// RA
    }



    //// Second stage: the following constraints are valid for each scenario
    for (int s = 0; s < Data.Omega; ++s) {

        //////// R3: A maximum of k vehicles can be used, just for latency /////////
        for (int i = 0; i < Data.T; ++i) {
            GRBLinExpr R17A=0.0;
            GRBLinExpr R17B=0.0;
            for (int j = Data.T; j <Data.V ; ++j) {
                R17A+=X[s][i][j];
            }
            for (int k = 0; k <Data.R ; ++k) {
                R17B+=V[k][i];
            }
            modelo.addConstr(R17A == R17B);// we may use less than or equal to
        }


        //////// R4 and R5 Each customer must be visited either by a vehicle or by direct allocation, or will be penalized  /////////
        for (int i = Data.T; i < Data.V; ++i) {
            GRBLinExpr R2 = 0.0;
            GRBLinExpr R2b = 0.0;
            for (int j = 0; j < Data.V; ++j) {
                if (i == j) continue;
                R2 += X[s][j][i];
                R2b += X[s][i][j];
            }

            GRBLinExpr Rauxi = 0.0;
            for (int j = 0; j < Data.T; ++j) {
                Rauxi += A[s][i - Data.T][j];
            }
            modelo.addConstr(R2 + Rauxi+NSC[s][i-Data.T] == 1); //modified NSC
            modelo.addConstr(R2b + Rauxi+NSC[s][i-Data.T] == 1); //modified NSC
        }

        //////// R6,R7 for latency and XXXX for cost: Each customer must be allocated to an open depot:CHECK HERE FOR WRITTING THE MODEL!!! ************************************** /////////
        for (int i = Data.T; i < Data.V; ++i) {
            for (int j = 0; j < Data.T; ++j) {
                if (Data.OF == 0) {
                    modelo.addConstr(X[s][j][i] <= Y[j]);
                    modelo.addConstr(X[s][i][j] <= Y[j]);
                }

                if (Data.OF == 1) {
                    modelo.addConstr(X[s][j][i] <= f[s][j][i - Data.T]); //17
                    modelo.addConstr(X[s][i][j] <= f[s][j][i - Data.T]); //16
                    modelo.addConstr(f[s][j][i - Data.T] <= Y[j]); //15
                }
            }
        }


        //////// R8 flow balance /////////
        for (int i = 0; i < Data.V; ++i) {
            GRBLinExpr R3_a = 0.0;
            GRBLinExpr R3_b = 0.0;
            for (int j = 0; j < Data.V; ++j) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                R3_a += X[s][i][j];
                R3_b += X[s][j][i];

            }
            modelo.addConstr(R3_a - R3_b == 0);
        }
        cout << "R8 ok  " << endl;

        //////// R9 and R10: Customers can be directly allocated just to an open depot and within the coverage range /////////
        for (int i = Data.T; i < Data.V; ++i) {
            for (int j = 0; j < Data.T; ++j) {
                modelo.addConstr(Data.dist[i][j] * A[s][i - Data.T][j] <=  Data.Radius *Y[j]);
                modelo.addConstr(A[s][i - Data.T][j] <= Y[j]);
            }
        }

        /////// R11 and R10: Cumulative demand and number of customers in the routes /////////
        for (int i = Data.T; i < Data.V; i++) {
            GRBLinExpr DEM1 = 0.0;
            GRBLinExpr DEM2 = 0.0;

            GRBLinExpr NEW1 = 0.0;
            GRBLinExpr NEW2 = 0.0;

            GRBLinExpr Rnew = 0.0;
            for (int j = 0; j < Data.T; ++j) {
                Rnew += A[s][i - Data.T][j];
            }
            Rnew+=NSC[s][i-Data.T]; // new NSC

            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                DEM1 += W[s][i][j];
                DEM2 += W[s][j][i];

                NEW1 += NC[s][i][j];
                NEW2 += NC[s][j][i];
            }
            modelo.addConstr(DEM2 - DEM1 == (1 - Rnew) * Data.demand[s][i-Data.T]);// new NSC and demand
            //modelo.addConstr(NEW2 - NEW1 == (1 - Rnew));// new NSC
        }


        /////// R13 and R14: Vehicles Capacity and maximum number of customers in a route /////////
        for (int i = 0; i < Data.V; i++) {
            for (int j = 0; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                modelo.addConstr(W[s][i][j] <= (Data.Q) * X[s][i][j]);
                //modelo.addConstr(NC[s][i][j] <= (Data.L - 2) * X[s][i][j]);
            }
        }


        /////// R15 and R16: Lower bounds for W and NC/////////
        for (int j = Data.T; j < Data.V; j++) {
            for (int i = 0; i < Data.V; i++) {
                if (i == j) continue;
                modelo.addConstr(W[s][i][j] >= (Data.demand[s][j-Data.T]) * X[s][i][j]);
                //modelo.addConstr(NC[s][i][j] >= X[s][i][j]);
            }
        }

        ///////// R17: Valid inequalities symmetry breaking
        for (int i = Data.T; i < Data.V; i++) {
            for (int j = Data.T; j < Data.V; j++) {
                if (i == j) continue;
                if ((i < Data.T) & (j < Data.T)) continue;
                modelo.addConstr(X[s][j][i] + X[s][i][j] <= 1);

            }
        }


/// new things
        //////// Each customer must be allocated to a depot or directly allocated, if not it will be penalized, just for cost/////////
        if (Data.OF == 1) {
            for (int i = 0; i < Data.N; ++i) {
                GRBLinExpr R1_aux = 0.0;
                GRBLinExpr R1_aux_b = 0.0;
                for (int j = 0; j < Data.T; ++j) {
                    R1_aux += f[s][j][i];
                    R1_aux_b += A[s][i][j];
                }
                modelo.addConstr(R1_aux + R1_aux_b + NSC[s][i]== 1); // modified NSC
            }
        }


        ///////  consistency on the depots, JUST FOR COST    ***************************/////////
        if (Data.OF == 1) {
            for (int j = Data.T; j < Data.V; j++) {
                for (int u = Data.T; u < Data.V; u++) {
                    if (j == u) continue;
                    for (int i = 0; i < Data.T; i++) {
                        modelo.addConstr((X[s][j][u] <= 1 - f[s][i][j - Data.T] + f[s][i][u - Data.T]));//new
                        modelo.addConstr((X[s][j][u] <= 1 + f[s][i][j - Data.T] - f[s][i][u - Data.T]));//new
                    }
                }
            }
        }



        ///// these are new variables for maximum lenght constraints, just for cost
        /////// R9: Cumulative time /////////
        if (Data.OF == 1) {
            for (int i = Data.T; i < Data.V; i++) {
                GRBLinExpr time1 = 0.0;
                GRBLinExpr time2 = 0.0;
                GRBLinExpr time3 = 0.0;
                GRBLinExpr Tnew = 0.0;
                for (int j = 0; j < Data.T; ++j) {
                    Tnew += X[s][i][j] * Data.dist[i][j];
                }

                for (int j = 0; j < Data.V; j++) {
                    if (i == j) continue;
                    time1 += t[s][i][j];
                    time2 += t[s][j][i];
                    time3 += Data.dist[j][i] * X[s][j][i];
                }
                modelo.addConstr(time2 - time1 == time3 + Tnew);

            }
            //cout << " R9 ok" << endl;

            /////// R11: Maximum lengh constraint /////////
            for (int i = 0; i < Data.V; i++) {
                for (int j = 0; j < Data.V; j++) {
                    if (i == j) continue;
                    if ((i < Data.T) & (j < Data.T)) continue;
                    modelo.addConstr(t[s][i][j] <= Data.lenghtMax * X[s][i][j]);
                }
            }
            cout << "R11 ok" << endl;
        }

        /////// Depots capacity constraints: not used by Arslan/////////

        for (int j = 0; j < Data.T; j++)
        {
            GRBLinExpr demandssum=0.0;
            for (int i = 0; i < Data.N; i++)
            {
                demandssum+= (f[s][j][i]+ A[s][i][j])*Data.demand[s][i];
            }

            modelo.addConstr(demandssum  <= Data.MyDepots[j].QD*Y[j]);

        }
        cout << "R12 ok" << endl;



    }
///until here




    //modelo.set(GRB_IntParam_Threads,1);
    modelo.write("filename.lp");
    modelo.set(GRB_DoubleParam_MIPGap,0.0);
    modelo.set(GRB_DoubleParam_TimeLimit,3600);



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

    out << instance << "\t"  <<  "2index" <<"\t" << objectivefun <<"\t" << Data.WR<< "\t" << Data.WA<< "\t" << Data.Radius<<"\t"<< Data.lenghtMax<< "\t"  << Data.f<<"\t" <<modelo.get(GRB_DoubleAttr_ObjVal) << "\t" << modelo.get(GRB_DoubleAttr_ObjBound)<< "\t" << modelo.get(GRB_IntAttr_Status)<< "\t" << modelo.get(GRB_DoubleAttr_Runtime)<< "\t" << modelo.get(GRB_DoubleAttr_MIPGap)<< "\t" <<CostDepot.getValue()<< "\t" <<CostVehicle.getValue()<< "\t" <<TranspCost.getValue()<< "\t" <<DirectALL.getValue()<< "\t"<< "depots"<<  "\t";
    for (int i = 0; i < Data.T; i++) {
            if (Y[i].get(GRB_DoubleAttr_X) > 0.0001) {
                int sumV=0;
                for (int j = 0; j < Data.R; ++j) {
                    sumV+=round(V[j][i].get(GRB_DoubleAttr_X));
                }
                out << "d" << i + 1 << "\t";
                out << "s" << "Std" << "\t";
                out <<  sumV << "\t";

            }
    }
    out<<endl;
    out.close();


    int sumv=0;
    for (int i = 0; i < Data.R; ++i) {
        for (int j = 0; j < Data.T; ++j) {
            if (V[i][j].get(GRB_DoubleAttr_X) > 0.0001) cout<< " V_ "<< i+1 << " _ D_ " << j+1 << endl;
            sumv+=round (V[i][j].get(GRB_DoubleAttr_X));
        }
    }
    cout<<" total vehicles departed: " << sumv <<endl;



    ///// for graph, determinisitc ///
    for (int i = 0; i < Data.T; i++)
    {
        Z_graph[i]=round(Y[i].get(GRB_DoubleAttr_X));
    }
    cout<<"z ok" <<endl;


    for (int j = 0; j < Data.V; j++)
    {
        for (int i = 0; i < Data.V; i++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            X_graph[i][j]=X[0][i][j].get(GRB_DoubleAttr_X);
        }
    }
    cout<< "X ok "<<endl;

    int direct=0;
    for (int i = 0; i < Data.N; i++)
    {
        for (int r = 0; r <Data.T; r++)
        {
            A_graph[i][r]=round(A[0][i][r].get(GRB_DoubleAttr_X)*1.0);
            if (A[0][i][r].get(GRB_DoubleAttr_X)>0.0001) {
                direct++;
                cout<< "A_"<<i+1 << "_"<< r+1 <<" = " << A[0][i][r].get(GRB_DoubleAttr_X) <<endl;
            }
        }
    }



    cout<<"model finished "<<endl;

}

void createstc(string instance, Parameters &Data, string &results, double &of){

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
        /// Lofler two index formulation returning to the depot
        string graph2if =auxname+ to_string(Data.Radius)+ to_string(Data.WA)+"solution_cost_2IF_new.gml";
        GRBEnv env_2if;
        vector<vector<vector<GRBVar>>> W_2if;
        vector<vector<vector<GRBVar>>>X_2if;

        vector<vector<bool>>X_graph_2if;
        vector<vector<bool>>A_graph_2if;
        vector<bool>Z_graph_2if;
        vector<vector<vector<GRBVar>>> NC_2if;
        vector<vector<vector<GRBVar>>>A_2if;
        vector<vector<vector<GRBVar>>> f_2if;
        vector<vector<vector<GRBVar>>> t_2if;

        vector<vector<GRBVar>>NSC;

        //vector<GRBVar>Y_2if; //location
        vector<GRBVar>Y_2if;
        vector<vector<GRBVar>> V_2if; //fleet size,fleet alloc.
        vector<GRBVar>Psi;
        GRBVar eta;


        LoRPSD_2IF(instance, Data.OF, results, env_2if, Data, eta, Psi, Y_2if, V_2if, NSC,  X_2if ,W_2if, f_2if, A_2if, NC_2if, t_2if, X_graph_2if, A_graph_2if, Z_graph_2if);
        Data.R=Data.R*100/Data.maxdist;
        GraphLLoRP_withRad_cost(graph2if, Data, X_graph_2if, A_graph_2if, Z_graph_2if);

    }

    catch (...) {
        cerr << "Error" << endl;
    }


}
