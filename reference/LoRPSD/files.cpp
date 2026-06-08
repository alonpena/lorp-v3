//
// Created by alan on 20/07/21.
//

#include <cfloat>
#include <chrono>
#include "files.h"


template<class T>
static inline void str2val( const char* const str , T &sthg ) {
    istringstream( str ) >> sthg;
}

void ReadAlgorithmParams(int argc, char **argv, MetaParameters &MetaData, string &instance, string &results){


    std::vector<std::vector<char *> > parameters_checking;
    //cout<<endl;
    for(int i=1;i<argc;i=i+2){
        vector<char *> aux;
        //cout<<argv[i]<<" "<<argv[i+1]<<endl;
        aux.push_back(argv[i]);
        aux.push_back(argv[i+1]);
        parameters_checking.push_back(aux);
    }

    if(parameters_checking.size()!=11){
        cout<<"Error: SA-VNS needs 11 parameter("<<parameters_checking.size()<<")"<<endl;
        exit(0);
    }else{
        for(int i=0;i<parameters_checking.size();i++){
            string descriptor = parameters_checking[i][0];

            if(descriptor=="-instance") {
                //fin = parameters_checking[i][1].data();
                //fin = &parameters_checking[i][1][0];
                instance = parameters_checking[i][1];
            } else if(descriptor=="-problemID"){
                str2val(parameters_checking[i][1], MetaData.problemID);
            } else if(descriptor=="-WR"){
                str2val(parameters_checking[i][1], MetaData.WR);
            } else if(descriptor=="-WA"){
                str2val(parameters_checking[i][1], MetaData.WA);
            } else if(descriptor=="-Radius"){
                str2val(parameters_checking[i][1], MetaData.Radius);
            }
            else if(descriptor=="-OF"){
                str2val(parameters_checking[i][1], MetaData.OF);
            } else if(descriptor=="-VFX"){
                str2val(parameters_checking[i][1], MetaData.VFX);
            } else if(descriptor=="-model"){
                str2val(parameters_checking[i][1], MetaData.model);
            }
            else if(descriptor=="-length"){
                str2val(parameters_checking[i][1], MetaData.lenghtMax);
            }
            else if(descriptor=="-original"){
                str2val(parameters_checking[i][1], MetaData.originalLoRP);
            }
            else if(descriptor=="-results"){
                //str2val(parameters_checking[i][1], seed);
                str2val(parameters_checking[i][1], results);
            }else{
                cout<<"Error: parameter descriptor not found("<<descriptor<<")"<<endl;
                exit(0);
            }
        }
    }

}

