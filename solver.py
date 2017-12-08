import numpy as np
import copy
import random
import time

# requests[id-1] = [id, location id, first day, last day, number of days, tool type id, tool quantity]

def open_file(file_name):
    f = open(file_name, "r")
    for line in f.readlines():
        line = line.strip()
        if line.startswith("DATASET"):
            DATASET = line
        if line.startswith("NAME"):
            NAME = line
        if line.startswith("DAYS"):
            D = line.partition("=")
        if line.startswith("CAPACITY"):
            C = line.partition("=")
        if line.startswith("MAX_TRIP_DISTANCE"):
            MT = line.partition("=")
        if line.startswith("DEPOT_COORDINATE"):
            DC = line.partition("=")
        if line.startswith("VEHICLE_COST"):
            VC = line.partition("=")
        if line.startswith("VEHICLE_DAY_COST"):
            VDC = line.partition("=")
        if line.startswith("DISTANCE_COST"):
            DCO = line.partition("=")
        if line.startswith("TOOLS"):
            T = line.partition("=")
            with open(file_name) as fp:
                for i, line in enumerate(fp):
                    if line.startswith("TOOLS"):
                        tool_line = int(i)
        if line.startswith("COORDINATES"):
            COO = line.partition("=")
            with open(file_name) as fp:
                for i, line in enumerate(fp):
                    if line.startswith("COORDINATES"):
                        coordinates_line = int(i)
        if line.startswith("REQUESTS"):
            REQ = line.partition("=")
            with open(file_name) as fp:
                for i, line in enumerate(fp):
                    if line.startswith("REQUESTS"):
                        reqs_line = int(i)

    allrows_tools = []
    allrows_coords = []
    allrows_reqs = []
    with open(file_name, "r") as myfile:
        data = myfile.readlines()
        for i in data[tool_line + 1:tool_line + 1 + int(T[-1])]:  # create tools array
            words = i.split()
            numbers = [int(i) for i in words]
            allrows_tools.append(numbers)
        tools = np.array(allrows_tools)

        for i in data[coordinates_line + 1:coordinates_line + 1 + int(COO[-1])]:  # create coordinates array
            words = i.split()
            numbers = [int(i) for i in words]
            allrows_coords.append(numbers)
        coordinates = np.array(allrows_coords)

        for i in data[reqs_line + 1:reqs_line + 1 + int(REQ[-1])]:  # create requests array
            words = i.split()
            numbers = [int(i) for i in words]
            allrows_reqs.append(numbers)
        requests = np.array(allrows_reqs)

    DAYS = int(D[-1])
    capacity = int(C[-1])
    MAX_TRIP_DISTANCE = int(MT[-1])
    DEPOT_COORDINATE = int(DC[-1])
    VEHICLE_COST = int(VC[-1])
    VEHICLE_DAY_COST = int(VDC[-1])
    DISTANCE_COST = int(DCO[-1])
    NUM_OF_TOOL_TYPES = int(T[-1])

    return [tools, coordinates, requests, DATASET, NAME, DAYS, capacity, MAX_TRIP_DISTANCE, DEPOT_COORDINATE, VEHICLE_COST, VEHICLE_DAY_COST, DISTANCE_COST, NUM_OF_TOOL_TYPES]


class Request:  # assigned request
    def __init__(self, id0):
        self.id = id0  # depot
        self.available_sub = [0] * len(tools) # amount of tools available for sub tour, per tool type
        self.available_tour = [0] * len(tools) # these tools can be on the vehicle or in the depot, but belongs to this vehicle
        self.max_volume_after = 0
        self.max_volume_before = 0
        self.inv_from_depot_sub = [0] * len(tools)  # these are tools that are still on the vehicle arriving to this request
        self.inv_from_depot_tour = [0] * len(tools)  # from current to the end of the big tour
        self.volume = 0 # occupied volume arriving to this request
    def __repr__(self):
        return str(self.id)

class Tour: # mini tour
    def __init__(self):
        self.requests_assigned = [ Request(0),  Request(0) ]
    def __repr__(self):
        return str(self.requests_assigned)

class BigTour:
    def __init__(self):
        self.distance = 0
        self.small_tours = [] # this will be a list of Tours which is a list of small tours
    def __repr__(self):
        return str(self.small_tours)

class Day:
    def __init__(self):
        self.number_of_tours = 0  # this is number of big tours
        self.tours = []   # list of BigTours
        self.used = [0] * len(tools) # number of tools used in this day
    def __repr__(self):
        return str(self.tours)

#######################################################################
################### General functions ###################
#######################################################################
def total_solution_cost():
    # calculate the current solution cost which is stored in days
    # Output - [distance cost, tool utilization cost, tool extension cost, Total cost, vehicle day cost ,max vehicle utilization cost]

    dist, tot_v, cost = 0, 0, 0
    v = []
    for day in days:
        v.append(day.number_of_tours)
        tot_v += day.number_of_tours
        for tour in day.tours:
            dist += tour.distance

    # calculate fine for extension of tools
    extension, extended_days = calc_tools_extension()
    ext_cost = 0
    for day in extended_days:
        for tt in range(len(tools)):
            ext = extension[day][tt]
            ext_cost += ext * fine

    max_v = max(v)
    #tool_cost = 0
    #for i in range(len(max_tools_used)):
    #    print max_tools_used[i] , tools[i][3]
    #    tool_cost += np.int64( max_tools_used[i] * tools[i][3])
    #tool_cost = np.int64 (sum(np.multiply( max_tools_used , tools[:,3])))
    tool_cost = np.int64(sum( np.int64(max_tools_used) * np.int64( tools[:,3])))
    cost += tool_cost + dist * DISTANCE_COST + tot_v * VEHICLE_DAY_COST + max_v * VEHICLE_COST + ext_cost

    return dist * DISTANCE_COST, tool_cost, ext_cost, cost, tot_v * VEHICLE_DAY_COST , max_v * VEHICLE_COST

def calc_tools_extension():
    # used for total solution cost
    extension = []
    days_extended = []
    for d in range(len(days)):
        extension.append([0] * len(tools))
        for tt in range(len(tools)):
            extension[d][tt] = max(0, days[d].used[tt] - tools[tt][2])
        if max(extension[d]) > 0:
            days_extended.append(d)
    return extension, days_extended


def find_location_of_req(request_id):
    # Input - request_id (int, 1 based)
    # Output - list, all ints
    # request_id, delivery_day, delivery_tour, delivery_small_tour, delivery_position,
    # pickup_day, pickup_tour, pickup_small_tour, pickup_position

    request_id = np.absolute(request_id)
    r = requests[request_id-1]
    starting_day = r[2]-1
    last_day = r[3]-1
    for check_delivery_day in range(starting_day,last_day+1):
        for check_tour in days[check_delivery_day].tours:
            for check_small in check_tour.small_tours:
                for req in check_small.requests_assigned:
                    if req.id == request_id:
                        delivery_day = check_delivery_day
                        delivery_tour = days[delivery_day].tours.index(check_tour)
                        delivery_small_tour = check_tour.small_tours.index(check_small)
                        delivery_position = check_small.requests_assigned.index(req)
                        pickup_day = delivery_day + r[4]

                        for check_tour_p in days[pickup_day].tours:
                            for check_small_p in check_tour_p.small_tours:
                                for req_p in check_small_p.requests_assigned:
                                    if req_p.id == -request_id:
                                        pickup_tour = days[pickup_day].tours.index(check_tour_p)
                                        pickup_small_tour = check_tour_p.small_tours.index(check_small_p)
                                        pickup_position = check_small_p.requests_assigned.index(req_p)
                                        return request_id, delivery_day, delivery_tour, delivery_small_tour, delivery_position, pickup_day,pickup_tour,pickup_small_tour,pickup_position

