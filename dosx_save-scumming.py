import copy
import random
import re
import sys
import time

areas = [
    {"area": "Blackpits",
     "types": [
        {"type": "Container",
         "abbrev": "c",
         "count": 2,                    # 12,
         "objective": False
        },
        {"type": "Container - Brian",
         "abbrev": "cB",
         "count": 2,                    # 8,
         "objective": False
        },
        {"type": "Desk",
         "abbrev": "d",
         "count": 1,
         "objective": False
        },
        {"type": "Cupboard",
         "abbrev": "CupB",
         "count": 1,
         "objective": False
        },
        {"type": "Cabinet",
         "abbrev": "Cab",
         "count": 1,
         "objective": False
        },
        {"type": "Kitchen rack",
         "abbrev": "KR",
         "count": 1,
         "objective": False
        },
        {"type": "Coffin",
         "abbrev": "Cof",
         "count": 2,                    # 8,
         "objective": False
        },
       {"type": "Skeleton",
         "abbrev": "Sk",
         "count": 2,                    # 5,
         "objective": False
        },
        {"type": "Unlabeled sacks",
         "abbrev": "US",
         "count": 2,                    # 4,
         "objective": False
        },
 
        {"type": "target",
         "abbrev": "TGT",
         "count": 1,
         "objective": True
        },
     ]
    },
]

solutions = [
#    {"cost": 0,
#     "number": 0,
#     "steps": [
#        {"type": "ornate chest",
#         "abbrev": "ES-ORNATE",
#         "count": 1
#         "objective": True
#        }
#     ]
#    }
]

solutions_set = set()
preserve_rare_abbrevs = set()

start_time = time.time()
total_solutions = 0
exploration_cutoff_base_len = 8
max_solutions = 1000000
reduction_count = 50000
total_items = 0
overrepresented_age_window_size = reduction_count
cost_delete_threshold = 10.0
total_deletions_by_cost = 0
total_deletions_by_inversion = 0
total_deletions_for_longer = 0
longer = False
longer_factor = 1
time_limited = True
randomly_terminate_exploration = None
preserve_rares_threshold = 0
printed_times_up = False