void ReadData(string &instance, Parameters & Data){
    cout<< " This is the original function used for the LoRP"<<endl;
    ifstream fileinput(instance.c_str());
    if (!fileinput) {
        cout << "Error opening file fileinput" << endl;
        exit(0);
    }


    int tempi; //to save garbage



    fileinput >> Data.N; // customers
    Data.MyCustomers.resize(Data.N);
    fileinput >> Data.T; // depots
    Data.MyDepots.resize(Data.T);
    fileinput >> Data.f; // depots to open
    //f=T; // depots to open
    fileinput >> Data.R; // number of vehicles
    //R=N; // number of vehicles

    Data.q.resize(Data.N);
    Data.cost.resize(Data.T);

    //reading depots' data
    for (int i = 0; i < Data.T; ++i) {
        Data.MyDepots[i].ID = i + 1;
        fileinput >> Data.MyDepots[i].x;
        fileinput >> Data.MyDepots[i].y;

        ////cout << "id: " << MyNodes[i].ID << endl;
        ////cout << "x " << MyNodes[i].x << endl;
        ////cout << "y " << MyNodes[i].y << endl;
    }

    //reading customers' data
    for (int i = 0; i < Data.N; ++i) {
        Data.MyCustomers[i].ID = i + 1;
        fileinput >> Data.MyCustomers[i].x;
        fileinput >> Data.MyCustomers[i].y;

        ////cout << "id: " << MyNodes[i].ID << endl;
        ////cout << "x " << MyNodes[i].x << endl;
        ////cout << "y " << MyNodes[i].y << endl;
    }


    fileinput >> Data.Q; // Vehicle capacity
    Data.Q_original=Data.Q;
    //cout << "Q:" << Q << endl;


    //depots' capacity
    for (int i = 0; i < Data.T; ++i) {
        fileinput >> Data.MyDepots[i].QD; // Depot capacity
        ////cout << "QD " << MyDepots[i].QD << endl;
    }

    //customers' demand
    Data.totaldemandinstance=0;
    for (int i = 0; i < Data.N; ++i) {
        fileinput >> Data.q[i];
        Data.MyCustomers[i].q=Data.q[i];
        Data.totaldemandinstance+=Data.q[i];
        ////cout << "q: " << i + 1 << "= " << MyCustomers[i].q << endl;
    }

    //cout<<"sumademanda: " << totaldemandinstance<<endl;

    //depots' invest
    for (int i = 0; i < Data.T; ++i) {
        fileinput >> Data.cost[i];
        //cost[i]=0.0;
        // Depot fixed cost
        cout << "QD " << Data.cost[i] << endl;
    }

    fileinput >> Data.vehiclesfixed; // ?
    //vehiclesfixed=0.0;
    //cout << "vehicles " << vehiclesfixed << endl;
    fileinput >> tempi; // ?
    //cout << "tempi " << tempi << endl;



    Data.V = Data.N + Data.T; //number of nodes

    if ((tempi != 0)&&(tempi != 1)) {
        //cout << "Error, correct the reading function" << tempi << endl;
        exit(0);
    }


    //filling the distance matrix
    Data.dist.resize(Data.V);
    Data.worstd.resize(Data.V);
    for (int i = 0; i < Data.V; ++i) {
        Data.dist[i].resize(Data.V);
        Data.worstd[i] = 0;
        for (int j = 0; j < Data.V; ++j) {
            if (i < Data.T) {
                if (j < Data.T) {
                    Data.dist[i][j] = sqrt(pow(Data.MyDepots[i].x - Data.MyDepots[j].x, 2)
                                      + pow(Data.MyDepots[i].y - Data.MyDepots[j].y, 2));
                }
                else {
                    Data.dist[i][j] = sqrt(pow(Data.MyDepots[i].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                      + pow(Data.MyDepots[i].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2));
                }

            }
            else {
                if (j < Data.T) {
                    Data.dist[i][j] = sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyDepots[j].x, 2)
                                      + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyDepots[j].y, 2));
                }
                else {
                    Data.dist[i][j] = sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                      + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2));
                }
            }
            if (Data.dist[i][j] > Data.worstd[i]) Data.worstd[i] = Data.dist[i][j];
            //cout << "dist[" << i + 1 << "]" << "[" << j + 1 << "]" << dist[i][j] << endl;
        }
    }


    //Big M
    Data.BigM = 0;
    for (int i = 0; i < Data.V; i++)
    {
        Data.BigM += Data.worstd[i];
        //	//cout << " Worst[" << i + 1 << "] =" << worstd[i] << endl;
    }

    //BigM = V;
    //cout << " BigM" << "=" << BigM << endl;

    double totaldemand=0;
    for (int i = 0; i <Data.N ; ++i) {
        totaldemand+=Data.MyCustomers[i].q;
    }

    Data.L=0;

    //cout<< "total demand= "<< totaldemand << "  ||   total capacity= "<< Q*R<<endl;

    //cout << "The number of nodes is= " << V << endl;
    //cout << "The number of customers is= " << N << endl;
    //cout << "The number of vehicles is= " << R << endl;
    //cout << "The capacity of vehicles is= " << Q << endl;
    //cout << "the number of depots to open is = " << f << endl;

    //exit(0);

    fileinput.close(); // closing the file
}