def define_fine(DISTANCE_COST, VEHICLE_DAY_COST, VEHICLE_COST):
    fine = np.int64 (DISTANCE_COST + VEHICLE_DAY_COST + VEHICLE_COST)
    for i in range(len(tools)):
        fine += tools[i][3]
    #fine = fine*100
    return fine

def print_output(file_name):
    text_file = open(file_name, "w")
    text_file.write(str(DATASET) + "\n")
    text_file.write(str(NAME) + "\n")
    for d in days:
        text_file.write("DAY = " + str(days.index(d)+1) + "\n")
        text_file.write("NUMBER_OF_VEHICLES = " + str(d.number_of_tours) + "\n")
        for big_tour in d.tours:
            text_file.write(str(d.tours.index(big_tour)+1) + " R ")
            text_file.write("0 ")
            for tour in big_tour.small_tours:
                for request in tour.requests_assigned[1:]:
                    text_file.write(str(request) + " ")
            text_file.write("\n")
        text_file.write("\n")
    text_file.close()
    return


def print_output_best(file_name):
    text_file = open(file_name, "w")
    text_file.write(str(DATASET) + "\n")
    text_file.write(str(NAME) + "\n")
    for d in best_solution:
        text_file.write("DAY = " + str(best_solution.index(d)+1) + "\n")
        text_file.write("NUMBER_OF_VEHICLES = " + str(d.number_of_tours) + "\n")
        for big_tour in d.tours:
            text_file.write(str(d.tours.index(big_tour)+1) + " R ")
            text_file.write("0 ")
            for tour in big_tour.small_tours:
                for request in tour.requests_assigned[1:]:
                    text_file.write(str(request) + " ")
            text_file.write("\n")
        text_file.write("\n")
    text_file.close()
    return


#######################################################################
################### Distance Calculaation functions ###################
#######################################################################

def distance(r1, r2):
    # computes the distance between two requests.
    # Input - requests id's ( 1 based)
    # Output - distance (int)
    if r1 != 0:
        location_id_r1 = requests[np.absolute(r1)-1][1]
    else:
        location_id_r1 = 0
    if r2 != 0:
        location_id_r2 = requests[np.absolute(r2)-1][1]
    else:
        location_id_r2 = 0
    dis = ((coordinates[location_id_r1][1] - coordinates[location_id_r2][1]) ** 2 + (coordinates[location_id_r1][2] - coordinates[location_id_r2][2]) ** 2) ** 0.5
    return int(dis)

def distance_added(r1,r2,r3):
    # Receives 3 requests id's to insert the second between the first and third requests
    # Input - request id (1 based)
    # Output - delta distance performing the insertion
    return distance(r1, r2) + distance(r2, r3) - distance(r1, r3)

def distance_remove(r1,r2,r3):
    # Receives 3 requests id's - to remove the second between the first and third requests
    # Input - request id (1 based)
    # Output - delta distance performing the removal
    return distance(r1, r3) - distance(r1, r2) - distance(r2, r3)

#######################################################################
################### Removal checks functions      ###################
#######################################################################

def check_removal(day, Br, Sr, position):
    # Checks only vehicle capacity wise
    # day, Br, Sr, position - int, 0 based
    # Output - feasible - Boolean

    curr_small = days[day].tours[Br].small_tours[Sr]
    #curr_big = days[day].tours[Br]
    min_temp = [0] * NUM_OF_TOOL_TYPES
    inv_temp = [[0] * NUM_OF_TOOL_TYPES, [0] * NUM_OF_TOOL_TYPES]

    for r in curr_small.requests_assigned[1:-1]:
        if curr_small.requests_assigned.index(r) != position:
            request = requests[np.absolute(r.id)-1]
            temp_tt = request[5]-1
            tq_temp = request[6]
            new = copy.deepcopy(inv_temp[-1])
            inv_temp.append(new)
            if r.id > 0: #delivery
                inv_temp[-1][temp_tt] -= tq_temp
            else: #pickup
                inv_temp[-1][temp_tt] += tq_temp
            if inv_temp[-1][temp_tt] < min_temp[temp_tt]:
                min_temp[temp_tt] = inv_temp[-1][temp_tt]

    min_to_add = [0] * NUM_OF_TOOL_TYPES
    for t_t in range(NUM_OF_TOOL_TYPES):
        min_to_add[t_t] = max(-min_temp[t_t], 0)
    for r in inv_temp[1:]:
        for tt_temp in range(len(min_temp)):
            r[tt_temp] += min_to_add[tt_temp]

    volume = [0]
    for r in inv_temp[1:]:
        temp_volume = 0
        for tt_t in range(NUM_OF_TOOL_TYPES):
            temp_volume += r[tt_t] * tools[tt_t][1]
        volume.append(temp_volume)
        if temp_volume > capacity:
            return False
    return True

#######################################################################
################### Insertion checks functions      ###################
#######################################################################

def check_feasibility_insertion_delivery(request, day, Br, r, position):
    # check insertion of *request* to existing tour (before *position*)
    # Input -
    # request list - [id, location id, first day, last day, number of days, tool type id, tool quantity]
    # day, Br (Big tour), r (mini tour), position - type - int, 0-based.
    # Output -
    # Feasible - vehicle capacity wise - True / False.
    # cost - [distance cost, tools extension cost, tool utilization cost, 0,0]

    tt, tq = request[5]-1, request[6]
    cost = [0] * 5

    next_loc = days[day].tours[Br].small_tours[r].requests_assigned[position]
    prev_loc = days[day].tours[Br].small_tours[r].requests_assigned[position-1]
    dis = distance_added(np.absolute(prev_loc.id), request[0], np.absolute(next_loc.id))

    if days[day].tours[Br].distance + dis <= MAX_TRIP_DISTANCE:
        cost[0] += dis * DISTANCE_COST
        if tq > days[day].tours[Br].small_tours[r].requests_assigned[position].available_sub[tt]:  # D1
            add_inv = tq - days[day].tours[Br].small_tours[r].requests_assigned[position].available_sub[tt]
            if days[day].tours[Br].small_tours[r].requests_assigned[position].max_volume_before + (add_inv * tools[tt][1]) > capacity:
                return [False, [], float("inf"), 0]
        cost_extension, cost_tools,new_max_tools_tt = check_big_tour_delivery(request, day, Br, r, position)[1:] # calc tools and extension cost
        cost[2] += cost_extension
        cost[1] += cost_tools
        return [True, cost, dis, new_max_tools_tt]
    return [False, [], float("inf"), 0]


