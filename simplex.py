"""
Multi-Year Production Line Optimiser
=====================================
Solves an LP for each year in a timeline, automatically updating
constraint capacities based on labour growth and investment schedules.

INSTRUCTIONS:
    1. Edit the CONFIGURATION section below with your real data.
    2. Define your investments in the INVESTMENTS section.
    3. Run: python production_optimiser.py
    Results will be printed to the console and saved to results.csv.
"""

import csv
from pulp import *

# =============================================================================
# CONFIGURATION - Edit this section with your data
# =============================================================================

YEARS = 5  # Number of years to model

# --- Products ---
PRODUCTS = ["Legacy", "MRI", "AI", "MRI2", "AI2"]
PROFIT_PER_UNIT_LWR = {"Legacy": 19, "MRI": 37.6, "AI": 104.88, "MRI2": 37.6, "AI2": 104.88}
PROFIT_PER_UNIT_HIR = {"Legacy": 19, "MRI": 37.6, "AI": 115, "MRI2": 37.6, "AI2": 115}
REV_PER_UNIT_LWR = {"Legacy": 42.75, "MRI": 75.2, "AI": 172.04, "MRI2": 75.2, "AI2": 172.04}
REV_PER_UNIT_HIR = {"Legacy": 42.75, "MRI": 75.2, "AI": 182.16, "MRI2": 75.2, "AI2": 182.16}


# LEGACY_PER_YEAR = [2100755, 1979288, 1857822, 1736355, 1614889] # 121466 (5.5%) reduction per year; slightly faster than market decline. Use when keeping AI chips around
LEGACY_PER_YEAR = [2111111, 2000000, 1888889, 1777778, 1666667] # 111111 (5%) reduction per year; exactly in line with market decline. Use when AI chips no longer an option.
MRI_PER_YEAR    = [1962765, 2289892, 2617019, 2826380, 3035741] # Above mkt growth
# MRI_PER_YEAR    = [1908244, 2180850, 2453456, 2726062, 2998668] # Market growth
# MAX_AI          = [209790, 314685, 419580, 524475, 629370] # ensures 250% growth at most. Or rather, slightly less, since I forgot to account for WASTE AGAIN
MAX_AI          = [228032, 342048, 456064, 570080, 684096] # Accounting for waste
# MAX_AI          = [0, 0, 0, 0, 0] # no AI chips

# --- Constraints ---
# Names and base (Year 0) capacities for each constraint.
CONSTRAINTS = ["Labour", "Wafer_Cutting", "Line_1", "Line_2", "Energy", "Station_B", "x45max", ]
BASE_CAPACITY = {
    "Labour":        2560000,
    "Wafer_Cutting": 800000,
    "Line_1":        640000,
    "Line_2":        1248000,
    "Energy":        64000000,
    "Station_B":     5280000,
    "x45max":        0,
}

USAGE = {
    "Labour":        {"Legacy": 0.5,   "MRI": 0.8,   "AI": 1.2,   "MRI2": 0.8,   "AI2": 1.2},
    "Wafer_Cutting": {"Legacy": 0.2,   "MRI": 0.2,   "AI": 0.2,   "MRI2": 0.2,   "AI2": 0.2},
    "Line_1":        {"Legacy": 0.2,   "MRI": 0.0,   "AI": 0.0,   "MRI2": 0.4,   "AI2": 0.8},
    "Line_2":        {"Legacy": 0.0,   "MRI": 0.4,   "AI": 0.8,   "MRI2": 0.0,   "AI2": 0.0},
    "Energy":        {"Legacy": 4.0,   "MRI": 7.0,   "AI": 10.0,  "MRI2": 7.0,   "AI2": 10.0},
    "Station_B":     {"Legacy": 1.0,   "MRI": 1.0,   "AI": 1.0,   "MRI2": 1.0,   "AI2": 1.0},
    "x45max":        {"Legacy": 0.0,   "MRI": 0.0,   "AI": 0.0,   "MRI2": 1.0,   "AI2": 1.0},
}

# --- Labour Growth per year.
LABOUR_GROWTH_RATE = 522000 # Gives just enough to reach tgt by end of 5 years

# =============================================================================
# INVESTMENTS - Define available investments here
# =============================================================================

