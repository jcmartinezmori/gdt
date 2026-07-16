import osmnx as ox
import pickle
import src.solver
import src.instance
from src.config import *


def main(**kwargs):

    place = kwargs.get('place', PLACE)
    instance_load = kwargs.get('instance_load', True)

    if instance_load:

        # G, U, B, stop_nodes_dict, rhos, W, T, st_pairs, times, C, L, L_st = src.instance.load_full_instance(place)
        rhos, st_pairs, C, L, L_st = src.instance.load_solver_instance(place)

    else:

        # G, U, B = src.instance.get_graphs()
        # ox.save_graphml(G, './results/instances/G_{0}.graphml'.format(place))
        # ox.save_graphml(U, './results/instances/U_{0}.graphml'.format(place))
        # ox.save_graphml(B, './results/instances/B_{0}.graphml'.format(place))
        G = src.instance.__load_G(place)
        U = src.instance.__load_U(place)
        B = src.instance.__load_B(place)

        # stop_nodes_dict = src.instance.get_stop_nodes_dict(U)
        # with open('./results/instances/stop_nodes_dict_{0}.pkl'.format(place), 'wb') as file:
        #     pickle.dump(stop_nodes_dict, file)
        stop_nodes_dict = src.instance.__load_stop_nodes_dict(place)

        # rhos = src.instance.get_rhos(U, stop_nodes_dict)
        # with open('./results/instances/rhos_{0}.pkl'.format(place), 'wb') as file:
        #     pickle.dump(rhos, file)
        rhos = src.instance.__load_rhos(place)

        W, T, F = src.instance.get_W_T_F(stop_nodes_dict, rhos)
        with open('./results/instances/W_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(W, file)
        with open('./results/instances/T_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(T, file)
        with open('./results/instances/F_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(F, file)
        W, T, F = src.instance.__load_W_T_F(place)

        st_pairs, times = src.instance.get_st_pairs_times(G, U, W, T, F)
        with open('./results/instances/st_pairs_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(st_pairs, file)
        with open('./results/instances/times_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(times, file)
        # st_pairs = src.instance.__load_st_pairs(place)
        # times = src.instance.__load_times(place)

        C = src.instance.get_C(G, stop_nodes_dict, W)
        with open('./results/instances/C_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(C, file)
        # C = src.instance.__load_C(place)

        L, L_st = src.instance.get_L_L_st(G, B, W, st_pairs, times, C)
        with open('./results/instances/L_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(L, file)
        with open('./results/instances/L_st_{0}.pkl'.format(place), 'wb') as file:
            pickle.dump(L_st, file)
        # L, L_st = src.instance.__load_L_L_st(place)

    P_u, P_y = src.solver.service_plans(rhos, st_pairs, C, L, L_st, **kwargs)

    budget_factor = kwargs.get('budget_factor', BUDGET_FACTOR)
    ridership_factor = kwargs.get('ridership_factor', RIDERSHIP_FACTOR)
    solution_filename = place + '_' + 'BUDGET_FACTOR-{0}_RIDERSHIP_FACTOR-{1}'.format(budget_factor, ridership_factor)

    with open('./results/solutions/P_u_{0}.pkl'.format(solution_filename), 'wb') as file:
        pickle.dump(P_u, file)
    with open('./results/solutions/P_y_{0}.pkl'.format(solution_filename), 'wb') as file:
        pickle.dump(P_y, file)


if __name__ == '__main__':

    budget_factors = [0.8, 0.9, 1.0]
    ridership_factors = [0.5, 0.55, 0.6, 0.65, 0.7]
    # budget_factors = git st[1.0]
    # ridership_factors = [0.7]
    for budget_factor in budget_factors:
        for ridership_factor in ridership_factors:
            kwargs = {
                'instance_load': True,
                'model_load': True,
                'budget_factor': budget_factor,
                'ridership_factor': ridership_factor,
            }
            main(**kwargs)
