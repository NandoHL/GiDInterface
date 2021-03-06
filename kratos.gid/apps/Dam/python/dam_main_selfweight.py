from __future__ import print_function, absolute_import, division #makes KratosMultiphysics backward compatible with python 2.6 and 2.7

# Time monitoring
import time as timer
print(timer.ctime())
initial_time = timer.perf_counter()

## Importing modules -----------------------------------------------------------------------------------------

# Import system python
import os

# Import kratos core and applications
import KratosMultiphysics
import KratosMultiphysics.ExternalSolversApplication as KratosSolvers
#import KratosMultiphysics.TrilinosApplication as TrilinosApplication
import KratosMultiphysics.ConvectionDiffusionApplication as KratosConvDiff
import KratosMultiphysics.SolidMechanicsApplication as KratosSolid
import KratosMultiphysics.PoromechanicsApplication as KratosPoro
import KratosMultiphysics.DamApplication as KratosDam

# Parsing the parameters
parameter_file = open("ProjectParameters.json",'r')
ProjectParameters = KratosMultiphysics.Parameters( parameter_file.read())

# Parsing parmeters of Selfweight Problem
self_parameter_file = open("ProjectParametersSelfWeight.json",'r')
SelfWeightProjectParameters = KratosMultiphysics.Parameters( self_parameter_file.read())

# Parallel Configuration
parallel_type = ProjectParameters["problem_data"]["parallel_type"].GetString()
parallel=KratosMultiphysics.OpenMPUtils()
parallel.SetNumThreads(ProjectParameters["problem_data"]["number_of_threads"].GetInt())
if parallel_type == "MPI":
    import KratosMultiphysics.mpi as KratosMPI
    print("MPI parallel configuration. OMP_NUM_THREADS =",parallel.GetNumThreads())
else:
    print("OpenMP parallel configuration. OMP_NUM_THREADS =",parallel.GetNumThreads())

## Defining variables ----------------------------------------------------------------------------------------

domain_size = ProjectParameters["problem_data"]["domain_size"].GetInt()
problem_name = ProjectParameters["problem_data"]["problem_name"].GetString()
problem_path = os.getcwd()
echo_level = ProjectParameters["solver_settings"]["echo_level"].GetInt()
buffer_size = ProjectParameters["solver_settings"]["buffer_size"].GetInt()
use_streamline_utility = ProjectParameters["problem_data"]["streamlines_utility"].GetBool()
delta_time = ProjectParameters["problem_data"]["time_step"].GetDouble()
end_time = ProjectParameters["problem_data"]["end_time"].GetDouble()
time = ProjectParameters["problem_data"]["start_time"].GetDouble()
tol = delta_time*1.0e-10
time_scale = ProjectParameters["problem_data"]["time_scale"].GetString()
# Time Units Converter
if(time_scale=="Weeks"):               # Factor to pass from weeks to seconds
    time_unit_converter = 604800.0
elif(time_scale=="Days"):               # Factor to pass from days to seconds
    time_unit_converter = 86400.0
elif(time_scale=="Hours"):              # Factor to pass from hours to seconds
    time_unit_converter = 3600.0
else:                                       # No changes
    time_unit_converter = 1.0

# Update time variables
start_time = time
delta_time = delta_time * time_unit_converter
end_time = end_time * time_unit_converter
time = time * time_unit_converter
tol = tol * time_unit_converter

## PREVIOUS SELFWEIGHT PROBLEM ------------------------------------------------------------------------------------------------
## In case that was needed a previous problem just considering the selfweight is solved. The aim of this is to sum the computed
## stresses but not the displacements field. This can be controlled through a tab in the inteface.

