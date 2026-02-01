# Import the external modules
import numpy as np
from pyclmuapp import usp_clmu
import shutil
import os
from multiprocessing import Pool, cpu_count
import argparse

def get_params():
    parser = argparse.ArgumentParser(description='Run CLMU')
    parser.add_argument('--n', type=int, 
                        default=400, help='Number of samples to generate')
    parser.add_argument('--nproc', type=int, 
                        default=20, help='Number of processes to use')
    parser.add_argument('--container_type', type=str,
                        default='docker', help='Container type to use')
    return parser.parse_args()

def initialize_params():
    try:
        import __main__  # check if running as script
        if hasattr(__main__, '__file__'):  # running as script
            args = get_params()
            return args.n, args.nproc, args.container_type
    except ImportError:
        pass
    return 400, 20, 'docker'

n, nproc, container_type = initialize_params()

## <--- 1. Define the parameter setting functions --->
def set_action_mode(mode: float, usp_input_path):
    #mode = int(mode)
    with open(f'{usp_input_path}/action_mode.txt', 'w') as f:
        f.write(f'{mode}')
        
def set_tg_threshold(threshold: float, usp_input_path):
    threshold = threshold + 273.15
    with open(f'{usp_input_path}/tg_threshold.txt', 'w') as f:
        f.write(f'{threshold}')
        
def set_water_tank_size(size: float, usp_input_path):
    with open(f'{usp_input_path}/water_tank_size.txt', 'w') as f:
        f.write(f'{size}')

## <--- 2. Define the run_clmu function --->
## This function is used to run the CLMU model and return the dataset
def run_clmu(
             exp=(1, 35, 5),
             case_num=0,
             SURF="../data/surfdata_1x1_JP-Yoy_detailed_simyr2000_c230710.nc",
             FORCING="../data/CTSM_DATM_JP-Yoy_2006-2020.nc",
             RUN_STARTDATE = "2018-01-01",
             STOP_N = "1"):
    usp = usp_clmu(pwd=os.path.join(os.getcwd(), f'workdir/workdir{case_num}'), # will create a temporary working directory workdir
                   container_type = container_type)
                   

    shutil.copytree('src', usp.input_path+'/usp/SourceMods/src.clm', dirs_exist_ok=True)
    #shutil.copy('action_mode.txt', usp.input_path+'/action_mode.txt')
    #shutil.copy('tg_threshold.txt', usp.input_path+'/tg_threshold.txt')
    #shutil.copy('water_tank_size.txt', usp.input_path+'/water_tank_size.txt')
    shutil.copy('usp_irr.sh', usp.input_path+'/usp/usp.sh')

    set_action_mode(exp[0], usp.input_path)
    set_tg_threshold(exp[1], usp.input_path)
    set_water_tank_size(exp[2], usp.input_path)
    
    # the SourceMods/src.clm is not including the urban irr model
    #usp_init = usp.run(
    #            case_name = "urbirr_spinup",
    #            SURF = SURF,
    #            FORCING = FORCING,
    #            RUN_STARTDATE = "2008-01-01", # the start date of the simulation, must include in the forcing file time range
    #            STOP_OPTION = "nmonths", # can be 'ndays', 'nmonths', 'nyears', 'nsteps'; nsteps means 1800s
    #            STOP_N = "126", # run for 10 years)
    #)
    #epoch_num=50
 
    usp_res = usp.run(
                    case_name = "roof_sp",
                    SURF = SURF,
                    FORCING = FORCING,
                    RUN_STARTDATE = RUN_STARTDATE, # the start date of the simulation, must include in the forcing file time range
                    STOP_OPTION = "nyears", # can be 'ndays', 'nmonths', 'nyears', 'nsteps'; nsteps means 1800s
                    STOP_N = STOP_N, # run for 10 years
                    hist_type="COLS",
                    #hist_nhtfrq=0, # output frequency - 0 means monthly
                    #hist_type="'GRID','COLS'",
                    #RUN_TYPE= "branch",
                    #RUN_REFCASE= "urbirr_spinup",
                    #RUN_REFDATE= "2018-07-01",
                )
    
    #os.system(f'rm -rf {usp.input_path}')
    
    #ds = usp.nc_view()
    
    print(f'Experiment {exp} , case_num {case_num} completed.')
    print(f'usp_res: {usp_res}')
    
    #the ouptut path is in op_path
    op_path = os.path.join(usp.output_path, 'lnd', 'hist')
    
    usp_res = []
    
    for filename in os.listdir(op_path):
        
        usp_res.append(os.path.join(op_path, filename))
    
    return usp_res


