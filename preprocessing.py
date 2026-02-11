import pandas as pd
from typing import Tuple

def get_constituency(PostcodeDistricts: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Purpose of the function is to read in a cut of ONS' postcode directory for the UK
    and match on the westminster constituency that all of the postcode districts belong to
    Additionally, we return a dictionary containing the indices for columns in the distance
    matrixes which correspond to postcode districts in that constituency, to be used later
    to create a, weighted by demand in each district, distance figure for each potential
    warehouse location to each relevant constituency.    
    """
    pc_lookup = pd.read_csv("pcd_pcon_uk_lu_may_24_cut.csv")
    pc_lookup["pcd"] = pc_lookup["pcd"].str.replace(" ", "")

    pc_dict = {postcode: constituency for postcode, constituency in zip(pc_lookup["pcd"], pc_lookup["pconnm"])}

    PostcodeDistricts["Constituency"] = PostcodeDistricts["Reference PC"].map(pc_dict)

    constituency_set = set(PostcodeDistricts["Constituency"].tolist())

    print(f"number of consitutencies  {len(constituency_set)}")

    index_dict = {constituency: list(PostcodeDistricts[PostcodeDistricts["Constituency"]==constituency].index)
                  for constituency in constituency_set
    }

  
    return PostcodeDistricts, index_dict


def get_clustered_demand(DemandPeriods_df: pd.DataFrame, PostcodeDistricts_constituency: pd.DataFrame)->Tuple[dict, dict]:
    """
    Purpose of the function is to group demand for each postcode district in a given constituency,
    for product and period.
    Moreover, we return the demand periods dataframe with a column to indicate proportion of total demand for the 
    constituency heading to a specific postcode district in each time period, summed over product type.
    """

    DemandPeriods_df = pd.merge(DemandPeriods_df, PostcodeDistricts_constituency[["District ID", "Constituency"]],
                                how="left", left_on="Customer", right_on="District ID")
    
    
    DemandPeriod_grouped_demand = DemandPeriods_df.groupby(["Product", "Period", "Constituency"])["Demand"].sum()
    DemandPeriod_grouped_demand = DemandPeriod_grouped_demand.reset_index()
   
    DemandPeriod_grouped_demand_over_product = DemandPeriods_df.groupby(["Period", "Constituency"])["Demand"].sum()
    DemandPeriod_grouped_demand_over_product = DemandPeriod_grouped_demand_over_product.reset_index()

    DemandPeriodsGrouped = (
    DemandPeriod_grouped_demand
        .set_index(["Constituency", "Product", "Period"])["Demand"]
        .to_dict()
    )
    

    DemandPeriod_grouped_demand_over_product = DemandPeriod_grouped_demand_over_product.rename(columns={"Demand": "GroupedDemand"})

    DemandPeriods_df = DemandPeriods_df.groupby(["Customer", "Period", "Constituency"])["Demand"].sum()
    DemandPeriods_df = DemandPeriods_df.reset_index()

    DemandPeriods_df = pd.merge(DemandPeriods_df, DemandPeriod_grouped_demand_over_product,
                                how="left", on = ["Constituency", "Period"])
    
    DemandPeriods_df["DemandProportion"] = DemandPeriods_df["Demand"] / DemandPeriods_df["GroupedDemand"]

    return DemandPeriodsGrouped, DemandPeriods_df 


def get_clustered_distance_weighted_by_demand(DistanceDistrictDistrict_df: pd.DataFrame,
                                              DemandPeriods_df: pd.DataFrame,
                                              con_index_dict: dict)->dict:
    """
    Purpose of the function is to create a distance value from each potential warehouse location
    to each relevant parliamentary constituency, for each time period.
    TO do this, for each potential warehouse location, we sum the weighted distance of each postcode district
    in the constituency to the potential warehouse location, weighted by its proportion of total constituency demand,
    in each time period.
    """
    
    con_distances = {constituency: DistanceDistrictDistrict_df[[i + 1 for i in constituency_indices]] 
                     for constituency, constituency_indices in con_index_dict.items()}
    
   
    demand_periods = list(set(DemandPeriods_df["Period"]))
    demand_periods.sort()

    
    weighted_con_distance_dict = {}

    for p in demand_periods:
        DemandPeriods_df_year = DemandPeriods_df[DemandPeriods_df["Period"] == p]        
        for con in con_distances.keys():
            DemandPeriods_df_year_ct = DemandPeriods_df_year[DemandPeriods_df_year["Constituency"] == con]
            con_distances_array = con_distances[con].to_numpy()
            weights = DemandPeriods_df_year_ct["DemandProportion"].to_numpy()
            weighted_con_distance_dict[(con, p)] = pd.Series(con_distances_array.dot(weights))

    return weighted_con_distance_dict   


