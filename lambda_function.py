from __future__ import print_function
from ortools.sat.python import cp_model
import json
import collections
import pandas as pd
from collections import defaultdict
import boto3

class AutoVivification(dict):
    """Implementation of perl's autovivification feature."""
    def __getitem__(self, item):
        try:
            return dict.__getitem__(self, item)
        except KeyError:
            value = self[item] = type(self)()
            return value
            
def upload(source_file, bucket_name, object_key):
    s3 = boto3.resource('s3')

    # Uploads the source file to the specified s3 bucket by using a
    # managed uploader. The uploader automatically splits large
    # files and uploads parts in parallel for faster uploads.
    try:
        return s3.Bucket(bucket_name).upload_file(source_file, object_key)
    except Exception as e:
        print(e)
        
def lambda_handler(event, context):
    # This program tries to find an optimal assignment of nurses to shifts
    # (3 shifts per day, for 7 days), subject to some constraints (see below).
    # Each nurse can request to be assigned to specific shifts.
    # The optimal assignment maximizes the number of fulfilled shift requests.
    body = json.loads(event['body'])
    # body = event
    num_nurses = int(body['num_doctors'])
    num_shifts = 1
    num_days = int(body['num_days'])
    num_rooms = int(body['num_rooms'])
    constraints = body['constraints']

    all_nurses = range(num_nurses)
    # all_shifts = range(num_shifts)
    all_days = range(num_days)
    all_rooms = range(num_rooms)
    # shift_requests = [[[0, 0, 1], [0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 1],
    #                   [0, 1, 0], [0, 0, 1]],
    #                   [[0, 0, 0], [0, 0, 0], [0, 1, 0], [0, 1, 0], [1, 0, 0],
    #                   [0, 0, 0], [0, 0, 1]],
    #                   [[0, 1, 0], [0, 1, 0], [0, 0, 0], [1, 0, 0], [0, 0, 0],
    #                   [0, 1, 0], [0, 0, 0]],
    #                   [[0, 0, 1], [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0],
    #                   [1, 0, 0], [0, 0, 0]],
    #                   [[0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 0, 0], [1, 0, 0],
    #                   [0, 1, 0], [0, 0, 0]]]
    room_requests = [ [0]*num_nurses for _ in all_rooms ]
    for n, item in enumerate(constraints):
        if (constraints[n]['doctor']):
            doctor_number = int(constraints[n]['doctor'])
            room_requests[n][doctor_number] = 1
    print(room_requests)
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
                    print(r,n)
                    if n<len(room_requests) and room_requests[r][n] == 1:
                        data["Day"+str(d)][constraints[r]['room']]= n
                        # print('Nurse', constraints[n]['doctor'], 'works ' , 'in room', r, '(requested).')
                    else:
                        data["Day"+str(d)][constraints[r]['room']]= n
                        # print('Nurse', constraints[n]['doctor'], 'works', 'in room', r, '(not requested).')
        # print()

    df = pd.DataFrame.from_dict({(i): data[i] 
                           for i in data.keys() 
                           },orient='index')
    source = '/tmp/schedule.xls'
    bucket = 'doctor-schedule'
    destination = 'schedule.xls'
    df.to_excel(source, index=True)
    upload(source,bucket,destination)
    url = 'https://'+bucket+'.s3.amazonaws.com/'+destination
    result = {
        'statusCode':200,
        'headers':{'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'},
        'body':json.dumps({'url': url})
    }
    # print(result)
    # # Statistics.
    # print()
    # print('Statistics')
    # print('  - Number of shift requests met = %i' % solver.ObjectiveValue(),
    #       '(out of', num_nurses * min_shifts_per_nurse, ')')
    # print('  - wall time       : %f s' % solver.WallTime())
    return result