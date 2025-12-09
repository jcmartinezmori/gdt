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
    m.NumStart = 2

    print('     Started writing variables ... ')
    m._x = m.addVars(((ell, h) for ell in L.keys() for h in H), vtype=gp.GRB.BINARY, name='x')
    m._y, m._u = dict(), dict()
    for s, t in st_pairs:
        m._y[(s, t)] = m.addVar(vtype=gp.GRB.BINARY, name='y')
        m._u[(s, t)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / min(H), name='u')
    m._t = m.addVars(((ell1, ell2) for ell1, ell2 in T.keys()), vtype=gp.GRB.CONTINUOUS, lb=0, ub=1 / min(H), name='t')
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

    print('         Started writing transfer constraints ...')
    for (ell1, ell2), var in m._t.items():
        m.addConstr(var <= gp.quicksum(1 / h * m._x[(ell1, h)] for h in H))
        m.addConstr(var <= gp.quicksum(1 / h * m._x[(ell2, h)] for h in H))
        m.addConstr(var <= 2 - gp.quicksum(m._x[(ell1, h)] + m._x[(ell2, h)] for h in H if h > TRANSFER_MIN_H))
    t1 = time.time()
    print('             ... done writing transfer constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing budget constraints ...')
    lhs = gp.quicksum(L[ell]['length'] / h * var for (ell, h), var in m._x.items())
    rhs = sum(L[ell]['length'] / h for ell, h in C) * COST_FACTOR
    m.addConstr(lhs <= rhs)
    lhs = gp.quicksum(m._x.values())
    rhs = len(C) * SIZE_FACTOR
    m.addConstr(lhs <= rhs)
    t1 = time.time()
    print('             ... done writing budget constraint!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         Started writing level of service constraints ...')
    C_dict = {ell: h for ell, h in C}
    for (s, t), var in m._u.items():
        lb = 0
        for ell in L_st[(s, t)]:
            if ell in C_dict.keys():
                lb += 1 / C_dict[ell]
        for ell1, ell2 in T_st[(s, t)]:
            if ell1 in C_dict.keys() and ell2 in C_dict.keys():
                if C_dict[ell1] <= TRANSFER_MIN_H or C_dict[ell2] <= TRANSFER_MIN_H:
                    lb += min(1 / C_dict[ell1], 1 / C_dict[ell2])
        lb = min(1 / min(H), lb) * IC_FACTOR
        ub = 0
        for ell in L_st[(s, t)]:
            for h in H:
                ub += 1 / h * m._x[(ell, h)]
        for ell1, ell2 in T_st[(s, t)]:
            ub += m._t[(ell1, ell2)]
        m.addConstr(lb <= var)
        m.addConstr(var <= ub)
        m.addConstr(var - 1 / max(H) <= m._y[(s, t)])
        m.addConstr(m._y[(s, t)] <= 1 - 1 / max(H) + var)
    t1 = time.time()
    print('             ... done writing level of service constraints!')
    print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    # print('         Started writing coverage (strengthening) constraints ...')
    # for (s, t), var in m._y.items():
    #     for ell in L_st[(s, t)]:
    #         for h in H:
    #             m.addConstr(m._x[(ell, h)] <= var)
    #     for ell1, ell2 in T_st[(s, t)]:
    #         m.addConstr(m._t[(ell1, ell2)] - 1 / max(H) <= var)
    # t1 = time.time()
    # print('             ... done writing coverage (strengthening) constraints!')
    # print('             ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('         ... done writing constraints!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    print('     Started writing first warm start ...')
    m.params.StartNumber = 0
    for (ell, h), var in m._x.items():
        if (ell, h) in C:
            var.Start = 1
        else:
            var.Start = 0
    print('         ... done writing first warm start!')
    t1 = time.time()
    print('         ... elapsed time: {0:.2f} sec'.format(t1 - t0))

    ridership_obj = gp.quicksum((int(G.nodes[s]['rho']) * int(G.nodes[t]['rho'])) * var for (s, t), var in m._u.items())
    coverage_obj = gp.quicksum(m._y.values())

    print('     Started optimizing ... ')

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
