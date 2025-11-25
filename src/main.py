import osmnx as ox
import pickle
import src.solver
import src.instance
from src.config import *


def main(filename, load=False):

    if load:
        G = ox.load_graphml('./results/instances/G_{0}.graphml'.format(filename))
        U = ox.load_graphml('./results/instances/U_{0}.graphml'.format(filename))
        with open('./results/instances/instance_{0}.pkl'.format(filename), 'rb') as file:
            instance = pickle.load(file)
            W, st_pairs, L, L_st, C, T = instance
    else:
        G, U = src.instance.graph()
        stops, stops_ref_to_node = src.instance.stops(U)
        W, st_pairs = src.instance.cover_and_st_pairs(U, stops=stops)
        L, L_st, C = src.instance.candidate_lines(G, U, W, st_pairs, stops_ref_to_node)
        T = src.instance.transfer_candidates(L)
        ox.save_graphml(G, './results/instances/G_{0}.graphml'.format(filename))
        ox.save_graphml(U, './results/instances/U_{0}.graphml'.format(filename))
        instance = (W, st_pairs, L, L_st, C, T)
        with open('./results/instances/instance_{0}.pkl'.format(filename), 'wb') as file:
            pickle.dump(instance, file)

    rho = {(s, t): max(G.nodes[s]['rho'], G.nodes[t]['rho']) for s, t in st_pairs}

    print('     Some statistics ... ')
    print('         - number of nodes: {0}'.format(len(W)))
    print('         - number of s-t pairs: {0}'.format(len(st_pairs)))
    print('         - number of headway options: {0}'.format(len(H)))
    print('         - number of candidate lines: {0}'.format(len(L)))
    print('         - number of transfer candidates: {0}'.format(len(T)))

    P_u, P_y = src.solver.service_plans(st_pairs, L, L_st, C, T, rho=rho)

    with open('./results/output/P_u_{0}.pkl'.format(filename), 'wb') as file:
        pickle.dump(P_u, file)
    with open('./results/output/P_y_{0}.pkl'.format(filename), 'wb') as file:
        pickle.dump(P_y, file)


if __name__ == '__main__':
    filename = 'ithaca'
    load = False
    main(filename, load=load)


# freq_C = {(s, t): 0 for s, t in st_pairs}
# for idx, (s, t) in enumerate(st_pairs):
#     print(idx)
#     for ell1, h1 in C:
#         if ell1 in L_st[(s, t)]:
#             freq_C[(s, t)] += 1/h1
#         else:
#             for ell2, h2 in C:
#                 if ell1 == ell2 or ell2 in L_st[(s, t)] or h1 > min(H) or h2 > min(H):
#                     continue
#                 if {s, t}.issubset(L[ell1]['coverage'].symmetric_difference(L[ell2]['coverage'])):
#                     freq_C[(s, t)] += 1 / min(H)


# import matplotlib.pyplot as plt
#
# values = sorted(freq_C.values())
# keys = range(len(freq_C))
#
#
# import plotly.graph_objects as go
#
# fig = go.Figure(data=[go.Bar(x=keys, y=values)])
# fig.update_layout(
#     title='Dictionary Values Sorted',
#     xaxis_title='Keys',
#     yaxis_title='Values'
# )
#
# fig.show()