INVESTMENTS = [
    {
        "name":            "Wafer Cutting Module 1",
        "constraint":      "Wafer_Cutting",
        "install_months":  3.5,        # 3-4 months to install
        "full_capacity":   200000,   # +200,000 machine hours/year once installed
    },
    {
        "name":            "Wafer Cutting Module 2",
        "constraint":      "Wafer_Cutting",
        "install_months":  3.5,
        "full_capacity":   200000,
    },
    {
        "name":            "Wafer Cutting Module 3",
        "constraint":      "Wafer_Cutting",
        "install_months":  3.5,        # 3 months to install
        "full_capacity":   200000,   # +200,000 machine hours/year once installed
    },
    {
        "name":            "Line 3",
        "constraint":      "Line_2",
        "install_months":  13,       # min 12, max 14
        "full_capacity":   1248000,
    },
    {
        "name":            "Station B Upgrade",
        "constraint":      "Station_B",
        "install_months":  6,        # 6 months to install
        "full_capacity":   2376000,  # min 2376000, max 2904000
        "downtime_months": 1
    },
    {
        "name": "Line_1_Upgrade",
        "constraint": "x45max",
        "install_months": 5,
        "full_capacity": 12000000, # infinite
        "downtime_months": 1
    }
]

# =============================================================================
# SCENARIO SELECTION - Choose which investments to include
# =============================================================================
# Set each investment to True or False to toggle it on/off.
# This lets you quickly compare different investment combinations.

ACTIVE_INVESTMENTS = {
    "Wafer Cutting Module 1":  True,
    "Wafer Cutting Module 2":  True,
    "Wafer Cutting Module 3":  False,
    "Line 3":                  False,
    "Station B Upgrade":       False,
    "Line_1_Upgrade":          True
}

# =============================================================================
# CAPACITY CALCULATION
# =============================================================================