void ReadData_sizing(string &instance, Parameters & Data){
    cout<< " This is the function used for the LoRP with depot sizing (deterministic), it is useful also for the LRP with sizing decisions"<<endl;

    ifstream fileinput(instance.c_str());
    if (!fileinput) {
        cout << "Error opening file fileinput" << endl;
        exit(0);
    }


    int tempi; //to save garbage

    Data.facsize=5;

    int slash=0;
    int punto=0;
    for (int i = 0; i < instance.size(); ++i) {
        if(instance[i]=='/') slash=i;
        if(instance[i]=='.'){
            punto=i;
            break;
        }
    }

    for (int i = slash+1; i < punto; ++i) {
        Data.shortname.push_back(instance[i]);
    }
    cout<<Data.shortname<<endl;



    fileinput >> Data.N; // customers
    Data.MyCustomers.resize(Data.N);
    fileinput >> Data.T; // depots
    Data.MyDepots.resize(Data.T);
    fileinput >> Data.f; // depots to open
    //f=T; // depots to open
    fileinput >> Data.R; // number of vehicles
    //R=N; // number of vehicles

    Data.q.resize(Data.N);
    Data.cost.resize(Data.T);

    //reading depots' data
    for (int i = 0; i < Data.T; ++i) {
        Data.MyDepots[i].ID = i + 1;
        fileinput >> Data.MyDepots[i].x;
        fileinput >> Data.MyDepots[i].y;

        ////cout << "id: " << MyNodes[i].ID << endl;
        ////cout << "x " << MyNodes[i].x << endl;
        ////cout << "y " << MyNodes[i].y << endl;
    }

    //reading customers' data
    for (int i = 0; i < Data.N; ++i) {
        Data.MyCustomers[i].ID = i + 1;
        fileinput >> Data.MyCustomers[i].x;
        fileinput >> Data.MyCustomers[i].y;

        ////cout << "id: " << MyNodes[i].ID << endl;
        ////cout << "x " << MyNodes[i].x << endl;
        ////cout << "y " << MyNodes[i].y << endl;
    }


    fileinput >> Data.Q; // Vehicle capacity
    Data.Q_original=Data.Q;
    //cout << "Q:" << Q << endl;


    //depots' capacity
    for (int i = 0; i < Data.T; ++i) {
        fileinput >> Data.MyDepots[i].QD; // Depot capacity
        ////cout << "QD " << MyDepots[i].QD << endl;
    }

    //customers' demand
    Data.totaldemandinstance=0;
    for (int i = 0; i < Data.N; ++i) {
        fileinput >> Data.q[i];
        Data.MyCustomers[i].q=Data.q[i];
        Data.totaldemandinstance+=Data.q[i];
        ////cout << "q: " << i + 1 << "= " << MyCustomers[i].q << endl;
    }

    //cout<<"sumademanda: " << totaldemandinstance<<endl;

    //depots' invest
    double totalfix=0.0;
    for (int i = 0; i < Data.T; ++i) {
        fileinput >> Data.cost[i];
        totalfix+=Data.cost[i];
        // Depot fixed cost
        cout << "cost " << Data.cost[i] << endl;
    }

    fileinput >> Data.vehiclesfixed; // ?
    //vehiclesfixed=0.0;
    //cout << "vehicles " << vehiclesfixed << endl;
    fileinput >> tempi; // ?
    //cout << "tempi " << tempi << endl;



    Data.V = Data.N + Data.T; //number of nodes

    if ((tempi != 0)&&(tempi != 1)) {
        cout << "Error, correct the reading function" << tempi << endl;
        exit(0);
    }


    //filling the distance matrix
    Data.dist.resize(Data.V);
    Data.worstd.resize(Data.V);
    for (int i = 0; i < Data.V; ++i) {
        Data.dist[i].resize(Data.V);
        Data.worstd[i] = 0;
        for (int j = 0; j < Data.V; ++j) {
            if (i < Data.T) {
                if (j < Data.T) {
                    Data.dist[i][j] = sqrt(pow(Data.MyDepots[i].x - Data.MyDepots[j].x, 2)
                                           + pow(Data.MyDepots[i].y - Data.MyDepots[j].y, 2));
                }
                else {
                    Data.dist[i][j] = sqrt(pow(Data.MyDepots[i].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                           + pow(Data.MyDepots[i].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2));
                }

            }
            else {
                if (j < Data.T) {
                    Data.dist[i][j] = sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyDepots[j].x, 2)
                                           + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyDepots[j].y, 2));
                }
                else {
                    Data.dist[i][j] = sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                           + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2));
                }
            }
            if (Data.dist[i][j] > Data.worstd[i]) Data.worstd[i] = Data.dist[i][j];
            //cout << "dist[" << i + 1 << "]" << "[" << j + 1 << "]" << dist[i][j] << endl;
        }
    }


    //Big M
    Data.BigM = 0;
    for (int i = 0; i < Data.V; i++)
    {
        Data.BigM += Data.worstd[i];
        //	//cout << " Worst[" << i + 1 << "] =" << worstd[i] << endl;
    }

    //BigM = V;
    //cout << " BigM" << "=" << BigM << endl;

    double totaldemand=0;
    for (int i = 0; i <Data.N ; ++i) {
        totaldemand+=Data.MyCustomers[i].q;
    }

    Data.L=0;


    //// creating the size-dependent parameters ////
    Data.dep_cap.resize(Data.T);
    Data.dep_cost.resize(Data.T);
    for (int i = 0; i < Data.T; ++i) {
        Data.dep_cap[i].resize(Data.facsize);
        Data.dep_cost[i].resize(Data.facsize);
        //cout<<"Cap Original= " << Data.MyDepots[i].QD <<endl;
        cout<< "Depot:"  << i+1  << " | cap Original: " <<Data.MyDepots[i].QD <<"Cost Original= " << Data.cost[i] <<endl;
        if (Data.facsize>1){
            for (int j = 0; j < Data.facsize; ++j) {
                Data.dep_cap[i][j]=Data.MyDepots[i].QD*(1+(-2+j)*0.25);
                //cout<<"Cap size= " << j+1 << " | " <<Data.dep_cap[i][j] <<endl;

                Data.dep_cost[i][j]=1.0*(Data.cost[i]+((Data.dep_cap[i][j]-Data.MyDepots[i].QD)/(2*Data.MyDepots[i].QD))*(totalfix/Data.T));
                cout<<"size= " << j+1 << " | cap: " << Data.dep_cap[i][j]<< " | cost: " <<Data.dep_cost[i][j] <<endl;
            }
        }
        else{
            Data.dep_cap[i][0]=Data.MyDepots[i].QD;
            Data.dep_cost[i][0]=Data.cost[i];
        }

    }

    //exit(0);

    fileinput.close(); // closing the file
}

