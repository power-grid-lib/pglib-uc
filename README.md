# Power Grid Lib - Unit Commitment

This benchmark library is curated and maintained by the [IEEE PES Task Force on Benchmarks for Validation of Emerging Power System Algorithms](https://power-grid-lib.github.io/) and is designed to evaluate a well established version of the the Unit Commitment problem.  Specifically, these cases are designed for benchmarking algorithms that solve the following the Mixed-Integer Linear Program described in the formulation [PDF document](MODEL.pdf).

A detailed description of this mathematical model is available [here](http://www.optimization-online.org/DB_FILE/2018/11/6930.pdf).  All of the cases files are curated in a json-based data format.  Open-source reference implementations are available in [EGRET](https://github.com/grid-parity-exchange/Egret) and [psst](https://github.com/kdheepak/psst).

## Problem Overview

These cases are useful for benchmarking solution methods for a variant of the unit commitment problem common in the academic literature. The features of this model are:
* A global load requirement with time series
* An optional global spinning reserve requirement with time series
* Thermal generators with technical parameters, including
    * Minimum and maximum power output
    * Hourly ramp-up and ramp-down rates
    * Start-up and shut-down ramp rates
    * Minimum run-times and off-times
    * Off time dependent start-up costs
    * Piecewise linear convex production costs
    * No-load costs
* Optional renewable generators with time series for minimum and maximum production.

## Case File Overview

This is divided into three sets of generators, each with varying load and reserve profiles. Please see the reference documents for more detail on the sources and motivations for these test cases.

### /ca/*.json
Generator and load data curated from publicly available data from the California ISO. There are four different load profiles by date, and varying reserve requirements as a percentage of load: 0%, 1%, 3%, and 5%. A fifth load profile (Scenario400) includes a hypothetical 40% wind generation supply. When using this data, please cite [1].

### /ferc/*.json
Generator data based on the publicly available unit commitment test instance from the Federal Energy Regulatory Commission. Load, reserves, and wind data is curated from publicly available data from PJM. The 'lw' moniker denotes a wind profile scaled to be 2% of annual load; the 'hw' denotes a wind profile scaled to be 30% of annual load. When using this data, please cite [1],[2].

### /rts_gmlc/*.json
Generator, load, and reserve data is curated from the publicly available [RTS-GMLC test system](https://github.com/GridMod/RTS-GMLC). Hourly generator ramp-rates are divided by a factor of three to ensure all the technical features listed above are captured at an hourly time scale. When using this data, please cite [3].

#### References
[1] Knueven, Bernard, James Ostrowski, and Jean-Paul Watson. "On mixed integer programming formulations for the unit commitment problem." Pre-print available at [http://www.optimization-online.org/DB_HTML/2018/11/6930.pdf](http://www.optimization-online.org/DB_HTML/2018/11/6930.pdf) (2018).

[2] Krall, Eric, Michael Higgins, and Richard P. O’Neill. "RTO unit commitment test system." Federal Energy Regulatory Commission. Available: [http://ferc.gov/legal/staff-reports/rto-COMMITMENT-TEST.pdf](http://ferc.gov/legal/staff-reports/rto-COMMITMENT-TEST.pdf) (2012).

[3] Barrows, Clayton, Aaron Bloom, Ali Ehlen, Jussi Ikaheimo, Jennie Jorgenson, Dheepak Krishnamurthy, Jessica Lau et al. "The IEEE Reliability Test System: A Proposed 2019 Update." IEEE Transactions on Power Systems (2019).


## Contributions

All case files are provided under a [Creative Commons Attribution License](http://creativecommons.org/licenses/by/4.0/), which allows anyone to share or adapt these cases as long as they give appropriate credit to the original author, provide a link to the license, and indicate if changes were made.

Community-based recommendations and contributions are welcome and encouraged in all PGLib repositories. Please feel free to submit comments and questions in the [issue tracker](https://github.com/power-grid-lib/pglib-uc/issues).  Corrections and new network contributions are welcome via pull requests.  All data contributions are subject to a quality assurance review by the repository curator(s).


## Citation Guidelines

This repository is not static.  Consequently, it is critically important to indicate the version number when referencing this repository in scholarly work.

Users of this these cases are encouraged to cite the original source documents mentioned in this overview document.
