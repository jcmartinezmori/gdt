import osmnx as ox
import pickle
import src.solver
import src.instance
from src.config import *


def main(solver_params, load=False):

    instance_filename = PLACE
    solution_filename = PLACE + '_' + solver_params

    if load:

        G, U, B, stop_nodes, W, st_pairs, dists, L, L_st, C, T, T_st = src.instance.load_instance(instance_filename)

    else:

        G, U, B = src.instance.get_graphs()
        ox.save_graphml(G, './results/instances/G_{0}.graphml'.format(instance_filename))
        ox.save_graphml(U, './results/instances/U_{0}.graphml'.format(instance_filename))
        ox.save_graphml(B, './results/instances/B_{0}.graphml'.format(instance_filename))

        stop_nodes = src.instance.get_stop_nodes(U)
        with open('./results/instances/stop_nodes_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(stop_nodes, file)

        rhos = src.instance.get_rhos(U, stop_nodes)
        with open('./results/instances/rhos{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(rhos, file)

        W, st_pairs, dists = src.instance.get_walk_cover_st_pairs_and_dists(U, rhos)
        with open('./results/instances/W_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(W, file)
        with open('./results/instances/st_pairs_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(st_pairs, file)
        with open('./results/instances/dists_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(dists, file)

        L, L_st, C = src.instance.get_candidate_lines(G, U, B, stop_nodes, W, st_pairs, dists)
        with open('./results/instances/L_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(L, file)
        with open('./results/instances/L_st_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(L_st, file)
        with open('./results/instances/C_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(C, file)

        T, T_st = src.instance.get_candidate_transfers(G, B, W, st_pairs, dists, L, L_st)
        with open('./results/instances/T_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(T, file)
        with open('./results/instances/T_st_{0}.pkl'.format(instance_filename), 'wb') as file:
            pickle.dump(T_st, file)

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

    solver_params = 'IC-FACTOR-{0}'.format(IC_FACTOR)
    load = False
    main(solver_params, load=load)
