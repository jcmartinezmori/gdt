import networkx as nx
import gurobipy as gp
import time

import numpy as np

from src.config import *


def service_plans(rhos, st_pairs, C, L, L_st):

    t0 = time.time()

    m = gp.Model()
    m.ModelSense = gp.GRB.MAXIMIZE
    m.Params.MIPFocus = MIP_FOCUS
    m.Params.TimeLimit = TIME_LIMIT
    m.NumStart = 2

    print('     Started writing variables ... ')
    m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
    m._y, m._f, m._u = dict(), dict(), dict()
    for s, t in st_pairs:
        m._y[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='y')
        m._f[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / min(H), name='f')
        m._u[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / np.log2(min(H)), name='u')
    t1 = time.time()
    print('         ... done writing variables!')
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('     Started writing constraints ... ')
    print('         Started writing selection constraints ...')
    for ell in L.keys():
        lhs = gp.quicksum(m._x[(ell, h)] for h in H)
        rhs = 1
        m.addConstr(lhs <= rhs)
    t1 = time.time()
    print('             ... done writing selection constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing budget constraints ...')
    B_var = gp.quicksum(L[ell]['time'] / h * var for (ell, h), var in m._x.items())
    B_C = sum(C[ell]['time'] / C[ell]['headway'] for ell in C.keys()) * COST_FACTOR
    m.addConstr(B_var <= B_C)
    lhs = gp.quicksum(m._x.values())
    rhs = len(C) * SIZE_FACTOR
    m.addConstr(lhs <= rhs)
    t1 = time.time()
    print('             ... done writing budget constraint!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing level of service constraints ...')
    for (s, t), var in m._f.items():
        # lb = 0
        # for ell in L_st[(s, t)]:
        #     if ell in C_dict.keys():
        #         lb += 1 / C_dict[ell]
        # lb = min(1 / min(H), lb) * IC_FACTOR
        # m.addConstr(lb <= var)
        ub = 0
        for ell in L_st[(s, t)]:
            for h in H:
                ub += 1 / h * m._x[(ell, h)]
        m.addConstr(var <= ub)
        m.addConstr(m._y[(s, t)] <= 1 - 1 / max(H) + var)
    for (s, t), var in m._u.items():
        ub = 0
        for ell in L_st[(s, t)]:
            for h in H:
                ub += 1 / np.log2(h) * m._x[(ell, h)]
        m.addConstr(var <= ub)
    t1 = time.time()
    print('             ... done writing level of service constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         ... done writing constraints!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    # print('     Started writing first warm start ...')
    # m.params.StartNumber = 0
    # for (ell, h), var in m._x.items():
    #     if (ell, h) in C:
    #         var.Start = 1
    #     else:
    #         var.Start = 0
    # print('         ... done writing first warm start!')
    # t1 = time.time()
    # print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    ridership_obj = gp.quicksum(rhos[s] * rhos[t] * var for (s, t), var in m._u.items())
    coverage_obj = gp.quicksum(m._y.values())

    print('     Started optimizing ... ')

    cnstr = m.addConstr(B_var <= BUDGET_RATIO * B_C)
    m.setObjective(ridership_obj)
    m.optimize()
    rid = m.ObjVal

    m.remove(cnstr)
    cnstr = m.addConstr(B_var <= (1 - BUDGET_RATIO) * B_C)
    m.setObjective(coverage_obj)
    m.optimize()
    cov = m.ObjVal

    m.remove(cnstr)
    m.addConstr(ridership_obj >= rid)
    m.addConstr(coverage_obj >= cov)

    m.setObjective(ridership_obj)
    m.optimize()
    P_u = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    print('     Started writing second warm start ...')
    m.params.StartNumber = 1
    for (ell, h), var in m._x.items():
        if (ell, h) in P_u:
            var.Start = 1
        else:
            var.Start = 0
    print('         ... done writing second warm start!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    m.setObjective(coverage_obj)
    m.optimize()
    P_y = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    print('         ... done optimizing!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    return P_u, P_y