void Instance_Generator( string instance, Parameters&Data) {

    Data.dist_name="Uniform";
    Data.Omega=10;

    string dataout="instances_stc/"+Data.shortname+"_"+to_string(Data.Omega)+"_"+Data.dist_name+".dat";

    fstream fileinput(dataout, ios::app);



    int tempi; //to save garbage
    string mystring;

    fileinput << Data.N<<endl; // customers
    fileinput << Data.T<<endl; // depots
    fileinput << Data.f<<endl; // depots to open
    fileinput << Data.R <<endl; // number of vehicles
    fileinput << Data.Omega <<endl; // number of scenarios
    fileinput << Data.dist_name <<endl; // prob dist

    fileinput<< "\n" ;

    //reading depots' data
    for (int i = 0; i < Data.T; ++i) {
        fileinput << Data.MyDepots[i].x<< "\t" << Data.MyDepots[i].y<<endl;
    }

    fileinput<< "\n" ;

    //reading customers' data
    for (int i = 0; i < Data.N; ++i) {
        fileinput << Data.MyCustomers[i].x<< "\t" << Data.MyCustomers[i].y <<endl;
    }

    fileinput<< "\n" ;

    fileinput << Data.Q <<endl; // Vehicle capacity

    fileinput<< "\n" ;

    //depots' capacity
    for (int i = 0; i < Data.T; ++i) {
        fileinput << Data.MyDepots[i].QD <<endl; // Depot capacity
        ////cout << "QD " << MyDepots[i].QD << endl;
    }

    fileinput<< "\n" ;

    //customers' demand
    Data.totaldemandinstance=0;
    for (int i = 0; i < Data.N; ++i) {
        fileinput << Data.q[i]<<endl;
        Data.MyCustomers[i].q=Data.q[i];
        Data.totaldemandinstance+=Data.q[i];
        ////cout << "q: " << i + 1 << "= " << MyCustomers[i].q << endl;
    }
    fileinput<< "\n" ;

    //depots' invest
    double totalfix=0.0;
    for (int i = 0; i < Data.T; ++i) {
        fileinput << Data.cost[i] <<endl;
        totalfix+=Data.cost[i];
        // Depot fixed cost
        cout << "cost " << Data.cost[i] << endl;
    }
    fileinput<< "\n" ;

    fileinput << Data.vehiclesfixed<<endl; // ?
    fileinput<< "\n" ;
    fileinput << 0 <<endl; // ?
    fileinput<< "\n" ;

    //// creating section
    Data.demand.resize(Data.Omega);

    //resizing
    for (int w = 0; w < Data.Omega; ++w) {
        ////linear profit and weights
        Data.demand[w].resize(Data.N);
    }


    //// random numbers generator: fixed seed equal to 1
    ///
    /*
    static std::random_device rd;
    static std::mt19937 gen(rd());

    ////linear profit and weight
    for (int i = 0; i < Data.N; ++i) {
        cout<<"item: " << i+1 << "   q original"<< Data.MyCustomers[i].q  <<endl;

        if (Data.dist_name=="Poisson"){
            cout<<"POISSON" <<endl;
            std::poisson_distribution<int> q_pois(Data.MyCustomers[i].q);
            for (int w = 0; w < Data.Omega; ++w){
                Data.demand[w][i]=q_pois(gen);
                 std::cout << q_pois(gen) << '\n';
            }
        }
        else{
            cout<<"UNIFORM" <<endl;
            std::uniform_int_distribution<> q_uni(0.2*Data.MyCustomers[i].q, 1.8*Data.MyCustomers[i].q);
            for (int w = 0; w != Data.Omega; ++w){
                Data.demand[w][i]=q_uni(gen);
                std::cout << q_uni(gen) << ' ';
                std::cout << '\n';
            }

        }

    }



    //// printing section
    for (int w = 0; w < Data.Omega; ++w) {
        fileinput << "Scenario " << w+1 <<endl; // comments

        ////demand
        for (int i = 0; i < Data.N; ++i) {
            fileinput <<  Data.demand[w][i] << "\t";
        }
        fileinput<<endl;



        //fileinput >> mystring; // space


    }

    fileinput << "END" <<endl; // X
*/

}

