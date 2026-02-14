def get_filepath()->str:
    filepath = "CaseStudyDataPY"
    return filepath

def number_of_scenarios_to_use():
    return 1


def cluster_size():
    return 10

def clustertype():
    """
    return 'parliament' if you want to cluster demand by westminster parliamentary constituency
    return kmeans{cluster_size()} if you'd like to cluster demand, k being set by the cluster size function above
    """
    #return "parliament"
    return f"kmeans{cluster_size()}"

# =============================================================================
# Vehicle-related data
# Vehicles are indexed as:
#   1 = 18t trucks
#   2 = 7.5t lorries
#   3 = 3.5t vans
# =============================================================================

# Vehicle capacity in tonnes
VehicleCapacity = {
    1: 9.0,
    2: 2.4,
    3: 1.5
}

# Cost in pounds per mile travelled (fixed cost)
VehicleCostPerMileOverall = {
    1: 1.666,
    2: 1.727,
    3: 1.285
}

# Cost in pounds per mile and tonne transported (variable cost)
VehicleCostPerMileAndTonneOverall = {
    1: 0.185,
    2: 0.720,
    3: 0.857
}

# CO₂ emissions in kg per mile and tonne transported
VehicleCO2PerMileAndTonne = {
    1: 0.11,
    2: 0.31,
    3: 0.30
}