def compute_capacity_schedule():
    """
    Returns a dict: capacity_schedule[year][constraint] = capacity
    Year 1 is the first year of the timeline.
    """
    schedule = {}

    for year in range(1, YEARS + 1):
        schedule[year] = {}

        for constraint in CONSTRAINTS:
            # Start from base capacity
            cap = BASE_CAPACITY[constraint]

            # Apply labour growth if this is the labour constraint
            if constraint == "Labour":
                cap += LABOUR_GROWTH_RATE * year

            # Apply each active investment that affects this constraint
            for inv in INVESTMENTS:
                if inv["constraint"] != constraint:
                    continue
                if not ACTIVE_INVESTMENTS.get(inv["name"], False):
                    continue

                install_months = inv["install_months"]
                full_cap = inv["full_capacity"]

                # Which year does the investment finish in, and how
                # many months of that year is it actually active?
                # e.g. 14 months -> finishes in Year 2, active for 10 months
                finish_year        = (install_months // 12) + 1
                months_active      = 12 - (install_months % 12)
                # If install_months is an exact multiple of 12 (e.g. 12, 24),
                # the investment finishes at the very start of the next year,
                # so it contributes a full year there, not a partial one.
                if install_months % 12 == 0:
                    finish_year   = install_months // 12 + 1
                    months_active = 12

                if year < finish_year:
                    pass                                        # Still being installed
                elif year == finish_year:
                    cap += full_cap * (months_active / 12)      # Partial year
                else:
                    cap += full_cap                             # Fully operational

            schedule[year][constraint] = cap

        for inv in INVESTMENTS:
            if not ACTIVE_INVESTMENTS.get(inv["name"], False):
                continue
            if inv.get("downtime_months", 0) == 0:
                continue

            finish_year = (inv["install_months"] // 12) + 1
            if inv["install_months"] % 12 == 0:
                finish_year = inv["install_months"] // 12 + 1

            if year == finish_year:
                downtime_factor = (12 - inv["downtime_months"]) / 12
                for constraint in CONSTRAINTS:
                    schedule[year][constraint] *= downtime_factor
    


    return schedule


# =============================================================================
# OPTIMISATION - Solves one LP per year
# =============================================================================

def solve_year(year, capacities):
    """
    Solves the LP for a single year given a dict of capacities.
    Returns a results dict with optimal values, profit, and constraint info.
    """
    prob = LpProblem(f"Production_Year_{year}", LpMaximize)

    # Decision variables: units of each product to produce
    x = {p: LpVariable(p, lowBound=0) for p in PRODUCTS}

    # Objective: maximise total profit
    prob += lpSum(PROFIT_PER_UNIT_LWR[p] * x[p] for p in PRODUCTS), "Total_Profit"

    # Constraints
    for constraint in CONSTRAINTS:
        prob += (
            lpSum(USAGE[constraint][p] * x[p] for p in PRODUCTS)
            <= capacities[constraint],
            constraint
        )

    # Add minimum quantities of legacy and MRI chips, otherwise AI takes over
    prob += (
        x["Legacy"] <= LEGACY_PER_YEAR[year-1]
    )
    prob += (
        x["MRI"] + x["MRI2"] == MRI_PER_YEAR[year-1]
    )
    prob += (
        x["AI"] + x["AI2"] == MAX_AI[year-1]
    )
    # Solve (using the default CBC solver; suppress output)
    prob.solve(PULP_CBC_CMD(msg=0))

    # --- Extract results ---
    results = {"year": year, "status": LpStatus[prob.status]}

    # Optimal production quantities
    for p in PRODUCTS:
        results[p] = x[p].varValue

    # Optimal profit
    results["profit_lwr"] = value(prob.objective)
    results["profit_hir"] = sum(PROFIT_PER_UNIT_HIR[p]*x[p].varValue for p in PRODUCTS)
    results["revenue_lwr"] = sum(REV_PER_UNIT_LWR[p]*x[p].varValue for p in PRODUCTS)
    results["revenue_hir"] = sum(REV_PER_UNIT_HIR[p]*x[p].varValue for p in PRODUCTS)


    # Constraint utilisation and binding status
    results["constraints"] = {}
    for constraint in CONSTRAINTS:
        used = value(prob.constraints[constraint].expr)
        # PuLP stores constraints as (LHS - RHS <= 0), so slack is -constraint.slack
        slack = -prob.constraints[constraint].slack
        utilisation = (used / capacities[constraint]) * 100 if capacities[constraint] > 0 else 0
        is_binding = abs(slack) < 1e-6  # Effectively zero slack

        results["constraints"][constraint] = {
            "capacity":     capacities[constraint],
            "used":         used,
            "slack":        slack,
            "utilisation":  utilisation,
            "binding":      is_binding,
        }

    return results


# =============================================================================
# REPORTING
# =============================================================================

def print_results(all_results):
    """Prints a formatted summary of all years to the console."""
    print("\n" + "=" * 70)
    print(" MULTI-YEAR PRODUCTION OPTIMISATION RESULTS")
    print("=" * 70)

    # Print which investments are active
    active = [name for name, on in ACTIVE_INVESTMENTS.items() if on]
    print(f"\nActive investments: {', '.join(active) if active else 'None'}\n")

    for res in all_results:
        print("-" * 70)
        print(f"  YEAR {res['year']}  |  Status: {res['status']}  |  Optimal Profit: {res['profit_lwr']:.2f}")
        print("-" * 70)

        # Production mix
        print("  Production Mix:")
        for p in PRODUCTS:
            print(f"    {p:20s} {res[p]:>12.2f} units")

        # Constraint table
        print("\n  Constraints:")
        print(f"    {'Constraint':<20s} {'Capacity':>12s} {'Used':>12s} {'Utilisation':>12s} {'Binding':>8s}")
        for c in CONSTRAINTS:
            info = res["constraints"][c]
            binding_flag = "  <---" if info["binding"] else ""
            print(f"    {c:<20s} {info['capacity']:>12.2f} {info['used']:>12.2f} {info['utilisation']:>11.1f}% {binding_flag}")

        print()

    # Identify the binding constraint in each year (useful for investment decisions)
    print("=" * 70)
    print(" BOTTLENECK SUMMARY")
    print("=" * 70)
    for res in all_results:
        binding = [c for c in CONSTRAINTS if res["constraints"][c]["binding"]]
        print(f"  Year {res['year']}: Binding constraints: {', '.join(binding) if binding else 'None'}")
    print()


def export_csv(all_results, filename="results.csv"):
    """Exports results to a CSV file for easy use in presentations."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        header = ["Year", "Status", "Profit (lower)", "Profit (upper)", "Revenue (lower)", "Revenue (upper)"] + PRODUCTS
        for c in CONSTRAINTS:
            header += [f"{c}_Capacity", f"{c}_Used", f"{c}_Utilisation_%", f"{c}_Binding"]
        writer.writerow(header)

        # Rows
        for res in all_results:
            row = [res["year"], res["status"], f"{res['profit_lwr']:.2f}", f"{res['profit_hir']:.2f}", f"{res['revenue_lwr']:.2f}", f"{res['revenue_hir']:.2f}"]
            row += [f"{res[p]:.2f}" for p in PRODUCTS]
            for c in CONSTRAINTS:
                info = res["constraints"][c]
                row += [
                    f"{info['capacity']:.2f}",
                    f"{info['used']:.2f}",
                    f"{info['utilisation']:.1f}",
                    info["binding"],
                ]
            writer.writerow(row)

    print(f"  Results exported to {filename}")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    # 1. Build the capacity schedule for all years
    capacity_schedule = compute_capacity_schedule()

    print("\nCapacity Schedule:")
    print(f"  {'Year':<6s}", end="")
    for c in CONSTRAINTS:
        print(f"{c:>15s}", end="")
    print()
    for year in range(1, YEARS + 1):
        print(f"  {year:<6d}", end="")
        for c in CONSTRAINTS:
            print(f"{capacity_schedule[year][c]:>15.2f}", end="")
        print()

    # 2. Solve for each year
    all_results = []
    for year in range(1, YEARS + 1):
        result = solve_year(year, capacity_schedule[year])
        all_results.append(result)

    # 3. Print and export results
    print_results(all_results)
    export_csv(all_results)