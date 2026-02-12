import pandas as pd
from typing import Tuple
import constants

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

    #PostcodeDistricts.to_csv("heynow.csv")
    #hi = PostcodeDistricts.groupby("Constituency")['Population'].sum()
    #hi.to_csv("wowtcha.csv")
    #wotcha = cool

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


def get_total_demand_per_product_per_period(DemandPeriods_df: pd.DataFrame)->dict:
        DemandPeriods_total = DemandPeriods_df.groupby(["Product", "Period"])["Demand"].sum()
        DemandPeriods_total.to_csv("checkgood.csv")
        DemandPeriodsTotal_dict = (
        DemandPeriods_total.reset_index()
            .set_index(["Product", "Period"])["Demand"]
            .to_dict()
        )

        return DemandPeriodsTotal_dict


def read_input_data_and_preprocess():
    """
    Read in all relevant input data, group demand and distances between candidates + customers
    """
    data_dir = constants.get_filepath()
    
    # -----------------------------------------------------------------------------
    # Read supplier data
    # The first column is used as the supplier index
    # -----------------------------------------------------------------------------
    Suppliers_df = pd.read_csv(f"{data_dir}/Suppliers.csv", index_col=0)
    Vehicle_df = pd.read_csv(f"{data_dir}/vehicleType.csv", index_col=0)
    # -----------------------------------------------------------------------------
    # Read postcode district data (used to define customers)
    # Group postcode demand data by westminster parliamentary constituency
    PostcodeDistricts = pd.read_csv(f"{data_dir}/PostcodeDistricts.csv")
    PostcodeDistricts_constituency, con_index_dict  = get_constituency(PostcodeDistricts)


    # Read demand data with time periods
    # Creates a dictionary keyed by (Customer, Product, Period)
    # Roll up total demand for each product for each period
    # And group demand for each product for each period for each consituency

    DemandPeriods_df = pd.read_csv(f"{data_dir}/DemandPeriods.csv")

    TotalDemandProductPeriod_dict = get_total_demand_per_product_per_period(DemandPeriods_df)

    DemandPeriodsGrouped, DemandPeriodsProportion = get_clustered_demand(DemandPeriods_df, PostcodeDistricts_constituency)

    # -----------------------------------------------------------------------------
    # Read demand data with time periods and scenarios
    # Creates a dictionary keyed by (Customer, Product, Period, Scenario)
    # -----------------------------------------------------------------------------
    DemandPeriodsScenarios_df = pd.read_csv(f"{data_dir}/DemandPeriodScenarios.csv")
    DemandPeriodsScenarios_df = DemandPeriodsScenarios_df[DemandPeriodsScenarios_df["Scenario"] <= constants.number_of_scenarios_to_use()]

    DemandPeriodsGrouped_scenarios = []
    DemandPeriodsProportion_scenarios = []
    for i in range(constants.number_of_scenarios_to_use()):
        
        DemandPeriodsScenarios_singular_df = DemandPeriodsScenarios_df[DemandPeriodsScenarios_df["Scenario"]==i+1]
        DemandPeriodsGrouped_single_scenario, DemandPeriodsProportion_single_scenario = get_clustered_demand(
            DemandPeriodsScenarios_singular_df, PostcodeDistricts_constituency)
        DemandPeriodsGrouped_scenarios.append(DemandPeriodsGrouped_single_scenario)
        DemandPeriodsProportion_scenarios.append(DemandPeriodsProportion_single_scenario)

    TotalDemandProductPeriodScenarios_dict = []
    for i in range(constants.number_of_scenarios_to_use()):
        DemandPeriodsScenarios_singular_df = DemandPeriodsScenarios_df[DemandPeriodsScenarios_df["Scenario"]==i+1]
        TotalDemandProductPeriodSingleScenario = get_total_demand_per_product_per_period(DemandPeriodsScenarios_singular_df)
        TotalDemandProductPeriodScenarios_dict.append(TotalDemandProductPeriodSingleScenario)
 
    # Group postcode demand data by westminster parliamentary constituency for each scenario



    # -----------------------------------------------------------------------------
    # Read candidate facility data
    # -----------------------------------------------------------------------------
    Candidates_df = pd.read_csv(f"{data_dir}/Candidates.csv", index_col=0)

    # -----------------------------------------------------------------------------
    # Read candidate capacity and setup operating costs data

    Capacity_df = pd.read_csv(f"{data_dir}/Capacity.csv")
    Setup_df = pd.read_csv(f"{data_dir}/Setup.csv")
    Operating_df = pd.read_csv(f"{data_dir}/Operating.csv")

    # -----------------------------------------------------------------------------
    # Read distance matrices
    # Supplier → District distances
    # District → District distances
    # -----------------------------------------------------------------------------

    DistanceSupplierDistrict_df = pd.read_csv(
        f"{data_dir}/Distance Supplier-District.csv", index_col=0
    )
    DistanceSupplierDistrict_df.columns = DistanceSupplierDistrict_df.columns.astype(int)

    #Adjust distance based on grouping by parliamentary constituency,
    #weighted by proportion of total demand in each constituency by demand in each
    # individual postcode district, for each period

    DistanceDistrictDistrict_df = pd.read_csv(
        f"{data_dir}/Distance District-District.csv", index_col=0
    )
    DistanceDistrictDistrict_df.columns = DistanceDistrictDistrict_df.columns.astype(int)

    DistanceDistrictPeriod_df_dict = get_clustered_distance_weighted_by_demand(DistanceDistrictDistrict_df,
                                                                               DemandPeriodsProportion,
                                                                               con_index_dict)
    DistanceDistrictPeriod_df_scenarios_dict_list = []
    
    for i in range(constants.number_of_scenarios_to_use()):
        DistanceDistrictPeriod_df_dict_single_scenario = get_clustered_distance_weighted_by_demand(
            DistanceDistrictDistrict_df,
            DemandPeriodsProportion_scenarios[i],
            con_index_dict)
        DistanceDistrictPeriod_df_scenarios_dict_list.append(DistanceDistrictPeriod_df_dict_single_scenario)
    


    return (Suppliers_df, Candidates_df, DemandPeriods_df, DemandPeriodsScenarios_df, DistanceSupplierDistrict_df,
            DistanceDistrictPeriod_df_dict, DemandPeriodsGrouped, con_index_dict, Operating_df, Setup_df,
            DemandPeriodsGrouped_scenarios, DistanceDistrictPeriod_df_scenarios_dict_list,
            TotalDemandProductPeriod_dict, TotalDemandProductPeriodScenarios_dict)


 


