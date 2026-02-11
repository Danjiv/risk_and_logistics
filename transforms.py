
import pandas as pd
def get_CostSupplierCandidate(DistanceSupplierDistrict_df: pd.DataFrame, Suppliers_df: pd.DataFrame,
                               VehicleCostPerMileAndTonneOverall: dict, Candidates, Suppliers)->dict:
    # Cost from suppliers to candidate facilities
    # Round-trip distance (factor 2)
    # Cost depends on supplier vehicle type
    # Division by 1000 converts from kg to tonnes
    CostSupplierCandidate = {
        (k, j): 2
        * DistanceSupplierDistrict_df.loc[k, j]
        * VehicleCostPerMileAndTonneOverall[
            Suppliers_df.loc[k, "Vehicle type"]
        ]
        / 1000
        for j in Candidates
        for k in Suppliers
    }

    return CostSupplierCandidate

def get_CostCandidateCustomers(DistanceDistrictPeriod_df_dict: dict, VehicleCostPerMileAndTonneOverall: dict,
                               Candidates, Customers, Times)->dict:
    # Cost from candidate facilities to customers
    # All transports use 3.5t vans (vehicle type 3)
    CostCandidateCustomers = {
        (j, i, t): 2
        * DistanceDistrictPeriod_df_dict.get((i, t))[j-1]
        * VehicleCostPerMileAndTonneOverall[3]
        / 1000
        for j in Candidates
        for i in Customers
        for t in Times
    }

    return CostCandidateCustomers