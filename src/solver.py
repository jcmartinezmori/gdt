import networkx as nx
import gurobipy as gp
import time
from src.config import *


def walk_cover(U, stop_nodes=None):

    m = gp.Model()
    m._x = m.addVars(U.nodes(), vtype=gp.GRB.BINARY, name='x')

    for s in U.nodes():
        if stop_nodes is not None:
            service_cover = nx.single_source_dijkstra_path_length(
                U, s, weight='length', cutoff=SERVICE_COVER_FACTOR * WALK_DIST
            )
            if set(service_cover.keys()).isdisjoint(stop_nodes.values()):
                continue
        m.addConstr(gp.quicksum(m._x[t] for t in U.nodes[s]['walk_cover']) >= 1)
    if stop_nodes is not None:
        for stop_node in stop_nodes.values():
            m.addConstr(m._x[stop_node] == 1)

    obj = gp.quicksum(m._x.values())

    m.setObjective(obj)
    m.optimize()

    W = {s for s, var in m._x.items() if var.X > 0}

    return W


def service_plans(G, st_pairs, L, L_st, C, T, T_st):

    t0 = time.time()

    m = gp.Model()
    m.ModelSense = gp.GRB.MAXIMIZE
    m.Params.MIPFocus = MIP_FOCUS
    m.Params.TimeLimit = TIME_LIMIT

    print('     Started writing variables ... ')
    m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
    m._y, m._z, m._u = dict(), dict(), dict()
    for s, t in st_pairs:
        m._y[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='y')
        m._z[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='z')
        m._u[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / min(H), name='u')
    m._t = m.addVars(((ell1, ell2) for ell1, ell2 in T.keys()), vtype=gp.GRB.BINARY, name='t')
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
    rhs = sum(L[ell]['length'] * 1 / h for ell, h in C) * BUDGET_FACTOR
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
        lb = min(sum(1 / h for ell, h in C if ell in L_st[(s, t)]), 1 / min(H)) * IC_FACTOR
        ub = 0
        for ell in L_st[(s, t)]:
            for h in H:
                ub += 1 / h * m._x[(ell, h)]
        m.addConstr(lb <= var)
        m.addConstr(var <= ub)
        m.addConstr(var <= m._y[(s, t)])
    t1 = time.time()
    print('             ... done writing quality of service constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing transfer constraints ...')
    for (s, t), var in m._z.items():
        m.addConstr(var <= 1 - m._y[(s, t)])
        m.addConstr(var <= gp.quicksum(m._t[(ell1, ell2)] for ell1, ell2 in T_st[(s, t)]))
    for (ell1, ell2), var in m._t.items():
        m.addConstr(var <= gp.quicksum(m._x[(ell1, h)] for h in H if h <= TRANSFER_MIN_H))
        m.addConstr(var <= gp.quicksum(m._x[(ell2, h)] for h in H if h <= TRANSFER_MIN_H))
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

    u_obj = gp.quicksum(max(G.nodes[s]['rho'], G.nodes[t]['rho']) * var for (s, t), var in m._u.items())
    y_obj = gp.quicksum(m._y.values())
    z_obj = gp.quicksum(m._z.values())

    print('     Started optimizing ... ')

    m.setObjective(u_obj)
    m.optimize()
    c_u = m.addConstr(u_obj >= (1 - REL_TOL) * m.ObjVal)
    m.setObjective(z_obj)
    m.optimize()
    c_z = m.addConstr(z_obj >= (1 - REL_TOL) * m.ObjVal)
    m.setObjective(y_obj)
    m.optimize()
    P_u = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    m.remove(c_u)
    m.remove(c_z)

    m.setObjective(y_obj)
    m.optimize()
    m.addConstr(y_obj >= (1 - REL_TOL) * m.ObjVal)
    m.setObjective(u_obj)
    m.optimize()
    m.addConstr(u_obj >= (1 - REL_TOL) * m.ObjVal)
    m.setObjective(z_obj)
    m.optimize()
    P_y = {(ell, h) for (ell, h), var in m._x.items() if var.X > 0}

    print('         ... done optimizing!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    return P_u, P_y
