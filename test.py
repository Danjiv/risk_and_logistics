import pandas as pd
import xpress as xp
import os
import zipfile
import preprocessing 

data_dir = "CaseStudyDataPY"

#PostcodeDistricts = pd.read_csv(f"{data_dir}/PostcodeDistricts.csv", index_col=0)
PostcodeDistricts = pd.read_csv(f"{data_dir}/PostcodeDistricts.csv")

PostcodeDistricts_constituency, con_index_dict  = preprocessing.get_constituency(PostcodeDistricts)

DemandPeriods_df = pd.read_csv(f"{data_dir}/DemandPeriods.csv")

DemandPeriodsGrouped, DemandPeriodsProportion = preprocessing.get_clustered_demand(DemandPeriods_df, PostcodeDistricts_constituency)

DistanceDistrictDistrict_df = pd.read_csv(
    f"{data_dir}/Distance District-District.csv", index_col=0
)
DistanceDistrictDistrict_df.columns = DistanceDistrictDistrict_df.columns.astype(int)

preprocessing.get_clustered_distance_weighted_by_demand(DistanceDistrictDistrict_df,
                                                        DemandPeriodsProportion,
                                                        con_index_dict)


#PostcodeDistricts[PostcodeDistricts["Constituency"]=="Aberdeen South"].to_csv("working.csv")
#PostcodeDistricts.to_csv("working.csv")
#print(constituency_index_dict["Aberdeen North"])
#in each constituency, just take the postcode district with min distance to all other postcode districts!!

print("ok!")