def main():
    global longer
    global longer_factor
    global time_limited
    global randomly_terminate_exploration
    global start_time
    global printed_times_up
    global solutions
    global total_solutions
    global total_items
    global total_deletions_by_cost
    global total_deletions_by_inversion
    global total_deletions_for_longer
    global preserve_rares_threshold

    min_area_index = None
    final_solutions_limit = 25

    argv_copy = sys.argv[1:]

    while len(argv_copy):
        if argv_copy[0] == '--sequential' or argv_copy[0] == '-s':
            min_area_index = 0
            argv_copy = argv_copy[1:]
            continue

        if argv_copy[0] == '--no-time-limit' or argv_copy[0] == '-t':
            time_limited = False
            argv_copy = argv_copy[1:]
            continue

        if argv_copy[0] == '--randomly-terminate-exploration':
            if len(argv_copy) == 1:
                raise KeyError("missing termination factor") 
            randomly_terminate_exploration = int(argv_copy[1])
            argv_copy = argv_copy[2:]
            continue

        if argv_copy[0] == '--longer' or argv_copy[0] == '-l':
            if len(argv_copy) == 1:
                raise KeyError("missing longer factor") 
            if re.search(r'[^0-9]', argv_copy[1]):
                raise ValueError(f"invalid longer factor {argv_copy[1]}") 
            longer_factor = int(argv_copy[1])
            longer = True
            time_limited = False
            argv_copy = argv_copy[2:]
            continue

        if argv_copy[0] == '--num-solutions' or argv_copy[0] == '-n':
            if len(argv_copy) == 1:
                raise KeyError("missing solution count") 
            if re.search(r'[^0-9]', argv_copy[1]):
                raise ValueError(f"invalid solution count {argv_copy[1]}") 
            final_solutions_limit = int(argv_copy[1])
            argv_copy = argv_copy[2:]
            continue

        if argv_copy[0] == '--preserve-rares' or argv_copy[0] == '-p' or argv_copy[0] == '-p2':
            for area in areas:
                for cont_group in area["types"]:
                    if cont_group["count"] == 1 and not cont_group["objective"]:
                        preserve_rare_abbrevs.add(cont_group["abbrev"])
            if argv_copy[0] == '-p2':
                preserve_rares_threshold = 2
            else:
                preserve_rares_threshold = 1
            argv_copy = argv_copy[1:]
            continue

        raise KeyError(f"invalid argument {argv_copy[0]}") 

    for area in areas:
        for cont_group in area["types"]:
            # cont_groups need a reference to their area
            if "area" not in cont_group:
                cont_group["area"] = area["area"]

            # Check for duplicate abbrev
            for other_area in areas:
                for other_group in other_area["types"]:
                    if cont_group is not other_group:
                        if cont_group["abbrev"] == other_group["abbrev"]:
                            dup_abbrev = cont_group["abbrev"]
                            raise Exception(f"duplicate abbrev {dup_abbrev}")
            total_items += cont_group["count"]

    explore_all(areas, [], None, min_area_index)

    elapsed_time = time.time() - start_time
    num_solutions = len(solutions)
    limit_solutions_length(final_solutions_limit)
    print(f"\nElapsed time: {elapsed_time}, num solutions = {num_solutions}, total solutions = {total_solutions}\n")
    print(f"total_deletions_by_cost = {total_deletions_by_cost}")
    print(f"total_deletions_by_inversion = {total_deletions_by_inversion}")
    print(f"total_deletions_for_longer = {total_deletions_for_longer}")

    if printed_times_up:
        print("\nNOTE: ABORTED DUE TO TIME LIMIT")

    solutions.sort(key=lambda s: [(not x["objective"], x["abbrev"].upper()) for x in s["steps"]])
    
    print("\nFINAL SET:\n")
    final = []
    for s in solutions:
        final.append(concise_string(s["steps"]))
    for s in final:
        print(s)

def explore_all(areas, steps, skip_container_type, min_area_index):
    global start_time
    global time_limited
    global printed_times_up
    global exploration_cutoff_base_len
    global longer
    global longer_factor
    global preserve_rares_threshold

    if time_limited and time.time() - start_time > 15 * 60:
        if not printed_times_up:
            print("\nTime's up!\n")
            printed_times_up = True
        return

    if len(steps) > exploration_cutoff_base_len + longer_factor and not continue_long_run_anyway(areas):
        # yeah no, that's really excessive...
        return

    if ( randomly_terminate_exploration is not None and len(steps) >= 2 + longer_factor and
            random.random() > 0.5 / (longer_factor * randomly_terminate_exploration) ):
        return

    if preserve_rares_threshold >= 1 and len(steps) > 1:
        total_rares = 0
        for step in steps:
            if step["abbrev"] in preserve_rare_abbrevs:
                total_rares += 1
        if total_rares > preserve_rares_threshold or (
                total_rares == preserve_rares_threshold and random.random() > 0.5):
            return

    range_start_index = 0
    if min_area_index is not None:
        range_start_index = min_area_index

    for a_i in range(range_start_index, len(areas)):
        area = areas[a_i]
        for t_i in range(0, len(area["types"])):
            cont_group = area["types"][t_i]

            if cont_group["type"] == skip_container_type:
                continue

            if cont_group["objective"]:
                steps.append(cont_group)
                add_solution_if_not_redundant_limit_count(steps)
                steps.pop()
            else:
                for add_c in range(1, cont_group["count"]+1):
                    for i in range(0, add_c):
                        steps.append(cont_group)

                    new_cont_group_count = cont_group["count"] - add_c
                    assert new_cont_group_count >= 0 and new_cont_group_count < cont_group["count"]

                    if min_area_index is not None:
                        assert a_i >= min_area_index
                        min_area_index = a_i

                    if new_cont_group_count > 0:
                        old_count = cont_group["count"]
                        cont_group["count"] = new_cont_group_count
                        explore_all(areas, steps, cont_group["type"], min_area_index)
                        cont_group["count"] = old_count
                    else:
                        # This container group is now empty
                        if len(area["types"]) > 1:
                            # Remove the empty container group, but there are other container groups left
                            types = area["types"]
                            removed_group = types.pop(t_i)
                            explore_all(areas, steps, cont_group["type"], min_area_index)
                            types.insert(t_i, removed_group)
                        elif len(areas) > 1:
                            # That was the last container group in the area, so remove the area
                            removed_area = areas.pop(a_i)
                            explore_all(areas, steps, cont_group["type"], min_area_index)
                            areas.insert(a_i, removed_area)

                    for i in range(0, add_c):
                        steps.pop()

