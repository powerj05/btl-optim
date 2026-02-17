# Production Line Analysis for ByrnSil
This script simulates production over a number of years, and can be configured to explore different investment scenarios.

## Config
You won't need to touch any of the methods below `compute_capacity_schedule()` - all of the config happens above that, and only the following variables will need to be changed:
- `YEARS` (maybe)
- `PROFIT_PER_UNIT`
- `ÀCTIVE_INVESTMENTS`

**N.B. If using GitHub, DO NOT upload/push any of your changes. I'll be working on some updates over the next few days, and don't want to deal with merging.**

`YEARS = 5`
The number of years to simulate. Unless labour is still a binding constraint in year 5, there's no need to change this.

`PRODUCTS = ["Legacy", "MRI", "AI"]`
`PROFIT_PER_UNIT = {"Legacy": 19, "MRI": 37.6, "AI": 93.96}`

Declares the product names and profit per unit. The only change you might be making here is to the `AI` entry in `PROFIT_PER_UNIT` - depending on the royalty, this can take any of the following values:
| Royalty                                                  | Profit/unit |
| -------------------------------------------------------- | ----------- |
| 35% (current)                                            | 64.4        |
| 15%                                                      | 104.88      |
| 10%                                                      | 115         |
| 12.5% (average)                                          | 109.94      |
| No AI production (i.e. <br>BTL loses access to AI chips) | 0           |


`LEGACY_PER_YEAR = [1950000, 1950000, 1950000, 1950000, 1950000]`
`MRI_PER_YEAR = [1537500, 1537500, 1537500, 1537500, 1537500]`
Minimum amount of legacy and MRI chips to produce in each year. If you change `YEARS`, make sure you change this array so it has the same number of entries. 
NOTE: JB has given us figures for this, so no need to change this either.

`CONSTRAINTS`, `BASE CAPACITY` and `USAGE`
No need to change these either; they stay the same under all scenarios.

`LABOUR_GROWTH_RATE` = 512000
How much the workforce can grow each year. This figure is just a placeholder until MK gets back to me.

`INVESTMENTS`
Details the investments available to BTL. No need to change this.

`ACTIVE_INVESTMENTS`
Change for each scenario by setting investments to `True` or `False`.

## How to use this tool

Once you've set up the scenario - e.g. by setting `PROFIT_PER_UNIT["AI"]` to 0, to simulate BTL losing access to AI production, just run the script with all `ACTIVE_INVESTMENTS` set to `FALSE` to see what happens. The output will show you:
- What the value of each constraint is in each year
- A breakdown of the solution for each year
- A summary of what constraints were holding back production in each year

Once you're run it once, activate one investment that addresses the binding constraint, then check the output to see what's holding it back. Keep going until you can't.

Text me if you have any trouble!

- John