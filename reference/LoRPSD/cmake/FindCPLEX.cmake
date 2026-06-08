if (NOT CPLEX_INSTALL_PATH OR CPLEX_INSTALL_PATH STREQUAL "")

    set(DEFAULT_CPLEX_INSTALL_PATH "/opt/ibm/ILOG/CPLEX_Studio*")
    message(STATUS "Parameter CPLEX_INSTALL_PATH was not given, looking for IBM CPLEX inside ${DEFAULT_CPLEX_INSTALL_PATH}")

    file(GLOB CPLEX_DIRS /opt/ibm/ILOG/CPLEX_Studio*)
    list(LENGTH CPLEX_DIRS CPLEX_DIRS_LENGTH)

    if (CPLEX_DIRS_LENGTH EQUAL 0)
        message(FATAL_ERROR "Looking for IBM CPLEX inside ${DEFAULT_CPLEX_INSTALL_PATH} failed.")
    endif()

    list(GET CPLEX_DIRS 0 CPLEX_INSTALL_PATH)
    message(STATUS "Set CPLEX_INSTALL_PATH=${CPLEX_INSTALL_PATH}")
else()
    message(STATUS "User provided CPLEX_INSTALL_PATH=${CPLEX_INSTALL_PATH}")
endif()

string(CONCAT CPLEX_DIR ${CPLEX_INSTALL_PATH};/cplex)
string(CONCAT CONCERT_DIR ${CPLEX_INSTALL_PATH};/concert)

find_path(CPLEX_INCLUDE_DIR ilocplex.h HINTS "${CPLEX_DIR}/include/ilcplex")
find_path(CONCERT_INCLUDE_DIR iloalg.h HINTS "${CONCERT_DIR}/include/ilconcert")

if(APPLE)
    find_library(CPLEX_CPP_LIBRARY libcplex.a HINTS "${CPLEX_DIR}/lib/x86-64_osx/static_pic")
    find_library(CONCERT_CPP_LIBRARY libconcert.a HINTS "${CONCERT_DIR}/lib/x86-64_osx/static_pic")
    find_library(CPLEX_ILO_CPP_LIBRARY libilocplex.a HINTS "${CPLEX_DIR}/lib/x86-64_osx/static_pic")
elseif(UNIX)
    find_library(CPLEX_CPP_LIBRARY libcplex.a x HINTS "${CPLEX_DIR}/lib/x86-64_linux/static_pic")
    find_library(CONCERT_CPP_LIBRARY libconcert.a libcplexdistmip.a HINTS "${CONCERT_DIR}/lib/x86-64_linux/static_pic")
    find_library(CPLEX_ILO_CPP_LIBRARY libilocplex.a HINTS "${CPLEX_DIR}/lib/x86-64_linux/static_pic")
endif()

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(CPLEX DEFAULT_MSG CPLEX_CPP_LIBRARY  CPLEX_ILO_CPP_LIBRARY CONCERT_CPP_LIBRARY  CPLEX_INCLUDE_DIR CONCERT_INCLUDE_DIR)

if(CPLEX_FOUND)
    set(CPX_LICENSE_FILE "~/cplex.research.lic")
    set(CPLEX_INCLUDE_DIRS ${CPLEX_INCLUDE_DIR}/.. ${CONCERT_INCLUDE_DIR}/..)
    set(CPLEX_LIBRARIES ${CPLEX_ILO_CPP_LIBRARY} ${CPLEX_CPP_LIBRARY}  ${CONCERT_CPP_LIBRARY})
else()
    message(FATAL_ERROR "Couod not find solver IBM CPLEX")
endif(CPLEX_FOUND)

mark_as_advanced(CPLEX_LIBRARY CPLEX_CPP_LIBRARY CPLEX_INCLUDE_DIR)