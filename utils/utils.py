import numpy as np
import pandas as pd
import scipy
from sklearn.model_selection import StratifiedShuffleSplit as SSS
from numba import jit

import sys;sys.path.append("..//DIFFI_master")
from interpretability_module import diffi_ib
#from utils.simulation_setup import MatFileDataset
from simulation_setup import MatFileDataset

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)


def make_rand_vector(df,dimensions):
    """
    Random unitary vector in the unit ball with max number of dimensions
    --------------------------------------------------------------------------------
    
    Parameters
    ----------
    df: Degrees of freedom

    dimensions: number of dimensions of the feature space

    If df<dimensions then dimensions-df indexes will be set to 0. 

    Returns
    ----------
    n:      random vector: the normal to the splitting hyperplane
        
    """
    if dimensions<df:
        raise ValueError("degree of freedom does not match with dataset dimensions")
    else:
        vec_ = np.random.normal(loc=0.0, scale=1.0, size=df)
        indexes = np.random.choice(range(dimensions),df,replace=False)
        vec = np.zeros(dimensions)
        vec[indexes] = vec_
        vec=vec/np.linalg.norm(vec)
    return vec



@jit(nopython=True) 
def c_factor(n):
    """
    Average path length of unsuccesful search in a binary search tree given n points
    --------------------------------------------------------------------------------
    
    Parameters
    ----------
    n :         int
        Number of data points for the BST.

    Returns
    -------
    float:      Average path length of unsuccesful search in a BST
        
    """
    return 2.0*(np.log(n-1)+0.5772156649) - (2.0*(n-1.)/(n*1.0))


def mean_confidence_interval_importances(l, confidence=0.95):
    """
    Mean value and confidence interval of a list of lists of results
    --------------------------------------------------------------------------------
    
    Parameters
    ----------
    l :         list
        list of lists of scores.

    Returns
    -------
    M:      list of tuples (m,m-h,m+h) where h is confidence interval
        
    """
    M=[]
    for i in range(l.shape[0]):
        a = 1.0 * np.array(l[i,:])
        n = len(a)
        m, se = np.mean(a), scipy.stats.sem(a)
        h = se * scipy.stats.t.ppf((1 + confidence) / 2., n-1)
        M.append((m, m-h, m+h))
    return M

def extract_order(X):
    X=X.sort_values(by=[0])
    X.reset_index(inplace=True)
    X.rename(columns={"index":"feature"},inplace=True)
    X.drop(labels=0,axis=1,inplace=True)
    X=X.squeeze()
    X.index=(X.index+1)*np.linspace(0,1,len(X))
    X=X.sort_values()
    return X.index

def cosine_ordered_similarity(v,u):
    v=np.exp((np.array(v)/np.array(v).max()))-1/(np.exp(1)-1)
    u=np.exp((np.array(u)/np.array(u).max()))-1/(np.exp(1)-1)
    S=1-(v).dot(u)/(np.sqrt(v.dot(v)*u.dot(u)))
    return S

        
def drop_duplicates(X,y):
    S=np.c_[X,y]
    S=pd.DataFrame(S).drop_duplicates().to_numpy()
    X,y = S[:,:-1], S[:,-1]
    return X,y

def dataset(name, path = "../data/"):
    try: 
        datapath = path + name + ".mat"
    except FileNotFoundError:
        datapath = path + name + ".csv"

    if datapath[-3:]=="mat":
        T=MatFileDataset() 
        T.load(datapath)
    elif datapath[-3:]=="csv":
        T=pd.DataFrame()
        T["X"]=pd.read_csv(datapath)
    else:
        raise Exception("Sorry, the path is not valid")
    
    X,y = drop_duplicates(T.X,T.y)
    print(name, "\n")
    print_dataset_resume(X,y)
    
    return X,y

def print_dataset_resume(X,y):
    n_sample=int(X.shape[0])
    perc_outliers=sum(y)/X.shape[0]
    size=int(X.shape[1])
    n_outliers=int(sum(y))
    print("[numero elementi = {}]\n[percentage outliers = {}]\n[number features = {}]\n[number outliers = {}]".format(n_sample,perc_outliers,size,n_outliers))

def downsample(X,y):
    if len(X)>2500:
        print("downsampled to 2500")
        sss = SSS(n_splits=1,test_size=1-2500/len(X))
        index = list(sss.split(X,y))[0][0]
        X,y = X[index,:],y[index]
        print(X.shape)
    return X,y

def partition_data(X,y):
    inliers=X[y==0,:]
    outliers=X[y==1,:]
    return inliers,outliers


def get_extended_test(n_pts,n_anomalies,cluster_distance,n_dim,anomalous_dim = [0]):
    #not_anomalous_dim     = np.setdiff1d(np.arange(n_dim),anomalous_dim)
    X1 = np.random.randn(n_pts,n_dim) + cluster_distance
    y1 = np.zeros(n_pts)
    #The first half of the additional anomalies are obtained subtracting 2*cluster_distance from the original points (X1)
    y1[:n_anomalies-int(n_anomalies/2)] = 1
    X1[:n_anomalies-int(n_anomalies/2),anomalous_dim] -= 2*cluster_distance
    #The second half of the additional anomalies are obtained adding 2*cluster_distance from the original points (X2)
    X2 = np.random.randn(n_pts,n_dim) - cluster_distance
    y2 = np.zeros(n_pts)
    y2[:int(n_anomalies/2)] = 1
    X2[:int(n_anomalies/2),anomalous_dim] += 2*cluster_distance
    #Concatenate together X1,X2 and y1,y2
    X = np.vstack([X1,X2])
    y = np.hstack([y1,y2])
    return X,y

        