import xpress as xp
import numpy as np
import postprocessing
import pandas as pd

def MECWLP_model(Candidates, Times, Suppliers, Products,Customers,
                 Operating_df, Setup_df, CostSupplierCandidate,
                 DemandPeriodsGrouped, CostCandidateCustomers,
                 Suppliers_df, Candidates_df):
    # =============================================================================
    # Build optimization model
    # =============================================================================
    prob = xp.problem("MECWLP")

    xp.setOutputEnabled(False)
    prob.controls.maxtime = -300
    # =============================================================================
    # Declarations
    # =============================================================================

    build = np.array([prob.addVariable(name='build_{0}_{1}'.format(c, t), vartype=xp.binary)
                    for c in Candidates for t in Times], dtype=xp.npvar).reshape(len(Candidates), len(Times))

    open = np.array([prob.addVariable(name='open_{0}_{1}'.format(c, t), vartype=xp.binary)
                    for c in Candidates for t in Times], dtype=xp.npvar).reshape(len(Candidates), len(Times))

    supply = np.array([prob.addVariable(name='supply_{0}_{1}_{2}'.format(c, s, t), vartype=xp.integer)
                    for c in Candidates for s in Suppliers for t in Times], dtype=xp.npvar).reshape(
                        len(Candidates), len(Suppliers), len(Times))

    warehoused = np.array([prob.addVariable(name='warehoused_{0}_{1}_{2}'.format(c, p, t), vartype=xp.integer)
                        for c in Candidates for p in Products for t in Times],dtype=xp.npvar).reshape(
                            len(Candidates), len(Products), len(Times)
                        )
    delivered = np.array([prob.addVariable(name='delivered_{0}_{1}_{2}_{3}'.format(c, Customers[k], p, t), vartype=xp.continuous, ub = 1)
                        for c in Candidates for k in range(len(Customers)) for p in Products for t in Times],dtype=xp.npvar).reshape(
                            len(Candidates), len(Customers), len(Products), len(Times)
                        )

    #=========================================================================================================
    # Objective function
    # ========================================================================================================
    # Need to factor in the fixed costs related to the number of vans you have to send!!!!!
    prob.setObjective(xp.Sum(open[c-1,t-1]*Operating_df["Operating cost"][c-1] for c in Candidates for t in Times) +
                    xp.Sum(build[c-1, t-1]*Setup_df["Setup cost"][c-1] for c in Candidates for t in Times) +
                    xp.Sum(supply[c-1, s-1, t-1]*CostSupplierCandidate[(s, c)] for c in Candidates for s in Suppliers for t in Times) +
                    xp.Sum(delivered[c-1, k, p-1, t-1]*DemandPeriodsGrouped[Customers[k], p, t]*CostCandidateCustomers[(c, Customers[k], t)] 
                            for c in Candidates for k in range(len(Customers)) for p in Products for t in Times), 
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
    # supplier constraints - can't supply more than total capacity
    prob.addConstraint(xp.Sum(supply[c-1, s-1, t-1] for c in Candidates) <= Suppliers_df["Capacity"][s] for s in Suppliers for t in Times)
    # update warehouse stock
    prob.addConstraint(warehoused[c-1, p-1, t-1] == xp.Sum(supply[c-1, s-1, t-1] 
                            for s in Suppliers if Suppliers_df["Product group"][s] == p)
                            for c in Candidates for p in Products for t in Times)
    # Can't carry more stock than max capacity
    prob.addConstraint(xp.Sum(warehoused[c-1, p-1, t-1] for p in Products) <= Candidates_df["Capacity"][c] for c in Candidates for t in Times)
    # Can't carry any stock in a warehouse that isn't open
    prob.addConstraint(xp.Sum(warehoused[c-1, p-1, t-1] for p in Products) <= Candidates_df["Capacity"][c]*open[c-1, t-1]
                    for c in Candidates for t in Times)
    #delivery constraints
    #ensure we meed customer demand
    #prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1] for c in Candidates) >= DemandPeriodsGrouped[Customers[k], p, t]
    #                   for k in range(len(Customers)) for p in Products for t in Times)
    prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1] for c in Candidates)==1
                    for k in range(len(Customers)) for p in Products for t in Times)
    #can't deliver more than the warehouses hold
    prob.addConstraint(xp.Sum(delivered[c-1, k, p-1, t-1]*DemandPeriodsGrouped[Customers[k], p, t]
                            for k in range(len(Customers))) <= warehoused[c-1, p-1, t-1]
                    for c in Candidates for p in Products for t in Times)
    

    prob.solve()
    print(f'The objective function value is {prob.attributes.objval}')
    
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


    build_df.to_csv("build.csv")
    open_df.to_csv("open.csv")

    print(f"operating costs: {operating_costs}")
    print(f"building costs: {building_costs}")

    postprocessing.postprocessing(prob)
