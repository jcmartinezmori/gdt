import math
import pickle
import gurobipy as gp
import networkx as nx
import numpy as np
import time
from src.config import *
from pathlib import Path
from uuid import uuid4


def service_plans(rhos, st_pairs, C, L, L_st, **kwargs):

    model_load = kwargs.get('model_load', True)
    budget_factor = kwargs.get('budget_factor', BUDGET_FACTOR)
    ridership_factor = kwargs.get('ridership_factor', RIDERSHIP_FACTOR)

    t0 = time.time()

    if not model_load:

        m = gp.Model()
        m.ModelSense = gp.GRB.MAXIMIZE

        print('     Started writing variables ... ')
        m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
        m._y = m.addVars(st_pairs, vtype=gp.GRB.BINARY, name='y')
        m._f = m.addVars(st_pairs, vtype=gp.GRB.CONTINUOUS, lb=0, ub=gp.GRB.INFINITY, name='f')
        m._u = m.addVars(st_pairs, vtype=gp.GRB.CONTINUOUS, lb=0, ub=1/np.sqrt(min(H)), name='u')
        m._r = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=gp.GRB.INFINITY, name='r')
        m._c = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=gp.GRB.INFINITY, name='c')
        m._b = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=gp.GRB.INFINITY, name='b')
        t1 = time.time()
        print('         ... done writing variables!')
        print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

        print('     Started writing constraints ... ')
        print('         Started writing system performance constraints ...')
        m.addConstr(m._r == gp.quicksum(np.sqrt(rhos[s] * rhos[t]) * var for (s, t), var in m._u.items()))
        m.addConstr(m._c == gp.quicksum(m._y.values()))
        m.addConstr(m._b == gp.quicksum(L[ell]['time'] / h * var for (ell, h), var in m._x.items()))
        print('             ... done writing selection constraints!')
        print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

        print('         Started writing selection constraints ...')
        for ell in L.keys():
            lhs = gp.quicksum(m._x[(ell, h)] for h in H)
            rhs = 1
            m.addConstr(lhs <= rhs)
        t1 = time.time()
        print('             ... done writing selection constraints!')
        print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

        print('         Started writing level of service constraints ...')
        for (s, t), var in m._f.items():
            ub = 0
            for ell in L_st[(s, t)]:
                for h in H:
                    ub += 1 / h * m._x[(ell, h)]
            m.addConstr(var <= ub)
            m.addConstr(m._y[(s, t)] <= 1 - 1 / COVERAGE_H + var)
        for (s, t), var in m._u.items():
            # ub = 0
            # for ell in L_st[(s, t)]:
            #     for h in H:
            #         ub += 1 / np.sqrt(h) * m._x[(ell, h)]
            # m.addConstr(var <= ub)

            # m.addQConstr(var * var <= m._f[(s, t)])

            # m.addConstr(var <= m._f[(s, t)])

            # npts = 4
            # pts = [1/min(H) * (i / (npts - 1)) ** 2 for i in range(npts)]
            # vals = [np.sqrt(t) for t in pts]
            # m.addGenConstrPWL(m._f[(s, t)], var, pts, vals)

            # m.addConstr(var <= 9.486832980505*m._f[(s, t)] + 0.000000000000)
            # m.addConstr(var <= 3.162277660168*m._f[(s, t)] + 0.070272836893)
            # m.addConstr(var <= 1.897366596101*m._f[(s, t)] + 0.126491106407)

            m.addConstr(var <= 12.649110640673516 * m._f[(s, t)] + 0.000000000000000)
            m.addConstr(var <= 4.216370213557838 * m._f[(s, t)] + 0.052704627669473)
            m.addConstr(var <= 2.529822128134703 * m._f[(s, t)] + 0.094868329805051)
            m.addConstr(var <= 1.807015805810503 * m._f[(s, t)] + 0.135526185435788)

        t1 = time.time()
        print('             ... done writing level of service constraints!')
        print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

        print('         ... done writing constraints!')
        t1 = time.time()
        print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

        print('     Started storing model ...')
        x_idx = {key: var.index for key, var in m._x.items()}
        r_idx = m._r.index
        c_idx = m._c.index
        b_idx = m._b.index
        idx_data = (x_idx, r_idx, c_idx, b_idx)
        with open('./results/models/idx_data.pkl', 'wb') as file:
            pickle.dump(idx_data, file)
        m.write('./results/models/model.mps')
        print('         ... done storing model!')
        t1 = time.time()
        print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    else:

        print('     Started loading model ...')
        with open('./results/models/idx_data.pkl', 'rb') as file:
            idx_data = pickle.load(file)
        x_idx, r_idx, c_idx, b_idx = idx_data

        m = gp.read('./results/models/model.mps')
        m._vars = m.getVars()
        m._x = {key: m._vars[idx] for key, idx in x_idx.items()}
        m._r = m._vars[r_idx]
        m._c = m._vars[c_idx]
        m._b = m._vars[b_idx]

        print('         ... done loading model!')
        t1 = time.time()
        print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    m.Params.MIPFocus = kwargs.get('mip_focus', MIP_FOCUS)
    m.Params.TimeLimit = kwargs.get('time_limit', TIME_LIMIT)

    print('         Started writing budget constraints ...')
    budget_C = sum(C[ell]['time'] / C[ell]['h'] for ell in C.keys()) * budget_factor
    m.addConstr(m._b <= budget_C)
    t1 = time.time()
    print('             ... done writing budget constraint!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('     Started writing warm starts ...')
    for filename in Path('./results/warmstarts').glob("*.mst"):
        m.Params.StartNumber = -1
        m.read(str(filename))
        filename.unlink()
    t1 = time.time()
    print('         ... done writing warm starts!')
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('     Started optimizing ... ')
    cnstr = m.addConstr(m._b <= ridership_factor * budget_C)
    m.setObjective(m._r)
    m.optimize()
    m.write(f'./results/warmstarts/{uuid4().hex}.mst')
    ridership_obj_val = m.ObjVal
    m.remove(cnstr)

    cnstr = m.addConstr(m._b <= (1 - ridership_factor) * budget_C)
    m.setObjective(m._c)
    m.optimize()
    m.write(f'./results/warmstarts/{uuid4().hex}.mst')
    coverage_obj_val = m.ObjVal
    m.remove(cnstr)

    m.addConstr(m._r >= ridership_obj_val)
    m.addConstr(m._c >= coverage_obj_val)

    m.setObjective(m._r)
    m.optimize()
    P_u = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}
    m.write(f'./results/warmstarts/{uuid4().hex}.mst')

    m.setObjective(m._c)
    m.optimize()
    P_y = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}
    m.write(f'./results/warmstarts/{uuid4().hex}.mst')

    print('         ... done optimizing!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    return P_u, P_y