def add_solution_if_not_redundant_limit_count(new_steps):
    global start_time
    global longer
    global longer_factor
    global exploration_cutoff_base_len
    global total_items
    global solutions
    global solutions_set
    global total_solutions
    global max_solutions
    global reduction_count
    global preserve_rares_threshold

    len_new_steps = len(new_steps)

    if ( longer and len_new_steps < exploration_cutoff_base_len + longer_factor * 0.75
                and len_new_steps < total_items * 0.75 ):
        # Too short
        return

    if preserve_rares_threshold >= 1 and len_new_steps > 1:
        total_rares = 0
        for step in new_steps:
            if step["abbrev"] in preserve_rare_abbrevs:
                total_rares += 1
        if total_rares > preserve_rares_threshold or (
                total_rares == preserve_rares_threshold and random.random() > 0.5):
            return

    # Calculate solution cost
    new_steps_cost = 1.0
    if len_new_steps > 1:
        for s_i in range(1, len_new_steps):
            if new_steps[s_i]["area"] != new_steps[s_i - 1]["area"]:
                new_steps_cost += 1.0
            else:
                new_steps_cost += 0.1

    solution_set_string = set_string(new_steps)
    if solution_set_string in solutions_set:
        # Find the redundancy
        for existing_solution_i in range(0, len(solutions)):
            existing_solution_steps = solutions[existing_solution_i]["steps"]
            redundant = len(existing_solution_steps) == len_new_steps
            if redundant:
                # Not necessarily...
                for s_i in range(0, len_new_steps):
                    if existing_solution_steps[s_i]["type"] != new_steps[s_i]["type"]:
                        redundant = False
                        break
            if redundant:
                # We found the match.  Replace the existing solution if the cost is lower.
                if new_steps_cost < solutions[existing_solution_i]["cost"]:
                    print(f"Better solution:\nOLD: {solutions[existing_solution_i]}")
                    solutions[existing_solution_i]["cost"] = new_steps_cost
                    # solutions[existing_solution_i]["steps"] = copy.deepcopy(new_steps)    # slow, unnecessary
                    # solutions[existing_solution_i]["steps"] = copy.copy(new_steps)        # shallow copy: medium
                    solutions[existing_solution_i]["steps"] = new_steps[:]                  # shallow copy: fastest
                    print(f"NEW: {solutions[existing_solution_i]}")
                return

        raise LookupError("Redundant item from solutions_set not found in solutions")

    # solutions.append({"cost": new_steps_cost, "steps": copy.deepcopy(new_steps)}) # slow, unnecessary
    # solutions.append({"cost": new_steps_cost, "steps": copy.copy(new_steps)})     # shallow copy: medium
    solutions.append({"cost": new_steps_cost, "number": total_solutions, "steps": new_steps[:]})               # shallow copy: fastest
    solutions_set.add(solution_set_string)
    total_solutions += 1

    print(concise_string(solutions[-1]["steps"]))
    elapsed_time = time.time() - start_time
    print(f"Elapsed time: {elapsed_time}, num solutions = {len(solutions)}, total = {total_solutions}")

    # Keep the number of solutions under control
    if len(solutions) > max_solutions:
        limit_solutions_length(max_solutions - reduction_count)