## <--- 3. Define the Latin Hypercube Sampling function --->
def LHS(n, ranges, seed=0):
    """
    Generate Latin Hypercube Sample (LHS) in a given dimension with different ranges for each dimension.

    Args:
        n (int): Number of samples.
        ranges (list of tuples): Ranges for each dimension. Each tuple contains (min, max) for that dimension.

    Returns:
        np.array: Latin Hypercube Sample.
    """
    
    np.random.seed(seed)

    dims = len(ranges)

    lhs = np.zeros((n, dims))

    # Generate random numbers for each dimension
    for i, (min_val, max_val) in enumerate(ranges):
        step = (max_val - min_val) / n
        for j in range(n):
            lhs[j, i] = np.random.uniform(min_val + j * step, min_val + (j + 1) * step)

    # Shuffle the samples
    for i in range(dims):
        np.random.shuffle(lhs[:,i])

    return lhs

def worker(worker_args):
    # Set the parameters
    exp, case_num, input_dict = worker_args
    
    # Run the CLMU model
    res = run_clmu(
                  exp=exp,
                  case_num=case_num,
                  SURF=input_dict['SURF'],
                  FORCING=input_dict['FORCING'],
                  RUN_STARTDATE=input_dict['RUN_STARTDATE'],
                  STOP_N=input_dict['LENGTH'])
    outputpath='../data/water_tank_exps/'
    os.system(f'cp {res[0]} {outputpath}/roof_sp_{exp[0]}_{exp[1]}_{exp[2]}.nc')
    os.system(f'rm -rf {res[0]}')
    print(f'Experiment {exp} completed.')
    return res

## <--- 4. Define the main function --->
def main(exp_range = [
                (1, 20),  # action_mode
                (35, 75),  # tg_threshold
                (5, 50)  # water_tank_size
            ],
        cities = ['JP-Yoy'],
        n = 100,
        nproc = None
        ):

    """
    Main function to run the CLMU model with Latin Hypercube Sampling.
    
    Args:
        exp_range (list of tuples): Ranges for each parameter. Each tuple contains (min, max) for that parameter.
        cities (list of str): List of cities to run the model.
        n (int): Number of samples.
        nproc (int): Number of processes to run in parallel.
    """
    
    input_dict ={}

    for city in cities:
        forcing = os.listdir(f'../data/URBAN_PLUMBER/datm_files/{city}/CLM1PT_data')[0]
        date = forcing.split('_')[-1].split('.')[0]
        start_year = date.split('-')[0]
        end_year = date.split('-')[1]
        surfdata = f'../data/URBAN_PLUMBER/input_files/{city}/surfdata_1x1_{city}_detailed_simyr2000_c230710.nc'
        forcingdata = f'../data/URBAN_PLUMBER/datm_files/{city}/CLM1PT_data/{forcing}'
        length = int(end_year) - int(start_year) + 1
        print(f'City: {city}, Start Year: {start_year}, End Year: {end_year}, Length: {length}')
        input_dict[city] = {
            'SURF': surfdata,
            'FORCING': forcingdata,
            'RUN_STARTDATE': f'{start_year}-01-01',
            'LENGTH': length
        }
        
        lhs_exps = LHS(n, exp_range)
        #lhs_exps = lhs_exps.round(0)
        
        print(f'City: {city}')
        print(f'Number of experiments: {n}')
        print(f'Experiment ranges: {exp_range}')
        print(f'Experiments: {lhs_exps}')
        
        num_processes = cpu_count() if nproc is None else nproc
        print(f"num_processes: {num_processes}")
        
        for i in range(0, len(lhs_exps), num_processes):
        
            # multiprocessing.Pool is used to run the CLMU model in parallel
            with Pool(processes=num_processes) as pool:
                batch_results = pool.map(
                    worker,
                    [(lhs_exp, j, input_dict[city]) for j, lhs_exp in enumerate(lhs_exps[i:i+num_processes])]
                )
                
            print(f'Batch {i//num_processes} completed.')
            
            
if __name__ == '__main__':
    os.makedirs('../data/water_tank_exps/', exist_ok=True)
    main(exp_range = [
                (1, 20),  # action_mode
                #(35, 75),  # tg_threshold
                #(5, 50)  # water_tank_size
                (35, 65),  # tg_threshold
                (0.01, 20)  # water_tank_size
            ],
        cities = ['JP-Yoy'],
        n = n,
        nproc = nproc)


