"""Functions to generate infrastructure network plots and result plots."""

import networkx as nx
import pandas as pd
import wntr
import pandapower as pp
import pandapower.plotting as pandaplot
import matplotlib.pyplot as plt
import re
import seaborn as sns


# -----------------------------------------------------------#
#                      NETWORK PLOTS                        #
# -----------------------------------------------------------#


def plot_transpo_net(transpo_folder):
    """Generates the transportation network plot.

    :param transpo_folder: Location of the .tntp files.
    :type transpo_folder: string
    """
    links = pd.DataFrame(
        columns=[
            "Init node",
            "Term node",
            "Capacity",
            "Length",
            "Free Flow Time",
            "B",
            "Power",
            "Speed limit",
            "Toll",
            "Type",
        ]
    )
    with open("{}/example_net.tntp".format(transpo_folder), "r") as f:
        for line in f:
            if "~" in line:
                for line in f:
                    link_data = line.split("\t")[1:11]
                    links = links.append(
                        {
                            "Init node": link_data[0],
                            "Term node": link_data[1],
                            "Capacity": link_data[2],
                            "Length": link_data[3],
                            "Free Flow Time": link_data[4],
                            "B": link_data[5],
                            "Power": link_data[6],
                            "Speed limit": link_data[7],
                            "Toll": link_data[8],
                            "Type": link_data[9],
                        },
                        ignore_index=True,
                    )

    nodes = pd.read_csv("{}/example_node.tntp".format(transpo_folder), sep="\t")

    G = nx.Graph()
    edge_list = list(
        map(list, zip(links["Init node"].values, links["Term node"].values))
    )
    G.add_edges_from(edge_list)
    pos = {str(i + 1): (row[1], row[2]) for i, row in nodes.iterrows()}

    options = {
        "node_size": 500,
        "node_color": "lightsteelblue",
        "font_size": 14,
        "edge_color": "slategray",
        "width": 2,
    }
    plt.figure(1, figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, **options)


def plot_power_net(net):
    """Generates the power systems plot.

    :param net: The power systems network.
    :type net: pandapower network object
    """
    options = {
        "bus_size": 1.5,
        "plot_loads": True,
        "library": "networkx",
        "bus_color": "lightsteelblue",
        "show_plot": True,
        "scale_size": True,
    }
    plt.figure(1, figsize=(10, 7))
    pandaplot.simple_plot(net, **options)


def plot_water_net(wn):
    """Generates the water network plot.

    :param wn: The water network.
    :type wn: wntr network object
    """
    # wn = wntr.network.WaterNetworkModel(water_net)

    coord_list = list(wn.query_node_attribute("coordinates"))
    node_coords = [list(ele) for ele in coord_list]
    node_list = wn.node_name_list
    G = wn.get_graph()
    pos = {node_list[i]: element for i, element in enumerate(node_coords)}

    options = {
        "node_size": 500,
        "node_color": "lightsteelblue",
        "font_size": 14,
        "edge_color": "slategray",
        "width": 2,
    }
    plt.figure(1, figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, **options)
    # nodes, edges = wntr.graphics.plot_network(water_net, node_cmap='lightsteelblue', **options)


#############################################################
#                      RESULT PLOTS                        #
#############################################################


def plot_repair_curves(disrupt_recovery_object, scatter=False):
    """Generates the direct impact and repair level plots for the failed components.

    :param disrupt_recovery_object: The disrupt_generator.DisruptionAndRecovery object.
    :type disrupt_recovery_object: DisasterAndRecovery object
    :param scatter: scatter plot, defaults to False
    :type scatter: bool, optional
    """
    plt.figure(figsize=(10, 7))
    sns.set_style("white")
    sns.set_context("talk")
    sns.set_palette(sns.color_palette("Set1"))

    for name in disrupt_recovery_object.network.get_disrupted_components():
        time_tracker = (
            disrupt_recovery_object.event_table[
                disrupt_recovery_object.event_table.components == name
            ].time_stamp
            / 60
        )
        # print(time_tracker)
        damage_tracker = disrupt_recovery_object.event_table[
            disrupt_recovery_object.event_table.components == name
        ].perf_level
        # print(damage_tracker)

        sns.lineplot(
            x=time_tracker,
            y=damage_tracker,
            label=name,
            drawstyle="steps-post",
        )
        if scatter == True:
            sns.scatterplot(
                x=time_tracker,
                y=damage_tracker,
                alpha=0.5,
            )
    plt.xlabel("Time (minutes)")
    plt.xlim(0, 1.01 * (disrupt_recovery_object.event_table.time_stamp.max() / 60))
    plt.ylabel("Damage level (%)")
    plt.ylim(0, 102)
    plt.title("Disrupted components and their restoration")
    plt.legend(loc="best")
    plt.show()


def plot_interdependent_effects(
    power_consump_tracker, water_consump_tracker, time_tracker, scatter=True
):
    """Generates the network-level performance plots.

    :param power_consump_tracker: A list of power consumption resilience metric values.
    :type power_consump_tracker: list of floats
    :param water_consump_tracker: A list of water consumption resilience metric values.
    :type water_consump_tracker: list of floats
    :param time_tracker: A list of time-stamps from the similation.
    :type time_tracker: list of floats
    :param scatter: scatter plot, defaults to True
    :type scatter: bool, optional
    """
    sns.set_style("white")
    sns.set_context("talk")
    sns.set_palette(sns.color_palette("Set1"))

    plt.figure(figsize=(10, 7))
    plt.title("Network-wide effects and recovery")
    sns.lineplot(
        x=time_tracker,
        y=water_consump_tracker,
        label="Water",
    )
    sns.lineplot(
        x=time_tracker,
        y=power_consump_tracker,
        label="Power",
    )
    if scatter == True:
        sns.scatterplot(
            x=time_tracker,
            y=water_consump_tracker,
            alpha=0.5,
        )
        sns.scatterplot(
            x=time_tracker,
            y=power_consump_tracker,
            alpha=0.5,
        )
    plt.xlabel("Time (minutes)")
    plt.ylabel("Consumption ratio")
    plt.xlim(0, 1.01 * max(time_tracker))
    plt.ylim(-0.01, 1.05)
    plt.legend(loc="best")
    plt.show()