void ReadData_stoc(string &instance, Parameters & Data){
    cout<< " This is the function used for the LoRP-SD with depot sizing"<<endl;

    ifstream fileinput(instance.c_str());
    if (!fileinput) {
        cout << "Error opening file fileinput" << endl;
        exit(0);
    }


    int tempi; //to save garbage
    string temps; //to save garbage

    Data.facsize=5;

    int slash=0;
    int punto=0;
    for (int i = 0; i < instance.size(); ++i) {
        if(instance[i]=='/') slash=i;
        if(instance[i]=='.'){
            punto=i;
            break;
        }
    }

    for (int i = slash+1; i < punto+4; ++i) {
        Data.shortname.push_back(instance[i]);
    }
    cout<<Data.shortname<<endl;



    fileinput >> Data.N; // customers
    Data.MyCustomers.resize(Data.N);
    fileinput >> Data.T; // depots
    Data.MyDepots.resize(Data.T);
    fileinput >> Data.f; // depots to open
    //f=T; // depots to open
    fileinput >> Data.R; // number of vehicles
    Data.R=Data.N;
    //R=N; // number of vehicles
    fileinput >> Data.Omega; // number of scenarios
    fileinput >> Data.dist_name; // number of vehicles

    Data.q.resize(Data.N);
    Data.cost.resize(Data.T);

    //reading depots' data
    for (int i = 0; i < Data.T; ++i) {
        Data.MyDepots[i].ID = i + 1;
        fileinput >> Data.MyDepots[i].x;
        fileinput >> Data.MyDepots[i].y;

        ////cout << "id: " << MyNodes[i].ID << endl;
        ////cout << "x " << MyNodes[i].x << endl;
        ////cout << "y " << MyNodes[i].y << endl;
    }

    //reading customers' data
    for (int i = 0; i < Data.N; ++i) {
        Data.MyCustomers[i].ID = i + 1;
        fileinput >> Data.MyCustomers[i].x;
        fileinput >> Data.MyCustomers[i].y;

        ////cout << "id: " << MyNodes[i].ID << endl;
        ////cout << "x " << MyNodes[i].x << endl;
        ////cout << "y " << MyNodes[i].y << endl;
    }


    fileinput >> Data.Q; // Vehicle capacity
    Data.Q_original=Data.Q;
    //cout << "Q:" << Q << endl;


    //depots' capacity
    for (int i = 0; i < Data.T; ++i) {
        fileinput >> Data.MyDepots[i].QD; // Depot capacity
        ////cout << "QD " << MyDepots[i].QD << endl;
    }

    //customers' demand
    Data.totaldemandinstance=0;
    for (int i = 0; i < Data.N; ++i) {
        fileinput >> Data.q[i];
        Data.MyCustomers[i].q=Data.q[i];
        Data.totaldemandinstance+=Data.q[i];
        ////cout << "q: " << i + 1 << "= " << MyCustomers[i].q << endl;
    }

    //cout<<"sumademanda: " << totaldemandinstance<<endl;

    //depots' invest
    double totalfix=0.0;
    for (int i = 0; i < Data.T; ++i) {
        fileinput >> Data.cost[i];
        totalfix+=Data.cost[i];
        // Depot fixed cost
        cout << "cost " << Data.cost[i] << endl;
    }

    fileinput >> Data.vehiclesfixed; // ?
    //vehiclesfixed=0.0;
    //cout << "vehicles " << vehiclesfixed << endl;
    fileinput >> tempi; // ?
    //cout << "tempi " << tempi << endl;



    Data.V = Data.N + Data.T; //number of nodes

    if ((tempi != 0)&&(tempi != 1)) {
        cout << "Error, correct the reading function" << tempi << endl;
        exit(0);
    }

    /// probability of scenarios
    Data.prob.resize(Data.Omega);
    for (int s = 0; s < Data.Omega; ++s) {
        Data.prob[s]=1.0/(Data.Omega);
    }

    //filling the distance matrix
    Data.dist.resize(Data.V);
    Data.worstd.resize(Data.V);
    for (int i = 0; i < Data.V; ++i) {
        Data.dist[i].resize(Data.V);
        Data.worstd[i] = 0;
        for (int j = 0; j < Data.V; ++j) {
            if (i < Data.T) {
                if (j < Data.T) {
                    Data.dist[i][j] = sqrt(pow(Data.MyDepots[i].x - Data.MyDepots[j].x, 2)
                                           + pow(Data.MyDepots[i].y - Data.MyDepots[j].y, 2));
                }
                else {
                    Data.dist[i][j] = sqrt(pow(Data.MyDepots[i].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                           + pow(Data.MyDepots[i].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2));
                }

            }
            else {
                if (j < Data.T) {
                    Data.dist[i][j] = sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyDepots[j].x, 2)
                                           + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyDepots[j].y, 2));
                }
                else {
                    Data.dist[i][j] = sqrt(pow(Data.MyCustomers[i - Data.MyDepots.size()].x - Data.MyCustomers[j - Data.MyDepots.size()].x, 2)
                                           + pow(Data.MyCustomers[i - Data.MyDepots.size()].y - Data.MyCustomers[j - Data.MyDepots.size()].y, 2));
                }
            }
            if (Data.dist[i][j] > Data.worstd[i]) Data.worstd[i] = Data.dist[i][j];
            //cout << "dist[" << i + 1 << "]" << "[" << j + 1 << "]" << dist[i][j] << endl;
        }
    }


    //Big M
    Data.BigM = 0;
    for (int i = 0; i < Data.V; i++)
    {
        Data.BigM += Data.worstd[i];
        //	//cout << " Worst[" << i + 1 << "] =" << worstd[i] << endl;
    }

    //BigM = V;
    //cout << " BigM" << "=" << BigM << endl;

    double totaldemand=0;
    for (int i = 0; i <Data.N ; ++i) {
        totaldemand+=Data.MyCustomers[i].q;
    }

    Data.L=0;


    //// creating the size-dependent parameters ////
    Data.dep_cap.resize(Data.T);
    Data.dep_cost.resize(Data.T);
    for (int i = 0; i < Data.T; ++i) {
        Data.dep_cap[i].resize(Data.facsize);
        Data.dep_cost[i].resize(Data.facsize);
        //cout<<"Cap Original= " << Data.MyDepots[i].QD <<endl;
        cout<< "Depot:"  << i+1  << " | cap Original: " <<Data.MyDepots[i].QD <<"Cost Original= " << Data.cost[i] <<endl;
        for (int j = 0; j < Data.facsize; ++j) {
            Data.dep_cap[i][j]=Data.MyDepots[i].QD*(1+(-2+j)*0.25);
            //cout<<"Cap size= " << j+1 << " | " <<Data.dep_cap[i][j] <<endl;

            Data.dep_cost[i][j]=1.0*int(Data.cost[i]+((Data.dep_cap[i][j]-Data.MyDepots[i].QD)/(2*Data.MyDepots[i].QD))*(totalfix/Data.T));
            cout<<"size= " << j+1 << " | cap: " << Data.dep_cap[i][j]<< " | cost: " <<Data.dep_cost[i][j] <<endl;
        }
    }

    //exit(0);



    /// reading the demand scenarios ///
    Data.demand.resize(Data.Omega);
    for (int s = 0; s < Data.Omega; ++s) {
        fileinput >> temps >> temps; // ?
        cout<< "tempi scenarios: " << temps <<endl;
        Data.demand[s].resize(Data.N);
        for (int i = 0; i < Data.N; ++i) {
            fileinput >> Data.demand[s][i]  ;
        }
    }

    fileinput >> temps; // END

    if (temps != "END") {
        cout << "Error, correct the reading function" << temps << endl;
        exit(0);
    }


    fileinput.close(); // closing the file
}

