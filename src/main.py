import osmnx as ox
import pickle
import src.solver
import src.instance
from src.config import *


def main(solver_params, load=False):

    solution_filename = PLACE + '_' + solver_params

    if load:

        # G, U, B, stop_nodes_dict, rhos, W, T, st_pairs, times, C, L, L_st = src.instance.load_full_instance(PLACE)
        rhos, st_pairs, C, L, L_st = src.instance.load_solver_instance(PLACE)

    else:

        # G, U, B = src.instance.get_graphs()
        # ox.save_graphml(G, './results/instances/G_{0}.graphml'.format(PLACE))
        # ox.save_graphml(U, './results/instances/U_{0}.graphml'.format(PLACE))
        # ox.save_graphml(B, './results/instances/B_{0}.graphml'.format(PLACE))
        G = src.instance.__load_G(PLACE)
        U = src.instance.__load_U(PLACE)
        B = src.instance.__load_B(PLACE)

        # stop_nodes_dict = src.instance.get_stop_nodes_dict(U)
        # with open('./results/instances/stop_nodes_dict_{0}.pkl'.format(PLACE), 'wb') as file:
        #     pickle.dump(stop_nodes_dict, file)
        stop_nodes_dict = src.instance.__load_stop_nodes_dict(PLACE)

        # rhos = src.instance.get_rhos(U, stop_nodes_dict)
        # with open('./results/instances/rhos_{0}.pkl'.format(PLACE), 'wb') as file:
        #     pickle.dump(rhos, file)
        rhos = src.instance.__load_rhos(PLACE)

        # W, T = src.instance.get_W_T(stop_nodes_dict, rhos)
        # with open('./results/instances/W_{0}.pkl'.format(PLACE), 'wb') as file:
        #     pickle.dump(W, file)
        # with open('./results/instances/T_{0}.pkl'.format(PLACE), 'wb') as file:
        #     pickle.dump(T, file)
        W, T = src.instance.__load_W_T(PLACE)

        # st_pairs, times = src.instance.get_st_pairs_times(G, U, W, T)
        # with open('./results/instances/st_pairs_{0}.pkl'.format(PLACE), 'wb') as file:
        #     pickle.dump(st_pairs, file)
        # with open('./results/instances/times_{0}.pkl'.format(PLACE), 'wb') as file:
        #     pickle.dump(times, file)
        st_pairs = src.instance.__load_st_pairs(PLACE)
        times = src.instance.__load_times(PLACE)

        C = src.instance.get_C(G, stop_nodes_dict, W)
        with open('./results/instances/C_{0}.pkl'.format(PLACE), 'wb') as file:
            pickle.dump(C, file)
        # C = src.instance.__load_C(PLACE)

        L, L_st = src.instance.get_L_L_st(G, B, W, st_pairs, times, C)
        with open('./results/instances/L_{0}.pkl'.format(PLACE), 'wb') as file:
            pickle.dump(L, file)
        with open('./results/instances/L_st_{0}.pkl'.format(PLACE), 'wb') as file:
            pickle.dump(L_st, file)
        # L, L_st = src.instance.__load_L_L_st(PLACE)

        # T_st = src.instance.get_T_st(G, B, W, st_pairs, dists, L)
        # with open('./results/instances/T_st_{0}.pkl'.format(instance_filename), 'wb') as file:
        #     pickle.dump(T_st, file)

    P_u, P_y = src.solver.service_plans(rhos, st_pairs, C, L, L_st)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'wb') as file:
        pickle.dump(P_u, file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'wb') as file:
        pickle.dump(P_y, file)


if __name__ == '__main__':

    solver_params = 'IC-FACTOR-{0}'.format(IC_FACTOR)
    load = False
    main(solver_params, load=load)
