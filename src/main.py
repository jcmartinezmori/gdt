import osmnx as ox
import pickle
import src.solver
import src.instance
from src.config import *


def main(filename, solver_params, load=False):

    instance_filename = filename
    solution_filename = filename + '_' + solver_params

    if load:
        G = ox.load_graphml('./results/instances/graph_{0}.graphml'.format(instance_filename))
        with open('./results/instances/instance_{0}.pkl'.format(instance_filename), 'rb') as file:
            instance = pickle.load(file)
            W, st_pairs, L, L_st, C, T, T_st = instance
    else:
        G, U = src.instance.graph()
        stops, stops_ref_to_node = src.instance.stops(U)
        W, st_pairs = src.instance.walk_cover_and_st_pairs(U, stops=stops)
        L, L_st, C = src.instance.candidate_lines(G, U, stops, stops_ref_to_node, W, st_pairs)
        T, T_st = src.instance.candidate_transfers(L, st_pairs)
        ox.save_graphml(G, './results/instances/graph_{0}.graphml'.format(instance_filename))
        instance = (W, st_pairs, L, L_st, C, T, T_st)
        with open('./results/instances/instance_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(instance, file)

    print('     Some statistics ... ')
    print('         - number of nodes: {0}'.format(len(W)))
    print('         - number of s-t pairs: {0}'.format(len(st_pairs)))
    print('         - number of headway options: {0}'.format(len(H)))
    print('         - number of candidate lines: {0}'.format(len(L)))
    print('         - number of transfer candidates: {0}'.format(len(T)))

    P_u, P_y = src.solver.service_plans(G, st_pairs, L, L_st, C, T, T_st)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'wb') as file:
        pickle.dump(P_u, file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'wb') as file:
        pickle.dump(P_y, file)


if __name__ == '__main__':

    filename = 'ITHACA'
    solver_params = 'LS-FACTOR-{0}'.format(LS_FACTOR)
    load = True
    main(filename, solver_params, load=load)


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
