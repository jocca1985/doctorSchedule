from __future__ import print_function
from ortools.sat.python import cp_model
import json
import collections
import csv
import pandas as pd
from collections import defaultdict

class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value

def main():
    # This program tries to find an optimal assignment of nurses to shifts
    # (3 shifts per day, for 7 days), subject to some constraints (see below).
    # Each nurse can request to be assigned to specific shifts.
    # The optimal assignment maximizes the number of fulfilled shift requests.
    with open('sample.json') as f:
        data = json.load(f)

    num_nurses = int(data['num_doctors'])
    num_shifts = 1
    num_days = int(data['num_days'])
    num_rooms = int(data['num_rooms'])
    constraints = data['constraints']
    vacations = data['vacation']
    all_nurses = range(num_nurses)
    all_shifts = range(num_shifts)
    all_rooms = range(num_rooms)
    all_days = range(num_days)

    room_requests = [ [0]*num_nurses for _ in all_rooms ]
    # room_requests = [room_requests for _ in all_rooms]
    for constraint, item in enumerate(constraints):
        if (constraints[constraint]['doctor']):
            doctor_number = int(constraints[constraint]['doctor'])
            # for d in all_days:
            room_requests[constraint][doctor_number] = 1

    # for i, item in enumerate(vacations):
    #     start = int(vacations[i]['dayStart'])
    #     end = int(vacations[i]['dayEnd'])
    #     for d in range(start,end):
    #         for r in all_rooms:
    #             doctor_number = int(vacations[i]['doctor'])
    #             room_requests[r][d][doctor_number] = 0
    # print(len(room_requests))
    # Creates the model.
    model = cp_model.CpModel()

    # Creates shift variables.
    # shifts[(n, d, s, r)]: nurse 'n' works shift 's' on day 'd' in room 'r'.
    shifts = {}
    for n in all_nurses:
        for d in all_days:
            for r in all_rooms:
                    shifts[(n, d, r)] = model.NewBoolVar('shift_n%id%ir%i' % (n, d, r))

    # Each shift is assigned to exactly one nurse in .
    for d in all_days:
        for r in all_rooms:
            model.Add(sum(shifts[(n, d, r)] for n in all_nurses) == 1)

    # Each nurse works at most one shift per day.
    for n in all_nurses:
        for d in all_days:
            model.Add(sum(shifts[(n, d, r)] for r in all_rooms) <= 1)

    # for i, item in enumerate(vacations):
    #     start = int(vacations[i]['dayStart'])
    #     end = int(vacations[i]['dayEnd'])
    #     for d in range(start,end):
    #         for r in all_rooms:
    #             n = int(vacations[i]['doctor'])
    #             model.Add(shifts[(n,d,r)] == 0)
            
    # room constraints
    # for d in all_days:
    #     for s in all_shifts:
    #         model.Add(shifts[(0, d, s, 0)] == 1)
    model.Maximize(sum(room_requests[r][i]*shifts[(i, d, r)] for i in range(len(room_requests)) for d in all_days for r in all_rooms))
    # min_shifts_assigned is the largest integer such that every nurse can be
    # assigned at least that number of shifts.
    min_shifts_per_nurse = (num_rooms*num_shifts * num_days) // num_nurses
    max_shifts_per_nurse = min_shifts_per_nurse + 1
    for n in all_nurses:
        num_shifts_worked = sum(
            shifts[(n, d, r)] for d in all_days for r in all_rooms)
        model.Add(min_shifts_per_nurse <= num_shifts_worked)
        model.Add(num_shifts_worked <= max_shifts_per_nurse)

    # model.Maximize(
    #     sum(shift_requests[n][d][s] * shifts[(n, d, s, r)] for n in all_nurses
    #         for d in all_days for s in all_shifts for r in all_rooms))
    
    # Creates the solver and solve.
    solver = cp_model.CpSolver()
    solver.Solve(model)
    print("Solved")
    data = AutoVivification()
    for d in all_days:
        for n in all_nurses:
            for r in all_rooms:
                if solver.Value(shifts[(n, d, r)]) == 1:
                    data["Day"+str(d)][constraints[r]['room']]= n

    df = pd.DataFrame.from_dict({(i): data[i] 
                           for i in data.keys() 
                           },orient='index')
    source = './schedule.xls'
    df.to_excel(source, index=True)
    print(data)


if __name__ == '__main__':
    main()