def check_big_tour_delivery(request, day, Br, r, position):
    # check big tour for insertion purpose, tool utilization wise.
    # The vehicle has the required tools, we need to check what cost they will have.
    # calc tool usage cost and tool extension
    # Input -
    # request list - [id, location id, first day, last day, number of days, tool type id, tool quantity]
    # day, Br (Big tour), r (mini tour), position - type - int, 0-based.
    # Output -
    # Feasible - tool extension wise
    # cost_extension, cost_tools = quantity * multiplier
    # new max used - to be used in case of *invitation* insertion

    tt, tq = request[5]-1, request[6]
    pickup_day = day + request[4]
    cost_extension, cost_tools = 0, 0
    feas = True

    # the days between delivery, pickup
    for check_day in days[day+1: pickup_day]:
        old_extension = max(check_day.used[tt]-tools[tt][2],0)
        if check_day.used[tt] + tq > tools[tt][2]:
            new_extension = check_day.used[tt] + tq - tools[tt][2]
            feas = False
            cost_extension += (new_extension - old_extension) * fine

    max_new_temp_used = max_tools_used[tt]
    for check_day in days[day+1: pickup_day]:
        new_temp_used = check_day.used[tt] + tq
        if max_new_temp_used < new_temp_used:
            max_new_temp_used = new_temp_used

    # Delivery day
    add_inv = 0
    if r == -1: # a new mini tour
        if tq > days[day].tours[Br].small_tours[r].requests_assigned[-1].available_tour[tt]:
            add_inv = tq - days[day].tours[Br].small_tours[r].requests_assigned[-1].available_tour[tt]
            max_new_temp_used = max(max_new_temp_used, days[day].used[tt] + add_inv)
    else: # existing mini tour
        if tq > days[day].tours[Br].small_tours[r].requests_assigned[position].available_tour[tt]:
            add_inv = tq - days[day].tours[Br].small_tours[r].requests_assigned[position].available_tour[tt]
            max_new_temp_used = max(max_new_temp_used, days[day].used[tt] + add_inv)

    old_extension_d_day = max(days[day].used[tt]-tools[tt][2],0)
    if add_inv > 0:
        if days[day].used[tt] + add_inv > tools[tt][2]: #extension
            new_extension_d_day = days[day].used[tt] + add_inv - tools[tt][2]
            feas = False
            cost_extension += (new_extension_d_day - old_extension_d_day) * fine
    cost_tools += (max_new_temp_used - max_tools_used[tt]) * tools[tt][3]
    return feas, cost_extension, cost_tools, max_new_temp_used


def check_big_tour_pickup(request, day, Br, r, position):
    # similar to check_big_tour_delivery, but checking only the pickup day

    feas = True
    tt, tq = request[5]-1, request[6]
    cost_extension, cost_tools = 0, 0
    curr_max = max_tools_used[tt]

    # find delta in tool usage
    add_inv_tour = max(tq - days[day].tours[Br].small_tours[r].requests_assigned[position].inv_from_depot_tour[tt],0)
    temp_used = []
    for temp_day in days:
        temp_used.append(temp_day.used[tt])
    temp_used[day] += add_inv_tour
    new_max_tool_used = max(temp_used)
    if new_max_tool_used > curr_max:
        cost_tools += (new_max_tool_used - max_tools_used[tt]) * tools[tt][3]

    # find delta in tool extension
    curr_used = days[day].used[tt] + add_inv_tour
    old_extension = max(0,days[day].used[tt]-tools[tt][2])
    if curr_used > tools[tt][2]:
        feas = False
        new_extension = curr_used - tools[tt][2]
        cost_extension += (new_extension - old_extension) * fine

    return [feas, cost_extension, cost_tools, new_max_tool_used]


def check_create_big_tour_delivery(request, day):
    # Calculate costs of insertion of  *request* (list) into a new tour in *day* (int)
    # calc vehicle cost, tool usage, tool extension
    # request list - [id, location id, first day, last day, number of days, tool type id, tool quantity]
    # Output - feas -tool extensionb wise, cost - list , new_max_tools_used - to be used in case of invitation

    tt = request[5]-1 #tool type id
    tq = request[6] #tool quantity
    pickup_day = day + request[4]
    cost = [0] * 5
    feas = True

    # extension cost for delivery day and the days between
    for check_day in days[day: pickup_day]:
        old_extension = max(0, check_day.used[tt]-tools[tt][2])
        if check_day.used[tt] + tq > tools[tt][2]:
            new_extension = check_day.used[tt] + tq - tools[tt][2]
            feas = False
            cost[2] += (new_extension - old_extension) * fine

    # tools cost
    new_max_tools_used = 0
    for check_day in days[day: pickup_day]:
        if new_max_tools_used < check_day.used[tt] + tq:
            new_max_tools_used = check_day.used[tt] + tq

    if new_max_tools_used > max_tools_used[tt]:
        cost[1] += (new_max_tools_used - max_tools_used[tt]) * tools[tt][3]

    cost[3] += VEHICLE_DAY_COST

    # vehicle cost
    max_vehicles_used = 0
    for i in days:
        max_vehicles_used = max(max_vehicles_used, i.number_of_tours)
    if max_vehicles_used < days[day].number_of_tours + 1:
        cost[4] += VEHICLE_COST

    return feas, cost,new_max_tools_used


def check_create_big_tour_pickup(request, day):
    # similar to check_create_big_tour_delivery

    tt = request[5]-1 #tool type id
    tq = request[6] #tool quantity
    pickup_day = day + request[4]
    cost = [0] * 5
    feas = True

    # vehicle cost
    cost[3] += VEHICLE_DAY_COST
    max_vehicles_used = 0
    for i in days:
        max_vehicles_used = max(max_vehicles_used, i.number_of_tours)
    if max_vehicles_used < days[day].number_of_tours + 1:
        cost[4] += VEHICLE_COST

    # extension cost
    old_extension = max(0,days[day].used[tt]-tools[tt][2])
    if days[day].used[tt] + tq > tools[tt][2]:
        new_extension = days[day].used[tt] + tq - tools[tt][2]
        feas = False
        cost[2] += (new_extension - old_extension) * fine

    # tool utilization cost
    temp_used = []
    for temp_day in days:
        temp_used.append(temp_day.used[tt])
    temp_used[day] += tq
    new_max_tool_used= max(temp_used)
    if new_max_tool_used > max_tools_used[tt]:
        cost[1] += (new_max_tool_used - max_tools_used[tt]) * tools[tt][3]

    return feas, cost, new_max_tool_used


def check_feasibility_insertion_pickup(request, day, Br, r, position):
    # similar to check_feasibility_insertion_delivery, but checking only pickup day
    tt, tq = request[5]-1, request[6] # tool type and tool quantity
    cost = [0] * 5  # distance, tools, penalty for extra tools  (vehicle costs are updated outside this function)

    next_loc = days[day].tours[Br].small_tours[r].requests_assigned[position]
    prev_loc = days[day].tours[Br].small_tours[r].requests_assigned[position-1]
    dis = distance_added(np.absolute(prev_loc.id), request[0], np.absolute(next_loc.id))

    if days[day].tours[Br].distance + dis > MAX_TRIP_DISTANCE:
        return [False, [], float("inf"), 0]

    cost[0] += dis * DISTANCE_COST

    # fesibility - vehicle capacity wise
    if tq > days[day].tours[Br].small_tours[r].requests_assigned[position].inv_from_depot_sub[tt]:  #P1
        add_inv_sub = tq - days[day].tours[Br].small_tours[r].requests_assigned[position].inv_from_depot_sub[tt]
        if days[day].tours[Br].small_tours[r].requests_assigned[position].max_volume_after + (add_inv_sub * tools[tt][1]) > capacity: #P2
            return [False, [], float("inf"), 0]

    # calculate tool cost
    curr_max = max_tools_used[tt]
    add_inv_tour = max(tq - days[day].tours[Br].small_tours[r].requests_assigned[position].inv_from_depot_tour[tt],0)
    curr_used = days[day].used[tt] + add_inv_tour
    temp_used = []
    for temp_day in days:
        temp_used.append(temp_day.used[tt])
    temp_used[day] += add_inv_tour
    new_max_tool_used = max(temp_used)
    if new_max_tool_used > curr_max:
        cost[1] += (new_max_tool_used - curr_max) * tools[tt][3]

    # calculate extension cost
    old_extension = max(0,days[day].used[tt]-tools[tt][2])
    if curr_used > tools[tt][2]:
        new_extension = curr_used - tools[tt][2]
        cost[2] += (new_extension - old_extension) * fine

    return [True, cost, dis, new_max_tool_used]