def continue_long_run_anyway(areas):
    num_containers = 0
    for area in areas:
        for cont_group in area["types"]:
            num_containers += cont_group["count"]
    return random.random() < (0.1 / num_containers)

def concise_string(steps):
    s = steps[0]["abbrev"]
    for s_i in range(1, len(steps)):
        s += ", " + steps[s_i]["abbrev"]
    return s

def set_string(steps):
    s = steps[0]["type"]
    for s_i in range(1, len(steps)):
        s += ", " + steps[s_i]["type"]
    return s

def limit_solutions_length(max_count):
    global solutions
    global solutions_set
    global longer
    global longer_factor
    global cost_delete_threshold
    global total_deletions_by_cost
    global total_deletions_by_inversion
    global total_deletions_for_longer

    while len(solutions) > max_count:
        most_overrepresented_age = find_most_overrepresented_age()

        remove_count = int(most_overrepresented_age["count"] / 100)
        if remove_count < most_overrepresented_age["by_how_many"]:
            remove_count = most_overrepresented_age["by_how_many"]

        if remove_count > len(solutions) - max_count:
            remove_count = len(solutions) - max_count

        assert remove_count >= 1

        while remove_count:
            delete_candidate_i = ( most_overrepresented_age["start_i"] +
                                    random.randint(0, most_overrepresented_age["count"] - 1) )

            delete_label = None
            use_longer_factor = longer_factor
            if longer and longer_factor < 4:
                use_longer_factor = 4

            if use_longer_factor > 1 and random.random() > 1.85 / use_longer_factor:
                # deleting an item without considering the cost heuristic is more prone to deleting shorter solutions
                # than with, thereby allowing longer solutions to survive
                delete_label = "DELETING (LONGER)"
                total_deletions_for_longer += 1
            elif random.random() * (solutions[delete_candidate_i]["cost"]) > cost_delete_threshold:
                delete_label = "DELETING (COST)"
                total_deletions_by_cost += 1
                cost_delete_threshold += 0.03
            elif simple_inversion_exists(delete_candidate_i):
                delete_label = "DELETING (INVERSION)"
                total_deletions_by_inversion += 1

            if delete_label is not None:
                solution_concise_string = concise_string(solutions[delete_candidate_i]["steps"])
                solution_set_string = set_string(solutions[delete_candidate_i]["steps"])
                print(f"{delete_label}: {solution_concise_string}")
                del solutions[delete_candidate_i]
                solutions_set.remove(solution_set_string)

                remove_count -= 1

                if delete_candidate_i < most_overrepresented_age["start_i"] + most_overrepresented_age["count"]:
                    most_overrepresented_age["count"] -= 1
            elif cost_delete_threshold > 1.0:
                cost_delete_threshold -= 0.005

    print(f"total_deletions_by_cost = {total_deletions_by_cost}")
    print(f"total_deletions_by_inversion = {total_deletions_by_inversion}")
    print(f"total_deletions_for_longer = {total_deletions_for_longer}")
    print(f"cost_delete_threshold = {cost_delete_threshold}")