void GraphLLoRP(string graph, Parameters&Data, vector<vector<vector <bool>>> &Y, vector<vector <bool>> &Y0)
{
    vector <string> my_colors;
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");

    double GMLFactor = 10;
    fstream yed(graph, ios::app);

    yed << "graph [ hierarchic 1 directed 1" << std::endl;

    //Graficamos los origenes
    for (int i = Data.T; i < Data.V; ++i) {
        yed << "node [ id \"" << i + 1 -Data.T<< "\"" << " graphics [ x " << Data.MyCustomers[i-Data.T].x * GMLFactor
            << " y " << Data.MyCustomers[i-Data.T].y * GMLFactor
            << " w 10 h 10 type \"ellipse\" fill \"#c0c0c0\"] LabelGraphics [text \""
            << i + 1 -Data.T<< "\" fontSize 5 ] ]" << std::endl;
    }
    //Graficamos los depositos
    for (int i = 0; i < Data.T; ++i) {
        yed << "node [ id \"D" << i + 1 << "\"" << " graphics [ x " << Data.MyDepots[i].x * GMLFactor
            << " y " << Data.MyDepots[i].y * GMLFactor
            << " w 10 h 10 type \"rectangle\" fill \"#ffffff\"] LabelGraphics [text \"" << "D"
            << i + 1 << "\" fontSize 5 ] ]" << std::endl;
    }


    //Graficamos los arcos
    for (int l = 0; l < Data.L-1; l++)
    {
        for (int i = 0; i < Data.V; i++)
        {
            for (int j = 0; j < Data.N; j++) {
                if(i-Data.T==j) continue;
                if (Y[i][j][l] > 0.0001) {

                    if (i < Data.T) {
                        yed << "edge [ source \"D" << i + 1 << "\" target \"" << j + 1 << "\" ";


                    } else {

                        yed << "edge [ source \"" << i + 1 - Data.T << "\"  target \"" << j + 1 << "\" ";


                    }


                    yed << "graphics [ fill \"" << my_colors[10] << "\"" << "width 1 targetArrow "
                        << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector


                }


            }

        }
    }

    for (int i = 0; i < Data.N; ++i) {
        for (int j = 0; j < Data.T; ++j) {
            /// drawing the edges returning to the depots
            if (Y0[i][j] > 0.0001){
                yed << "edge [ source \"D" << j + 1 << "\"  target \"" << i + 1 << "\" ";

                yed << "graphics [ fill \"" << my_colors[2] << "\"" << "width 1 targetArrow "
                    << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector

            }
        }
    }
    yed << "]" << endl;

    cout << "grafico bien" << endl;
    yed.close();


}

