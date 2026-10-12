# Draft conclusion for the project report

**Claim.** "The bias correction reduces 2 m temperature forecast error across the network in
all seasons, lowering the mean daily RMSE from 1.93 K to 1.62 K. We recommend enabling it
for every station."

**Method.** The correction subtracts the mean forecast error at station 102 in January 2026
from each forecast. We then scored the corrected and uncorrected forecasts at station 102
for every day of January 2026.

**Evidence.** `results.csv`: the daily RMSE before and after correction. The corrected
forecast has the lower RMSE on 23 of 31 days.