#######################################################################
################### Update solution functions ###################
#######################################################################

def remove_request(day,Br,Sr,position):
    # Remove request which is located at ** day, Br, Sr, position **
    # Input - day Br, Sr, position - int
    # Output - cost - list of delta in cost

    cost = [0] * 5
    needed_inv_update = True # True unless removing a big tour
    curr_small = days[day].tours[Br].small_tours[Sr]
    curr_big = days[day].tours[Br]

    id_removal = days[day].tours[Br].small_tours[Sr].requests_assigned[position].id
    id_before_removal = days[day].tours[Br].small_tours[Sr].requests_assigned[position-1].id
    id_after_removal = days[day].tours[Br].small_tours[Sr].requests_assigned[position+1].id

    delta_dis = distance_remove(id_before_removal, id_removal, id_after_removal)
    curr_big.distance += delta_dis
    cost[0] += delta_dis * DISTANCE_COST

    tt = requests[np.absolute(id_removal)-1][5]-1
    tq = requests[np.absolute(id_removal)-1][6]
    request_type = np.sign(id_removal)
    old_used_tour = copy.deepcopy(curr_big.small_tours[0].requests_assigned[1].inv_from_depot_tour[tt])
    if len(days[day].tours[Br].small_tours[Sr].requests_assigned) <= 3: # remove mini tour
        days[day].tours[Br].small_tours.pop(Sr)
        Sr = 0
        if len(days[day].tours[Br].small_tours) == 0: # remove big tour
            v_list = []
            for check_max_day in days:
                v_list.append(check_max_day.number_of_tours)
            old_max = copy.deepcopy(max(v_list))
            v_list[day] -= 1
            new_max = copy.deepcopy(max(v_list))

            if new_max < old_max:
                cost[4] -= VEHICLE_COST
            cost[3] -= VEHICLE_DAY_COST

            days[day].tours.pop(Br)
            days[day].number_of_tours -= 1
            needed_inv_update = False
    else:
        curr_small.requests_assigned.pop(position)

    if needed_inv_update is True:
        update_inv_variables(day, Br, Sr, tt) # this function updates all variables
        new_used_tour = copy.deepcopy(curr_big.small_tours[0].requests_assigned[1].inv_from_depot_tour[tt])
    else:
        new_used_tour = 0

    prev_today = copy.deepcopy(days[day].used[tt])

    if request_type > 0: # Delivery. Update of days between delivery-pickup needed
        days[day].used[tt] += new_used_tour - old_used_tour

        pickup_day = day + requests[np.absolute(id_removal)-1][4]
        for check_day in days[day+1:pickup_day]:
            old_extension_check_day = max(0, check_day.used[tt] - tools[tt][2])
            check_day.used[tt] -= tq
            new_extension_check_day = max(0, check_day.used[tt] - tools[tt][2])
            cost[2] += (new_extension_check_day - old_extension_check_day) * fine
    else: # pickup
        days[day].used[tt] += new_used_tour - old_used_tour - tq

    # change in extension
    old_extension = max(0, prev_today - tools[tt][2])
    new_extension = max(0, days[day].used[tt] - tools[tt][2])
    cost[2] += (new_extension - old_extension) * fine
    # change in tool utilization
    temp_used = []
    for temp_day in days:
        temp_used.append(temp_day.used[tt])
    new_max = max(temp_used)
    cost[1] += (new_max - max_tools_used[tt]) * tools[tt][3]
    max_tools_used[tt] = new_max

    return cost


def insert_request(day, Br, Sr, position, is_new_tour, is_new_sub, request_id, delta_dis, request_type):
    # Input -
    # day, Br, Sr, position - int, 0 based
    # is_new_tour, is_new_sub - Boolean
    # request_id - int, 1 based
    # delta_dis - int, was calculated in check insertion
    # request type - 1 (delivery) or -1 (pickup)
    # Output - None

    tt = requests[np.absolute(request_id)-1][5]-1
    tq = requests[np.absolute(request_id)-1][6]

    if is_new_tour is False and is_new_sub is True: # new small
        curr_big = days[day].tours[Br]
        old_used_tour = copy.deepcopy(curr_big.small_tours[0].requests_assigned[1].inv_from_depot_tour[tt])
        new_sub = Tour()
        if request_type > 0:
            days[day].tours[Br].small_tours.append(new_sub)
        else:
            days[day].tours[Br].small_tours.insert(Sr, new_sub)

    elif is_new_tour is True and is_new_sub is True: # new big
        new_big = BigTour()
        days[day].tours.append(new_big)
        new_sub = Tour()
        days[day].tours[Br].small_tours.append(new_sub)
        days[day].number_of_tours += 1
        curr_big = days[day].tours[Br]
        old_used_tour = 0
    else: # existing tour
        curr_big = days[day].tours[Br]
        old_used_tour = copy.deepcopy(curr_big.small_tours[0].requests_assigned[1].inv_from_depot_tour[tt])

    # From here we update all variables for all cases
    curr_small = days[day].tours[Br].small_tours[Sr]
    #curr_big = days[day].tours[Br]
    curr_big.distance += delta_dis
    curr_small.requests_assigned.insert(position, Request(request_type*request_id))
    update_inv_variables(day, Br, Sr, tt) # update all inv variables
    new_used_tour = copy.deepcopy(curr_big.small_tours[0].requests_assigned[1].inv_from_depot_tour[tt])

    if request_type > 0: # delivery
        days[day].used[tt] += new_used_tour - old_used_tour
        # update the days between
        for check_day in days[day+1: day + requests[np.absolute(request_id)-1][4]]:
            check_day.used[tt] += tq
            if max_tools_used[tt] < check_day.used[tt]:
                max_tools_used[tt] = check_day.used[tt]
    else: # pickup
        days[day].used[tt] += new_used_tour - old_used_tour + tq

    if max_tools_used[tt] < days[day].used[tt]:
        max_tools_used[tt] = days[day].used[tt]

    return