void GraphLLoRP_withRad(string graph, Parameters&Data, vector<vector<vector <bool>>> &Y, vector<vector <bool>> &Y0, vector<bool>&Z)
{
    vector <string> my_colors;
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");

    //double GMLFactor = 10;
    double GMLFactor = 10;
    fstream yed(graph, ios::app);

    yed << "graph [ hierarchic 1 directed 1" << std::endl;

    //Graficamos los origenes
    for (int i = Data.T; i < Data.V; ++i) {
        yed << "node [ id \"" << i + 1 -Data.T<< "\"" << " graphics [ x " << Data.MyCustomers[i-Data.T].x * GMLFactor
            << " y " << Data.MyCustomers[i-Data.T].y * GMLFactor
            << " w 10 h 10 type \"ellipse\" fill \"#c0c0c0\"] LabelGraphics [text \""
            << i + 1 -Data.T<< "\" fontSize 5 ] ]" << std::endl;
    }
    //Graficamos los depositos
    for (int i = 0; i < Data.T; ++i) {
        yed << "node [ id \"D" << i + 1 << "\"" << " graphics [ x " << Data.MyDepots[i].x * GMLFactor
            << " y " << Data.MyDepots[i].y * GMLFactor
            << " w 10 h 10 type \"rectangle\" fill \"#ffffff\"] LabelGraphics [text \"" << "D"
            << i + 1 << "\" fontSize 5 ] ]" << std::endl;
    }

    //Graficamos los Radios de depots abiertos
    for (int i = 0; i < Data.T; ++i) {
        if (Z[i]>0.3){
            yed << "node [ id \"R" << i + 1 << "\"" << " graphics [ x " << Data.MyDepots[i].x * GMLFactor
                << " y " << Data.MyDepots[i].y * GMLFactor
                << " w "<< Data.Radius*2*GMLFactor << " h "<< Data.Radius*2*GMLFactor << " type \"ellipse\" hasFill 0 outline \"#000000\"] ]" << std::endl;
        }
    }

    //fill "#----" transparent "true"

    //Graficamos los arcos
    for (int l = 0; l < Data.L-1; l++)
    {
        for (int i = 0; i < Data.V; i++)
        {
            for (int j = 0; j < Data.N; j++) {
                if(i-Data.T==j) continue;
                if (Y[i][j][l] > 0.3) {

                    if (i < Data.T) {
                        yed << "edge [ source \"D" << i + 1 << "\" target \"" << j + 1 << "\" ";


                    } else {

                        yed << "edge [ source \"" << i + 1 - Data.T << "\"  target \"" << j + 1 << "\" ";


                    }


                    yed << "graphics [ fill \"" << my_colors[10] << "\"" << "width 1 targetArrow "
                        << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector


                }


            }

        }
    }

    for (int i = 0; i < Data.N; ++i) {
        for (int j = 0; j < Data.T; ++j) {
            /// drawing the edges returning to the depots
            if (Y0[i][j] > 0.0001){
                yed << "edge [ source \"" << i + 1 << "\"  target \"D" << j + 1 << "\" ";

                yed << "graphics [ fill \"" << my_colors[2] << "\"" << "width 1 targetArrow "
                    << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector

            }
        }
    }
    yed << "]" << endl;

    cout << "grafico bien" << endl;
    yed.close();


}

