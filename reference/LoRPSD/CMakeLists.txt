cmake_minimum_required(VERSION 3.12)
project(LoRPSD)
option(CXX "enable C++ compilation" ON)
if(CXX)
    enable_language(CXX)
endif()

set(CMAKE_CXX_STANDARD 14)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")
# CPLEX
#find_package(CPLEX REQUIRED)
#include_directories(${CPLEX_INCLUDE_DIRS})
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -DIL_STD")

# GUROBI
#set(GRB_LICENSE_FILE /home/carlosrey/gurobi903/linux64/gurobi.lic)
set(GRB_LICENSE_FILE /home/alan/gurobi.lic)
set(GUROBI_DIR /home/alan/gurobi1003/linux64)

#set(GRB_LICENSE_FILE /home/alan/gurobi811/linux64/gurobi.lic)
#set(GUROBI_DIR /home/alan/gurobi811/linux64)


find_package(GUROBI REQUIRED)
include_directories(${GUROBI_INCLUDE_DIRS})

# OPEN MP
find_package(OpenMP REQUIRED)

#the first is the original
#add_executable(LoRPSD main.cpp files.h files.cpp functions.cpp functions.h  initial.cpp initial.h  localsearch.cpp localsearch.h hybrid.cpp hybrid.h perturbation.cpp perturbation.h algorithmbody.cpp algorithmbody.h final_lkh.cpp final_lkh.h  model_first_mdktrp.cpp model_first_mdktrp.h  StochasticHeuristic.cpp StochasticHeuristic.h  bycbenders_gur.cpp bycbenders_gur.h benders.cpp benders.h LLrRP.cpp  LLrRP.h)

add_executable(LoRPSD main.cpp files.h files.cpp  models.h models.cpp
        stcmodels.cpp
        stcmodels.h
        initial.cpp
        initial.h functions.cpp functions.h)

#bycbenders.cpp bycbenders.h


#add_executable(LoRPSD main.cpp CPLX_Model.h CPLX_Model.cpp files.h files.cpp functions.cpp functions.h  initial.cpp initial.h localsearch.cpp localsearch.h hybrid.cpp hybrid.h perturbation.cpp perturbation.h algorithmbody.cpp algorithmbody.h final_lkh.cpp final_lkh.h initial_mdktrp.cpp initial_mdktrp.h mdccvrpmilp.cpp mdccvrpmilp.h llrp_model1.cpp llrp_model1.h model_first_mdktrp.cpp model_first_mdktrp.h lowerbounds.cpp lowerbounds.h sampling.cpp sampling.h)

#add_executable(LoRPSD main.cpp files.h files.cpp  bycbenders.cpp bycbenders.h)


message("${GUROBI_LIBRARY} ${GUROBI_CXX_LIBRARY} ${GUROBI_CXX_DEBUG_LIBRARY}")
#target_link_libraries(LoRPSD ${CPLEX_LIBRARIES} pthread)
target_link_libraries(LoRPSD OpenMP::OpenMP_CXX ${CMAKE_DL_LIBS})

if(CXX)
    target_link_libraries(LoRPSD optimized ${GUROBI_CXX_LIBRARY}
            debug ${GUROBI_CXX_DEBUG_LIBRARY})
endif()

target_link_libraries(LoRPSD ${GUROBI_LIBRARY})

if(${CMAKE_SOURCE_DIR} STREQUAL ${CMAKE_CURRENT_SOURCE_DIR})
    include(FeatureSummary)
    feature_summary(WHAT ALL)
endif()