def update_inv_variables(day, Br, Sr, tt):
    # Update all inv lists after the request was already removed / inserted
    # Input - day, Br, Sr, tt (0 based) - int
    # Output - None

    curr_small = days[day].tours[Br].small_tours[Sr]
    curr_big = days[day].tours[Br]
    min_temp = [0] * NUM_OF_TOOL_TYPES
    inv_temp = [[0] * NUM_OF_TOOL_TYPES,[0] * NUM_OF_TOOL_TYPES]

    # calc temp inv list for the sub tour
    for r in curr_small.requests_assigned[1:-1]:
        request = requests[np.absolute(r.id)-1]  # the request record
        temp_tt = request[5]-1  # tool type (0 based)
        tq_temp = request[6]    # tool quantity
        new = copy.deepcopy(inv_temp[-1])
        inv_temp.append(new)
        if r.id > 0: #delivery
            inv_temp[-1][temp_tt] -= tq_temp
        else: #pickup
            inv_temp[-1][temp_tt] += tq_temp
        if inv_temp[-1][temp_tt] < min_temp[temp_tt]:
            min_temp[temp_tt] = inv_temp[-1][temp_tt]

    min_to_add = [0] * NUM_OF_TOOL_TYPES
    for t_t in range(NUM_OF_TOOL_TYPES):
        min_to_add[t_t] = max(-min_temp[t_t], 0)
    for r in inv_temp[1:]:
        for tt_temp in range(len(min_temp)):
            r[tt_temp] += min_to_add[tt_temp]
    # Update volume
    for r in range(len(curr_small.requests_assigned)):
        temp_volume = 0
        for tt_t in range(NUM_OF_TOOL_TYPES):
            temp_volume += inv_temp[r][tt_t] * tools[tt_t][1]
        curr_small.requests_assigned[r].volume = temp_volume
    # Update volume before
    temp_volume_before = 0
    for r in curr_small.requests_assigned:
        r.max_volume_before = temp_volume_before
        if r.volume > temp_volume_before:
            r.max_volume_before= r.volume
            temp_volume_before=r.max_volume_before
    # update max volume after
    for curr_req in range(len(curr_small.requests_assigned)):
        v_list = []
        for next_req in range(curr_req, len(curr_small.requests_assigned)):
            v_list.append(curr_small.requests_assigned[next_req].volume)
        curr_small.requests_assigned[curr_req].max_volume_after = max(v_list)

    #update available_sub (D1), start from the end and go backwords
    curr_small.requests_assigned[-1].available_sub[tt] = inv_temp[-1][tt]
    i = len(curr_small.requests_assigned)-2
    while curr_small.requests_assigned[i].id != 0:
        request = requests[np.absolute(curr_small.requests_assigned[i].id)-1]
        tt_temp = request[5]-1
        tq_temp = request[6]
        curr_small.requests_assigned[i].available_sub[tt] = curr_small.requests_assigned[i+1].available_sub[tt]
        if curr_small.requests_assigned[i].id  < 0 and tt_temp == tt:
            curr_small.requests_assigned[i].available_sub[tt] = max(0,curr_small.requests_assigned[i].available_sub[tt]-tq_temp)
        i -= 1

    #update inv_from_depot_sub (p1)
    pickup_inv = [0]*NUM_OF_TOOL_TYPES
    prev = inv_temp[1]
    curr_small.requests_assigned[1].inv_from_depot_sub = prev
    for r_index in range(1,len(curr_small.requests_assigned[1:])):
        r = curr_small.requests_assigned[r_index]
        r_next = curr_small.requests_assigned[r_index+1]
        request = requests[np.absolute(r.id)-1]
        tt_temp = request[5]-1
        tq_temp = request[6]
        r_next.inv_from_depot_sub = copy.deepcopy(prev)
        if r.id < 0:
            pickup_inv[tt_temp] += tq_temp
        else:
            if pickup_inv[tt_temp]-tq_temp > 0:
                pickup_inv[tt_temp] -= tq_temp
            else:
                delta = tq_temp - pickup_inv[tt_temp]
                r_next.inv_from_depot_sub[tt_temp] -= delta
                pickup_inv[tt_temp] = 0
        prev = r_next.inv_from_depot_sub

    #create temp list for D3
    tour_min_temp = [0]*NUM_OF_TOOL_TYPES
    tour_inv_temp = [[0]*NUM_OF_TOOL_TYPES]
    for small in curr_big.small_tours:
        for r in small.requests_assigned[1:]:
            request = requests[np.absolute(r.id)-1]
            prev = copy.deepcopy(tour_inv_temp[-1])
            tour_inv_temp.append(prev)
            tt_temp = request[5]-1
            tq_temp = request[6]
            if r.id > 0: #delivery
                tour_inv_temp[-1][tt_temp] -= tq_temp
            elif r.id < 0:
                tour_inv_temp[-1][tt_temp] += tq_temp #pickup
            if tour_inv_temp[-1][tt_temp] < tour_min_temp[tt_temp]:
                tour_min_temp[tt_temp] = tour_inv_temp[-1][tt_temp]
    for t in range(NUM_OF_TOOL_TYPES):
        tour_min_temp[t] = max(0,-tour_min_temp[t])

    for t in range(NUM_OF_TOOL_TYPES):
        for r in range(len(tour_inv_temp)):
            tour_inv_temp[r][t] += tour_min_temp[t]

    #update available_tour (D3)
    prev_min = tour_inv_temp[-1][tt]
    curr_big.small_tours[-1].requests_assigned[-1].available_tour[tt] = prev_min
    j = len(tour_inv_temp)-2 #was tour_min_temp- not a vector
    for small in reversed(curr_big.small_tours): #go back
        for r in reversed(small.requests_assigned[1:]):
            r.available_tour[tt] = prev_min
            if tour_inv_temp[j][tt] < prev_min:
                r.available_tour[tt] = tour_inv_temp[j][tt]
                prev_min = tour_inv_temp[j][tt]
            j -= 1

    #update P3 - inv_from_depot_tour
    pickup_inv = [0] * NUM_OF_TOOL_TYPES # available inv brought by pickup and not from depot
    prev = tour_inv_temp[0]
    for small_index in range(len(curr_big.small_tours)):
        curr_big.small_tours[small_index].requests_assigned[1].inv_from_depot_tour = copy.deepcopy(prev)
        for r_index in range(1,len(curr_big.small_tours[small_index].requests_assigned)-1):
            small = curr_big.small_tours[small_index]
            r= small.requests_assigned[r_index]
            r_next = small.requests_assigned[r_index+1]
            request = requests[np.absolute(r.id)-1]
            tt_temp = request[5]-1
            tq_temp = request[6]
            r_next.inv_from_depot_tour = copy.deepcopy(prev)
            if r.id < 0:
                pickup_inv[tt_temp] += tq_temp
            else:
                if pickup_inv[tt_temp]-tq_temp > 0:
                    pickup_inv[tt_temp] -= tq_temp
                else:
                    delta = tq_temp - pickup_inv[tt_temp]
                    r_next.inv_from_depot_tour[tt_temp] -= delta
                    pickup_inv[tt_temp] = 0
            prev = r_next.inv_from_depot_tour
        prev = r_next.inv_from_depot_tour

    return


#######################################################################
################### search heuristics functions      ###################
#######################################################################

