import pandas as pd
from typing import Tuple

def get_constituency(PostcodeDistricts: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    pc_lookup = pd.read_csv("pcd_pcon_uk_lu_may_24_test.csv")
    pc_lookup["pcd"] = pc_lookup["pcd"].str.replace(" ", "")

    pc_dict = {postcode: constituency for postcode, constituency in zip(pc_lookup["pcd"], pc_lookup["pconnm"])}

    PostcodeDistricts["Constituency"] = PostcodeDistricts["Reference PC"].map(pc_dict)

    constituency_set = set(PostcodeDistricts["Constituency"].tolist())

    print(f"number of consitutencies  {len(constituency_set)}")

    index_dict = {constituency: list(PostcodeDistricts[PostcodeDistricts["Constituency"]==constituency].index)
                  for constituency in constituency_set
    }

    #print(index_dict["Aberdeen South"])

    return PostcodeDistricts, index_dict


def get_clustered_demand(DemandPeriods_df: pd.DataFrame, PostcodeDistricts_constituency: pd.DataFrame)->Tuple[dict, dict]:

    DemandPeriods_df = pd.merge(DemandPeriods_df, PostcodeDistricts_constituency[["District ID", "Constituency"]],
                                how="left", left_on="Customer", right_on="District ID")
    
    #DemandPeriods_df.to_csv("wellnow.csv")

    DemandPeriod_grouped_demand = DemandPeriods_df.groupby(["Product", "Period", "Constituency"])["Demand"].sum()
    DemandPeriod_grouped_demand = DemandPeriod_grouped_demand.reset_index()
    DemandPeriod_grouped_demand.to_csv("hellno.csv")

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

   # DemandPeriods_df.to_csv("w2000000.csv")

   # DemandPeriodsProportion = (
   # DemandPeriods_df
   #     .set_index(["Customer", "Product", "Period", "Constituency"])["DemandProportion"]
   #     .to_dict()
   # )

    #print(DemandPeriodsProportion[(1, 1, 1, "Aberdeen South")])
    #print(DemandPeriodsGrouped[("Aberdeen South", 1, 1)])

    return DemandPeriodsGrouped, DemandPeriods_df #DemandPeriodsProportion


def get_clustered_distance_weighted_by_demand(DistanceDistrictDistrict_df: pd.DataFrame,
                                              DemandPeriods_df: pd.DataFrame,
                                              con_index_dict: dict)->dict:
    
    con_distances = {constituency: DistanceDistrictDistrict_df[[i + 1 for i in constituency_indices]] 
                     for constituency, constituency_indices in con_index_dict.items()}
    
    #print(con_distances["Aberdeen South"].head())

    demand_periods = list(set(DemandPeriods_df["Period"]))
    demand_periods.sort()

    #distance_list = []

    weighted_con_distance_dict = {}

    for p in demand_periods:
        DemandPeriods_df_year = DemandPeriods_df[DemandPeriods_df["Period"] == p]        
        for con in con_distances.keys():
            DemandPeriods_df_year_ct = DemandPeriods_df_year[DemandPeriods_df_year["Constituency"] == con]
            con_distances_array = con_distances[con].to_numpy()
            weights = DemandPeriods_df_year_ct["DemandProportion"].to_numpy()
            weighted_con_distance_dict[(con, p)] = pd.Series(con_distances_array.dot(weights))
            #if con == "Aberdeen South" and p == 1:
            #    print(DemandPeriods_df_year_ct)
            #    print(con_distances[con].head())
            #    print(weighted_con_distance_dict[con].head())
                     

        #distance_list.append(pd.DataFrame(weighted_con_distance_dict))

    return weighted_con_distance_dict   


