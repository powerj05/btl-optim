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
# Names, and profit per unit for each product.
PRODUCTS = ["Product_A", "Product_B", "Product_C"]
PROFIT_PER_UNIT = {"Product_A": 50, "Product_B": 60, "Product_C": 45}

# --- Constraints ---
# Names and base (Year 0) capacities for each constraint.
CONSTRAINTS = ["Labour", "Wafer_Cutting", "Assembly", "Packaging"]
BASE_CAPACITY = {
    "Labour":        1000,
    "Wafer_Cutting": 800,
    "Assembly":      600,
    "Packaging":     500,
}

# How much of each constraint one unit of each product uses.
# Format: USAGE[constraint][product] = amount
USAGE = {
    "Labour":        {"Product_A": 2,   "Product_B": 3,   "Product_C": 1.5},
    "Wafer_Cutting": {"Product_A": 4,   "Product_B": 0,   "Product_C": 2  },
    "Assembly":      {"Product_A": 0,   "Product_B": 5,   "Product_C": 3  },
    "Packaging":     {"Product_A": 1,   "Product_B": 2,   "Product_C": 1  },
}

# --- Labour Growth ---
# Yearly percentage increase in labour capacity (applied every year).
LABOUR_GROWTH_RATE = 0.05  # 5% per year

# =============================================================================
# INVESTMENTS - Define available investments here
# =============================================================================
# Each investment is a dictionary:
#   "name":             Label for reporting
#   "constraint":       Which constraint it affects
#   "install_months":   How many months installation takes
#   "full_capacity":    The full yearly capacity increase once installed
#
# The script automatically calculates the partial-year increase:
#   partial_year_capacity = full_capacity * (12 - install_months) / 12
#
# In the installation year you get partial_year_capacity.
# In every subsequent year you get full_capacity.
# If install_months >= 12, there is no capacity increase in Year 1.

INVESTMENTS = [
    {
        "name":            "Wafer Cutting Module",
        "constraint":      "Wafer_Cutting",
        "install_months":  3,        # 3 months to install
        "full_capacity":   200000,   # +200,000 machine hours/year once installed
    },
    {
        "name":            "New Production Line",
        "constraint":      "Assembly",
        "install_months":  12,       # Takes the full first year — no benefit until Year 2
        "full_capacity":   150000,
    },
    {
        "name":            "Packaging Upgrade",
        "constraint":      "Packaging",
        "install_months":  6,        # 6 months to install
        "full_capacity":   100000,
    },
]

# =============================================================================
# SCENARIO SELECTION - Choose which investments to include
# =============================================================================
# Set each investment to True or False to toggle it on/off.
# This lets you quickly compare different investment combinations.

ACTIVE_INVESTMENTS = {
    "Wafer Cutting Module":  True,
    "New Production Line":   True,
    "Packaging Upgrade":     False,
}

# =============================================================================
# CAPACITY CALCULATION - No need to edit below this line
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
                cap *= (1 + LABOUR_GROWTH_RATE) ** (year - 1)

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
    prob += lpSum(PROFIT_PER_UNIT[p] * x[p] for p in PRODUCTS), "Total_Profit"

    # Constraints
    for constraint in CONSTRAINTS:
        prob += (
            lpSum(USAGE[constraint][p] * x[p] for p in PRODUCTS)
            <= capacities[constraint],
            constraint
        )

    # Solve (using the default CBC solver; suppress output)
    prob.solve(PULP_CBC_CMD(msg=0))

    # --- Extract results ---
    results = {"year": year, "status": LpStatus[prob.status]}

    # Optimal production quantities
    for p in PRODUCTS:
        results[p] = x[p].varValue

    # Optimal profit
    results["profit"] = value(prob.objective)

    # Constraint utilisation and binding status
    results["constraints"] = {}
    for constraint in CONSTRAINTS:
        used = value(prob.constraints[constraint].expr) + capacities[constraint]
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
        print(f"  YEAR {res['year']}  |  Status: {res['status']}  |  Optimal Profit: {res['profit']:.2f}")
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
        header = ["Year", "Status", "Profit"] + PRODUCTS
        for c in CONSTRAINTS:
            header += [f"{c}_Capacity", f"{c}_Used", f"{c}_Utilisation_%", f"{c}_Binding"]
        writer.writerow(header)

        # Rows
        for res in all_results:
            row = [res["year"], res["status"], f"{res['profit']:.2f}"]
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