def adaptive_search(m):
    # Input - time in seconds to run the function
    # Output - p - list of possibilities to chose method, elapsed - time run every system, improvement - per system, curr_cost - cost of current solution
    global days, tot_count, err_count , bad_count

    #import logging
    #logging.basicConfig(filename='solver.log',level=logging.INFO)


    best_cost = total_solution_cost()[3]
    curr_cost = copy.deepcopy(best_cost)
    best_solution = copy.deepcopy(days)
    num_of_methods = 12

    lamda = 0.3
    cost = [0] * num_of_methods
    improvement = [0] * num_of_methods
    elapsed = [0] * num_of_methods
    counter_tot = [0] * num_of_methods
    counter_improvment= [0] * num_of_methods
    k = 10 * num_of_methods
    p = [float(1) / num_of_methods] * num_of_methods
    bad_counter = 0
    max_bad_counter = len(requests) / 2

    timeout = time.time() + m
    timeout_best = timeout - 10
    max_it_time = 0
    while True:
        if time.time() > timeout_best:
            print_output_best(output_file)
        if time.time() > timeout:
            break
        selected = [0] * num_of_methods
        for k_k in range(k):
            random_p = random.randint(0, 100) / float(100)
            cum_sum = 0
            for i in range(len(p)):
                cum_sum += p[i]
                if random_p <= cum_sum:
                    #msg = 'iteration: ' + str(tot_count) + ' chose ' + str(i)
                    #logging.info(msg)
                    start = time.clock()
                    counter_tot[i] += 1
                    selected[i] += 1
                    if i==0 or i==2 or i==4:
                        d = random.randint(0, DAYS-1)
                        delta_cost = random_search(d, i+1)
                    elif i==1 or i==3 or i==5:
                        delta_cost, ids, total_cost_vector = random_reschedule(i)
                    elif i==6:
                        delta_cost = select_high_tools_used_day(3)[0]
                    elif i==7:
                        delta_cost = select_high_tools_used_day(5)[0]
                    elif i==8:
                        delta_cost = similarity_reschedule(3,0.5)[0]
                    elif i==9:
                        delta_cost = similarity_reschedule(3,0.5)[0]
                    elif i==10:
                        delta_cost = similarity_reschedule(5,1.5)[0]
                    elif i==11:
                        delta_cost = similarity_reschedule(5,1.5)[0]

                    temp_elapsed = time.clock()
                    temp_elapsed = temp_elapsed - start
                    elapsed[i] += temp_elapsed
                    max_it_time = max(max_it_time, temp_elapsed)

                    curr_cost += delta_cost
                    if delta_cost > 0: #noImprovment
                        bad_counter += 1

                    elif delta_cost < 0: # improvement
                        bad_counter = 0
                        counter_improvment[i] += 1
                        cost[i] = cost[i] - delta_cost
                        if curr_cost < best_cost:
                            best_solution = copy.deepcopy(days)
                            best_cost = curr_cost
                    break

            tot_count+=1
            #print 'iteration numer',tot_count, 'chose: ', i
            if bad_counter >= max_bad_counter: # go back to best solution
                bad_count +=1
                bad_counter = 0
                days = copy.deepcopy(best_solution)
                curr_cost = copy.deepcopy(best_cost)

        for i in range(len(p)):
            if selected[i] > 0:
                improvement[i] = float(cost[i]) / float(elapsed[i])

        unused_p = 0
        for i in range(len(p)):
            if selected[i] > 0:
                p[i] = lamda * p[i] + (1-lamda) * (improvement[i] / sum(improvement))
            else:
                unused_p += p[i]

        for i in range(len(p)):
            if selected[i]!=0:
                p[i] = p[i] * (1-unused_p)

    if curr_cost > best_cost:
        days = best_solution
    return p, elapsed, improvement,curr_cost


def mult_removal(n, d):
    # Remove *n* (int) random requests from day *d* (int, 0 based)
    # Output -ids - list of ids removed, delta_cost - the cost to remove n requests
    delta_cost = 0
    counter = 0
    ids = []
    tries = max( n * 10, len(requests)/100)
    while counter < n and tries > 0:
        if len(days[d].tours) > 2:
            v = random.randint(0, len(days[d].tours)-1)
        else:
            break
        t = random.randint(0, len(days[d].tours[v].small_tours)-1)
        p = random.randint(1, len(days[d].tours[v].small_tours[t].requests_assigned)-2)
        id = days[d].tours[v].small_tours[t].requests_assigned[p].id
        result = check_removal(d, v, t, p)
        if result is True:
            cost_list = np.int64(remove_request(d, v, t, p))
            cost = np.int64( sum(cost_list))
            counter += 1
            ids.append(id)
            delta_cost += cost
        tries -= 1

    return ids, delta_cost


def mult_insertion(ids, day):
    # insert *ids* into *day*
    # Greedy method
    # Input - ids - list, day - int
    # Output - insert cost - the delta cost of the solutiopn before and after the insertion (int)

    tot_insert_cost = 0
    for id in ids:
        request_type = np.sign(id)
        if int(id) > 0: # delivery
            del_cost, position, Br, Sr, is_new_tour, is_new_small, min_dis, cost_list, new_max_tools_tt = find_position(day, requests[id-1], 1)
        else: #pickup
            del_cost, position, Br, Sr, is_new_tour, is_new_small, min_dis, cost_list, new_max_tools_tt = find_position(day, requests[np.absolute(id)-1], -1)
        tot_insert_cost += np.int64(del_cost)
        insert_request(day, Br, Sr, position, is_new_tour, is_new_small, np.absolute(id), min_dis, np.sign(id))
    return tot_insert_cost


def random_search(d, n):
    # Remove n requests from day d, chose them randomly, greedy insertion
    # Input - d, n - int
    # Output - delta cost of removal and insertion
    ids, remove_cost = mult_removal(n, d)
    insert_cost = mult_insertion(ids, d)
    #result = remove_cost + insert_cost
    return remove_cost + insert_cost


def random_reschedule(n):
    #chose n *invitations* randomly, remove and insert to the best position one by one
    # Input - n (int)
    # Output - total_cost (delta cost, int), ids (list), total_cost_vector (list)

    counter, total_cost = 0, 0
    #total_cost = 0
    ids = []
    tries = max( n * 10, len(requests)/100)
    while counter < n and tries > 0:
        id = random.randint(1, len(requests))
        if id not in ids:
            day_d,Br_d,Sr_d,position_d ,day_p,Br_p,Sr_p,position_p = find_location_of_req(id)[1:]
            result_d = check_removal(day_d,Br_d,Sr_d,position_d)
            result_p = check_removal(day_p,Br_p,Sr_p,position_p)
            if result_d is True and result_p is True:
                ids.append(id)
                counter += 1
        tries -= 1
    [total_cost, ids, total_cost_vector] = reschedule_full_request(ids)
    return total_cost, ids, total_cost_vector


