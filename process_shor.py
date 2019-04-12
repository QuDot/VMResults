import matplotlib
matplotlib.use('TkAgg')
from matplotlib import cm
import matplotlib.pyplot as plt

import numpy as np
import math
import argparse
import pandas as pd
from sympy.ntheory.continued_fraction import continued_fraction_periodic, continued_fraction_convergents

#TODO --save_csv flag to save a txt output of the resulting df

def get_lowest_cf(p,d,x):
    #find convergent cfs
    cfp = continued_fraction_periodic(p,d)
    fracs = list(continued_fraction_convergents(cfp))

    #get list of denominators
    denoms = [int(f.q) for f in fracs]
    try:
        val = max([num for num in denoms if num < x])
    except ValueError:
        raise('List is empty!')

    return val

def out_to_df(filename):
    data = pd.read_csv(filename, sep=",", header=0, dtype={'state': str})
    data = data.sort_values(by=['frequency'],ascending=False)
    avg = data['frequency'].mean()
    std = data['frequency'].std()

    #Slice df to get top frequencies
    #data = data[data.frequency > avg+(2.5*std)] #slicing to get only the top frequencies
    data['int'] = data.state.apply(lambda x: int(x,2))
    plot_df = data[['int','frequency']].copy().sort_values(by=['int'],ascending=True)
    return {'raw':data,'plot':plot_df}

def get_gcd(period,N,x):
    p = int(period/2)
    term = x**p
    a = math.gcd(term+1,N)
    b = math.gcd(term-1,N)

    nums = [x for x in [a,b] if x!=1]
    if len(nums)==0:
        return 0
    elif len(nums)==1:
        return (nums[0],int(N/nums[0]))
    else:
        return tuple(nums)

def test_shor(bit,N,x,k,l):
    #function to test it on specific random bitstring
    d = 2**k
    p = int(bit, 2) >> l
    period = get_lowest_cf(p,d,x)
    print(f'Period:{period}')
    if period%2!=0: #if odd
        print('Fail, Odd Period')
        return 0
    else:
        factors = get_gcd(period,N,x)
        if factors==0:
            print('Fail, Factors are 1')
            return 0
        else:
            print(f'Factors: {factors}')
            print('Success!')
            return factors

def classical_shor(df,N,x,k,l,save=False):
    num_passes=0
    sum_passes=0
    num_even_period=0
    num_failed=0
    passed_freqs = []
    freq_results = []
    df = df.copy()
    df['pass'] = np.nan
    d = 2**k
    for idx, row in df.iterrows():
        p = row['int'] >> l
        period = get_lowest_cf(p,d,x)
        if period%2!=0: #if odd
            df.loc[idx,'pass'] = False
            num_failed+=1
            continue
        else:
            num_even_period+=1
            factors = get_gcd(period,N,x)
            if factors==0:
                df.loc[idx,'pass'] = False
                num_failed+=1
                continue
            else:
                passed_freqs.append(row['frequency'])
                sum_passes += row['frequency']
                freq_results.append(factors)
                df.loc[idx,'pass'] = True
                num_passes+=1
    print(f'Number of passes:{num_passes}')
    print(f'Sum of passes:{sum_passes}')
    print(f'Number of even periods:{num_even_period}')
    return df

def plot_results(df,N,x,save=False,filename=None):
    groups = df.groupby('pass')
    colors = {True:'green',False:'red'}

    fig, ax = plt.subplots()
    ax.margins(0.05) # Optional, just adds 5% padding to the autoscaling
    for name, group in groups:
        ax.plot(group.int, group.frequency, c=colors[name], marker='o', linestyle='',label=name)
        
    ax.set_xlabel('Integer value')
    ax.set_ylabel('Frequency')
    ax.legend()
    if save:
        plt.savefig(f'{filename}.png')
        plt.close()
    else:
        plt.show()

def get_params(qudotfile):
    file = open(qudotfile,'r')
    r1, r2, r3, r4, N, k, x = [0,0,0,0,0,0,0]
    for line in file:
        line = line.replace('\n', '')
        if 'iload r1' in line:
            r1 = int(line.split(', ')[1])
        elif 'iload r2' in line:
            r2 = int(line.split(', ')[1])
        elif 'iload r3' in line:
            r3 = int(line.split(', ')[1])
        elif 'iload r4' in line:
            r4 = int(line.split(', ')[1])
        elif 'iload r5' in line:
            N = int(line.split(', ')[1])
        elif 'iload r6' in line:
            x = int(line.split(', ')[1])
        else:
            pass

    k = (r2-r1)+1
    l = (r4-r3)+1
    return (k,l,N,x)

def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def main():
    parser = argparse.ArgumentParser(description="Input your Shor Params and output file")
    parser.add_argument("-f", "--file", help="Choose shor.out file")#choices=FUNCTION_MAP.keys())
    parser.add_argument("-N", "--number", type=int, help="Prime number to factor")
    parser.add_argument("-x", "--seed", type=int, help="Random seed to use for factoring")
    parser.add_argument("-k", "--control", type=int, help="Size of control register")
    parser.add_argument("-l", "--multiplication", type=int, help="Size of multiplication register")
    #Optional
    parser.add_argument("-q", "--qudot", required=False, help=".QuDot file to read params from")
    parser.add_argument("-s", "--saveplot",type=str2bool,nargs='?',
                        const=True, required=False, help="True/False for saving plots")
    args = parser.parse_args()

    if args.qudot:
        qudotfile = args.qudot
        k,l,N,x = get_params(qudotfile)

    else:
        try:
            N,x,k,l = args.number, args.seed, args.control, args.multiplication
        except:
            raise('If you are not passing in a .QuDot file, you must pass in N,x,k,l!')

    data = out_to_df(args.file)
    plotname = args.file.split('.')[0]
    candidates = data['raw']
    print(f'Number of results: {len(candidates)}')
    result_df = classical_shor(candidates,N,x,k,l)
    print(result_df.sort_values(by=['frequency'],ascending=True))

    #For numbers 2291, 2573 in paper include the bottom two lines to remove outlier freqs
    #result_df = result_df.drop(result_df['frequency'].idxmax())
    #result_df = result_df.drop(result_df['frequency'].idxmax())
    if args.saveplot:
        plot_results(result_df,N,x,save=True,filename=plotname)
    else:
        plot_results(result_df,N,x)


if __name__ == "__main__":
    main()
