import networkx as nx
import gurobipy as gp
import time
from src.config import *


def cover(U, stops=None):

    m = gp.Model()
    m._x = m.addVars(U.nodes(), vtype=gp.GRB.BINARY, name='x')

    for s in U.nodes():
        if stops is not None:
            lengths = nx.single_source_dijkstra_path_length(U, s, weight='length', cutoff=COVER_DST_FACTOR * COVER_DST)
            if set(lengths.keys()).isdisjoint(stops):
                continue
        m.addConstr(gp.quicksum(m._x[t] for t in U.nodes[s]['coverage']) >= 1)
    if stops is not None:
        for stop in stops:
            m.addConstr(m._x[stop] == 1)

    obj = gp.quicksum(m._x.values())

    m.setObjective(obj)
    m.optimize()

    W = {s for s, var in m._x.items() if var.X > 0}

    return W


def service_plans(st_pairs, L, L_st, C, T, **kwargs):

    if 'rho' not in kwargs:
        rho = {(s, t): 1 for s, t in st_pairs}
    else:
        rho = kwargs['rho']

    t0 = time.time()

    m = gp.Model()
    m.ModelSense = gp.GRB.MAXIMIZE
    m.Params.MIPFocus = 3

    print('     Started writing variables ... ')
    m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
    m._y, m._u = dict(), dict()
    for s, t in st_pairs:
        m._y[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='y')
        m._u[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / min(H), name='u')
    m._z = m.addVars(((ell1, ell2) for ell1, ell2 in T.keys()), vtype=gp.GRB.BINARY, name='z')
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

    print('         Started writing budget constraint ...')
    lhs = gp.quicksum(L[ell]['length'] / h * var for (ell, h), var in m._x.items())
    rhs = sum(L[ell]['length'] * 1 / h for ell, h in C) * BDGT_FACTOR
    m.addConstr(lhs <= rhs)
    t1 = time.time()
    print('             ... done writing budget constraint!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing coverage constraints ...')
    for (s, t), var in m._y.items():
        rhs = 0
        for ell in L_st[(s, t)]:
            for h in H:
                rhs += m._x[(ell, h)]
        m.addConstr(var <= rhs)
    t1 = time.time()
    print('             ... done writing coverage constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing quality of service constraints ...')
    for (s, t), var in m._u.items():
        lb = min(sum(1 / h for ell, h in C if ell in L_st[(s, t)]), 1 / min(H)) * QS_FACTOR
        ub = 0
        for ell in L_st[(s, t)]:
            for h in H:
                ub += 1 / h * m._x[(ell, h)]
        m.addConstr(lb <= var)
        m.addConstr(var <= ub)
    t1 = time.time()
    print('             ... done writing quality of service constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing transfer constraints ...')
    for (ell1, ell2), var in m._z.items():
        m.addConstr(var <= m._x[(ell1, min(H))])
        m.addConstr(var <= m._x[(ell2, min(H))])
    t1 = time.time()
    print('             ... done writing transfer constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         ... done writing constraints!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('     Started writing warm start ...')
    for (ell, h), var in m._x.items():
        if (ell, h) in C:
            var.Start = 1
        else:
            var.Start = 0
    print('         ... done writing warm start!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    u_obj = gp.quicksum(rho[(s, t)] * var for (s, t), var in m._u.items())
    y_obj = gp.quicksum(m._y.values())
    z_obj = gp.quicksum(T[(ell1, ell2)] * var for (ell1, ell2), var in m._z.items())

    print('     Started optimizing ... ')

    m.setObjectiveN(u_obj, index=0, priority=3, reltol=REL_TOL)
    m.setObjectiveN(z_obj, index=1, priority=2, reltol=REL_TOL)
    m.setObjectiveN(y_obj, index=2, priority=1, reltol=REL_TOL)
    m.optimize()
    P_u = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    m.setObjectiveN(y_obj, index=0, priority=3, reltol=REL_TOL)
    m.setObjectiveN(u_obj, index=1, priority=2, reltol=REL_TOL)
    m.setObjectiveN(z_obj, index=2, priority=1, reltol=REL_TOL)
    m.optimize()
    P_y = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    print('         ... done optimizing!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    return P_u, P_y