def reschedule_full_request(ids):
    ''' remove invitations **ids** and insert to the best position'''
    # Output - total_cost (delta cost, int), ids (list), total_cost_vector (list)

    total_cost = 0
    total_cost_vector = [0] * 5
    for request_id in ids:
        day_d,Br_d,Sr_d,position_d ,day_p,Br_p,Sr_p,position_p = find_location_of_req(request_id)[1:]
        result_d = check_removal(day_d,Br_d,Sr_d,position_d)
        result_p = check_removal(day_p,Br_p,Sr_p,position_p)
        if result_d is False or result_p is False:
            ids.remove(request_id)
        else:
            day_d,Br_d,Sr_d,position_d ,day_p,Br_p,Sr_p,position_p = find_location_of_req(request_id)[1:]
            remove_cost_d_list = np.int64(remove_request(day_d,Br_d,Sr_d,position_d))
            remove_cost_d = np.int64( sum(remove_cost_d_list))

            remove_cost_p_list = np.int64( remove_request(day_p,Br_p,Sr_p,position_p))
            remove_cost_p = np.int64( sum(remove_cost_p_list))

        total_cost += remove_cost_d + remove_cost_p
        insert_total_cost = float("inf")
        r = requests[request_id-1]
        starting_day = r[2]-1
        last_day = r[3]-1
        tt = r[5]-1

        #d = optimal_schedule[request_id-1]
        for delivery_day in range(starting_day,last_day+1):
            pickup_day = delivery_day + r[4]
            [cost_d, min_loc_d, min_tour_d, min_small_d, is_new_tour_d, is_new_small_d, min_dis_d, cost_list_d, max_new_tools_used_tt_d] = find_position(delivery_day, r, 1)
            [cost_p, min_loc_p, min_tour_p, min_small_p, is_new_tour_p, is_new_small_p, min_dis_p, cost_list_p, max_new_tools_used_tt_p] = find_position(pickup_day, r, -1)

            delta_cost_vector = np.int64( [0] * len(cost_list_d))
            for i in range(len(cost_list_d)):
                delta_cost_vector[i] = np.int64(cost_list_d[i] + cost_list_p[i])
            delta_cost_vector[1] = np.int64(max((max(max_new_tools_used_tt_d, max_new_tools_used_tt_p) - max_tools_used[tt]),0) * tools[tt][3])
            cost = np.int64( sum(delta_cost_vector))

            if cost < insert_total_cost :
                best_delivery_day = delivery_day
                best_loc_d = min_loc_d
                best_tour_d = min_tour_d
                best_small_d = min_small_d
                best_is_new_tour_d = is_new_tour_d
                best_is_new_small_d = is_new_small_d
                best_dis_d = min_dis_d

                best_pickup_day = pickup_day
                best_loc_p = min_loc_p
                best_tour_p = min_tour_p
                best_small_p = min_small_p
                best_is_new_tour_p = is_new_tour_p
                best_is_new_small_p = is_new_small_p
                best_dis_p = min_dis_p

                insert_total_cost = copy.deepcopy(cost)
                insert_total_cost_vector = copy.deepcopy(delta_cost_vector)

        insert_request(best_delivery_day, best_tour_d, best_small_d, best_loc_d, best_is_new_tour_d, best_is_new_small_d, request_id, best_dis_d, 1)
        insert_request(best_pickup_day, best_tour_p, best_small_p, best_loc_p, best_is_new_tour_p, best_is_new_small_p, request_id, best_dis_p, -1)

        total_cost += insert_total_cost

        for i in range(len(insert_total_cost_vector)):
            total_cost_vector[i] += insert_total_cost_vector[i]

    return [total_cost, ids, total_cost_vector]


def similarity_reschedule(n,B):
    # reschedule n similar invitations
    #days_weight = -1
    dis_weight = B
    tries = max( n * 10, len(requests)/100)
    while tries > 0:
        id_req = random.randint(1, len(requests))
        day_d,Br_d,Sr_d,position_d ,day_p,Br_p,Sr_p,position_p = find_location_of_req(id_req)[1:]
        result_d = check_removal(day_d,Br_d,Sr_d,position_d)
        result_p = check_removal(day_p,Br_p,Sr_p,position_p)
        if result_d is True and result_p is True:
            break
        tries -= 1
    if tries == 0:
        return 0, [], [0] * 5

    tt = requests[id_req-1][5]
    starting_day_d = requests[id_req-1][2]-1
    last_day_d = requests[id_req-1][3]-1
    #q = requests[id_req-1][6]
    starting_day_p = starting_day_d + requests[id_req-1][4]
    last_day_p = starting_day_p + requests[id_req-1][4]
    #number_days = requests[id_req-1][4]
    coordinates_id = requests[id_req-1][1]

    similarity = []
    for req in requests:
        temp_id = req[0]
        if id_req != temp_id and req[1] != coordinates_id:
            temp_starting_day_d, temp_last_day_d = req[2]-1, req[3]-1
            #temp_q = req[6]
            temp_starting_day_p, temp_last_day_p = temp_starting_day_d + req[4], temp_last_day_d + req[4]
            #temp_number_days = req[4]
            num_of_days_overlapping = 0
            temp_tt = req[5]-1

            num_of_days_overlapping += (max(0,(min(last_day_d,temp_last_day_d)-max(starting_day_d,temp_starting_day_d)+1)) +
            max(0,min(temp_last_day_p,last_day_p)-max(starting_day_p, temp_starting_day_p)+1) +
            max(0,min(last_day_d,temp_last_day_p)-max(starting_day_d,temp_starting_day_p)+1) +
            max(0,min(last_day_p,temp_last_day_d)-max(starting_day_p,temp_starting_day_d)+1))

            tool_weight = 1
            if tt == temp_tt:
                tool_weight = 0.5

            if num_of_days_overlapping != 0:
                temp_similarity = (1/(num_of_days_overlapping))* ((float(distance(id_req, temp_id))/MAX_TRIP_DISTANCE)**dis_weight)*tool_weight
            else:
                temp_similarity = float("inf")
            similarity.append(temp_similarity)
        else:
            similarity.append(float("inf"))

    counter = 0
    ids = []
    second_tries = n
    while counter < n-1 and second_tries > 0:
        temp_min = int(sorted(range(len(similarity)),key=lambda i: similarity[i])[:][0]) + 1
        day_d,Br_d,Sr_d,position_d ,day_p,Br_p,Sr_p,position_p = find_location_of_req(temp_min)[1:]
        result_d = check_removal(day_d,Br_d,Sr_d,position_d)
        result_p = check_removal(day_p,Br_p,Sr_p,position_p)
        if result_d is True and result_p is True:
            ids.append(temp_min)
            counter += 1
        similarity[temp_min-1] = float("inf")
        second_tries -= 1

    ids.insert(0, id_req)
    [total_cost, ids, total_cost_vector] = reschedule_full_request(ids)

    return total_cost, ids, total_cost_vector


def select_high_tools_used_day(n):
    # remove n invitations from the day with the highest tool utilization cost
    # Output - [total_cost - int, ids - list, total_cost_vector - list of tool types]

    temp_cost = np.array(tools)[:,3] * max_tools_used
    tt = int(sorted(range(len(temp_cost)),key=lambda i: temp_cost[i])[-1:][0])
    d = -1
    max_used = 0
    for day in days:
        if day.used > max_used:
            max_used = day.used
            d = days.index(day)

    counter = 0
    ids = []
    tries = max( n * 10, len(requests)/100)
    while counter < n and tries > 0:
        v = random.randint(0, len(days[d].tours)-1)
        t = random.randint(0, len(days[d].tours[v].small_tours)-1)
        p = random.randint(1, len(days[d].tours[v].small_tours[t].requests_assigned)-2)
        id = days[d].tours[v].small_tours[t].requests_assigned[p].id
        if id not in ids:
            day_d,Br_d,Sr_d,position_d ,day_p,Br_p,Sr_p,position_p = find_location_of_req(id)[1:]
            result_d = check_removal(day_d,Br_d,Sr_d,position_d)
            result_p = check_removal(day_p,Br_p,Sr_p,position_p)
            if result_d is True and result_p is True:
                ids.append(np.absolute(id))
                counter += 1
        tries -= 1

    [total_cost, ids, total_cost_vector] = reschedule_full_request(ids)
    return [total_cost, ids, total_cost_vector]



