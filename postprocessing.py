import xpress as xp

def postprocessing(prob):
    # =============================================================================
# Post-processing and data visualisation
# =============================================================================

    sol_status = prob.attributes.solstatus

    if sol_status == xp.SolStatus.OPTIMAL:
        print("Optimal solution found")
        best_obj = prob.attributes.objval
        best_bound = prob.attributes.bestbound
        mip_gap = abs(best_obj - best_bound) / (1e-10 +abs(best_obj))
        print(f"MIP Gap: {mip_gap*100:.2f}%")
    
    elif sol_status == xp.SolStatus.FEASIBLE:
        print("Feasible solution (not proven optimal)")
        best_obj = prob.attributes.objval
        best_bound = prob.attributes.bestbound
        print(f"Best bound: {best_bound}")
        mip_gap = abs(best_obj - best_bound) / (1e-10 +abs(best_obj))
        print(f"MIP Gap: {mip_gap*100:.2f}%")
    elif sol_status == xp.SolStatus.INFEASIBLE:
        print("Model is infeasible")
    elif sol_status == xp.SolStatus.UNBOUNDED:
        print("Model is unbounded")
    else:
        print("No solution available")