void GraphLLoRP_withRad_cost(string graph, Parameters&Data, vector<vector<bool>> &X, vector<vector <bool>> &Y0, vector<bool>&Z)
{
    vector <string> my_colors;
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");
    my_colors.push_back("#FF0000");
    my_colors.push_back("#00FF00");
    my_colors.push_back("#0000FF");
    my_colors.push_back("#FFC125");
    my_colors.push_back("#00FFFF");
    my_colors.push_back("#FF00FF");
    my_colors.push_back("#5E5E5E");
    my_colors.push_back("#000080");
    my_colors.push_back("#000000");
    my_colors.push_back("#008000");
    my_colors.push_back("#008080");
    my_colors.push_back("#800080");
    my_colors.push_back("#800000");
    my_colors.push_back("#643200");
    my_colors.push_back("#C86400");
    my_colors.push_back("#964B00");

    if (Data.problemID==0) Data.Radius= (Data.Radius*Data.maxdist)/100;

    cout<<" RAD= " << Data.Radius <<endl;

    //double GMLFactor = 10;
    double GMLFactor = 10;
    fstream yed(graph, ios::app);

    yed << "graph [ hierarchic 1 directed 1" << std::endl;

    //Graficamos los origenes
    for (int i = Data.T; i < Data.V; ++i) {
        yed << "node [ id \"" << i + 1 -Data.T<< "\"" << " graphics [ x " << Data.MyCustomers[i-Data.T].x * GMLFactor
            << " y " << Data.MyCustomers[i-Data.T].y * GMLFactor
            << " w 10 h 10 type \"ellipse\" fill \"#c0c0c0\"] LabelGraphics [text \""
            << i + 1 -Data.T<< "\" fontSize 5 ] ]" << std::endl;
    }
    //Graficamos los depositos
    for (int i = 0; i < Data.T; ++i) {
        yed << "node [ id \"D" << i + 1 << "\"" << " graphics [ x " << Data.MyDepots[i].x * GMLFactor
            << " y " << Data.MyDepots[i].y * GMLFactor
            << " w 10 h 10 type \"rectangle\" fill \"#ffffff\"] LabelGraphics [text \"" << "D"
            << i + 1 << "\" fontSize 5 ] ]" << std::endl;
    }

    cout<< "nodes ok"<< endl;


    //Graficamos los Radios de depots abiertos
    for (int i = 0; i < Data.T; ++i) {
        if (Z[i]>0.3){
            yed << "node [ id \"R" << i + 1 << "\"" << " graphics [ x " << Data.MyDepots[i].x * GMLFactor
                << " y " << Data.MyDepots[i].y * GMLFactor
                << " w "<< Data.Radius*2*GMLFactor << " h "<< Data.Radius*2*GMLFactor << " type \"ellipse\" hasFill 0 outline \"#000000\"] ]" << std::endl;
        }
    }

    cout<< "radious ok"<< endl;

    //fill "#----" transparent "true"

    //Graficamos los arcos

    for (int i = 0; i < Data.V; i++)
    {
        for (int j = 0; j < Data.V; j++)
        {
            if (i==j) continue;
            if ((i<Data.T)&(j<Data.T)) continue;
            //if (X[i][j][k].get(GRB_DoubleAttr_X)>0.001)
            if (X[i][j]>0.001)
            {
                if (Data.T > i)
                {
                    if(j>=Data.T) {
                        yed << "edge [ source \"D" << i + 1 << "\" target \"" << j + 1 - Data.T << "\" ";
                        yed << "graphics [ fill \"" << my_colors[10] << "\"" << "width 1 targetArrow " << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector
                    }
                    else continue;


                }
                else
                {

                    if (Data.T > j)
                    {

                        yed << "edge [ source \"" << i + 1 -Data.T<< "\"  target \"D" << j + 1 << "\" ";
                        yed << "graphics [ fill \"" << my_colors[10] << "\"" <<  "style " << "\"dashed\""<< "width 1 targetArrow " << "\"standard\" ] ]" << std::endl; //arreglar el color con un vector
                    }
                    else
                    {
                        yed << "edge [ source \"" << i + 1 -Data.T<< "\"  target \"" << j + 1 -Data.T<< "\" ";
                        yed << "graphics [ fill \"" << my_colors[10] << "\"" << "width 1 targetArrow " << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector
                    }

                }


                //yed << "graphics [ fill \"" << my_colors[10] << "\"" << "width 1 targetArrow " << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector


            }

        }

    }




    for (int i = 0; i < Data.N; ++i) {
        for (int j = 0; j < Data.T; ++j) {
            /// drawing the edges returning to the depots
            if (Y0[i][j] > 0.0001){
                yed << "edge [ source \"" << i + 1 << "\"  target \"D" << j + 1 << "\" ";

                yed << "graphics [ fill \"" << my_colors[2] << "\"" << "width 1 targetArrow "
                    << "\"standard\"  ] ]" << std::endl; //arreglar el color con un vector

            }
        }
    }
    yed << "]" << endl;

    cout << "grafico bien" << endl;
    yed.close();


}

