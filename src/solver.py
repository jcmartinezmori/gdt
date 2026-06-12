import gurobipy as gp
import networkx as nx
import numpy as np
import time
from src.config import *


def service_plans(rhos, st_pairs, C, L, L_st):

    t0 = time.time()

    m = gp.Model()
    m.ModelSense = gp.GRB.MAXIMIZE
    m.Params.MIPFocus = MIP_FOCUS
    m.Params.TimeLimit = TIME_LIMIT
    m.NumStart = 1

    print('     Started writing variables ... ')
    m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
    m._y, m._f, m._u = dict(), dict(), dict()
    for s, t in st_pairs:
        m._y[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='y')
        m._f[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / min(H), name='f')
        m._u[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / np.sqrt(min(H)), name='u')
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
    budget_var = gp.quicksum(L[ell]['time'] / h * var for (ell, h), var in m._x.items())
    budget_C = sum(C[ell]['time'] / C[ell]['headway'] for ell in C.keys()) * COST_FACTOR
    m.addConstr(budget_var <= budget_C)
    t1 = time.time()
    print('             ... done writing budget constraint!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing level of service constraints ...')
    for (s, t), var in m._f.items():
        lb = 0
        for ell in L_st[(s, t)]:
            if ell in C.keys():
                lb += 1 / C[ell]['headway']
        lb = min(1 / min(H), lb) * IC_FACTOR
        m.addConstr(lb <= var)
        ub = 0
        for ell in L_st[(s, t)]:
            for h in H:
                ub += 1 / h * m._x[(ell, h)]
        m.addConstr(var <= ub)
        m.addConstr(m._y[(s, t)] <= 1 - 1 / COVERAGE_FREQ + var)
    for (s, t), var in m._u.items():
        ub = 0
        for ell in L_st[(s, t)]:
            for h in H:
                ub += 1 / np.sqrt(h) * m._x[(ell, h)]
        m.addConstr(var <= ub)
    t1 = time.time()
    print('             ... done writing level of service constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         ... done writing constraints!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('     Started writing warm start ...')
    m.params.StartNumber = 0
    for (ell, h), var in m._x.items():
        if ell in C.keys():
            if C[ell]['headway'] == h:
                var.Start = 1
            else:
                var.Start = 0
        else:
            var.Start = 0
    print('         ... done writing first warm start!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    ridership_obj = gp.quicksum(rhos[s] * rhos[t] * var for (s, t), var in m._u.items())
    coverage_obj = gp.quicksum(m._y.values())

    print('     Started optimizing ... ')

    m.setObjectiveN(ridership_obj, index=0, priority=2, reltol=OBJ_REL_TOL)
    m.setObjectiveN(coverage_obj, index=1, priority=1)
    m.optimize()
    P_u = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    m.setObjectiveN(coverage_obj, index=0, priority=2, reltol=OBJ_REL_TOL)
    m.setObjectiveN(ridership_obj, index=1, priority=1)
    m.optimize()
    P_y = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    print('         ... done optimizing!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    return P_u, P_y