consider_selfweight = ProjectParameters["problem_data"]["consider_selfweight"].GetBool()
if(consider_selfweight == True):

    ## Creating Selfweight model part --------------------------------------------------------------
    self_weight_model_part = KratosMultiphysics.ModelPart("SelfWeight")
    self_weight_model_part.ProcessInfo.SetValue(KratosMultiphysics.DOMAIN_SIZE, domain_size)
    self_weight_model_part.ProcessInfo.SetValue(KratosMultiphysics.TIME, time)
    self_weight_model_part.ProcessInfo.SetValue(KratosMultiphysics.DELTA_TIME, delta_time)
    self_weight_model_part.ProcessInfo.SetValue(KratosPoro.TIME_UNIT_CONVERTER, time_unit_converter)

    ## Construct the solver for selfweight problem -------------------------------------------------
    selfweight_solver_module = __import__(SelfWeightProjectParameters["solver_settings"]["solver_type"].GetString())
    selfweight_solver = selfweight_solver_module.CreateSolver(self_weight_model_part, SelfWeightProjectParameters["solver_settings"])
    selfweight_solver.AddVariables()
    selfweight_solver.ImportModelPart()
    selfweight_solver.AddDofs()

    ## Kratos Selfweight Model ---------------------------------------------------------------------
    DamSelfWeightModel = KratosMultiphysics.Model()
    DamSelfWeightModel.AddModelPart(self_weight_model_part)

    ## Get the list of the submodel part in the object Model
    #for i in range(SelfWeightProjectParameters["solver_settings"]["processes_sub_model_part_list"].size()):
    #    self_part_name = SelfWeightProjectParameters["solver_settings"]["processes_sub_model_part_list"][i].GetString()
    #    DamSelfWeightModel.AddModelPart(self_weight_model_part.GetSubModelPart(self_part_name))


    ## Initialize ----------------------------------------------------------------------------------

    # Construct processes to be applied
    import process_factory
    self_list_of_processes = process_factory.KratosProcessFactory(DamSelfWeightModel).ConstructListOfProcesses( SelfWeightProjectParameters["constraints_process_list"] )

    # Initialize processes
    for process in self_list_of_processes:
        process.ExecuteInitialize()

    # Set TIME and DELTA_TIME and fill the previous steps of the buffer with the initial conditions
    self_time = time - (buffer_size-1)*delta_time
    self_weight_model_part.ProcessInfo.SetValue(KratosMultiphysics.TIME, time)
    for step in range(buffer_size-1):
       self_time = self_time + delta_time
       self_weight_model_part.CloneTimeStep(self_time)

    # Initialize the solver
    selfweight_solver.Initialize()

    # ExecuteBeforeSolutionLoop
    for process in self_list_of_processes:
        process.ExecuteBeforeSolutionLoop()

    # Getting gravity direction
    direction_selfweight = ProjectParameters["problem_data"]["selfweight_direction"].GetString()
    if(direction_selfweight == "X"): 
        variable_name = KratosMultiphysics.VOLUME_ACCELERATION_X
    elif(direction_selfweight == "Y"):
        variable_name = KratosMultiphysics.VOLUME_ACCELERATION_Y
    else:
        variable_name = KratosMultiphysics.VOLUME_ACCELERATION_Z

    # Set the acceleration at the nodes according to gravity direction
    for node in self_weight_model_part.Nodes:
        node.SetSolutionStepValue(variable_name, -9.81)

    # Solving selfweight problem
    selfweight_solver.Solve()

    # Cleaning selfweight solver
    selfweight_solver.Clear()

    # Initialize transfer_selfweight_stress_utility
    import transfer_selfweight_stress_utility
    transfer_utility = transfer_selfweight_stress_utility.TransferSelfweightStressToMainModelPartUtility()


## DEFINED PROBLEM ------------------------------------------------------------------------------------------------

## Model part ------------------------------------------------------------------------------------------------

# Defining the model part
main_model_part = KratosMultiphysics.ModelPart(ProjectParameters["problem_data"]["model_part_name"].GetString())
main_model_part.ProcessInfo.SetValue(KratosMultiphysics.DOMAIN_SIZE, domain_size)
main_model_part.ProcessInfo.SetValue(KratosMultiphysics.TIME, time)
main_model_part.ProcessInfo.SetValue(KratosMultiphysics.DELTA_TIME, delta_time)
main_model_part.ProcessInfo.SetValue(KratosPoro.TIME_UNIT_CONVERTER, time_unit_converter)

# Construct the solver (main setting methods are located in the solver_module)
solver_module = __import__(ProjectParameters["solver_settings"]["solver_type"].GetString())
solver = solver_module.CreateSolver(main_model_part, ProjectParameters["solver_settings"])

# Add problem variables
solver.AddVariables()

# Read model_part (note: the buffer_size is set here)
solver.ImportModelPart()

# Add degrees of freedom
solver.AddDofs()

# Creation of Kratos model
DamModel = KratosMultiphysics.Model()
DamModel.AddModelPart(main_model_part)

