//
// Created by alan on 07/04/22.
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


#ifndef LLORP_H
#define LLORP_H



void createmodelnew(string instance, Parameters &Data, string &results, double &of);

#endif //LLORP_H