def find_most_overrepresented_age():
    global solutions
    global reduction_count
    global overrepresented_age_window_size

    if len(solutions) <= 2 * reduction_count:
        # There are not enough solutions left for this analysis
        return {"start_i": 0,
                "start_number": solutions[0]["number"],
                "end_number": solutions[-1]["number"],
                "count": len(solutions),
                "by_how_many": len(solutions)}

    while True:
        dithered_age_window_size = overrepresented_age_window_size
        dithered_age_window_size += int(((random.random() - 0.5) / 3) * dithered_age_window_size)

        start_number = solutions[0]["number"]
        start_number -= start_number % dithered_age_window_size
        age_range_end_i = find_last_solution_with_number_less_than(0, start_number + dithered_age_window_size);
        current = {"start_i": 0,
                   "start_number": start_number,
                   "end_number": solutions[age_range_end_i]["number"],
                   "count": age_range_end_i + 1}
        first = current
        second = None
        check_i = age_range_end_i + 1

        while check_i < len(solutions):
            start_number = solutions[check_i]["number"]
            start_number -= start_number % dithered_age_window_size
            age_range_end_i = find_last_solution_with_number_less_than(check_i,
                                                                       start_number + dithered_age_window_size);
            current = {"start_i": check_i,
                       "start_number": start_number,
                       "end_number": solutions[age_range_end_i]["number"],
                       "count": age_range_end_i + 1 - check_i}

            if current["count"] > first["count"]:
                second = first
                first = current
            elif second is None or current["count"] > second["count"]:
                second = current

            check_i = age_range_end_i + 1

        if first["count"] > reduction_count / 2:
            # That's a big enough set to be a keeper
            break

        # That's not a big enough set, double the age block size and retry
        overrepresented_age_window_size *= 2

    # See if current (the trailing block) should be lumped in with first or second
    if current is not first and current["start_i"] == first["start_i"] + first["count"]:
        first["count"] += current["count"]
        current = first
    elif current is not second and second is not None and current["start_i"] == second["start_i"] + second["count"]:
        second["count"] += current["count"]
        current = second
    else:
        tempering_check_lower_limit = 750
        tempering_factor = 0.0075
        tempered_result_minimum = 2

        if current["count"] >= tempering_check_lower_limit:
            # See if on a weighted basis, current is actually overrepresented
            current_count_per_age = current["count"] / (current["end_number"] - current["start_number"])
            first_count_per_age = first["count"] / (first["end_number"] - first["start_number"])
            if current_count_per_age > first_count_per_age:
                density_ratio = first_count_per_age / current_count_per_age
                raw_excess = int(current["count"] * (1.0 - density_ratio))
                by_how_many = int(raw_excess * tempering_factor)
                if by_how_many == 0:
                    by_how_many = 1
                elif by_how_many > current["count"] - 2:
                    by_how_many = current["count"] - 2

                if by_how_many >= tempered_result_minimum:
                    return {"start_i": current["start_i"],
                            "start_number": current["start_number"],
                            "end_number": current["end_number"],
                            "count": current["count"],
                            "by_how_many": by_how_many}

    return {"start_i": first["start_i"],
            "start_number": first["start_number"],
            "end_number": first["end_number"],
            "count": first["count"],
            "by_how_many": first["count"] - second["count"]}

def find_last_solution_with_number_less_than(checked_start_i, less_than_number):
    global solutions

    unchecked_end_i = len(solutions) - 1
    while checked_start_i < unchecked_end_i:
        mid_i = int((checked_start_i + unchecked_end_i) / 2)
        if mid_i == checked_start_i:
            mid_i += 1
        assert mid_i < len(solutions)
        mid_i_number = solutions[mid_i]["number"]
        if mid_i_number < less_than_number:
            checked_start_i = mid_i
        elif mid_i_number == less_than_number:
            assert solutions[mid_i-1]["number"] < less_than_number
            return mid_i - 1
        else:
            assert solutions[mid_i]["number"] > less_than_number
            unchecked_end_i = mid_i - 1

    assert (solutions[checked_start_i]["number"] < less_than_number and
            (checked_start_i == len(solutions) - 1 or solutions[checked_start_i+1]["number"] >= less_than_number))

    return checked_start_i

def simple_inversion_exists(check_i):
    global solutions
    global solutions_set

    check_solution = solutions[check_i];
    steps = check_solution["steps"]
    for i in range(0, len(steps)-2):        # last step is always a target
        if steps[i]["type"] != steps[i+1]["type"]:
            inverted_steps = steps[:]       # shallow copy
            temp = inverted_steps[i]
            inverted_steps[i] = inverted_steps[i+1]
            inverted_steps[i+1] = temp
            if set_string(inverted_steps) in solutions_set:
                return True

    return False

main()