# Build sub_model_parts or submeshes (rearrange parts for the application of custom processes)
## Get the list of the submodel part in the object Model
#for i in range(ProjectParameters["solver_settings"]["processes_sub_model_part_list"].size()):
#    part_name = ProjectParameters["solver_settings"]["processes_sub_model_part_list"][i].GetString()
#    DamModel.AddModelPart(main_model_part.GetSubModelPart(part_name))

# Print model_part and properties
if(echo_level > 1):
    print(main_model_part)
    for properties in main_model_part.Properties:
        print(properties)


## Initialize ------------------------------------------------------------------------------------------------

# Construct processes to be applied
import process_factory
list_of_processes = process_factory.KratosProcessFactory(DamModel).ConstructListOfProcesses( ProjectParameters["constraints_process_list"] )
list_of_processes += process_factory.KratosProcessFactory(DamModel).ConstructListOfProcesses( ProjectParameters["loads_process_list"] )

# Print list of constructed processes
if(echo_level>1):
    for process in list_of_processes:
        print(process)

# Initialize processes
for process in list_of_processes:
    process.ExecuteInitialize()

# Set TIME and DELTA_TIME and fill the previous steps of the buffer with the initial conditions
time = time - (buffer_size-1)*delta_time
main_model_part.ProcessInfo.SetValue(KratosMultiphysics.TIME, time)
for step in range(buffer_size-1):
    time = time + delta_time
    main_model_part.CloneTimeStep(time)

# Initialize GiD I/O
computing_model_part = solver.GetComputingModelPart()
output_settings = ProjectParameters["output_configuration"]
if parallel_type == "OpenMP":
    import poromechanics_cleaning_utility
    poromechanics_cleaning_utility.CleanPreviousFiles(problem_path) # Clean previous post files
    from gid_dam_output_process import GiDDamOutputProcess
    gid_output = GiDDamOutputProcess(computing_model_part,
                                  problem_name,
                                  start_time,
                                  output_settings)
else:
    from gid_output_process_mpi import GiDOutputProcessMPI
    gid_output = GiDOutputProcessMPI(computing_model_part,
                                     problem_name,
                                     start_time,
                                     output_settings)
gid_output.ExecuteInitialize()

# Initialize the solver
solver.Initialize()

# ExecuteBeforeSolutionLoop
for process in list_of_processes:
    process.ExecuteBeforeSolutionLoop()

## Set results when they are written in a single file
gid_output.ExecuteBeforeSolutionLoop()

# Initialize streamlines_output_utility
UseStreamlineUtility = False
if (use_streamline_utility == True and domain_size==3):
    UseStreamlineUtility = True
    import streamlines_output_utility
    streamline_utility = streamlines_output_utility.StreamlinesOutputUtility(domain_size)

if (echo_level > 1):
    f = open("ProjectParametersOutput.json", 'w')
    f.write(ProjectParameters.PrettyPrintJsonString())
    f.close()

## Temporal loop ---------------------------------------------------------------------------------------------

while( (time+tol) <= end_time ):

    # Update temporal variables
    delta_time = main_model_part.ProcessInfo[KratosMultiphysics.DELTA_TIME]
    time = time + delta_time
    main_model_part.CloneTimeStep(time)

    # Update imposed conditions
    for process in list_of_processes:
        process.ExecuteInitializeSolutionStep()

    gid_output.ExecuteInitializeSolutionStep()

    # Solve step
    solver.Solve()

    # streamlines_output_utility
    if (UseStreamlineUtility== True):
        streamline_utility.ComputeOutputStep( main_model_part ,domain_size)

    gid_output.ExecuteFinalizeSolutionStep()

    for process in list_of_processes:
        process.ExecuteFinalizeSolutionStep()

    for process in list_of_processes:
        process.ExecuteBeforeOutputStep()

    # transfer_selfweight_stress_utility
    if (consider_selfweight== True):
        transfer_utility.Transfer( self_weight_model_part, main_model_part, domain_size)

    # Write GiD results
    if gid_output.IsOutputStep():
        gid_output.PrintOutput()

    for process in list_of_processes:
        process.ExecuteAfterOutputStep()


## Finalize --------------------------------------------------------------------------------------------------

# Finalizing output files
gid_output.ExecuteFinalize()

for process in list_of_processes:
    process.ExecuteFinalize()

# Finalizing strategy
if parallel_type == "OpenMP":
    solver.Clear()

# Time control
print("Analysis Completed. Elapsed Time = %.3f" % (timer.perf_counter() - initial_time)," seconds.")
print(timer.ctime())
