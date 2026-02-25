# Production Line Analysis for ByrnSil
This script simulates production over a number of years, and can be configured to explore different investment scenarios.

## Config
The code can be configured to explore various scenarios by changing the following variables:
* `LEGACY_PER_YEAR`, `MRI_PER_YEAR` and `MAX_AI` - yearly production targets for each product. Some preset values that were used in the analysis are present here, and can be commented in and out as needed.
* `ACTIVE_INVESTMENTS` - selects what investments to use for the scenario
* The following blocks in `solve_year()`:
    `prob += (`
    `   x["Legacy"] == LEGACY_PER_YEAR[year-1]`
    `)`
    `prob += (`
    `    x["MRI"] + x["MRI2"] == MRI_PER_YEAR[year-1]`
    `)`
    `prob += (`
    `    x["AI"] + x["AI2"] == MAX_AI[year-1]`
    `)`

    These can be tweaked to determine whether a production target is a maximum ( `<=`), minimum (`>=`), or exact target (`==`)

* `LABOUR_GROWTH_RATE` = 512000
    How much the workforce can grow each year (in labour-hours). This model assumes that the workforce can double in 5 years' time.

## How to use this tool

Once a scenario is configured by altering the variables above, running the script gives a 5-year breakdown of the following figures for each year:
- The value of each constraint
- The production mix (i.e. how much of each product to aim to produce)
- A summary of what constraints were holding back production
- The optimal profit for the year - this is the lower bound of contributions, assuming a 15% royalty on AI chips

It also exports the results to a `results.csv` file, which also contains the lower and upper bounds on contributions and the lower and upper bounds on revenue.

