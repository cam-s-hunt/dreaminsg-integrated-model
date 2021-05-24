import pandas as pd
from scipy import spatial

import dreaminsg_integrated_model.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.data.disruptive_scenarios.disrupt_generator_discrete as disrupt_generator

water_dict = water.get_water_dict()
power_dict = power.get_power_dict()

# -------------------------------------------------------------------------------------------------#
#                               DEPENDENCY TABLE CLASS AND METHODS                                 #
# -------------------------------------------------------------------------------------------------#
class DependencyTable:
    """A class to store information related to dependencies between power, water and transportation networks."""

    def __init__(self):
        """Initiates an empty dataframe to store node-to-node dependencies."""
        self.wp_table = pd.DataFrame(
            columns=["water_id", "power_id", "water_type", "power_type"]
        )
        self.access_table = pd.DataFrame(
            columns=[
                "origin_id",
                "transp_id",
                "origin_cat",
                "origin_type",
                "access_dist",
            ]
        )

    # Water-Power interdependencies
    def add_pump_motor_coupling(self, water_id, power_id):
        """Creates a pump-on-motor dependency entry in the dependency table.

        Arguments:
            water_id {string} -- The name of the pump in the water network model.
            power_id {string} -- The name of the motor in the power systems model.
        """
        self.wp_table = self.wp_table.append(
            {
                "water_id": water_id,
                "power_id": power_id,
                "water_type": "Pump",
                "power_type": "Motor",
            },
            ignore_index=True,
        )

    def add_gen_reserv_coupling(self, water_id, power_id):
        """Creates a generator-on-reservoir dependency entry in the dependency table.

        Arguments:
            water_id {string} -- The name of the reservoir in the water network model.
            power_id {string} -- The name of the generator in the power systems model.
        """
        self.wp_table = self.wp_table.append(
            {
                "water_id": water_id,
                "power_id": power_id,
                "water_type": "Reservoir",
                "power_type": "Generator",
            },
            ignore_index=True,
        )

    # Power-Transportation and  Interdependencies
    def add_transpo_access(self, integrated_graph):
        """Create a mapping to nearest road link from every water/power network component.

        Arguments:
            integrated_graph {networkx object} -- The integrated network as networkx object.
        """
        nodes_of_interest = [
            x
            for x, y in integrated_graph.nodes(data=True)
            if y["type"] == "power_node" or y["type"] == "water_node"
        ]
        for node in nodes_of_interest:
            name = "{}"
            (
                compon_infra,
                compon_notation,
                compon_code,
                compon_full,
            ) = get_compon_details(node)
            near_node, near_dist = get_nearest_node(
                integrated_graph, node, "transpo_node"
            )
            self.access_table = self.access_table.append(
                {
                    "origin_id": node,
                    "transp_id": near_node,
                    "origin_cat": compon_infra,
                    "origin_type": compon_full,
                    "access_dist": near_dist,
                },
                ignore_index=True,
            )

    def update_dependencies(self, pn, wn, time_stamp, next_time_stamp):
        """Updates the operational performance of all the dependent components in the integrated network.

        Arguments:
            pn {pandapower network object} -- The power systems model.
            wn {wntr network model} -- The water network model.
            time_stamp {float} -- The start time of the iteration.
            next_time_stamp {float} -- The end tiem of the iteration.
        """
        for index, row in self.wp_table.iterrows():
            if (row.water_type == "Pump") & (row.power_type == "Motor"):
                print(
                    "Motor operational status: ",
                    pn.motor[pn.motor.name == row.power_id].in_service.item(),
                )
                if pn.motor[pn.motor.name == row.power_id].in_service.item() == False:
                    pump = wn.get_link(row.water_id)
                    pump.add_outage(wn, time_stamp, next_time_stamp)
                    print(
                        f"Pump outage resulting from electrical motor failure is added between {time_stamp} s and {next_time_stamp} s"
                    )
                else:
                    pump = wn.get_link(row.water_id)
                    pump.status = 1


# -------------------------------------------------------------------------------------------------#
#                                   MISCELLANEOUS FUNCTIONS                                        #
# -------------------------------------------------------------------------------------------------#


def get_compon_details(compon_name):
    compon_infra, compon_id = compon_name.split("_")
    compon_type = ""
    for char in compon_id[0:2]:
        if char.isalpha():
            compon_type = "".join([compon_type, char])
    if compon_infra == "P":
        if compon_type in power_dict.keys():
            return (
                "power",
                compon_type,
                power_dict[compon_type]["code"],
                power_dict[compon_type]["name"],
            )
        else:
            print(
                "The naming convention suggests that {} belongs to power netwok. However, the element {} does not exist in the power component dictionary.".format(
                    compon_name, compon_type
                )
            )
    elif compon_name.split("_")[0] == "W":
        if compon_type in water_dict.keys():
            return (
                "water",
                compon_type,
                water_dict[compon_type]["code"],
                water_dict[compon_type]["name"],
            )
        else:
            print(
                "The naming convention suggests that {} belongs to water netwok. However, the element {} does not exist in the water component dictionary.".format(
                    compon_name, compon_type
                )
            )
    else:
        print(
            "Component does not belong to either water or power network. Please check the name."
        )


def get_nearest_node(integrated_graph, connected_node, target_type):
    """Finds the nearest node belonging to a specific family from a given node and the distance between the two.

    Arguments:
        integrated_graph {netwrokx integrated network object} --The integrated network in networkx format.
        origin_node {string/integer} -- Name of the node for which the nearest node has to be identified.
        target_type {string} -- The type of the target node (power_node, transpo_node, water_node)
    """
    curr_node_loc = integrated_graph.nodes[connected_node]["coord"]
    nodes_of_interest = [
        x for x, y in integrated_graph.nodes(data=True) if y["type"] == target_type
    ]
    coords_of_interest = [
        y["coord"]
        for x, y in integrated_graph.nodes(data=True)
        if y["type"] == target_type
    ]

    tree = spatial.KDTree(coords_of_interest)
    dist_nearest = tree.query([curr_node_loc])[0][0]
    nearest_node = nodes_of_interest[tree.query([curr_node_loc])[1][0]]

    return nearest_node, round(dist_nearest, 2)


def find_connected_power_node(origin_node, pn):
    """Finds the bus to which the given power systems component is connected to. For elements which are connected to two buses, the start bus is returned.

    Arguments:
        origin_node {string} -- Name of the power systems component.
        pn {pandapower network object} -- The power network the origin node belongs to.

    Returns:
        string -- Name of the connected bus.
    """
    origin_infra, origin_notation, origin_code, origin_full = get_compon_details(
        origin_node
    )

    near_node_field = power_dict[origin_notation]["connect_field"]
    bus_index = (
        pn[origin_code]
        .query('name == "{}"'.format(origin_node))[near_node_field]
        .item()
    )

    connected_bus = pn.bus.iloc[bus_index]["name"]
    return connected_bus


def find_connected_water_node(origin_node, wn):
    """Finds the water network node to which the water component is connected to.

    Arguments:
        origin_node {string} -- Name of the water network component.
        wn {wntr network object} -- The water distribution network the origin node belongs to

    Returns:
        string -- Name of the water network node.
    """
    origin_infra, origin_notation, origin_code, origin_full = get_compon_details(
        origin_node
    )
    near_node_field = water_dict[origin_notation]["connect_field"]
    connected_node = getattr(wn.get_link(origin_node), near_node_field)
    return connected_node
