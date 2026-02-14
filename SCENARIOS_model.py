import xpress as xp
import numpy as np
import postprocessing
import pandas as pd
import constants

def SCENARIOS_model(Candidates, Times, Suppliers, Products,Customers, Scenarios,
                 Operating_df, Setup_df, CostSupplierCandidate,
                 DemandPeriodsGrouped, CostCandidateCustomers,
                 Suppliers_df, Candidates_df, TotalDemandProductPeriodScenarios_dict):
    # =============================================================================
    # Build optimization model
    # =============================================================================
    prob = xp.problem("SCENARIOS")

    xp.setOutputEnabled(True)
    #prob.controls.maxtime = -300
    # =============================================================================
    # Declarations
    # =============================================================================

    build = np.array([prob.addVariable(name='build_{0}_{1}'.format(c, t), vartype=xp.binary)
                    for c in Candidates for t in Times], dtype=xp.npvar).reshape(len(Candidates), len(Times))

    open = np.array([prob.addVariable(name='open_{0}_{1}'.format(c, t), vartype=xp.binary)
                    for c in Candidates for t in Times], dtype=xp.npvar).reshape(len(Candidates), len(Times))

    supply = np.array([prob.addVariable(name='supply_{0}_{1}_{2}_{3}'.format(c, s, t, sc), vartype=xp.continuous, ub = 1)
                    for c in Candidates for s in Suppliers for t in Times for sc in Scenarios], dtype=xp.npvar).reshape(
                        len(Candidates), len(Suppliers), len(Times), len(Scenarios))

    warehoused = np.array([prob.addVariable(name='warehoused_{0}_{1}_{2}_{3}'.format(c, p, t, sc), vartype=xp.continuous)
                        for c in Candidates for p in Products for t in Times for sc in Scenarios],dtype=xp.npvar).reshape(
                            len(Candidates), len(Products), len(Times), len(Scenarios)
                        )
    delivered = np.array([prob.addVariable(name='delivered_{0}_{1}_{2}_{3}_{4}'.format(c, Customers[k], p, t, sc), vartype=xp.continuous, ub = 1)
                        for c in Candidates for k in range(len(Customers))
                        for p in Products for t in Times for sc in Scenarios],dtype=xp.npvar).reshape(
                            len(Candidates), len(Customers), len(Products), len(Times), len(Scenarios)
                        )

    #=========================================================================================================
    # Objective function
    # ========================================================================================================
    # Need to factor in the fixed costs related to the number of vans you have to send!!!!!
    prob.setObjective(xp.Sum(open[c-1,t-1]*Operating_df["Operating cost"][c-1] for c in Candidates for t in Times) +
                    xp.Sum(build[c-1, t-1]*Setup_df["Setup cost"][c-1] for c in Candidates for t in Times) +
                    (1/len(Scenarios))*xp.Sum(
                    xp.Sum(supply[c-1, s-1, t-1]*TotalDemandProductPeriodScenarios_dict[sc-1][(Suppliers_df["Product group"][s], t)]*CostSupplierCandidate[(s, c)]
                            for c in Candidates for s in Suppliers for t in Times for sc in Scenarios) +
                    xp.Sum(delivered[c-1, k, p-1, t-1, sc-1]*DemandPeriodsGrouped[sc-1][Customers[k], p, t]*CostCandidateCustomers[sc-1][(c, Customers[k], t)] 
                            for c in Candidates for k in range(len(Customers)) for p in Products for t in Times for sc in Scenarios)), 
                    sense = xp.minimize)

    # ========================================================================================================
    # Constraints
    # ========================================================================================================
    # warehouses can only be built in one time period
    prob.addConstraint(xp.Sum(build[c-1, t-1] for t in Times) <= 1 for c in Candidates)
    # warehouse cannot be open if it's not been built
    # not sure this constraint is working as intended!!!!!!
    prob.addConstraint(open[c-1, t-1] <= xp.Sum(build[c-1, t2] for t2 in range(t-1)) for c in Candidates for t in Times if t != 1)
    # Warehouse remains open from the year it's built onwards
    prob.addConstraint(open[c-1, t-1] >= build[c-1, t-1] for c in Candidates for t in Times)
    prob.addConstraint(open[c-1, t-1] >= open[c-1, t-2] for c in Candidates for t in Times if t != 1)
    prob.addConstraint(open[c-1, 0] == build[c-1, 0] for c in Candidates)
    # SUPPLIER CONSTRAINTS
    # Can't supply to a warehouse that is not open.
    prob.addConstraint(supply[c-1, s-1, t-1, sc-1] <= open[c-1, t-1]
                               for c in Candidates for s in Suppliers for t in Times for sc in Scenarios)   
    # will always supply enough in each time period to meet total demand but can add a specific constraint
    prob.addConstraint(xp.Sum(supply[c-1, s-1, t-1, sc-1]
                              for s in Suppliers if Suppliers_df["Product group"][s]==p
                               for c in Candidates )==1 
                       for p in Products for t in Times for sc in Scenarios) 
    #  can't supply more than total capacity
    prob.addConstraint(xp.Sum(supply[c-1, s-1, t-1, sc-1]*TotalDemandProductPeriodScenarios_dict[sc-1][(Suppliers_df["Product group"][s], t)]
                               for c in Candidates) <= Suppliers_df["Capacity"][s]
                        for s in Suppliers for t in Times for sc in Scenarios)
    # No point in supplying more than total product demand in any period
    prob.addConstraint(xp.Sum(supply[c-1, s-1, t-1]*TotalDemandProductPeriodScenarios_dict[sc-1][(Suppliers_df["Product group"][s], t)] 
                        for c in Candidates) <= TotalDemandProductPeriodScenarios_dict[sc-1][(Suppliers_df["Product group"][s], t)]
                          for s in Suppliers for t in Times for sc in Scenarios)
    # update warehouse stock
    prob.addConstraint(warehoused[c-1, p-1, t-1, sc-1] == xp.Sum(supply[c-1, s-1, t-1, sc-1]*TotalDemandProductPeriodScenarios_dict[sc-1][(Suppliers_df["Product group"][s], t)]
                            for s in Suppliers if Suppliers_df["Product group"][s] == p)
                            for c in Candidates for p in Products for t in Times for sc in Scenarios)
    # Can't carry more stock than max capacity
    prob.addConstraint(xp.Sum(warehoused[c-1, p-1, t-1, sc-1] for p in Products) <= Candidates_df["Capacity"][c]
                        for c in Candidates for t in Times for sc in Scenarios)
    # Can't carry any stock in a warehouse that isn't open
    prob.addConstraint(xp.Sum(warehoused[c-1, p-1, t-1, sc-1] for p in Products) <= Candidates_df["Capacity"][c]*open[c-1, t-1]
                    for c in Candidates for t in Times for sc in Scenarios)
    #DELIVERY CONSTRAINTS
    # Cannot deliver from a warehouse that is not open
    prob.addConstraint(delivered[c-1, k, p-1, t-1, sc-1] <= open[c-1, t-1]
                    for c in Candidates for k in range(len(Customers)) for p in Products for t in Times for sc in Scenarios)
    #ensure we meed customer demand
    #prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1] for c in Candidates) >= DemandPeriodsGrouped[Customers[k], p, t]
    #                   for k in range(len(Customers)) for p in Products for t in Times)
    prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1, sc-1] for c in Candidates)==1
                    for k in range(len(Customers)) for p in Products for t in Times for sc in Scenarios)
    #can't deliver more than the warehouses hold
    prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1, sc-1]*DemandPeriodsGrouped[sc-1][Customers[k], p, t]
                            for k in range(len(Customers))) <= warehoused[c-1, p-1, t-1, sc-1]
                    for c in Candidates for p in Products for t in Times for sc in Scenarios)
    

    prob.solve()
    print(f'The objective function value for scenarios is {prob.attributes.objval}')
    
    #print and save some summary stats
    #the period when warehouses get built/opened is saved off into
    #the csv's build.csv and open.csv, respectively.

    operating_costs = 0
    building_costs = 0
    supply_costs = 0
    delivery_costs = 0
    open = prob.getSolution(open)
    build = prob.getSolution(build)
    supply = prob.getSolution(supply)
    delivery = prob.getSolution(delivered)
    for c in Candidates:
        for t in Times:
            operating_costs = operating_costs + open[c-1,t-1]*Operating_df["Operating cost"][c-1]
            building_costs = building_costs + build[c-1, t-1]*Setup_df["Setup cost"][c-1]

    build_df = pd.DataFrame(data = build, index = Candidates, columns = Times)
    build_df = build_df[build_df.sum(axis=1) > 0]
    open_df = pd.DataFrame(data = open, index = Candidates, columns = Times)
    open_df = open_df[open_df.sum(axis=1)>0]


    build_df.to_csv(f"build_{constants.clustertype()}_scenarios{len(Scenarios)}.csv")
    open_df.to_csv(f"open_{constants.clustertype()}_scenarios_{len(Scenarios)}.csv")
    vals = pd.DataFrame({"number_of_scenarios": [len(Scenarios)],
                        "obj_val": [prob.attributes.objval],
                        "operating_costs": [operating_costs],
                        "building_costs": [building_costs]})
    vals.to_csv(f"model_stats_{constants.clustertype()}_scenarios{len(Scenarios)}.csv")

    print(f"operating costs scenarios: {operating_costs}")
    print(f"building costs scenarios: {building_costs}")

    postprocessing.postprocessing(prob)