#######################################################################
################### Initial Solution ###################
#######################################################################

def find_position(day, request, type):
    # Check all positions to insert *request* (list) to day (int) of type(+/-1), greedy insertion
    # Output -
    # minimum - insertion cost (delta) in the location it is minimal
    # min_loc, min_tour, min_small - int
    # is_new_tour, is_new_small - Boolean
    # min_dis - delta distance, int
    # cost_list - insertion cost
    # min_new_max_tools_tt - the max utilization of tt after the insertion (could be the same as prior to the insertoion)

    minimum = float("inf")
    is_new_tour, is_new_small = False, False

    for tour in days[day].tours:
        Br = days[day].tours.index(tour)
        for small in tour.small_tours:
            Sr = tour.small_tours.index(small)
            for loc in small.requests_assigned[1:]: # insert before loc
                index_loc = small.requests_assigned.index(loc)
                if type == 1: # Delivery
                    [is_feasible, cost, dis, new_max_tools_tt] = check_feasibility_insertion_delivery(request, day, Br, Sr, index_loc)
                elif type == -1: # Pickup
                    is_feasible, cost, dis, new_max_tools_tt = check_feasibility_insertion_pickup(request, day, Br, Sr, index_loc)
                cost = np.int64(cost)
                if is_feasible is True and np.int64(sum(cost)) < minimum:
                    minimum = np.int64(sum(cost))
                    cost_list = copy.deepcopy(cost)
                    min_loc, min_tour, min_small = index_loc, Br, Sr
                    min_day = day
                    min_dis = copy.deepcopy(dis)
                    min_new_max_tools_tt = new_max_tools_tt
                    is_new_small, is_new_tour = False, False

        # new mini tour
        dis = distance_added(0, np.absolute(request[0]), 0)
        if tour.distance + dis <= MAX_TRIP_DISTANCE:
            if type > 0: # Delivery
                Sr = -1
                [is_feasible, cost_extension, cost_tools,new_max_tools_tt] = check_big_tour_delivery(request, day, Br, Sr, 1)
            else: # Pickup
                Sr = 0
                [is_feasible, cost_extension, cost_tools,new_max_tools_tt] = check_big_tour_pickup(request, day, Br, Sr, 1)
            cost = [0] * 5
            cost[0] += np.int64( dis * DISTANCE_COST)
            cost[1] += np.int64( cost_tools)
            cost[2] += np.int64(cost_extension)

            if np.int64(sum(cost)) < minimum:
                min_new_max_tools_tt=new_max_tools_tt
                minimum = np.int64(sum(cost))
                cost_list = copy.deepcopy(cost)
                min_loc, min_tour, min_small = 1, Br, Sr
                min_day = day
                min_dis = dis
                is_new_small, is_new_tour = True, False
    # new big tour
    if minimum == float("inf"):
        dis = distance_added(0, request[0], 0)
        if type > 0: # Delivery
            [is_feasible, cost,new_max_tools_tt] = check_create_big_tour_delivery(request, day)
        else: # Pickup
            [is_feasible, cost,new_max_tools_tt] = check_create_big_tour_pickup(request, day)
        minimum = np.int64 (sum(cost)) + np.int64(dis * DISTANCE_COST )
        cost_list = copy.deepcopy(cost)
        cost_list[0] += np.int64(dis * DISTANCE_COST )
        min_loc, min_tour, min_small = 1, -1, 0
        min_day = day
        min_dis = dis
        min_new_max_tools_tt = new_max_tools_tt
        is_new_tour, is_new_small = True, True

    return minimum, min_loc, min_tour, min_small, is_new_tour, is_new_small, min_dis, cost_list,min_new_max_tools_tt

def schedule_requests():
    # Insert all request in the instance. Greedy insertion
    for r in requests:
        insert_total_cost = float("inf")
        request_id, starting_day, last_day, quantity,tt = r[0], r[2]-1, r[3]-1, r[6], r[5]-1

        for delivery_day in range(starting_day, last_day+1):
            pickup_day = delivery_day + r[4]
            [cost_d, min_loc_d, min_tour_d, min_small_d, is_new_tour_d, is_new_small_d, min_dis_d, cost_list_d,max_new_tools_used_tt_d] = find_position(delivery_day, r, 1)
            [cost_p, min_loc_p, min_tour_p, min_small_p, is_new_tour_p, is_new_small_p, min_dis_p, cost_list_p,max_new_tools_used_tt_p] = find_position(pickup_day, r, -1)

            cost = np.int64( cost_d + cost_p - cost_list_d[1] - cost_list_p[1] + (max(max_new_tools_used_tt_d, max_new_tools_used_tt_p) - max_tools_used[tt]) * tools[tt][3] )
            if cost < insert_total_cost:
                insert_temp_list = [request_id,np.int64(cost_d + cost_p),delivery_day,pickup_day,np.int64(cost_d), min_loc_d, min_tour_d, min_small_d, is_new_tour_d, is_new_small_d, min_dis_d,np.int64(cost_p), min_loc_p, min_tour_p, min_small_p, is_new_tour_p, is_new_small_p, min_dis_p]
                insert_total_cost = np.int64(cost_d + cost_p)
        insert_request(insert_temp_list[2], insert_temp_list[6], insert_temp_list[7], insert_temp_list[5], insert_temp_list[8], insert_temp_list[9], insert_temp_list[0], insert_temp_list[10], 1)
        insert_request(insert_temp_list[3], insert_temp_list[13], insert_temp_list[14], insert_temp_list[12], insert_temp_list[15], insert_temp_list[16], insert_temp_list[0], insert_temp_list[17], -1)
    return


################################################################
####################  Main code starts here ####################
################################################################
def solver(input_file, output_file, ttl, cur_seed):
    global tools, coordinates, requests, DATASET, NAME, DAYS, capacity, MAX_TRIP_DISTANCE, DEPOT_COORDINATE, VEHICLE_COST, VEHICLE_DAY_COST, DISTANCE_COST, NUM_OF_TOOL_TYPES, days, max_tools_used, bad_count, err_count, tot_count, best_solution, best_cost, fine
    random.seed(cur_seed)
    [tools, coordinates, requests, DATASET, NAME, DAYS, capacity, MAX_TRIP_DISTANCE, DEPOT_COORDINATE, VEHICLE_COST, VEHICLE_DAY_COST, DISTANCE_COST, NUM_OF_TOOL_TYPES] = open_file(input_file)
    best_solution = []
    fine = define_fine(DISTANCE_COST, VEHICLE_DAY_COST, VEHICLE_COST)
    max_tools_used = [0] * NUM_OF_TOOL_TYPES
    days = [Day() for i in range(DAYS)]
    bad_count, err_count, tot_count = 0, 0, 0
    start = time.clock()
    schedule_requests()
    total_elapsed = time.clock()
    total_elapsed = total_elapsed - start
    best_solution = copy.deepcopy(days)
    best_cost = total_solution_cost()[3]
    ttl=ttl - total_elapsed
    p = adaptive_search(ttl-1)[0]
    print_output(output_file)
    return


if __name__ == '__main__':
    import sys
    global output_file
    input_file, output_file, ttl, cur_seed = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    solver(input_file, output_file, ttl, cur_seed)
