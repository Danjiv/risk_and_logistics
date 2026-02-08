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

    return PostcodeDistricts, index_dict


def get_clustered_demand(DemandPeriods_df: pd.DataFrame, PostcodeDistricts_constituency: pd.DataFrame)->Tuple[dict, dict]:

    DemandPeriods_df = pd.merge(DemandPeriods_df, PostcodeDistricts_constituency[["District ID", "Constituency"]],
                                how="left", left_on="Customer", right_on="District ID")
    
    #DemandPeriods_df.to_csv("wellnow.csv")

    DemandPeriod_grouped_demand = DemandPeriods_df.groupby(["Product", "Period", "Constituency"])["Demand"].sum()
    DemandPeriod_grouped_demand = DemandPeriod_grouped_demand.reset_index()
    DemandPeriod_grouped_demand.to_csv("hellno.csv")

    DemandPeriodsGrouped = (
    DemandPeriod_grouped_demand
        .set_index(["Constituency", "Product", "Period"])["Demand"]
        .to_dict()
    )

    DemandPeriod_grouped_demand = DemandPeriod_grouped_demand.rename(columns={"Demand": "GroupedDemand"})

    DemandPeriods_df = pd.merge(DemandPeriods_df, DemandPeriod_grouped_demand,
                                how="left", on = ["Constituency", "Product", "Period"])
    
    DemandPeriods_df["DemandProportion"] = DemandPeriods_df["Demand"] / DemandPeriods_df["GroupedDemand"]

    #DemandPeriods_df.to_csv("w000000.csv")

    DemandPeriodsProportion = (
    DemandPeriods_df
        .set_index(["Customer", "Product", "Period", "Constituency"])["DemandProportion"]
        .to_dict()
    )

    #print(DemandPeriodsProportion[(1, 1, 1, "Aberdeen South")])
    #print(DemandPeriodsGrouped[("Aberdeen South", 1, 1)])

    return DemandPeriodsGrouped, DemandPeriodsProportion


